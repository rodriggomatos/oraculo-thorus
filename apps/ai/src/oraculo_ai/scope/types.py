"""Schemas Pydantic do orçamento parseado."""

from typing import Literal

from pydantic import BaseModel, Field


VALID_LEGAL: frozenset[str] = frozenset({"executivo", "legal"})


class DisciplinaRow(BaseModel):
    disciplina: str
    incluir: bool = False
    legal: str
    source_row: int


class ParsedOrcamento(BaseModel):
    spreadsheet_id: str
    disciplinas: list[DisciplinaRow] = Field(default_factory=list)


IssueSeverity = Literal["error", "warning"]


class ValidationIssue(BaseModel):
    code: str
    severity: IssueSeverity
    message: str
    field: str | None = None
    value: str | None = None
    row: int | None = None


class ValidationResult(BaseModel):
    ok: bool
    errors: list[ValidationIssue] = Field(default_factory=list)
    warnings: list[ValidationIssue] = Field(default_factory=list)
