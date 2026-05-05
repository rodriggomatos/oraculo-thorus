"""Endpoints de projetos: listagem + criação via 3-step flow (sem interrupt LangGraph)."""

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from oraculo_ai.agents.qa.repository import ProjectRepository
from oraculo_ai.drive import (
    DriveFolderAlreadyExistsError,
    DriveTemplateNotAccessibleError,
    copy_project_template,
)
from oraculo_ai.ldp import (
    DefinicoesParentNotEditableError,
    DriveFolderStructureError,
    LdpSheetAlreadyExistsError,
    LdpSheetGenerationError,
    MasterNotAccessibleError,
    generate_ldp_sheet,
    read_master_r04,
)
from oraculo_ai.permissions import check_permission
from oraculo_ai.projects import (
    create_project_with_scope,
    format_project_name,
    get_next_project_number,
    get_project_drive_state,
    get_project_ldp_state,
    update_drive_folder_path,
)
from oraculo_ai.scope import parse_orcamento_from_sheets, validate_against_template
from oraculo_ai.scope.types import ParsedOrcamento, ValidationResult

from oraculo_api.auth import UserContext, get_current_user
from oraculo_api.schemas.projects import ProjectDTO


_log = logging.getLogger(__name__)


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
    city_id: int | None = None


class CreateProjectRequest(BaseModel):
    spreadsheet_id: str = Field(min_length=8)
    confirmed_number: int = Field(gt=0)
    metadata: ProjectMetadataPayload


class CreateProjectResponse(BaseModel):
    project_id: str
    project_number: int
    project_name: str
    drive_folder_pending: bool = True
    drive_folder_id: str | None = None
    ldp_sheets_id: str | None = None
    scope_inserted: int = 0
    scope_skipped: list[str] = []
    already_existed: bool = False
    definitions_count: int = 0
    definitions_by_discipline: dict[str, int] = {}


class CreateDriveFolderResponse(BaseModel):
    folder_id: str
    folder_url: str
    folder_name: str


class CreateLdpSheetResponse(BaseModel):
    sheets_id: str
    sheets_url: str
    sheets_name: str
    rows_written: int


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

    try:
        master_rows = await read_master_r04()
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))

    estado = (body.metadata.estado or "").strip() or None

    name = format_project_name(
        project_number=body.confirmed_number,
        client=body.metadata.cliente,
        empreendimento=body.metadata.empreendimento,
        cidade=body.metadata.cidade,
        estado=estado,
    )

    city_ibge_code = (
        str(body.metadata.city_id) if body.metadata.city_id is not None else None
    )

    result: dict[str, Any] = await create_project_with_scope(
        project_number=body.confirmed_number,
        name=name,
        client=body.metadata.cliente,
        empreendimento=body.metadata.empreendimento,
        cidade=body.metadata.cidade,
        estado=estado,
        orcamento_sheets_id=body.spreadsheet_id,
        disciplinas=parsed.disciplinas,
        created_by=user.user_id,
        city_ibge_code=city_ibge_code,
        master_rows=master_rows,
    )

    ldp_state = await get_project_ldp_state(UUID(str(result["project_id"])))
    drive_folder_id = ldp_state["drive_folder_path"] if ldp_state else None
    ldp_sheets_id = ldp_state["ldp_sheets_id"] if ldp_state else None

    return CreateProjectResponse(
        project_id=str(result["project_id"]),
        project_number=int(result["project_number"]),
        project_name=name,
        drive_folder_pending=drive_folder_id is None,
        drive_folder_id=drive_folder_id,
        ldp_sheets_id=ldp_sheets_id,
        scope_inserted=int(result.get("scope_inserted", 0)),
        scope_skipped=list(result.get("scope_skipped", [])),
        already_existed=not bool(result.get("created", True)),
        definitions_count=int(result.get("definitions_count", 0)),
        definitions_by_discipline=dict(result.get("definitions_by_discipline", {})),
    )


