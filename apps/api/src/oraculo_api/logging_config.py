"""Logging configuration for production-ready stdout output."""

import logging
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from oraculo_ai.core.config import Settings


def configure_logging(settings: "Settings") -> None:
    """Configure root logger for stdout output with level from settings.

    Force uvicorn loggers to propagate to root so they share the same
    timestamped format. Without this, uvicorn installs its own handlers
    with its own formatter (no timestamp) and bypasses our config.
    """
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
        force=True,
    )
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        uvi_log = logging.getLogger(name)
        uvi_log.handlers.clear()
        uvi_log.propagate = True
        uvi_log.setLevel(level)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
