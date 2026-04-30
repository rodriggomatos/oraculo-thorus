"""Endpoint de listagem de projetos ativos."""

from fastapi import APIRouter

from oraculo_ai.agents.qa.repository import ProjectRepository

from oraculo_api.schemas.projects import ProjectDTO


router = APIRouter()


@router.get("/projects", response_model=list[ProjectDTO])
async def list_projects() -> list[ProjectDTO]:
    async with ProjectRepository() as repo:
        rows = await repo.list_active_recent(limit=50)
    return [
        ProjectDTO(
            project_number=int(r["project_number"]),
            name=str(r["name"]),
            client=str(r["client"]) if r.get("client") else None,
        )
        for r in rows
    ]
