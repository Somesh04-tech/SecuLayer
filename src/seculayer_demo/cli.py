"""The `seculayer` command-line tool."""

from __future__ import annotations

import os
from typing import Annotated

import typer
from pydantic import ValidationError

from seculayer.types import LayerSwitches
from seculayer_demo.config import Mode, Settings, get_settings, is_loopback

app = typer.Typer(
    help="SecuLayer: a prompt-injection demo and a layered defense.",
    no_args_is_help=True,
    add_completion=False,
)


def _load_settings() -> Settings:
    try:
        return get_settings()
    except ValidationError as error:
        for problem in error.errors():
            typer.echo(f"Configuration problem: {problem['msg']}", err=True)
        raise typer.Exit(2) from None


@app.command()
def serve(
    host: Annotated[str | None, typer.Option(help="Loopback address to bind.")] = None,
    port: Annotated[int | None, typer.Option(help="Port to listen on.")] = None,
    mode: Annotated[str | None, typer.Option(help="replay (default) or live.")] = None,
    reload: Annotated[bool, typer.Option(help="Restart on code changes (make dev).")] = False,
) -> None:
    """Start the demo server (API and built frontend)."""
    import uvicorn

    settings = _load_settings()
    host = host or settings.host
    port = port or settings.port
    chosen = mode or settings.mode
    if chosen not in ("replay", "live"):
        typer.echo(f"Unknown mode {chosen!r}; use replay or live.", err=True)
        raise typer.Exit(2)
    if not is_loopback(host):
        typer.echo(f"Refusing to bind {host}: the demo only listens on loopback.", err=True)
        raise typer.Exit(2)
    if chosen == "live" and not settings.has_api_key:
        typer.echo("Live mode needs an OpenAI key in .env (OPENAI_API_KEY).", err=True)
        raise typer.Exit(2)

    # The factory reads settings from the environment, which also survives --reload restarts.
    os.environ["SECULAYER_MODE"] = chosen
    get_settings.cache_clear()
    mode_label: Mode = "live" if chosen == "live" else "replay"
    typer.echo(f"SecuLayer ({mode_label} mode) at http://{host}:{port}")
    uvicorn.run(
        "seculayer_demo.server.app:create_app",
        factory=True,
        host=host,
        port=port,
        reload=reload,
        reload_dirs=["src"] if reload else None,
        log_level=settings.log_level,
        server_header=False,
    )


@app.command()
def doctor(
    online: Annotated[
        bool, typer.Option(help="Also make one tiny live call per model (M3).")
    ] = False,
) -> None:
    """Check the environment: tools, disk space, caches, port, key, classifier, recordings."""
    from seculayer_demo.doctor import format_report, run_checks

    if online:
        typer.echo("doctor --online: not implemented yet (M3)", err=True)
        raise typer.Exit(1)
    checks = list(run_checks(_load_settings()))
    typer.echo(format_report(checks))
    if any(check.status == "fail" for check in checks):
        raise typer.Exit(1)


@app.command("fetch-model")
def fetch_model(
    verify_only: Annotated[
        bool, typer.Option("--verify-only", help="Only check the files already present.")
    ] = False,
) -> None:
    """Download the pinned classifier files from Hugging Face and check their SHA-256."""
    from seculayer_demo.fetch_model import FetchError, fetch, load_manifest, verify

    settings = _load_settings()
    manifest = load_manifest()
    directory = settings.classifier_path
    if verify_only:
        result = verify(directory, manifest)
        for name, state in result.states.items():
            typer.echo(f"  {state:<9} {name}")
        raise typer.Exit(0 if result.ok else 1)

    typer.echo(f"Classifier {manifest.name} at revision {manifest.revision[:12]} into {directory}")
    try:
        result = fetch(directory, manifest, log=typer.echo)
    except FetchError as error:
        typer.echo(f"Download failed: {error}", err=True)
        raise typer.Exit(1) from None
    if not result.ok:
        typer.echo(f"Some files don't match the manifest: {result.states}", err=True)
        raise typer.Exit(1)
    typer.echo("All classifier files present and hash-checked.")


def _layers(spec: str) -> LayerSwitches:
    from seculayer_demo.console import parse_layers

    try:
        return parse_layers(spec)
    except ValueError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(2) from None


@app.command()
def screen(
    case: Annotated[str, typer.Option("--case", help="Case ID, e.g. inbox.hidden_forward.")],
    layers: Annotated[str, typer.Option(help="all, none, a list to keep on, or -layer,…")] = "all",
) -> None:
    """Print the hidden-text cleaner's and screening's verdicts for a case's inputs.

    Runs locally with no model call, so the LLM judge is always off here.
    """
    from seculayer.detect.prompt_guard import CachedClassifier, PromptGuardClassifier, ScoreCache
    from seculayer_demo.console import screen_case

    settings = _load_settings()
    model = PromptGuardClassifier(settings.classifier_path)
    classifier = CachedClassifier(
        ScoreCache(settings.data_dir / "cache" / "classifier_scores.jsonl"),
        model if model.available else None,
    )
    try:
        inspections = screen_case(case, _layers(layers), classifier)
    except KeyError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(2) from None
    steps = ["The user's message", "Tool result: the inbox"]
    for title, inspection in zip(steps, inspections, strict=False):
        typer.echo(title + (":" if len(inspections) > 1 else " and outside content:"))
        for verdict in inspection.verdicts:
            typer.echo(f"  [{verdict.layer.value:<11}] {verdict.action.value:<9} {verdict.reason}")
            for line in verdict.detail:
                typer.echo(f"      · {line[:150]}")
        if inspection.withheld_ids:
            typer.echo(f"  withheld: {', '.join(inspection.withheld_ids)}")
        if inspection.blocked:
            typer.echo(f"  blocked: {inspection.block_reason}")
    typer.echo("(The LLM judge is off here: it needs a model call. Use `seculayer run`.)")


if __name__ == "__main__":
    app()
