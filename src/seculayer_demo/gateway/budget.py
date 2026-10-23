"""The token budget for live calls and the spend log, data/spend.jsonl (docs/PLAN.md §2, §8.3).

Live and record batches refuse to start, and stop, when the estimate exceeds what remains of
SECULAYER_TOKEN_BUDGET. Each live batch appends one line: date, model, calls, tokens, cost.
"""

from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from pathlib import Path

from seculayer_demo.status import tokens_used


class BudgetExceeded(RuntimeError):
    """A live call or batch would exceed SECULAYER_TOKEN_BUDGET."""


class TokenBudget:
    def __init__(self, limit: int, spend_log: Path) -> None:
        self.limit = limit
        self.spend_log = spend_log
        self._lock = threading.Lock()
        self._pending: dict[str, dict[str, float]] = {}  # model -> calls, tokens, cost

    @property
    def used(self) -> int:
        pending = sum(int(entry["tokens"]) for entry in self._pending.values())
        return tokens_used(self.spend_log) + pending

    @property
    def remaining(self) -> int:
        return max(self.limit - self.used, 0)

    def check(self, estimated_tokens: int) -> None:
        if estimated_tokens > self.remaining:
            raise BudgetExceeded(
                f"needs about {estimated_tokens:,} tokens but only {self.remaining:,} of "
                f"{self.limit:,} remain (SECULAYER_TOKEN_BUDGET)"
            )

    def add(self, model: str, tokens: int, cost: float) -> None:
        with self._lock:
            entry = self._pending.setdefault(model, {"calls": 0, "tokens": 0, "cost": 0.0})
            entry["calls"] += 1
            entry["tokens"] += tokens
            entry["cost"] += cost

    def flush(self, label: str = "") -> int:
        """Append one line per model used since the last flush. Returns the tokens written."""
        with self._lock:
            pending, self._pending = self._pending, {}
        if not pending:
            return 0
        self.spend_log.parent.mkdir(parents=True, exist_ok=True)
        date = datetime.now(UTC).strftime("%Y-%m-%d")
        with self.spend_log.open("a", encoding="utf-8") as handle:
            for model, entry in sorted(pending.items()):
                line = {
                    "date": date,
                    "model": model,
                    "calls": int(entry["calls"]),
                    "tokens": int(entry["tokens"]),
                    "cost_usd": round(entry["cost"], 6),
                    "label": label,
                }
                handle.write(json.dumps(line) + "\n")
        return sum(int(entry["tokens"]) for entry in pending.values())
