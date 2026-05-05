"""Validador do ParsedOrcamento contra scope_template + regras de domínio.

ERRORS (bloqueiam se user não confirmar via interrupt):
- DISCIPLINA_FORA_TEMPLATE: nome de disciplina não existe em scope_template
- LEGAL_INVALIDO: valor diferente de 'executivo' ou 'legal'

WARNINGS (informa, não bloqueia):
- DISCIPLINA_FALTANDO: disciplina do template não está na planilha
"""

from collections.abc import Iterable

from oraculo_ai.scope.types import (
    VALID_LEGAL,
    ParsedOrcamento,
    ValidationIssue,
    ValidationResult,
)


def validate_against_template(
    parsed: ParsedOrcamento,
    template_disciplines: Iterable[str],
) -> ValidationResult:
    template_set = {name.strip() for name in template_disciplines}
    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []

    seen_disciplines: set[str] = set()
    for row in parsed.disciplinas:
        seen_disciplines.add(row.disciplina.strip())

        if row.disciplina.strip() not in template_set:
            errors.append(
                ValidationIssue(
                    code="DISCIPLINA_FORA_TEMPLATE",
                    severity="error",
                    message=(
                        f"Disciplina {row.disciplina!r} não está no template oficial Thórus"
                    ),
                    field="disciplina",
                    value=row.disciplina,
                    row=row.source_row,
                )
            )

        if row.legal not in VALID_LEGAL:
            errors.append(
                ValidationIssue(
                    code="LEGAL_INVALIDO",
                    severity="error",
                    message=(
                        f"Coluna 'legal' tem valor {row.legal!r} (esperado: executivo ou legal)"
                    ),
                    field="legal",
                    value=row.legal,
                    row=row.source_row,
                )
            )

    missing = sorted(template_set - seen_disciplines)
    for nome in missing:
        warnings.append(
            ValidationIssue(
                code="DISCIPLINA_FALTANDO",
                severity="warning",
                message=f"Disciplina {nome!r} do template não está na planilha",
                field="disciplina",
                value=nome,
            )
        )

    return ValidationResult(
        ok=not errors,
        errors=errors,
        warnings=warnings,
    )
