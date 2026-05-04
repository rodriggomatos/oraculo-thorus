"""Schemas Pydantic do orçamento parseado."""

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


VALID_ESTADOS: frozenset[str] = frozenset({"SC", "PR", "MG", "SP", "RS", "RO", "ES"})
VALID_LEGAL: frozenset[str] = frozenset({"executivo", "legal"})


class DisciplinaRow(BaseModel):
    disciplina: str
    incluir: bool = False
    unificar: bool | None = None
    essencial: bool = False
    pontos: Decimal = Decimal("0")
    legal: str
    peso_disciplina: Decimal | None = None
    ponto_fixo: Decimal | None = None
    pontos_calculados: Decimal = Decimal("0")
    source_row: int


class ParsedOrcamento(BaseModel):
    spreadsheet_id: str
    estado: str | None = None
    custo_fator: Decimal | None = None
    fluxo: str | None = None
    area_m2: Decimal | None = None
    total_contratado: Decimal | None = None
    margem: Decimal | None = None
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
