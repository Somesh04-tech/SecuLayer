"""An explicit, approved identical-request repair through `seculayer record`.

Opaque encrypted reasoning can randomly contain a key-like substring. Keep the secret scan
unchanged; record the exact request again, and preserve the old call in an uncommitted backup.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime

from seculayer_demo.config import Settings
from seculayer_demo.gateway import ModelGateway, RecordingStore, TokenBudget
from seculayer_demo.gateway.openai_client import OpenAITransport
from seculayer_demo.recording_batch import TOKENS_PER_CALL, select_cases


def replace_recording(
    settings: Settings,
    cases: str,
    selector: str,
    *,
    confirm: Callable[[str], bool],
    log: Callable[[str], None],
) -> None:
    key, separator, trial_text = selector.partition(":")
    if not separator or not re.fullmatch(r"[0-9a-f]{64}", key) or not trial_text.isdecimal():
        raise ValueError("Use --replace-recording SHA256:TRIAL")
    store = RecordingStore(settings.recordings_dir)
    old = store.get(key, int(trial_text))
    if old is None or old.case_id not in {case.id for case in select_cases(cases)}:
        raise ValueError("The exact recording must exist and belong to the selected cases")
    backup = (
        settings.data_dir.parent
        / ".cache"
        / "recording-backups"
        / old.model
        / (f"{old.key}-{old.trial}.json.gz")
    )
    if backup.exists():
        raise ValueError("A backup for this recording already exists; refusing to overwrite it")
    budget = TokenBudget(settings.token_budget, settings.spend_log)
    estimates = {settings.model: (0, 0), settings.compare_model: (0, 0)}
    estimates[old.model] = (1, TOKENS_PER_CALL)
    log(f"Replace one {old.purpose} recording: {old.case_id}, trial {old.trial}, key {old.key}.")
    budget.preflight(estimates, log)
    if not settings.has_api_key:
        raise ValueError("Recording replacement needs OPENAI_API_KEY in .env")
    if not confirm("Replace this one recording, keeping a recoverable backup?"):
        raise ValueError("Replacement cancelled; no live call or file change")
    transport = OpenAITransport(settings.openai_api_key.get_secret_value())
    gateway = ModelGateway("live", store, transport=transport, budget=budget)
    try:
        result = gateway.call(
            old.request,
            trial=old.trial,
            scenario=old.case_id.split(".")[0],
            case_id=old.case_id,
            purpose=old.purpose,
        )
        if re.search(r"sk-[A-Za-z0-9_-]{16,}", json.dumps(result.raw)):
            raise RuntimeError("The new response also matches the secret scan; original retained")
        new = replace(
            old,
            response=result.raw,
            latency_ms=result.latency_ms,
            usage=result.usage,
            sdk_version=transport.sdk_version,
            recorded_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
        store.replace(old, new, backup=backup)
        log(f"Replaced exactly one recording. Recoverable old call: {backup}")
    finally:
        written = budget.flush(
            label=f"approved identical-request replacement {old.case_id} {selector}"
        )
        log(f"{written:,} tokens logged to data/spend.jsonl.")
