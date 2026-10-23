"""Finding links and images in model output, and private data inside their addresses."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal
from urllib.parse import unquote_plus, urlsplit

from seculayer.text.encodings import SecretMatch, find_secrets

UrlKind = Literal["image", "link", "bare"]

_TITLE = r'(?:\s+"[^"]*")?'
_MD_IMAGE = re.compile(r"!\[(?P<text>[^\]]*)\]\(\s*<?(?P<url>[^\s)>]+)>?" + _TITLE + r"\s*\)")
_MD_LINK = re.compile(r"(?<!!)\[(?P<text>[^\]]*)\]\(\s*<?(?P<url>[^\s)>]+)>?" + _TITLE + r"\s*\)")
_HTML_IMG = re.compile(
    r"<img\b[^>]*?\bsrc\s*=\s*(?P<q>[\"']?)(?P<url>[^\"'\s>]+)(?P=q)[^>]*>", re.IGNORECASE
)
_HTML_A = re.compile(
    r"<a\b[^>]*?\bhref\s*=\s*(?P<q>[\"']?)(?P<url>[^\"'\s>]+)(?P=q)[^>]*>(?P<text>.*?)</a\s*>",
    re.IGNORECASE | re.DOTALL,
)
_AUTOLINK = re.compile(r"<(?P<url>https?://[^\s>]+)>", re.IGNORECASE)
_BARE = re.compile(r"(?P<url>(?:https?://|www\.)[^\s<>()\[\]\"'`]+)", re.IGNORECASE)
_ALT = re.compile(r"\balt\s*=\s*([\"'])(.*?)\1", re.IGNORECASE | re.DOTALL)
_TRAILING = ".,;:!?*_"
_HOSTNAME = re.compile(r"\b((?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z][a-z0-9-]*[a-z0-9])\b", re.I)


@dataclass(frozen=True)
class UrlRef:
    kind: UrlKind
    url: str
    text: str  # link text or image alt text
    start: int  # span of the whole construct in the source text
    end: int

    @property
    def host(self) -> str:
        return url_host(self.url)


def url_host(url: str) -> str:
    """The lowercase host of an absolute URL, or "" for a relative one."""
    candidate = (
        url
        if "://" in url or url.startswith("//")
        else ("http://" + url if url.lower().startswith("www.") else url)
    )
    try:
        return (urlsplit(candidate).hostname or "").lower()
    except ValueError:
        return ""


def extract_urls(text: str) -> list[UrlRef]:
    """Every Markdown or HTML image and link, autolink and bare URL, in order of position."""
    found: list[UrlRef] = []
    taken: list[tuple[int, int]] = []

    def add(kind: UrlKind, url: str, label: str, start: int, end: int) -> None:
        if any(s <= start < e or s < end <= e for s, e in taken):
            return
        taken.append((start, end))
        found.append(UrlRef(kind, url, label, start, end))

    for m in _MD_IMAGE.finditer(text):
        add("image", m["url"], m["text"], m.start(), m.end())
    for m in _HTML_IMG.finditer(text):
        alt = _ALT.search(m.group())
        add("image", m["url"], alt.group(2) if alt else "", m.start(), m.end())
    for m in _MD_LINK.finditer(text):
        add("link", m["url"], m["text"], m.start(), m.end())
    for m in _HTML_A.finditer(text):
        add("link", m["url"], re.sub(r"<[^>]+>", "", m["text"]).strip(), m.start(), m.end())
    for m in _AUTOLINK.finditer(text):
        add("link", m["url"], m["url"], m.start(), m.end())
    for m in _BARE.finditer(text):
        url = m["url"].rstrip(_TRAILING)
        add("bare", url, url, m.start(), m.start() + len(url))
    return sorted(found, key=lambda ref: ref.start)


def decode_url(url: str) -> str:
    """URL-decode (twice, to undo double encoding) so private data in a query is readable."""
    return unquote_plus(unquote_plus(url))


def private_data_in_url(url: str, values: tuple[str, ...] | list[str]) -> list[SecretMatch]:
    return find_secrets(decode_url(url), values)


def mentions_host(text: str, host: str) -> bool:
    """True if the host name (or a URL on it) appears anywhere in the text."""
    host = host.lower()
    return any(name.lower() == host for name in _HOSTNAME.findall(text))


def hosts_in_text(text: str) -> set[str]:
    return {name.lower() for name in _HOSTNAME.findall(text)}
