"""Valida o sandbox da role thor_query_ro contra um DB real.

Pra rodar:

    set RUN_DB_DRIFT_TEST=1   (Windows)
    export RUN_DB_DRIFT_TEST=1 (POSIX)

E garanta que `DATABASE_URL_QUERY_RO` aponta pra um Postgres com a
migration 20260505160000 aplicada e a senha + LOGIN configurados na
role.

Skip por padrão; opt-in via env var (mesmo padrão do
test_schema_drift_vs_db.py).
"""

import os
import sys

import pytest

_RUN_FLAG = "RUN_DB_DRIFT_TEST"
_SKIP_REASON = (
    f"set {_RUN_FLAG}=1 + DATABASE_URL_QUERY_RO pra rodar (test integrado)"
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
    if not settings.database_url_query_ro:
        pytest.skip("DATABASE_URL_QUERY_RO não configurado")
    with psycopg.connect(settings.database_url_query_ro) as c:
        yield c


def test_can_select_from_projects(conn):
    cur = conn.execute("SELECT count(*) FROM projects")
    assert cur.fetchone()[0] is not None


def test_can_select_from_definitions(conn):
    cur = conn.execute("SELECT count(*) FROM definitions")
    assert cur.fetchone()[0] is not None


@pytest.mark.parametrize(
    "table",
    [
        "checkpoints",
        "checkpoint_blobs",
        "checkpoint_writes",
        "checkpoint_migrations",
    ],
)
def test_cannot_select_from_checkpoint_tables(conn, table: str):
    """REVOKE explícito impede SELECT mesmo no schema public."""
    import psycopg

    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        conn.execute(f"SELECT 1 FROM {table} LIMIT 1").fetchone()
    conn.rollback()  # libera txn pro próximo test


@pytest.mark.parametrize(
    "schema_table",
    [
        "auth.users",
        "storage.buckets",
        "supabase_migrations.schema_migrations",
    ],
)
def test_cannot_access_internal_schemas(conn, schema_table: str):
    """Sem GRANT USAGE no schema, qualquer query falha."""
    import psycopg

    with pytest.raises(
        (psycopg.errors.InsufficientPrivilege, psycopg.errors.UndefinedTable)
    ):
        conn.execute(f"SELECT 1 FROM {schema_table} LIMIT 1").fetchone()
    conn.rollback()


def test_cannot_insert(conn):
    import psycopg

    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        conn.execute(
            "INSERT INTO projects (project_number, name) VALUES (99999, 'fake')"
        )
    conn.rollback()


def test_cannot_update(conn):
    import psycopg

    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        conn.execute("UPDATE projects SET status = 'inactive'")
    conn.rollback()


def test_cannot_delete(conn):
    import psycopg

    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        conn.execute("DELETE FROM projects")
    conn.rollback()


def test_cannot_drop_table(conn):
    import psycopg

    with pytest.raises(
        (psycopg.errors.InsufficientPrivilege, psycopg.errors.SyntaxError)
    ):
        conn.execute("DROP TABLE projects")
    conn.rollback()


def test_cannot_truncate(conn):
    import psycopg

    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        conn.execute("TRUNCATE projects")
    conn.rollback()


def test_statement_timeout_aborts_long_query(conn):
    """Aplicado SET LOCAL no contexto da query — pg_sleep mais que timeout
    deve abortar."""
    import psycopg

    cur = conn.cursor()
    cur.execute("BEGIN")
    cur.execute("SET LOCAL statement_timeout = 1000")  # 1s
    with pytest.raises(psycopg.errors.QueryCanceled):
        cur.execute("SELECT pg_sleep(3)")
    conn.rollback()
