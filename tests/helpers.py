"""Shared test doubles: a classifier with fixed scores and a scripted judge."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Literal

from seculayer.types import ClassifierUnavailable, JudgeResult, JudgeUnavailable, Segment

Verdict = Literal["benign", "suspicious", "malicious"]


class FixedClassifier:
    """Scores by substring: the first matching key wins; otherwise `default`."""

    name = "fixed"

    def __init__(self, scores: dict[str, float] | None = None, default: float | None = 0.01):
        self.scores = scores or {}
        self.default = default
        self.calls: list[str] = []

    def score(self, text: str) -> float:
        self.calls.append(text)
        for needle, value in self.scores.items():
            if needle in text:
                return value
        if self.default is None:
            raise ClassifierUnavailable("no score")
        return self.default


class ScriptedJudge:
    def __init__(
        self, verdict: Callable[[Segment], Verdict] | None = None, *, unavailable: bool = False
    ) -> None:
        self.verdict = verdict or (lambda _segment: "benign")
        self.unavailable = unavailable
        self.calls: list[tuple[list[str], str]] = []

    def judge(
        self, items: Sequence[Segment], mode: Literal["outside", "user"]
    ) -> list[JudgeResult]:
        self.calls.append(([s.id for s in items], mode))
        if self.unavailable:
            raise JudgeUnavailable("down")
        return [
            JudgeResult(
                s.id,
                self.verdict(s),
                self.verdict(s) != "benign",
                None,
                None,
                f"scripted {self.verdict(s)}",
            )
            for s in items
        ]
