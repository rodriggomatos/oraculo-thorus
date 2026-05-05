"""Cópia da pasta-template Thórus pra criar a estrutura inicial dum projeto novo no Drive.

Drive API v3 não tem cópia recursiva nativa: `files.copy()` em pasta cria só
o shell. Esse módulo lista os filhos da template, copia arquivos via copy()
e desce nas subpastas, replicando a hierarquia inteira.

Pre-check: antes de copiar, lista 107_PROJETOS procurando o nome alvo. Se
existir (manualmente criada ou de uma corrida anterior), aborta com erro
explícito — nunca sobrescreve.

Erros mapeados pra mensagens humanas em PT-BR no caller (endpoint).
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError

from oraculo_ai.core.config import get_settings
from oraculo_ai.document_ai.drive_scanner import build_drive_service_rw

_log = logging.getLogger(__name__)

_FOLDER_MIME = "application/vnd.google-apps.folder"


@dataclass(frozen=True)
class CreateFolderResult:
    folder_id: str
    folder_name: str
    folder_url: str


class DriveFolderAlreadyExistsError(RuntimeError):
    """Já existe pasta com mesmo nome no parent — abortado pra não sobrescrever."""

    def __init__(self, folder_name: str) -> None:
        super().__init__(folder_name)
        self.folder_name = folder_name


class DriveTemplateNotAccessibleError(RuntimeError):
    """Service account não consegue ler/copiar a pasta-template."""


def folder_url_for(folder_id: str) -> str:
    return f"https://drive.google.com/drive/folders/{folder_id}"


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _list_children(service: Resource, folder_id: str) -> list[dict[str, Any]]:
    """Lista todos os filhos de uma pasta (não recursivo). Pagina até esgotar."""
    out: list[dict[str, Any]] = []
    page_token: str | None = None
    while True:
        kwargs: dict[str, Any] = dict(
            q=f"'{folder_id}' in parents and trashed=false",
            fields="nextPageToken, files(id,name,mimeType)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            pageSize=200,
        )
        if page_token:
            kwargs["pageToken"] = page_token
        payload = service.files().list(**kwargs).execute()
        out.extend(payload.get("files", []))
        page_token = payload.get("nextPageToken")
        if not page_token:
            break
    return out


def _name_exists_in_parent(service: Resource, parent_id: str, name: str) -> bool:
    escaped = _escape(name)
    payload = (
        service.files()
        .list(
            q=(
                f"'{parent_id}' in parents and "
                f"name = '{escaped}' and "
                f"trashed = false"
            ),
            fields="files(id,name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            pageSize=1,
        )
        .execute()
    )
    return bool(payload.get("files"))


def _create_folder(
    service: Resource, *, parent_id: str, name: str
) -> dict[str, Any]:
    metadata = {
        "name": name,
        "mimeType": _FOLDER_MIME,
        "parents": [parent_id],
    }
    return (
        service.files()
        .create(body=metadata, fields="id,name", supportsAllDrives=True)
        .execute()
    )


def _copy_file(
    service: Resource, *, file_id: str, parent_id: str, name: str
) -> dict[str, Any]:
    return (
        service.files()
        .copy(
            fileId=file_id,
            body={"name": name, "parents": [parent_id]},
            fields="id,name",
            supportsAllDrives=True,
        )
        .execute()
    )


def _copy_recursive(
    service: Resource, *, source_folder_id: str, dest_folder_id: str
) -> None:
    """Replica os filhos de `source_folder_id` em `dest_folder_id`."""
    for child in _list_children(service, source_folder_id):
        child_id = str(child["id"])
        child_name = str(child["name"])
        child_mime = str(child.get("mimeType") or "")
        if child_mime == _FOLDER_MIME:
            sub = _create_folder(service, parent_id=dest_folder_id, name=child_name)
            _copy_recursive(service, source_folder_id=child_id, dest_folder_id=str(sub["id"]))
        else:
            _copy_file(service, file_id=child_id, parent_id=dest_folder_id, name=child_name)


def _copy_template_blocking(project_name: str) -> CreateFolderResult:
    """Implementação síncrona — `copy_project_template` envolve com `asyncio.to_thread`."""
    settings = get_settings()
    template_id = settings.thorus_drive_template_folder_id
    parent_id = settings.thorus_drive_root_id

    service = build_drive_service_rw()

    try:
        service.files().get(
            fileId=template_id, fields="id,name", supportsAllDrives=True
        ).execute()
    except HttpError as exc:
        status = getattr(getattr(exc, "resp", None), "status", None)
        if status in (403, 404):
            raise DriveTemplateNotAccessibleError(
                f"template id {template_id!r} inacessível"
            ) from exc
        raise

    if _name_exists_in_parent(service, parent_id, project_name):
        raise DriveFolderAlreadyExistsError(project_name)

    new_folder = _create_folder(service, parent_id=parent_id, name=project_name)
    new_folder_id = str(new_folder["id"])

    _copy_recursive(service, source_folder_id=template_id, dest_folder_id=new_folder_id)

    return CreateFolderResult(
        folder_id=new_folder_id,
        folder_name=project_name,
        folder_url=folder_url_for(new_folder_id),
    )


async def copy_project_template(project_name: str) -> CreateFolderResult:
    """Cria pasta `project_name` em 107_PROJETOS copiando a estrutura da template.

    Roda I/O bloqueante em thread separado — Drive API client é síncrono.
    """
    return await asyncio.to_thread(_copy_template_blocking, project_name)
