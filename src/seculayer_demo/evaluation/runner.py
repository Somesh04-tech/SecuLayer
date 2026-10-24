"""Replay the recorded matrix into per-run records (docs/PLAN.md §7.2–7.4).

Configurations A–D and C+ replay their recordings. One extra pass, A-observe, replays A's runs
with SecuLayer in observe-only mode: every layer computes its verdict while nothing changes, so
the model requests are exactly A's. That pass gives the per-layer catch rates without new model
calls. A judge call that A's path reaches but no recorded configuration made (for example on a
sent email's tool result) can't be replayed; the judge then counts as unavailable for that
step, and the record says so.
"""

from __future__ import annotations

import fnmatch
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from seculayer.types import InjectionClassifier, LayerSwitches
from seculayer_demo.config import Settings
from seculayer_demo.gateway import ModelGateway, ModelResult, RecordingStore, ReplayMiss
from seculayer_demo.recording_batch import Config, configs
from seculayer_demo.runner import AgentRunner, ConfirmPolicy, RunRequest, readable
from seculayer_demo.scenarios import Case, all_cases, find_case

EVAL_CONFIGS = ("A", "B", "C", "D", "C+")
OBSERVE = "A-observe"
TRIALS = {"A": 3, "B": 3, "C": 1, "D": 3, "C+": 1, OBSERVE: 3}
RecordRow = dict[str, Any]


