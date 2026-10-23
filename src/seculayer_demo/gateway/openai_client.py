"""The model gateway and the OpenAI Responses API transport (docs/PLAN.md §6.8).

Modes:
- replay (the default) looks up every call in the recordings; a missing key raises ReplayMiss.
- live calls the model and saves nothing.
- record calls the model only for keys that aren't recorded yet, and saves the result.

Every live call has a 60 s timeout, retries twice with backoff on 429 and 5xx errors (the
SDK's own retry), and checks the token budget first. The key is never logged or recorded.
"""

from __future__ import annotations

import json
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal, Protocol

from seculayer_demo.gateway.budget import TokenBudget
from seculayer_demo.gateway.pricing import cost_usd
from seculayer_demo.gateway.recordings import Recording, RecordingStore, request_key

GatewayMode = Literal["replay", "live", "record"]
TIMEOUT_S = 60.0
MAX_RETRIES = 2
ESTIMATED_TOKENS_PER_CALL = 3_000  # a conservative per-call budget check (about 1,700 typical)


class ReplayMiss(LookupError):
    """No recording for this request and trial. The UI shows it as "not recorded"."""

    def __init__(self, key: str, trial: int, purpose: str) -> None:
        super().__init__(f"no recording for this {purpose} call (trial {trial})")
        self.key = key
        self.trial = trial
        self.purpose = purpose


class ModelError(RuntimeError):
    """The model didn't respond (timeout, rate limit, server error after retries)."""

    def __init__(self, message: str, *, retryable: bool = True) -> None:
        super().__init__(message)
        self.retryable = retryable


class Transport(Protocol):
    """Something that sends a Responses API request and returns the response as JSON."""

    sdk_version: str

    def create(self, request: Mapping[str, Any]) -> dict[str, Any]: ...


@dataclass(frozen=True)
class ParsedToolCall:
    call_id: str
    name: str
    arguments: dict[str, Any]
    raw_arguments: str


@dataclass(frozen=True)
class ModelResult:
    output_text: str
    tool_calls: tuple[ParsedToolCall, ...]
    usage: Mapping[str, int]
    latency_ms: float
    recorded: bool  # played back from a recording
    recorded_at: str | None
    trial: int  # the trial actually used (a variant recorded once falls back to trial 1)
    trials_available: int
    cost_usd: float
    model: str
    status: str = "completed"
    raw: Mapping[str, Any] = field(default_factory=dict)


def parse_response(response: Mapping[str, Any]) -> tuple[str, tuple[ParsedToolCall, ...]]:
    """The output text and function calls of a Responses API response (as JSON)."""
    texts: list[str] = []
    calls: list[ParsedToolCall] = []
    for item in response.get("output") or []:
        kind = item.get("type")
        if kind == "message":
            for part in item.get("content") or []:
                if part.get("type") == "output_text":
                    texts.append(str(part.get("text", "")))
                elif part.get("type") == "refusal":
                    texts.append(str(part.get("refusal", "")))
        elif kind == "function_call":
            raw = str(item.get("arguments") or "{}")
            try:
                arguments = json.loads(raw)
            except json.JSONDecodeError:
                arguments = {}
            calls.append(
                ParsedToolCall(
                    call_id=str(item.get("call_id", "")),
                    name=str(item.get("name", "")),
                    arguments=arguments if isinstance(arguments, dict) else {},
                    raw_arguments=raw,
                )
            )
    return "".join(texts), tuple(calls)


def usage_of(response: Mapping[str, Any]) -> dict[str, int]:
    usage = response.get("usage") or {}
    details = usage.get("input_tokens_details") or {}
    return {
        "input_tokens": int(usage.get("input_tokens") or 0),
        "output_tokens": int(usage.get("output_tokens") or 0),
        "cached_tokens": int(details.get("cached_tokens") or 0),
    }


