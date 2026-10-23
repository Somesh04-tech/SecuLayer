"""Security headers on every response (docs/PLAN.md §6.10).

Written as plain ASGI middleware, not BaseHTTPMiddleware, so streamed NDJSON responses pass
through untouched and still get the headers.
"""

from __future__ import annotations

from starlette.types import ASGIApp, Message, Receive, Scope, Send

CONTENT_SECURITY_POLICY = (
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-src 'self'; "
    "frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
)

SECURITY_HEADERS: tuple[tuple[str, str], ...] = (
    ("content-security-policy", CONTENT_SECURITY_POLICY),
    ("referrer-policy", "no-referrer"),
    ("x-content-type-options", "nosniff"),
)

_HEADER_NAMES = {name.encode("latin-1") for name, _ in SECURITY_HEADERS}
_ENCODED = [(name.encode("latin-1"), value.encode("latin-1")) for name, value in SECURITY_HEADERS]


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = [
                    (name, value)
                    for name, value in message.get("headers", [])
                    if name.lower() not in _HEADER_NAMES
                ]
                message["headers"] = headers + _ENCODED
            await send(message)

        await self.app(scope, receive, send_with_headers)
