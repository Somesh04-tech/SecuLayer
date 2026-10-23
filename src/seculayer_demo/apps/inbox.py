"""Inbox assistant: lists Dana's unread email and sends email for her (docs/PLAN.md §5.4).

Naive choices: tool results carry the raw email HTML, and send_email runs immediately.
"""

from __future__ import annotations

import json
from typing import Any

from seculayer.types import Segment, Source, ToolCall
from seculayer_demo.apps.base import ToolExecution, ToyApp
from seculayer_demo.apps.tools import LIST_UNREAD_EMAILS, SEND_EMAIL, message_id
from seculayer_demo.scenarios import Email


def email_segment(email: Email) -> Segment:
    return Segment(
        id=f"email:{email.id}",
        source=Source.EXTERNAL,
        text=email.body,
        format=email.format,
        label=email.subject,
        private=email.private,
        meta=(
            ("id", email.id),
            ("from", email.sender),
            ("subject", email.subject),
            ("received", email.received),
        ),
    )


class InboxApp(ToyApp):
    def tools(self) -> tuple[dict[str, Any], ...]:
        return (LIST_UNREAD_EMAILS, SEND_EMAIL)

    def emails(self) -> list[Email]:
        """Unread email, newest first: the case's fifth email, then the four standing ones."""
        inbox = list(self.scenario.emails)
        if self.case.extra_email is not None:
            inbox.append(self.case.extra_email)
        return sorted(inbox, key=lambda e: e.received, reverse=True)

    def execute_tool(self, call: ToolCall) -> ToolExecution:
        if call.name == "list_unread_emails":
            emails = self.emails()
            return ToolExecution(
                tuple(email_segment(e) for e in emails), f"Listed {len(emails)} unread emails"
            )
        if call.name == "send_email":
            args = call.arguments
            result = {"status": "sent", "message_id": message_id(self.seed, call.call_id)}
            segment = Segment(
                f"tool:send_email:{call.call_id}",
                Source.EXTERNAL,
                json.dumps(result),
                format="json",
                label="send_email result",
            )
            to = [*(args.get("to") or []), *(args.get("cc") or []), *(args.get("bcc") or [])]
            summary = f"Sent email to {', '.join(str(a) for a in to) or 'nobody'}"
            return ToolExecution((segment,), summary, sent=dict(args))
        return super().execute_tool(call)

    def setup(self) -> dict[str, Any]:
        return {
            "kind": "inbox",
            "emails": [
                {
                    "id": e.id,
                    "from": e.sender,
                    "subject": e.subject,
                    "received": e.received,
                    "body": e.body,
                    "format": e.format,
                    "private": e.private,
                    "outside": True,
                    "case_specific": self.case.extra_email is not None
                    and e.id == self.case.extra_email.id,
                    "reads": self.reads(email_segment(e)),
                }
                for e in self.emails()
            ],
        }
