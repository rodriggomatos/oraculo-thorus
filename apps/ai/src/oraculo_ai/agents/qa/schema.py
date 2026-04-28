"""Pydantic schemas do agente Q&A."""

from pydantic import BaseModel, Field


class QAQuery(BaseModel):
    question: str
    project_number: int
    top_k: int = 5


class Citation(BaseModel):
    item_code: str
    disciplina: str
    tipo: str | None = None
    node_id: str
    score: float


class QAAnswer(BaseModel):
    answer: str
    sources: list[Citation] = Field(default_factory=list)
    found_relevant: bool
