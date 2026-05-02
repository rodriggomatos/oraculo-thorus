"""Pipeline de ingestão de documentos do cliente → LDP estruturada."""

import hashlib
import json
from pathlib import Path
from typing import Any
from uuid import UUID

from oraculo_ai.core.config import get_settings
from oraculo_ai.document_ai.extractor import extract_ldp_from_documents
from oraculo_ai.document_ai.parsers import SUPPORTED_EXTENSIONS, parse_file
from oraculo_ai.document_ai.repository import SourceDocumentsRepository
from oraculo_ai.document_ai.schemas import IngestionStats
from oraculo_ai.ingestion.google_sheets.pipeline import register_definition_version
from oraculo_ai.ingestion.google_sheets.repository import SheetsRepository
from oraculo_ai.ingestion.schema import SYSTEM_USER_ID


_SCHEMA_PATH = Path(__file__).resolve().parent / "schema_thorus.json"


def _load_schema_thorus() -> list[dict[str, Any]]:
    if not _SCHEMA_PATH.is_file():
        raise FileNotFoundError(
            f"schema_thorus.json não encontrado em {_SCHEMA_PATH}. "
            f"Rode: cd apps/ai && uv run python scripts/export_schema.py"
        )
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


def _list_incoming_files(incoming_dir: Path, project_number: int) -> list[Path]:
    project_dir = incoming_dir / str(project_number)
    if not project_dir.is_dir():
        raise FileNotFoundError(
            f"Pasta de documentos não encontrada: {project_dir}. "
            f"Crie a pasta e coloque arquivos do cliente lá."
        )
    files: list[Path] = []
    for entry in sorted(project_dir.iterdir()):
        if entry.is_file() and entry.suffix.lower() in SUPPORTED_EXTENSIONS:
            files.append(entry)
    return files


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


async def ingest_documents_into_ldp(project_number: int) -> IngestionStats:
    settings = get_settings()
    incoming_dir = Path(settings.document_ai_incoming_dir)
    files = _list_incoming_files(incoming_dir, project_number)

    schema_thorus = _load_schema_thorus()
    stats = IngestionStats(
        project_number=project_number,
        total_thorus_items=len(schema_thorus),
    )

    if not files:
        return stats

    parsed_documents: list[tuple[str, str, bytes | None, UUID]] = []
    primary_source_document_id: UUID | None = None

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

        for file_path in files:
            data = file_path.read_bytes()
            content_hash = _hash_bytes(data)

            existing = await docs_repo.find_by_hash(project_id, content_hash)
            if existing is not None:
                stats.files_skipped_already_processed += 1
                continue

            content_text, file_format = await parse_file(file_path)
            source_document_id = await docs_repo.create(
                project_id=project_id,
                filename=file_path.name,
                file_format=file_format,
                content_hash=content_hash,
                content_markdown=content_text,
                metadata={"size_bytes": len(data)},
            )
            stats.files_processed += 1
            stats.source_document_ids.append(str(source_document_id))

            pdf_bytes = data if file_format == "pdf" else None
            parsed_documents.append(
                (file_path.name, content_text, pdf_bytes, source_document_id)
            )

            if primary_source_document_id is None:
                primary_source_document_id = source_document_id

    if not parsed_documents:
        return stats

    extractor_input = [
        (filename, content_text, pdf_bytes)
        for filename, content_text, pdf_bytes, _ in parsed_documents
    ]
    primary_filename = parsed_documents[0][0]

    extracted = await extract_ldp_from_documents(
        project_number=project_number,
        documents=extractor_input,
        schema_thorus=schema_thorus,
    )

    schema_lookup = {item["item_code"]: item for item in schema_thorus}

    for item in extracted.items:
        if item.opcao_escolhida is None:
            stats.items_blank += 1
            continue

        canonical = schema_lookup.get(item.item_code)
        if canonical is None:
            stats.items_blank += 1
            continue

        stats.items_filled += 1
        if item.confidence == "alta":
            stats.items_high_confidence += 1
        elif item.confidence == "media":
            stats.items_medium_confidence += 1
        else:
            stats.items_low_confidence += 1

        fonte_descricao = primary_filename
        if item.fonte_no_documento:
            fonte_descricao = f"{primary_filename} - {item.fonte_no_documento}"

        await register_definition_version(
            project_number=project_number,
            item_code=item.item_code,
            pergunta=str(canonical.get("pergunta") or item.pergunta_thorus),
            opcao_escolhida=item.opcao_escolhida,
            disciplina=canonical.get("disciplina"),
            tipo=canonical.get("tipo"),
            fase=canonical.get("fase"),
            status=item.status,
            fonte_informacao="documento",
            fonte_descricao=fonte_descricao,
            source_document_id=primary_source_document_id,
            created_by_user_id=SYSTEM_USER_ID,
        )

    return stats
