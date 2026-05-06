"""Health check endpoint with real database probe."""

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, Response, status

from oraculo_ai.core.db import get_pool


router = APIRouter()
_log = logging.getLogger(__name__)

_DB_PROBE_TIMEOUT_SECONDS = 2.0


@router.get("/health")
async def health(response: Response) -> dict[str, Any]:
    """Probe critical dependencies and report aggregate health.

    Returns 200 with `status: healthy` when all checks pass; 503 with
    `status: unhealthy` and per-check detail otherwise. External services
    (LLM providers, Google APIs) are intentionally not probed — they are
    out of our control and should not trigger restarts.
    """
    checks: dict[str, str] = {"database": "unknown"}
    overall_ok = True

    try:
        pool = get_pool()
        async with asyncio.timeout(_DB_PROBE_TIMEOUT_SECONDS):
            async with pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT 1")
                    await cur.fetchone()
        checks["database"] = "ok"
    except asyncio.TimeoutError:
        checks["database"] = "timeout"
        overall_ok = False
        _log.warning("health check: database timeout")
    except Exception as exc:
        checks["database"] = f"error: {type(exc).__name__}"
        overall_ok = False
        _log.warning("health check: database error: %s", exc)

    if not overall_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "healthy" if overall_ok else "unhealthy",
        "service": "oraculo-thorus-api",
        "version": "0.1.0",
        "checks": checks,
    }
