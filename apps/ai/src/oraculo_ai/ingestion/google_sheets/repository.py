"""UPSERT em definitions e chunks via psycopg 3 async + pgvector."""

from types import TracebackType
from typing import Any
from uuid import UUID

from pgvector.psycopg import register_vector_async
from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg.types.json import Json
from psycopg_pool import AsyncConnectionPool

from oraculo_ai.ingestion.schema import ChunkData, Definition


async def _configure_connection(conn: AsyncConnection) -> None:
    await register_vector_async(conn)


class SheetsRepository:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._pool: AsyncConnectionPool | None = None

    async def open(self) -> None:
        if self._pool is not None:
            return
        pool = AsyncConnectionPool(
            self._dsn,
            min_size=1,
            max_size=4,
            open=False,
            configure=_configure_connection,
        )
        await pool.open()
        self._pool = pool

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def __aenter__(self) -> "SheetsRepository":
        await self.open()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.close()

    @property
    def _ensured_pool(self) -> AsyncConnectionPool:
        if self._pool is None:
            raise RuntimeError("repository pool not open; call await repo.open() first")
        return self._pool

    async def get_project_by_number(self, project_number: int) -> dict[str, Any] | None:
        async with self._ensured_pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT id, project_number, name, google_sheet_id "
                    "FROM projects WHERE project_number = %s",
                    (project_number,),
                )
                return await cur.fetchone()

    async def upsert_definition(self, definition: Definition) -> tuple[UUID, bool]:
        sql = """
        INSERT INTO definitions (
            project_id, disciplina, tipo, fase, item_code, pergunta,
            opcao_escolhida, status, custo, observacoes, validado,
            informacao_auxiliar, apoio_1, apoio_2,
            source_sheet_id, source_row, raw_data
        ) VALUES (
            %(project_id)s, %(disciplina)s, %(tipo)s, %(fase)s, %(item_code)s, %(pergunta)s,
            %(opcao_escolhida)s, %(status)s, %(custo)s, %(observacoes)s, %(validado)s,
            %(informacao_auxiliar)s, %(apoio_1)s, %(apoio_2)s,
            %(source_sheet_id)s, %(source_row)s, %(raw_data)s
        )
        ON CONFLICT (project_id, item_code) DO UPDATE SET
            disciplina = EXCLUDED.disciplina,
            tipo = EXCLUDED.tipo,
            fase = EXCLUDED.fase,
            pergunta = EXCLUDED.pergunta,
            opcao_escolhida = EXCLUDED.opcao_escolhida,
            status = EXCLUDED.status,
            custo = EXCLUDED.custo,
            observacoes = EXCLUDED.observacoes,
            validado = EXCLUDED.validado,
            informacao_auxiliar = EXCLUDED.informacao_auxiliar,
            apoio_1 = EXCLUDED.apoio_1,
            apoio_2 = EXCLUDED.apoio_2,
            source_sheet_id = EXCLUDED.source_sheet_id,
            source_row = EXCLUDED.source_row,
            raw_data = EXCLUDED.raw_data,
            updated_at = now()
        RETURNING id, (xmax = 0) AS inserted
        """
        params: dict[str, Any] = definition.model_dump(exclude={"id"})
        params["raw_data"] = Json(params["raw_data"]) if params["raw_data"] is not None else None

        async with self._ensured_pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, params)
                row = await cur.fetchone()
                if row is None:
                    raise RuntimeError("upsert_definition returned no row")
                return row[0], bool(row[1])

    async def fetch_chunk_for_source(
        self,
        source_table: str,
        source_row_id: UUID,
    ) -> dict[str, Any] | None:
        async with self._ensured_pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT id, content_hash FROM chunks "
                    "WHERE source_table = %s AND source_row_id = %s LIMIT 1",
                    (source_table, source_row_id),
                )
                return await cur.fetchone()

    async def upsert_chunk(
        self,
        chunk: ChunkData,
        existing_id: UUID | None = None,
    ) -> tuple[UUID, str]:
        async with self._ensured_pool.connection() as conn:
            async with conn.cursor() as cur:
                if existing_id is None:
                    await cur.execute(
                        """
                        INSERT INTO chunks (
                            project_id, source_table, source_row_id,
                            content, content_hash, embedding, metadata
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s
                        )
                        RETURNING id
                        """,
                        (
                            chunk.project_id,
                            chunk.source_table,
                            chunk.source_row_id,
                            chunk.content,
                            chunk.content_hash,
                            chunk.embedding,
                            Json(chunk.metadata),
                        ),
                    )
                    row = await cur.fetchone()
                    if row is None:
                        raise RuntimeError("insert chunk returned no row")
                    return row[0], "created"

                await cur.execute(
                    """
                    UPDATE chunks SET
                        content = %s,
                        content_hash = %s,
                        embedding = %s,
                        metadata = %s
                    WHERE id = %s
                    """,
                    (
                        chunk.content,
                        chunk.content_hash,
                        chunk.embedding,
                        Json(chunk.metadata),
                        existing_id,
                    ),
                )
                return existing_id, "updated"
