"""FastAPI app — Oráculo Thórus API."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from oraculo_ai.core.config import get_settings
from oraculo_ai.llm.client import shutdown_traces

from oraculo_api.routes import health, projects, query


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    async with AsyncConnectionPool(
        conninfo=settings.database_url,
        max_size=20,
        kwargs={
            "autocommit": True,
            "prepare_threshold": 0,
            "row_factory": dict_row,
        },
    ) as pool:
        checkpointer = AsyncPostgresSaver(conn=pool)
        await checkpointer.setup()
        app.state.checkpointer = checkpointer
        try:
            yield
        finally:
            shutdown_traces()


app = FastAPI(
    title="Oráculo Thórus API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(query.router)
app.include_router(projects.router)
