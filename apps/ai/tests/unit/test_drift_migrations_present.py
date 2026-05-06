"""Guarda estática contra remoção/edição acidental das migrations corretivas.

Não conecta ao banco — só verifica que as 4 migrations criadas em
20260505 ainda estão no repo e contêm os comandos que reconciliam o drift
identificado no audit. Se alguém deletar/editar uma delas, este test
quebra antes do deploy.
"""

from pathlib import Path

import pytest


_MIGRATIONS_DIR = (
    Path(__file__).resolve().parents[4] / "supabase" / "migrations"
)


def _read(name: str) -> str:
    path = _MIGRATIONS_DIR / name
    assert path.is_file(), f"migration ausente: {name}"
    return path.read_text(encoding="utf-8")


def test_estado_check_migration_exists_and_lists_27_uf():
    sql = _read("20260505120000_estado_check_all_brazilian_states.sql")
    assert "DROP CONSTRAINT IF EXISTS projects_estado_check" in sql
    assert "DROP CONSTRAINT IF EXISTS city_estado_check" in sql
    # Sanity: a lista de UFs precisa estar no SQL (27 = 26 estados + DF)
    for uf in [
        "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
        "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
        "RS", "RO", "RR", "SC", "SP", "SE", "TO",
    ]:
        assert f"'{uf}'" in sql, f"UF {uf!r} faltando na migration de estado_check"


@pytest.mark.parametrize(
    "table",
    [
        "project_scope",
        "scope_template",
        "ldp_discipline",
        "scope_to_ldp_discipline",
        "source_documents",
    ],
)
def test_rls_migration_enables_each_scope_table(table: str):
    sql = _read("20260505130000_enable_rls_on_scope_tables.sql")
    assert f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY" in sql
    assert f"auth_read_{table}" in sql


def test_city_policy_recreate_migration():
    sql = _read("20260505140000_recreate_city_read_policy.sql")
    assert 'DROP POLICY IF EXISTS "auth_read_city"' in sql
    assert 'CREATE POLICY "auth_read_city"' in sql
    assert "auth.uid() IS NOT NULL" in sql


def test_drop_chunks_legacy_backup_migration():
    sql = _read("20260505150000_drop_chunks_legacy_backup.sql")
    assert "DROP TABLE IF EXISTS chunks_legacy_backup" in sql
