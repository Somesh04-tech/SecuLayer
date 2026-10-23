"""Core types shared by every layer (docs/PLAN.md §6.5)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Literal, Protocol

if TYPE_CHECKING:
    from seculayer.policy import Policy

Format = Literal["text", "html", "markdown", "json"]
Role = Literal["developer", "user", "assistant", "tool_call", "tool_result"]


class Source(StrEnum):
    DEVELOPER = "developer"  # the app's own instructions
    USER = "user"  # the person using the app (the attacker, in direct attacks)
    EXTERNAL = "external"  # outside content: emails, pages, documents, tool results
    SECULAYER = "seculayer"  # text SecuLayer adds: the trust policy, withheld placeholders


# What a withheld item is called in its placeholder, by segment-ID prefix.
_ITEM_NOUNS = {"email": "email", "page": "page", "kb": "article", "article": "article"}


def noun_for(segment_id: str) -> str:
    """What an item is, for UI copy: "email", "page", "article" or "item"."""
    return _ITEM_NOUNS.get(segment_id.split(":", 1)[0], "item")


@dataclass(frozen=True)
class Segment:
    id: str  # stable, e.g. "email:nw-88213"
    source: Source
    text: str
    format: Format = "text"
    label: str = ""  # shown in the UI, e.g. "Email from Northwind Logistics"
    private: bool = False  # holds the user's private data (used by the tool guard)
    # App text that only frames outside content ("Page HTML:"); hardening moves it with that
    # content when it moves the content out of the developer or user message.
    outside_scaffold: bool = False
    meta: tuple[tuple[str, str], ...] = ()  # app fields shown beside the text (from, subject)

    @property
    def noun(self) -> str:
        """What the item is, for UI copy: "email", "page", "article" or "item"."""
        return noun_for(self.id)

    def with_text(self, text: str, *, format: Format | None = None) -> Segment:
        return replace(self, text=text, format=format or self.format)


@dataclass(frozen=True)
class Message:
    """A provider-neutral prompt message."""

    role: Role
    segments: tuple[Segment, ...]
    tool_name: str | None = None
    call_id: str | None = None
    label: str = ""  # optional UI label, e.g. "Outside content (moved by SecuLayer)"
    content: str = ""  # model-written text: an assistant reply or a tool call's JSON arguments

    @property
    def text(self) -> str:
        """The message as the model reads it."""
        return ("".join(segment.text for segment in self.segments) or self.content).strip()


@dataclass(frozen=True)
class PromptLayout:
    messages: tuple[Message, ...]

    def segments(self) -> tuple[Segment, ...]:
        return tuple(segment for message in self.messages for segment in message.segments)

    def inspectable_segments(self) -> tuple[Segment, ...]:
        """Segments that layers 1-2 inspect: the user's text and all outside content."""
        return tuple(s for s in self.segments() if s.source is not Source.DEVELOPER)

    def replace_segments(self, replacements: Sequence[Segment]) -> PromptLayout:
        """Swap segments by ID (for example, cleaned or withheld versions)."""
        by_id = {segment.id: segment for segment in replacements}
        return PromptLayout(
            tuple(
                replace(m, segments=tuple(by_id.get(s.id, s) for s in m.segments))
                for m in self.messages
            )
        )

    def append(self, *messages: Message) -> PromptLayout:
        return PromptLayout(self.messages + messages)


class LayerId(StrEnum):
    HIDDEN_TEXT = "hidden_text"
    SCREENING = "screening"
    HARDENING = "hardening"
    TOOL_GUARD = "tool_guard"
    OUTPUT_GUARD = "output_guard"


class Action(StrEnum):
    PASSED = "passed"
    FLAGGED = "flagged"
    APPLIED = "applied"
    REMOVED = "removed"
    WITHHELD = "withheld"
    BLOCKED = "blocked"
    CONFIRM = "confirm"
    OFF = "off"
    NOT_REACHED = "not_reached"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class Finding:
    detector: str  # "rule:addressed_to_ai", "classifier", "judge", "hidden:white_text", ...
    segment_id: str | None
    span: tuple[int, int] | None  # character offsets in the segment's text
    excerpt: str
    score: float | None
    explanation: str  # one plain-language sentence


