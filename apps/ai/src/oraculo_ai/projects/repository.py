"""Repository: projects + project_scope com versionamento + queries auxiliares.

Operações principais:
- get_next_project_number(): MAX(project_number) + 1 (lock leve via SERIALIZABLE)
- create_project_with_scope(): transação atômica que faz INSERT projects + version 1 de project_scope
  - Idempotente em project_number: se já existir, retorna o existente (não duplica).
- mark_old_versions_superseded() + insert_new_scope_version(): pra re-uploads de planilha
- get_project_scope_current / history / active LDP

Acesso ao pool central via oraculo_ai.core.db.get_pool().
"""

import logging
from decimal import Decimal
from typing import Any
from uuid import UUID

from psycopg.rows import dict_row
from psycopg.types.json import Json

from oraculo_ai.core.db import get_pool
from oraculo_ai.projects.drive import list_project_numbers_from_drive
from oraculo_ai.scope.types import DisciplinaRow, ParsedOrcamento


_log = logging.getLogger(__name__)


class ProjectScopeRow:
    """View leve duma linha de project_scope joinada com scope_template."""

    def __init__(self, row: dict[str, Any]) -> None:
        self.id = row["id"]
        self.project_id = row["project_id"]
        self.scope_template_id = row["scope_template_id"]
        self.disciplina = str(row["disciplina_nome"])
        self.ordem = int(row["ordem"])
        self.version = int(row["version"])
        self.is_current = bool(row["is_current"])
        self.incluir = bool(row["incluir"])
        self.unificar = row["unificar"]
        self.essencial = bool(row["essencial"])
        self.legal = str(row["legal"])
        self.pontos = row["pontos"]
        self.peso_disciplina = row["peso_disciplina"]
        self.ponto_fixo = row["ponto_fixo"]
        self.pontos_calculados = row["pontos_calculados"]
        self.created_at = row["created_at"]
        self.created_by = row.get("created_by")
        self.superseded_at = row.get("superseded_at")
        self.superseded_reason = row.get("superseded_reason")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "scope_template_id": str(self.scope_template_id),
            "disciplina": self.disciplina,
            "ordem": self.ordem,
            "version": self.version,
            "is_current": self.is_current,
            "incluir": self.incluir,
            "unificar": self.unificar,
            "essencial": self.essencial,
            "legal": self.legal,
            "pontos": float(self.pontos) if self.pontos is not None else None,
            "peso_disciplina": float(self.peso_disciplina) if self.peso_disciplina is not None else None,
            "ponto_fixo": float(self.ponto_fixo) if self.ponto_fixo is not None else None,
            "pontos_calculados": float(self.pontos_calculados) if self.pontos_calculados is not None else None,
        }


async def _max_project_number_in_db() -> int:
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT COALESCE(MAX(project_number), 26000) AS max_number FROM projects"
            )
            row = await cur.fetchone()
    if row is None:
        return 26000
    return int(row["max_number"]) if isinstance(row, dict) else int(row[0])


async def get_next_project_number() -> int:
    """Sugere o próximo número de projeto.

    Fonte de verdade: o Drive `107_PROJETOS 2026`, NÃO o banco. A tabela
    `projects` está incompleta (só contém projetos já ingeridos), enquanto
    o Drive tem TODAS as pastas físicas — incluindo as criadas manualmente
    sem ingestão correspondente.

    Estratégia: MAX(numbers do Drive ∪ numbers do DB) + 1. A união cobre o
    edge case onde alguém criou um projeto via API (foi pro DB mas a pasta
    no Drive talvez ainda não exista).

    Fallback: se o Drive falhar (rede, scope, permissão), usa só o DB e loga
    warning. Melhor sugerir baixo do que travar o flow.
    """
    db_max = await _max_project_number_in_db()

    try:
        drive_numbers = await list_project_numbers_from_drive()
    except Exception as exc:
        _log.warning(
            "list_project_numbers_from_drive failed (%s: %s); falling back to DB MAX",
            type(exc).__name__,
            exc,
        )
        return max(db_max, 26000) + 1

    if not drive_numbers:
        _log.warning("Drive returned no project folders; falling back to DB MAX")
        return max(db_max, 26000) + 1

    drive_max = drive_numbers[0]
    return max(drive_max, db_max) + 1


