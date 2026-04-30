"""Batch ingester de projetos LDP via YAML config."""

import argparse
import asyncio
import sys
from pathlib import Path

import yaml
from pydantic import BaseModel, ValidationError

from oraculo_ai.core.config import get_settings
from oraculo_ai.core.db import close_db, init_db
from oraculo_ai.ingestion.google_sheets.pipeline import run_ingestion
from oraculo_ai.ingestion.google_sheets.projects_repo import ProjectsWriter
from oraculo_ai.ingestion.schema import IngestionStats
from oraculo_ai.llm.client import shutdown_traces


if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


class ProjectConfig(BaseModel):
    project_number: int
    name: str
    client: str
    google_sheet_id: str


class BatchConfig(BaseModel):
    projects: list[ProjectConfig]


def _load_config(config_path: Path) -> BatchConfig:
    if not config_path.is_file():
        raise FileNotFoundError(f"config not found at {config_path}")
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if raw is None:
        raise ValueError("YAML config is empty")
    return BatchConfig.model_validate(raw)


async def _run_one(project: ProjectConfig, writer: ProjectsWriter) -> IngestionStats:
    print(f"=== Projeto {project.project_number} ({project.name}) ===")
    await writer.upsert_project(
        project_number=project.project_number,
        name=project.name,
        client=project.client,
        google_sheet_id=project.google_sheet_id,
    )
    print("✅ Inserido em projects (ou atualizado)")
    print("📥 Ingerindo planilha...")
    stats = await run_ingestion(project_number=project.project_number)
    print(
        f"✅ Created: {stats.chunks_created}  "
        f"Updated: {stats.chunks_updated}  "
        f"Unchanged: {stats.chunks_unchanged}  "
        f"Embeddings: {stats.embedding_calls}"
    )
    print()
    return stats


async def _run_batch(config: BatchConfig) -> None:
    successful = 0
    total_chunks_created = 0
    total_chunks_updated = 0
    total_embedding_calls = 0

    async with ProjectsWriter() as writer:
        for project in config.projects:
            stats = await _run_one(project, writer)
            successful += 1
            total_chunks_created += stats.chunks_created
            total_chunks_updated += stats.chunks_updated
            total_embedding_calls += stats.embedding_calls

    print("=== Resumo ===")
    print(f"Projetos ingeridos: {successful}/{len(config.projects)}")
    print(f"Chunks totais criados: {total_chunks_created + total_chunks_updated}")
    print(f"Embeddings totais: {total_embedding_calls}")


async def _amain(config: BatchConfig) -> None:
    settings = get_settings()
    await init_db(settings.database_url, pool_size=3)
    try:
        await _run_batch(config)
    finally:
        await close_db()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python -m oraculo_ai.ingestion.google_sheets.batch",
        description="Batch ingester de projetos LDP via YAML config.",
        epilog=(
            "Exemplo:\n"
            "  python -m oraculo_ai.ingestion.google_sheets.batch --config ../../projects.yaml\n"
            "  python -m oraculo_ai.ingestion.google_sheets.batch --config ../../projects.yaml --dry-run"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Caminho do YAML de configuração (path absoluto ou relativo ao cwd).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Só valida o YAML — não insere em projects nem ingere planilhas.",
    )
    args = parser.parse_args()

    try:
        config = _load_config(args.config.resolve())
    except (FileNotFoundError, ValueError, ValidationError) as exc:
        print(f"❌ ERRO no YAML: {exc}", file=sys.stderr)
        sys.exit(2)

    print(f"YAML válido. {len(config.projects)} projetos encontrados.")
    print()

    if args.dry_run:
        print("Modo --dry-run: encerrando antes de qualquer write no banco.")
        return

    exit_code = 0
    try:
        asyncio.run(_amain(config))
    except Exception as exc:
        print(f"❌ ERRO durante batch: {type(exc).__name__}: {exc}", file=sys.stderr)
        exit_code = 1
    finally:
        shutdown_traces()

    if exit_code != 0:
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
