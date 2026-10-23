"""`seculayer doctor` prints a readable report and never shows the key."""

from __future__ import annotations

from typer.testing import CliRunner

from seculayer_demo.cli import app
from seculayer_demo.config import Settings
from seculayer_demo.doctor import format_report, run_checks


def test_report_covers_the_planned_checks() -> None:
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    names = {check.name for check in run_checks(settings)}
    for expected in (
        "Project path",
        "Internal disk",
        "Cache UV_CACHE_DIR",
        "Cache npm_config_cache",
        "Cache PLAYWRIGHT_BROWSERS_PATH",
        "uv",
        "node",
        "Port",
        "OpenAI key",
        "Classifier",
        "Recordings",
        "Token budget",
    ):
        assert expected in names


def test_key_shown_only_as_set() -> None:
    key = "sk-test-not-a-real-key-0123456789"
    settings = Settings(_env_file=None, OPENAI_API_KEY=key)  # type: ignore[call-arg]
    report = format_report(list(run_checks(settings)))
    assert key not in report
    assert "OpenAI key" in report


def test_cli_doctor_runs() -> None:
    result = CliRunner().invoke(app, ["doctor"])
    assert "SecuLayer doctor" in result.output
    assert result.exit_code in (0, 1)


def test_cli_doctor_online_not_implemented_yet() -> None:
    result = CliRunner().invoke(app, ["doctor", "--online"])
    assert result.exit_code == 1
    assert "not implemented yet (M3)" in result.output


def test_cli_serve_refuses_non_loopback() -> None:
    result = CliRunner().invoke(app, ["serve", "--host", "0.0.0.0"])
    assert result.exit_code == 2
    assert "loopback" in result.output


def test_cli_serve_live_needs_key() -> None:
    result = CliRunner().invoke(app, ["serve", "--mode", "live"])
    assert result.exit_code == 2
    assert "OpenAI key" in result.output
