"""No API key ever lands in recordings, logs or data (docs/PLAN.md §6.10)."""

from __future__ import annotations

import gzip
import re
from pathlib import Path

from seculayer_demo.config import REPO_ROOT

KEY = re.compile(r"sk-[A-Za-z0-9_-]{16,}")


def _text(path: Path) -> str:
    if path.name.endswith(".gz"):
        with gzip.open(path, "rt", encoding="utf-8", errors="replace") as handle:
            return handle.read()
    return path.read_text(encoding="utf-8", errors="replace")


def scan(root: Path) -> list[str]:
    hits = []
    for path in root.rglob("*"):
        readable = path.is_file() and path.stat().st_size < 50_000_000
        if readable and path.suffix != ".onnx" and KEY.search(_text(path)):
            hits.append(str(path))
    return hits


def test_no_keys_in_data_or_logs() -> None:
    roots = [REPO_ROOT / "data", REPO_ROOT / "artifacts"]
    assert [hit for root in roots if root.is_dir() for hit in scan(root)] == []


def test_the_scanner_finds_keys(tmp_path: Path) -> None:
    with gzip.open(tmp_path / "x.jsonl.gz", "wt") as handle:
        handle.write('{"auth": "sk-proj-abcdefghijklmnopqrstuvwxyz"}\n')
    assert scan(tmp_path) == [str(tmp_path / "x.jsonl.gz")]
