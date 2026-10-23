"""Support chat: "Fern", the store's support bot. No tools; one customer message
(docs/PLAN.md §5.3). The staff code sits in the developer instructions."""

from __future__ import annotations

from typing import Any

from seculayer_demo.apps.base import ToyApp


class SupportChatApp(ToyApp):
    def setup(self) -> dict[str, Any]:
        return {"kind": "chat", "message": self.case.user_request}
