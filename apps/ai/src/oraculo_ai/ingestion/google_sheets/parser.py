"""Sheets row → Definition Pydantic."""

from typing import Any
from uuid import UUID

from oraculo_ai.ingestion.schema import Definition


COLUMN_MAP: dict[str, str] = {
    "Geral": "disciplina",
    "Tipo": "tipo",
    "Fase 02": "fase",
    "Item": "item_code",
    "Definições": "pergunta",
    "Status": "status",
    "Custo": "custo",
    "Opção escolhida": "opcao_escolhida",
    "Observações": "observacoes",
    "Validado": "validado",
    "Informação auxiliar": "informacao_auxiliar",
    "APOIO 1": "apoio_1",
    "APOIO 2": "apoio_2",
}


_TRUTHY = {"sim", "yes", "y", "true", "1", "x", "ok", "validado"}


def _to_str(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def _parse_validado(value: Any) -> bool:
    if value is None:
        return False
    return str(value).strip().lower() in _TRUTHY


def parse_row(
    row: dict[str, str],
    project_id: UUID,
    source_sheet_id: str,
    source_row: int,
) -> Definition | None:
    item_code = _to_str(row.get("Item"))
    if not item_code:
        return None

    pergunta = _to_str(row.get("Definições")) or ""

    return Definition(
        project_id=project_id,
        disciplina=_to_str(row.get("Geral")),
        tipo=_to_str(row.get("Tipo")),
        fase=_to_str(row.get("Fase 02")),
        item_code=item_code,
        pergunta=pergunta,
        opcao_escolhida=_to_str(row.get("Opção escolhida")),
        status=_to_str(row.get("Status")),
        custo=_to_str(row.get("Custo")),
        observacoes=_to_str(row.get("Observações")),
        validado=_parse_validado(row.get("Validado")),
        informacao_auxiliar=_to_str(row.get("Informação auxiliar")),
        apoio_1=_to_str(row.get("APOIO 1")),
        apoio_2=_to_str(row.get("APOIO 2")),
        source_sheet_id=source_sheet_id,
        source_row=source_row,
        raw_data=dict(row),
    )
