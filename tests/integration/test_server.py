"""The HTTP server: health, meta, security headers and the single-page-app fallback."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from seculayer_demo.config import Settings
from seculayer_demo.server.app import create_app

EXPECTED_CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-src 'self'; "
    "frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
)


class TmpSettings(Settings):
    """Settings whose data directory is a temporary folder."""

    tmp_data: Path = Path()

    @property
    def data_dir(self) -> Path:
        return self.tmp_data


@pytest.fixture
def dist(tmp_path: Path) -> Path:
    root = tmp_path / "dist"
    (root / "assets").mkdir(parents=True)
    (root / "index.html").write_text("<!doctype html><title>SecuLayer</title>", encoding="utf-8")
    (root / "assets" / "app-abc123.js").write_text("console.log(1)", encoding="utf-8")
    (root / "favicon.svg").write_text("<svg/>", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("outside dist", encoding="utf-8")
    return root


def make_settings(tmp_path: Path, **values: object) -> TmpSettings:
    data = tmp_path / "data"
    data.mkdir(exist_ok=True)
    return TmpSettings(_env_file=None, tmp_data=data, **values)  # type: ignore[call-arg]


@pytest.fixture
def client(tmp_path: Path, dist: Path) -> TestClient:
    return TestClient(create_app(make_settings(tmp_path), dist_dir=dist, warm=False))


def test_health(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.parametrize("path", ["/api/health", "/api/meta", "/", "/lab/inbox", "/api/nope"])
def test_security_headers_on_every_response(client: TestClient, path: str) -> None:
    response = client.get(path)
    assert response.headers["content-security-policy"] == EXPECTED_CSP
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_head_request_carries_csp(client: TestClient) -> None:
    response = client.head("/")
    assert response.status_code == 200
    assert response.headers["content-security-policy"] == EXPECTED_CSP


def test_meta_defaults_offline(client: TestClient) -> None:
    body = client.get("/api/meta").json()
    assert body["mode"] == "replay"
    assert body["live_available"] is False
    assert body["models"] == {
        "target": "gpt-5.4-mini-2026-03-17",
        "compare": "gpt-5.4-2026-03-05",
        "judge": "gpt-5.4-mini-2026-03-17",
    }
    assert body["recordings"] == {"files": 0, "models": []}
    assert body["budget"] == {"limit": 1_500_000, "used": 0, "remaining": 1_500_000}
    assert body["classifier"]["status"] in {"present", "missing"}
    assert isinstance(body["version"], str)


def test_meta_never_exposes_the_key(tmp_path: Path, dist: Path) -> None:
    key = "sk-test-not-a-real-key-0123456789"
    settings = make_settings(tmp_path, OPENAI_API_KEY=key)
    client = TestClient(create_app(settings, mode="live", dist_dir=dist, warm=False))
    response = client.get("/api/meta")
    assert response.json()["live_available"] is True
    assert response.json()["mode"] == "live"
    assert key not in response.text
    assert "sk-" not in response.text


def test_meta_budget_reads_spend_log(tmp_path: Path, dist: Path) -> None:
    settings = make_settings(tmp_path, SECULAYER_TOKEN_BUDGET=10_000)
    lines = [
        {"date": "2026-10-23", "model": "gpt-5.4-mini-2026-03-17", "tokens": 4_000},
        {"date": "2026-10-23", "model": "gpt-5.4-2026-03-05", "tokens": 2_500},
    ]
    settings.spend_log.write_text(
        "\n".join(json.dumps(line) for line in lines) + "\nnot json\n", encoding="utf-8"
    )
    body = TestClient(create_app(settings, dist_dir=dist, warm=False)).get("/api/meta").json()
    assert body["budget"] == {"limit": 10_000, "used": 6_500, "remaining": 3_500}


def test_meta_counts_recordings(tmp_path: Path, dist: Path) -> None:
    settings = make_settings(tmp_path)
    folder = settings.recordings_dir / "gpt-5.4-mini-2026-03-17"
    folder.mkdir(parents=True)
    (folder / "inbox.jsonl.gz").write_bytes(b"\x1f\x8b")
    body = TestClient(create_app(settings, dist_dir=dist, warm=False)).get("/api/meta").json()
    assert body["recordings"] == {"files": 1, "models": ["gpt-5.4-mini-2026-03-17"]}


@pytest.mark.parametrize("path", ["/", "/lab/inbox", "/results", "/lab/inbox?case=x", "/a/b/c"])
def test_spa_fallback_serves_index(client: TestClient, path: str) -> None:
    response = client.get(path)
    assert response.status_code == 200
    assert "<title>SecuLayer</title>" in response.text
    assert response.headers["cache-control"] == "no-cache"


def test_static_files_are_served(client: TestClient) -> None:
    asset = client.get("/assets/app-abc123.js")
    assert asset.status_code == 200
    assert asset.text == "console.log(1)"
    assert "immutable" in asset.headers["cache-control"]
    assert client.get("/favicon.svg").text == "<svg/>"


def test_unknown_api_path_is_json_404(client: TestClient) -> None:
    response = client.get("/api/does-not-exist")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


def test_no_path_traversal_out_of_dist(client: TestClient) -> None:
    response = client.get("/..%2Fsecret.txt")
    assert "outside dist" not in response.text
    response = client.get("/assets/..%2F..%2Fsecret.txt")
    assert "outside dist" not in response.text


def test_missing_frontend_explains_itself(tmp_path: Path) -> None:
    client = TestClient(
        create_app(make_settings(tmp_path), dist_dir=tmp_path / "missing", warm=False)
    )
    response = client.get("/")
    assert response.status_code == 503
    assert "./run.sh" in response.text
    assert client.get("/api/health").status_code == 200
