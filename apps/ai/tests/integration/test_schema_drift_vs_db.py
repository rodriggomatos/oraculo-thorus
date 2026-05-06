"""Valida que o schema do banco real reflete o que as migrations descrevem.

Pra rodar contra um DB qualquer, defina:

    set RUN_DB_DRIFT_TEST=1   (Windows)
    export RUN_DB_DRIFT_TEST=1 (POSIX)

E garanta que `DATABASE_URL` aponta pra um Supabase com TODAS as
migrations aplicadas — incluindo as 4 corretivas de 20260505 (estado_check
27 UFs, RLS nas 5 tabelas de scope, recreate auth_read_city, drop
chunks_legacy_backup).

Skip por padrão pra não quebrar CI sem DB. Se você fizer DDL direto no
SQL Editor sem migration correspondente, este test dá `FAIL` na próxima
execução — é o canário do drift.
"""

import os
import sys

import pytest


_RUN_FLAG = "RUN_DB_DRIFT_TEST"
_SKIP_REASON = (
    f"set {_RUN_FLAG}=1 + DATABASE_URL pra rodar (test integrado contra Postgres)"
)


pytestmark = pytest.mark.skipif(
    os.environ.get(_RUN_FLAG) != "1",
    reason=_SKIP_REASON,
)


@pytest.fixture(scope="module")
def conn():
    if sys.platform == "win32":
        import asyncio

        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    import psycopg

    from oraculo_ai.core.config import get_settings

    settings = get_settings()
    if not settings.database_url:
        pytest.skip("DATABASE_URL não configurado")
    with psycopg.connect(settings.database_url) as c:
        yield c


# --- Tabelas esperadas (apenas as geridas por migration) ---

_EXPECTED_TABLES = {
    "city",
    "definitions",
    "ldp_discipline",
    "project_scope",
    "projects",
    "scope_template",
    "scope_to_ldp_discipline",
    "source_documents",
    "user_profiles",
}

# `chunks_legacy_backup` não está na lista — foi dropada pela migration
# 20260505150000. As tabelas runtime (data_chunks, checkpoint_*) também
# ficam fora — não são geridas por migration.

_TABLES_RUNTIME = {
    "data_chunks",
    "checkpoint_blobs",
    "checkpoint_migrations",
    "checkpoint_writes",
    "checkpoints",
}


def test_managed_tables_present(conn):
    cur = conn.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema='public' AND table_type='BASE TABLE'"
    )
    real = {r[0] for r in cur.fetchall()}
    missing = _EXPECTED_TABLES - real
    assert not missing, f"tabelas geridas por migration faltando: {missing}"


def test_chunks_legacy_backup_dropped(conn):
    cur = conn.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name='chunks_legacy_backup'"
    )
    assert cur.fetchone() is None, (
        "chunks_legacy_backup ainda existe — migration "
        "20260505150000_drop_chunks_legacy_backup não foi aplicada"
    )


@pytest.mark.parametrize(
    "table",
    [
        "projects",
        "definitions",
        "user_profiles",
        "city",
        "project_scope",
        "scope_template",
        "ldp_discipline",
        "scope_to_ldp_discipline",
        "source_documents",
    ],
)
def test_rls_enabled(conn, table: str):
    cur = conn.execute(
        "SELECT relrowsecurity FROM pg_class c "
        "JOIN pg_namespace n ON n.oid=c.relnamespace "
        "WHERE n.nspname='public' AND c.relname=%s",
        (table,),
    )
    row = cur.fetchone()
    assert row is not None, f"{table} não encontrada"
    assert row[0] is True, f"RLS desabilitado em {table}"


@pytest.mark.parametrize(
    "table,policy",
    [
        ("projects", "auth_read_projects"),
        ("definitions", "auth_read_definitions"),
        ("user_profiles", "auth_read_profiles"),
        ("user_profiles", "auth_update_own_profile"),
        ("city", "auth_read_city"),
        ("project_scope", "auth_read_project_scope"),
        ("scope_template", "auth_read_scope_template"),
        ("ldp_discipline", "auth_read_ldp_discipline"),
        ("scope_to_ldp_discipline", "auth_read_scope_to_ldp_discipline"),
        ("source_documents", "auth_read_source_documents"),
    ],
)
def test_policy_present(conn, table: str, policy: str):
    cur = conn.execute(
        "SELECT 1 FROM pg_policies "
        "WHERE schemaname='public' AND tablename=%s AND policyname=%s",
        (table, policy),
    )
    assert cur.fetchone() is not None, (
        f"policy {policy!r} ausente em {table} — drift entre migration e banco"
    )


_BR_UFS = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
    "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
    "RS", "RO", "RR", "SC", "SP", "SE", "TO",
}


@pytest.mark.parametrize("table", ["projects", "city"])
def test_estado_check_lists_27_uf(conn, table: str):
    cur = conn.execute(
        """
        SELECT pg_get_constraintdef(c.oid)
        FROM pg_constraint c
        JOIN pg_class cl ON cl.oid = c.conrelid
        JOIN pg_namespace n ON n.oid = cl.relnamespace
        WHERE n.nspname='public' AND cl.relname=%s
          AND c.conname = %s
        """,
        (table, f"{table}_estado_check"),
    )
    row = cur.fetchone()
    assert row is not None, f"{table}_estado_check ausente"
    definition = row[0]
    for uf in _BR_UFS:
        assert f"'{uf}'" in definition, (
            f"{table}_estado_check não lista {uf!r} — drift na constraint"
        )
