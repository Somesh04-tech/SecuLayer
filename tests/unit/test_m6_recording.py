"""Daily quota, qualification isolation and exact offline coverage, with FakeModel only."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from seculayer_demo.gateway import (
    BudgetExceeded,
    FakeModel,
    ModelGateway,
    RecordingStore,
    TokenBudget,
)
from seculayer_demo.qualification import qualify_cases
from seculayer_demo.recording_batch import configs, estimate_by_model, plan_jobs, select_cases
from seculayer_demo.replay_check import replay_check
from seculayer_demo.runner import AgentRunner, RunRequest
from tests.fakes import MODEL, inbox_script
from tests.integration.test_server import make_settings

FULL = "gpt-5.4-2026-03-05"


def test_preflight_reports_each_model_and_rejects_daily_overage(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    settings.spend_log.write_text(
        json.dumps(
            {
                "date": datetime.now(UTC).strftime("%Y-%m-%d"),
                "model": FULL,
                "tokens": 249_000,
            }
        )
        + "\n"
    )
    budget = TokenBudget(1_500_000, settings.spend_log)
    lines: list[str] = []
    with pytest.raises(BudgetExceeded, match="/day"):
        budget.preflight({FULL: (1, 1700), MODEL: (1, 1700)}, lines.append)
    assert any("249,000 today" in line for line in lines)
    assert any(MODEL in line and "1 calls / 1,700" in line for line in lines)


def test_pending_calls_count_toward_daily_limit_and_old_days_do_not(tmp_path: Path) -> None:
    log = tmp_path / "spend.jsonl"
    log.write_text(json.dumps({"date": "2000-01-01", "model": FULL, "tokens": 249_000}) + "\n")
    budget = TokenBudget(1_500_000, log)
    budget.check(2000, FULL)
    budget.add(FULL, 249_000, 0)
    with pytest.raises(BudgetExceeded, match="/day"):
        budget.check(2000, FULL)


def test_compare_model_estimate_accounts_for_mini_judge() -> None:
    jobs = plan_jobs(
        select_cases("page.hidden_link"),
        configs(["C+"], MODEL, FULL),
        1,
        combos=False,
        target=MODEL,
    )
    assert estimate_by_model(jobs, MODEL) == {FULL: (1, 1700), MODEL: (1, 1700)}


def test_qualification_runs_only_configuration_a_and_saves_no_recordings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from seculayer_demo import qualification

    settings = make_settings(tmp_path, OPENAI_API_KEY="test-fixture")
    fake = FakeModel(inbox_script(None, final="Five ordinary emails."))
    monkeypatch.setattr(qualification, "OpenAITransport", lambda _: fake)
    qualify_cases(settings, "inbox.fake_system", "original", lambda _: None)
    audit = [
        json.loads(line)
        for line in (settings.data_dir / "qualification.jsonl").read_text().splitlines()
    ]
    assert len(audit) == 3 and {row["config"] for row in audit} == {"A"}
    assert {row["trial"] for row in audit} == {1, 2, 3}
    assert len(RecordingStore(settings.recordings_dir)) == 0
    assert not any("Security policy" in json.dumps(request) for request in fake.requests)
    assert TokenBudget(1_500_000, settings.spend_log).used > 0
    before = len(fake.requests)
    qualify_cases(settings, "inbox.fake_system", "original", lambda _: None)
    assert len(fake.requests) == before  # resuming never adds a fourth trial


def test_qualification_rejects_frozen_and_normal_cases(tmp_path: Path) -> None:
    for case in ("support.override", "inbox.hidden_forward", "support.n_returns"):
        with pytest.raises(ValueError, match="already-qualified"):
            qualify_cases(make_settings(tmp_path), case, "round-1", lambda _: None)


def test_replay_audit_requires_real_trials_despite_ui_fallback(tmp_path: Path) -> None:
    from seculayer.types import LayerSwitches
    from tests.fakes import reply_script

    settings = make_settings(tmp_path)
    store = RecordingStore(settings.recordings_dir)
    gateway = ModelGateway("record", store, transport=FakeModel(reply_script("30 days")))
    for protected in (False, True):
        layers = LayerSwitches() if protected else LayerSwitches.all_off()
        runner = AgentRunner(
            RunRequest("support.n_returns", protected, MODEL, layers),
            gateway=gateway,
            judge_model=MODEL,
            classifier=None,
            run_id="fixture",
        )
        for _ in runner.events():
            pass
    lines: list[str] = []
    assert replay_check(settings, "support.n_returns", None, 1, lines.append) == 0
    assert replay_check(settings, "support.n_returns", None, 3, lines.append) > 0
    assert any("trial 2" in line for line in lines)
    assert len(store) > 0  # read-only audit leaves the recording store alone


def test_inventory_distinguishes_paused_from_approved_harm(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from seculayer_demo import recording_report as module
    from tests.fakes import email

    settings = make_settings(tmp_path)
    cases = select_cases("inbox.polite_invoice")
    chosen = configs(["A", "B"], MODEL, FULL)
    jobs = plan_jobs(cases, chosen, 3, combos=False, target=MODEL)
    script = inbox_script(email("billing@northwind-payments.example", "Account 4417; statement."))
    gateway = ModelGateway(
        "record", RecordingStore(settings.recordings_dir), transport=FakeModel(script)
    )
    for job in jobs:
        runner = AgentRunner(
            RunRequest(
                job.case.id, job.config.protected, MODEL, job.config.layers, job.trial, "approve"
            ),
            gateway=gateway,
            judge_model=MODEL,
            classifier=None,
            run_id="fixture",
        )
        for _ in runner.events():
            pass
    monkeypatch.setattr(module, "all_cases", lambda: cases)
    monkeypatch.setattr(module, "configs", lambda *_: chosen)
    rows = module.recording_report(settings)["cases"][cases[0].id]
    assert [row["outcome"] for row in rows["A"]] == ["hijacked"] * 3
    assert [row["outcome"] for row in rows["B"]] == ["paused"] * 3
    assert [row["if_approved"] for row in rows["B"]] == ["hijacked"] * 3


def test_transport_errors_never_echo_provider_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    import httpx
    import openai

    from seculayer_demo.gateway.openai_client import ModelError, OpenAITransport

    secret = "sensitive-fixture-value"
    transport = OpenAITransport(secret)

    def reject(**_: object) -> None:
        raise openai.APIStatusError(
            f"Incorrect API key provided: {secret}",
            response=httpx.Response(401, request=httpx.Request("POST", "https://api.openai.com")),
            body=None,
        )

    monkeypatch.setattr(transport._client.responses, "create", reject)
    with pytest.raises(ModelError, match="HTTP 401") as caught:
        transport.create({"model": MODEL})
    assert secret not in str(caught.value)


def test_approved_replacement_changes_one_response_and_keeps_recoverable_backup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import gzip

    from seculayer_demo import recording_repair
    from seculayer_demo.gateway import FakeReply
    from tests.unit.test_gateway import REQUEST

    settings = make_settings(tmp_path, OPENAI_API_KEY="fixture")
    store = RecordingStore(settings.recordings_dir)
    recorder = ModelGateway(
        "record", store, transport=FakeModel([FakeReply(text="old"), FakeReply(text="keep")])
    )
    recorder.call(REQUEST, trial=1, scenario="support", case_id="support.n_returns")
    other_request = {**REQUEST, "input": [{"role": "user", "content": "Another request"}]}
    recorder.call(other_request, trial=1, scenario="support", case_id="support.n_codes")
    old, other = store.entries()
    fake = FakeModel([FakeReply(text="new")])
    monkeypatch.setattr(recording_repair, "OpenAITransport", lambda _: fake)
    recording_repair.replace_recording(
        settings,
        "support.n_returns",
        f"{old.key}:1",
        confirm=lambda _: True,
        log=lambda _: None,
    )
    assert fake.requests == [old.request]  # identical model settings and input
    reloaded = RecordingStore(settings.recordings_dir)
    assert len(reloaded) == 2
    assert reloaded.get(other.key, other.trial) == other
    assert (
        ModelGateway("replay", reloaded).call(REQUEST, trial=1, scenario="support").output_text
        == "new"
    )
    [backup] = list((tmp_path / ".cache" / "recording-backups").glob("*/*.gz"))
    with gzip.open(backup, "rt") as handle:
        assert json.load(handle) == json.loads(old.to_json())
    assert TokenBudget(1_500_000, settings.spend_log).used > 0


def test_replacement_rejects_request_changes_before_writing(tmp_path: Path) -> None:
    from dataclasses import replace

    from seculayer_demo.gateway import FakeReply
    from tests.unit.test_gateway import REQUEST

    store = RecordingStore(tmp_path / "recordings")
    ModelGateway("record", store, transport=FakeModel([FakeReply(text="old")])).call(
        REQUEST,
        trial=1,
        scenario="support",
        case_id="support.n_returns",
    )
    [old] = store.entries()
    with pytest.raises(ValueError, match="identical request"):
        store.replace(
            old, replace(old, request={**old.request, "model": FULL}), backup=tmp_path / "backup.gz"
        )
    assert not (tmp_path / "backup.gz").exists()
    assert RecordingStore(store.root).entries() == (old,)
