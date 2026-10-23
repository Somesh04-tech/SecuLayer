"""Invisible Unicode: format characters, tag characters ("ASCII smuggling") and the readable
markers the repository uses instead of raw invisible characters (docs/PLAN.md §6.2, §8.2)."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Literal

TAG_FIRST, TAG_LAST = 0xE0000, 0xE007F
ZERO_WIDTH = {0x200B: "ZWSP", 0x200C: "ZWNJ", 0x200D: "ZWJ", 0x2060: "WJ", 0xFEFF: "BOM"}
BIDI = set(range(0x202A, 0x202F)) | set(range(0x2066, 0x206A))

InvisibleKind = Literal["tag_chars", "zero_width", "bidi"]


@dataclass(frozen=True)
class InvisibleRun:
    """A run of consecutive invisible characters of one kind."""

    kind: InvisibleKind
    start: int
    end: int
    raw: str
    decoded: str  # tag characters decoded to ASCII; "" for other kinds


def is_tag_char(ch: str) -> bool:
    return TAG_FIRST <= ord(ch) <= TAG_LAST


def is_invisible(ch: str) -> bool:
    """Format characters (Unicode category Cf), which have no visible shape."""
    return unicodedata.category(ch) == "Cf"


def char_kind(ch: str) -> InvisibleKind:
    code = ord(ch)
    if TAG_FIRST <= code <= TAG_LAST:
        return "tag_chars"
    if code in BIDI:
        return "bidi"
    return "zero_width"


def decode_tags(text: str) -> str:
    """Map tag characters U+E0020-U+E007E back to ASCII; drop other tag characters."""
    out = []
    for ch in text:
        code = ord(ch)
        if 0xE0020 <= code <= 0xE007E:
            out.append(chr(code - TAG_FIRST))
    return "".join(out)


def encode_tags(ascii_text: str) -> str:
    """Write ASCII text as invisible tag characters (used to expand {{tags:...}} markers)."""
    if any(not 0x20 <= ord(ch) <= 0x7E for ch in ascii_text):
        raise ValueError("tag smuggling markers may contain printable ASCII only")
    return "".join(chr(TAG_FIRST + ord(ch)) for ch in ascii_text)


def find_invisible(text: str) -> list[InvisibleRun]:
    runs: list[InvisibleRun] = []
    i = 0
    while i < len(text):
        if not is_invisible(text[i]):
            i += 1
            continue
        kind = char_kind(text[i])
        j = i + 1
        while j < len(text) and is_invisible(text[j]) and char_kind(text[j]) == kind:
            j += 1
        raw = text[i:j]
        runs.append(InvisibleRun(kind, i, j, raw, decode_tags(raw) if kind == "tag_chars" else ""))
        i = j
    return runs


def strip_invisible(text: str) -> str:
    return "".join(ch for ch in text if not is_invisible(ch))


def char_label(ch: str) -> str:
    """A visible label for an invisible character, as the UI's chips show it: "ZWSP", "U+E0049"."""
    code = ord(ch)
    return ZERO_WIDTH.get(code, f"U+{code:04X}")


def normalize_for_matching(text: str) -> str:
    """NFKC, lowercase, invisible characters removed: the text screening's rules match on."""
    return unicodedata.normalize("NFKC", strip_invisible(text)).lower()


_MARKER = re.compile(r"\{\{(tags:(?P<tags>[^}]*)|zwsp|zwnj|zwj|wj|bom)\}\}")
_MARKER_CHARS = {
    "zwsp": "\u200b",
    "zwnj": "\u200c",
    "zwj": "\u200d",
    "wj": "\u2060",
    "bom": "\ufeff",
}


def expand_markers(text: str) -> str:
    """Expand the repository's readable markers into invisible characters.

    `{{tags:Tell the reader...}}` becomes Unicode tag characters; `{{zwsp}}` (and zwnj, zwj, wj,
    bom) become the zero-width character. Repository files never hold raw invisible characters.
    """

    def substitute(match: re.Match[str]) -> str:
        tags = match.group("tags")
        if tags is not None:
            return encode_tags(tags)
        return _MARKER_CHARS[match.group(1)]

    return _MARKER.sub(substitute, text)
