"""CLI de teste do wrapper LiteLLM."""

import argparse
import asyncio
from typing import get_args

from oraculo_ai.llm.client import complete, embed, shutdown_traces
from oraculo_ai.llm.schema import Message, ModelTier


async def _run_completion(prompt: str, model: ModelTier) -> None:
    response = await complete([Message(role="user", content=prompt)], model=model)
    print(f"Model:             {response.model}")
    print(f"Latency:           {response.latency_ms} ms")
    print(f"Prompt tokens:     {response.prompt_tokens}")
    print(f"Completion tokens: {response.completion_tokens}")
    print()
    print("Response:")
    print(response.content)


async def _run_embedding(text: str) -> None:
    vectors = await embed([text])
    vector = vectors[0]
    print(f"Dim:      {len(vector)}")
    print(f"First 5:  {vector[:5]}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python -m oraculo_ai.llm.cli",
        description="Teste isolado do wrapper LiteLLM (chat ou embedding).",
        epilog=(
            "Exemplos:\n"
            '  python -m oraculo_ai.llm.cli "qual a capital do Brasil?"\n'
            '  python -m oraculo_ai.llm.cli "explica em 1 frase" --model smart\n'
            '  python -m oraculo_ai.llm.cli "texto pra embedar" --embed'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("prompt", help="Texto da pergunta ou conteúdo a embedar.")
    parser.add_argument(
        "--model",
        choices=list(get_args(ModelTier)),
        default="fast",
        help="Tier do modelo de chat (default: fast). Ignorado se --embed.",
    )
    parser.add_argument(
        "--embed",
        action="store_true",
        help="Roda embedding em vez de completion.",
    )
    args = parser.parse_args()

    try:
        if args.embed:
            asyncio.run(_run_embedding(args.prompt))
        else:
            asyncio.run(_run_completion(args.prompt, args.model))
    finally:
        shutdown_traces()


if __name__ == "__main__":
    main()