async def get_scope_template_names() -> list[str]:
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute("SELECT nome FROM scope_template ORDER BY ordem")
            rows = await cur.fetchall()
    return [str(r["nome"]) for r in rows]


async def _get_project_id_by_number(conn: Any, project_number: int) -> UUID | None:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            "SELECT id FROM projects WHERE project_number = %s",
            (project_number,),
        )
        row = await cur.fetchone()
    return row["id"] if row else None


async def _scope_template_id_by_name(conn: Any, nome: str) -> UUID | None:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            "SELECT id FROM scope_template WHERE nome = %s LIMIT 1",
            (nome,),
        )
        row = await cur.fetchone()
    return row["id"] if row else None


def _empty_to_none(value: str | None) -> str | None:
    """Converte string vazia/whitespace em None — convenção SQL pra ausência."""
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


async def create_project_with_scope(
    *,
    project_number: int,
    name: str,
    client: str,
    empreendimento: str,
    cidade: str,
    estado: str | None,
    area_m2: Decimal | None,
    fluxo: str | None,
    custo_fator: Decimal | None,
    total_contratado: Decimal | None,
    margem: Decimal | None,
    orcamento_sheets_id: str,
    disciplinas: list[DisciplinaRow],
    created_by: UUID,
    city_ibge_code: str | None = None,
) -> dict[str, Any]:
    """Idempotente em project_number — se já existe, retorna sem duplicar.

    Cria o registro em projects + version=1 de project_scope numa transação atômica.
    Pra re-uploads, use mark_versions_superseded + insert_new_scope_version.
    """
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.transaction():
            existing_id = await _get_project_id_by_number(conn, project_number)
            if existing_id is not None:
                return {
                    "project_id": str(existing_id),
                    "project_number": project_number,
                    "created": False,
                }

            client_clean = _empty_to_none(client)
            empreendimento_clean = _empty_to_none(empreendimento)
            cidade_clean = _empty_to_none(cidade)
            estado_clean = _empty_to_none(estado)

            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    INSERT INTO projects (
                        project_number, name, client, empreendimento, cidade,
                        estado, area_m2, fluxo, custo_fator,
                        total_contratado, margem,
                        orcamento_sheets_id, created_by, status,
                        city_ibge_code
                    ) VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s,
                        %s, %s, 'active',
                        %s
                    )
                    RETURNING id
                    """,
                    (
                        project_number, name, client_clean, empreendimento_clean, cidade_clean,
                        estado_clean, area_m2, _empty_to_none(fluxo), custo_fator,
                        total_contratado, margem,
                        orcamento_sheets_id, str(created_by),
                        _empty_to_none(city_ibge_code),
                    ),
                )
                row = await cur.fetchone()
                if row is None:
                    raise RuntimeError("INSERT projects returned no row")
                project_id: UUID = row["id"]

            inserted = 0
            skipped: list[str] = []
            for d in disciplinas:
                template_id = await _scope_template_id_by_name(conn, d.disciplina.strip())
                if template_id is None:
                    skipped.append(d.disciplina)
                    continue
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        INSERT INTO project_scope (
                            project_id, scope_template_id,
                            version, is_current,
                            incluir, unificar, essencial, legal,
                            pontos, peso_disciplina, ponto_fixo, pontos_calculados,
                            created_by
                        ) VALUES (
                            %s, %s,
                            1, TRUE,
                            %s, %s, %s, %s,
                            %s, %s, %s, %s,
                            %s
                        )
                        """,
                        (
                            str(project_id), str(template_id),
                            d.incluir, d.unificar, d.essencial, d.legal,
                            d.pontos, d.peso_disciplina, d.ponto_fixo, d.pontos_calculados,
                            str(created_by),
                        ),
                    )
                inserted += 1

            return {
                "project_id": str(project_id),
                "project_number": project_number,
                "created": True,
                "scope_inserted": inserted,
                "scope_skipped": skipped,
            }


