"""Carrega tools do MCP server `mcp-drive` (subprocess stdio ou HTTP) pro agente Thor.

Lazy init com módulo-level cache. Falha graciosa: se não conseguir conectar,
retorna lista vazia e loga warning. O Q&A continua funcionando sem awareness
do Drive.

Modo de conexão controlado por `settings.mcp_drive_transport`:
  - stdio (default, dev): spawna `python -m mcp_drive` como subprocess.
  - streamable-http / sse (prod): conecta no `mcp_drive_url` com header
    `X-MCP-Token`. Token tem que estar configurado nesse modo.
"""

import logging
from pathlib import Path
from typing import Any

from langchain_core.tools import BaseTool

from oraculo_ai.core.config import get_settings


_log = logging.getLogger(__name__)


_REPO_ROOT = Path(__file__).resolve().parents[6]
_MCP_DRIVE_DIR = _REPO_ROOT / "apps" / "mcp-drive"


_drive_tools_cache: list[BaseTool] | None = None
_failed_load: bool = False


def _build_stdio_config() -> dict[str, Any] | None:
    if not _MCP_DRIVE_DIR.is_dir():
        _log.warning(
            "mcp-drive directory not found at %s; drive tools disabled",
            _MCP_DRIVE_DIR,
        )
        return None
    return {
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


def _build_http_config(transport: str, url: str, token: str) -> dict[str, Any] | None:
    if not token:
        _log.warning(
            "mcp_drive_auth_token is empty for transport=%s; drive tools disabled",
            transport,
        )
        return None
    adapter_transport = "streamable_http" if transport == "streamable-http" else "sse"
    return {
        "drive": {
            "transport": adapter_transport,
            "url": url,
            "headers": {"X-MCP-Token": token},
        }
    }


async def get_drive_tools() -> list[BaseTool]:
    global _drive_tools_cache, _failed_load

    if _drive_tools_cache is not None:
        return _drive_tools_cache

    if _failed_load:
        return []

    settings = get_settings()
    transport = settings.mcp_drive_transport

    if transport == "stdio":
        server_config = _build_stdio_config()
    else:
        server_config = _build_http_config(
            transport, settings.mcp_drive_url, settings.mcp_drive_auth_token
        )

    if server_config is None:
        _failed_load = True
        return []

    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient
    except ImportError as exc:
        _log.warning("langchain-mcp-adapters not installed: %s; drive tools disabled", exc)
        _failed_load = True
        return []

    try:
        client = MultiServerMCPClient(server_config)
        tools = await client.get_tools()
    except Exception as exc:
        _log.warning(
            "failed to load drive tools from mcp-drive (transport=%s): %s: %s; drive tools disabled",
            transport,
            type(exc).__name__,
            exc,
        )
        _failed_load = True
        return []

    _drive_tools_cache = list(tools)
    _log.info(
        "loaded %d drive tools from mcp-drive (transport=%s)",
        len(_drive_tools_cache),
        transport,
    )
    return _drive_tools_cache
