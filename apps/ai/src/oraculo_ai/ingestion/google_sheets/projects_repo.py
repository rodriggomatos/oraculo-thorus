"""ProjectsWriter — UPSERT em projects via psycopg."""

from types import TracebackType
from uuid import UUID

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from oraculo_ai.core.db import get_pool


class ProjectsWriter:
    def __init__(self, pool: AsyncConnectionPool | None = None) -> None:
        self._pool: AsyncConnectionPool | None = pool

    async def open(self) -> None:
        if self._pool is None:
            self._pool = get_pool()

    async def close(self) -> None:
        return None

    async def __aenter__(self) -> "ProjectsWriter":
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
            raise RuntimeError("ProjectsWriter not opened; call await writer.open() first")
        return self._pool

    async def upsert_project(
        self,
        project_number: int,
        name: str,
        client: str,
        google_sheet_id: str,
    ) -> UUID:
        async with self._ensured_pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    INSERT INTO projects (project_number, name, client, google_sheet_id, status)
                    VALUES (%s, %s, %s, %s, 'ativo')
                    ON CONFLICT (project_number) DO UPDATE SET
                        name = EXCLUDED.name,
                        client = EXCLUDED.client,
                        google_sheet_id = EXCLUDED.google_sheet_id,
                        updated_at = now()
                    RETURNING id
                    """,
                    (project_number, name, client, google_sheet_id),
                )
                row = await cur.fetchone()
                if row is None:
                    raise RuntimeError("upsert_project returned no row")
                return UUID(str(row["id"]))
