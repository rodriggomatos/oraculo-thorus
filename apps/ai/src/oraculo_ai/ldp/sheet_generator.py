"""Gera a planilha LDP do projeto a partir da Master R04.

Caminho A: copia a master inteira pra `02 TRABALHO/DEFINIÇÕES` da pasta do
projeto, renomeia, depois reescreve a aba "Lista de definições" com as
perguntas vigentes do `definitions` e preenche a aba "Projeto" com os
metadados básicos.

Helpers ficam puros (sem I/O) pra serem testáveis com fakes; o orchestrator
`generate_ldp_sheet` faz I/O na ordem certa e mapeia exceções dos clients
do Drive/Sheets pra erros tipados consumidos pelo endpoint.
"""

import asyncio
import logging
import unicodedata
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError

from oraculo_ai.core.config import get_settings
from oraculo_ai.document_ai.drive_scanner import build_drive_service_rw
from oraculo_ai.ingestion.google_sheets.connector import build_sheets_service
from oraculo_ai.projects.repository import (
    get_definitions_for_project,
    get_project_ldp_state,
    update_ldp_sheets_id,
)

_log = logging.getLogger(__name__)

_FOLDER_MIME = "application/vnd.google-apps.folder"
_DEFINICOES_TAB = "Lista de definições"
_PROJETO_TAB = "Projeto"
_DEFINITIONS_DATA_RANGE = f"'{_DEFINICOES_TAB}'!A2:M"
_PROJETO_SCAN_RANGE = f"'{_PROJETO_TAB}'!A1:Z80"

_DEFINITIONS_COLUMNS: tuple[str, ...] = (
    "disciplina",
    "tipo",
    "fase",
    "item_code",
    "pergunta",
    "status",
    "custo",
    "opcao_escolhida",
    "observacoes",
    "validado",
    "informacao_auxiliar",
    "apoio_1",
    "apoio_2",
)


@dataclass(frozen=True)
class CreateLdpSheetResult:
    sheets_id: str
    sheets_url: str
    sheets_name: str
    rows_written: int


class LdpSheetAlreadyExistsError(RuntimeError):
    """ldp_sheets_id já estava preenchido — não regera."""

    def __init__(self, existing_sheets_id: str) -> None:
        super().__init__(existing_sheets_id)
        self.existing_sheets_id = existing_sheets_id


class DriveFolderStructureError(RuntimeError):
    """Pasta `02 TRABALHO` ou `DEFINIÇÕES` ausente abaixo de drive_folder_path."""


class MasterNotAccessibleError(RuntimeError):
    """Service account não consegue ler a Master R04 (perm/404)."""


class DefinicoesParentNotEditableError(RuntimeError):
    """Service account não consegue escrever na pasta `DEFINIÇÕES` do projeto."""


class LdpSheetGenerationError(RuntimeError):
    """Falha genérica do Drive/Sheets API durante geração."""


def sheet_url_for(sheets_id: str) -> str:
    return f"https://docs.google.com/spreadsheets/d/{sheets_id}/edit"


def _strip_accents(text: str) -> str:
    return "".join(
        ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch)
    )


def _normalize(text: str) -> str:
    return _strip_accents(text).strip().casefold()


