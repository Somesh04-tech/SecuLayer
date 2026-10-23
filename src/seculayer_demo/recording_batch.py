"""`seculayer record`: fill in missing recordings for cases and configurations
(docs/PLAN.md §6.8, §7.2). Only keys that aren't recorded yet call the model, so a batch that
stops at a usage limit resumes where it left off.
"""

from __future__ import annotations

import fnmatch
import itertools
from collections.abc import Callable, Iterator
from dataclasses import dataclass, replace

from seculayer.types import LayerSwitches
from seculayer_demo.gateway import ModelGateway
from seculayer_demo.runner import AgentRunner, RunRequest
from seculayer_demo.scenarios import Case, all_cases

TOKENS_PER_CALL = 1_700  # about 1,500 input and 200 output tokens (docs/PLAN.md §7.2)
CALLS_PER_RUN = {"support": 2, "inbox": 5, "page": 2, "helpdesk": 2}  # app calls plus judge


@dataclass(frozen=True)
class Config:
    name: str
    model: str
    protected: bool
    layers: LayerSwitches


def configs(names: list[str], target: str, compare: str) -> list[Config]:
    table = {
        "A": Config("A", target, False, LayerSwitches.all_off()),
        "B": Config("B", target, True, LayerSwitches()),
        "C": Config("C", compare, False, LayerSwitches.all_off()),
        "D": Config(
            "D",
            target,
            True,
            LayerSwitches(
                hidden_text=False,
                screening=False,
                rules=False,
                classifier=False,
                judge=False,
                tool_guard=False,
                output_guard=False,
            ),
        ),
        "C+": Config("C+", compare, True, LayerSwitches()),
    }
    unknown = [n for n in names if n not in table and n != "combos"]
    if unknown:
        raise ValueError(f"unknown configurations: {', '.join(unknown)} (A, B, C, D, C+, combos)")
    return [table[n] for n in names if n in table]


def layer_combinations() -> Iterator[LayerSwitches]:
    """Every combination of the eight switches (the Layers menu)."""
    names = (
        "hidden_text",
        "screening",
        "rules",
        "classifier",
        "judge",
        "hardening",
        "tool_guard",
        "output_guard",
    )
    for values in itertools.product((True, False), repeat=len(names)):
        yield LayerSwitches(**dict(zip(names, values, strict=True)))


def select_cases(patterns: str) -> list[Case]:
    wanted = [p.strip() for p in patterns.split(",") if p.strip()]
    cases = [c for c in all_cases() if any(fnmatch.fnmatchcase(c.id, p) for p in wanted)]
    if not cases:
        raise ValueError(f"no cases match {patterns!r}")
    return cases


@dataclass(frozen=True)
class Job:
    case: Case
    config: Config
    trial: int


def companion(config: Config) -> Config | None:
    """The same configuration with the tool guard off.

    Layers that only decide never change a model request, but a blocked call ends the run, so
    the requests after it are never made. Recording this companion run too lets the Layers menu
    switch the tool guard off offline.
    """
    if not config.protected or not config.layers.tool_guard:
        return None
    return Config(config.name + "~", config.model, True, replace(config.layers, tool_guard=False))


def plan_jobs(
    cases: list[Case], chosen: list[Config], trials: int, *, combos: bool, target: str
) -> list[Job]:
    jobs = []
    for cfg in chosen:
        for case in cases:
            for trial in range(1, trials + 1):
                jobs.append(Job(case, cfg, trial))
                extra = companion(cfg)
                if extra is not None and case.scenario_id == "inbox":
                    jobs.append(Job(case, extra, trial))
    if combos:
        for case in cases:
            for layers in layer_combinations():
                jobs.append(Job(case, Config("combo", target, True, layers), 1))
    return jobs


def estimate_tokens(jobs: list[Job], *, combos_variants: int = 12) -> int:
    """An upper-bound estimate. Layer combinations share most requests, so they are counted
    as about a dozen distinct variants per case rather than 256 runs."""
    plain = [j for j in jobs if j.config.name != "combo"]
    combo_cases = {j.case.id: j.case for j in jobs if j.config.name == "combo"}
    calls = sum(CALLS_PER_RUN[j.case.scenario_id] for j in plain)
    calls += sum(CALLS_PER_RUN[c.scenario_id] * combos_variants for c in combo_cases.values())
    return calls * TOKENS_PER_CALL


def run_jobs(
    jobs: list[Job],
    gateway: ModelGateway,
    *,
    judge_model: str,
    classifier: object,
    log: Callable[[str], None],
) -> dict[str, int]:
    """Run every job in record mode. Paused runs are approved, so the continuation is recorded
    too (declining needs no further model calls)."""
    counts: dict[str, int] = {}
    before = gateway.live_calls
    for index, job in enumerate(jobs, 1):
        runner = AgentRunner(
            RunRequest(
                job.case.id,
                job.config.protected,
                job.config.model,
                job.config.layers,
                job.trial,
                on_confirm="approve",
            ),
            gateway=gateway,
            judge_model=judge_model,
            classifier=classifier,  # type: ignore[arg-type]
            run_id=f"record-{index}",
        )
        for _event in runner.events():
            pass
        outcome = runner.finished.outcome if runner.finished else "error"
        counts[outcome] = counts.get(outcome, 0) + 1
        if job.config.name != "combo" or outcome == "error":
            log(f"  {job.config.name:<5} {job.case.id:<40} trial {job.trial}: {outcome}")
        if outcome == "error" and runner.finished is not None:
            log(f"        {runner.finished.banner.sentence}")
    counts["live_calls"] = gateway.live_calls - before
    return counts
