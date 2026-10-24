"""Offline matrix coverage and unreachable-recording audit (PLAN §6.8). No transport exists."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from seculayer_demo.config import Settings
from seculayer_demo.gateway import ModelGateway, RecordingStore, ReplayMiss
from seculayer_demo.recording_batch import configs, plan_jobs, select_cases
from seculayer_demo.runner import AgentRunner, RunRequest
from seculayer_demo.server.runs import make_classifier


class AuditGateway(ModelGateway):
    def __init__(self, store: RecordingStore) -> None:
        super().__init__("replay", store)
        self.strict = True
        self.used: set[tuple[str, int]] = set()
        self.missing: set[tuple[str, int, str]] = set()

    def _lookup(self, key: str, trial: int) -> Any:
        if self.strict:
            recording = self.store.get(key, trial)
            result = (recording, trial) if recording else None
        else:
            result = super()._lookup(key, trial)
        if result is not None:
            self.used.add((key, result[1]))
        return result

    def call(self, request: Mapping[str, Any], **kwargs: Any) -> Any:
        try:
            return super().call(request, **kwargs)
        except ReplayMiss as error:
            self.missing.add((error.key, error.trial, error.purpose))
            raise


def replay_check(
    settings: Settings,
    patterns: str,
    model: str | None,
    trials: int,
    log: Callable[[str], None],
) -> int:
    selected = select_cases(patterns)
    primary = [c for c in selected if c.kind == "attack" and c.variant_of is None]
    chosen_model = model or settings.model
    compare = chosen_model == settings.compare_model
    if compare:
        attacks = [c for c in selected if c.kind == "attack"]
        jobs = plan_jobs(
            attacks,
            configs(["C"], settings.model, chosen_model),
            1,
            combos=False,
            target=settings.model,
        )
        jobs += plan_jobs(
            primary,
            configs(["C+"], settings.model, chosen_model),
            1,
            combos=False,
            target=settings.model,
        )
    else:
        jobs = plan_jobs(
            selected,
            configs(["A", "B"], chosen_model, settings.compare_model),
            trials,
            combos=False,
            target=chosen_model,
        )
        jobs += plan_jobs(
            primary,
            configs(["D"], chosen_model, settings.compare_model),
            trials,
            combos=True,
            target=chosen_model,
        )
    store = RecordingStore(settings.recordings_dir)
    gateway = AuditGateway(store)
    classifier = make_classifier(settings)
    errors = 0
    for index, job in enumerate(jobs, 1):
        gateway.strict = job.config.name != "combo"
        before = len(gateway.missing)
        runner = AgentRunner(
            RunRequest(
                job.case.id,
                job.config.protected,
                job.config.model,
                job.config.layers,
                job.trial,
                "approve",
            ),
            gateway=gateway,
            judge_model=settings.judge_model,
            classifier=classifier,
            run_id=f"audit-{index}",
        )
        for _ in runner.events():
            pass
        if runner.finished is None or runner.finished.outcome == "error":
            errors += 1
            if len(gateway.missing) != before:
                log(f"Missing: {job.case.id} {job.config.name} trial {job.trial}")
    for key, trial, purpose in sorted(gateway.missing):
        log(f"  {purpose} {key} trial {trial}")
    log(
        f"{chosen_model}: {len(jobs):,} runs checked; "
        f"{len(gateway.missing)} missing recording keys; {errors} incomplete runs."
    )
    unused = [
        r
        for r in store.entries()
        if r.model == chosen_model and (r.key, r.trial) not in gateway.used
    ]
    log(
        f"{len(unused)} unreferenced recordings (may include other models' judge calls, "
        "other cases, or unreachable continuations; none deleted)."
    )
    for recording in unused:
        log(
            f"  Unreferenced {recording.purpose}: {recording.case_id} {recording.key} "
            f"trial {recording.trial}"
        )
    return len(gateway.missing) + errors