@router.post(
    "/projects/{project_id}/create-drive-folder",
    response_model=CreateDriveFolderResponse,
)
async def create_drive_folder_endpoint(
    project_id: UUID,
    user: UserContext = Depends(get_current_user),
) -> CreateDriveFolderResponse:
    if not check_permission(user, "create_project"):
        raise HTTPException(
            status_code=403,
            detail="Sem permissão para criar pasta no Drive.",
        )

    state = await get_project_drive_state(project_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")

    is_admin = user.role == "admin"
    if not is_admin and str(state["created_by"]) != str(user.user_id):
        raise HTTPException(
            status_code=403,
            detail="Sem permissão para criar pasta no Drive deste projeto.",
        )

    if state["drive_folder_path"]:
        raise HTTPException(
            status_code=409,
            detail="Pasta deste projeto já foi criada anteriormente.",
        )

    try:
        result = await copy_project_template(state["name"])
    except DriveFolderAlreadyExistsError as exc:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Pasta '{exc.folder_name}' já existe no Drive. "
                "Verifique se não foi criada manualmente. "
                "Em caso de dúvida, contate Rodrigo."
            ),
        ) from exc
    except DriveTemplateNotAccessibleError as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "Pasta template do Drive não encontrada ou sem acesso. "
                "Contate Rodrigo para liberar a service account."
            ),
        ) from exc
    except PermissionError as exc:
        raise HTTPException(
            status_code=403,
            detail=(
                "Sem permissão para criar pasta no Drive. Service account precisa "
                "ser Editor em 107_PROJETOS. Contate o admin."
            ),
        ) from exc
    except Exception as exc:
        _log.exception("Drive folder copy failed for project %s", project_id)
        raise HTTPException(
            status_code=502,
            detail=(
                "Erro de comunicação com Google Drive. Tente novamente em alguns segundos."
            ),
        ) from exc

    updated = await update_drive_folder_path(project_id, result.folder_id)
    if not updated:
        _log.error(
            "Drive folder %s created but project %s vanished before UPDATE",
            result.folder_id,
            project_id,
        )
        raise HTTPException(
            status_code=500,
            detail="Pasta criada no Drive mas projeto sumiu antes de salvar — contate o admin.",
        )

    return CreateDriveFolderResponse(
        folder_id=result.folder_id,
        folder_url=result.folder_url,
        folder_name=result.folder_name,
    )


@router.post(
    "/projects/{project_id}/create-ldp-sheet",
    response_model=CreateLdpSheetResponse,
)
async def create_ldp_sheet_endpoint(
    project_id: UUID,
    user: UserContext = Depends(get_current_user),
) -> CreateLdpSheetResponse:
    if not check_permission(user, "create_project"):
        raise HTTPException(
            status_code=403,
            detail="Sem permissão para criar planilha LDP.",
        )

    state = await get_project_ldp_state(project_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")

    is_admin = user.role == "admin"
    if not is_admin and str(state["created_by"]) != str(user.user_id):
        raise HTTPException(
            status_code=403,
            detail="Sem permissão para criar planilha LDP deste projeto.",
        )

    if not state["drive_folder_path"]:
        raise HTTPException(
            status_code=409,
            detail="Crie a pasta no Drive primeiro.",
        )

    if state["ldp_sheets_id"]:
        raise HTTPException(
            status_code=409,
            detail="Planilha LDP já existe para este projeto.",
        )

    try:
        result = await generate_ldp_sheet(project_id)
    except LdpSheetAlreadyExistsError as exc:
        # Race rara: outro request criou entre o pre-check e o generate.
        raise HTTPException(
            status_code=409, detail="Planilha LDP já existe para este projeto."
        ) from exc
    except DriveFolderStructureError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except MasterNotAccessibleError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except DefinicoesParentNotEditableError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        # Defensivo: definitions vazias.
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except LdpSheetGenerationError as exc:
        _log.exception("LDP sheet generation failed for project %s", project_id)
        raise HTTPException(
            status_code=502,
            detail=(
                "Erro de comunicação com Google Sheets. Tente novamente em alguns segundos."
            ),
        ) from exc
    except Exception as exc:
        _log.exception("LDP sheet unexpected failure for project %s", project_id)
        raise HTTPException(
            status_code=502,
            detail=(
                "Erro de comunicação com Google Sheets. Tente novamente em alguns segundos."
            ),
        ) from exc

    return CreateLdpSheetResponse(
        sheets_id=result.sheets_id,
        sheets_url=result.sheets_url,
        sheets_name=result.sheets_name,
        rows_written=result.rows_written,
    )
