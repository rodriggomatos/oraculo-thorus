"""Lista pastas de projeto direto da Drive 107_PROJETOS 2026.

Fonte de verdade pro próximo número de projeto: o Drive (não o banco), porque a
tabela `projects` está incompleta e nem todo projeto criado fisicamente no Drive
foi ingerido. Padrão das pastas: '<5 dígitos> - <cliente> - <resto>'.
"""

import asyncio
import logging
import re
from typing import Any

from googleapiclient.discovery import Resource

from oraculo_ai.core.config import get_settings
from oraculo_ai.document_ai.drive_scanner import build_drive_service

_log = logging.getLogger(__name__)


_FOLDER_MIME = "application/vnd.google-apps.folder"
_PROJECT_NUMBER_RE = re.compile(r"^(\d{5})\s*-\s*")


async def list_project_numbers_from_drive() -> list[int]:
    """Lista todos os números de projeto presentes como pastas no Drive raiz.

    Retorna lista deduplicada e ordenada decrescente de inteiros. Pastas com
    nome fora do padrão '<5 dígitos> - ...' são ignoradas em silêncio.

    Levanta RuntimeError se o serviço Drive falhar (sem fallback aqui — o caller
    decide se usa fallback ou propaga).
    """
    settings = get_settings()
    drive_id = settings.thorus_drive_root_id
    service: Resource = build_drive_service()

    folder_names: list[str] = []
    page_token: str | None = None

    def _list_page(token: str | None) -> dict[str, Any]:
        kwargs: dict[str, Any] = dict(
            q=(
                f"'{drive_id}' in parents and "
                f"mimeType='{_FOLDER_MIME}' and "
                f"trashed=false"
            ),
            fields="nextPageToken, files(id,name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            corpora="drive",
            driveId=drive_id,
            pageSize=200,
        )
        if token:
            kwargs["pageToken"] = token
        return service.files().list(**kwargs).execute()

    while True:
        payload = await asyncio.to_thread(_list_page, page_token)
        for file in payload.get("files", []):
            folder_names.append(str(file.get("name") or ""))
        page_token = payload.get("nextPageToken")
        if not page_token:
            break

    numbers: set[int] = set()
    for name in folder_names:
        match = _PROJECT_NUMBER_RE.match(name)
        if match is None:
            continue
        try:
            numbers.add(int(match.group(1)))
        except ValueError:
            continue

    return sorted(numbers, reverse=True)
