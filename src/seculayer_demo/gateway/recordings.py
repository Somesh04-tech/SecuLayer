"""Recordings: stored model calls, keyed by the SHA-256 of the canonical request plus the trial
number (docs/PLAN.md §6.8).

Storage is data/recordings/{model-snapshot}/{scenario}.jsonl.gz, one recording per line,
committed to git. New recordings are appended as extra gzip members, which gzip reads as one
stream. The store builds an in-memory index on first use.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import tempfile
import threading
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

# Request fields that make up the canonical request. Anything else is dropped.
CANONICAL_FIELDS = (
    "model",
    "instructions",
    "input",
    "tools",
    "tool_choice",
    "reasoning",
    "text",
    "max_output_tokens",
    "parallel_tool_calls",
    "store",
)


def _drop_item_ids(value: Any) -> Any:
    """Response-item `id` fields vary between calls, so they're not part of the key."""
    if isinstance(value, list):
        return [_drop_item_ids(item) for item in value]
    if isinstance(value, dict):
        return {k: _drop_item_ids(v) for k, v in value.items() if k != "id"}
    return value


def canonical_request(request: Mapping[str, Any]) -> dict[str, Any]:
    canonical = {k: request[k] for k in CANONICAL_FIELDS if k in request}
    if "input" in canonical:
        canonical["input"] = _drop_item_ids(canonical["input"])
    return canonical


def canonical_json(request: Mapping[str, Any]) -> str:
    return json.dumps(
        canonical_request(request), sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )


def request_key(request: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json(request).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Recording:
    key: str
    trial: int
    model: str
    purpose: str  # "app" or "judge"
    case_id: str
    request: Mapping[str, Any]
    response: Mapping[str, Any]
    latency_ms: float
    usage: Mapping[str, int]
    sdk_version: str
    recorded_at: str
    extra: Mapping[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, ensure_ascii=False)

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> Recording:
        return cls(
            key=str(data["key"]),
            trial=int(data["trial"]),
            model=str(data["model"]),
            purpose=str(data.get("purpose", "app")),
            case_id=str(data.get("case_id", "")),
            request=dict(data["request"]),
            response=dict(data["response"]),
            latency_ms=float(data.get("latency_ms", 0.0)),
            usage={k: int(v) for k, v in dict(data.get("usage", {})).items()},
            sdk_version=str(data.get("sdk_version", "")),
            recorded_at=str(data.get("recorded_at", "")),
            extra=dict(data.get("extra", {})),
        )


class RecordingStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self._lock = threading.Lock()
        self._index: dict[tuple[str, int], Recording] | None = None
        self._trials: dict[str, set[int]] = {}

    def _load(self) -> dict[tuple[str, int], Recording]:
        if self._index is None:
            index: dict[tuple[str, int], Recording] = {}
            trials: dict[str, set[int]] = {}
            for path in sorted(self.root.glob("*/*.jsonl.gz")) if self.root.is_dir() else []:
                with gzip.open(path, "rt", encoding="utf-8") as handle:
                    for line in handle:
                        if not line.strip():
                            continue
                        recording = Recording.from_mapping(json.loads(line))
                        index[(recording.key, recording.trial)] = recording
                        trials.setdefault(recording.key, set()).add(recording.trial)
            self._index, self._trials = index, trials
        return self._index

    def reload(self) -> None:
        with self._lock:
            self._index = None
            self._load()

    def __len__(self) -> int:
        with self._lock:
            return len(self._load())

    def get(self, key: str, trial: int) -> Recording | None:
        with self._lock:
            return self._load().get((key, trial))

    def trials(self, key: str) -> list[int]:
        with self._lock:
            self._load()
            return sorted(self._trials.get(key, set()))

    def entries(self) -> tuple[Recording, ...]:
        with self._lock:
            return tuple(self._load().values())

    def add(self, recording: Recording, scenario: str) -> None:
        folder = self.root / recording.model
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{scenario}.jsonl.gz"
        with self._lock:
            self._load()
            assert self._index is not None
            with gzip.open(path, "at", encoding="utf-8") as handle:
                handle.write(recording.to_json() + "\n")
            self._index[(recording.key, recording.trial)] = recording
            self._trials.setdefault(recording.key, set()).add(recording.trial)

    def replace(self, old: Recording, new: Recording, *, backup: Path) -> None:
        """Explicitly replace one call after approval, preserving every other JSONL record.

        The old call is recoverable from backup. Requests, trials and case identities cannot
        change. Build a complete gzip beside the original, then atomically replace it.
        """
        identity = ("key", "trial", "model", "purpose", "case_id")
        if any(getattr(old, name) != getattr(new, name) for name in identity) or (
            canonical_json(old.request) != canonical_json(new.request)
        ):
            raise ValueError("A replacement must keep the identical request and recording identity")
        path = self.root / old.model / f"{old.case_id.split('.')[0]}.jsonl.gz"
        with self._lock:
            if self._load().get((old.key, old.trial)) != old:
                raise ValueError("Recording changed since it was selected; refusing replacement")
            backup.parent.mkdir(parents=True, exist_ok=True)
            # Exclusive creation prevents a later repair from overwriting the original backup.
            with backup.open("xb") as raw, gzip.open(raw, "wt", encoding="utf-8") as handle:
                handle.write(old.to_json() + "\n")
            with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".tmp", delete=False) as tmp:
                temporary = Path(tmp.name)
            try:
                replaced = 0
                with (
                    gzip.open(path, "rt", encoding="utf-8") as source,
                    gzip.open(temporary, "wt", encoding="utf-8") as target,
                ):
                    for line in source:
                        row = json.loads(line) if line.strip() else {}
                        if (row.get("key"), row.get("trial")) == (old.key, old.trial):
                            target.write(new.to_json() + "\n")
                            replaced += 1
                        else:
                            target.write(line)
                if replaced != 1:
                    raise ValueError(f"Expected exactly one old recording, found {replaced}")
                temporary.replace(path)
            finally:
                temporary.unlink(missing_ok=True)
            assert self._index is not None
            self._index[(new.key, new.trial)] = new
