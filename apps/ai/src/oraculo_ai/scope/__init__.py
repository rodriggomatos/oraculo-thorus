"""Parser + validator do orçamento Thórus → ParsedOrcamento + ValidationResult."""

from oraculo_ai.scope.parser import parse_orcamento_from_sheets
from oraculo_ai.scope.types import (
    DisciplinaRow,
    ParsedOrcamento,
    ValidationIssue,
    ValidationResult,
)
from oraculo_ai.scope.validator import validate_against_template


__all__ = [
    "DisciplinaRow",
    "ParsedOrcamento",
    "ValidationIssue",
    "ValidationResult",
    "parse_orcamento_from_sheets",
    "validate_against_template",
]
