"""FastAPI app factory: the /api routes plus the built frontend from web/dist."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response

from seculayer_demo.config import Mode, Settings, get_settings
from seculayer_demo.server.routes import router
from seculayer_demo.server.security import SecurityHeadersMiddleware
from seculayer_demo.status import app_version

FRONTEND_MISSING = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>SecuLayer</title></head>
<body><p>The SecuLayer frontend isn't built yet. Run <code>./run.sh</code> or
<code>make e2e</code> to build it.</p></body></html>
"""


def create_app(
    settings: Settings | None = None,
    *,
    mode: Mode | None = None,
    dist_dir: Path | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    dist = (dist_dir or settings.web_dist).resolve()

    app = FastAPI(
        title="SecuLayer",
        version=app_version(),
        docs_url=None,
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )
    app.state.settings = settings
    app.state.mode = mode or settings.mode
    app.add_middleware(SecurityHeadersMiddleware)
    app.include_router(router)

    @app.api_route("/{full_path:path}", methods=["GET", "HEAD"], include_in_schema=False)
    def frontend(full_path: str) -> Response:
        if full_path == "api" or full_path.startswith("api/"):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        index = dist / "index.html"
        if not index.is_file():
            return HTMLResponse(FRONTEND_MISSING, status_code=503)
        if full_path:
            candidate = (dist / full_path).resolve()
            if candidate.is_relative_to(dist) and candidate.is_file():
                cache = (
                    "public, max-age=31536000, immutable"
                    if candidate.parent == dist / "assets"
                    else "no-cache"
                )
                return FileResponse(candidate, headers={"cache-control": cache})
        return FileResponse(index, headers={"cache-control": "no-cache"})

    return app
