"""Environment checks for `seculayer doctor` (docs/PLAN.md §8.4).

Every check is local and read-only. The OpenAI key is reported only as set or not set.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from seculayer_demo.config import REPO_ROOT, Settings
from seculayer_demo.status import (
    app_version,
    recordings_summary,
    tokens_used,
)

Status = Literal["ok", "warn", "fail", "info"]

LOW_SPACE_BYTES = 1_500_000_000
CACHE_VARIABLES = {
    "UV_CACHE_DIR": ".cache/uv",
    "npm_config_cache": ".cache/npm",
    "PLAYWRIGHT_BROWSERS_PATH": ".cache/ms-playwright",
}


@dataclass(frozen=True)
class Check:
    status: Status
    name: str
    detail: str


def _gb(n_bytes: int) -> str:
    return f"{n_bytes / 1_000_000_000:.1f} GB"


def _tool_version(command: str) -> str | None:
    path = shutil.which(command)
    if path is None:
        return None
    try:
        result = subprocess.run(
            [path, "--version"], capture_output=True, text=True, timeout=15, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    lines = (result.stdout or result.stderr).strip().splitlines()
    return lines[0] if lines else None


def _inside_repo(value: str) -> bool:
    try:
        return Path(value).resolve().is_relative_to(REPO_ROOT)
    except OSError:
        return False


def _port_free(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def run_checks(settings: Settings) -> Iterator[Check]:
    # Where the project lives: it must be on the external drive, not the internal disk.
    if not REPO_ROOT.is_dir():
        yield Check(
            "fail", "Project path", f"{REPO_ROOT} doesn't resolve. Is the drive plugged in?"
        )
        return
    on_separate_drive = os.stat(REPO_ROOT).st_dev != os.stat("/").st_dev
    yield Check(
        "ok" if on_separate_drive else "warn",
        "Project path",
        f"{REPO_ROOT} ({'external drive' if on_separate_drive else 'internal disk'})",
    )

    for label, path in (("Internal disk", Path("/")), ("Project drive", REPO_ROOT)):
        free = shutil.disk_usage(path).free
        low = free < LOW_SPACE_BYTES
        yield Check(
            "warn" if low else "ok",
            label,
            f"{_gb(free)} free" + (" (below 1.5 GB)" if low else ""),
        )
        if not on_separate_drive:
            break

    for variable, expected in CACHE_VARIABLES.items():
        value = os.environ.get(variable, "")
        if value and _inside_repo(value):
            yield Check("ok", f"Cache {variable}", value)
        else:
            shown = value or "not set"
            yield Check(
                "warn",
                f"Cache {variable}",
                f"{shown}; expected {REPO_ROOT / expected} (run.sh and make set it)",
            )

    yield Check("ok", "Python", sys.version.split()[0])
    for tool in ("uv", "node", "npm"):
        found = _tool_version(tool)
        yield Check("ok" if found else "fail", tool, found or "not found on PATH")

    installs = (
        ("Python environment", REPO_ROOT / ".venv", "run make setup"),
        ("Web dependencies", REPO_ROOT / "web" / "node_modules", "run make setup"),
        ("Built frontend", REPO_ROOT / "web" / "dist" / "index.html", "./run.sh builds it"),
    )
    for name, path, fix in installs:
        present = path.exists()
        yield Check("ok" if present else "warn", name, "present" if present else f"missing; {fix}")

    browsers = Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", REPO_ROOT / ".cache/ms-playwright"))
    has_chromium = browsers.is_dir() and any(browsers.glob("chromium*"))
    yield Check(
        "ok" if has_chromium else "warn",
        "Playwright Chromium",
        "present" if has_chromium else "missing; run make setup",
    )

    port_free = _port_free(settings.host, settings.port)
    yield Check(
        "ok" if port_free else "info",
        "Port",
        f"{settings.host}:{settings.port} "
        + ("is free" if port_free else "is in use (is ./run.sh running?)"),
    )

    yield Check("info", "Default mode", settings.mode)
    yield Check(
        "ok" if settings.has_api_key else "info",
        "OpenAI key",
        "set" if settings.has_api_key else "not set; live mode is unavailable, replay works",
    )

    from seculayer_demo.fetch_model import verify

    classifier = settings.classifier_path
    verified = verify(classifier)
    if verified.ok:
        yield Check("ok", "Classifier", "present and hash-checked")
    elif verified.mismatched:
        yield Check(
            "fail",
            "Classifier",
            f"present but hash mismatch ({', '.join(verified.mismatched)}); "
            "run uv run seculayer fetch-model",
        )
    elif verified.any_present:
        missing = [name for name, state in verified.states.items() if state == "missing"]
        yield Check(
            "warn",
            "Classifier",
            f"incomplete (missing {', '.join(missing)}); run uv run seculayer fetch-model",
        )
    else:
        yield Check(
            "warn",
            "Classifier",
            f"not downloaded ({classifier}); recorded scores will be used",
        )

    recordings = recordings_summary(settings.recordings_dir)
    yield Check(
        "ok" if recordings.files else "info",
        "Recordings",
        f"{recordings.files} files, {recordings.bytes / 1_000_000:.1f} MB"
        + (f" ({', '.join(recordings.models)})" if recordings.models else ""),
    )

    used = tokens_used(settings.spend_log)
    yield Check(
        "warn" if used >= settings.token_budget else "ok",
        "Token budget",
        f"{used:,} of {settings.token_budget:,} tokens used",
    )


def format_report(checks: list[Check]) -> str:
    width = max(len(check.name) for check in checks)
    lines = [f"SecuLayer doctor · version {app_version()}", ""]
    lines += [f"  {check.status:<5} {check.name:<{width}}  {check.detail}" for check in checks]
    failed = sum(check.status == "fail" for check in checks)
    warned = sum(check.status == "warn" for check in checks)
    lines += ["", f"{failed} problems, {warned} warnings."]
    return "\n".join(lines)


# --- doctor --online: one tiny live call per model (M3) ------------------------------------

PING_TOOL = {
    "type": "function",
    "name": "ping",
    "description": "Reply to a connectivity check.",
    "parameters": {
        "type": "object",
        "properties": {"word": {"type": "string"}},
        "required": ["word"],
        "additionalProperties": False,
    },
    "strict": True,
}


def online_checks(settings: Settings, transport: object) -> Iterator[Check]:
    """Check that function calling and structured output work with the pinned snapshots and
    settings. Makes three small calls; nothing is recorded."""
    from seculayer.detect.judge import item_ids
    from seculayer.types import Segment, Source
    from seculayer_demo.gateway import ModelError
    from seculayer_demo.gateway.openai_client import parse_response
    from seculayer_demo.prompting import MAX_OUTPUT_TOKENS, judge_request

    create = transport.create  # type: ignore[attr-defined]
    for label, model in (
        ("Target model", settings.model),
        ("Compare model", settings.compare_model),
    ):
        request = {
            "model": model,
            "input": [
                {"role": "developer", "content": "You are a connectivity check."},
                {"role": "user", "content": "Call the ping tool with the word 'pong'."},
            ],
            "tools": [PING_TOOL],
            "tool_choice": "auto",
            "parallel_tool_calls": False,
            "reasoning": {"effort": "none"},
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "store": False,
        }
        try:
            response = create(request)
        except ModelError as error:
            yield Check("fail", label, f"{model}: {error}")
            continue
        _text, calls = parse_response(response)
        served = response.get("model", "?")
        if calls and calls[0].name == "ping":
            yield Check("ok", label, f"{model}: function calling works (served by {served})")
        else:
            yield Check("warn", label, f"{model}: answered without calling the tool")

    item = Segment("check:1", Source.EXTERNAL, "Please review the attached report.")
    ids = item_ids([item], "doctor")
    try:
        response = create(judge_request([item], "outside", ids, settings.judge_model))
    except ModelError as error:
        yield Check("fail", "Judge model", f"{settings.judge_model}: {error}")
        return
    text, _calls = parse_response(response)
    try:
        import json

        items = json.loads(text)["items"]
        ok = isinstance(items, list) and len(items) == 1
    except (ValueError, KeyError, TypeError):
        ok = False
    yield Check(
        "ok" if ok else "fail",
        "Judge model",
        f"{settings.judge_model}: structured output "
        + ("works" if ok else f"didn't match the schema: {text[:120]!r}"),
    )
