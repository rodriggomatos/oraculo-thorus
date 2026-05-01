"""Pydantic schemas pros retornos de tool."""

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, computed_field

from mcp_drive.parsing import FileMetadata


class FileResult(BaseModel):
    id: str
    name: str
    path: list[str] = Field(
        default_factory=list,
        description="Caminho relativo à pasta de projeto (segmentos)",
    )
    web_view_link: str | None = None
    modified_time: datetime | None = None
    mime_type: str
    size: int | None = None
    metadata: FileMetadata = Field(default_factory=FileMetadata)


class ProjectFolder(BaseModel):
    project_number: int
    folder_id: str
    folder_name: str
    web_view_link: str | None = None


class ToolResult(BaseModel):
    found: bool
    project_number: int
    project_folder_name: str | None = None
    project_folder_link: str | None = None
    category: str | None = None
    discipline: str | None = None
    count: int = 0
    items: list[FileResult] = Field(default_factory=list)
    note: str | None = None


class LDPStatus(str, Enum):
    FOUND = "found"
    NOT_FOUND = "not_found"
    UNCERTAIN = "uncertain"


LDPResolvedVia = Literal["gsheet", "xlsx", "link_txt"]


class LDPResult(BaseModel):
    status: LDPStatus
    project_number: int
    project_folder_name: str | None = None
    project_folder_link: str | None = None
    category: Literal["lista_definicoes"] = "lista_definicoes"

    sheet_id: str | None = None
    sheet_url: str | None = None
    resolved_via: LDPResolvedVia | None = None

    found_files: list[FileResult] = Field(
        default_factory=list,
        description="Todos os arquivos encontrados na pasta DEFINIÇÕES (vazio se NOT_FOUND)",
    )
    uncertainty_reason: str | None = None

    items: list[FileResult] = Field(
        default_factory=list,
        description="Match(es) primário(s) — vazio se NOT_FOUND, 1 item se FOUND",
    )
    note: str | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def found(self) -> bool:
        return self.status == LDPStatus.FOUND

    @computed_field  # type: ignore[prop-decorator]
    @property
    def count(self) -> int:
        return len(self.items)
