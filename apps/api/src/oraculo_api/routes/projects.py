"""Endpoints de projetos: listagem + criação via 3-step flow (sem interrupt LangGraph)."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from oraculo_ai.agents.qa.repository import ProjectRepository
from oraculo_ai.permissions import check_permission
from oraculo_ai.projects import create_project_with_scope, get_next_project_number
from oraculo_ai.scope import parse_orcamento_from_sheets, validate_against_template
from oraculo_ai.scope.types import ParsedOrcamento, ValidationResult

from oraculo_api.auth import UserContext, get_current_user
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


class SuggestNumberResponse(BaseModel):
    suggested: int


class ParseSheetRequest(BaseModel):
    spreadsheet_id: str = Field(min_length=8)


class ParseSheetResponse(BaseModel):
    parsed: ParsedOrcamento
    validation: ValidationResult


class ProjectMetadataPayload(BaseModel):
    cliente: str
    empreendimento: str
    cidade: str
    estado: str | None = None


class CreateProjectRequest(BaseModel):
    spreadsheet_id: str = Field(min_length=8)
    confirmed_number: int = Field(gt=0)
    metadata: ProjectMetadataPayload


class CreateProjectResponse(BaseModel):
    project_id: str
    project_number: int
    total_contratado: float | None
    margem: float | None
    drive_folder_pending: bool = True
    scope_inserted: int = 0
    scope_skipped: list[str] = []
    already_existed: bool = False


@router.post("/projects/suggest-number", response_model=SuggestNumberResponse)
async def suggest_number(
    user: UserContext = Depends(get_current_user),
) -> SuggestNumberResponse:
    if not check_permission(user, "create_project"):
        raise HTTPException(status_code=403, detail="Sem permissão pra criar projeto")
    suggested = await get_next_project_number()
    return SuggestNumberResponse(suggested=suggested)


@router.post("/projects/parse-sheet", response_model=ParseSheetResponse)
async def parse_sheet(
    body: ParseSheetRequest,
    user: UserContext = Depends(get_current_user),
) -> ParseSheetResponse:
    if not check_permission(user, "create_project"):
        raise HTTPException(status_code=403, detail="Sem permissão pra criar projeto")

    try:
        parsed = await parse_orcamento_from_sheets(body.spreadsheet_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))

    from oraculo_ai.projects import get_scope_template_names

    template_names = await get_scope_template_names()
    validation = validate_against_template(parsed, template_names)
    return ParseSheetResponse(parsed=parsed, validation=validation)


@router.post("/projects/create", response_model=CreateProjectResponse)
async def create_project_endpoint(
    body: CreateProjectRequest,
    user: UserContext = Depends(get_current_user),
) -> CreateProjectResponse:
    if not check_permission(user, "create_project"):
        raise HTTPException(status_code=403, detail="Sem permissão pra criar projeto")

    try:
        parsed = await parse_orcamento_from_sheets(body.spreadsheet_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))

    name = (
        f"{body.confirmed_number} - "
        f"{body.metadata.cliente} - "
        f"{body.metadata.empreendimento}"
    )

    form_estado = (body.metadata.estado or "").strip() or None
    estado = form_estado if form_estado is not None else parsed.estado

    result: dict[str, Any] = await create_project_with_scope(
        project_number=body.confirmed_number,
        name=name,
        client=body.metadata.cliente,
        empreendimento=body.metadata.empreendimento,
        cidade=body.metadata.cidade,
        estado=estado,
        area_m2=parsed.area_m2,
        fluxo=parsed.fluxo,
        custo_fator=parsed.custo_fator,
        total_contratado=parsed.total_contratado,
        margem=parsed.margem,
        orcamento_sheets_id=body.spreadsheet_id,
        disciplinas=parsed.disciplinas,
        created_by=user.user_id,
    )

    return CreateProjectResponse(
        project_id=str(result["project_id"]),
        project_number=int(result["project_number"]),
        total_contratado=float(parsed.total_contratado) if parsed.total_contratado else None,
        margem=float(parsed.margem) if parsed.margem else None,
        drive_folder_pending=True,
        scope_inserted=int(result.get("scope_inserted", 0)),
        scope_skipped=list(result.get("scope_skipped", [])),
        already_existed=not bool(result.get("created", True)),
    )
