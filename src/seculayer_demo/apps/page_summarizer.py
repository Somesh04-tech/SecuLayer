"""Page summarizer: Dana's browser sidebar assistant (docs/PLAN.md §5.5).

Naive choice: the page's raw HTML, hidden parts and comments included, goes into the user's
message: `{request}\n\nURL: {url}\n\nPage HTML:\n{html}`.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlsplit

from seculayer.types import Message, PromptLayout, Segment, Source
from seculayer_demo.apps.base import ToyApp

NOTES = re.compile(r'Dana\'s notes, for context: "([^"]*)"')


class PageSummarizerApp(ToyApp):
    def page_segment(self) -> Segment:
        page = self.case.page
        assert page is not None
        parts = urlsplit(page.url)
        title = re.search(r"<title>(.*?)</title>", page.html, re.S)
        return Segment(
            f"page:{parts.hostname}{parts.path}",
            Source.EXTERNAL,
            page.html,
            format="html",
            label=title.group(1).strip() if title else page.url,
        )

    def build_layout(self) -> PromptLayout:
        page = self.case.page
        assert page is not None
        template = str(self.scenario.settings.get("user_template", "{request}\n\n{html}"))
        before_html = template.split("{html}")[0]
        request_part, _, scaffold = before_html.partition("{request}")
        scaffold = scaffold.format(url=page.url)
        segments = (
            Segment("user", Source.USER, request_part + self.case.user_request, label="Dana"),
            Segment(
                "page-scaffold",
                Source.DEVELOPER,
                scaffold,
                outside_scaffold=True,
                label="Added by the app",
            ),
            self.page_segment(),
        )
        return PromptLayout(
            (
                Message("developer", (self.developer_segment(),), label="Developer instructions"),
                Message("user", segments, label="Dana"),
            )
        )

    def setup(self) -> dict[str, Any]:
        page = self.case.page
        assert page is not None
        notes = NOTES.search(self.scenario.developer_instructions)
        return {
            "kind": "page",
            "url": page.url,
            "html": page.html,
            "title": self.page_segment().label,
            "notes": notes.group(1) if notes else "",
        }