@dataclass(frozen=True)
class Verdict:
    layer: LayerId
    action: Action
    reason: str  # the one line the UI shows
    findings: tuple[Finding, ...] = ()
    latency_ms: float = 0.0
    detail: tuple[str, ...] = ()  # extra lines for the expandable row detail


@dataclass(frozen=True)
class LayerSwitches:
    hidden_text: bool = True
    screening: bool = True
    rules: bool = True
    classifier: bool = True
    judge: bool = True
    hardening: bool = True
    tool_guard: bool = True
    output_guard: bool = True
    observe_only: bool = False  # compute every verdict but change nothing (evaluation only)

    @classmethod
    def all_off(cls) -> LayerSwitches:
        return cls(
            hidden_text=False,
            screening=False,
            rules=False,
            classifier=False,
            judge=False,
            hardening=False,
            tool_guard=False,
            output_guard=False,
        )


HiddenKind = Literal["css", "comment", "element", "tag_chars", "zero_width", "bidi"]


@dataclass(frozen=True)
class HiddenPiece:
    """A piece of text the hidden-text cleaner removed."""

    segment_id: str
    text: str  # the removed text, decoded where possible (tag characters become ASCII)
    kind: HiddenKind
    reason: str  # plain language: "white text", "HTML comment", "tag characters", ...
    span: tuple[int, int] | None = None  # offsets in the original segment text, when known


@dataclass(frozen=True)
class ToolCall:
    call_id: str
    name: str
    arguments: Mapping[str, Any]


@dataclass(frozen=True)
class JudgeResult:
    segment_id: str
    verdict: Literal["benign", "suspicious", "malicious"]
    targets_ai: bool
    requested_action: str | None
    evidence: str | None
    reason: str


class JudgeUnavailable(RuntimeError):
    """The judge couldn't give a verdict; every item it was asked about counts as suspicious."""


class ClassifierUnavailable(RuntimeError):
    """The classifier can't score this text: no model files and no recorded score."""


ScoreSource = Literal["live", "cached", "recorded"]


class InjectionClassifier(Protocol):
    name: str

    def score(self, text: str) -> float:
        """Probability that the text is an injection ("malicious"), 0-1.

        Raises ClassifierUnavailable when no score can be produced.
        """
        ...


class SourcedClassifier(InjectionClassifier, Protocol):
    """A classifier that also says where a score came from (the UI shows "recorded score")."""

    def score_with_source(self, text: str) -> tuple[float, ScoreSource]: ...


class InjectionJudge(Protocol):
    def judge(
        self, items: Sequence[Segment], mode: Literal["outside", "user"]
    ) -> Sequence[JudgeResult]: ...


@dataclass
class RunContext:
    """Per-run state the layers share (mutable: it accumulates as the run proceeds)."""

    policy: Policy
    user_text: str
    seed: str = ""
    developer_text: str = ""  # the app's own instructions (trusted, for the link rule)
    outside_segments: dict[str, Segment] = field(default_factory=dict)  # original text, by ID
    visible_outside: dict[str, str] = field(default_factory=dict)  # what a person would see
    flagged_segment_ids: set[str] = field(default_factory=set)  # flagged or withheld by screening


@dataclass(frozen=True)
class Inspection:
    segments: tuple[Segment, ...]  # cleaned; withheld ones replaced by a placeholder segment
    hidden: tuple[HiddenPiece, ...]
    withheld_ids: tuple[str, ...]
    blocked: bool  # the user's own message was blocked
    verdicts: tuple[Verdict, ...]
    block_reason: str = ""


ToolAction = Literal["allow", "confirm", "block"]


@dataclass(frozen=True)
class ToolReview:
    action: ToolAction
    verdict: Verdict
    highlights: tuple[Finding, ...] = ()


@dataclass(frozen=True)
class OutputReview:
    text: str
    blocked: bool
    verdict: Verdict
    removed_urls: tuple[str, ...] = ()
