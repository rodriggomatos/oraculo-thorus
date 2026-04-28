"""Schemas HTTP da rota /projects."""

from pydantic import BaseModel


class ProjectDTO(BaseModel):
    project_number: int
    name: str
    client: str | None = None
