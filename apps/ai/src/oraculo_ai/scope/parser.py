"""Parser da planilha de orçamento Thórus via Google Sheets API.

Lê APENAS o que pertence ao escopo do projeto pra gerar a Lista de Definições.
Tudo o resto (estado, área, fluxo, custo, total contratado, margem) ou vem do
form do user (estado) ou é responsabilidade da planilha de orçamento — não
desse parser.

Layout (aba 'orçamento'):

Disciplinas (R3:W46) — só campos de escopo:
  R: disciplina (nome — deve bater com scope_template.nome)
  S: incluir (bool)
  W: legal ('executivo' | 'legal')

A service account precisa estar compartilhada como leitora na planilha.
SpreadsheetNotFound vira PermissionError com mensagem orientando o user.
"""

import asyncio
import json
from pathlib import Path
from typing import Any

from googleapiclient.errors import HttpError

from oraculo_ai.core.config import get_settings
from oraculo_ai.ingestion.google_sheets.connector import build_sheets_service
from oraculo_ai.scope.types import DisciplinaRow, ParsedOrcamento


_SHEET_NAME = "orçamento"
_DISCIPLINAS_RANGE = f"{_SHEET_NAME}!R3:W46"


def _normalize_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    text = str(value).strip().lower()
    return text in {"true", "verdadeiro", "sim", "x", "1", "yes"}


def _trim(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _resolve_service_account_email(raw: str) -> str | None:
    """Best-effort: extrai client_email do JSON da service account (path ou inline)."""
    stripped = (raw or "").strip()
    if not stripped:
        return None
    try:
        if stripped.startswith("{"):
            data = json.loads(stripped)
        else:
            path = Path(stripped)
            if not path.is_file():
                return None
            data = json.loads(path.read_text(encoding="utf-8"))
        email = data.get("client_email")
        return str(email) if email else None
    except Exception:
        return None


async def parse_orcamento_from_sheets(spreadsheet_id: str) -> ParsedOrcamento:
    settings = get_settings()
    if not settings.google_service_account_json:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON not configured")

    service = build_sheets_service(settings.google_service_account_json)

    def _fetch_disciplinas() -> list[list[Any]]:
        try:
            result = (
                service.spreadsheets()
                .values()
                .get(
                    spreadsheetId=spreadsheet_id,
                    range=_DISCIPLINAS_RANGE,
                    valueRenderOption="UNFORMATTED_VALUE",
                )
                .execute()
            )
        except HttpError as exc:
            status = getattr(getattr(exc, "resp", None), "status", None)
            if status in (403, 404):
                sa_email = _resolve_service_account_email(settings.google_service_account_json)
                hint = (
                    f" Compartilhe-a como Leitor com {sa_email}."
                    if sa_email
                    else " Compartilhe-a como Leitor com a service account configurada."
                )
                raise PermissionError(
                    f"Não consigo acessar a planilha (id {spreadsheet_id!r})."
                    + hint
                ) from exc
            raise
        rows = result.get("values", [])
        return rows  # type: ignore[no-any-return]

    disciplinas_rows = await asyncio.to_thread(_fetch_disciplinas)

    disciplinas: list[DisciplinaRow] = []
    for offset, row in enumerate(disciplinas_rows):
        padded = list(row) + [None] * (6 - len(row))
        nome = _trim(padded[0])
        if nome is None:
            continue
        legal_raw = _trim(padded[5]) or "executivo"
        disciplinas.append(
            DisciplinaRow(
                disciplina=nome,
                incluir=_normalize_bool(padded[1]),
                legal=legal_raw,
                source_row=3 + offset,
            )
        )

    return ParsedOrcamento(
        spreadsheet_id=spreadsheet_id,
        disciplinas=disciplinas,
    )
