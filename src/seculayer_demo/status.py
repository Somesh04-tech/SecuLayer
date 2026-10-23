"""Read-only facts about the local installation, shared by /api/meta and `seculayer doctor`."""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

CLASSIFIER_MODEL_FILE = "model.quant.onnx"
CLASSIFIER_TOKENIZER_FILE = "tokenizer.json"


def app_version() -> str:
    try:
        return version("seculayer")
    except PackageNotFoundError:
        return "0.0.0"


@dataclass(frozen=True)
class RecordingsSummary:
    files: int
    bytes: int
    models: tuple[str, ...]


def recordings_summary(recordings_dir: Path) -> RecordingsSummary:
    if not recordings_dir.is_dir():
        return RecordingsSummary(files=0, bytes=0, models=())
    files = sorted(recordings_dir.glob("*/*.jsonl.gz"))
    models = tuple(sorted({path.parent.name for path in files}))
    return RecordingsSummary(
        files=len(files), bytes=sum(path.stat().st_size for path in files), models=models
    )


def tokens_used(spend_log: Path) -> int:
    """Total tokens logged by live batches in data/spend.jsonl. Unreadable lines count as zero."""
    if not spend_log.is_file():
        return 0
    total = 0
    for line in spend_log.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        tokens = entry.get("tokens") if isinstance(entry, dict) else None
        if isinstance(tokens, int):
            total += tokens
    return total


def classifier_files_present(classifier_dir: Path) -> bool:
    return all(
        (classifier_dir / name).is_file()
        for name in (CLASSIFIER_MODEL_FILE, CLASSIFIER_TOKENIZER_FILE)
    )
