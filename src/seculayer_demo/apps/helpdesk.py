"""HelpDesk: Fernway's internal assistant answers from the wiki (docs/PLAN.md §5.6).

Naive choice: the top three retrieved articles go into the developer instructions.
"""

from __future__ import annotations

from typing import Any

from seculayer.types import Message, PromptLayout, Segment, Source
from seculayer_demo.apps.base import ToyApp
from seculayer_demo.apps.retrieval import rank
from seculayer_demo.scenarios import Article

HEADING = "Knowledge-base articles:"


def article_text(article: Article) -> str:
    header = f"## {article.title}\nAuthor: {article.author} · Last edited: {article.edited}"
    return f"{header}\n{article.body}"


def article_segment(article: Article) -> Segment:
    return Segment(
        f"kb:{article.id}",
        Source.EXTERNAL,
        article_text(article),
        format="markdown",
        label=article.title,
        meta=(
            ("author", article.author),
            ("edited", article.edited),
            ("verified", "true" if article.verified else "false"),
        ),
    )


class HelpDeskApp(ToyApp):
    def retrieved(self) -> list[Article]:
        top_k = int(self.scenario.settings.get("top_k", 3))
        return rank(self.case.user_request, self.case.articles, top_k)

    def build_layout(self) -> PromptLayout:
        instructions = self.scenario.developer_instructions
        own, _, _ = instructions.rpartition(HEADING)
        segments: list[Segment] = [
            Segment(
                "developer", Source.DEVELOPER, own.rstrip("\n"), label="Developer instructions"
            ),
            Segment(
                "kb-heading",
                Source.DEVELOPER,
                "\n\n" + HEADING + "\n",
                outside_scaffold=True,
                label="Added by the app",
            ),
        ]
        for index, article in enumerate(self.retrieved()):
            if index:
                segments.append(
                    Segment(f"kb-gap-{index}", Source.DEVELOPER, "\n\n", outside_scaffold=True)
                )
            segments.append(article_segment(article))
        return PromptLayout(
            (
                Message("developer", tuple(segments), label="Developer instructions"),
                Message("user", (self.user_segment(),), label="Dana"),
            )
        )

    def setup(self) -> dict[str, Any]:
        added = set(self.case.added_article_ids)
        return {
            "kind": "helpdesk",
            "question": self.case.user_request,
            "articles": [
                {
                    "id": a.id,
                    "title": a.title,
                    "author": a.author,
                    "edited": a.edited,
                    "verified": a.verified,
                    "body": a.body,
                    "case_specific": a.id in added,
                    "reads": self.reads(article_segment(a)),
                }
                for a in self.retrieved()
            ],
        }
