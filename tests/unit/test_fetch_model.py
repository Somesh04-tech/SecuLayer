"""fetch-model: downloads are kept only when size and SHA-256 match; hosts are pinned.

All tests use httpx's MockTransport. The socket guard blocks real network access.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import httpx
import pytest

from seculayer_demo.fetch_model import (
    FetchError,
    Manifest,
    ManifestFile,
    check_file,
    fetch,
    load_manifest,
    verify,
)

GOOD = b"model bytes " * 100
OTHER = b"tokenizer!" * 10


def manifest_for(files: dict[str, bytes]) -> Manifest:
    return Manifest(
        name="test-model",
        repo="org/repo",
        revision="abc123",
        url_template="https://huggingface.co/{repo}/resolve/{revision}/{file}",
        allowed_hosts=("huggingface.co", ".hf.co"),
        files=tuple(
            ManifestFile(name=name, bytes=len(body), sha256=hashlib.sha256(body).hexdigest())
            for name, body in files.items()
        ),
    )


def serving(bodies: dict[str, bytes], seen: list[str]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        name = request.url.path.rsplit("/", 1)[-1]
        if name in bodies:
            return httpx.Response(200, content=bodies[name])
        return httpx.Response(404)

    return httpx.MockTransport(handler)


def quiet(_: str) -> None:
    pass


def test_downloads_and_verifies(tmp_path: Path) -> None:
    manifest = manifest_for({"model.onnx": GOOD, "tokenizer.json": OTHER})
    seen: list[str] = []
    result = fetch(
        tmp_path,
        manifest,
        transport=serving({"model.onnx": GOOD, "tokenizer.json": OTHER}, seen),
        log=quiet,
    )
    assert result.ok
    assert (tmp_path / "model.onnx").read_bytes() == GOOD
    assert seen == [
        "https://huggingface.co/org/repo/resolve/abc123/model.onnx",
        "https://huggingface.co/org/repo/resolve/abc123/tokenizer.json",
    ]
    assert not list(tmp_path.glob("*.part"))


def test_already_present_files_are_skipped(tmp_path: Path) -> None:
    manifest = manifest_for({"model.onnx": GOOD})
    (tmp_path / "model.onnx").write_bytes(GOOD)
    seen: list[str] = []
    assert fetch(tmp_path, manifest, transport=serving({}, seen), log=quiet).ok
    assert seen == []


def test_size_mismatch_is_rejected(tmp_path: Path) -> None:
    manifest = manifest_for({"model.onnx": GOOD})
    with pytest.raises(FetchError, match="bytes"):
        fetch(tmp_path, manifest, transport=serving({"model.onnx": GOOD[:-5]}, []), log=quiet)
    assert not (tmp_path / "model.onnx").exists()
    assert not list(tmp_path.glob("*.part"))


def test_oversized_download_is_rejected(tmp_path: Path) -> None:
    manifest = manifest_for({"model.onnx": GOOD})
    with pytest.raises(FetchError, match="larger"):
        fetch(tmp_path, manifest, transport=serving({"model.onnx": GOOD + b"x"}, []), log=quiet)
    assert not (tmp_path / "model.onnx").exists()


def test_hash_mismatch_is_rejected(tmp_path: Path) -> None:
    manifest = manifest_for({"model.onnx": GOOD})
    tampered = b"X" + GOOD[1:]
    with pytest.raises(FetchError, match="SHA-256"):
        fetch(tmp_path, manifest, transport=serving({"model.onnx": tampered}, []), log=quiet)
    assert not (tmp_path / "model.onnx").exists()


def test_tampered_local_file_is_replaced(tmp_path: Path) -> None:
    manifest = manifest_for({"model.onnx": GOOD})
    (tmp_path / "model.onnx").write_bytes(b"X" + GOOD[1:])
    assert verify(tmp_path, manifest).mismatched == ["model.onnx"]
    assert fetch(tmp_path, manifest, transport=serving({"model.onnx": GOOD}, []), log=quiet).ok


def test_http_error_status(tmp_path: Path) -> None:
    manifest = manifest_for({"model.onnx": GOOD})
    with pytest.raises(FetchError, match="404"):
        fetch(tmp_path, manifest, transport=serving({}, []), log=quiet)


def test_redirect_to_hf_cdn_is_followed(tmp_path: Path) -> None:
    manifest = manifest_for({"model.onnx": GOOD})

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "huggingface.co":
            return httpx.Response(302, headers={"location": "https://us.aws.cdn.hf.co/blob?x=1"})
        return httpx.Response(200, content=GOOD)

    assert fetch(tmp_path, manifest, transport=httpx.MockTransport(handler), log=quiet).ok


@pytest.mark.parametrize(
    "location",
    [
        "https://evil.example/model.onnx",
        "http://us.aws.cdn.hf.co/model.onnx",
        "https://hf.co.evil.example/x",
    ],
)
def test_redirect_to_other_hosts_is_refused(tmp_path: Path, location: str) -> None:
    manifest = manifest_for({"model.onnx": GOOD})
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.host)
        if request.url.host == "huggingface.co":
            return httpx.Response(302, headers={"location": location})
        return httpx.Response(200, content=GOOD)

    with pytest.raises(FetchError, match="refusing"):
        fetch(tmp_path, manifest, transport=httpx.MockTransport(handler), log=quiet)
    assert seen == ["huggingface.co"]


def test_repository_manifest_matches_the_plan() -> None:
    manifest = load_manifest()
    assert manifest.repo == "gravitee-io/Llama-Prompt-Guard-2-22M-onnx"
    assert manifest.revision == "da68d0f6023c7aeaf6b256eec549de295d5e8740"
    files = {f.name: f for f in manifest.files}
    assert files["model.quant.onnx"].bytes == 72_542_430
    assert files["model.quant.onnx"].sha256 == (
        "38c3f03e30a4d5d229aeb7bf638e778322f8179d0ed0d4953eb22f88d8e0cf6b"
    )
    assert files["tokenizer.json"].bytes == 8_649_291
    assert files["tokenizer.json"].sha256 == (
        "92c8b45d0b12ae0dd9680fbfe9804503542c377d65838558cd0b48a795385dde"
    )
    assert {"LICENSE", "NOTICE"} <= set(files)
    assert all(len(f.sha256) == 64 for f in manifest.files)


def test_check_file_states(tmp_path: Path) -> None:
    file = manifest_for({"a": GOOD}).files[0]
    assert check_file(tmp_path, file) == "missing"
    (tmp_path / "a").write_bytes(GOOD)
    assert check_file(tmp_path, file) == "ok"
    (tmp_path / "a").write_bytes(GOOD[:-1] + b"!")
    assert check_file(tmp_path, file) == "mismatch"
