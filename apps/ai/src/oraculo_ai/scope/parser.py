"""Parser da planilha de orçamento Thórus via Google Sheets API.

Layout conhecido (aba 'orçamento'):

Inputs do operador:
  D2 → estado (SC/PR/MG/SP/RS/RO/ES)
  C3 → custo_fator
  D4 → fluxo (texto)
  G2 → area_m2

Disciplinas (R3:Z46):
  R: disciplina (nome — deve bater com scope_template.nome)
  S: incluir (bool)
  T: unificar (bool ou null)
  U: essencial (bool)
  V: pontos
  W: legal ('executivo' | 'legal')
  X: peso_disciplina
  Y: ponto_fixo
  Z: pontos_calculados

Agregados:
  G8  → total_contratado
  K16 → margem

A service account precisa estar compartilhada como leitora na planilha.
SpreadsheetNotFound vira PermissionError com mensagem orientando o user.
"""

import asyncio
from decimal import Decimal, InvalidOperation
from typing import Any

from googleapiclient.errors import HttpError

from oraculo_ai.core.config import get_settings
from oraculo_ai.ingestion.google_sheets.connector import build_sheets_service
from oraculo_ai.scope.types import DisciplinaRow, ParsedOrcamento


_SHEET_NAME = "orçamento"
_INPUT_RANGES: dict[str, str] = {
    "estado": f"{_SHEET_NAME}!D2",
    "custo_fator": f"{_SHEET_NAME}!C3",
    "fluxo": f"{_SHEET_NAME}!D4",
    "area_m2": f"{_SHEET_NAME}!G2",
    "total_contratado": f"{_SHEET_NAME}!G8",
    "margem": f"{_SHEET_NAME}!K16",
}
_DISCIPLINAS_RANGE = f"{_SHEET_NAME}!R3:Z46"


def _normalize_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    text = str(value).strip().lower()
    return text in {"true", "verdadeiro", "sim", "x", "1", "yes"}


def _normalize_optional_bool(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    return _normalize_bool(value)


def _parse_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    text = str(value).strip().replace(".", "").replace(",", ".") if "," in str(value) else str(value).strip()
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return None


def _parse_decimal_required(value: Any, default: Decimal = Decimal("0")) -> Decimal:
    parsed = _parse_decimal(value)
    return parsed if parsed is not None else default


def _trim(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


async def parse_orcamento_from_sheets(spreadsheet_id: str) -> ParsedOrcamento:
    settings = get_settings()
    if not settings.google_service_account_json:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON not configured")

    service = build_sheets_service(settings.google_service_account_json)

    def _batch_get(ranges: list[str]) -> dict[str, list[list[Any]]]:
        try:
            result = (
                service.spreadsheets()
                .values()
                .batchGet(
                    spreadsheetId=spreadsheet_id,
                    ranges=ranges,
                    valueRenderOption="UNFORMATTED_VALUE",
                )
                .execute()
            )
        except HttpError as exc:
            status = getattr(getattr(exc, "resp", None), "status", None)
            if status in (403, 404):
                raise PermissionError(
                    f"Não consegui acessar a planilha {spreadsheet_id!r}. "
                    f"Compartilhe-a como Leitor com o e-mail da service account "
                    f"(veja GOOGLE_SERVICE_ACCOUNT_JSON.client_email)."
                ) from exc
            raise
        out: dict[str, list[list[Any]]] = {}
        for value_range in result.get("valueRanges", []):
            range_name = value_range.get("range", "")
            out[range_name] = value_range.get("values", [])
        return out

    all_ranges = list(_INPUT_RANGES.values()) + [_DISCIPLINAS_RANGE]
    fetched = await asyncio.to_thread(_batch_get, all_ranges)

    def _scalar_at(range_name: str) -> Any:
        candidates = [k for k in fetched if range_name.split("!")[-1] in k]
        if not candidates:
            return None
        rows = fetched[candidates[0]]
        if not rows or not rows[0]:
            return None
        return rows[0][0]

    estado = _trim(_scalar_at(_INPUT_RANGES["estado"]))
    custo_fator = _parse_decimal(_scalar_at(_INPUT_RANGES["custo_fator"]))
    fluxo = _trim(_scalar_at(_INPUT_RANGES["fluxo"]))
    area_m2 = _parse_decimal(_scalar_at(_INPUT_RANGES["area_m2"]))
    total_contratado = _parse_decimal(_scalar_at(_INPUT_RANGES["total_contratado"]))
    margem = _parse_decimal(_scalar_at(_INPUT_RANGES["margem"]))

    disciplinas_rows: list[list[Any]] = []
    for key, rows in fetched.items():
        if "R3" in key:
            disciplinas_rows = rows
            break

    disciplinas: list[DisciplinaRow] = []
    for offset, row in enumerate(disciplinas_rows):
        padded = list(row) + [None] * (9 - len(row))
        nome = _trim(padded[0])
        if nome is None:
            continue
        legal_raw = _trim(padded[5]) or "executivo"
        disciplinas.append(
            DisciplinaRow(
                disciplina=nome,
                incluir=_normalize_bool(padded[1]),
                unificar=_normalize_optional_bool(padded[2]),
                essencial=_normalize_bool(padded[3]),
                pontos=_parse_decimal_required(padded[4]),
                legal=legal_raw,
                peso_disciplina=_parse_decimal(padded[6]),
                ponto_fixo=_parse_decimal(padded[7]),
                pontos_calculados=_parse_decimal_required(padded[8]),
                source_row=3 + offset,
            )
        )

    return ParsedOrcamento(
        spreadsheet_id=spreadsheet_id,
        estado=estado,
        custo_fator=custo_fator,
        fluxo=fluxo,
        area_m2=area_m2,
        total_contratado=total_contratado,
        margem=margem,
        disciplinas=disciplinas,
    )
