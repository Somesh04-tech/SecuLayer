"""Shared run machinery for the server: the gateway, the classifier and paused runs."""

from __future__ import annotations

import threading
import time
import uuid
from collections.abc import Generator, Iterator
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel

from seculayer.detect.prompt_guard import CachedClassifier, PromptGuardClassifier, ScoreCache
from seculayer.engine import SecuLayer
from seculayer.types import LayerSwitches
from seculayer_demo.config import Settings
from seculayer_demo.gateway import ModelGateway, RecordingStore, TokenBudget
from seculayer_demo.gateway.openai_client import GatewayMode, OpenAITransport, Transport
from seculayer_demo.runner import AgentRunner, RunRequest
from seculayer_demo.server.events import RunFinished, RunPaused, RunStarted, to_line

PAUSED_TTL_S = 600.0  # paused runs are kept for 10 minutes (docs/PLAN.md §6.9)
RunGenerator = Generator[BaseModel, bool | None, None]


@dataclass(frozen=True)
class RecordedRuns:
    """The unprotected runs recorded for an attack: how many, and which were hijacked."""

    trials: int
    hijacked: tuple[int, ...]

    @property
    def default_trial(self) -> int:
        # The first hijacked trial, so replay shows the attack working (docs/PLAN.md §6.8).
        return self.hijacked[0] if self.hijacked else 1


def classifier_cache_path(settings: Settings) -> Path:
    return settings.data_dir / "cache" / "classifier_scores.jsonl"


def make_classifier(settings: Settings) -> CachedClassifier:
    """Cache first, then the live model (when downloaded), then recorded scores."""
    model = PromptGuardClassifier(settings.classifier_path)
    return CachedClassifier(
        ScoreCache(classifier_cache_path(settings)), model if model.available else None
    )


def warm_classifier(classifier: CachedClassifier) -> int:
    """Score every curated input in advance (screening with the cleaner on and off)."""
    from seculayer_demo.apps import make_app
    from seculayer_demo.scenarios import all_cases, find_case

    if not classifier.model_available:
        return 0
    scored = 0
    for case in all_cases():
        scenario, _ = find_case(case.id)
        app = make_app(scenario, case, seed=case.id)
        segments = list(app.build_layout().inspectable_segments())
        if scenario.app == "inbox":
            from seculayer.types import ToolCall

            segments += app.execute_tool(ToolCall("warm", "list_unread_emails", {})).segments
        for hidden_text in (True, False):
            layers = LayerSwitches(hidden_text=hidden_text, judge=False)
            guard = SecuLayer(scenario.policy, layers=layers, classifier=classifier, seed=case.id)
            before = len(classifier.cache)
            guard.inspect(segments, guard.new_context(case.user_request))
            scored += len(classifier.cache) - before
    return scored


@dataclass
class PausedRun:
    generator: RunGenerator
    runner: AgentRunner
    expires_at: float


class PausedRuns:
    def __init__(self, ttl_s: float = PAUSED_TTL_S) -> None:
        self.ttl_s = ttl_s
        self._lock = threading.Lock()
        self._runs: dict[str, PausedRun] = {}

    def put(self, run_id: str, generator: RunGenerator, runner: AgentRunner) -> None:
        with self._lock:
            self._expire()
            self._runs[run_id] = PausedRun(generator, runner, time.monotonic() + self.ttl_s)

    def take(self, run_id: str) -> PausedRun | None:
        with self._lock:
            self._expire()
            return self._runs.pop(run_id, None)

    def __len__(self) -> int:
        with self._lock:
            return len(self._runs)

    def _expire(self) -> None:
        now = time.monotonic()
        for run_id in [k for k, v in self._runs.items() if v.expires_at < now]:
            self._runs.pop(run_id).generator.close()


class RunService:
    """Builds runners for the routes and streams their events as NDJSON lines."""

    def __init__(
        self, settings: Settings, mode: GatewayMode, *, transport: Transport | None = None
    ) -> None:
        self.settings = settings
        self.mode: GatewayMode = mode
        self.store = RecordingStore(settings.recordings_dir)
        self.budget = TokenBudget(settings.token_budget, settings.spend_log)
        self.classifier = make_classifier(settings)
        self.paused = PausedRuns()
        self._transport = transport
        self._recorded: dict[tuple[str, str, int], RecordedRuns] = {}
        self._recorded_lock = threading.Lock()

    def transport(self) -> Transport | None:
        if self.mode == "replay":
            return None
        if self._transport is None and self.settings.has_api_key:
            self._transport = OpenAITransport(self.settings.openai_api_key.get_secret_value())
        return self._transport

    def gateway(self) -> ModelGateway:
        return ModelGateway(self.mode, self.store, transport=self.transport(), budget=self.budget)

    def recorded_runs(self, case_id: str, model: str) -> RecordedRuns:
        """Replay every recorded trial of the unprotected run (no model calls). Cached until the
        recording store changes."""
        key = (case_id, model, len(self.store))
        with self._recorded_lock:
            if key in self._recorded:
                return self._recorded[key]
        replay = ModelGateway("replay", self.store)
        trials, hijacked, trial = 0, [], 1
        while trial == 1 or trial <= trials:
            request = RunRequest(case_id, False, model, LayerSwitches.all_off(), trial, "stop")
            runner = AgentRunner(
                request, gateway=replay, judge_model=model, classifier=None, run_id="recorded"
            )
            for event in runner.events():
                if isinstance(event, RunStarted):
                    trials = max(trials, event.trials_available)
                elif isinstance(event, RunFinished) and event.outcome == "hijacked":
                    hijacked.append(trial)
            trial += 1
        result = RecordedRuns(trials, tuple(hijacked))
        with self._recorded_lock:
            self._recorded[key] = result
        return result

    def start(self, request: RunRequest) -> tuple[AgentRunner, RunGenerator]:
        runner = AgentRunner(
            request,
            gateway=self.gateway(),
            judge_model=self.settings.judge_model,
            classifier=self.classifier,
            run_id=uuid.uuid4().hex,
        )
        return runner, runner.events()

    def stream(
        self, runner: AgentRunner, generator: RunGenerator, first: BaseModel | None = None
    ) -> Iterator[str]:
        """NDJSON lines until the run finishes or pauses (a paused run is kept for /decision)."""
        try:
            if first is not None:
                yield to_line(first)
                if isinstance(first, RunPaused):
                    self.paused.put(runner.run_id, generator, runner)
                    return
            for event in generator:
                yield to_line(event)
                if isinstance(event, RunPaused):
                    self.paused.put(runner.run_id, generator, runner)
                    return
        finally:
            if self.mode == "live":
                self.budget.flush(label=f"live run {runner.case.id}")
