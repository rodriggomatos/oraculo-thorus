"""CLI do agente Q&A."""

import argparse
import asyncio
import sys
from uuid import uuid4

from oraculo_ai.agents.qa.agent import answer_question
from oraculo_ai.agents.qa.schema import QAQuery
from oraculo_ai.llm.client import shutdown_traces


if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


async def _run(
    question: str,
    project_number: int | None,
    top_k: int,
    thread_id: str,
) -> None:
    answer = await answer_question(
        QAQuery(
            question=question,
            project_number=project_number,
            top_k=top_k,
            thread_id=thread_id,
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
            "Exemplos:\n"
            '  python -m oraculo_ai.agents.qa.cli "qual o material do gás @26002"\n'
            '  python -m oraculo_ai.agents.qa.cli "qual o material do gás no Stylo"\n'
            '  python -m oraculo_ai.agents.qa.cli "qual o material do gás?" --project-number 26002\n'
            '  python -m oraculo_ai.agents.qa.cli "qual o material do gás?"'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("question", help="Pergunta em português.")
    parser.add_argument(
        "--project-number",
        type=int,
        default=None,
        help="Número do projeto (opcional). Se omitido, o agente tenta resolver pelo texto da pergunta ou pede ao usuário.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Número de chunks que a tool de busca retorna (default: 5).",
    )
    parser.add_argument(
        "--thread-id",
        default=None,
        help="ID da sessão pra reaproveitar contexto (default: gera novo uuid; cada CLI = sessão isolada).",
    )
    args = parser.parse_args()

    thread_id = args.thread_id or str(uuid4())

    try:
        asyncio.run(_run(args.question, args.project_number, args.top_k, thread_id))
    finally:
        shutdown_traces()


if __name__ == "__main__":
    main()