class ObserveGateway(ModelGateway):
    """Replay, but a judge call that was never recorded makes the judge unavailable for that
    step instead of failing the run (observe-only pass only)."""

    def __init__(self, store: RecordingStore) -> None:
        super().__init__("replay", store)
        self.judge_misses = 0

    def call(self, request: Mapping[str, Any], **kwargs: Any) -> ModelResult:
        try:
            return super().call(request, **kwargs)
        except ReplayMiss as error:
            if error.purpose != "judge":
                raise
            self.judge_misses += 1
            # Empty output fails the judge's schema check, so OpenAIJudge reports every item
            # as "judge unavailable" (suspicious): a flag, never an intervention.
            return ModelResult(
                output_text="",
                tool_calls=(),
                usage={"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0},
                latency_ms=0.0,
                recorded=False,
                recorded_at=None,
                trial=int(kwargs.get("trial", 1)),
                trials_available=0,
                cost_usd=0.0,
                model=str(request.get("model", "")),
            )


@dataclass(frozen=True)
class Job:
    case: Case
    config: Config
    trial: int


def cases_for(name: str, cases: list[Case]) -> list[Case]:
    """A and B: all 56 cases. C: the 36 attack cases. D and C+: the 12 primary attacks."""
    if name in ("A", "B"):
        return cases
    if name in ("C", OBSERVE):
        return [c for c in cases if c.is_attack]
    return [c for c in cases if c.is_attack and c.is_primary]


def plan(settings: Settings, names: list[str], patterns: str | None) -> list[Job]:
    cases = all_cases()
    if patterns:
        wanted = [p.strip() for p in patterns.split(",") if p.strip()]
        cases = [c for c in cases if any(fnmatch.fnmatchcase(c.id, p) for p in wanted)]
    table = {
        c.name: c
        for c in configs(
            [n for n in names if n != OBSERVE] or ["A"], settings.model, settings.compare_model
        )
    }
    if OBSERVE in names:
        table[OBSERVE] = Config(OBSERVE, settings.model, True, LayerSwitches(observe_only=True))
    jobs = []
    for name in names:
        for case in cases_for(name, cases):
            for trial in range(1, TRIALS[name] + 1):
                jobs.append(Job(case, table[name], trial))
    return jobs


def _harm(case: Case) -> str:
    return "tool" if any(c.get("type") == "tool_called" for c in case.success) else "reply"


def _run(
    job: Job,
    gateway: ModelGateway,
    settings: Settings,
    classifier: InjectionClassifier | None,
    on_confirm: ConfirmPolicy,
) -> tuple[AgentRunner, list[dict[str, Any]]]:
    runner = AgentRunner(
        RunRequest(
            job.case.id,
            job.config.protected,
            job.config.model,
            job.config.layers,
            job.trial,
            on_confirm,
        ),
        gateway=gateway,
        judge_model=settings.judge_model,
        classifier=classifier,
        run_id=f"eval-{job.config.name}-{job.case.id}-{job.trial}",
    )
    events = [event.model_dump(mode="json") for event in runner.events()]
    return runner, events


def record_for(
    job: Job,
    gateway: ModelGateway,
    settings: Settings,
    classifier: InjectionClassifier | None,
) -> RecordRow:
    case = job.case
    scenario, _ = find_case(case.id)
    misses_before = gateway.judge_misses if isinstance(gateway, ObserveGateway) else 0
    runner, events = _run(job, gateway, settings, classifier, "stop")
    finished = runner.finished
    injected = [readable(t) for t in case.injected_text if t]
    outbound_tools = {name for name, tool in scenario.policy.tools.items() if tool.outbound}

    verdicts: list[dict[str, Any]] = []
    layer_ms: dict[str, float] = {}
    app = {"calls": 0, "input_tokens": 0, "output_tokens": 0, "latency_ms": 0.0}
    last_tool = ""
    for event in events:
        kind = event["type"]
        if kind == "tool.proposed":
            last_tool = event["name"]
        elif kind == "model.response":
            app["calls"] += 1
            app["input_tokens"] += event["usage"]["input_tokens"]
            app["output_tokens"] += event["usage"]["output_tokens"]
            app["latency_ms"] += event["latency_ms"]
        elif kind == "layer.verdict":
            layer_ms[event["layer"]] = layer_ms.get(event["layer"], 0.0) + event["latency_ms"]
            row: dict[str, Any] = {
                "layer": event["layer"],
                "step": event["step"],
                "action": event["action"],
                "findings": [
                    {
                        "detector": f["detector"],
                        "decision": f.get("decision"),
                        "segment_id": f["segment_id"],
                    }
                    for f in event["findings"]
                ],
            }
            if event["layer"] == "hidden_text" and event["action"] == "removed":
                row["removed_injected"] = any(
                    len(f["excerpt"]) > 8
                    and any(n in f["excerpt"] or f["excerpt"] in n for n in injected)
                    for f in event["findings"]
                )
            if event["layer"] == "tool_guard":
                row["outbound"] = last_tool in outbound_tools
            verdicts.append(row)

    judge_calls = runner.judge.calls if runner.judge else []
    judge = {
        "calls": sum(1 for c in judge_calls if c.recorded),
        "input_tokens": sum(c.usage.get("input_tokens", 0) for c in judge_calls),
        "output_tokens": sum(c.usage.get("output_tokens", 0) for c in judge_calls),
        "latency_ms": round(sum(c.latency_ms for c in judge_calls), 1),
    }
    app["latency_ms"] = round(app["latency_ms"], 1)

    record: RecordRow = {
        "case_id": case.id,
        "scenario": case.scenario_id,
        "kind": case.kind,
        "variant_of": case.variant_of,
        "config": job.config.name,
        "model": job.config.model,
        "protected": job.config.protected,
        "trial": job.trial,
        "outcome": finished.outcome if finished else "error",
        "stopped_by": finished.stopped_by if finished else None,
        "success": finished.checks.success.passed if finished and finished.checks.success else None,
        "utility": finished.checks.utility.passed if finished and finished.checks.utility else None,
        "success_if_approved": None,
        "harm": _harm(case) if case.is_attack else None,
        "verdicts": verdicts,
        "app": app,
        "judge": judge,
        "cost_usd": finished.cost_usd if finished else 0.0,
        "error": next((e["message"] for e in events if e["type"] == "run.error"), None),
        "judge_unrecorded": (
            gateway.judge_misses - misses_before if isinstance(gateway, ObserveGateway) else 0
        ),
        "layer_ms": {k: round(v, 3) for k, v in layer_ms.items()},
    }
    if finished is not None and finished.outcome == "paused":
        approved, _ = _run(job, gateway, settings, classifier, "approve")
        result = approved.finished
        record["success_if_approved"] = bool(
            result and result.checks.success and result.checks.success.passed
        )
    return record


def evaluate(
    settings: Settings,
    classifier: InjectionClassifier | None,
    *,
    names: list[str] | None = None,
    patterns: str | None = None,
    log: Callable[[str], None] = lambda _line: None,
) -> list[RecordRow]:
    """Every run record, in a stable order (configuration, case, trial)."""
    names = names or [*EVAL_CONFIGS, OBSERVE]
    store = RecordingStore(settings.recordings_dir)
    replay = ModelGateway("replay", store)
    observe = ObserveGateway(store)
    records = []
    jobs = plan(settings, names, patterns)
    for job in jobs:
        gateway = observe if job.config.name == OBSERVE else replay
        records.append(record_for(job, gateway, settings, classifier))
    errors = [r for r in records if r["outcome"] == "error"]
    log(
        f"{len(records)} runs replayed; {len(errors)} errors; "
        f"{observe.judge_misses} observe-only judge steps unrecorded."
    )
    return records
