"""Pydantic schemas do agente Q&A."""

from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class UserContext(BaseModel):
    user_id: UUID
    email: str
    name: str
    role: str = "engineer"
    # Permissões extras carregadas de user_profiles.permissions. Default
    # vazio pra que o caller possa omitir e check_permission funcione sem
    # AttributeError em paths non-admin.
    # TODO sprint futura: carregar permissions reais ao construir o
    # AgentUserContext em apps/api/src/oraculo_api/routes/query.py.
    permissions: list[str] = Field(default_factory=list)


class QAQuery(BaseModel):
    question: str
    project_number: int | None = None
    top_k: int = 5
    thread_id: str = Field(default_factory=lambda: str(uuid4()))


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
