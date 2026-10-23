"""Turn provider-neutral prompt layouts into Responses API requests (docs/PLAN.md §2, §6.7).

Both sides use the same model and settings: reasoning effort none, default sampling,
store false, parallel tool calls off, at most 1,000 output tokens.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from seculayer.detect.judge import JUDGE_SCHEMA, JudgeMode, judge_input, judge_instructions
from seculayer.types import Message, PromptLayout, Segment

MAX_OUTPUT_TOKENS = 1000
JUDGE_MAX_OUTPUT_TOKENS = 2000  # the judge reasons (effort low), which uses output tokens too


def tool_result_text(message: Message) -> str:
    """A tool result as the model reads it.

    A result built from items with app fields (an email list) is a JSON array of those fields
    plus each item's (possibly cleaned, marked or withheld) body.
    """
    if message.segments and all(segment.meta for segment in message.segments):
        items = [{**dict(segment.meta), "body": segment.text} for segment in message.segments]
        return json.dumps(items, ensure_ascii=False, indent=1)
    return message.text


def input_items(layout: PromptLayout) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for message in layout.messages:
        if message.role in ("developer", "user", "assistant"):
            items.append({"role": message.role, "content": message.text})
        elif message.role == "tool_call":
            items.append(
                {
                    "type": "function_call",
                    "call_id": message.call_id,
                    "name": message.tool_name,
                    "arguments": message.content,
                }
            )
        elif message.role == "tool_result":
            items.append(
                {
                    "type": "function_call_output",
                    "call_id": message.call_id,
                    "output": tool_result_text(message),
                }
            )
    return items


def responses_request(
    layout: PromptLayout, tools: Sequence[Mapping[str, Any]], model: str
) -> dict[str, Any]:
    request: dict[str, Any] = {
        "model": model,
        "input": input_items(layout),
        "reasoning": {"effort": "none"},
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "store": False,
    }
    if tools:
        request["tools"] = [dict(tool) for tool in tools]
        request["tool_choice"] = "auto"
        request["parallel_tool_calls"] = False
    return request


def judge_request(
    items: Sequence[Segment], mode: JudgeMode, ids: Mapping[str, str], model: str
) -> dict[str, Any]:
    return {
        "model": model,
        "input": [
            {"role": "developer", "content": judge_instructions(mode)},
            {"role": "user", "content": judge_input(items, ids)},
        ],
        "reasoning": {"effort": "low"},
        "text": {
            "format": {
                "type": "json_schema",
                "name": "judge_output",
                "schema": JUDGE_SCHEMA,
                "strict": True,
            }
        },
        "max_output_tokens": JUDGE_MAX_OUTPUT_TOKENS,
        "store": False,
    }
