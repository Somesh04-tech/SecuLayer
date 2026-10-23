"""The model gateway: every model call goes through here, in replay, live or record mode
(docs/PLAN.md §6.8)."""

from __future__ import annotations

from seculayer_demo.gateway.budget import BudgetExceeded, TokenBudget
from seculayer_demo.gateway.fake import FakeModel, FakeReply
from seculayer_demo.gateway.openai_client import (
    GatewayMode,
    ModelError,
    ModelGateway,
    ModelResult,
    ReplayMiss,
    Transport,
)
from seculayer_demo.gateway.recordings import Recording, RecordingStore, canonical_json, request_key

__all__ = [
    "BudgetExceeded",
    "FakeModel",
    "FakeReply",
    "GatewayMode",
    "ModelError",
    "ModelGateway",
    "ModelResult",
    "Recording",
    "RecordingStore",
    "ReplayMiss",
    "TokenBudget",
    "Transport",
    "canonical_json",
    "request_key",
]
