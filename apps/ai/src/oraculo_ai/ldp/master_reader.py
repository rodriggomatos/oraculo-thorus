"""Leitor da Master R04 da Lista de Definições.

A Master R04 é o template oficial Thórus de perguntas técnicas a fazer
em todo projeto, mantido fora do banco. Ao criar projeto novo, o sistema
lê as perguntas dessa planilha e popula `definitions` filtrando pelas
categorias LDP ativas.

Schema (canonical names + aliases) vive em
`oraculo_ai/ldp/schema/master_r04_schema.yaml` — adicionar variação de
nome de coluna não exige editar este arquivo. Apenas Disciplina, Tipo,
Fase, Item, Definições, Informação auxiliar, APOIO 1 e APOIO 2 são
copiados pra `definitions`; demais colunas (Status/Custo/Opção
escolhida/Observações/Validado) existem no template mas são preenchidas
por projeto, não pelo parser.

Cache: a master raramente muda; mantemos a leitura em memória até o
processo cair. Pra forçar refetch, chame `clear_master_cache()`.
"""

import asyncio
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
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


@dataclass(frozen=True)
class FieldSpec:
    name: str
    canonical: str
    aliases: tuple[str, ...]


_SCHEMA_PATH = Path(__file__).resolve().parent / "schema" / "master_r04_schema.yaml"

# Subconjunto do schema que o parser exige: campos faltantes nesse conjunto
# bloqueiam a leitura. As demais colunas (status/custo/opcao_escolhida/
# observacoes/validado) podem estar ausentes na planilha sem quebrar nada —
# o template lista, mas elas não viram dados em `definitions`.
_REQUIRED_FIELDS: tuple[str, ...] = (
    "disciplina",
    "tipo",
    "fase",
    "item_code",
    "pergunta",
    "informacao_auxiliar",
    "apoio_1",
    "apoio_2",
)


def _trim(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_header(value: Any) -> str:
    return str(value).strip().casefold()


def _normalize_alias(alias: str) -> str:
    return alias.strip().casefold()


@lru_cache(maxsize=1)
def _load_schema(path: str | None = None) -> dict[str, FieldSpec]:
    """Carrega o schema YAML uma vez por processo e retorna {field_name: FieldSpec}."""
    schema_path = Path(path) if path else _SCHEMA_PATH
    if not schema_path.is_file():
        raise FileNotFoundError(
            f"Schema da Master R04 não encontrado em {schema_path}. "
            "Esse arquivo é parte do código e deveria estar versionado."
        )
    try:
        raw = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(
            f"Schema da Master R04 ({schema_path}) tem YAML inválido: {exc}"
        ) from exc
    if not isinstance(raw, dict) or "fields" not in raw:
        raise ValueError(
            f"Schema da Master R04 ({schema_path}) sem chave 'fields' no nível raiz."
        )
    fields_raw = raw["fields"]
    if not isinstance(fields_raw, dict):
        raise ValueError(
            f"Schema da Master R04 ({schema_path}): 'fields' precisa ser um mapa."
        )
    out: dict[str, FieldSpec] = {}
    for name, spec in fields_raw.items():
        if not isinstance(spec, dict):
            raise ValueError(f"Schema malformado: campo {name!r} não é um mapa.")
        canonical = spec.get("canonical")
        aliases = spec.get("aliases", [])
        if not isinstance(canonical, str) or not canonical:
            raise ValueError(f"Schema malformado: campo {name!r} sem 'canonical'.")
        if not isinstance(aliases, list):
            raise ValueError(f"Schema malformado: campo {name!r} com 'aliases' não-lista.")
        out[name] = FieldSpec(
            name=name,
            canonical=canonical,
            aliases=tuple(_normalize_alias(a) for a in aliases),
        )
    missing_required = [f for f in _REQUIRED_FIELDS if f not in out]
    if missing_required:
        raise ValueError(
            f"Schema da Master R04 ({schema_path}) está sem campos obrigatórios: {missing_required}"
        )
    return out


def _map_header_to_indices(header: list[str]) -> dict[str, int]:
    """Mapeia cada campo obrigatório do schema ao índice da primeira coluna que casa por prefixo.

    Levanta ValueError com mensagem instrucional listando, pra cada campo faltante,
    o nome canônico, os aliases aceitos e os headers realmente presentes.
    """
    schema = _load_schema()
    normalized = [_normalize_header(h) for h in header]

    mapping: dict[str, int] = {}
    for field in _REQUIRED_FIELDS:
        spec = schema[field]
        for idx, head in enumerate(normalized):
            if any(head.startswith(alias) for alias in spec.aliases):
                mapping[field] = idx
                break

    missing = [f for f in _REQUIRED_FIELDS if f not in mapping]
    if missing:
        present = ", ".join(repr(h) for h in header) or "(nenhum)"
        details: list[str] = []
        for field in missing:
            spec = schema[field]
            aliases_human = ", ".join(repr(a) for a in spec.aliases)
            details.append(
                f"  - Coluna obrigatória {spec.canonical!r} não encontrada.\n"
                f"    Aliases aceitos: [{aliases_human}]"
            )
        raise ValueError(
            "Master R04 com header inválido.\n"
            f"Headers presentes: [{present}]\n"
            "Campos faltantes:\n"
            + "\n".join(details)
            + "\nVerifique se o nome da coluna na Master R04 está correto ou adicione um alias em "
            f"{_SCHEMA_PATH.relative_to(_SCHEMA_PATH.parents[3])}."
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
        item_code = _trim(padded[idx["item_code"]])
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
                    f"Não consigo acessar a Master R04 "
                    f"(id {spreadsheet_id!r}, aba {range_name!r}). "
                    "Confirma se a service account tem acesso de leitura."
                ) from exc
            raise
        return result.get("values", [])  # type: ignore[no-any-return]

    values = await asyncio.to_thread(_fetch)
    parsed = parse_master_rows(values)
    _master_cache = parsed
    return parsed
