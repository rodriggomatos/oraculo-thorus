"""Pydantic schemas do módulo de retrieval."""

from typing import Any

from pydantic import BaseModel, Field


class SearchQuery(BaseModel):
    query: str
    project_number: int
    top_k: int = 5


class ChunkResult(BaseModel):
    node_id: str
    score: float
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
