"""Exporta schema canônico Thórus pra JSON.

Como rodar:
    cd apps/ai
    uv run python scripts/export_schema.py

Saída: apps/ai/src/oraculo_ai/document_ai/schema_thorus.json
"""

import asyncio
import json
import sys
from pathlib import Path

from psycopg.rows import dict_row

from oraculo_ai.core.config import get_settings
from oraculo_ai.core.db import close_db, get_pool, init_db


if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


_OUTPUT_PATH = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "oraculo_ai"
    / "document_ai"
    / "schema_thorus.json"
)

_REFERENCE_PROJECT_NUMBER = 26002


async def _export() -> None:
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                SELECT DISTINCT ON (item_code)
                    item_code, disciplina, tipo, fase, pergunta, informacao_auxiliar
                FROM definitions
                WHERE project_id = (SELECT id FROM projects WHERE project_number = %s)
                  AND fonte_informacao = 'lista_definicoes_inicial'
                ORDER BY item_code, created_at ASC
                """,
                (_REFERENCE_PROJECT_NUMBER,),
            )
            rows = await cur.fetchall()

    items = [
        {
            "item_code": str(r["item_code"]),
            "disciplina": r.get("disciplina"),
            "tipo": r.get("tipo"),
            "fase": r.get("fase"),
            "pergunta": r.get("pergunta"),
            "informacao_auxiliar": r.get("informacao_auxiliar"),
        }
        for r in rows
    ]

    _OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    _OUTPUT_PATH.write_text(
        json.dumps(items, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Exportados {len(items)} itens canônicos para {_OUTPUT_PATH}")


async def _amain() -> None:
    settings = get_settings()
    await init_db(settings.database_url, pool_size=2)
    try:
        await _export()
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(_amain())
