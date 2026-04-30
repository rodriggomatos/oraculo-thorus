"""CLI de ingestão Google Sheets."""

import argparse
import asyncio
import sys

from oraculo_ai.core.config import get_settings
from oraculo_ai.core.db import close_db, init_db
from oraculo_ai.ingestion.google_sheets.pipeline import run_ingestion
from oraculo_ai.llm.client import shutdown_traces


if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


async def _run(project_number: int, sheet_name: str) -> None:
    stats = await run_ingestion(project_number=project_number, sheet_name=sheet_name)
    print("=== Ingestion stats ===")
    print(f"Total rows:             {stats.total_rows}")
    print(f"Definitions created:    {stats.definitions_created}")
    print(f"Definitions updated:    {stats.definitions_updated}")
    print(f"Chunks created:         {stats.chunks_created}")
    print(f"Chunks updated:         {stats.chunks_updated}")
    print(f"Chunks unchanged:       {stats.chunks_unchanged}")
    print(f"Embedding calls:        {stats.embedding_calls}")


async def _amain(project_number: int, sheet_name: str) -> None:
    settings = get_settings()
    await init_db(settings.database_url, pool_size=3)
    try:
        await _run(project_number, sheet_name)
    finally:
        await close_db()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python -m oraculo_ai.ingestion.google_sheets.cli",
        description="Ingere a planilha de definições de um projeto no Supabase.",
        epilog=(
            "Exemplo:\n"
            "  python -m oraculo_ai.ingestion.google_sheets.cli --project-number 26002"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--project-number",
        type=int,
        required=True,
        help="Número do projeto (ex.: 26002). Deve existir na tabela projects com google_sheet_id setado.",
    )
    parser.add_argument(
        "--sheet-name",
        default="Lista de definições",
        help="Nome da aba (default: 'Lista de definições').",
    )
    args = parser.parse_args()

    try:
        asyncio.run(_amain(project_number=args.project_number, sheet_name=args.sheet_name))
    finally:
        shutdown_traces()


if __name__ == "__main__":
    main()
