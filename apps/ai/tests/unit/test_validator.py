"""Unit tests pra validate_against_template (errors + warnings)."""

from oraculo_ai.scope.types import DisciplinaRow, ParsedOrcamento
from oraculo_ai.scope.validator import validate_against_template


_TEMPLATE: list[str] = [
    "Hidrossanitário + Drenagem",
    "SPDA",
    "Climatização",
]


def _make_row(
    nome: str,
    *,
    legal: str = "executivo",
    incluir: bool = True,
    source_row: int = 3,
) -> DisciplinaRow:
    return DisciplinaRow(
        disciplina=nome,
        incluir=incluir,
        legal=legal,
        source_row=source_row,
    )


def test_clean_orcamento_passes() -> None:
    parsed = ParsedOrcamento(
        spreadsheet_id="abc",
        disciplinas=[
            _make_row("Hidrossanitário + Drenagem"),
            _make_row("SPDA"),
            _make_row("Climatização"),
        ],
    )
    result = validate_against_template(parsed, _TEMPLATE)
    assert result.ok
    assert result.errors == []


def test_disciplina_fora_template_vira_error() -> None:
    parsed = ParsedOrcamento(
        spreadsheet_id="abc",
        disciplinas=[
            _make_row("Hidrossanitário + Drenagem"),
            _make_row("Geotermia"),
        ],
    )
    result = validate_against_template(parsed, _TEMPLATE)
    assert not result.ok
    codes = [e.code for e in result.errors]
    assert "DISCIPLINA_FORA_TEMPLATE" in codes


def test_legal_invalido_vira_error() -> None:
    parsed = ParsedOrcamento(
        spreadsheet_id="abc",
        disciplinas=[_make_row("SPDA", legal="misto")],
    )
    result = validate_against_template(parsed, _TEMPLATE)
    codes = [e.code for e in result.errors]
    assert "LEGAL_INVALIDO" in codes


def test_disciplina_faltando_vira_warning() -> None:
    parsed = ParsedOrcamento(
        spreadsheet_id="abc",
        disciplinas=[_make_row("SPDA")],
    )
    result = validate_against_template(parsed, _TEMPLATE)
    codes = [w.code for w in result.warnings]
    assert "DISCIPLINA_FALTANDO" in codes
