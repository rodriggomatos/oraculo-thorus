"""query_database — tool genérica de SELECT pro Thor com sandbox rigoroso.

A tool roda contra a role read-only `thor_query_ro` (criada na migration
20260505160000). Garantias:

  - Conexão via DATABASE_URL_QUERY_RO; role tem só SELECT em public e
    nenhum acesso a auth/storage/checkpoint_*.
  - statement_timeout=10s por query (SET LOCAL na transação).
  - LIMIT automático: injeta LIMIT 100 se ausente; capa LIMIT em 1000.
  - Erro mapeado pra mensagem PT-BR acionável.
  - Audit via Langfuse @observe.

Permissão: gateada no agent.py via `check_permission(user,
'query_database')` — admin sempre, demais precisam permissão explícita
em user_profiles.permissions.
"""

import json
import re
import time
from typing import Any

from langchain_core.tools import tool
from langfuse import get_client, observe
from psycopg import AsyncConnection
from psycopg.errors import QueryCanceled
from psycopg.rows import dict_row

from oraculo_ai.core.config import get_settings

_DEFAULT_LIMIT = 100
_MAX_LIMIT = 1000
_TIMEOUT_MS = 10_000
_MAX_OUTPUT_CHARS = 8_000  # Trunca payload pra LLM não estourar contexto

# Regex pra detectar LIMIT trailing (nível top — não bate com LIMIT em
# subquery interna). Aceita ponto-e-vírgula opcional + whitespace.
_TRAILING_LIMIT_RE = re.compile(
    r"(?i)\bLIMIT\s+(\d+)(?:\s+OFFSET\s+\d+)?\s*;?\s*$"
)


def apply_limit(
    sql: str,
    *,
    default_limit: int = _DEFAULT_LIMIT,
    max_limit: int = _MAX_LIMIT,
) -> tuple[str, str | None]:
    """Garante LIMIT no SQL pra não retornar resultsets gigantes pro LLM.

    Returns (sql_modificada, tag_aplicada) — tag é None se já tinha LIMIT
    razoável; "default_<n>" se injetado; "capped_to_<n>" se reduzido.
    """
    cleaned = sql.rstrip().rstrip(";").rstrip()
    match = _TRAILING_LIMIT_RE.search(cleaned)
    if match is None:
        return f"{cleaned} LIMIT {default_limit}", f"default_{default_limit}"
    requested = int(match.group(1))
    if requested > max_limit:
        new_sql = cleaned[: match.start()] + f"LIMIT {max_limit}"
        return new_sql, f"capped_to_{max_limit}"
    return cleaned, None


def _truncate_for_llm(payload: dict[str, Any]) -> dict[str, Any]:
    """Trunca rows se o JSON ficar grande demais pro LLM mastigar."""
    serialized = json.dumps(payload, ensure_ascii=False, default=str)
    if len(serialized) <= _MAX_OUTPUT_CHARS:
        return payload
    rows = list(payload.get("rows", []))
    while rows:
        candidate = {**payload, "rows": rows}
        size = len(json.dumps(candidate, ensure_ascii=False, default=str))
        if size <= _MAX_OUTPUT_CHARS:
            break
        rows.pop()
    return {
        **payload,
        "rows": rows,
        "truncated": True,
        "truncated_reason": (
            f"Resposta excedeu {_MAX_OUTPUT_CHARS} chars; mostrando "
            f"{len(rows)} linhas. Refine a query (LIMIT menor, agregação)."
        ),
    }


@observe(as_type="tool", name="query_database")
@tool
async def query_database(sql: str) -> str:
    """Executa SQL SELECT read-only no banco da Thórus e retorna JSON.

    Use pra perguntas exploratórias que NÃO são cobertas por tools
    específicas: agregações (COUNT, GROUP BY), comparações entre projetos,
    detecção de gaps (ex: projetos sem escopo), análises ad-hoc.

    NÃO use quando uma tool específica resolve (search_definitions,
    list_projects, get_project_scope, etc). Tool específica é mais barata
    e tem schema validado.

    Restrições da role read-only:
      - Apenas SELECT em tabelas de domínio (projects, definitions,
        project_scope, scope_template, ldp_discipline, source_documents,
        user_profiles, city, etc.).
      - Sem acesso a checkpoint_*, auth.*, storage.*, supabase_migrations.*.
      - Timeout de 10s por query.
      - LIMIT 100 injetado se ausente; LIMIT > 1000 é reduzido pra 1000.

    Args:
        sql: SQL SELECT válido. Tente sempre filtrar bem e usar LIMIT.

    Returns:
        JSON string com {columns, rows, row_count, applied_limit?,
        elapsed_ms} em sucesso; {error} em falha.
    """
    settings = get_settings()
    if not settings.database_url_query_ro:
        return json.dumps(
            {
                "error": (
                    "DATABASE_URL_QUERY_RO não configurado no servidor. "
                    "A tool query_database está indisponível até o admin "
                    "configurar a role read-only."
                )
            },
            ensure_ascii=False,
        )

    prepared, applied = apply_limit(sql)
    started = time.monotonic()
    langfuse = get_client()

    try:
        async with await AsyncConnection.connect(
            settings.database_url_query_ro
        ) as conn:
            async with conn.transaction():
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(
                        f"SET LOCAL statement_timeout = {_TIMEOUT_MS}"
                    )
                    await cur.execute(prepared)
                    if cur.description is None:
                        # Statement sem rowset (SET, comments, etc) — não
                        # deveria ocorrer em SELECT, mas defensivo.
                        columns: list[str] = []
                        rows: list[dict[str, Any]] = []
                    else:
                        columns = [d.name for d in cur.description]
                        rows = await cur.fetchall()
    except QueryCanceled:
        elapsed_ms = int((time.monotonic() - started) * 1000)
        langfuse.update_current_span(
            input={"sql": sql, "prepared": prepared},
            output={"error": "timeout"},
            metadata={"elapsed_ms": elapsed_ms, "applied_limit": applied or "none"},
        )
        return json.dumps(
            {
                "error": (
                    "Query demorou demais (>10s). Tente filtrar mais "
                    "(WHERE), reduzir o LIMIT, ou agregar com GROUP BY."
                )
            },
            ensure_ascii=False,
        )
    except Exception as exc:  # noqa: BLE001
        elapsed_ms = int((time.monotonic() - started) * 1000)
        message = f"{type(exc).__name__}: {exc}"
        langfuse.update_current_span(
            input={"sql": sql, "prepared": prepared},
            output={"error": message},
            metadata={"elapsed_ms": elapsed_ms, "applied_limit": applied or "none"},
        )
        return json.dumps(
            {
                "error": (
                    f"Query falhou: {message}. Verifique sintaxe SQL, nomes "
                    "de tabelas/colunas, e se a tabela é acessível pela "
                    "role read-only (auth/storage/checkpoint_* são bloqueados)."
                )
            },
            ensure_ascii=False,
        )

    elapsed_ms = int((time.monotonic() - started) * 1000)
    payload: dict[str, Any] = {
        "columns": columns,
        "rows": [list(r.values()) for r in rows],
        "row_count": len(rows),
        "elapsed_ms": elapsed_ms,
    }
    if applied is not None:
        payload["applied_limit"] = applied

    payload = _truncate_for_llm(payload)

    langfuse.update_current_span(
        input={"sql": sql, "prepared": prepared},
        output={
            "row_count": str(payload["row_count"]),
            "elapsed_ms": str(elapsed_ms),
            "applied_limit": applied or "none",
            "truncated": str(payload.get("truncated", False)),
        },
    )

    return json.dumps(payload, ensure_ascii=False, default=str)
