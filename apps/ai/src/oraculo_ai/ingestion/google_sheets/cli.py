"""CLI de ingestão Google Sheets."""

import argparse
import asyncio

from oraculo_ai.ingestion.google_sheets.pipeline import run_ingestion
from oraculo_ai.llm.client import shutdown_traces


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
        asyncio.run(_run(project_number=args.project_number, sheet_name=args.sheet_name))
    finally:
        shutdown_traces()


if __name__ == "__main__":
    main()
