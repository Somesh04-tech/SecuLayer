"""FakeModel: a scripted stand-in for the OpenAI API, used by every test and by development.

It returns responses in the Responses API's JSON shape, so the gateway, recordings and replay
run exactly as they would with the real model, and nothing touches the network.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class FakeReply:
    text: str = ""
    tool_calls: Sequence[tuple[str, Mapping[str, Any]]] = field(default_factory=tuple)
    status: str = "completed"


Script = Callable[[Mapping[str, Any]], FakeReply]


class FakeModel:
    """Implements gateway.Transport. `script` decides the reply for each request.

    Pass a callable (request -> FakeReply) or a list of replies used in order.
    """

    sdk_version = "fake"

    def __init__(self, script: Script | Sequence[FakeReply]) -> None:
        if callable(script):
            self._script: Script = script
        else:
            replies = list(script)

            def next_reply(_request: Mapping[str, Any]) -> FakeReply:
                if not replies:
                    raise AssertionError("FakeModel ran out of scripted replies")
                return replies.pop(0)

            self._script = next_reply
        self.requests: list[dict[str, Any]] = []

    def create(self, request: Mapping[str, Any]) -> dict[str, Any]:
        self.requests.append(dict(request))
        reply = self._script(request)
        digest = hashlib.sha256(
            json.dumps(request, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()
        output: list[dict[str, Any]] = []
        if reply.text:
            output.append(
                {
                    "type": "message",
                    "id": f"msg_{digest[:12]}",
                    "role": "assistant",
                    "status": "completed",
                    "content": [{"type": "output_text", "text": reply.text, "annotations": []}],
                }
            )
        for index, (name, arguments) in enumerate(reply.tool_calls):
            output.append(
                {
                    "type": "function_call",
                    "id": f"fc_{digest[:12]}_{index}",
                    "call_id": f"call_{digest[:16]}_{index}",
                    "name": name,
                    "arguments": json.dumps(arguments),
                    "status": "completed",
                }
            )
        text_in = json.dumps(request.get("input", ""), ensure_ascii=False)
        output_size = len(reply.text) + sum(len(json.dumps(a)) for _, a in reply.tool_calls)
        return {
            "id": f"resp_{digest[:16]}",
            "object": "response",
            "model": request.get("model"),
            "status": reply.status,
            "output": output,
            "usage": {
                "input_tokens": max(1, len(text_in) // 4),
                "input_tokens_details": {"cached_tokens": 0},
                "output_tokens": max(1, output_size // 4),
                "output_tokens_details": {"reasoning_tokens": 0},
                "total_tokens": max(1, len(text_in) // 4) + max(1, output_size // 4),
            },
        }


def is_judge_request(request: Mapping[str, Any]) -> bool:
    text = request.get("text")
    return isinstance(text, Mapping) and isinstance(text.get("format"), Mapping)


def judge_reply(request: Mapping[str, Any], verdict: Callable[[str], str]) -> FakeReply:
    """A FakeReply for a judge request: `verdict(item_body)` gives each item's verdict."""
    import re

    user = next(
        (str(m.get("content", "")) for m in request.get("input", []) if m.get("role") == "user"),
        "",
    )
    items = []
    for item_id, body in re.findall(r"<<ITEM id=(\w+)>>\n(.*?)\n<<END ITEM id=\1>>", user, re.S):
        decoded = json.loads(body)
        result = verdict(decoded)
        items.append(
            {
                "id": item_id,
                "verdict": result,
                "targets_ai": result != "benign",
                "requested_action": None,
                "evidence": None,
                "reason": f"scripted {result}",
            }
        )
    return FakeReply(text=json.dumps({"items": items}))
