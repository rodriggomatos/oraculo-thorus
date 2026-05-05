"""Leitor da Master R04 da Lista de Definições.

A Master R04 é o template oficial Thórus de perguntas técnicas a fazer
em todo projeto, mantido fora do banco. Ao criar projeto novo, o sistema
lê as perguntas dessa planilha e popula `definitions` filtrando pelas
categorias LDP ativas.

Layout da aba (header obrigatório):
  Disciplina | Tipo | Fase | Item | Definições | Status | Custo |
  Opção escolhida | Observações | Validado | Informação auxiliar |
  APOIO 1 | APOIO 2

Apenas Disciplina, Tipo, Fase, Item, Definições, Informação auxiliar,
APOIO 1, APOIO 2 são copiados pra `definitions`. Status/Custo/Opção
escolhida/Observações/Validado vêm do preenchimento por projeto, não
do template.

Cache: a master raramente muda; mantemos a leitura em memória até o
processo cair. Pra forçar refetch, chame `clear_master_cache()`.
"""

import asyncio
from typing import Any

from googleapiclient.errors import HttpError
from pydantic import BaseModel

from oraculo_ai.core.config import get_settings
from oraculo_ai.ingestion.google_sheets.connector import build_sheets_service


class MasterRow(BaseModel):
    disciplina: str
    tipo: str | None = None
    fase: str | None = None
    item_code: str
    pergunta: str
    informacao_auxiliar: str | None = None
    apoio_1: str | None = None
    apoio_2: str | None = None
    source_row: int


# Match por prefixo case-insensitive: tolerante a variações como
# "Informação auxiliar para tomada de decisão (EX: …)" — basta o header começar
# com algum dos prefixos canônicos.
_FIELD_PREFIXES: dict[str, tuple[str, ...]] = {
    "disciplina": ("disciplina",),
    "tipo": ("tipo",),
    "fase": ("fase",),
    "item": ("item",),
    "pergunta": ("definições", "definicoes", "pergunta"),
    "informacao_auxiliar": ("informação auxiliar", "informacao auxiliar"),
    "apoio_1": ("apoio 1", "apoio_1"),
    "apoio_2": ("apoio 2", "apoio_2"),
}


def _trim(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_header(value: Any) -> str:
    return str(value).strip().casefold()


def _map_header_to_indices(header: list[str]) -> dict[str, int]:
    """Mapeia cada campo canônico ao índice da primeira coluna que casa por prefixo.

    Levanta ValueError listando os campos que ficaram sem coluna correspondente.
    """
    normalized = [_normalize_header(h) for h in header]
    mapping: dict[str, int] = {}
    for field, prefixes in _FIELD_PREFIXES.items():
        for idx, head in enumerate(normalized):
            if any(head.startswith(p) for p in prefixes):
                mapping[field] = idx
                break
    missing = [f for f in _FIELD_PREFIXES if f not in mapping]
    if missing:
        raise ValueError(
            f"Master R04 com header inválido — faltam colunas: {missing} (header: {header!r})"
        )
    return mapping


def parse_master_rows(values: list[list[Any]]) -> list[MasterRow]:
    """Parser puro — recebe `values` no formato Sheets API (lista de listas).

    Pula header e linhas sem `Item` ou `Definições` (linhas brancas).
    """
    if not values:
        return []

    header = [str(h).strip() for h in values[0]]
    idx = _map_header_to_indices(header)
    width = len(header)

    out: list[MasterRow] = []
    for offset, raw in enumerate(values[1:]):
        padded = list(raw) + [None] * (width - len(raw))
        item_code = _trim(padded[idx["item"]])
        pergunta = _trim(padded[idx["pergunta"]])
        if not item_code or not pergunta:
            continue
        disciplina = _trim(padded[idx["disciplina"]])
        if not disciplina:
            continue
        out.append(
            MasterRow(
                disciplina=disciplina,
                tipo=_trim(padded[idx["tipo"]]),
                fase=_trim(padded[idx["fase"]]),
                item_code=item_code,
                pergunta=pergunta,
                informacao_auxiliar=_trim(padded[idx["informacao_auxiliar"]]),
                apoio_1=_trim(padded[idx["apoio_1"]]),
                apoio_2=_trim(padded[idx["apoio_2"]]),
                source_row=2 + offset,
            )
        )
    return out


_master_cache: list[MasterRow] | None = None


def clear_master_cache() -> None:
    global _master_cache
    _master_cache = None


async def read_master_r04() -> list[MasterRow]:
    """Lê (e cacheia) a Master R04 do Google Sheets.

    Spreadsheet/aba configuráveis via `LDP_MASTER_SHEET_ID` / `LDP_MASTER_TAB`.
    """
    global _master_cache
    if _master_cache is not None:
        return _master_cache

    settings = get_settings()
    if not settings.google_service_account_json:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON not configured")

    service = build_sheets_service(settings.google_service_account_json)
    spreadsheet_id = settings.ldp_master_sheet_id
    range_name = settings.ldp_master_tab

    def _fetch() -> list[list[Any]]:
        try:
            result = (
                service.spreadsheets()
                .values()
                .get(
                    spreadsheetId=spreadsheet_id,
                    range=range_name,
                    valueRenderOption="UNFORMATTED_VALUE",
                )
                .execute()
            )
        except HttpError as exc:
            status = getattr(getattr(exc, "resp", None), "status", None)
            if status in (403, 404):
                raise PermissionError(
                    f"Não consigo acessar a Master R04 (id {spreadsheet_id!r}, aba {range_name!r}). "
                    "Confirma se a service account tem acesso de leitura."
                ) from exc
            raise
        return result.get("values", [])  # type: ignore[no-any-return]

    values = await asyncio.to_thread(_fetch)
    parsed = parse_master_rows(values)
    _master_cache = parsed
    return parsed
