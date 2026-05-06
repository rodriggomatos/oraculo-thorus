"""Entrypoint: `python -m mcp_drive` ou `mcp-drive` script.

Two boot paths:

  - stdio (default, dev): Thor spawns this as a subprocess and talks via
    stdin/stdout. Same as before.
  - streamable-http / sse (prod): runs as a standalone HTTP service,
    serving the FastMCP Starlette app via uvicorn behind a token-auth
    middleware. Requires a non-empty `MCP_DRIVE_AUTH_TOKEN` — startup
    fails otherwise.
"""

import sys

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from mcp_drive.config import Settings, get_settings
from mcp_drive.logging import get_logger
from mcp_drive.server import build_server


_log = get_logger("main")


class TokenAuthMiddleware(BaseHTTPMiddleware):
    """Reject requests missing or with mismatched `X-MCP-Token` header."""

    def __init__(self, app: ASGIApp, expected_token: str) -> None:
        super().__init__(app)
        self._expected_token = expected_token

    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        if not self._expected_token:
            return Response("server misconfigured: empty token", status_code=500)
        token = request.headers.get("x-mcp-token", "")
        if token != self._expected_token:
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        return await call_next(request)


def _run_stdio() -> int:
    if sys.platform == "win32":
        import asyncio

        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    server = build_server()
    server.run(transport="stdio")
    return 0


def _run_http(settings: Settings) -> int:
    if not settings.mcp_drive_auth_token:
        _log.error(
            "MCP_DRIVE_AUTH_TOKEN must be set when transport=%s; refusing to "
            "start an unauthenticated HTTP server",
            settings.mcp_drive_transport,
        )
        return 2

    import uvicorn

    server = build_server()
    if settings.mcp_drive_transport == "streamable-http":
        app = server.streamable_http_app()
    else:
        app = server.sse_app()

    app.add_middleware(
        TokenAuthMiddleware, expected_token=settings.mcp_drive_auth_token
    )

    _log.info(
        "starting %s server on %s:%d (token auth enabled)",
        settings.mcp_drive_transport,
        settings.mcp_drive_host,
        settings.mcp_drive_port,
    )
    uvicorn.run(
        app,
        host=settings.mcp_drive_host,
        port=settings.mcp_drive_port,
        log_level=settings.mcp_drive_log_level.lower(),
    )
    return 0


def main() -> int:
    settings = get_settings()
    if settings.mcp_drive_transport == "stdio":
        return _run_stdio()
    return _run_http(settings)


if __name__ == "__main__":
    sys.exit(main())
