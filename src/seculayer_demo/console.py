"""Compact text output for the command line: run events and screening reports."""

from __future__ import annotations

import textwrap
from collections.abc import Iterable

from pydantic import BaseModel

from seculayer.engine import SecuLayer
from seculayer.types import InjectionClassifier, Inspection, LayerSwitches, ToolCall
from seculayer_demo.apps import make_app
from seculayer_demo.scenarios import find_case

LAYER_NAMES = (
    "hidden_text",
    "screening",
    "rules",
    "classifier",
    "judge",
    "hardening",
    "tool_guard",
    "output_guard",
)


def parse_layers(spec: str) -> LayerSwitches:
    """ "all", "none", a list of layers to keep on ("tool_guard,output_guard"), or layers to
    switch off ("-hidden_text,-screening")."""
    spec = spec.strip()
    if spec in ("", "all"):
        return LayerSwitches()
    if spec == "none":
        return LayerSwitches.all_off()
    names = [n.strip() for n in spec.split(",") if n.strip()]
    bad = [n for n in names if n.lstrip("-") not in LAYER_NAMES]
    if bad:
        raise ValueError(f"unknown layers: {', '.join(bad)} (known: {', '.join(LAYER_NAMES)})")
    if all(n.startswith("-") for n in names):
        return LayerSwitches(**{n[1:]: False for n in names})
    if any(n.startswith("-") for n in names):
        raise ValueError("list the layers to keep on, or the layers to switch off, not both")
    on = set(names)
    if "screening" in on and not on & {"rules", "classifier", "judge"}:
        on |= {"rules", "classifier", "judge"}
    return LayerSwitches(**{n: n in on for n in LAYER_NAMES})


def _short(text: str, width: int = 96) -> str:
    text = " ".join(text.split())
    return text if len(text) <= width else text[: width - 1] + "…"


def format_event(event: BaseModel) -> list[str]:
    data = event.model_dump(mode="json")
    kind = data["type"]
    if kind == "run.started":
        side = "with SecuLayer" if data["protected"] else "without SecuLayer"
        return [
            f"▶ {data['case_id']} {side} · {data['model']} · {data['mode']} · trial "
            f"{data['trial']} of {data['trials_available']} recorded"
        ]
    if kind == "layer.started":
        return []
    if kind == "layer.verdict":
        lines = [f"  [{data['layer']:<12}] {data['action']:<11} {_short(data['reason'], 120)}"]
        lines += [f"  {'':14}   · {_short(d, 110)}" for d in data["detail"][:6]]
        return lines
    if kind == "model.request":
        shares = ", ".join(f"{k} {v}" for k, v in data["tokens_by_source"].items())
        return [f"  model call {data['call_index'] + 1} (≈ tokens: {shares})"]
    if kind == "model.response":
        calls = ", ".join(
            f"{c['name']}({_short(str(c['arguments']), 70)})" for c in data["tool_calls"]
        )
        source = "recorded " + (data["recorded_at"] or "") if data["recorded"] else "live"
        return [
            f"  ← {calls or _short(data['output_text'], 90)} · {data['latency_ms']:.0f} ms "
            f"· {source}"
        ]
    if kind == "tool.proposed":
        return []
    if kind == "tool.decision":
        return [f"  tool {data['action']}: {_short(data['reason'], 100)}"]
    if kind == "tool.result":
        return [f"  tool result: {data['summary']}"]
    if kind == "run.paused":
        dialog = data["dialog"]
        return [f"  ⏸ paused: send to {', '.join(dialog['to'])}? {dialog['reason']}"]
    if kind == "attacker.event":
        click = "zero-click" if data["zero_click"] else "if clicked"
        return [
            f"  ☠ attacker's server ({data['channel']}, {click}) {data['destination']}: "
            f"{_short(data['data'], 80)}"
        ]
    if kind == "run.error":
        return [f"  ✗ {data['message']}"]
    if kind == "run.finished":
        banner = data["banner"]
        lines = [f"■ {data['outcome']}: {banner['title']}: {banner['sentence']}"]
        reply = data["reply_markdown"].strip()
        if reply:
            lines += ["  reply:"] + ["    " + line for line in textwrap.wrap(reply, 92)[:12]]
        lines.append(f"  cost ${data['cost_usd']:.5f}")
        return lines
    return [f"  {kind}"]


def print_events(events: Iterable[BaseModel], echo: object) -> None:
    for event in events:
        for line in format_event(event):
            echo(line)  # type: ignore[operator]


def screen_case(
    case_id: str, layers: LayerSwitches, classifier: InjectionClassifier | None
) -> list[Inspection]:
    """Layers 1-2 on a case's inputs: the user's message and its outside content.

    No model call: the judge is always off here.
    """
    scenario, case = find_case(case_id)
    app = make_app(scenario, case, seed=case.id)
    guard = SecuLayer(
        scenario.policy,
        layers=LayerSwitches(**{**vars(layers), "judge": False}),
        classifier=classifier,
        seed=case.id,
    )
    ctx = guard.new_context(case.user_request)
    inspections = [guard.inspect(app.build_layout().inspectable_segments(), ctx)]
    if scenario.app == "inbox":
        emails = app.execute_tool(ToolCall("screen", "list_unread_emails", {})).segments
        inspections.append(guard.inspect(emails, ctx))
    return inspections
