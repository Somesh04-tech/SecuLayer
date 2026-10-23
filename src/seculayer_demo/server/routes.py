"""HTTP API routes under /api (docs/PLAN.md §6.9)."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel

from seculayer_demo.config import Mode, Settings
from seculayer_demo.status import (
    app_version,
    classifier_files_present,
    recordings_summary,
    tokens_used,
)

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
