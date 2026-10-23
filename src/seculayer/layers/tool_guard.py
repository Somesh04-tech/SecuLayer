"""Layer 4, the tool guard: check every tool call the model proposes before it runs
(docs/PLAN.md §6.2). For an outbound tool the checks run in this order:

1. Task permission: the user's own message must ask for an outbound action. Otherwise block.
2. Recipients: every address must be a contact or written in the user's message. Otherwise ask.
3. Provenance: a value (address or URL) that appears in outside content, but not in the user's
   message or the contacts, "came from outside content". If screening flagged that content,
   block; otherwise ask.
4. Data: a protected value, or 40+ characters copied from a private item, going to anyone who
   isn't a contact: ask, with the data highlighted.
5. Otherwise the call passes.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from seculayer.policy import ToolPolicy
from seculayer.text.encodings import find_secrets
from seculayer.text.unicode import normalize_for_matching
from seculayer.text.urls import extract_urls
from seculayer.types import Action, Finding, RunContext, Segment, ToolAction, ToolCall

COPIED_RUN = 40
_ADDRESS = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")


@dataclass(frozen=True)
class GuardOutcome:
    action: ToolAction
    verdict_action: Action
    reason: str
    findings: tuple[Finding, ...]
    detail: tuple[str, ...]


def recipients(call: ToolCall, tool: ToolPolicy) -> list[str]:
    found: list[str] = []
    for field in tool.recipient_fields:
        found += [a.strip().lower() for a in _as_strings(call.arguments.get(field))]
    return [a for a in found if a]


def _as_strings(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [part for part in re.split(r"[,;]", value) if part.strip()]
    if isinstance(value, list | tuple):
        return [str(item) for item in value if item is not None]
    return [str(value)]


def asks_for_outbound(user_text: str, words: Iterable[str]) -> bool:
    """Whether the user's own text asks for an outbound action (whole words only)."""
    text = normalize_for_matching(user_text)
    return any(re.search(rf"\b{re.escape(word.lower())}\b", text) for word in words)


def review(call: ToolCall, ctx: RunContext) -> GuardOutcome:
    policy = ctx.policy
    tool = policy.tools.get(call.name)
    if tool is None or not tool.outbound:
        return GuardOutcome("allow", Action.PASSED, f"{call.name} only reads data.", (), ())
    who = policy.user_name

    # 1. Task permission (least privilege): only the user's own text is read.
    if not asks_for_outbound(ctx.user_text, tool.user_intent_words):
        return GuardOutcome(
            "block",
            Action.BLOCKED,
            f"{who} didn't ask to send anything.",
            (),
            (f"{who}'s request contains none of: {', '.join(tool.user_intent_words)}.",),
        )

    user_lower = normalize_for_matching(ctx.user_text)
    confirm: list[str] = []
    findings: list[Finding] = []
    detail: list[str] = []

    # 2. Recipients.
    addresses = recipients(call, tool)
    outsiders = [a for a in addresses if not policy.is_contact(a) and a not in user_lower]
    for address in outsiders:
        confirm.append(f"{address} isn't in {who}'s contacts.")

    # 3. Provenance: values that came from outside content, not from the user or contacts.
    values = list(addresses)
    for field in tool.data_fields:
        for text in _as_strings(call.arguments.get(field)):
            values += [ref.url for ref in extract_urls(text)]
    for value in dict.fromkeys(values):
        lowered = value.lower()
        if policy.is_contact(lowered) or lowered in user_lower:
            continue
        sources = [seg for seg in ctx.outside_segments.values() if lowered in _haystack(seg)]
        if not sources:
            continue
        noun = sources[0].noun
        flagged = [seg for seg in sources if seg.id in ctx.flagged_segment_ids]
        findings.append(
            Finding(
                "tool_guard:provenance",
                sources[0].id,
                None,
                value,
                None,
                f"This value came from an {noun} {who} received, not from {who}.",
            )
        )
        if flagged:
            label = flagged[0].label or flagged[0].id
            return GuardOutcome(
                "block",
                Action.BLOCKED,
                f"{value} came from “{label}”, which screening flagged.",
                tuple(findings),
                tuple(detail),
            )
        confirm.append(f"{value} came from an {noun} {who} received, not from {who}.")

    # 4. Data: protected values or copied private text going to someone who isn't a contact.
    if any(not policy.is_contact(a) for a in addresses):
        for field in tool.data_fields:
            for text in _as_strings(call.arguments.get(field)):
                for match in find_secrets(text, policy.protected_values):
                    label = policy.label_for(match.value)
                    findings.append(
                        Finding(
                            "tool_guard:data",
                            None,
                            _span(text, match.value),
                            match.value,
                            None,
                            f"The {field} contains {label}.",
                        )
                    )
                    confirm.append(f"The {field} contains {label}.")
                for segment_id, chunk in _copied_private(text, ctx):
                    findings.append(
                        Finding(
                            "tool_guard:data",
                            segment_id,
                            None,
                            chunk,
                            None,
                            f"The {field} copies text from a private item.",
                        )
                    )
                    confirm.append(f"The {field} copies text from a private item.")

    if confirm:
        reasons = list(dict.fromkeys(confirm))
        return GuardOutcome(
            "confirm", Action.CONFIRM, " ".join(reasons), tuple(findings), tuple(reasons)
        )
    return GuardOutcome(
        "allow",
        Action.PASSED,
        f"{who} asked for this, and every recipient is a contact or named by {who}.",
        tuple(findings),
        tuple(detail),
    )


def _span(text: str, value: str) -> tuple[int, int] | None:
    at = text.lower().find(value.lower())
    return (at, at + len(value)) if at >= 0 else None


def _haystack(segment: Segment) -> str:
    """A segment's text plus its app fields (an email's From line), lowercased."""
    return "\n".join([segment.text, *(value for _, value in segment.meta)]).lower()


def _copied_private(text: str, ctx: RunContext) -> list[tuple[str, str]]:
    """(segment ID, copied text) for private items `text` copies 40+ characters from."""
    out: list[tuple[str, str]] = []
    squashed = _squash(text)
    for segment in ctx.outside_segments.values():
        if not segment.private:
            continue
        source = _squash(ctx.visible_outside.get(segment.id, segment.text))
        for start in range(0, max(len(source) - COPIED_RUN + 1, 0), 10):
            chunk = source[start : start + COPIED_RUN]
            if chunk in squashed:
                out.append((segment.id, chunk))
                break
    return out


def _squash(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)).strip().lower()


def dialog_fields(call: ToolCall) -> Mapping[str, Any]:
    """What the confirmation dialog shows: recipients, subject and body."""
    args = call.arguments
    to = [*_as_strings(args.get("to")), *_as_strings(args.get("cc")), *_as_strings(args.get("bcc"))]
    return {
        "to": to,
        "subject": str(args.get("subject") or ""),
        "body": str(args.get("body") or ""),
    }
