"""The SecuLayer class: the five layers behind one interface (docs/PLAN.md §6.5).

An app hands SecuLayer its prompt as labelled segments. Layers 1-2 inspect the user's message
and outside content (`inspect`), layer 3 re-places and marks outside content (`harden`), layer 4
checks each proposed tool call (`review_tool_call`) and layer 5 checks the final reply
(`review_output`). Every layer can be switched off, and every call returns verdicts the UI shows.
"""

from __future__ import annotations

import time
from collections.abc import Sequence

from seculayer.layers import hardening, output_guard, tool_guard
from seculayer.layers.hidden_text import clean_segment, describe_pieces
from seculayer.layers.rules import run_rules
from seculayer.layers.screening import ItemScreen, classifier_score, screen
from seculayer.policy import Policy
from seculayer.text.html import clean_html
from seculayer.text.unicode import strip_invisible
from seculayer.types import (
    Action,
    Finding,
    HiddenPiece,
    InjectionClassifier,
    InjectionJudge,
    Inspection,
    LayerId,
    LayerSwitches,
    OutputReview,
    PromptLayout,
    RunContext,
    Segment,
    Source,
    ToolCall,
    ToolReview,
    Verdict,
    noun_for,
)

OFF_REASON = "Switched off."


def withheld_placeholder(segment: Segment) -> Segment:
    text = f"[Withheld by SecuLayer: this {segment.noun} contained instructions aimed at the AI]"
    return Segment(
        segment.id,
        Source.SECULAYER,
        text,
        "text",
        segment.label,
        segment.private,
        outside_scaffold=True,  # it stands in for outside content, so hardening moves it too
        meta=segment.meta,
    )


def blocked_reply(reason: str) -> str:
    return f"SecuLayer blocked this message: {reason}"


def visible_text(segment: Segment) -> str:
    """What a person would see of an outside segment."""
    text = strip_invisible(segment.text)
    return clean_html(text).text if segment.format == "html" else text


def _ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 2)