def _list_children(service: Resource, folder_id: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    page_token: str | None = None
    while True:
        kwargs: dict[str, Any] = dict(
            q=f"'{folder_id}' in parents and trashed=false",
            fields="nextPageToken, files(id,name,mimeType,parents)",
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


def _find_subfolder_by_name(
    service: Resource, parent_id: str, target_name: str
) -> dict[str, Any] | None:
    """Match case/acento-insensitive — Drive guarda o nome do jeito que o user salvou."""
    target = _normalize(target_name)
    for child in _list_children(service, parent_id):
        if str(child.get("mimeType") or "") != _FOLDER_MIME:
            continue
        if _normalize(str(child.get("name") or "")) == target:
            return child
    return None


def resolve_definicoes_folder(
    service: Resource, project_root_folder_id: str
) -> str:
    """Navega `{root}/02 TRABALHO/DEFINIÇÕES` e retorna o folder_id final.

    Levanta DriveFolderStructureError com mensagem específica indicando qual
    nível faltou.
    """
    trabalho = _find_subfolder_by_name(service, project_root_folder_id, "02 TRABALHO")
    if trabalho is None:
        raise DriveFolderStructureError(
            "Estrutura de pastas incompleta. Pasta '02 TRABALHO/DEFINIÇÕES' "
            "não encontrada. Crie manualmente ou recrie a pasta do projeto."
        )
    definicoes = _find_subfolder_by_name(service, str(trabalho["id"]), "DEFINIÇÕES")
    if definicoes is None:
        raise DriveFolderStructureError(
            "Estrutura de pastas incompleta. Pasta '02 TRABALHO/DEFINIÇÕES' "
            "não encontrada. Crie manualmente ou recrie a pasta do projeto."
        )
    return str(definicoes["id"])


def _stringify_cell(value: Any) -> Any:
    """Sheets API aceita primitivos; `None` vira string vazia pra não pular células."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return value
    return str(value)


def map_definitions_to_rows(definitions: list[dict[str, Any]]) -> list[list[Any]]:
    """Converte rows do banco em matriz pronta pra Sheets values.update.

    Ordem das colunas segue _DEFINITIONS_COLUMNS, que bate com a aba
    "Lista de definições" (A..M).
    """
    out: list[list[Any]] = []
    for row in definitions:
        out.append([_stringify_cell(row.get(col)) for col in _DEFINITIONS_COLUMNS])
    return out


def find_label_cell(
    grid: list[list[Any]], needle: str
) -> tuple[int, int] | None:
    """Procura o primeiro cell cujo texto contém `needle` (normalizado)."""
    target = _normalize(needle)
    for r, row in enumerate(grid):
        for c, cell in enumerate(row):
            if cell is None:
                continue
            if target in _normalize(str(cell)):
                return (r, c)
    return None


def _column_letter(index: int) -> str:
    """Converte índice 0-based pra letra do Sheets (0→A, 25→Z, 26→AA…)."""
    letters = ""
    n = index
    while True:
        letters = chr(ord("A") + (n % 26)) + letters
        n = n // 26 - 1
        if n < 0:
            break
    return letters


def projeto_tab_updates(
    grid: list[list[Any]],
    *,
    empreendimento: str | None,
    cidade: str | None,
    estado: str | None,
) -> list[dict[str, Any]]:
    """Decide o que escrever na aba "Projeto" via match de label.

    Procura "Nome do edifício" (ou "edifício") e "Cidade" e propõe escrever na
    célula imediatamente à direita do label. Retorna lista de updates no
    formato Sheets API ({range, values}). Se não encontrar label, omite o
    update — spec diz que é não-crítico.
    """
    updates: list[dict[str, Any]] = []
    width = max((len(r) for r in grid), default=0)

    def _push(label_cell: tuple[int, int] | None, value: str | None) -> None:
        if label_cell is None or not value:
            return
        r, c = label_cell
        if c + 1 >= width:
            return
        a1 = f"'{_PROJETO_TAB}'!{_column_letter(c + 1)}{r + 1}"
        updates.append({"range": a1, "values": [[value]]})

    edif_cell = find_label_cell(grid, "nome do edificio") or find_label_cell(
        grid, "edificio"
    )
    _push(edif_cell, empreendimento)

    cidade_cell = find_label_cell(grid, "cidade/uf") or find_label_cell(grid, "cidade")
    cidade_uf = None
    if cidade and estado:
        cidade_uf = f"{cidade} / {estado}"
    elif cidade:
        cidade_uf = cidade
    elif estado:
        cidade_uf = estado
    _push(cidade_cell, cidade_uf)

    return updates


def _drive_copy_master_to_definicoes(
    drive: Resource,
    *,
    master_id: str,
    target_folder_id: str,
    new_name: str,
) -> str:
    """Copia a master direto pra `target_folder_id` (sem move pós-cópia).

    Passar `parents` no body de `files.copy` faz a cópia nascer dentro da
    pasta destino — a SA precisa apenas de READ na master e WRITE em
    `target_folder_id`. SEM `parents`, Drive cria a cópia nos parents da
    master, exigindo WRITE na pasta da master também (que a SA não tem).

    Probe `files.get(master_id)` antes do copy distingue 403 da master
    (mensagem "master inacessível") do 403 do destino ("DEFINIÇÕES não
    editável") — essencial pra mensagem PT-BR ser acionável.
    """
    _log.info("Probing master access master_id=%s", master_id)
    try:
        drive.files().get(
            fileId=master_id, fields="id,name", supportsAllDrives=True
        ).execute()
    except HttpError as exc:
        status = getattr(getattr(exc, "resp", None), "status", None)
        if status in (403, 404):
            raise MasterNotAccessibleError(
                "Sem permissão para acessar a planilha master R04. Contate Rodrigo."
            ) from exc
        raise

    _log.info(
        "Copying master %s into target_folder_id=%s as %r",
        master_id,
        target_folder_id,
        new_name,
    )
    try:
        copied = (
            drive.files()
            .copy(
                fileId=master_id,
                body={"name": new_name, "parents": [target_folder_id]},
                fields="id,parents",
                supportsAllDrives=True,
            )
            .execute()
        )
    except HttpError as exc:
        status = getattr(getattr(exc, "resp", None), "status", None)
        if status in (403,):
            # Master já foi probed acima — 403 aqui aponta pro destino.
            raise DefinicoesParentNotEditableError(
                "Sem permissão para criar planilha na pasta DEFINIÇÕES. Service "
                "account precisa ser Editor. Contate Rodrigo."
            ) from exc
        raise

    new_id = str(copied["id"])
    _log.info("Master copied; new sheets_id=%s parents=%s", new_id, copied.get("parents"))
    return new_id


def _sheets_clear_range(sheets: Resource, sheets_id: str, range_a1: str) -> None:
    sheets.spreadsheets().values().clear(
        spreadsheetId=sheets_id, range=range_a1, body={}
    ).execute()


def _sheets_update_range(
    sheets: Resource, sheets_id: str, range_a1: str, values: list[list[Any]]
) -> None:
    sheets.spreadsheets().values().update(
        spreadsheetId=sheets_id,
        range=range_a1,
        valueInputOption="USER_ENTERED",
        body={"values": values},
    ).execute()


def _sheets_get_grid(sheets: Resource, sheets_id: str, range_a1: str) -> list[list[Any]]:
    payload = (
        sheets.spreadsheets()
        .values()
        .get(spreadsheetId=sheets_id, range=range_a1, valueRenderOption="FORMATTED_VALUE")
        .execute()
    )
    return payload.get("values", [])


def _sheets_batch_update(
    sheets: Resource, sheets_id: str, updates: list[dict[str, Any]]
) -> None:
    if not updates:
        return
    sheets.spreadsheets().values().batchUpdate(
        spreadsheetId=sheets_id,
        body={"valueInputOption": "USER_ENTERED", "data": updates},
    ).execute()


def _generate_ldp_sheet_blocking(
    state: dict[str, Any],
    definitions: list[dict[str, Any]],
) -> CreateLdpSheetResult:
    """Implementação síncrona — `generate_ldp_sheet` envolve com `asyncio.to_thread`."""
    settings = get_settings()
    master_id = settings.ldp_master_sheet_id
    project_number = int(state["project_number"])
    project_folder_id = str(state["drive_folder_path"])
    new_name = f"Lista de definição - {project_number}"

    _log.info(
        "LDP sheet pipeline begin project_number=%d project_folder_id=%s",
        project_number,
        project_folder_id,
    )

    drive = build_drive_service_rw()
    sheets = build_sheets_service(settings.google_service_account_json)

    _log.info("Resolving DEFINIÇÕES folder under project_folder_id=%s", project_folder_id)
    target_folder_id = resolve_definicoes_folder(drive, project_folder_id)
    _log.info("DEFINIÇÕES folder resolved: %s", target_folder_id)

    new_sheets_id = _drive_copy_master_to_definicoes(
        drive,
        master_id=master_id,
        target_folder_id=target_folder_id,
        new_name=new_name,
    )

    try:
        _log.info("Clearing 'Lista de definições' range on sheets_id=%s", new_sheets_id)
        _sheets_clear_range(sheets, new_sheets_id, _DEFINITIONS_DATA_RANGE)

        rows = map_definitions_to_rows(definitions)
        if rows:
            _log.info(
                "Writing %d definition rows into sheets_id=%s", len(rows), new_sheets_id
            )
            _sheets_update_range(
                sheets,
                new_sheets_id,
                f"'{_DEFINICOES_TAB}'!A2",
                rows,
            )

        _log.info("Reading 'Projeto' tab grid on sheets_id=%s", new_sheets_id)
        projeto_grid = _sheets_get_grid(sheets, new_sheets_id, _PROJETO_SCAN_RANGE)
        updates = projeto_tab_updates(
            projeto_grid,
            empreendimento=state.get("empreendimento"),
            cidade=state.get("cidade"),
            estado=state.get("estado"),
        )
        if updates:
            _log.info(
                "Applying %d 'Projeto' tab cell updates on sheets_id=%s",
                len(updates),
                new_sheets_id,
            )
        _sheets_batch_update(sheets, new_sheets_id, updates)
    except HttpError as exc:
        # Best-effort cleanup: deleta a planilha que copiamos pra não deixar
        # lixo flutuando se o ajuste pós-cópia falhou. Erros do delete são
        # silenciados — o erro original é o que importa.
        _log.exception(
            "Sheets API failed after copy; attempting cleanup of sheets_id=%s",
            new_sheets_id,
        )
        try:
            drive.files().delete(fileId=new_sheets_id, supportsAllDrives=True).execute()
        except Exception:
            _log.exception("Falha limpando planilha LDP %s após erro", new_sheets_id)
        raise LdpSheetGenerationError(
            f"Sheets API falhou durante geração: {exc}"
        ) from exc

    return CreateLdpSheetResult(
        sheets_id=new_sheets_id,
        sheets_url=sheet_url_for(new_sheets_id),
        sheets_name=new_name,
        rows_written=len(definitions),
    )


async def generate_ldp_sheet(project_id: UUID) -> CreateLdpSheetResult:
    """Cria a planilha LDP do projeto a partir da Master R04.

    Pre-checks no banco antes de tocar Drive/Sheets:
      - Projeto existe
      - drive_folder_path != NULL  → senão DriveFolderStructureError textual
      - ldp_sheets_id == NULL      → senão LdpSheetAlreadyExistsError
      - definitions tem linhas     → senão ValueError (mapeado pelo caller)

    O caller (endpoint) traduz exceções em mensagens PT-BR pro usuário.
    """
    state = await get_project_ldp_state(project_id)
    if state is None:
        raise LookupError(f"projeto {project_id} não encontrado")
    if not state.get("drive_folder_path"):
        raise DriveFolderStructureError("Crie a pasta no Drive primeiro.")
    if state.get("ldp_sheets_id"):
        raise LdpSheetAlreadyExistsError(str(state["ldp_sheets_id"]))

    definitions = await get_definitions_for_project(project_id)
    if not definitions:
        raise ValueError("Projeto não tem perguntas geradas. Recrie o projeto.")

    result = await asyncio.to_thread(_generate_ldp_sheet_blocking, state, definitions)

    persisted = await update_ldp_sheets_id(project_id, result.sheets_id)
    if not persisted:
        _log.error(
            "LDP sheet %s criada mas projeto %s sumiu antes de salvar",
            result.sheets_id,
            project_id,
        )
        raise LdpSheetGenerationError(
            "Planilha criada mas projeto sumiu antes de salvar — contate o admin."
        )
    return result
