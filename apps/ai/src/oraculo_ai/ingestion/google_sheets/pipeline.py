"""Pipeline de ingestão Google Sheets — orquestra connect → read → parse → upsert."""

import asyncio
from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

from oraculo_ai.core.config import get_settings
from oraculo_ai.ingestion.google_sheets.connector import build_sheets_service, read_sheet
from oraculo_ai.ingestion.google_sheets.content import build_chunk_text, compute_hash
from oraculo_ai.ingestion.google_sheets.parser import parse_row
from oraculo_ai.ingestion.google_sheets.repository import ChunksVectorStore, SheetsRepository
from oraculo_ai.ingestion.schema import Definition, IngestionStats


_INITIAL_SOURCE = "lista_definicoes_inicial"
_INITIAL_DESCRICAO = "Ingestão inicial da planilha LDP"


async def run_ingestion(
    project_number: int,
    sheet_name: str = "Lista de definições",
) -> IngestionStats:
    settings = get_settings()

    if not settings.google_service_account_json:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON not configured")

    stats = IngestionStats()
    today = date.today()
    registered_at = datetime.now(timezone.utc).isoformat()

    async with (
        SheetsRepository() as repo,
        ChunksVectorStore() as chunks_store,
    ):
        project = await repo.get_project_by_number(project_number)
        if project is None:
            raise RuntimeError(
                f"project number {project_number} not found in `projects` table"
            )
        spreadsheet_id = project.get("google_sheet_id")
        if not spreadsheet_id:
            raise RuntimeError(
                f"project {project_number} has no google_sheet_id set"
            )

        project_id: UUID = project["id"]

        service = build_sheets_service(settings.google_service_account_json)
        rows = await asyncio.to_thread(read_sheet, service, spreadsheet_id, sheet_name)
        stats.total_rows = len(rows)

        for index, row in enumerate(rows, start=2):
            definition = parse_row(
                row=row,
                project_id=project_id,
                source_sheet_id=spreadsheet_id,
                source_row=index,
            )
            if definition is None:
                continue

            definition.fonte_informacao = _INITIAL_SOURCE
            definition.fonte_descricao = _INITIAL_DESCRICAO
            definition.data_informacao = today

            def_id, was_inserted = await repo.upsert_definition(definition)
            if was_inserted:
                stats.definitions_created += 1
            else:
                stats.definitions_updated += 1

            content = build_chunk_text(definition)
            content_hash = compute_hash(content)

            existing = await chunks_store.fetch_existing_node_id_for_source(
                "definitions", def_id
            )
            if existing is not None and existing[1] == content_hash:
                stats.chunks_unchanged += 1
                continue

            metadata_extra: dict[str, str] = {
                "disciplina": definition.disciplina or "",
                "tipo": definition.tipo or "",
                "fase": definition.fase or "",
                "item_code": definition.item_code,
                "source_row": str(definition.source_row) if definition.source_row else "",
                "project_number": str(project["project_number"]),
                "fonte_informacao": _INITIAL_SOURCE,
                "fonte_descricao": _INITIAL_DESCRICAO,
                "data_informacao": today.isoformat(),
                "registrado_em": registered_at,
            }

            existing_node_id = existing[0] if existing is not None else None
            await chunks_store.add_or_update(
                definition_id=def_id,
                project_id=project_id,
                content=content,
                content_hash=content_hash,
                metadata_extra=metadata_extra,
                existing_node_id=existing_node_id,
            )
            stats.embedding_calls += 1
            if existing_node_id is None:
                stats.chunks_created += 1
            else:
                stats.chunks_updated += 1

    return stats


async def register_definition_version(
    project_number: int,
    item_code: str,
    pergunta: str,
    opcao_escolhida: str | None,
    disciplina: str | None,
    tipo: str | None,
    fase: str | None,
    status: str | None,
    fonte_informacao: str,
    fonte_descricao: str,
    data_informacao: date | None = None,
) -> dict[str, Any]:
    effective_date = data_informacao or date.today()
    registered_at = datetime.now(timezone.utc).isoformat()

    async with (
        SheetsRepository() as repo,
        ChunksVectorStore() as chunks_store,
    ):
        project = await repo.get_project_by_number(project_number)
        if project is None:
            raise RuntimeError(
                f"project number {project_number} not found in `projects` table"
            )
        project_id: UUID = project["id"]

        definition = Definition(
            project_id=project_id,
            disciplina=disciplina,
            tipo=tipo,
            fase=fase,
            item_code=item_code,
            pergunta=pergunta,
            opcao_escolhida=opcao_escolhida,
            status=status,
            data_informacao=effective_date,
            fonte_informacao=fonte_informacao,
            fonte_descricao=fonte_descricao,
        )

        def_id = await repo.insert_definition_version(definition)

        content = build_chunk_text(definition)
        content_hash = compute_hash(content)

        metadata_extra: dict[str, str] = {
            "disciplina": disciplina or "",
            "tipo": tipo or "",
            "fase": fase or "",
            "item_code": item_code,
            "project_number": str(project["project_number"]),
            "fonte_informacao": fonte_informacao,
            "fonte_descricao": fonte_descricao,
            "data_informacao": effective_date.isoformat(),
            "registrado_em": registered_at,
        }

        node_id = await chunks_store.add_or_update(
            definition_id=def_id,
            project_id=project_id,
            content=content,
            content_hash=content_hash,
            metadata_extra=metadata_extra,
            existing_node_id=None,
        )

    return {
        "definition_id": str(def_id),
        "node_id": node_id,
        "item_code": item_code,
        "opcao_escolhida": opcao_escolhida,
        "fonte_descricao": fonte_descricao,
        "data_informacao": effective_date.isoformat(),
    }
