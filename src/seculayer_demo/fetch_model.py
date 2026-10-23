"""Download and verify the pinned classifier files (docs/PLAN.md §8.1).

This is one of the demo's two allowed outbound connections. Every request, including
redirects, must go to a host listed in models/manifest.toml; a file is kept only when its
size and SHA-256 match the manifest.
"""

from __future__ import annotations

import hashlib
import tomllib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import httpx

from seculayer_demo.config import REPO_ROOT

MANIFEST_PATH = REPO_ROOT / "models" / "manifest.toml"
CHUNK_BYTES = 1 << 20


class FetchError(RuntimeError):
    """A download failed or produced a file that doesn't match the manifest."""


@dataclass(frozen=True)
class ManifestFile:
    name: str
    bytes: int
    sha256: str


@dataclass(frozen=True)
class Manifest:
    name: str
    repo: str
    revision: str
    url_template: str
    allowed_hosts: tuple[str, ...]
    files: tuple[ManifestFile, ...]

    def url(self, file: ManifestFile) -> str:
        return self.url_template.format(repo=self.repo, revision=self.revision, file=file.name)

    def host_allowed(self, host: str) -> bool:
        host = host.lower()
        return any(
            host.endswith(entry) if entry.startswith(".") else host == entry
            for entry in self.allowed_hosts
        )


def load_manifest(path: Path = MANIFEST_PATH) -> Manifest:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    model = data["model"]
    return Manifest(
        name=model["name"],
        repo=model["repo"],
        revision=model["revision"],
        url_template=model["url_template"],
        allowed_hosts=tuple(model["allowed_hosts"]),
        files=tuple(
            ManifestFile(name=f["name"], bytes=int(f["bytes"]), sha256=f["sha256"].lower())
            for f in data["file"]
        ),
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


FileState = Literal["ok", "missing", "mismatch"]


def check_file(directory: Path, file: ManifestFile) -> FileState:
    path = directory / file.name
    if not path.is_file():
        return "missing"
    if path.stat().st_size != file.bytes or sha256_file(path) != file.sha256:
        return "mismatch"
    return "ok"


@dataclass(frozen=True)
class VerifyResult:
    states: dict[str, FileState]

    @property
    def ok(self) -> bool:
        return all(state == "ok" for state in self.states.values())

    @property
    def any_present(self) -> bool:
        return any(state != "missing" for state in self.states.values())

    @property
    def mismatched(self) -> list[str]:
        return [name for name, state in self.states.items() if state == "mismatch"]


def verify(directory: Path, manifest: Manifest | None = None) -> VerifyResult:
    manifest = manifest or load_manifest()
    return VerifyResult({file.name: check_file(directory, file) for file in manifest.files})


def _download(client: httpx.Client, url: str, target: Path, file: ManifestFile) -> None:
    part = target.with_name(target.name + ".part")
    digest = hashlib.sha256()
    size = 0
    try:
        with client.stream("GET", url) as response:
            if response.status_code != 200:
                raise FetchError(f"{file.name}: the server answered HTTP {response.status_code}")
            with part.open("wb") as handle:
                for chunk in response.iter_bytes(CHUNK_BYTES):
                    size += len(chunk)
                    if size > file.bytes:
                        raise FetchError(
                            f"{file.name}: larger than the expected {file.bytes:,} bytes"
                        )
                    digest.update(chunk)
                    handle.write(chunk)
        if size != file.bytes:
            raise FetchError(f"{file.name}: got {size:,} bytes, expected {file.bytes:,}")
        if digest.hexdigest() != file.sha256:
            raise FetchError(f"{file.name}: SHA-256 doesn't match the manifest")
        part.replace(target)
    finally:
        part.unlink(missing_ok=True)


def fetch(
    directory: Path,
    manifest: Manifest | None = None,
    *,
    transport: httpx.BaseTransport | None = None,
    log: Callable[[str], None] = print,
) -> VerifyResult:
    """Download every manifest file that is missing or doesn't match. Raises FetchError."""
    manifest = manifest or load_manifest()
    directory.mkdir(parents=True, exist_ok=True)

    def check_host(request: httpx.Request) -> None:
        if request.url.scheme != "https" or not manifest.host_allowed(request.url.host):
            raise FetchError(f"refusing to contact {request.url.scheme}://{request.url.host}")

    with httpx.Client(
        transport=transport,
        follow_redirects=True,
        timeout=httpx.Timeout(60.0, connect=15.0),
        event_hooks={"request": [check_host]},
    ) as client:
        for file in manifest.files:
            target = directory / file.name
            state = check_file(directory, file)
            if state == "ok":
                log(f"  ok        {file.name} (already present, hash checked)")
                continue
            if state == "mismatch":
                log(f"  replacing {file.name} (hash mismatch)")
            log(f"  fetching  {file.name} ({file.bytes / 1_000_000:.1f} MB)")
            try:
                _download(client, manifest.url(file), target, file)
            except httpx.HTTPError as error:
                raise FetchError(f"{file.name}: download failed ({error})") from error
            log(f"  ok        {file.name} (hash checked)")
    return verify(directory, manifest)
