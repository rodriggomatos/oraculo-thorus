"""Conexões DB centralizadas — pool psycopg + engines SQLAlchemy globais."""

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from sqlalchemy import Engine, create_engine
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


_pool: AsyncConnectionPool | None = None
_async_engine: AsyncEngine | None = None
_sync_engine: Engine | None = None


async def init_db(database_url: str, pool_size: int = 5) -> None:
    global _pool, _async_engine, _sync_engine
    if _pool is not None:
        raise RuntimeError("DB already initialized; call close_db() before re-initializing")

    pool = AsyncConnectionPool(
        database_url,
        min_size=1,
        max_size=pool_size,
        open=False,
        check=AsyncConnectionPool.check_connection,
        max_lifetime=600,
        max_idle=300,
        kwargs={
            "autocommit": True,
            "prepare_threshold": 0,
            "row_factory": dict_row,
        },
    )
    await pool.open()
    _pool = pool

    async_dsn = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    _async_engine = create_async_engine(
        async_dsn,
        pool_size=pool_size,
        max_overflow=0,
        pool_pre_ping=True,
        pool_recycle=300,
    )

    _sync_engine = create_engine(
        database_url,
        pool_size=2,
        max_overflow=0,
        pool_pre_ping=True,
        pool_recycle=300,
    )


async def close_db() -> None:
    global _pool, _async_engine, _sync_engine
    if _pool is not None:
        await _pool.close()
        _pool = None
    if _async_engine is not None:
        await _async_engine.dispose()
        _async_engine = None
    if _sync_engine is not None:
        _sync_engine.dispose()
        _sync_engine = None


def get_pool() -> AsyncConnectionPool:
    if _pool is None:
        raise RuntimeError("DB not initialized; call await init_db(...) first")
    return _pool


def get_engine() -> AsyncEngine:
    if _async_engine is None:
        raise RuntimeError("DB not initialized; call await init_db(...) first")
    return _async_engine


def get_sync_engine() -> Engine:
    if _sync_engine is None:
        raise RuntimeError("DB not initialized; call await init_db(...) first")
    return _sync_engine
