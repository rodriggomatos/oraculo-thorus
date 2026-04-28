"""Repositório leve de leitura de projetos pra tools do agente Q&A."""

from types import TracebackType
from typing import Any

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool


class ProjectRepository:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._pool: AsyncConnectionPool | None = None

    async def open(self) -> None:
        if self._pool is not None:
            return
        pool = AsyncConnectionPool(self._dsn, min_size=1, max_size=2, open=False)
        await pool.open()
        self._pool = pool

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def __aenter__(self) -> "ProjectRepository":
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
            raise RuntimeError("ProjectRepository pool not open; call await repo.open() first")
        return self._pool

    async def list_active_recent(self, limit: int = 10) -> list[dict[str, Any]]:
        async with self._ensured_pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT project_number, name, client "
                    "FROM projects WHERE status = 'ativo' "
                    "ORDER BY updated_at DESC LIMIT %s",
                    (limit,),
                )
                return await cur.fetchall()

    async def search_by_term(self, term: str, limit: int = 5) -> list[dict[str, Any]]:
        async with self._ensured_pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                pattern = f"%{term}%"
                await cur.execute(
                    "SELECT project_number, name, client "
                    "FROM projects "
                    "WHERE name ILIKE %s OR client ILIKE %s "
                    "ORDER BY updated_at DESC LIMIT %s",
                    (pattern, pattern, limit),
                )
                return await cur.fetchall()
