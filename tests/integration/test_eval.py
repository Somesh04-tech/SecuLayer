"""`seculayer eval` from the committed recordings (§7.4, §9 M7): offline, complete, and
reproducible apart from generated_at and the live-measured latencies."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from seculayer_demo.cli import app
from seculayer_demo.config import get_settings
from seculayer_demo.gateway import RecordingStore

pytestmark = pytest.mark.skipif(
    len(RecordingStore(get_settings().recordings_dir)) == 0, reason="no recordings committed"
)


def evaluate(out: Path, cases: str) -> dict[str, Any]:
    result = CliRunner().invoke(app, ["eval", "--cases", cases, "--out-dir", str(out)])
    assert result.exit_code == 0, result.output
    return json.loads((out / "latest.json").read_text())


def stable(summary: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in summary.items() if k not in ("generated_at", "live")}


def test_eval_twice_is_identical_apart_from_time_and_live_latency(tmp_path: Path) -> None:
    first = evaluate(tmp_path / "one", "inbox.*,support.override")
    second = evaluate(tmp_path / "two", "inbox.*,support.override")
    assert stable(first) == stable(second)
    assert first["generated_at"] and "layer_ms" in first["live"]
    runs = list((tmp_path / "one" / "runs").glob("*.jsonl.gz"))
    assert len(runs) == 1
    assert not (tmp_path / "one" / "RESULTS.md").exists()  # filtered runs don't write the doc


def test_the_committed_summary_is_current() -> None:
    """data/eval/latest.json matches a fresh offline evaluation of the full matrix."""
    committed = get_settings().data_dir / "eval" / "latest.json"
    if not committed.is_file():
        pytest.skip("make eval hasn't been run")
    tmp = committed.parent / ".check"
    try:
        fresh = evaluate(tmp, "*")
    finally:
        for path in sorted(tmp.rglob("*"), reverse=True):
            path.unlink() if path.is_file() else path.rmdir()
        if tmp.exists():
            tmp.rmdir()
    assert stable(json.loads(committed.read_text())) == stable(fresh)


def test_summary_shape_and_denominators(tmp_path: Path) -> None:
    summary = evaluate(tmp_path, "inbox.hidden_forward,inbox.n_reply_priya")
    by_id = {c["id"]: c for c in summary["configs"]}
    assert set(by_id) == {"A", "B", "D", "C", "C+"}
    a = by_id["A"]
    assert a["attacks"]["total"] == 3 and a["normal_done"]["total"] == 3
    assert 0 <= a["attacks"]["ci"][0] <= a["attacks"]["rate"] <= a["attacks"]["ci"][1] <= 1
    case = summary["cases"]["inbox.hidden_forward"]
    assert case["configs"]["A"]["runs"] == 3 and len(case["configs"]["A"]["trials"]) == 3
    assert set(case["coverage"]) == {
        "hidden_text",
        "rules",
        "classifier",
        "judge",
        "tool_guard",
        "output_guard",
    }
    assert any("statement" in c["text"] for c in summary["caveats"])


def test_eval_api_serves_the_summary(tmp_path: Path) -> None:
    from seculayer_demo.server.app import create_app
    from tests.integration.test_server import make_settings

    settings = make_settings(tmp_path)
    client = TestClient(create_app(settings, dist_dir=tmp_path / "no-dist", warm=False))
    assert client.get("/api/eval/latest").status_code == 404
    (settings.data_dir / "eval").mkdir(parents=True)
    (settings.data_dir / "eval" / "latest.json").write_text('{"schema_version": 1}')
    assert client.get("/api/eval/latest").json() == {"schema_version": 1}


def test_live_mode_needs_record() -> None:
    result = CliRunner().invoke(app, ["eval", "--mode", "live"])
    assert result.exit_code == 2
