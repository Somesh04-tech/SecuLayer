"""HTTP API routes under /api (docs/PLAN.md §6.9)."""

from __future__ import annotations

import json
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from seculayer.engine import SecuLayer
from seculayer.types import LayerSwitches, Segment, Source
from seculayer_demo.apps import make_app
from seculayer_demo.config import Mode, Settings
from seculayer_demo.runner import RunRequest
from seculayer_demo.scenarios import Case, Scenario, load_all
from seculayer_demo.server.events import FindingOut, RunEvent
from seculayer_demo.server.runs import RunService
from seculayer_demo.status import (
    app_version,
    classifier_files_present,
    recordings_summary,
    tokens_used,
)

NDJSON = "application/x-ndjson"
LAYER_KEYS = set(LayerSwitches.__dataclass_fields__) - {"observe_only"}

router = APIRouter(prefix="/api")


class Health(BaseModel):
    status: Literal["ok"]


class ModelsInfo(BaseModel):
    target: str
    compare: str
    judge: str


class ClassifierInfo(BaseModel):
    status: Literal["present", "missing"]


class RecordingsInfo(BaseModel):
    files: int
    models: list[str]


class BudgetInfo(BaseModel):
    limit: int
    used: int
    remaining: int


class Meta(BaseModel):
    version: str
    mode: Mode
    live_available: bool
    models: ModelsInfo
    classifier: ClassifierInfo
    recordings: RecordingsInfo
    budget: BudgetInfo


@router.get("/health")
def health() -> Health:
    return Health(status="ok")


@router.get("/meta")
def meta(request: Request) -> Meta:
    settings: Settings = request.app.state.settings
    mode: Mode = request.app.state.mode
    recordings = recordings_summary(settings.recordings_dir)
    used = tokens_used(settings.spend_log)
    return Meta(
        version=app_version(),
        mode=mode,
        live_available=settings.has_api_key,
        models=ModelsInfo(
            target=settings.model, compare=settings.compare_model, judge=settings.judge_model
        ),
        classifier=ClassifierInfo(
            status="present" if classifier_files_present(settings.classifier_path) else "missing"
        ),
        recordings=RecordingsInfo(files=recordings.files, models=list(recordings.models)),
        budget=BudgetInfo(
            limit=settings.token_budget,
            used=used,
            remaining=max(settings.token_budget - used, 0),
        ),
    )


# --- Scenarios ----------------------------------------------------------------------------


class ScenarioSummary(BaseModel):
    id: str
    title: str
    summary: str
    card_summary: str
    injection: str
    trifecta: dict[str, str]
    attack_count: int
    normal_count: int


class RealWorld(BaseModel):
    title: str = ""
    date: str = ""
    url: str = ""


class RecordedRunsInfo(BaseModel):
    """The unprotected runs recorded for the target model (replay)."""

    trials: int
    hijacked: list[int]
    default_trial: int


class CaseDetail(BaseModel):
    id: str
    kind: Literal["attack", "normal"]
    title: str
    variant_of: str | None
    variants: list[str]
    hard_case: bool
    tags: list[str]
    frameworks: list[str]
    user_request: str
    injected_text: list[str]
    goal: str
    explanation: str
    why_it_works: str
    what_stops_it: str
    expected: str
    why_here: str
    real_world: RealWorld | None
    setup: dict[str, Any]
    recorded: RecordedRunsInfo | None


class ScenarioDetail(ScenarioSummary):
    user_name: str
    how_built: list[str]
    developer_instructions: str
    allowed_domains: list[str]
    contacts: list[str]
    cases: list[CaseDetail]
    measured: dict[str, Any] | None


def _summary(scenario: Scenario) -> dict[str, Any]:
    return {
        "id": scenario.id,
        "title": scenario.title,
        "summary": scenario.summary,
        "card_summary": scenario.card_summary,
        "injection": scenario.injection,
        "trifecta": dict(scenario.trifecta),
        "attack_count": len(scenario.attacks),
        "normal_count": len(scenario.normal_cases),
    }


def _case_detail(scenario: Scenario, case: Case, service: RunService, model: str) -> CaseDetail:
    recorded = None
    if case.kind == "attack" and case.variant_of is None:
        runs = service.recorded_runs(case.id, model)
        recorded = RecordedRunsInfo(
            trials=runs.trials, hijacked=list(runs.hijacked), default_trial=runs.default_trial
        )
    return CaseDetail(
        id=case.id,
        kind=case.kind,
        title=case.title,
        variant_of=case.variant_of,
        variants=list(case.variants),
        hard_case=case.hard_case,
        tags=list(case.tags),
        frameworks=list(case.frameworks),
        user_request=case.user_request,
        injected_text=list(case.injected_text),
        goal=case.goal,
        explanation=case.explanation,
        why_it_works=case.why_it_works,
        what_stops_it=case.what_stops_it,
        expected=case.expected,
        why_here=case.why_here,
        real_world=RealWorld(**case.real_world) if case.real_world else None,
        setup=make_app(scenario, case, seed=case.id).setup(),
        recorded=recorded,
    )


@router.get("/scenarios")
def scenarios() -> list[ScenarioSummary]:
    return [ScenarioSummary(**_summary(s)) for s in load_all().values()]


