"""OpenAIJudge: the LLM judge, called through the model gateway (docs/PLAN.md §6.5, §6.7).

It sends the strict JSON schema from seculayer.detect.judge and validates the answer with an
equivalent Pydantic model. A refusal, or output that doesn't fit the schema, makes every item
"suspicious" with the reason "judge unavailable". Replay misses and API errors propagate, so a
missing recording is never mistaken for a verdict.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError

from seculayer.detect.judge import JudgeMode, item_ids, parse_judge_output, unavailable
from seculayer.types import JudgeResult, Segment
from seculayer_demo.gateway import ModelGateway, ModelResult
from seculayer_demo.prompting import judge_request


class JudgeItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    verdict: Literal["benign", "suspicious", "malicious"]
    targets_ai: bool
    requested_action: str | None
    evidence: str | None
    reason: str


class JudgeOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[JudgeItem]


class OpenAIJudge:
    """Implements seculayer.types.InjectionJudge."""

    def __init__(
        self,
        gateway: ModelGateway,
        *,
        model: str,
        seed: str,
        trial: int,
        scenario: str,
        case_id: str = "",
    ) -> None:
        self.gateway = gateway
        self.model = model
        self.seed = seed
        self.trial = trial
        self.scenario = scenario
        self.case_id = case_id
        self.calls: list[ModelResult] = []
        self._count = 0

    def judge(self, items: Sequence[Segment], mode: JudgeMode) -> Sequence[JudgeResult]:
        self._count += 1
        ids = item_ids(items, f"{self.seed}|judge-{self._count}")
        request = judge_request(items, mode, ids, self.model)
        result = self.gateway.call(
            request,
            trial=self.trial,
            scenario=self.scenario,
            case_id=self.case_id,
            purpose="judge",
        )
        self.calls.append(result)
        try:
            parsed = JudgeOutput.model_validate(json.loads(result.output_text))
        except (json.JSONDecodeError, ValidationError):
            return [unavailable(item.id) for item in items]
        return parse_judge_output(parsed.model_dump(), ids)
