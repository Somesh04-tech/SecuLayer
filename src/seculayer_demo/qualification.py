"""Configuration A only: three independent live trials and a payload/outcome audit.

No SecuLayer checks are run here, so qualification cannot guide tuning against the defense.
The audit contains outcomes and hashes, not API requests or responses; live saves no recordings.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime

from seculayer.types import LayerSwitches
from seculayer_demo.config import Settings
from seculayer_demo.gateway import BudgetExceeded, ModelGateway, RecordingStore, TokenBudget
from seculayer_demo.gateway.openai_client import OpenAITransport
from seculayer_demo.recording_batch import configs, estimate_by_model, plan_jobs, select_cases
from seculayer_demo.runner import AgentRunner, RunRequest
from seculayer_demo.scenarios import Case

FROZEN = {"inbox.hidden_forward", "support.override"}


def payload_hash(case: Case) -> str:
    payload = {
        "user_request": case.user_request,
        "email": case.extra_email.body if case.extra_email else None,
        "page": case.page.html if case.page else None,
        "articles": [a.body for a in case.articles],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def qualify_cases(
    settings: Settings, patterns: str, round_name: str, log: Callable[[str], None]
) -> None:
    cases = select_cases(patterns)
    if any(c.kind != "attack" or c.id in FROZEN for c in cases):
        raise ValueError("Select attacks only, excluding the two already-qualified featured cases.")
    jobs = plan_jobs(
        cases,
        configs(["A"], settings.model, settings.compare_model),
        3,
        combos=False,
        target=settings.model,
    )
    audit = settings.data_dir / "qualification.jsonl"
    completed = (
        {
            (row["case_id"], row["round"], row["payload_sha256"], row["trial"])
            for row in (json.loads(line) for line in audit.read_text().splitlines())
            if row["outcome"] != "error"
        }
        if audit.is_file()
        else set()
    )
    hashes = {case.id: payload_hash(case) for case in cases}
    jobs = [
        job
        for job in jobs
        if (job.case.id, round_name, hashes[job.case.id], job.trial) not in completed
    ]
    budget = TokenBudget(settings.token_budget, settings.spend_log)
    log(f"Qualification {round_name}: {len(cases)} cases x 3 live configuration-A trials.")
    try:
        estimates = estimate_by_model(jobs, settings.judge_model)
        estimates.setdefault(settings.compare_model, (0, 0))
        budget.preflight(estimates, log)
    except BudgetExceeded as error:
        raise RuntimeError(str(error)) from None
    if not settings.has_api_key:
        raise ValueError("Qualification needs OPENAI_API_KEY in .env.")
    gateway = ModelGateway(
        "live",
        RecordingStore(settings.recordings_dir),
        budget=budget,
        transport=OpenAITransport(settings.openai_api_key.get_secret_value()),
    )
    try:
        for case in cases:
            digest = hashes[case.id]
            for trial in range(1, 4):
                if (case.id, round_name, digest, trial) in completed:
                    continue
                runner = AgentRunner(
                    RunRequest(case.id, False, settings.model, LayerSwitches.all_off(), trial),
                    gateway=gateway,
                    judge_model=settings.judge_model,
                    classifier=None,
                    run_id=f"qualify-{trial}",
                )
                calls_before, tokens_before = gateway.live_calls, budget.used
                for _ in runner.events():
                    pass
                result = runner.finished
                entry = {
                    "date": datetime.now(UTC).isoformat(),
                    "case_id": case.id,
                    "round": round_name,
                    "trial": trial,
                    "payload_sha256": digest,
                    "model": settings.model,
                    "config": "A",
                    "outcome": result.outcome if result else "error",
                    "live_calls": gateway.live_calls - calls_before,
                    "tokens": budget.used - tokens_before,
                }
                with audit.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(entry, sort_keys=True) + "\n")
                log(f"  {case.id} trial {trial}: {entry['outcome']} ({entry['tokens']:,} tokens)")
                if result is None or result.outcome == "error":
                    raise RuntimeError(result.banner.sentence if result else "Run failed")
    finally:
        written = budget.flush(label=f"qualify {patterns} {round_name} x3")
        log(f"{written:,} tokens logged to data/spend.jsonl.")
