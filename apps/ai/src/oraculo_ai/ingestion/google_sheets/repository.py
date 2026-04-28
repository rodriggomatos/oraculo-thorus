"""Persistência: definitions via psycopg + chunks via PGVectorStore (LlamaIndex)."""

from types import TracebackType
from typing import Any
from uuid import UUID

from llama_index.core import Settings
from llama_index.core.schema import TextNode
from llama_index.vector_stores.postgres import PGVectorStore
from psycopg.rows import dict_row
from psycopg.types.json import Json
from psycopg_pool import AsyncConnectionPool
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from oraculo_ai.core.config import get_settings
from oraculo_ai.ingestion.google_sheets.vector_store import make_vector_store
from oraculo_ai.ingestion.schema import Definition


class SheetsRepository:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._pool: AsyncConnectionPool | None = None

    async def open(self) -> None:
        if self._pool is not None:
            return
        pool = AsyncConnectionPool(self._dsn, min_size=1, max_size=4, open=False)
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


class ChunksVectorStore:
    def __init__(self) -> None:
        self._engine: AsyncEngine | None = None
        self._vector_store: PGVectorStore | None = None

    async def open(self) -> None:
        if self._vector_store is not None:
            return
        settings = get_settings()
        async_dsn = settings.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        self._engine = create_async_engine(async_dsn)
        self._vector_store = make_vector_store()

    async def close(self) -> None:
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
        self._vector_store = None

    async def __aenter__(self) -> "ChunksVectorStore":
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
    def _ensured_engine(self) -> AsyncEngine:
        if self._engine is None:
            raise RuntimeError("ChunksVectorStore not opened; call await store.open() first")
        return self._engine

    @property
    def _ensured_store(self) -> PGVectorStore:
        if self._vector_store is None:
            raise RuntimeError("ChunksVectorStore not opened; call await store.open() first")
        return self._vector_store

    async def fetch_existing_node_id_for_source(
        self,
        source_table: str,
        source_row_id: UUID,
    ) -> tuple[str, str] | None:
        try:
            async with self._ensured_engine.connect() as conn:
                result = await conn.execute(
                    text(
                        "SELECT node_id, metadata_->>'content_hash' AS content_hash "
                        "FROM data_chunks "
                        "WHERE metadata_->>'source_table' = :st "
                        "AND metadata_->>'source_row_id' = :srid "
                        "LIMIT 1"
                    ),
                    {"st": source_table, "srid": str(source_row_id)},
                )
                row = result.first()
        except ProgrammingError:
            return None
        if row is None:
            return None
        return (str(row.node_id), row.content_hash or "")

    async def add_or_update(
        self,
        definition_id: UUID,
        project_id: UUID,
        content: str,
        content_hash: str,
        metadata_extra: dict[str, str],
        existing_node_id: str | None,
    ) -> str:
        store = self._ensured_store
        if existing_node_id is not None:
            await store.adelete_nodes(node_ids=[existing_node_id])

        metadata: dict[str, Any] = {
            "source_table": "definitions",
            "source_row_id": str(definition_id),
            "project_id": str(project_id),
            "content_hash": content_hash,
            **metadata_extra,
        }
        node = TextNode(text=content, metadata=metadata)
        node.embedding = await Settings.embed_model.aget_text_embedding(content)
        ids = await store.async_add([node])
        return str(ids[0])
