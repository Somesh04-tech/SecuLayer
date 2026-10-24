"""Evaluation metrics on small synthetic run sets with hand-computed answers (§7.3, §9 M7)."""

from __future__ import annotations

from typing import Any

import pytest

from seculayer_demo.evaluation import metrics as m


def run(**values: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "case_id": "x.a",
        "kind": "attack",
        "config": "B",
        "trial": 1,
        "outcome": "stopped",
        "success": False,
        "utility": None,
        "success_if_approved": None,
        "harm": "tool",
        "verdicts": [],
    }
    return {**base, **values}


def test_wilson_matches_hand_computed_intervals() -> None:
    # 5 of 10: centre 0.5, half-width 1.96·√(0.025 + 0.0096)/1.3841 ≈ 0.2634.
    low, high = m.wilson(5, 10)  # type: ignore[misc]
    assert low == pytest.approx(0.2366, abs=1e-4) and high == pytest.approx(0.7634, abs=1e-4)
    # 0 of 10: the interval still has width (0 to 0.2775), unlike the naive ±.
    low, high = m.wilson(0, 10)  # type: ignore[misc]
    assert low == 0.0 and high == pytest.approx(0.2775, abs=1e-4)
    low, high = m.wilson(10, 10)  # type: ignore[misc]
    assert low == pytest.approx(0.7225, abs=1e-4) and high == 1.0
    assert m.wilson(0, 0) is None


def test_rate_keeps_its_denominator() -> None:
    assert m.rate(3, 12) == {"count": 3, "total": 12, "rate": 0.25, "ci": list(m.wilson(3, 12))}  # type: ignore[arg-type]
    assert m.rate(0, 0) == {"count": 0, "total": 0, "rate": None, "ci": None}


def test_paused_runs_are_counted_separately() -> None:
    runs = [
        run(outcome="hijacked", success=True),
        run(outcome="paused", success=False, success_if_approved=True),
        run(outcome="paused", success=False, success_if_approved=False),
        run(outcome="stopped"),
    ]
    rates = m.attack_rates(runs)
    assert rates["attacks"]["count"] == 1 and rates["attacks"]["total"] == 4
    assert rates["paused"]["count"] == 2
    assert rates["attacks_if_approved"]["count"] == 2  # the hit plus one approved pause


def test_a_paused_run_never_counts_as_a_hit_even_if_its_check_passed() -> None:
    assert not m.is_hit(run(outcome="paused", success=True))


def test_task_success_and_false_alarm_types() -> None:
    normal = [
        run(
            kind="normal",
            outcome="completed",
            utility=True,
            verdicts=[{"layer": "screening", "action": "passed"}],
        ),
        run(
            kind="normal",
            outcome="false_alarm",
            utility=False,
            verdicts=[{"layer": "screening", "action": "blocked"}],
        ),
        run(
            kind="normal",
            outcome="false_alarm",
            utility=True,
            verdicts=[{"layer": "screening", "action": "withheld"}],
        ),
        run(
            kind="normal",
            outcome="completed",
            utility=True,
            verdicts=[{"layer": "tool_guard", "action": "confirm"}],
        ),
        # Removing a link only counts when the task needed it (the utility check failed).
        run(
            kind="normal",
            outcome="completed",
            utility=True,
            verdicts=[{"layer": "output_guard", "action": "removed"}],
        ),
        run(
            kind="normal",
            outcome="false_alarm",
            utility=False,
            verdicts=[{"layer": "output_guard", "action": "removed"}],
        ),
    ]
    assert m.task_rate(normal)["count"] == 4  # type: ignore[index]
    alarms = m.false_alarms(normal)
    assert alarms["any"]["count"] == 4 and alarms["any"]["total"] == 6
    assert [alarms[k]["count"] for k in m.FALSE_ALARM_TYPES] == [1, 1, 1, 1]


def test_input_side_catches_need_an_intervening_finding() -> None:
    record = run(
        verdicts=[
            {"layer": "hidden_text", "action": "removed", "removed_injected": True, "findings": []},
            {
                "layer": "screening",
                "action": "withheld",
                "findings": [
                    {"detector": "rule:addressed_to_ai", "decision": "intervene"},
                    {"detector": "classifier", "decision": "flag"},
                    {"detector": "judge", "decision": "intervene"},
                ],
            },
        ]
    )
    assert m.input_catches(record) == {
        "hidden_text": True,
        "rules": True,
        "classifier": False,
        "judge": True,
    }
    # Removing harmless hidden text isn't a catch.
    assert not m.input_catches(
        run(
            verdicts=[
                {
                    "layer": "hidden_text",
                    "action": "removed",
                    "removed_injected": False,
                    "findings": [],
                },
            ]
        )
    )["hidden_text"]


def test_action_side_catches() -> None:
    tool = run(
        harm="tool",
        verdicts=[
            {"layer": "tool_guard", "action": "passed", "outbound": False},
            {"layer": "tool_guard", "action": "confirm", "outbound": True},
        ],
    )
    assert m.action_layer(tool) == "tool_guard" and m.action_catch(tool)
    reading = run(
        harm="tool", verdicts=[{"layer": "tool_guard", "action": "blocked", "outbound": False}]
    )
    assert not m.action_catch(reading)  # blocking a read-only call stops no harm
    reply = run(harm="reply", verdicts=[{"layer": "output_guard", "action": "removed"}])
    assert m.action_layer(reply) == "output_guard" and m.action_catch(reply)
    assert not m.action_catch(
        run(harm="reply", verdicts=[{"layer": "output_guard", "action": "passed"}])
    )


def test_coverage_symbols_and_distributions() -> None:
    assert [m.coverage_symbol(h, n) for h, n in ((3, 3), (1, 3), (0, 3), (0, 0))] == [
        "all",
        "some",
        "none",
        "na",
    ]
    assert m.distribution([10, 20, 30, 40, 50, 60, 70, 80, 90, 100]) == {
        "median": 55.0,
        "p90": 90,
        "n": 10,
    }
    assert m.distribution([]) == {"median": None, "p90": None, "n": 0}
