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
from typing import Any
from uuid import UUID

from psycopg.rows import dict_row

from oraculo_ai.core.config import get_settings
from oraculo_ai.core.db import get_pool
from oraculo_ai.ldp.master_reader import MasterRow
from oraculo_ai.ldp.seed import filter_master_for_active
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
        self.legal = str(row["legal"])
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
            "legal": self.legal,
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


async def get_project_drive_state(project_id: UUID) -> dict[str, Any] | None:
    """Retorna {name, drive_folder_path, created_by} ou None se projeto não existe."""
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                SELECT name, drive_folder_path, created_by
                FROM projects
                WHERE id = %s
                """,
                (str(project_id),),
            )
            row = await cur.fetchone()
    if row is None:
        return None
    return {
        "name": str(row["name"]),
        "drive_folder_path": (
            str(row["drive_folder_path"]) if row["drive_folder_path"] else None
        ),
        "created_by": row["created_by"],
    }


async def update_drive_folder_path(project_id: UUID, folder_id: str) -> bool:
    """Salva o folder_id em projects.drive_folder_path. Retorna False se id inexistente."""
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE projects
                   SET drive_folder_path = %s,
                       updated_at = NOW()
                 WHERE id = %s
                """,
                (folder_id, str(project_id)),
            )
            return cur.rowcount > 0


async def get_project_ldp_state(project_id: UUID) -> dict[str, Any] | None:
    """Estado pra geração da planilha LDP: pasta do Drive, ldp_sheets_id, metadata."""
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                SELECT project_number, name, empreendimento, cidade, estado,
                       drive_folder_path, ldp_sheets_id, created_by
                FROM projects
                WHERE id = %s
                """,
                (str(project_id),),
            )
            row = await cur.fetchone()
    if row is None:
        return None
    return {
        "project_number": int(row["project_number"]),
        "name": str(row["name"]),
        "empreendimento": (
            str(row["empreendimento"]) if row["empreendimento"] else None
        ),
        "cidade": str(row["cidade"]) if row["cidade"] else None,
        "estado": str(row["estado"]) if row["estado"] else None,
        "drive_folder_path": (
            str(row["drive_folder_path"]) if row["drive_folder_path"] else None
        ),
        "ldp_sheets_id": str(row["ldp_sheets_id"]) if row["ldp_sheets_id"] else None,
        "created_by": row["created_by"],
    }


async def update_ldp_sheets_id(project_id: UUID, sheets_id: str) -> bool:
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE projects
                   SET ldp_sheets_id = %s,
                       updated_at = NOW()
                 WHERE id = %s
                """,
                (sheets_id, str(project_id)),
            )
            return cur.rowcount > 0


async def get_definitions_for_project(project_id: UUID) -> list[dict[str, Any]]:
    """Versão vigente de cada `item_code` do projeto, ordenada como na master.

    Pega a linha mais recente por (project_id, item_code) — assim respostas
    registradas via chat (após a semeadura inicial) vão pra planilha.
    """
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                WITH latest AS (
                    SELECT DISTINCT ON (item_code)
                           disciplina, tipo, fase, item_code, pergunta,
                           status, custo, opcao_escolhida, observacoes,
                           validado, informacao_auxiliar, apoio_1, apoio_2,
                           source_row
                    FROM definitions
                    WHERE project_id = %s
                    ORDER BY item_code, created_at DESC
                )
                SELECT * FROM latest
                ORDER BY disciplina NULLS LAST, source_row NULLS LAST
                """,
                (str(project_id),),
            )
            rows = await cur.fetchall()
    return [dict(r) for r in rows]


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


def format_project_name(
    *,
    project_number: int,
    client: str | None,
    empreendimento: str | None,
    cidade: str | None,
    estado: str | None,
) -> str:
    """Monta o `projects.name` no padrão Thórus.

    Padrão: "{number} - {client} - {empreendimento} - {cidade} - {estado}".

    Defensivo: cada parte vazia/None vira "—" (em vez de quebrar o formato ou
    deixar segmentos colapsando). Cidade e estado vêm do form via metadata,
    então normalmente sempre estão preenchidos; o placeholder cobre o caminho
    do agent tool (que ainda não coleta estado pela conversa) e edge cases.
    """

    def _or_dash(value: str | None) -> str:
        cleaned = _empty_to_none(value)
        return cleaned if cleaned else "—"

    return (
        f"{project_number} - "
        f"{_or_dash(client)} - "
        f"{_or_dash(empreendimento)} - "
        f"{_or_dash(cidade)} - "
        f"{_or_dash(estado)}"
    )


async def create_project_with_scope(
    *,
    project_number: int,
    name: str,
    client: str,
    empreendimento: str,
    cidade: str,
    estado: str | None,
    orcamento_sheets_id: str,
    disciplinas: list[DisciplinaRow],
    created_by: UUID,
    city_ibge_code: str | None = None,
    master_rows: list[MasterRow] | None = None,
) -> dict[str, Any]:
    """Idempotente em project_number — se já existe, retorna sem duplicar.

    Cria o registro em projects + version=1 de project_scope numa transação atômica.
    Quando `master_rows` é fornecido, popula `definitions` com as perguntas da
    Master R04 filtradas pelas categorias LDP ativas (regra do Raul). Tudo na
    mesma transação: se a semeadura falhar, o projeto inteiro faz rollback.

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
                        estado,
                        orcamento_sheets_id, created_by, status,
                        city_ibge_code
                    ) VALUES (
                        %s, %s, %s, %s, %s,
                        %s,
                        %s, %s, 'active',
                        %s
                    )
                    RETURNING id
                    """,
                    (
                        project_number, name, client_clean, empreendimento_clean, cidade_clean,
                        estado_clean,
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
                            incluir, legal,
                            created_by
                        ) VALUES (
                            %s, %s,
                            1, TRUE,
                            %s, %s,
                            %s
                        )
                        """,
                        (
                            str(project_id), str(template_id),
                            d.incluir, d.legal,
                            str(created_by),
                        ),
                    )
                inserted += 1

            result: dict[str, Any] = {
                "project_id": str(project_id),
                "project_number": project_number,
                "created": True,
                "scope_inserted": inserted,
                "scope_skipped": skipped,
                "definitions_count": 0,
                "definitions_by_discipline": {},
            }

            if master_rows is not None:
                seeded = await _populate_definitions_from_master(
                    conn,
                    project_id=project_id,
                    user_id=created_by,
                    master_rows=master_rows,
                )
                result["definitions_count"] = seeded["count"]
                result["definitions_by_discipline"] = seeded["by_discipline"]

            return result


