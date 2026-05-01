"""Ingestor LDP a partir de Google Sheets — header mapping híbrido (aliases + LLM)."""

import asyncio
import hashlib
import json
import os
from typing import Any
from uuid import UUID

import instructor
from pydantic import BaseModel

from oraculo_ai.core.config import get_settings
from oraculo_ai.document_ai.repository import SourceDocumentsRepository
from oraculo_ai.document_ai.schemas import (
    HeaderMappingResult,
    SheetsIngestionStats,
)
from oraculo_ai.ingestion.google_sheets.connector import build_sheets_service
from oraculo_ai.ingestion.google_sheets.pipeline import register_definition_version
from oraculo_ai.ingestion.google_sheets.repository import SheetsRepository


ALIASES_BY_CANONICAL_FIELD: dict[str, list[str]] = {
    "disciplina": [
        "Geral",
        "Disciplina",
        "Categoria",
        "Setor",
        "Sanitário",
        "Hidráulica",
        "Elétrico / Comunicação",
        "Climatização",
        "Preventivo",
    ],
    "tipo": ["Tipo", "Subseção", "Setor"],
    "fase": ["Fase", "Fase 02", "Etapa"],
    "item_code": ["Item", "Item ", "Código", "Cód", "ID"],
    "pergunta": [
        "Definições",
        "Definições ",
        "Pergunta",
        "Item de definição",
        "Definição",
    ],
    "status": ["Status"],
    "custo": ["Custo"],
    "opcao_escolhida": ["Opção escolhida", "Resposta", "Decisão"],
    "observacoes": ["Observações", "Obs", "Comentários"],
    "validado": ["Validado", "Aprovado", "OK?"],
    "informacao_auxiliar": [
        "Informação auxiliar para tomada de decisão (EX: exemplo)",
        "Info auxiliar",
        "Auxiliar",
        "Informação auxiliar",
    ],
    "apoio_1": ["APOIO 1", "Apoio 1"],
    "apoio_2": ["APOIO 2", "Apoio 2"],
}


CANONICAL_FIELDS: list[str] = list(ALIASES_BY_CANONICAL_FIELD.keys())

REQUIRED_CANONICAL_FIELDS: list[str] = [
    "disciplina",
    "tipo",
    "fase",
    "item_code",
    "pergunta",
]


_HEADER_MAPPING_MODEL = "claude-haiku-4-5"
_HEADER_MAPPING_COST_USD = 0.01


class HeaderMappingFromLLM(BaseModel):
    disciplina: int | None = None
    tipo: int | None = None
    fase: int | None = None
    item_code: int | None = None
    pergunta: int | None = None
    status: int | None = None
    custo: int | None = None
    opcao_escolhida: int | None = None
    observacoes: int | None = None
    validado: int | None = None
    informacao_auxiliar: int | None = None
    apoio_1: int | None = None
    apoio_2: int | None = None
    reasoning: str | None = None


_LLM_SYSTEM_PROMPT = """Você recebe headers e amostra de 3 linhas de uma planilha Google Sheets de uma Lista de Definições de Projeto da Thórus Engenharia.

Sua tarefa: mapear cada campo canônico Thórus para o ÍNDICE (0-based) da coluna correspondente na planilha.

CAMPOS CANÔNICOS:
- disciplina (ex: Elétrico, Hidráulica, Sanitário)
- tipo (ex: Apartamento, Área comum, Comercial)
- fase (ex: Fase 00, Fase 01, Fase 02)
- item_code (ex: 1, 7, 85)
- pergunta (texto longo, ex: "Qual o tipo de máquina de climatização?")
- status (ex: Em análise, Validado)
- custo (ex: Sim, vazio)
- opcao_escolhida (texto)
- observacoes (texto)
- validado (booleano: TRUE/FALSE)
- informacao_auxiliar (texto longo com EX:)
- apoio_1 (texto curto)
- apoio_2 (texto curto)

DICAS:
- Se o header estiver errado, OLHE OS DADOS na sample_rows pra inferir o campo
- Ex: header diz "Sanitário" mas coluna tem "Elétrico", "Hidráulica" → é disciplina
- Se algum campo canônico não tem coluna correspondente, retorne None pra ele
"""


def _normalize(s: str) -> str:
    return s.strip().lower()


