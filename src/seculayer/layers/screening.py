"""Layer 2, screening: rules, the classifier and the LLM judge check the user's own message and
every outside item for text that tries to instruct the AI (docs/PLAN.md §6.2).

Decision per item:
- intervene if an intervene rule matches, the classifier scores at or above the intervene
  threshold, or the judge says malicious;
- flag if a flag rule matches, the classifier scores between the thresholds, or the judge says
  suspicious.
Intervening on the user's message blocks the run; on an outside item it withholds the item.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from seculayer.layers.rules import Place, RuleMatch, find_encoded, run_rules
from seculayer.policy import Policy
from seculayer.types import (
    ClassifierUnavailable,
    Finding,
    InjectionClassifier,
    InjectionJudge,
    JudgeResult,
    JudgeUnavailable,
    LayerSwitches,
    ScoreSource,
    Segment,
    Source,
)

Decision = Literal["pass", "flag", "intervene"]
_RANK: dict[Decision, int] = {"pass": 0, "flag": 1, "intervene": 2}
_JUDGE_DECISIONS: dict[str, Decision] = {
    "benign": "pass",
    "suspicious": "flag",
    "malicious": "intervene",
}


@dataclass(frozen=True)
class ItemScreen:
    segment_id: str
    place: Place
    decision: Decision
    findings: tuple[Finding, ...]
    reason: str  # why it was flagged or stopped, as a clause: "it speaks directly to an AI reader"
    detail: str  # every sub-check: "Rules: … · Classifier: 0.00 (looks normal) · Judge: benign"


@dataclass(frozen=True)
class ScreenResult:
    items: tuple[ItemScreen, ...]
    judge_called: bool


def _place(segment: Segment) -> Place:
    return "user" if segment.source is Source.USER else "outside"


def classifier_score(
    classifier: InjectionClassifier, text: str
) -> tuple[float | None, ScoreSource | None]:
    """A score and where it came from, or (None, None) when the classifier is unavailable."""
    try:
        score_with_source = getattr(classifier, "score_with_source", None)
        if score_with_source is not None:
            score, source = score_with_source(text)
            return float(score), source
        return float(classifier.score(text)), "live"
    except ClassifierUnavailable:
        return None, None


def screen(
    segments: Sequence[Segment],
    policy: Policy,
    *,
    switches: LayerSwitches,
    classifier: InjectionClassifier | None,
    judge: InjectionJudge | None,
) -> ScreenResult:
    """Screen the user's message and outside items. Placeholders SecuLayer added are skipped."""
    targets = [s for s in segments if s.source in (Source.USER, Source.EXTERNAL) and s.text.strip()]
    judged: dict[str, JudgeResult] = {}
    judge_called = False
    if switches.judge and judge is not None:
        items = [s for s in targets if s.source is Source.EXTERNAL or policy.screening.judge_user]
        if items:
            mode: Literal["outside", "user"] = (
                "outside" if any(s.source is Source.EXTERNAL for s in items) else "user"
            )
            judge_called = True
            try:
                judged = {r.segment_id: r for r in judge.judge(items, mode)}
            except JudgeUnavailable:
                judged = {
                    s.id: JudgeResult(s.id, "suspicious", False, None, None, "judge unavailable")
                    for s in items
                }

    results = tuple(
        _screen_item(segment, policy, switches, classifier, judged.get(segment.id))
        for segment in targets
    )
    return ScreenResult(results, judge_called)


def _screen_item(
    segment: Segment,
    policy: Policy,
    switches: LayerSwitches,
    classifier: InjectionClassifier | None,
    judged: JudgeResult | None,
) -> ItemScreen:
    place = _place(segment)
    findings: list[Finding] = []
    reasons: list[tuple[Decision, str]] = []
    detail: list[str] = []
    thresholds = policy.screening

    def decide_score(score: float) -> Decision:
        if score >= thresholds.classifier_intervene:
            return "intervene"
        if score >= thresholds.classifier_flag:
            return "flag"
        return "pass"

    if switches.rules:
        matches = run_rules(segment.text, place)
        for match in matches:
            findings.append(_rule_finding(segment.id, match))
            reasons.append(("intervene" if match.severity == "intervene" else "flag", match.name))
        encoded_notes = []
        for encoded in find_encoded(segment.text, place):
            label = "Base64" if encoded.encoding == "base64" else "hex"
            decision: Decision = "pass"
            if encoded.inner:
                decision = "intervene"
            elif switches.classifier and classifier is not None:
                score, _source = classifier_score(classifier, encoded.decoded)
                if score is not None:
                    decision = decide_score(score)
            if decision == "pass":
                continue
            excerpt = encoded.decoded[:160]
            findings.append(
                Finding(
                    "rule:encoded_payload",
                    segment.id,
                    encoded.span,
                    excerpt,
                    None,
                    f"Instructions hidden in {label}. Decoded: “{excerpt}”",
                    decision,
                )
            )
            reasons.append((decision, f"hides instructions in {label}"))
            encoded_notes.append(f"hidden in {label}")
        names = [m.name for m in matches] + encoded_notes
        detail.append("Rules: " + (", ".join(names) if names else "no match"))

    if switches.classifier and classifier is not None:
        score, source = classifier_score(classifier, segment.text)
        if score is None:
            detail.append("Classifier unavailable (model not downloaded)")
            findings.append(
                Finding("classifier", segment.id, None, "", None, "Classifier unavailable.")
            )
        else:
            decision = decide_score(score)
            looks = "looks like an attack" if decision != "pass" else "looks normal"
            recorded = ", recorded score" if source == "recorded" else ""
            detail.append(f"Classifier: {score:.2f} ({looks}{recorded})")
            if decision != "pass":
                findings.append(
                    Finding(
                        "classifier",
                        segment.id,
                        None,
                        segment.text[:160],
                        score,
                        f"The classifier scored this {score:.2f}: it looks like an attack.",
                        decision,
                    )
                )
                reasons.append((decision, f"the classifier scored it {score:.2f}"))

    if judged is not None:
        decision = _JUDGE_DECISIONS[judged.verdict]
        quoted = f" (‘{judged.reason}’)" if judged.reason else ""
        detail.append(f"Judge: {judged.verdict}{quoted}")
        if decision != "pass":
            findings.append(
                Finding(
                    "judge",
                    segment.id,
                    None,
                    judged.evidence or "",
                    None,
                    f"The judge rated this {judged.verdict}: {judged.reason}",
                    decision,
                )
            )
            reasons.append((decision, f"the judge rated it {judged.verdict}"))

    overall: Decision = "pass"
    for decision, _ in reasons:
        if _RANK[decision] > _RANK[overall]:
            overall = decision
    main = [text for decision, text in reasons if decision == overall]
    rule_clauses = [text for text in main if not text.startswith("the ")]
    other_clauses = [text for text in main if text.startswith("the ")]
    clauses = ([f"it {_join_clauses(rule_clauses)}"] if rule_clauses else []) + other_clauses
    reason = _join_clauses(clauses)
    return ItemScreen(segment.id, place, overall, tuple(findings), reason, " · ".join(detail))


def _rule_finding(segment_id: str, match: RuleMatch) -> Finding:
    return Finding(
        f"rule:{match.rule_id}",
        segment_id,
        match.span,
        match.excerpt,
        None,
        f"This text {match.name}.",
        match.severity,
    )


def _join_clauses(clauses: list[str]) -> str:
    unique = list(dict.fromkeys(clauses))
    if not unique:
        return ""
    if len(unique) == 1:
        return unique[0]
    return ", ".join(unique[:-1]) + " and " + unique[-1]
