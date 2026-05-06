"""FastAPI app — Oráculo Thórus API."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from oraculo_ai.core.config import get_settings

from oraculo_api.logging_config import configure_logging

_settings = get_settings()
configure_logging(_settings)

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver  # noqa: E402
from psycopg.rows import dict_row  # noqa: E402
from psycopg_pool import AsyncConnectionPool  # noqa: E402

from oraculo_ai.core.db import close_db, init_db  # noqa: E402
from oraculo_ai.llm.client import shutdown_traces  # noqa: E402

from oraculo_api.routes import auth, documents, health, projects, query  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()

    await init_db(
        settings.database_url,
        pool_size=settings.db_pool_max_size,
        min_size=settings.db_pool_min_size,
    )

    async with AsyncConnectionPool(
        conninfo=settings.database_url,
        max_size=settings.db_pool_max_size,
        kwargs={
            "autocommit": True,
            "prepare_threshold": 0,
            "row_factory": dict_row,
        },
    ) as checkpointer_pool:
        checkpointer = AsyncPostgresSaver(conn=checkpointer_pool)
        await checkpointer.setup()
        app.state.checkpointer = checkpointer
        try:
            yield
        finally:
            shutdown_traces()
            await close_db()


app = FastAPI(
    title="Oráculo Thórus API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(query.router)
app.include_router(projects.router)
app.include_router(documents.router, tags=["documents"])
