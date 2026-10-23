"""The four toy apps, each built the naive way many real apps are (docs/PLAN.md §5.2-5.6)."""

from __future__ import annotations

from seculayer_demo.apps.base import ToolExecution, ToyApp
from seculayer_demo.apps.helpdesk import HelpDeskApp
from seculayer_demo.apps.inbox import InboxApp
from seculayer_demo.apps.page_summarizer import PageSummarizerApp
from seculayer_demo.apps.support_chat import SupportChatApp
from seculayer_demo.scenarios import Case, Scenario

APPS: dict[str, type[ToyApp]] = {
    "support": SupportChatApp,
    "inbox": InboxApp,
    "page": PageSummarizerApp,
    "helpdesk": HelpDeskApp,
}


def make_app(scenario: Scenario, case: Case, *, seed: str = "") -> ToyApp:
    return APPS[scenario.app](scenario, case, seed=seed)


__all__ = ["APPS", "ToolExecution", "ToyApp", "make_app"]
