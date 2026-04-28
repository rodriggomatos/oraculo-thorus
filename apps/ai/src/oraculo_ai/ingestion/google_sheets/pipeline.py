"""Pipeline de ingestão Google Sheets — orquestra connect → read → parse → upsert."""

import asyncio
from uuid import UUID

from oraculo_ai.core.config import get_settings
from oraculo_ai.ingestion.google_sheets.connector import build_sheets_service, read_sheet
from oraculo_ai.ingestion.google_sheets.content import build_chunk_text, compute_hash
from oraculo_ai.ingestion.google_sheets.parser import parse_row
from oraculo_ai.ingestion.google_sheets.repository import SheetsRepository
from oraculo_ai.ingestion.schema import ChunkData, IngestionStats
from oraculo_ai.llm.client import embed


async def run_ingestion(
    project_number: int,
    sheet_name: str = "Lista de definições",
) -> IngestionStats:
    settings = get_settings()

    if not settings.google_service_account_json:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON not configured")

    stats = IngestionStats()

    async with SheetsRepository(settings.database_url) as repo:
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

            def_id, was_inserted = await repo.upsert_definition(definition)
            if was_inserted:
                stats.definitions_created += 1
            else:
                stats.definitions_updated += 1

            content = build_chunk_text(definition)
            content_hash = compute_hash(content)

            existing = await repo.fetch_chunk_for_source("definitions", def_id)
            if existing is not None and existing.get("content_hash") == content_hash:
                stats.chunks_unchanged += 1
                continue

            vectors = await embed([content])
            stats.embedding_calls += 1
            embedding = vectors[0] if vectors else None

            metadata: dict[str, str] = {
                "disciplina": definition.disciplina or "",
                "tipo": definition.tipo or "",
                "fase": definition.fase or "",
                "item_code": definition.item_code,
                "source_row": str(definition.source_row) if definition.source_row else "",
                "project_number": str(project["project_number"]),
            }

            chunk = ChunkData(
                project_id=project_id,
                source_table="definitions",
                source_row_id=def_id,
                content=content,
                content_hash=content_hash,
                embedding=embedding,
                metadata=metadata,
            )

            existing_id = existing["id"] if existing is not None else None
            _, action = await repo.upsert_chunk(chunk, existing_id=existing_id)
            if action == "created":
                stats.chunks_created += 1
            elif action == "updated":
                stats.chunks_updated += 1

    return stats