async def upload_new_scope_version(
    *,
    project_number: int,
    parsed: ParsedOrcamento,
    created_by: UUID,
    reason: str = "Nova versão da planilha de orçamento",
) -> dict[str, Any]:
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.transaction():
            project_id = await _get_project_id_by_number(conn, project_number)
            if project_id is None:
                raise RuntimeError(f"projeto {project_number} não existe")

            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT COALESCE(MAX(version), 0) + 1 AS v FROM project_scope WHERE project_id = %s",
                    (str(project_id),),
                )
                row = await cur.fetchone()
                next_version = int(row["v"]) if row else 1

                await cur.execute(
                    """
                    UPDATE project_scope
                       SET is_current = FALSE,
                           superseded_at = NOW(),
                           superseded_reason = %s
                     WHERE project_id = %s AND is_current = TRUE
                    """,
                    (reason, str(project_id)),
                )

            inserted = 0
            for d in parsed.disciplinas:
                template_id = await _scope_template_id_by_name(conn, d.disciplina.strip())
                if template_id is None:
                    continue
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        INSERT INTO project_scope (
                            project_id, scope_template_id,
                            version, is_current,
                            incluir, unificar, essencial, legal,
                            pontos, peso_disciplina, ponto_fixo, pontos_calculados,
                            created_by
                        ) VALUES (
                            %s, %s,
                            %s, TRUE,
                            %s, %s, %s, %s,
                            %s, %s, %s, %s,
                            %s
                        )
                        """,
                        (
                            str(project_id), str(template_id),
                            next_version,
                            d.incluir, d.unificar, d.essencial, d.legal,
                            d.pontos, d.peso_disciplina, d.ponto_fixo, d.pontos_calculados,
                            str(created_by),
                        ),
                    )
                inserted += 1

            return {
                "project_id": str(project_id),
                "version": next_version,
                "scope_inserted": inserted,
            }


async def get_project_scope_current(project_number: int) -> list[ProjectScopeRow]:
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                SELECT ps.*, st.nome AS disciplina_nome, st.ordem
                FROM project_scope ps
                JOIN scope_template st ON st.id = ps.scope_template_id
                WHERE ps.project_id = (SELECT id FROM projects WHERE project_number = %s)
                  AND ps.is_current = TRUE
                ORDER BY st.ordem
                """,
                (project_number,),
            )
            rows = await cur.fetchall()
    return [ProjectScopeRow(r) for r in rows]


async def get_project_scope_history(project_number: int) -> list[dict[str, Any]]:
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                SELECT version,
                       MAX(created_at) AS updated_at,
                       COUNT(*) AS items,
                       MAX(superseded_at) AS superseded_at,
                       MAX(superseded_reason) AS superseded_reason
                FROM project_scope
                WHERE project_id = (SELECT id FROM projects WHERE project_number = %s)
                GROUP BY version
                ORDER BY version DESC
                """,
                (project_number,),
            )
            rows = await cur.fetchall()
    return [
        {
            "version": int(r["version"]),
            "updated_at": r["updated_at"].isoformat() if r["updated_at"] else None,
            "items": int(r["items"]),
            "superseded_at": r["superseded_at"].isoformat() if r["superseded_at"] else None,
            "superseded_reason": r["superseded_reason"],
        }
        for r in rows
    ]


async def get_active_ldp_disciplines(project_number: int) -> list[dict[str, str]]:
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                SELECT DISTINCT ld.codigo, ld.nome
                FROM ldp_discipline ld
                WHERE ld.sempre_ativa = TRUE
                   OR ld.id IN (
                       SELECT m.ldp_discipline_id
                       FROM project_scope ps
                       JOIN scope_to_ldp_discipline m ON m.scope_template_id = ps.scope_template_id
                       WHERE ps.project_id = (SELECT id FROM projects WHERE project_number = %s)
                         AND ps.is_current = TRUE
                         AND ps.incluir = TRUE
                   )
                ORDER BY ld.codigo
                """,
                (project_number,),
            )
            rows = await cur.fetchall()
    return [{"codigo": str(r["codigo"]), "nome": str(r["nome"])} for r in rows]
