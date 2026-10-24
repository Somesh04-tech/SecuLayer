"""Run events, streamed as newline-delimited JSON (docs/PLAN.md §6.9).

Every line is one of these models, told apart by its `type`. The schema-only route
/api/schema/run-event puts the union into OpenAPI, so the frontend's types are generated.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

PartSource = Literal["developer", "user", "external", "injected", "seculayer", "model"]
HiddenKindOut = Literal["css", "comment", "tag_chars", "zero_width"]
Outcome = Literal[
    "hijacked", "resisted", "stopped", "paused", "completed", "false_alarm", "failed", "error"
]
LayerName = Literal["hidden_text", "screening", "hardening", "tool_guard", "output_guard"]
ActionName = Literal[
    "passed", "flagged", "applied", "removed", "withheld", "blocked", "confirm", "off",
    "not_reached", "unavailable",
]  # fmt: skip


class _Event(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AnatomyPart(_Event):
    text: str
    source: PartSource
    segment_id: str | None = None
    hidden: bool = False
    hidden_kind: HiddenKindOut | None = None
    removed: bool = False  # hidden text SecuLayer removed (shown as a struck-through chip)


class AnatomyMessage(_Event):
    role: Literal["developer", "user", "assistant", "tool_call", "tool_result"]
    label: str
    tool_name: str | None = None
    parts: list[AnatomyPart]


class FindingOut(_Event):
    detector: str
    segment_id: str | None
    span: tuple[int, int] | None
    excerpt: str
    score: float | None
    explanation: str
    decision: str | None = None


class ToolCallOut(_Event):
    call_id: str
    name: str
    arguments: dict[str, Any]


class Usage(_Event):
    input_tokens: int
    output_tokens: int
    cached_tokens: int = 0


class Highlight(_Event):
    text: str
    why: str


class Dialog(_Event):
    to: list[str]
    subject: str
    body: str
    highlights: list[Highlight]
    reason: str


class Banner(_Event):
    title: str
    sentence: str


class CheckOut(_Event):
    passed: bool
    detail: str


class Checks(_Event):
    success: CheckOut | None = None
    utility: CheckOut | None = None


class ActionOut(_Event):
    call_id: str
    name: str
    arguments: dict[str, Any]
    status: Literal["done", "blocked", "awaiting_approval", "declined"]


class RunStarted(_Event):
    type: Literal["run.started"] = "run.started"
    run_id: str
    case_id: str
    protected: bool
    model: str
    mode: Literal["replay", "live", "record"]
    trial: int
    trials_available: int
    layers: dict[str, bool]


class LayerStarted(_Event):
    type: Literal["layer.started"] = "layer.started"
    layer: LayerName
    step: int


class LayerVerdict(_Event):
    type: Literal["layer.verdict"] = "layer.verdict"
    layer: LayerName
    step: int
    action: ActionName
    reason: str
    findings: list[FindingOut]
    latency_ms: float
    detail: list[str] = Field(default_factory=list)


class ModelRequest(_Event):
    type: Literal["model.request"] = "model.request"
    call_index: int
    anatomy: list[AnatomyMessage]
    tokens_by_source: dict[str, int]


class ModelResponse(_Event):
    type: Literal["model.response"] = "model.response"
    call_index: int
    output_text: str
    tool_calls: list[ToolCallOut]
    latency_ms: float
    usage: Usage
    recorded: bool
    recorded_at: str | None
    trial: int


class ToolProposed(_Event):
    type: Literal["tool.proposed"] = "tool.proposed"
    call_id: str
    name: str
    arguments: dict[str, Any]


class ToolDecision(_Event):
    type: Literal["tool.decision"] = "tool.decision"
    call_id: str
    action: Literal["allow", "confirm", "block", "approved", "declined"]
    reason: str


class RunPaused(_Event):
    type: Literal["run.paused"] = "run.paused"
    run_id: str
    call_id: str
    dialog: Dialog


class ToolResult(_Event):
    type: Literal["tool.result"] = "tool.result"
    call_id: str
    summary: str


class AttackerEvent(_Event):
    type: Literal["attacker.event"] = "attacker.event"
    channel: Literal["email", "image", "link", "chat"]
    destination: str
    data: str
    zero_click: bool


class RunFinished(_Event):
    type: Literal["run.finished"] = "run.finished"
    outcome: Outcome
    banner: Banner
    stopped_by: LayerName | None
    checks: Checks
    reply_markdown: str
    actions: list[ActionOut]
    cost_usd: float


class RunError(_Event):
    type: Literal["run.error"] = "run.error"
    message: str
    retryable: bool


RunEvent = Annotated[
    RunStarted
    | LayerStarted
    | LayerVerdict
    | ModelRequest
    | ModelResponse
    | ToolProposed
    | ToolDecision
    | RunPaused
    | ToolResult
    | AttackerEvent
    | RunFinished
    | RunError,
    Field(discriminator="type"),
]
RUN_EVENT_ADAPTER: TypeAdapter[RunEvent] = TypeAdapter(RunEvent)


def to_line(event: BaseModel) -> str:
    return event.model_dump_json() + "\n"
