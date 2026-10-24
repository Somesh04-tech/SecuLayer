"""The token budget for live calls and the spend log, data/spend.jsonl (docs/PLAN.md §2, §8.3).

Live and record batches refuse to start, and stop, when the estimate exceeds what remains of
SECULAYER_TOKEN_BUDGET. Each live batch appends one line: date, model, calls, tokens, cost.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from seculayer_demo.status import tokens_used

DAILY_LIMITS = {"gpt-5.4-mini": 2_500_000, "gpt-5.4": 250_000}


def daily_limit(model: str) -> int | None:
    return next((limit for prefix, limit in DAILY_LIMITS.items() if model.startswith(prefix)), None)


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

    def usage_by_model(self, *, today_only: bool = False) -> dict[str, int]:
        usage: dict[str, int] = {}
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        if self.spend_log.is_file():
            for line in self.spend_log.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                entry = json.loads(line)
                if today_only and entry["date"] != today:
                    continue
                model = entry["model"]
                usage[model] = usage.get(model, 0) + int(entry["tokens"])
        for model, entry in self._pending.items():
            usage[model] = usage.get(model, 0) + int(entry["tokens"])
        return usage

    def check(self, estimated_tokens: int, model: str | None = None) -> None:
        if estimated_tokens > self.remaining:
            raise BudgetExceeded(
                f"needs about {estimated_tokens:,} tokens but only {self.remaining:,} of "
                f"{self.limit:,} remain (SECULAYER_TOKEN_BUDGET)"
            )
        if model is not None and (limit := daily_limit(model)) is not None:
            used = self.usage_by_model(today_only=True).get(model, 0)
            if used + estimated_tokens > limit:
                raise BudgetExceeded(
                    f"{model} needs about {estimated_tokens:,} tokens but only "
                    f"{max(limit - used, 0):,} of its {limit:,}/day remain (UTC)"
                )

    def preflight(self, estimates: dict[str, tuple[int, int]], log: Callable[[str], None]) -> None:
        """Print calls, tokens and spend for EVERY model before checking a live batch."""
        emit = log
        all_time = self.usage_by_model()
        today = self.usage_by_model(today_only=True)
        for model in sorted(set(estimates) | set(all_time) | set(DAILY_LIMITS)):
            # Only show snapshots, rather than the family names used by DAILY_LIMITS.
            if model in DAILY_LIMITS and model not in estimates and model not in all_time:
                continue
            calls, tokens = estimates.get(model, (0, 0))
            limit = daily_limit(model)
            emit(
                f"  {model}: estimated {calls:,} calls / {tokens:,} tokens; "
                f"used {all_time.get(model, 0):,} total, {today.get(model, 0):,} today "
                f"/ {limit or 0:,} daily (UTC)."
            )
        emit(f"  Total used {self.used:,} / {self.limit:,}; remaining {self.remaining:,}.")
        self.check(sum(tokens for _, tokens in estimates.values()))
        for model, (_, tokens) in estimates.items():
            self.check(tokens, model)

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
