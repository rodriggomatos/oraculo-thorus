"""Schemas HTTP da rota /query."""

from pydantic import BaseModel, Field


class CitationDTO(BaseModel):
    item_code: str
    disciplina: str
    tipo: str | None = None
    node_id: str
    score: float


class QueryRequest(BaseModel):
    question: str
    thread_id: str | None = None
    project_number: int | None = None
    top_k: int = 5


class QueryResponse(BaseModel):
    answer: str
    sources: list[CitationDTO] = Field(default_factory=list)
    found_relevant: bool
    thread_id: str
