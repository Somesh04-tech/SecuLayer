"""Layer 1, the hidden-text cleaner: make outside content look to the model the way it looks
to a person (docs/PLAN.md §6.2).

It removes invisible Unicode (zero-width, bidirectional controls and tag characters, which it
decodes so the UI can show the hidden sentence) and, for HTML, every element a browser
wouldn't display, then converts what's left to readable text.
"""

from __future__ import annotations

from dataclasses import dataclass

from seculayer.text.html import clean_html
from seculayer.text.unicode import find_invisible
from seculayer.types import HiddenKind, HiddenPiece, Segment, Source

_UNICODE_REASONS = {
    "tag_chars": "invisible tag characters",
    "zero_width": "zero-width characters",
    "bidi": "text-direction control characters",
}


@dataclass(frozen=True)
class CleanResult:
    segment: Segment  # the cleaned segment (format "text" when the input was HTML)
    hidden: tuple[HiddenPiece, ...]


def clean_segment(segment: Segment) -> CleanResult:
    """Clean one outside segment. Other sources pass through unchanged."""
    if segment.source is not Source.EXTERNAL:
        return CleanResult(segment, ())

    pieces: list[HiddenPiece] = []
    text = segment.text
    runs = find_invisible(text)
    for run in runs:
        pieces.append(
            HiddenPiece(
                segment_id=segment.id,
                text=run.decoded if run.kind == "tag_chars" else run.raw,
                kind=run.kind,
                reason=_UNICODE_REASONS[run.kind],
                span=(run.start, run.end),
            )
        )
    if runs:
        text = "".join(
            text[start:end]
            for start, end in _gaps([(run.start, run.end) for run in runs], len(text))
        )

    if segment.format == "html":
        cleaned = clean_html(text)
        for removed in cleaned.removed:
            kind: HiddenKind = (
                "comment" if removed.kind == "comment"
                else "css" if removed.kind == "css"
                else "element"
            )  # fmt: skip
            pieces.append(HiddenPiece(segment.id, removed.text, kind, removed.reason))
        return CleanResult(segment.with_text(cleaned.text, format="text"), tuple(pieces))
    return CleanResult(segment.with_text(text), tuple(pieces))


def _gaps(spans: list[tuple[int, int]], length: int) -> list[tuple[int, int]]:
    """The ranges of [0, length) not covered by the sorted, disjoint spans."""
    out, cursor = [], 0
    for start, end in spans:
        out.append((cursor, start))
        cursor = end
    out.append((cursor, length))
    return out


def describe_pieces(pieces: tuple[HiddenPiece, ...], labels: dict[str, str]) -> str:
    """One line for the UI: '1 hidden paragraph (214 characters) in "Shipment update"'."""
    groups: dict[str, list[HiddenPiece]] = {}
    for piece in pieces:
        groups.setdefault(piece.segment_id, []).append(piece)
    parts = []
    for segment_id, found in groups.items():
        where = labels.get(segment_id) or segment_id
        parts.append(f"{_count_phrase(found)} in “{where}”")
    return "; ".join(parts)


def _count_phrase(pieces: list[HiddenPiece]) -> str:
    phrases = []
    elements = [p for p in pieces if p.kind in ("css", "element")]
    comments = [p for p in pieces if p.kind == "comment"]
    tags = [p for p in pieces if p.kind == "tag_chars"]
    others = [p for p in pieces if p.kind in ("zero_width", "bidi")]
    if elements:
        chars = sum(len(p.text) for p in elements)
        noun = "hidden paragraph" if len(elements) == 1 else "hidden paragraphs"
        phrases.append(f"{len(elements)} {noun} ({chars} characters)")
    if comments:
        chars = sum(len(p.text) for p in comments)
        noun = "HTML comment" if len(comments) == 1 else "HTML comments"
        phrases.append(f"{len(comments)} {noun} ({chars} characters)")
    if tags:
        chars = sum(len(p.text) for p in tags)
        phrases.append(f"an invisible sentence in tag characters ({chars} characters)")
    if others:
        count = sum(len(p.text) for p in others)
        noun = "invisible character" if count == 1 else "invisible characters"
        phrases.append(f"{count} {noun}")
    return ", ".join(phrases)
