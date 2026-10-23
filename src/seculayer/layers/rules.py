"""Screening rules: patterns for text that tries to instruct an AI (docs/PLAN.md §6.2, layer 2).

Matching runs on text that is NFKC-normalised and lowercased, with invisible characters
removed. Rules are brittle by nature: paraphrases, typos and other languages slip past them,
and normal text can trip them. The normal-use cases measure both.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from seculayer.text.encodings import decode_runs
from seculayer.text.unicode import normalize_for_matching
from seculayer.text.urls import extract_urls

Place = Literal["user", "outside"]
Severity = Literal["intervene", "flag"]


@dataclass(frozen=True)
class RuleMatch:
    rule_id: str
    name: str  # plain language, e.g. "speaks directly to an AI reader"
    severity: Severity
    span: tuple[int, int]  # offsets in the normalised text
    excerpt: str


@dataclass(frozen=True)
class Rule:
    id: str
    name: str
    severity: dict[Place, Severity]  # the places it applies to, with the severity there
    find: Callable[[str, str], list[tuple[int, int]]]  # (normalised, original) -> spans


def _regex(*patterns: str) -> Callable[[str, str], list[tuple[int, int]]]:
    compiled = [re.compile(p) for p in patterns]

    def find(normalised: str, _original: str) -> list[tuple[int, int]]:
        return [m.span() for regex in compiled for m in regex.finditer(normalised)]

    return find


_W = r"(?:\W+\w+){0,%d}?\W+"  # up to n intervening words

_OVERRIDE = _regex(
    r"\b(?:ignore|disregard|forget|override)\b" + _W % 4
    + r"(?:previous|prior|above|earlier|all|your|any|preceding)\b" + _W % 3
    + r"(?:instructions?|rules|prompts?|guidance|guidelines|directions|directives)\b",
    r"\b(?:ignore|disregard|forget|override)\s+(?:all\s+|any\s+|your\s+|the\s+)?"
    r"(?:instructions?|rules|guidelines|directives)\b",
)  # fmt: skip

_EXTRACTION = _regex(
    r"\b(?:repeat|print|show|reveal|output|display|recite|dump|tell me)\b" + _W % 6
    + r"(?:system prompt|instructions|everything above|text above|initial prompt"
    r"|your prompt|hidden prompt)",
)  # fmt: skip

_ROLE = _regex(
    r"\byou are now\b",
    r"\bfrom now on,? you\b",
    r"\bact as\b",
    r"\bpretend (?:to be|you are)\b",
    r"\blet'?s play a game\b",
    r"\bdeveloper mode\b",
    r"\bstay in character\b",
    r"\bno restrictions\b",
)

_FAKE_SYSTEM = _regex(
    r"</?\s*system\s*>",
    r"</\s*email\s*>",
    r"\[\s*system\s*\]",
    r"###\s*instruction",
    r"<\|im_start\|>",
    r"<\|system\|>",
    r"\{\s*\"role\"\s*:\s*\"system\"",
    r"\[/?inst\]",
)

_AI_WORDS = r"(?:ai|llm|language model|assistants?|summari[sz]ers?|chatbots?|bots|agents?)"
_ADDRESSED = _regex(
    r"\b(?:ai|llm)\s+(?:assistants?|models?|agents?|summari[sz]ers?|readers?|systems?)\s*[:,]",
    r"\bnotes?\s+(?:for|to)\s+(?:the\s+|any\s+|all\s+)?(?:\w+\s+)?" + _AI_WORDS + r"\b",
    r"\b(?:for|to|attention)\s*:?\s+(?:all\s+|any\s+|the\s+)?(?:\w+\s+)?"
    + r"(?:ai|llm|assistants|summari[sz]ers?|chatbots?)\s*[:,!]",
    r"\b(?:ai|llm)s?\s+(?:assistants?\s+)?must\b",
    r"\bassistants?\s+(?:must|should always)\b",
    r"\bassistant instructions?\s*:",
    r"\binstructions? for (?:the |any )?" + _AI_WORDS + r"\b",
    r"\bif you are an? (?:ai|llm|language model|assistant)\b",
)

_SECRECY = _regex(
    r"\b(?:do not|don'?t|never|without)\s+(?:mention|tell|inform|reveal|disclose|notify|alert"
    r"|let)\w*\b" + _W % 8 + r"(?:the user|user|dana|them|the reader|reader|recipient"
    r"|summary|reply|response|answer)\b",
    r"\b(?:keep|leave)\s+(?:this|it|that)\s+(?:secret|hidden|confidential|out of)",
)


def _exfil(normalised: str, original: str) -> list[tuple[int, int]]:
    spans = [
        m.span()
        for m in re.finditer(
            r"\breplace\s+\w+\s+with\b|\burl-?encoded\b|\bfill in the\b"
            r"|\bappend\b[^.]{0,40}\bto the (?:url|link|address)\b",
            normalised,
        )
    ]
    # Placeholders inside link or image addresses are case-sensitive (NOTES, EMPLOYEE_ID).
    for ref in extract_urls(original):
        if re.search(r"\{[^}]*\}|\b[A-Z][A-Z_]{3,}\b", ref.url.split("://", 1)[-1]):
            spans.append((ref.start, ref.end))
    return spans


RULES: tuple[Rule, ...] = (
    Rule(
        "instruction_override",
        "tells the AI to ignore its instructions",
        {"user": "intervene", "outside": "intervene"},
        _OVERRIDE,
    ),
    Rule(
        "prompt_extraction",
        "asks the AI to reveal its hidden instructions",
        {"user": "intervene"},
        _EXTRACTION,
    ),
    Rule(
        "role_reassignment",
        "tries to give the AI a new role",
        {"user": "flag", "outside": "flag"},
        _ROLE,
    ),
    Rule(
        "fake_system_marker",
        "fakes a system-message marker",
        {"user": "flag", "outside": "intervene"},
        _FAKE_SYSTEM,
    ),
    Rule(
        "addressed_to_ai", "speaks directly to an AI reader", {"outside": "intervene"}, _ADDRESSED
    ),
    Rule(
        "secrecy_request",
        "asks for something to be hidden from the user",
        {"outside": "intervene"},
        _SECRECY,
    ),
    Rule(
        "exfil_template",
        "asks for private data to be put into a link or image address",
        {"outside": "intervene"},
        _exfil,
    ),
)
RULE_NAMES = {rule.id: rule.name for rule in RULES} | {
    "encoded_payload": "hides instructions in encoded text"
}


def run_rules(text: str, place: Place) -> list[RuleMatch]:
    """Every rule that applies at this place and matches the text (one match per rule)."""
    normalised = normalize_for_matching(text)
    matches: list[RuleMatch] = []
    for rule in RULES:
        severity = rule.severity.get(place)
        if severity is None:
            continue
        spans = rule.find(normalised, text)
        if spans:
            start, end = min(spans)
            source = text if len(text) == len(normalised) else normalised
            matches.append(RuleMatch(rule.id, rule.name, severity, (start, end), source[start:end]))
    return matches


@dataclass(frozen=True)
class EncodedMatch:
    encoding: str  # "base64" or "hex"
    span: tuple[int, int]
    decoded: str
    inner: tuple[RuleMatch, ...]  # rules the decoded text trips


def find_encoded(text: str, place: Place) -> list[EncodedMatch]:
    """Base64 and hex runs that decode to text, rescanned with the other rules.

    Whether a run intervenes also depends on the classifier, which the screening layer adds.
    """
    return [
        EncodedMatch(
            run.encoding, (run.start, run.end), run.decoded, tuple(run_rules(run.decoded, place))
        )
        for run in decode_runs(text)
    ]
