"""Carrega tools do MCP server `mcp-drive` (subprocess stdio) pro agente Thor.

Lazy init com módulo-level cache. Falha graciosa: se o subprocess não responder,
retorna lista vazia e loga warning. O Q&A continua funcionando sem awareness do Drive.
"""

import logging
from pathlib import Path
from typing import Any

from langchain_core.tools import BaseTool


_log = logging.getLogger(__name__)


_REPO_ROOT = Path(__file__).resolve().parents[6]
_MCP_DRIVE_DIR = _REPO_ROOT / "apps" / "mcp-drive"


_drive_tools_cache: list[BaseTool] | None = None
_failed_load: bool = False


async def get_drive_tools() -> list[BaseTool]:
    global _drive_tools_cache, _failed_load

    if _drive_tools_cache is not None:
        return _drive_tools_cache

    if _failed_load:
        return []

    if not _MCP_DRIVE_DIR.is_dir():
        _log.warning(
            "mcp-drive directory not found at %s; drive tools disabled",
            _MCP_DRIVE_DIR,
        )
        _failed_load = True
        return []

    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient
    except ImportError as exc:
        _log.warning("langchain-mcp-adapters not installed: %s; drive tools disabled", exc)
        _failed_load = True
        return []

    server_config: dict[str, Any] = {
        "drive": {
            "command": "uv",
            "args": [
                "--directory",
                str(_MCP_DRIVE_DIR),
                "run",
                "python",
                "-m",
                "mcp_drive",
            ],
            "transport": "stdio",
        }
    }

    try:
        client = MultiServerMCPClient(server_config)
        tools = await client.get_tools()
    except Exception as exc:
        _log.warning(
            "failed to load drive tools from mcp-drive: %s: %s; drive tools disabled",
            type(exc).__name__,
            exc,
        )
        _failed_load = True
        return []

    _drive_tools_cache = list(tools)
    _log.info("loaded %d drive tools from mcp-drive", len(_drive_tools_cache))
    return _drive_tools_cache
