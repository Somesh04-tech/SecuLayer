"""The prompt anatomy: each model request as source-coloured parts (docs/PLAN.md §6.9).

`injected` parts come only from the case's ground-truth `injected_text`, never from a detector.
Hidden parts (CSS-hidden elements, HTML comments, invisible characters) are marked so the UI
can show what the model reads but a person doesn't see.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Sequence

from seculayer.layers.hardening import approx_tokens, datamark, escape_markers
from seculayer.layers.hidden_text import clean_segment
from seculayer.text.unicode import find_invisible
from seculayer.types import HiddenPiece, Message, PromptLayout, Segment, Source
from seculayer_demo.prompting import tool_result_text
from seculayer_demo.server.events import AnatomyMessage, AnatomyPart, HiddenKindOut, PartSource

_COMMENT = re.compile(r"<!--.*?-->", re.S)
_SOURCE: dict[Source, PartSource] = {
    Source.DEVELOPER: "developer",
    Source.USER: "user",
    Source.EXTERNAL: "external",
    Source.SECULAYER: "seculayer",
}


def _hidden_spans(segment: Segment) -> list[tuple[int, int, HiddenKindOut]]:
    """Spans of text in the segment that a person wouldn't see."""
    spans: list[tuple[int, int, HiddenKindOut]] = []
    for run in find_invisible(segment.text):
        kind: HiddenKindOut = "tag_chars" if run.kind == "tag_chars" else "zero_width"
        spans.append((run.start, run.end, kind))
    if segment.format == "html":
        for match in _COMMENT.finditer(segment.text):
            spans.append((match.start(), match.end(), "comment"))
        for piece in clean_segment(segment).hidden:
            if piece.kind != "css":
                continue
            at = _find_flexible(segment.text, piece.text)
            if at is not None:
                spans.append((*at, "css"))
    return spans


def _find_flexible(text: str, needle: str) -> tuple[int, int] | None:
    """Find `needle` in `text`, allowing any whitespace (or markup) where the needle has spaces."""
    words = [re.escape(w) for w in needle.split()]
    if not words:
        return None
    match = re.search(r"(?:\s|<[^>]*>)+".join(words), text)
    return match.span() if match else None


def _injected_spans(text: str, injected: Sequence[str]) -> list[tuple[int, int]]:
    spans = []
    for needle in injected:
        for candidate in {needle, datamark(escape_markers(needle)), json.dumps(needle)[1:-1]}:
            start = text.find(candidate)
            while start >= 0 and candidate:
                spans.append((start, start + len(candidate)))
                start = text.find(candidate, start + 1)
    return spans


def segment_parts(
    segment: Segment,
    injected: Sequence[str],
    removed: Iterable[HiddenPiece] = (),
) -> list[AnatomyPart]:
    text = segment.text
    base = _SOURCE[segment.source]
    sources: list[PartSource] = [base] * len(text)
    hidden: list[HiddenKindOut | None] = [None] * len(text)
    if segment.source in (Source.EXTERNAL, Source.USER):
        for start, end in _injected_spans(text, injected):
            for i in range(start, end):
                sources[i] = "injected"
    if segment.source is Source.EXTERNAL:
        for start, end, kind in _hidden_spans(segment):
            for i in range(start, end):
                hidden[i] = hidden[i] or kind

    parts: list[AnatomyPart] = []
    i = 0
    while i < len(text):
        j = i + 1
        while j < len(text) and sources[j] == sources[i] and hidden[j] == hidden[i]:
            j += 1
        parts.append(
            AnatomyPart(
                text=text[i:j],
                source=sources[i],
                segment_id=segment.id,
                hidden=hidden[i] is not None,
                hidden_kind=hidden[i],
            )
        )
        i = j
    for piece in removed:
        is_injected = any(n in piece.text or piece.text in n for n in injected if n)
        parts.append(
            AnatomyPart(
                text=piece.text,
                source="injected" if is_injected else "external",
                segment_id=segment.id,
                hidden=True,
                hidden_kind="comment"
                if piece.kind == "comment"
                else "tag_chars"
                if piece.kind == "tag_chars"
                else "zero_width"
                if piece.kind in ("zero_width", "bidi")
                else "css",
                removed=True,
            )
        )
    return parts


def _label(message: Message) -> str:
    if message.label:
        return message.label
    if message.role == "tool_call":
        return f"Tool call · {message.tool_name}({_short_args(message.content)})"
    if message.role == "tool_result":
        count = len(message.segments)
        noun = message.segments[0].noun if message.segments else "item"
        return f"Tool result · outside content · {count} {noun}{'s' if count != 1 else ''}"
    return message.role.capitalize()


def _short_args(arguments: str) -> str:
    try:
        data = json.loads(arguments or "{}")
    except json.JSONDecodeError:
        return arguments
    if not isinstance(data, dict):
        return arguments
    parts = []
    for key, value in data.items():
        if value in (None, [], ""):
            continue
        shown = ", ".join(value) if isinstance(value, list) else str(value)
        parts.append(f"{key}: {shown if len(shown) <= 60 else shown[:57] + '…'}")
    return ", ".join(parts)


def build_anatomy(
    layout: PromptLayout,
    injected: Sequence[str],
    removed: Sequence[HiddenPiece] = (),
) -> list[AnatomyMessage]:
    by_segment: dict[str, list[HiddenPiece]] = {}
    for piece in removed:
        by_segment.setdefault(piece.segment_id, []).append(piece)
    messages: list[AnatomyMessage] = []
    for message in layout.messages:
        parts: list[AnatomyPart] = []
        if message.role == "tool_call":
            parts = []
        elif message.role == "assistant":
            parts = [AnatomyPart(text=message.content, source="model")]
        else:
            for segment in message.segments:
                if message.role == "tool_result" and segment.meta:
                    header = "\n".join(
                        f"{k.capitalize()}: {v}"
                        for k, v in segment.meta
                        if k in ("from", "subject")
                    )
                    parts.append(
                        AnatomyPart(text=header + "\n", source="external", segment_id=segment.id)
                    )
                parts += segment_parts(segment, injected, by_segment.pop(segment.id, []))
                if message.role == "tool_result" and segment.meta:
                    parts.append(AnatomyPart(text="\n\n", source="external"))
        messages.append(
            AnatomyMessage(
                role=message.role,
                label=_label(message),
                tool_name=message.tool_name,
                parts=parts,
            )
        )
    return messages


def tokens_by_source(anatomy: Sequence[AnatomyMessage]) -> dict[str, int]:
    """Approximate tokens per source (about four characters per token), for the share bar."""
    totals: dict[str, int] = {}
    for message in anatomy:
        for part in message.parts:
            if part.removed:
                continue
            totals[part.source] = totals.get(part.source, 0) + approx_tokens(part.text)
    return totals


__all__ = ["build_anatomy", "segment_parts", "tokens_by_source", "tool_result_text"]
