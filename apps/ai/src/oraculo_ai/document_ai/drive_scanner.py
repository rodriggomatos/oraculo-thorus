"""Scanner do Google Drive — descobre planilha LDP a partir do ID da pasta de projeto."""

import asyncio
import re
from typing import Any

from googleapiclient.discovery import Resource, build
from psycopg.rows import dict_row

from oraculo_ai.core.config import get_settings
from oraculo_ai.core.db import get_pool
from oraculo_ai.ingestion.google_sheets.connector import load_credentials


_DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
_DRIVE_RW_SCOPES = ["https://www.googleapis.com/auth/drive"]

_FOLDER_MIME = "application/vnd.google-apps.folder"
_SPREADSHEET_MIME = "application/vnd.google-apps.spreadsheet"
_TEXT_PLAIN_MIME = "text/plain"

_SHEET_ID_PATTERN: re.Pattern[str] = re.compile(r"/spreadsheets/d/([a-zA-Z0-9_-]+)")

_LDP_LOOKUP_PATHS: list[list[str]] = [
    ["02 TRABALHO", "DEFINIÇÕES"],
    ["02 TRABALHO", "DEFINIÇÕES", "Lista de definições"],
    ["DEFINIÇÕES"],
    ["DEFINIÇÕES", "Lista de definições"],
]


def parse_project_folder_name(folder_name: str) -> tuple[int, str, str]:
    """Extrai (number, client, full_name) do nome da pasta.

    Padrão: '<NUMERO> - <CLIENTE> - <RESTO>' (separador ' - ').

    Levanta ValueError se não bater.
    """
    raw = folder_name.strip()
    if not raw:
        raise ValueError("nome da pasta está vazio")

    segments = [s.strip() for s in raw.split(" - ")]
    if len(segments) < 2:
        raise ValueError(
            f"nome '{folder_name}' precisa ter ao menos 2 segmentos separados "
            f"por ' - ' (encontrado {len(segments)})"
        )

    first = segments[0]
    if not first.isdigit():
        raise ValueError(
            f"primeiro segmento '{first}' não é um número inteiro; "
            f"a pasta deve começar com o número do projeto"
        )

    project_number = int(first)
    client = segments[1]
    if not client:
        raise ValueError(f"segundo segmento (cliente) está vazio em '{folder_name}'")

    return project_number, client, raw


def build_drive_service() -> Resource:
    """Cria serviço Google Drive API v3 reusando a credencial de service account."""
    settings = get_settings()
    if not settings.google_service_account_json:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON not configured")

    creds = load_credentials(settings.google_service_account_json, _DRIVE_SCOPES)
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def build_drive_service_rw() -> Resource:
    """Variante com escopo de escrita — usada pelo folder_creator pra copiar templates.

    Service account precisa estar como Editor nas pastas alvo (107_PROJETOS) e na
    pasta template oficial. Mantemos esse builder separado do readonly pra deixar
    explícito quais callers fazem write no Drive.
    """
    settings = get_settings()
    if not settings.google_service_account_json:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON not configured")

    creds = load_credentials(settings.google_service_account_json, _DRIVE_RW_SCOPES)
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _escape_query_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


async def _list_files(
    service: Resource,
    query: str,
    fields: str = "files(id,name,mimeType,driveId)",
    page_size: int = 100,
) -> list[dict[str, Any]]:
    def _call() -> dict[str, Any]:
        return (
            service.files()
            .list(
                q=query,
                fields=fields,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                pageSize=page_size,
            )
            .execute()
        )

    result = await asyncio.to_thread(_call)
    files: list[dict[str, Any]] = result.get("files", [])
    return files


async def get_folder_metadata(service: Resource, folder_id: str) -> dict[str, Any]:
    """Retorna metadados básicos da pasta: id, name, mimeType, driveId."""

    def _call() -> dict[str, Any]:
        return (
            service.files()
            .get(
                fileId=folder_id,
                fields="id,name,mimeType,driveId",
                supportsAllDrives=True,
            )
            .execute()
        )

    metadata = await asyncio.to_thread(_call)
    if metadata.get("mimeType") != _FOLDER_MIME:
        raise ValueError(
            f"id '{folder_id}' não é uma pasta "
            f"(mimeType={metadata.get('mimeType')!r})"
        )
    return metadata


async def _find_subfolder_by_name(
    service: Resource,
    parent_id: str,
    name: str,
) -> str | None:
    escaped_name = _escape_query_value(name)
    query = (
        f"'{parent_id}' in parents and "
        f"mimeType='{_FOLDER_MIME}' and "
        f"name='{escaped_name}' and "
        f"trashed=false"
    )
    files = await _list_files(service, query, page_size=10)
    if not files:
        return None
    return str(files[0]["id"])


async def _list_spreadsheets_in_folder(
    service: Resource,
    folder_id: str,
) -> list[dict[str, Any]]:
    query = (
        f"'{folder_id}' in parents and "
        f"mimeType='{_SPREADSHEET_MIME}' and "
        f"trashed=false"
    )
    return await _list_files(service, query, page_size=50)