async def _active_ldp_discipline_names(conn: Any, project_id: UUID) -> list[str]:
    """Aplica a regra do Raul intra-transação contra o `project_id` recém-inserido."""
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            """
            SELECT DISTINCT ld.nome
            FROM ldp_discipline ld
            WHERE ld.sempre_ativa = TRUE
               OR ld.id IN (
                   SELECT m.ldp_discipline_id
                   FROM project_scope ps
                   JOIN scope_to_ldp_discipline m ON m.scope_template_id = ps.scope_template_id
                   WHERE ps.project_id = %s
                     AND ps.is_current = TRUE
                     AND ps.incluir = TRUE
               )
            ORDER BY ld.nome
            """,
            (str(project_id),),
        )
        rows = await cur.fetchall()
    return [str(r["nome"]) for r in rows]


async def _populate_definitions_from_master(
    conn: Any,
    *,
    project_id: UUID,
    user_id: UUID,
    master_rows: list[MasterRow],
) -> dict[str, Any]:
    """Insere as perguntas da Master R04 em `definitions` filtradas pelas categorias ativas."""
    active_names = await _active_ldp_discipline_names(conn, project_id)
    eligible = filter_master_for_active(master_rows, active_names)
    if not eligible:
        return {"count": 0, "by_discipline": {}}

    settings = get_settings()
    source_sheet_id = settings.ldp_master_sheet_id

    by_discipline: dict[str, int] = {}
    async with conn.cursor() as cur:
        for row in eligible:
            await cur.execute(
                """
                INSERT INTO definitions (
                    project_id, disciplina, tipo, fase, item_code,
                    pergunta, status,
                    informacao_auxiliar, apoio_1, apoio_2,
                    source_sheet_id, source_row,
                    fonte_informacao, fonte_descricao,
                    created_by_user_id, updated_by_user_id
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, 'Em análise',
                    %s, %s, %s,
                    %s, %s,
                    'lista_definicoes_inicial', 'Master R04 (auto-populate ao criar projeto)',
                    %s, %s
                )
                """,
                (
                    str(project_id), row.disciplina, row.tipo, row.fase, row.item_code,
                    row.pergunta,
                    row.informacao_auxiliar, row.apoio_1, row.apoio_2,
                    source_sheet_id, row.source_row,
                    str(user_id), str(user_id),
                ),
            )
            by_discipline[row.disciplina] = by_discipline.get(row.disciplina, 0) + 1

    return {"count": len(eligible), "by_discipline": by_discipline}


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
                            incluir, legal,
                            created_by
                        ) VALUES (
                            %s, %s,
                            %s, TRUE,
                            %s, %s,
                            %s
                        )
                        """,
                        (
                            str(project_id), str(template_id),
                            next_version,
                            d.incluir, d.legal,
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
