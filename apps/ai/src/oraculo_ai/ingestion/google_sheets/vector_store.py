"""Configuração do PGVectorStore — Settings.embed_model global + factory."""

from llama_index.core import Settings
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.postgres import PGVectorStore

from oraculo_ai.core.config import get_settings
from oraculo_ai.core.db import get_engine, get_sync_engine


_settings = get_settings()

Settings.embed_model = OpenAIEmbedding(
    model=_settings.embedding_model,
    embed_batch_size=20,
    api_key=_settings.openai_api_key or None,
)


def make_vector_store() -> PGVectorStore:
    sync_dsn = _settings.database_url
    async_dsn = sync_dsn.replace("postgresql://", "postgresql+asyncpg://", 1)
    return PGVectorStore(
        connection_string=sync_dsn,
        async_connection_string=async_dsn,
        table_name="chunks",
        embed_dim=_settings.embedding_dim,
        hybrid_search=False,
        use_jsonb=True,
        hnsw_kwargs={
            "hnsw_m": 16,
            "hnsw_ef_construction": 64,
            "hnsw_ef_search": 40,
            "hnsw_dist_method": "vector_cosine_ops",
        },
        perform_setup=False,
        engine=get_sync_engine(),
        async_engine=get_engine(),
    )