async def find_gsheet_in_project(
    service: Resource,
    project_folder_id: str,
) -> str | None:
    """Procura a primeira planilha .gsheet em locais conhecidos da pasta de projeto.

    Tenta nessa ordem:
      1. <projeto>/02 TRABALHO/DEFINIÇÕES/*.gsheet
      2. <projeto>/02 TRABALHO/DEFINIÇÕES/Lista de definições/*.gsheet
      3. <projeto>/DEFINIÇÕES/*.gsheet
      4. <projeto>/DEFINIÇÕES/Lista de definições/*.gsheet

    Se algum desses caminhos existir e tiver pelo menos uma planilha, retorna o
    sheet_id da primeira encontrada. Se nenhum caminho contiver planilhas,
    retorna None.
    """
    for path in _LDP_LOOKUP_PATHS:
        current_id: str | None = project_folder_id
        for segment in path:
            assert current_id is not None
            current_id = await _find_subfolder_by_name(service, current_id, segment)
            if current_id is None:
                break

        if current_id is None:
            continue

        sheets = await _list_spreadsheets_in_folder(service, current_id)
        if sheets:
            return str(sheets[0]["id"])

    return None


async def _list_link_text_files_in_folder(
    service: Resource,
    folder_id: str,
) -> list[dict[str, Any]]:
    query = (
        f"'{folder_id}' in parents and "
        f"mimeType='{_TEXT_PLAIN_MIME}' and "
        f"trashed=false"
    )
    files = await _list_files(service, query, page_size=50)
    return [f for f in files if "link" in str(f.get("name", "")).lower()]


async def _download_text_file(service: Resource, file_id: str) -> str | None:
    """Baixa o conteúdo de um arquivo do Drive como string utf-8.

    Retorna None em caso de falha (timeout, arquivo corrompido, etc.).
    """

    def _call() -> bytes:
        return (
            service.files()
            .get_media(fileId=file_id, supportsAllDrives=True)
            .execute()
        )

    try:
        data = await asyncio.to_thread(_call)
    except Exception as exc:
        print(f"AVISO: falha ao baixar arquivo {file_id}: {type(exc).__name__}: {exc}")
        return None

    if isinstance(data, bytes):
        return data.decode("utf-8", errors="replace")
    if isinstance(data, str):
        return data
    return None


async def find_sheet_id_via_link_txt(
    service: Resource,
    project_folder_id: str,
) -> tuple[str, str] | None:
    """Procura .txt com 'link' no nome em locais conhecidos e extrai sheet_id.

    Em cada caminho do `_LDP_LOOKUP_PATHS` lista arquivos `text/plain` cujo nome
    (case-insensitive) contenha 'link', baixa o conteúdo via Drive API e tenta
    extrair o sheet_id usando `_SHEET_ID_PATTERN`.

    Retorna (sheet_id, nome_do_arquivo_txt) na primeira ocorrência válida.
    Retorna None se nenhum caminho/arquivo render sheet_id.
    """
    for path in _LDP_LOOKUP_PATHS:
        current_id: str | None = project_folder_id
        for segment in path:
            assert current_id is not None
            current_id = await _find_subfolder_by_name(service, current_id, segment)
            if current_id is None:
                break

        if current_id is None:
            continue

        link_files = await _list_link_text_files_in_folder(service, current_id)
        for file in link_files:
            file_id = str(file["id"])
            file_name = str(file.get("name", ""))
            content = await _download_text_file(service, file_id)
            if content is None:
                continue
            match = _SHEET_ID_PATTERN.search(content)
            if match is None:
                print(
                    f"AVISO: arquivo '{file_name}' nao contem URL de "
                    f"Google Sheets valida"
                )
                continue
            return match.group(1), file_name

    return None


async def get_or_create_project(
    project_number: int,
    name: str,
    client: str,
    ldp_sheets_id: str,
) -> dict[str, Any]:
    """Garante que o projeto existe na tabela `projects` (chave: project_number).

    Se já existe: retorna {id, project_number, created: False}.
    Se não: insere e retorna {id, project_number, created: True}.

    Usa o pool global (init_db precisa ter sido chamado antes).
    """
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "SELECT id, project_number FROM projects WHERE project_number = %s",
                (project_number,),
            )
            existing = await cur.fetchone()
            if existing is not None:
                return {
                    "id": str(existing["id"]),
                    "project_number": existing["project_number"],
                    "created": False,
                }

            await cur.execute(
                """
                INSERT INTO projects (project_number, name, client, ldp_sheets_id, status)
                VALUES (%s, %s, %s, %s, 'active')
                RETURNING id, project_number
                """,
                (project_number, name, client, ldp_sheets_id),
            )
            row = await cur.fetchone()
            if row is None:
                raise RuntimeError("INSERT projects returned no row")
            return {
                "id": str(row["id"]),
                "project_number": row["project_number"],
                "created": True,
            }
