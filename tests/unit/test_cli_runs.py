"""The screen, run, record and export-openapi commands."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from seculayer_demo.cli import app
from seculayer_demo.console import parse_layers
from seculayer_demo.recording_batch import configs, estimate_tokens, plan_jobs, select_cases


def test_screen_shows_the_cleaner_and_screening() -> None:
    result = CliRunner().invoke(app, ["screen", "--case", "inbox.hidden_forward"])
    assert result.exit_code == 0, result.output
    assert "removed   Removed 1 hidden paragraph" in result.output
    off = CliRunner().invoke(
        app, ["screen", "--case", "inbox.hidden_forward", "--layers=-hidden_text"]
    )
    assert "withheld  Withheld “Shipment update”" in off.output


def test_run_without_recordings_reports_not_recorded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from seculayer_demo.config import Settings

    monkeypatch.setattr(Settings, "recordings_dir", property(lambda self: tmp_path))
    result = CliRunner().invoke(app, ["run", "--case", "support.n_returns", "--mode", "replay"])
    assert result.exit_code == 1
    assert "wasn't recorded" in result.output


def test_run_and_record_need_a_key_for_live_calls() -> None:
    assert (
        CliRunner().invoke(app, ["run", "--case", "support.n_returns", "--mode", "live"]).exit_code
        == 2
    )
    result = CliRunner().invoke(app, ["record", "--cases", "support.override", "--yes"])
    assert result.exit_code == 2 and "needs OPENAI_API_KEY" in result.output


def test_record_refuses_a_batch_over_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECULAYER_TOKEN_BUDGET", "1000")
    result = CliRunner().invoke(app, ["record", "--cases", "inbox.*", "--configs", "A,B"])
    assert result.exit_code == 1 and "exceeds the remaining budget" in result.output


def test_layer_specs() -> None:
    assert parse_layers("all") == parse_layers("")
    assert not parse_layers("none").tool_guard
    only = parse_layers("tool_guard")
    assert only.tool_guard and not only.hidden_text and not only.screening
    minus = parse_layers("-hidden_text,-screening")
    assert minus.tool_guard and not minus.hidden_text and not minus.screening
    with pytest.raises(ValueError):
        parse_layers("bogus")


def test_record_planning() -> None:
    cases = select_cases("inbox.hidden_forward,support.override")
    chosen = configs(["A", "B"], "mini", "full")
    jobs = plan_jobs(cases, chosen, 3, combos=True, target="mini")
    # A and B for both cases, three trials each, plus the inbox case's tool-guard-off companion.
    assert len([j for j in jobs if j.config.name != "combo"]) == 15
    assert {j.config.name for j in jobs if j.case.id == "inbox.hidden_forward"} >= {"B~"}
    assert len([j for j in jobs if j.config.name == "combo"]) == 2 * 256
    assert estimate_tokens(jobs) > 0
    with pytest.raises(ValueError):
        configs(["Z"], "mini", "full")


def test_export_openapi(tmp_path: Path) -> None:
    target = tmp_path / "openapi.json"
    result = CliRunner().invoke(app, ["export-openapi", str(target)])
    assert result.exit_code == 0, result.output
    assert "RunFinished" in json.loads(target.read_text())["components"]["schemas"]
