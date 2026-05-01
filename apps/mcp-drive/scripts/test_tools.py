"""Testa as 5 tools do mcp-drive contra o Drive real.

Não passa pelo protocolo MCP — instancia DriveTools direto.

Uso:
    cd apps/mcp-drive
    uv run python scripts/test_tools.py
"""

import asyncio
import json
import sys
from typing import Any

from mcp_drive.auth import load_service_account_credentials, validate_readonly_scopes
from mcp_drive.backend import GoogleDriveBackend
from mcp_drive.cache import TTLCache
from mcp_drive.config import get_settings
from mcp_drive.logging import configure_logging, get_logger
from mcp_drive.project_resolver import ProjectResolver
from mcp_drive.schemas import LDPResult, LDPStatus, ProjectFolder, ToolResult
from mcp_drive.tools import DriveTools


_log = get_logger("test_tools")


def _summary(result: ToolResult) -> dict[str, Any]:
    return {
        "found": result.found,
        "count": result.count,
        "project": result.project_folder_name,
        "note": result.note,
        "first_items": [
            {"name": i.name, "path": "/".join(i.path), "url": i.web_view_link}
            for i in result.items[:5]
        ],
    }


def _ldp_summary(r: LDPResult) -> str:
    if r.status == LDPStatus.FOUND:
        return (
            f"FOUND  via={r.resolved_via!s:9}  url={r.sheet_url}"
        )
    if r.status == LDPStatus.NOT_FOUND:
        return f"NOT_FOUND  ({r.note})"
    candidates = ", ".join(f.name for f in r.found_files[:3])
    return (
        f"UNCERTAIN  reason={r.uncertainty_reason}  "
        f"candidates=[{candidates}]"
    )


async def _run() -> int:
    settings = get_settings()
    configure_logging(settings.mcp_drive_log_level)

    credentials = load_service_account_credentials(settings.google_service_account_json)
    validate_readonly_scopes(credentials)

    backend = GoogleDriveBackend(credentials, drive_id=settings.thorus_drive_root_id)
    cache: TTLCache[int, ProjectFolder] = TTLCache(
        ttl_seconds=settings.mcp_drive_cache_ttl_seconds
    )
    resolver = ProjectResolver(backend, settings.thorus_drive_root_id, cache=cache)
    tools = DriveTools(backend=backend, resolver=resolver)

    print("=" * 80)
    print("LDP TRI-STATE — varrendo 26001..26009")
    print("=" * 80)
    for project_number in range(26001, 26010):
        try:
            ldp = await tools.find_lista_definicoes(project_number)
        except Exception as exc:
            print(f"[{project_number}] ERROR  {type(exc).__name__}: {exc}")
            continue
        print(f"[{project_number}] {_ldp_summary(ldp)}")

    print()
    print("=" * 80)
    print("DETALHE LDP — 26003 (gsheet), 26007 (uncertain), 26009 (link_txt)")
    print("=" * 80)
    for n in (26003, 26007, 26009):
        ldp = await tools.find_lista_definicoes(n)
        print(f"\n[{n}]")
        print(json.dumps(ldp.model_dump(mode="json", exclude_none=True), indent=2, ensure_ascii=False))

    print()
    print("=" * 80)
    print("OUTRAS TOOLS")
    print("=" * 80)
    atas = await tools.find_atas(26003)
    print("\nfind_atas(26003):")
    print(json.dumps(_summary(atas), indent=2, ensure_ascii=False))

    vofs = await tools.find_vof_revisoes(26009, discipline="HID", only_approved=True)
    print("\nfind_vof_revisoes(26009, HID, only_approved=True):")
    print(json.dumps(_summary(vofs), indent=2, ensure_ascii=False))

    ext = await tools.find_arquivos_externos(26008, source="Arquitet")
    print("\nfind_arquivos_externos(26008, source='Arquitet'):")
    print(json.dumps(_summary(ext), indent=2, ensure_ascii=False))

    return 0


def main() -> int:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    return asyncio.run(_run())


if __name__ == "__main__":
    sys.exit(main())