class SecuLayer:
    def __init__(
        self,
        policy: Policy,
        *,
        layers: LayerSwitches | None = None,
        classifier: InjectionClassifier | None = None,
        judge: InjectionJudge | None = None,
        seed: str = "",
    ) -> None:
        self.policy = policy
        self.layers = layers or LayerSwitches()
        self.classifier = classifier
        self.judge = judge
        self.seed = seed

    def new_context(self, user_text: str, developer_text: str = "") -> RunContext:
        return RunContext(
            policy=self.policy, user_text=user_text, seed=self.seed, developer_text=developer_text
        )

    # --- Layers 1-2 ------------------------------------------------------------------------

    def inspect(self, segments: Sequence[Segment], ctx: RunContext) -> Inspection:
        switches = self.layers
        observe = switches.observe_only
        for segment in segments:
            if segment.source is Source.EXTERNAL:
                ctx.outside_segments[segment.id] = segment
                ctx.visible_outside[segment.id] = visible_text(segment)
        labels = {s.id: s.label for s in segments}
        outside = [s for s in segments if s.source is Source.EXTERNAL]

        # Layer 1: the hidden-text cleaner.
        start = time.perf_counter()
        hidden: list[HiddenPiece] = []
        current = list(segments)
        if switches.hidden_text:
            cleaned = []
            for segment in segments:
                result = clean_segment(segment)
                hidden += result.hidden
                cleaned.append(result.segment)
            if not observe:
                current = cleaned
            screen_input = cleaned
        else:
            screen_input = list(segments)
        cleaner_verdict = self._cleaner_verdict(outside, hidden, labels, _ms(start))

        # Layer 2: screening.
        start = time.perf_counter()
        withheld: list[str] = []
        blocked = False
        block_reason = ""
        screening_on = switches.screening and (
            switches.rules or switches.classifier or switches.judge
        )
        if not screening_on:
            screening_verdict = Verdict(LayerId.SCREENING, Action.OFF, OFF_REASON)
        else:
            screened = screen(
                screen_input,
                self.policy,
                switches=switches,
                classifier=self.classifier,
                judge=self.judge,
            )
            for item in screened.items:
                if item.decision != "pass" and item.place == "outside":
                    ctx.flagged_segment_ids.add(item.segment_id)
            stopped = [i for i in screened.items if i.decision == "intervene"]
            user_stop = next((i for i in stopped if i.place == "user"), None)
            if user_stop is not None:
                blocked = True
                block_reason = _sentence(f"The message {user_stop.reason.removeprefix('it ')}")
            withheld = [i.segment_id for i in stopped if i.place == "outside"]
            screening_verdict = self._screening_verdict(
                screened.items, labels, user_stop, withheld, _ms(start)
            )
            if withheld and not observe:
                by_id = {s.id: s for s in current}
                current = [
                    withheld_placeholder(by_id[s.id]) if s.id in withheld else s for s in current
                ]

        if observe:
            current = list(segments)
        return Inspection(
            segments=tuple(current),
            hidden=tuple(hidden),
            withheld_ids=() if observe else tuple(withheld),
            blocked=blocked and not observe,
            verdicts=(cleaner_verdict, screening_verdict),
            block_reason=block_reason,
        )

    def _cleaner_verdict(
        self,
        outside: list[Segment],
        hidden: list[HiddenPiece],
        labels: dict[str, str],
        latency: float,
    ) -> Verdict:
        if not self.layers.hidden_text:
            return Verdict(LayerId.HIDDEN_TEXT, Action.OFF, OFF_REASON)
        if not outside:
            return Verdict(
                LayerId.HIDDEN_TEXT,
                Action.PASSED,
                "No outside content to clean.",
                latency_ms=latency,
            )
        if not hidden:
            count = len(outside)
            noun = outside[0].noun + ("s" if count > 1 else "")
            return Verdict(
                LayerId.HIDDEN_TEXT,
                Action.PASSED,
                f"Nothing hidden in {count} {noun}.",
                latency_ms=latency,
            )
        reason = f"Removed {describe_pieces(tuple(hidden), labels)}."
        if any(self._gives_orders(piece.text) for piece in hidden if piece.text.strip()):
            reason += " It gave orders to the AI."
        findings = tuple(
            Finding(
                f"hidden:{piece.kind}",
                piece.segment_id,
                piece.span,
                piece.text[:300],
                None,
                f"Removed: {piece.reason}.",
            )
            for piece in hidden
        )
        detail = tuple(f"{piece.reason}: “{piece.text[:200]}”" for piece in hidden)
        return Verdict(LayerId.HIDDEN_TEXT, Action.REMOVED, reason, findings, latency, detail)

    def _gives_orders(self, text: str) -> bool:
        """Whether screening's rules or classifier flag removed hidden text."""
        if self.layers.rules and run_rules(text, "outside"):
            return True
        if self.layers.classifier and self.classifier is not None:
            score, _ = classifier_score(self.classifier, text)
            return score is not None and score >= self.policy.screening.classifier_flag
        return False

    def _screening_verdict(
        self,
        items: tuple[ItemScreen, ...],
        labels: dict[str, str],
        user_stop: ItemScreen | None,
        withheld: list[str],
        latency: float,
    ) -> Verdict:
        findings = tuple(f for item in items for f in item.findings)
        detail = tuple(
            f"{labels.get(item.segment_id) or item.segment_id}: {item.detail}" for item in items
        )
        if user_stop is not None:
            reason = _sentence(f"Blocked the message: {user_stop.reason}")
            return Verdict(LayerId.SCREENING, Action.BLOCKED, reason, findings, latency, detail)
        if withheld:
            stopped = [i for i in items if i.segment_id in withheld]
            parts = [f"“{labels.get(i.segment_id) or i.segment_id}”: {i.reason}" for i in stopped]
            reason = _sentence("Withheld " + "; ".join(parts))
            return Verdict(LayerId.SCREENING, Action.WITHHELD, reason, findings, latency, detail)
        flagged = [i for i in items if i.decision == "flag"]
        if flagged:
            parts = [f"“{labels.get(i.segment_id) or i.segment_id}”: {i.reason}" for i in flagged]
            reason = _sentence("Passed, with a flag on " + "; ".join(parts))
            return Verdict(LayerId.SCREENING, Action.FLAGGED, reason, findings, latency, detail)
        outside = [i for i in items if i.place == "outside"]
        if outside:
            nouns = {noun_for(i.segment_id) for i in outside}
            noun = nouns.pop() if len(nouns) == 1 else "item"
            noun += "" if len(outside) == 1 else "s"
            reason = f"Visible text in {len(outside)} {noun} looks normal."
        elif items:
            reason = "The message looks normal."
        else:
            reason = "Nothing to screen."
        return Verdict(LayerId.SCREENING, Action.PASSED, reason, findings, latency, detail)

    # --- Layer 3 ---------------------------------------------------------------------------

    def harden(self, layout: PromptLayout, ctx: RunContext) -> tuple[PromptLayout, Verdict]:
        if not self.layers.hardening:
            return layout, Verdict(LayerId.HARDENING, Action.OFF, OFF_REASON)
        start = time.perf_counter()
        hardened, marked = hardening.harden_layout(layout, ctx.seed or self.seed)
        tokens = hardening.approx_tokens(hardening.TRUST_POLICY)
        policy_note = f"added the trust policy (about +{tokens} tokens)"
        if marked:
            nouns = {s.noun for s in layout.segments() if s.source is Source.EXTERNAL}
            noun = nouns.pop() if len(nouns) == 1 else "item"
            noun += "s" if marked > 1 else ""
            reason = f"Marked {marked} {noun} as outside content; {policy_note}."
        else:
            reason = f"No outside content to mark; {policy_note}."
        if self.layers.observe_only:
            return layout, Verdict(LayerId.HARDENING, Action.APPLIED, reason, latency_ms=_ms(start))
        return hardened, Verdict(LayerId.HARDENING, Action.APPLIED, reason, latency_ms=_ms(start))

    # --- Layer 4 ---------------------------------------------------------------------------

    def review_tool_call(self, call: ToolCall, ctx: RunContext) -> ToolReview:
        if not self.layers.tool_guard:
            return ToolReview("allow", Verdict(LayerId.TOOL_GUARD, Action.OFF, OFF_REASON))
        start = time.perf_counter()
        outcome = tool_guard.review(call, ctx)
        verdict = Verdict(
            LayerId.TOOL_GUARD,
            outcome.verdict_action,
            outcome.reason,
            outcome.findings,
            _ms(start),
            outcome.detail,
        )
        action = "allow" if self.layers.observe_only else outcome.action
        return ToolReview(action, verdict, outcome.findings)

    def review_tool_arguments(self, call: ToolCall, ctx: RunContext) -> Verdict | None:
        """The output guard's check of an outbound call's arguments: a blocking verdict, or None."""
        if not self.layers.output_guard:
            return None
        start = time.perf_counter()
        outcome = output_guard.review_tool_arguments(call, ctx)
        if outcome is None:
            return None
        return Verdict(
            LayerId.OUTPUT_GUARD, outcome.action, outcome.reason, outcome.findings, _ms(start)
        )

    # --- Layer 5 ---------------------------------------------------------------------------

    def review_output(self, text: str, ctx: RunContext) -> OutputReview:
        if not self.layers.output_guard:
            return OutputReview(text, False, Verdict(LayerId.OUTPUT_GUARD, Action.OFF, OFF_REASON))
        start = time.perf_counter()
        outcome = output_guard.review(text, ctx)
        verdict = Verdict(
            LayerId.OUTPUT_GUARD, outcome.action, outcome.reason, outcome.findings, _ms(start)
        )
        if self.layers.observe_only:
            return OutputReview(text, False, verdict, outcome.removed_urls)
        return OutputReview(outcome.text, outcome.blocked, verdict, outcome.removed_urls)


def _sentence(text: str) -> str:
    text = text.strip()
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    return text if text.endswith((".", "!", "?")) else text + "."
