"""Normalisation and decoding used to find secrets and encoded instructions (docs/PLAN.md §6.2)."""

from __future__ import annotations

import base64
import binascii
import re
from dataclasses import dataclass

from seculayer.text.unicode import normalize_for_matching

# Base64 (standard or URL-safe alphabet) and hex runs long enough to hide a sentence.
_BASE64_RUN = re.compile(r"[A-Za-z0-9+/_-]{24,}={0,2}")
_HEX_RUN = re.compile(r"\b(?:[0-9a-fA-F]{2}){12,}\b")


def alnum(text: str) -> str:
    """Lowercase with everything except letters and digits removed: "F-E-R-N" -> "fern"."""
    return "".join(ch for ch in normalize_for_matching(text) if ch.isalnum())


@dataclass(frozen=True)
class DecodedRun:
    encoding: str  # "base64" or "hex"
    start: int
    end: int
    raw: str
    decoded: str


def _printable(decoded: bytes) -> str | None:
    try:
        text = decoded.decode("utf-8")
    except UnicodeDecodeError:
        return None
    if not text or sum(ch.isprintable() or ch in "\n\t" for ch in text) < 0.9 * len(text):
        return None
    return text


def decode_runs(text: str) -> list[DecodedRun]:
    """Base64 and hex runs of 24 or more characters that decode to readable UTF-8 text."""
    runs: list[DecodedRun] = []
    for match in _HEX_RUN.finditer(text):
        decoded = _printable(bytes.fromhex(match.group()))
        if decoded is not None:
            runs.append(DecodedRun("hex", match.start(), match.end(), match.group(), decoded))
    hex_spans = [(r.start, r.end) for r in runs]
    for match in _BASE64_RUN.finditer(text):
        if any(s <= match.start() < e for s, e in hex_spans):
            continue
        raw = match.group()
        candidate = raw.replace("-", "+").replace("_", "/")
        candidate += "=" * (-len(candidate) % 4)
        try:
            data = base64.b64decode(candidate, validate=True)
        except (binascii.Error, ValueError):
            continue
        decoded = _printable(data)
        if decoded is not None:
            runs.append(DecodedRun("base64", match.start(), match.end(), raw, decoded))
    return sorted(runs, key=lambda run: run.start)


@dataclass(frozen=True)
class SecretMatch:
    value: str
    how: str  # "as written", "with separators removed", "reversed", "hidden in Base64", ...


def find_secret(text: str, value: str) -> SecretMatch | None:
    """Find a protected value in text after normalisation, reversed, or inside encoded runs."""
    target = alnum(value)
    if not target:
        return None
    if value.lower() in normalize_for_matching(text):
        return SecretMatch(value, "as written")
    flat = alnum(text)
    if target in flat:
        return SecretMatch(value, "with separators removed")
    if target[::-1] in flat:
        return SecretMatch(value, "reversed")
    for run in decode_runs(text):
        inner = find_secret(run.decoded, value)
        if inner is not None:
            label = "Base64" if run.encoding == "base64" else "hex"
            return SecretMatch(value, f"hidden in {label}")
    return None


def find_secrets(text: str, values: tuple[str, ...] | list[str]) -> list[SecretMatch]:
    return [match for value in values if (match := find_secret(text, value)) is not None]
