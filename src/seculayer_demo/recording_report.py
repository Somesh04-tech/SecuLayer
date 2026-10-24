"""A reproducible, offline M6 inventory of recorded outcomes, before M7's evaluation metrics."""

from __future__ import annotations

from typing import Any

from seculayer_demo.config import Settings
from seculayer_demo.gateway import ModelGateway, RecordingStore
from seculayer_demo.recording_batch import configs, plan_jobs
from seculayer_demo.runner import AgentRunner, RunRequest
from seculayer_demo.scenarios import all_cases
from seculayer_demo.server.runs import make_classifier


def recording_report(settings: Settings) -> dict[str, Any]:
    cases = all_cases()
    primary = [c for c in cases if c.kind == "attack" and c.variant_of is None]
    attacks = [c for c in cases if c.kind == "attack"]
    configurations = configs(["A", "B", "C", "D", "C+"], settings.model, settings.compare_model)
    gateway = ModelGateway("replay", RecordingStore(settings.recordings_dir))
    classifier = make_classifier(settings)
    rows: dict[str, dict[str, Any]] = {}
    for config in configurations:
        selected = (
            cases if config.name in ("A", "B") else attacks if config.name == "C" else primary
        )
        trials = 3 if config.name in ("A", "B", "D") else 1
        jobs = plan_jobs(selected, [config], trials, combos=False, target=settings.model)
        for job in jobs:
            if job.config.name.endswith("~"):
                continue
            request = RunRequest(
                job.case.id, config.protected, config.model, config.layers, job.trial, "stop"
            )
            runner = AgentRunner(
                request,
                gateway=gateway,
                judge_model=settings.judge_model,
                classifier=classifier,
                run_id="inventory",
            )
            for _ in runner.events():
                pass
            result = runner.finished
            row: dict[str, Any] = {
                "trial": job.trial,
                "outcome": result.outcome if result else "error",
                "stopped_by": result.stopped_by if result else None,
                "sentence": result.banner.sentence if result else "No result",
            }
            if result is not None and result.outcome == "paused":
                approved = AgentRunner(
                    RunRequest(
                        job.case.id,
                        config.protected,
                        config.model,
                        config.layers,
                        job.trial,
                        "approve",
                    ),
                    gateway=gateway,
                    judge_model=settings.judge_model,
                    classifier=classifier,
                    run_id="inventory-approved",
                )
                for _ in approved.events():
                    pass
                row["if_approved"] = approved.finished.outcome if approved.finished else "error"
            case_rows = rows.setdefault(job.case.id, {})
            case_rows.setdefault(config.name, []).append(row)
    return {"models": {"target": settings.model, "compare": settings.compare_model}, "cases": rows}
