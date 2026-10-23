"""The `seculayer` command-line tool."""

from __future__ import annotations

import os
from typing import Annotated

import typer
from pydantic import ValidationError

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


if __name__ == "__main__":
    app()