def try_map_headers_by_aliases(headers: list[str]) -> dict[str, int] | None:
    normalized_headers = [_normalize(h) for h in headers]
    mapping: dict[str, int | None] = {}

    for field, aliases in ALIASES_BY_CANONICAL_FIELD.items():
        found_idx: int | None = None
        for alias in aliases:
            normalized_alias = _normalize(alias)
            for idx, header in enumerate(normalized_headers):
                if header == normalized_alias:
                    found_idx = idx
                    break
            if found_idx is not None:
                break
        mapping[field] = found_idx

    missing_required = [
        f for f in REQUIRED_CANONICAL_FIELDS if mapping.get(f) is None
    ]
    if missing_required:
        return None
    return {k: v for k, v in mapping.items() if v is not None or k not in REQUIRED_CANONICAL_FIELDS}


async def map_headers_with_llm(
    headers: list[str],
    sample_rows: list[list[str]],
) -> dict[str, int | None]:
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY não configurada — necessária para fallback LLM "
            "de header mapping"
        )

    os.environ["ANTHROPIC_API_KEY"] = settings.anthropic_api_key

    client = instructor.from_provider(
        f"anthropic/{_HEADER_MAPPING_MODEL}",
        async_client=True,
        mode=instructor.Mode.ANTHROPIC_TOOLS,
    )

    headers_text = json.dumps(headers, ensure_ascii=False)
    sample_text = json.dumps(sample_rows, ensure_ascii=False, indent=2)
    user_prompt = (
        f"HEADERS (linha 1, índices 0-based):\n{headers_text}\n\n"
        f"SAMPLE_ROWS (até 3 linhas de dados):\n{sample_text}\n\n"
        f"Mapeie cada campo canônico para o índice da coluna correspondente."
    )

    result = await client.create(
        messages=[
            {"role": "system", "content": _LLM_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_model=HeaderMappingFromLLM,
        max_tokens=2000,
    )

    return {
        "disciplina": result.disciplina,
        "tipo": result.tipo,
        "fase": result.fase,
        "item_code": result.item_code,
        "pergunta": result.pergunta,
        "status": result.status,
        "custo": result.custo,
        "opcao_escolhida": result.opcao_escolhida,
        "observacoes": result.observacoes,
        "validado": result.validado,
        "informacao_auxiliar": result.informacao_auxiliar,
        "apoio_1": result.apoio_1,
        "apoio_2": result.apoio_2,
    }


def _trim_or_none(raw: object) -> str | None:
    s = str(raw).strip()
    return s or None


def _normalize_validado(raw: str | None) -> bool | None:
    if raw is None:
        return None
    v = raw.strip().upper()
    if not v:
        return None
    if v in ("TRUE", "SIM", "X", "VALIDADO", "OK", "Y", "YES"):
        return True
    if v in ("FALSE", "NAO", "NÃO", "-", "N", "NO"):
        return False
    return None


def _read_sheet_values_raw(
    service: Any,
    spreadsheet_id: str,
    sheet_name: str,
) -> list[list[str]]:
    result = (
        service.spreadsheets()
        .values()
        .get(
            spreadsheetId=spreadsheet_id,
            range=sheet_name,
            valueRenderOption="FORMATTED_VALUE",
        )
        .execute()
    )
    return result.get("values", [])


def _build_content_markdown(
    headers: list[str],
    rows: list[list[str]],
    limit: int = 50,
) -> str:
    if not headers:
        return ""
    sample = rows[:limit]
    width = len(headers)
    lines: list[str] = []
    safe_headers = [str(h).replace("|", "\\|") or "?" for h in headers]
    lines.append("| " + " | ".join(safe_headers) + " |")
    lines.append("|" + "|".join(["---"] * width) + "|")
    for row in sample:
        padded = list(row) + [""] * (width - len(row))
        cells = [
            str(c).replace("|", "\\|").replace("\n", " ")
            for c in padded[:width]
        ]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _hash_rows(rows: list[list[str]]) -> str:
    flat = "\n".join("\t".join(str(c) for c in row) for row in rows)
    return hashlib.sha256(flat.encode("utf-8")).hexdigest()


async def ingest_from_sheets(
    project_number: int,
    sheet_id: str,
    sheet_tab: str = "Lista de definições",
) -> SheetsIngestionStats:
    settings = get_settings()
    if not settings.google_service_account_json:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON not configured")

    stats = SheetsIngestionStats(
        project_number=project_number,
        sheet_id=sheet_id,
        sheet_tab=sheet_tab,
    )

    service = build_sheets_service(settings.google_service_account_json)
    raw_rows = await asyncio.to_thread(
        _read_sheet_values_raw, service, sheet_id, sheet_tab
    )

    if not raw_rows:
        return stats

    headers = [str(h).strip() for h in raw_rows[0]]
    data_rows = [list(r) for r in raw_rows[1:]]
    stats.rows_total = len(data_rows)

    alias_result = try_map_headers_by_aliases(headers)

    if alias_result is not None:
        mapping: dict[str, int | None] = {f: alias_result.get(f) for f in CANONICAL_FIELDS}
        method: str = "default_aliases"
        llm_cost = 0.0
    else:
        sample_rows = [list(r) for r in data_rows[:3]]
        mapping = await map_headers_with_llm(headers, sample_rows)
        method = "llm_assisted"
        llm_cost = _HEADER_MAPPING_COST_USD

    mapped_indices = {idx for idx in mapping.values() if idx is not None}
    unmapped_headers = [h for i, h in enumerate(headers) if i not in mapped_indices]

    stats.header_mapping = HeaderMappingResult(
        method=method,
        mapping=dict(mapping),
        unmapped_headers=unmapped_headers,
        llm_cost_estimate_usd=llm_cost,
    )

    missing = [f for f in REQUIRED_CANONICAL_FIELDS if mapping.get(f) is None]
    if missing:
        raise RuntimeError(
            f"Header mapping não resolveu campos obrigatórios mesmo via {method}: "
            f"{missing}. Headers da planilha: {headers}"
        )

    async with (
        SheetsRepository() as sheets_repo,
        SourceDocumentsRepository() as docs_repo,
    ):
        project = await sheets_repo.get_project_by_number(project_number)
        if project is None:
            raise RuntimeError(
                f"project number {project_number} not found in `projects` table"
            )
        project_id: UUID = project["id"]

        content_hash = _hash_rows(raw_rows)
        existing = await docs_repo.find_by_hash(project_id, content_hash)
        if existing is not None:
            stats.skipped_already_processed = True
            stats.source_document_id = str(existing["id"])
            return stats

        content_markdown = _build_content_markdown(headers, data_rows, limit=50)
        source_document_id = await docs_repo.create(
            project_id=project_id,
            filename=f"sheet_{sheet_id}_{sheet_tab}",
            file_format="google_sheets",
            content_hash=content_hash,
            content_markdown=content_markdown,
            metadata={
                "sheet_id": sheet_id,
                "sheet_tab": sheet_tab,
                "mapping_method": method,
                "header_mapping": dict(mapping),
                "rows_total": len(data_rows),
            },
        )
        stats.source_document_id = str(source_document_id)

    fonte_descricao = f"Planilha {sheet_id} - aba {sheet_tab}"

    for offset, row in enumerate(data_rows):
        try:
            if not any(str(c).strip() for c in row):
                stats.rows_skipped_empty += 1
                continue

            def get(field: str) -> str:
                col_idx = mapping.get(field)
                if col_idx is None or col_idx >= len(row):
                    return ""
                return str(row[col_idx])

            item_code = _trim_or_none(get("item_code"))
            pergunta = _trim_or_none(get("pergunta"))

            if not item_code or not pergunta:
                stats.rows_skipped_invalid += 1
                continue

            await register_definition_version(
                project_number=project_number,
                item_code=item_code,
                pergunta=pergunta,
                opcao_escolhida=_trim_or_none(get("opcao_escolhida")),
                disciplina=_trim_or_none(get("disciplina")),
                tipo=_trim_or_none(get("tipo")),
                fase=_trim_or_none(get("fase")),
                status=_trim_or_none(get("status")),
                fonte_informacao="google_sheets_document_ai",
                fonte_descricao=fonte_descricao,
                source_document_id=source_document_id,
                custo=_trim_or_none(get("custo")),
                observacoes=_trim_or_none(get("observacoes")),
                validado=_normalize_validado(get("validado")),
                informacao_auxiliar=_trim_or_none(get("informacao_auxiliar")),
                apoio_1=_trim_or_none(get("apoio_1")),
                apoio_2=_trim_or_none(get("apoio_2")),
            )
            stats.rows_processed += 1
        except Exception as exc:
            stats.rows_with_error += 1
            stats.errors.append(
                f"Linha {offset + 2}: {type(exc).__name__}: {exc}"
            )

    return stats