class OpenAITransport:
    """Calls the OpenAI Responses API with the official SDK."""

    def __init__(self, api_key: str) -> None:
        import openai

        self.sdk_version = openai.__version__
        self._client = openai.OpenAI(api_key=api_key, timeout=TIMEOUT_S, max_retries=MAX_RETRIES)

    def create(self, request: Mapping[str, Any]) -> dict[str, Any]:
        import openai

        try:
            response = self._client.responses.create(**request)
        except openai.APITimeoutError:
            raise ModelError(
                f"The model didn't respond (timed out after {TIMEOUT_S:.0f} s)."
            ) from None
        except openai.RateLimitError:
            raise ModelError(
                "The model is rate-limited right now. Try again in a minute."
            ) from None
        except openai.APIConnectionError:
            raise ModelError("Couldn't reach the OpenAI API. Check the network.") from None
        except openai.APIStatusError as error:
            # The message never includes the key; status and the API's own message are enough.
            raise ModelError(
                f"The OpenAI API returned {error.status_code}: {error.message}",
                retryable=error.status_code >= 500,
            ) from None
        dumped: dict[str, Any] = response.model_dump(mode="json")
        return dumped


class ModelGateway:
    def __init__(
        self,
        mode: GatewayMode,
        store: RecordingStore,
        *,
        transport: Transport | None = None,
        budget: TokenBudget | None = None,
    ) -> None:
        if mode in ("live", "record") and transport is None:
            raise ValueError(
                f"{mode} mode needs a transport (an OpenAI key, or FakeModel in tests)"
            )
        self.mode = mode
        self.store = store
        self.transport = transport
        self.budget = budget
        self.live_calls = 0

    def trials_available(self, request: Mapping[str, Any]) -> int:
        return len(self.store.trials(request_key(request)))

    def call(
        self,
        request: Mapping[str, Any],
        *,
        trial: int,
        scenario: str,
        case_id: str = "",
        purpose: str = "app",
    ) -> ModelResult:
        key = request_key(request)
        model = str(request.get("model", ""))
        if self.mode in ("replay", "record"):
            found = self._lookup(key, trial)
            if found is not None:
                recording, used_trial = found
                return self._result(
                    recording.response,
                    recording.latency_ms,
                    model,
                    recorded=True,
                    recorded_at=recording.recorded_at,
                    trial=used_trial,
                    trials=len(self.store.trials(key)),
                )
            if self.mode == "replay":
                raise ReplayMiss(key, trial, purpose)

        assert self.transport is not None
        if self.budget is not None:
            self.budget.check(ESTIMATED_TOKENS_PER_CALL)
        start = time.perf_counter()
        response = self.transport.create(dict(request))
        latency = round((time.perf_counter() - start) * 1000, 1)
        self.live_calls += 1
        usage = usage_of(response)
        cost = cost_usd(
            model, usage["input_tokens"], usage["output_tokens"], usage["cached_tokens"]
        )
        if self.budget is not None:
            self.budget.add(model, usage["input_tokens"] + usage["output_tokens"], cost)
        recorded_at = None
        if self.mode == "record":
            recorded_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
            self.store.add(
                Recording(
                    key=key,
                    trial=trial,
                    model=model,
                    purpose=purpose,
                    case_id=case_id,
                    request=dict(request),
                    response=response,
                    latency_ms=latency,
                    usage=usage,
                    sdk_version=self.transport.sdk_version,
                    recorded_at=recorded_at,
                ),
                scenario,
            )
        return self._result(
            response,
            latency,
            model,
            recorded=self.mode == "record",
            recorded_at=recorded_at,
            trial=trial,
            trials=len(self.store.trials(key)),
        )

    def _lookup(self, key: str, trial: int) -> tuple[Recording, int] | None:
        recording = self.store.get(key, trial)
        if recording is not None:
            return recording, trial
        # A variant recorded once falls back to trial 1 (only in replay; record fills it in).
        if self.mode == "replay" and trial > 1 and self.store.trials(key) == [1]:
            fallback = self.store.get(key, 1)
            if fallback is not None:
                return fallback, 1
        return None

    def _result(
        self,
        response: Mapping[str, Any],
        latency: float,
        model: str,
        *,
        recorded: bool,
        recorded_at: str | None,
        trial: int,
        trials: int,
    ) -> ModelResult:
        text, calls = parse_response(response)
        usage = usage_of(response)
        return ModelResult(
            output_text=text,
            tool_calls=calls,
            usage=usage,
            latency_ms=latency,
            recorded=recorded,
            recorded_at=recorded_at,
            trial=trial,
            trials_available=trials,
            cost_usd=cost_usd(
                model, usage["input_tokens"], usage["output_tokens"], usage["cached_tokens"]
            ),
            model=model,
            status=str(response.get("status") or "completed"),
            raw=response,
        )
