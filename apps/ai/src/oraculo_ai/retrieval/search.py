"""Busca semântica de chunks por projeto."""

from uuid import UUID

from langfuse import get_client, observe
from llama_index.core import VectorStoreIndex
from llama_index.core.vector_stores import (
    FilterOperator,
    MetadataFilter,
    MetadataFilters,
)

from oraculo_ai.core.config import get_settings
from oraculo_ai.ingestion.google_sheets.repository import SheetsRepository
from oraculo_ai.ingestion.google_sheets.vector_store import make_vector_store
from oraculo_ai.retrieval.schema import ChunkResult, SearchQuery


@observe(as_type="retriever", name="vector-search")
async def search(query: SearchQuery) -> list[ChunkResult]:
    settings = get_settings()

    async with SheetsRepository(settings.database_url) as repo:
        project = await repo.get_project_by_number(query.project_number)
        if project is None:
            raise RuntimeError(
                f"project number {query.project_number} not found in `projects` table"
            )
        project_id: UUID = project["id"]

    vector_store = make_vector_store()
    index = VectorStoreIndex.from_vector_store(vector_store)

    filters = MetadataFilters(
        filters=[
            MetadataFilter(
                key="project_id",
                value=str(project_id),
                operator=FilterOperator.EQ,
            )
        ]
    )

    retriever = index.as_retriever(
        similarity_top_k=query.top_k,
        filters=filters,
    )

    nodes_with_score = await retriever.aretrieve(query.query)

    results: list[ChunkResult] = [
        ChunkResult(
            node_id=str(nws.node.node_id),
            score=float(nws.score) if nws.score is not None else 0.0,
            content=nws.node.get_content(),
            metadata=dict(nws.node.metadata),
        )
        for nws in nodes_with_score
    ]

    get_client().update_current_span(
        input=query.query,
        output={
            "count": len(results),
            "node_ids": [r.node_id for r in results],
        },
        metadata={
            "project_number": str(query.project_number),
            "project_id": str(project_id),
            "top_k": str(query.top_k),
        },
    )

    return results
