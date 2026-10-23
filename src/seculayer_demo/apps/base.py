"""What every toy app provides: its naive prompt layout, its tools and their mock execution."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from seculayer.types import Message, PromptLayout, Segment, Source, ToolCall
from seculayer_demo.scenarios import Case, Scenario


@dataclass(frozen=True)
class ToolExecution:
    segments: tuple[Segment, ...]  # the result as outside content (docs/PLAN.md §6.5)
    summary: str  # one line for the UI: "Listed 5 unread emails"
    sent: Mapping[str, Any] | None = None  # an outbound message the mock tool "sent"


@dataclass
class ToyApp:
    """A toy app. Subclasses build the layout exactly as their scenario describes."""

    scenario: Scenario
    case: Case
    seed: str = ""
    tool_specs: Sequence[Mapping[str, Any]] = field(default_factory=tuple)

    def __init__(self, scenario: Scenario, case: Case, *, seed: str = "") -> None:
        self.scenario = scenario
        self.case = case
        self.seed = seed
        self.tool_specs = self.tools()

    def tools(self) -> tuple[Mapping[str, Any], ...]:
        return ()

    def developer_segment(self) -> Segment:
        return Segment(
            "developer",
            Source.DEVELOPER,
            self.scenario.developer_instructions,
            label="Developer instructions",
        )

    def user_segment(self) -> Segment:
        return Segment(
            "user", Source.USER, self.case.user_request, label=self.scenario.user_name.capitalize()
        )

    def build_layout(self) -> PromptLayout:
        """The naive layout: developer instructions, then the user's request."""
        return PromptLayout(
            (
                Message("developer", (self.developer_segment(),), label="Developer instructions"),
                Message("user", (self.user_segment(),), label=self.scenario.user_name.capitalize()),
            )
        )

    def execute_tool(self, call: ToolCall) -> ToolExecution:
        raise ValueError(f"{self.scenario.app} has no tool {call.name!r}")

    def setup(self) -> dict[str, Any]:
        """The setup content the Lab shows (emails, pages, articles, notes)."""
        return {}

    def reads(self, segment: Segment) -> list[dict[str, Any]]:
        """What the model reads of an outside item, as parts: the raw text the naive app sends,
        with hidden and injected spans marked (for "Show what the AI reads")."""
        from seculayer_demo.anatomy import segment_parts

        return [
            part.model_dump(exclude={"segment_id", "removed"})
            for part in segment_parts(segment, self.case.injected_text)
        ]