@router.get("/scenarios/{scenario_id}")
def scenario_detail(scenario_id: str, request: Request) -> ScenarioDetail:
    scenario = load_all().get(scenario_id)
    if scenario is None:
        raise HTTPException(404, f"Unknown scenario {scenario_id!r}.")
    settings: Settings = request.app.state.settings
    measured = None
    latest = settings.data_dir / "eval" / "latest.json"
    if latest.is_file():
        measured = json.loads(latest.read_text(encoding="utf-8")).get("cases", {})
        measured = {k: v for k, v in measured.items() if k.startswith(scenario_id + ".")}
    return ScenarioDetail(
        **_summary(scenario),
        user_name=scenario.user_name,
        how_built=list(scenario.how_built),
        developer_instructions=scenario.developer_instructions,
        allowed_domains=list(scenario.policy.allowed_domains),
        contacts=list(scenario.policy.contacts),
        cases=[
            _case_detail(scenario, case, _service(request), settings.model)
            for case in scenario.cases.values()
        ],
        measured=measured,
    )


# --- Runs ---------------------------------------------------------------------------------


class RunBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: str
    protected: bool
    layers: dict[str, bool] | None = None
    model: str | None = None
    trial: int = Field(default=1, ge=1, le=10)


class DecisionBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    approve: bool


def _service(request: Request) -> RunService:
    service: RunService = request.app.state.runs
    return service


@router.post(
    "/runs",
    response_class=StreamingResponse,
    responses={200: {"content": {NDJSON: {}}, "description": "Run events, one per line."}},
)
def start_run(body: RunBody, request: Request) -> StreamingResponse:
    settings: Settings = request.app.state.settings
    service = _service(request)
    unknown = set(body.layers or {}) - LAYER_KEYS
    if unknown:
        raise HTTPException(422, f"Unknown layers: {', '.join(sorted(unknown))}.")
    model = body.model or settings.model
    if model not in (settings.model, settings.compare_model):
        raise HTTPException(422, f"Unknown model {model!r}.")
    try:
        load_all()[body.case_id.split(".", 1)[0]].case(body.case_id)
    except KeyError:
        raise HTTPException(404, f"Unknown case {body.case_id!r}.") from None
    if service.mode == "live" and service.transport() is None:
        raise HTTPException(409, "Live mode needs an OpenAI key in .env.")
    layers = LayerSwitches(**(body.layers or {})) if body.protected else LayerSwitches.all_off()
    run = RunRequest(body.case_id, body.protected, model, layers, body.trial)
    runner, generator = service.start(run)
    return StreamingResponse(service.stream(runner, generator), media_type=NDJSON)


@router.post(
    "/runs/{run_id}/decision",
    response_class=StreamingResponse,
    responses={200: {"content": {NDJSON: {}}, "description": "More run events."}},
)
def decide(run_id: str, body: DecisionBody, request: Request) -> StreamingResponse:
    service = _service(request)
    paused = service.paused.take(run_id)
    if paused is None:
        raise HTTPException(404, "This run isn't waiting for a decision (it may have expired).")
    first = paused.generator.send(body.approve)
    return StreamingResponse(
        service.stream(paused.runner, paused.generator, first), media_type=NDJSON
    )


@router.get("/schema/run-event")
def run_event_schema() -> list[RunEvent]:
    """Schema only: puts the run-event union into OpenAPI for the frontend's generated types."""
    return []


# --- Screening only (the Sandbox in replay mode) --------------------------------------------


class ScreenBody(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    scenario_id: str
    text: str = Field(max_length=20_000)
    as_: Literal["user", "outside"] = Field(alias="as")
    format: Literal["text", "html"] = "text"


class VerdictOut(BaseModel):
    layer: str
    action: str
    reason: str
    findings: list[FindingOut]
    latency_ms: float
    detail: list[str]


class HiddenOut(BaseModel):
    text: str
    kind: str
    reason: str


class ScreenResult(BaseModel):
    verdicts: list[VerdictOut]
    hidden: list[HiddenOut]
    cleaned_text: str
    blocked: bool
    withheld: bool


@router.post("/screen")
def screen(body: ScreenBody, request: Request) -> ScreenResult:
    """Layers 1-2 on the viewer's text, locally: no model call, so the judge is off."""
    scenario = load_all().get(body.scenario_id)
    if scenario is None:
        raise HTTPException(404, f"Unknown scenario {body.scenario_id!r}.")
    service = _service(request)
    guard = SecuLayer(
        scenario.policy,
        layers=LayerSwitches(judge=False),
        classifier=service.classifier,
        seed="sandbox",
    )
    if body.as_ == "user":
        segment = Segment("user", Source.USER, body.text, label=scenario.user_name)
        user_text = body.text
    else:
        segment = Segment(
            "sandbox:outside", Source.EXTERNAL, body.text, body.format, label="Your text"
        )
        user_text = ""
    inspection = guard.inspect([segment], guard.new_context(user_text))
    return ScreenResult(
        verdicts=[
            VerdictOut(
                layer=v.layer.value,
                action=v.action.value,
                reason=v.reason,
                findings=[
                    FindingOut(
                        detector=f.detector,
                        segment_id=f.segment_id,
                        span=f.span,
                        excerpt=f.excerpt,
                        score=f.score,
                        explanation=f.explanation,
                    )
                    for f in v.findings
                ],
                latency_ms=v.latency_ms,
                detail=list(v.detail),
            )
            for v in inspection.verdicts
        ],
        hidden=[HiddenOut(text=h.text, kind=h.kind, reason=h.reason) for h in inspection.hidden],
        cleaned_text=inspection.segments[0].text if inspection.segments else "",
        blocked=inspection.blocked,
        withheld=bool(inspection.withheld_ids),
    )


# --- Evaluation ---------------------------------------------------------------------------


@router.get("/eval/latest", responses={404: {"description": "No evaluation results yet."}})
def eval_latest(request: Request) -> JSONResponse:
    settings: Settings = request.app.state.settings
    latest = settings.data_dir / "eval" / "latest.json"
    if not latest.is_file():
        return JSONResponse({"detail": "No results yet. Run make eval to measure them."}, 404)
    return JSONResponse(json.loads(latest.read_text(encoding="utf-8")))
