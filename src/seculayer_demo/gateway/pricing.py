"""List prices per million tokens, from OpenAI's model pages on 2026-10-23 (docs/PLAN.md §7.3)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Price:
    input: float
    cached_input: float
    output: float


PRICES: dict[str, Price] = {
    "gpt-5.4-mini": Price(0.75, 0.075, 4.50),
    "gpt-5.4": Price(2.50, 0.25, 15.00),
}


def price_for(model: str) -> Price | None:
    """The price of a model or snapshot: the longest family name the model starts with."""
    matches = [name for name in PRICES if model == name or model.startswith(name + "-")]
    return PRICES[max(matches, key=len)] if matches else None


def cost_usd(model: str, input_tokens: int, output_tokens: int, cached_tokens: int = 0) -> float:
    price = price_for(model)
    if price is None:
        return 0.0
    uncached = max(input_tokens - cached_tokens, 0)
    total = (
        uncached * price.input + cached_tokens * price.cached_input + output_tokens * price.output
    )
    return round(total / 1_000_000, 8)
