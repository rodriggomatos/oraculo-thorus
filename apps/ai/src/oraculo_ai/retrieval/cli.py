"""CLI de busca semântica."""

import argparse
import asyncio
import sys

from oraculo_ai.llm.client import shutdown_traces
from oraculo_ai.retrieval.schema import SearchQuery
from oraculo_ai.retrieval.search import search


if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


async def _run(query_text: str, project_number: int, top_k: int) -> None:
    results = await search(
        SearchQuery(
            query=query_text,
            project_number=project_number,
            top_k=top_k,
        )
    )

    print(f'Top {len(results)} resultados pra "{query_text}":')
    print()
    for idx, result in enumerate(results, start=1):
        item_code = result.metadata.get("item_code", "?")
        snippet = result.content[:200].replace("\n", " ")
        print(f"[{idx}] score={result.score:.4f}  {item_code}")
        print(f"    {snippet}")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python -m oraculo_ai.retrieval.cli",
        description="Busca semântica de chunks por projeto.",
        epilog=(
            "Exemplo:\n"
            '  python -m oraculo_ai.retrieval.cli "qual o material do hall?" --project-number 26002\n'
            '  python -m oraculo_ai.retrieval.cli "tubulação de gás" --project-number 26002 --top-k 3'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("query", help="Pergunta ou termo a buscar.")
    parser.add_argument(
        "--project-number",
        type=int,
        required=True,
        help="Número do projeto (ex.: 26002).",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Número de resultados a retornar (default: 5).",
    )
    args = parser.parse_args()

    try:
        asyncio.run(_run(args.query, args.project_number, args.top_k))
    finally:
        shutdown_traces()


if __name__ == "__main__":
    main()
