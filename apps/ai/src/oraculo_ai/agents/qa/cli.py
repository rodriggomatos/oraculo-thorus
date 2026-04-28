"""CLI do agente Q&A."""

import argparse
import asyncio
import sys

from oraculo_ai.agents.qa.agent import answer_question
from oraculo_ai.agents.qa.schema import QAQuery
from oraculo_ai.llm.client import shutdown_traces


if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


async def _run(question: str, project_number: int, top_k: int) -> None:
    answer = await answer_question(
        QAQuery(
            question=question,
            project_number=project_number,
            top_k=top_k,
        )
    )

    print(f"Pergunta: {question}")
    print()
    print("Resposta:")
    print(answer.answer)
    print()
    print(f"Fontes ({len(answer.sources)}):")
    for idx, src in enumerate(answer.sources, start=1):
        tipo_part = f" - {src.tipo}" if src.tipo else ""
        print(f"[{idx}] Item {src.item_code} - {src.disciplina}{tipo_part} - score {src.score:.2f}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python -m oraculo_ai.agents.qa.cli",
        description="Pergunta ao agente Q&A do Oráculo Thórus.",
        epilog=(
            "Exemplo:\n"
            '  python -m oraculo_ai.agents.qa.cli "qual o material da tubulação de gás?" --project-number 26002\n'
            '  python -m oraculo_ai.agents.qa.cli "tem definição sobre piso da sala?" --project-number 26002 --top-k 8'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("question", help="Pergunta em português.")
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
        help="Número de chunks que a tool de busca retorna (default: 5).",
    )
    args = parser.parse_args()

    try:
        asyncio.run(_run(args.question, args.project_number, args.top_k))
    finally:
        shutdown_traces()


if __name__ == "__main__":
    main()
