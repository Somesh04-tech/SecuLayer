"""The model gateway: canonical keys, the three modes, trial fallback, budget and pricing."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from seculayer_demo.gateway import (
    BudgetExceeded,
    FakeModel,
    FakeReply,
    ModelGateway,
    RecordingStore,
    ReplayMiss,
    TokenBudget,
    request_key,
)
from seculayer_demo.gateway.pricing import cost_usd, price_for
from seculayer_demo.status import tokens_used

REQUEST = {
    "model": "gpt-5.4-mini-2026-03-17",
    "input": [{"role": "user", "content": "Hello"}],
    "reasoning": {"effort": "none"},
    "max_output_tokens": 1000,
    "store": False,
}


def test_canonical_key_ignores_key_order_item_ids_and_extra_fields() -> None:
    reordered = dict(reversed(list(REQUEST.items())))
    with_ids = {
        **REQUEST,
        "input": [{"id": "msg_1", "role": "user", "content": "Hello"}],
        "metadata": {"x": 1},
    }
    assert request_key(REQUEST) == request_key(reordered) == request_key(with_ids)
    changed = {**REQUEST, "input": [{"role": "user", "content": "Hello!"}]}
    assert request_key(changed) != request_key(REQUEST)


def test_record_then_replay(tmp_path: Path) -> None:
    store = RecordingStore(tmp_path)
    fake = FakeModel([FakeReply(text="Hi there"), FakeReply(text="Second trial")])
    recorder = ModelGateway("record", store, transport=fake)
    first = recorder.call(REQUEST, trial=1, scenario="support", case_id="support.x")
    again = recorder.call(REQUEST, trial=1, scenario="support")  # already recorded: no call
    second = recorder.call(REQUEST, trial=2, scenario="support")
    assert len(fake.requests) == 2 and recorder.live_calls == 2
    assert first.output_text == again.output_text == "Hi there"
    assert second.output_text == "Second trial"
    assert (tmp_path / "gpt-5.4-mini-2026-03-17" / "support.jsonl.gz").is_file()

    replay = ModelGateway("replay", RecordingStore(tmp_path))
    played = replay.call(REQUEST, trial=2, scenario="support")
    assert played.output_text == "Second trial" and played.recorded
    assert played.trials_available == 2 and played.recorded_at


def test_replay_miss(tmp_path: Path) -> None:
    replay = ModelGateway("replay", RecordingStore(tmp_path))
    with pytest.raises(ReplayMiss):
        replay.call(REQUEST, trial=1, scenario="support")


def test_a_variant_recorded_once_falls_back_to_trial_one(tmp_path: Path) -> None:
    store = RecordingStore(tmp_path)
    ModelGateway("record", store, transport=FakeModel([FakeReply(text="only")])).call(
        REQUEST, trial=1, scenario="support"
    )
    result = ModelGateway("replay", RecordingStore(tmp_path)).call(
        REQUEST, trial=3, scenario="support"
    )
    assert result.output_text == "only" and result.trial == 1 and result.trials_available == 1


def test_live_mode_saves_nothing(tmp_path: Path) -> None:
    store = RecordingStore(tmp_path)
    live = ModelGateway("live", store, transport=FakeModel([FakeReply(text="x")]))
    assert not live.call(REQUEST, trial=1, scenario="support").recorded
    assert len(store) == 0 and not any(tmp_path.iterdir())


def test_live_modes_need_a_transport(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        ModelGateway("live", RecordingStore(tmp_path))


def test_budget_refuses_and_logs_spend(tmp_path: Path) -> None:
    log = tmp_path / "spend.jsonl"
    budget = TokenBudget(5_000, log)
    gateway = ModelGateway(
        "live",
        RecordingStore(tmp_path / "rec"),
        transport=FakeModel([FakeReply(text="ok")] * 3),
        budget=budget,
    )
    gateway.call(REQUEST, trial=1, scenario="support")
    assert budget.used > 0
    written = budget.flush(label="test")
    line = json.loads(log.read_text().splitlines()[0])
    assert line["model"] == "gpt-5.4-mini-2026-03-17" and line["calls"] == 1
    assert line["tokens"] == written == tokens_used(log)
    budget.limit = tokens_used(log) + 100  # less than one call's estimate remains
    with pytest.raises(BudgetExceeded):
        gateway.call(
            {**REQUEST, "input": [{"role": "user", "content": "x"}]}, trial=1, scenario="support"
        )


def test_pricing() -> None:
    assert price_for("gpt-5.4-mini-2026-03-17").input == 0.75  # type: ignore[union-attr]
    assert price_for("gpt-5.4-2026-03-05").output == 15.00  # type: ignore[union-attr]
    assert price_for("other-model") is None
    assert cost_usd("gpt-5.4-mini-2026-03-17", 1_000_000, 0) == 0.75
    assert cost_usd("gpt-5.4-mini-2026-03-17", 1_000_000, 1_000_000, cached_tokens=1_000_000) == (
        pytest.approx(0.075 + 4.5)
    )
