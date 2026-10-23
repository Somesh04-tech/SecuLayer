"""Mock mail tools for the inbox assistant. Nothing is ever sent (docs/PLAN.md §5.4)."""

from __future__ import annotations

from typing import Any

from seculayer.detect.judge import derived_id

LIST_UNREAD_EMAILS: dict[str, Any] = {
    "type": "function",
    "name": "list_unread_emails",
    "description": "List Dana's unread emails, newest first. Each has an id, sender, subject, "
    "received time and the raw body.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    },
    "strict": True,
}

SEND_EMAIL: dict[str, Any] = {
    "type": "function",
    "name": "send_email",
    "description": "Send an email from Dana's account.",
    "parameters": {
        "type": "object",
        "properties": {
            "to": {"type": "array", "items": {"type": "string"}},
            "cc": {"type": ["array", "null"], "items": {"type": "string"}},
            "bcc": {"type": ["array", "null"], "items": {"type": "string"}},
            "subject": {"type": "string"},
            "body": {"type": "string"},
        },
        "required": ["to", "cc", "bcc", "subject", "body"],
        "additionalProperties": False,
    },
    "strict": True,
}


def message_id(seed: str, call_id: str) -> str:
    """A deterministic mock message ID, so replays match (docs/PLAN.md §6.8)."""
    return f"<{derived_id(seed, 'message-id', call_id, length=16)}@mail.fernway.example>"
