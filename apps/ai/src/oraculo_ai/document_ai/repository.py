"""Repository de source_documents."""

from types import TracebackType
from typing import Any
from uuid import UUID

from psycopg.rows import dict_row
from psycopg.types.json import Json
from psycopg_pool import AsyncConnectionPool

from oraculo_ai.core.db import get_pool


class SourceDocumentsRepository:
    def __init__(self, pool: AsyncConnectionPool | None = None) -> None:
        self._pool: AsyncConnectionPool | None = pool

    async def open(self) -> None:
        if self._pool is None:
            self._pool = get_pool()

    async def close(self) -> None:
        return None

    async def __aenter__(self) -> "SourceDocumentsRepository":
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
            raise RuntimeError("SourceDocumentsRepository not opened")
        return self._pool

    async def find_by_hash(
        self,
        project_id: UUID,
        content_hash: str,
    ) -> dict[str, Any] | None:
        async with self._ensured_pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT id, project_id, filename, file_format, content_hash, uploaded_at "
                    "FROM source_documents "
                    "WHERE project_id = %s AND content_hash = %s LIMIT 1",
                    (project_id, content_hash),
                )
                return await cur.fetchone()

    async def create(
        self,
        project_id: UUID,
        filename: str,
        file_format: str,
        content_hash: str,
        content_markdown: str,
        metadata: dict[str, Any] | None = None,
    ) -> UUID:
        async with self._ensured_pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    INSERT INTO source_documents
                        (project_id, filename, file_format, content_hash, content_markdown, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        project_id,
                        filename,
                        file_format,
                        content_hash,
                        content_markdown,
                        Json(metadata or {}),
                    ),
                )
                row = await cur.fetchone()
                if row is None:
                    raise RuntimeError("create source_document returned no row")
                return row["id"]
