"""Popula a tabela `city` com municípios IBGE. Roda 1x manualmente.

Fonte: https://servicodados.ibge.gov.br/api/v1/localidades/municipios

Uso:
    cd apps/ai
    uv run python scripts/seed_cities.py

Idempotente — usa ON CONFLICT (ibge_code) DO NOTHING. Roda de novo é seguro
e só insere o que faltar.
"""

import asyncio
import sys
from typing import Any

import httpx

from oraculo_ai.core.config import get_settings
from oraculo_ai.core.db import close_db, get_pool, init_db


if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


_IBGE_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
_BATCH_SIZE = 500


def _safe_chain(data: Any, keys: list[str]) -> Any:
    """Navega keys aninhadas com tolerância a None/ausente em qualquer nível."""
    cursor: Any = data
    for key in keys:
        if not isinstance(cursor, dict):
            return None
        cursor = cursor.get(key)
        if cursor is None:
            return None
    return cursor


def _extract_sigla(m: dict[str, Any]) -> str | None:
    """Tenta caminhos conhecidos da resposta IBGE pra encontrar a UF.

    Caminho primário (estrutura clássica):
        microrregiao.mesorregiao.UF.sigla
    Fallback (estrutura nova com regiao-imediata):
        regiao-imediata.regiao-intermediaria.UF.sigla
    """
    sigla = _safe_chain(m, ["microrregiao", "mesorregiao", "UF", "sigla"])
    if isinstance(sigla, str) and sigla:
        return sigla
    sigla = _safe_chain(
        m, ["regiao-imediata", "regiao-intermediaria", "UF", "sigla"]
    )
    if isinstance(sigla, str) and sigla:
        return sigla
    return None


async def fetch_ibge_municipios() -> tuple[list[tuple[str, str, str]], list[str]]:
    """Retorna ([(ibge_code, nome, estado)], [warnings])."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(_IBGE_URL)
        response.raise_for_status()
        items: list[dict[str, Any]] = response.json()

    rows: list[tuple[str, str, str]] = []
    warnings: list[str] = []
    for m in items:
        sigla = _extract_sigla(m)
        if not sigla:
            ibge_id = m.get("id")
            nome = m.get("nome")
            warnings.append(
                f"sem UF identificável: id={ibge_id!r} nome={nome!r}"
            )
            continue
        rows.append((str(m["id"]), str(m["nome"]), sigla))
    return rows, warnings


async def insert_cities(rows: list[tuple[str, str, str]]) -> int:
    pool = get_pool()
    inserted_total = 0
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            for start in range(0, len(rows), _BATCH_SIZE):
                batch = rows[start : start + _BATCH_SIZE]
                await cur.executemany(
                    """
                    INSERT INTO city (ibge_code, nome, estado)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (ibge_code) DO NOTHING
                    """,
                    batch,
                )
                inserted_total += cur.rowcount or 0
                print(
                    f"  batch {start // _BATCH_SIZE + 1}: "
                    f"{len(batch)} sent, {cur.rowcount or 0} inserted (rest skipped on conflict)"
                )
    return inserted_total


async def _run() -> int:
    settings = get_settings()
    await init_db(settings.database_url, pool_size=2)
    try:
        print(f"Fetching IBGE municipios from {_IBGE_URL}…")
        rows, warnings = await fetch_ibge_municipios()
        print(f"Fetched {len(rows)} municípios with valid UF.")
        if warnings:
            print(f"Pulados {len(warnings)} municípios sem UF identificável:")
            for w in warnings[:10]:
                print(f"  AVISO: {w}")
            if len(warnings) > 10:
                print(f"  ... e mais {len(warnings) - 10}")

        if not rows:
            print("ERRO: IBGE retornou lista vazia.")
            return 1

        print(f"Inserting in batches of {_BATCH_SIZE}…")
        inserted = await insert_cities(rows)
        print(f"\nSeed completo: {inserted} novos / {len(rows)} totais (resto já existia).")
        return 0
    finally:
        await close_db()


def main() -> int:
    return asyncio.run(_run())


if __name__ == "__main__":
    sys.exit(main())
