"""HTML visibility: remove what a person wouldn't see, then convert the rest to readable text
(docs/PLAN.md §6.2, layer 1).

The rules are deliberately simple: inline styles plus single-class rules from <style> blocks.
A real browser evaluates far more (external stylesheets, complex selectors, transforms), and
the "How it can fail" copy says so.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup
from bs4.element import Comment, NavigableString, PageElement, Tag

REMOVED_ELEMENTS = ("script", "style", "template", "noscript")
BLOCK_TAGS = {
    "address", "article", "aside", "blockquote", "body", "dd", "div", "dl", "dt", "fieldset",
    "figcaption", "figure", "footer", "form", "h1", "h2", "h3", "h4", "h5", "h6", "header",
    "hr", "html", "li", "main", "nav", "ol", "p", "pre", "section", "table", "tbody", "td",
    "tfoot", "th", "thead", "tr", "ul", "title",
}  # fmt: skip
KNOWN_TAGS = BLOCK_TAGS | {
    "a", "abbr", "b", "bdi", "bdo", "br", "caption", "center", "cite", "code", "col", "colgroup",
    "data", "del", "dfn", "em", "font", "head", "i", "img", "ins", "kbd", "label", "link",
    "mark", "meta", "picture", "q", "s", "samp", "small", "source", "span", "strike", "strong",
    "sub", "sup", "time", "u", "var", "wbr", "button", "input", "select", "option", "textarea",
    "svg", "video", "audio", "iframe", "canvas", "map", "area", "object", "embed", "base",
} | set(REMOVED_ELEMENTS)  # fmt: skip

_CLASS_RULE = re.compile(r"\.([A-Za-z_][\w-]*)\s*\{([^}]*)\}")
_NAMED = {
    "white": (255, 255, 255),
    "black": (0, 0, 0),
    "transparent": None,
}
OFFSCREEN_PX = -1000


@dataclass(frozen=True)
class RemovedHtml:
    text: str
    kind: str  # "comment", "element" or "css"
    reason: str  # plain language, e.g. "white text on a white background"


@dataclass(frozen=True)
class CleanedHtml:
    text: str  # readable text of what a person would see
    removed: tuple[RemovedHtml, ...]


def _declarations(style: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in style.split(";"):
        if ":" in part:
            name, value = part.split(":", 1)
            out[name.strip().lower()] = value.strip().lower().replace("!important", "").strip()
    return out


def _class_rules(soup: BeautifulSoup) -> dict[str, dict[str, str]]:
    rules: dict[str, dict[str, str]] = {}
    for style in soup.find_all("style"):
        for name, body in _CLASS_RULE.findall(style.get_text()):
            rules.setdefault(name, {}).update(_declarations(body))
    return rules


def _parse_colour(value: str) -> tuple[int, int, int] | None | str:
    """An RGB triple, None for transparent, or "unknown"."""
    value = value.strip()
    if value in _NAMED:
        return _NAMED[value]
    hex_match = re.fullmatch(r"#([0-9a-f]{3,8})", value)
    if hex_match:
        digits = hex_match.group(1)
        if len(digits) in (3, 4):
            digits = "".join(ch * 2 for ch in digits)
        if len(digits) == 8 and digits[6:] == "00":
            return None
        if len(digits) in (6, 8):
            return (int(digits[0:2], 16), int(digits[2:4], 16), int(digits[4:6], 16))
    rgb = re.fullmatch(r"rgba?\(\s*(\d+)[\s,]+(\d+)[\s,]+(\d+)(?:[\s,/]+([\d.]+%?))?\s*\)", value)
    if rgb:
        alpha = rgb.group(4)
        if alpha is not None and float(alpha.rstrip("%")) == 0:
            return None
        return (int(rgb.group(1)), int(rgb.group(2)), int(rgb.group(3)))
    return "unknown"


def _length_px(value: str) -> float | None:
    match = re.match(r"(-?[\d.]+)\s*(px|pt|em|rem|%)?", value)
    if not match:
        return None
    number = float(match.group(1))
    unit = match.group(2) or "px"
    return {"px": 1.0, "pt": 4 / 3, "em": 16.0, "rem": 16.0, "%": 0.16}[unit] * number


def _style_of(tag: Tag, class_rules: dict[str, dict[str, str]]) -> dict[str, str]:
    style: dict[str, str] = {}
    raw: object = tag.get("class") or []
    classes: list[str] = list(raw) if isinstance(raw, list) else str(raw).split()
    for name in classes:
        style.update(class_rules.get(name, {}))
    inline = tag.get("style")
    if isinstance(inline, str):
        style.update(_declarations(inline))
    return style


def _background(style: dict[str, str]) -> tuple[int, int, int] | None | str:
    value = style.get("background-color") or style.get("background")
    if value is None:
        return "unset"
    return _parse_colour(value.split()[0]) if value.split() else "unset"


def _hidden_reason(
    tag: Tag, style: dict[str, str], inherited_bg: tuple[int, int, int] | None
) -> str | None:
    if tag.has_attr("hidden"):
        return "hidden element"
    if style.get("display", "").startswith("none"):
        return "hidden with display:none"
    if style.get("visibility", "") in ("hidden", "collapse"):
        return "invisible (visibility:hidden)"
    opacity = style.get("opacity")
    if opacity is not None:
        try:
            if float(opacity.rstrip("%")) == 0:
                return "fully transparent (opacity:0)"
        except ValueError:
            pass
    if "color" in style:
        colour = _parse_colour(style["color"])
        own_bg = _background(style)
        bg = inherited_bg if own_bg in ("unset", "unknown") else own_bg
        if colour is None:
            return "transparent text"
        if colour != "unknown" and colour == bg:
            return "white text on a white background" if colour == (255, 255, 255) else (
                "text coloured like its background"
            )
    size = style.get("font-size")
    if size is not None:
        px = _length_px(size)
        if px is not None and px <= 1:
            return "tiny text (font size 1px or less)"
    for prop in ("left", "top", "text-indent", "margin-left"):
        if prop in style:
            px = _length_px(style[prop])
            if px is not None and px <= OFFSCREEN_PX:
                return "positioned off-screen"
    return None


def _squash(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def clean_html(html: str) -> CleanedHtml:
    """Remove hidden parts of an HTML document and return what a person would read."""
    soup = BeautifulSoup(html, "html.parser")
    removed: list[RemovedHtml] = []
    class_rules = _class_rules(soup)

    for comment in soup.find_all(string=lambda s: isinstance(s, Comment)):
        if comment.strip():
            removed.append(RemovedHtml(_squash(str(comment)), "comment", "HTML comment"))
        comment.extract()

    for name in REMOVED_ELEMENTS:
        for element in soup.find_all(name):
            text = _squash(element.get_text(" "))
            if text and name != "style":
                removed.append(RemovedHtml(text, "element", f"<{name}> element"))
            element.decompose()

    def visit(tag: Tag, inherited_bg: tuple[int, int, int] | None) -> None:
        for child in list(tag.children):
            if not isinstance(child, Tag):
                continue
            style = _style_of(child, class_rules)
            reason = _hidden_reason(child, style, inherited_bg)
            if reason is not None:
                text = _squash(child.get_text(" "))
                alt = child.get("alt") if child.name == "img" else None
                if text or alt:
                    removed.append(RemovedHtml(text or f"[image: {alt}]", "css", reason))
                child.decompose()
                continue
            bg = _background(style)
            visit(child, inherited_bg if bg in ("unset", "unknown") else bg)  # type: ignore[arg-type]

    visit(soup, (255, 255, 255))
    return CleanedHtml(html_to_text(soup), tuple(removed))


def html_to_text(soup: BeautifulSoup | Tag) -> str:
    """Readable text: links as "text (url)", images as "[image: alt] (src)".

    Tags that aren't HTML (for example a fake <system> marker) are kept as literal text,
    because that is what a model reading the raw source would see.
    """
    parts: list[str] = []

    def walk(node: PageElement) -> None:
        if isinstance(node, NavigableString):
            if not isinstance(node, Comment):
                parts.append(re.sub(r"\s+", " ", str(node)))
            return
        if not isinstance(node, Tag):
            return
        name = node.name.lower()
        if name in ("head", "meta", "link", "base"):
            return
        if name == "br":
            parts.append("\n")
            return
        if name == "img":
            alt = str(node.get("alt") or "").strip()
            src = str(node.get("src") or "").strip()
            parts.append(f"[image: {alt}] ({src})" if src else f"[image: {alt}]")
            return
        block = name in BLOCK_TAGS
        unknown = name not in KNOWN_TAGS and name != "[document]"
        if name == "li":
            parts.append("\n- ")
            block = False
        elif block:
            parts.append("\n")
        if unknown:
            parts.append(f"<{node.name}>")
        for child in node.children:
            walk(child)
        if unknown:
            parts.append(f"</{node.name}>")
        if name == "a":
            href = str(node.get("href") or "").strip()
            label = _squash(node.get_text(" "))
            if href and href != label and not href.startswith("#"):
                parts.append(f" ({href})")
        if block:
            parts.append("\n")

    walk(soup)
    text = "".join(parts)
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    out: list[str] = []
    for line in lines:
        if line or (out and out[-1]):
            out.append(line)
    return "\n".join(out).strip()
