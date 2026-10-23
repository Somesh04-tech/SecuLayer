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


def test_cli_doctor_online_needs_a_key() -> None:
    result = CliRunner().invoke(app, ["doctor", "--online"])
    assert result.exit_code == 2
    assert "needs OPENAI_API_KEY" in result.output


def test_online_checks_cover_function_calling_and_structured_output() -> None:
    from seculayer_demo.config import Settings
    from seculayer_demo.doctor import online_checks
    from seculayer_demo.gateway import FakeModel, FakeReply
    from seculayer_demo.gateway.fake import is_judge_request, judge_reply

    def script(request):  # type: ignore[no-untyped-def]
        if is_judge_request(request):
            return judge_reply(request, lambda _body: "benign")
        return FakeReply(tool_calls=[("ping", {"word": "pong"})])

    fake = FakeModel(script)
    checks = list(online_checks(Settings(_env_file=None), fake))  # type: ignore[call-arg]
    assert [(c.name, c.status) for c in checks] == [
        ("Target model", "ok"),
        ("Compare model", "ok"),
        ("Judge model", "ok"),
    ]
    assert [r["model"] for r in fake.requests] == [
        "gpt-5.4-mini-2026-03-17",
        "gpt-5.4-2026-03-05",
        "gpt-5.4-mini-2026-03-17",
    ]
    assert all(r["store"] is False for r in fake.requests)


def test_cli_serve_refuses_non_loopback() -> None:
    result = CliRunner().invoke(app, ["serve", "--host", "0.0.0.0"])
    assert result.exit_code == 2
    assert "loopback" in result.output


def test_cli_serve_live_needs_key() -> None:
    result = CliRunner().invoke(app, ["serve", "--mode", "live"])
    assert result.exit_code == 2
    assert "OpenAI key" in result.output
