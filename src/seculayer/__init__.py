"""SecuLayer: a reusable, layered defense against prompt injection (docs/PLAN.md §6.5).

This package is the library. It must never import seculayer_demo, fastapi or openai
(tests/test_architecture.py enforces this).
"""

from seculayer.engine import SecuLayer, blocked_reply, visible_text, withheld_placeholder
from seculayer.policy import Policy, PolicyError, ScreeningPolicy, ToolPolicy
from seculayer.types import (
    Action,
    ClassifierUnavailable,
    Finding,
    HiddenPiece,
    InjectionClassifier,
    InjectionJudge,
    Inspection,
    JudgeResult,
    LayerId,
    LayerSwitches,
    Message,
    OutputReview,
    PromptLayout,
    RunContext,
    Segment,
    Source,
    ToolCall,
    ToolReview,
    Verdict,
)

__all__ = [
    "Action",
    "ClassifierUnavailable",
    "Finding",
    "HiddenPiece",
    "InjectionClassifier",
    "InjectionJudge",
    "Inspection",
    "JudgeResult",
    "LayerId",
    "LayerSwitches",
    "Message",
    "OutputReview",
    "Policy",
    "PolicyError",
    "PromptLayout",
    "RunContext",
    "ScreeningPolicy",
    "SecuLayer",
    "Segment",
    "Source",
    "ToolCall",
    "ToolPolicy",
    "ToolReview",
    "Verdict",
    "blocked_reply",
    "visible_text",
    "withheld_placeholder",
]
