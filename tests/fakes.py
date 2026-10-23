"""Scripted model behaviour for runner and API tests (never the real API)."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from seculayer_demo.gateway import FakeModel, FakeReply, ModelGateway, RecordingStore
from seculayer_demo.gateway.fake import is_judge_request, judge_reply

MODEL = "gpt-5.4-mini-2026-03-17"


def tool_rounds(request: Mapping[str, Any]) -> int:
    return sum(1 for item in request["input"] if item.get("type") == "function_call")


def inbox_script(
    send: Mapping[str, Any] | None,
    *,
    final: str = "You have 5 unread emails.",
    judge: Callable[[str], str] = lambda _body: "benign",
) -> Callable[[Mapping[str, Any]], FakeReply]:
    """List the inbox, then (optionally) send `send`, then reply with `final`."""

    def script(request: Mapping[str, Any]) -> FakeReply:
        if is_judge_request(request):
            return judge_reply(request, judge)
        rounds = tool_rounds(request)
        if rounds == 0:
            return FakeReply(tool_calls=[("list_unread_emails", {})])
        if rounds == 1 and send is not None:
            return FakeReply(tool_calls=[("send_email", dict(send))])
        return FakeReply(text=final)

    return script


def reply_script(text: str, judge: Callable[[str], str] = lambda _b: "benign"):  # type: ignore[no-untyped-def]
    def script(request: Mapping[str, Any]) -> FakeReply:
        if is_judge_request(request):
            return judge_reply(request, judge)
        return FakeReply(text=text)

    return script


def email(to: str, body: str = "Confirmed.", bcc: list[str] | None = None) -> dict[str, Any]:
    return {"to": [to], "cc": None, "bcc": bcc, "subject": "Re: your email", "body": body}


def gateway(mode: str, store: RecordingStore, script: Any = None) -> ModelGateway:
    transport = FakeModel(script) if script is not None else None
    return ModelGateway(mode, store, transport=transport)  # type: ignore[arg-type]
