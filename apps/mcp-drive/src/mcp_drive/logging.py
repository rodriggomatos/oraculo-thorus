"""Logger estruturado pro stderr (stdio MCP usa stdout pro protocolo)."""

import logging
import sys
from typing import Any


_FORMAT = "[mcp-drive] %(levelname)s %(name)s: %(message)s"


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(_FORMAT))

    root = logging.getLogger("mcp_drive")
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())
    root.propagate = False


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"mcp_drive.{name}")


def kvfmt(**fields: Any) -> str:
    return " ".join(f"{k}={v!r}" for k, v in fields.items())
