"""LDP master reader + filter helpers usados pra semear `definitions` ao criar projeto.

`sheet_generator` é exposto via lazy attribute access (`__getattr__`) pra evitar
ciclo de import com `oraculo_ai.projects.repository`, que precisa carregar
`MasterRow` do submódulo `master_reader` durante a própria inicialização.
"""

from typing import TYPE_CHECKING, Any

from oraculo_ai.ldp.master_reader import (
    MasterRow,
    parse_master_rows,
    read_master_r04,
)
from oraculo_ai.ldp.seed import filter_master_for_active

if TYPE_CHECKING:
    from oraculo_ai.ldp.sheet_generator import (
        CreateLdpSheetResult,
        DefinicoesParentNotEditableError,
        DriveFolderStructureError,
        LdpSheetAlreadyExistsError,
        LdpSheetGenerationError,
        MasterNotAccessibleError,
        generate_ldp_sheet,
        sheet_url_for,
    )

_LAZY_FROM_SHEET_GENERATOR = {
    "CreateLdpSheetResult",
    "DefinicoesParentNotEditableError",
    "DriveFolderStructureError",
    "LdpSheetAlreadyExistsError",
    "LdpSheetGenerationError",
    "MasterNotAccessibleError",
    "generate_ldp_sheet",
    "sheet_url_for",
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_FROM_SHEET_GENERATOR:
        from oraculo_ai.ldp import sheet_generator

        return getattr(sheet_generator, name)
    raise AttributeError(f"module 'oraculo_ai.ldp' has no attribute {name!r}")


__all__ = [
    "CreateLdpSheetResult",
    "DefinicoesParentNotEditableError",
    "DriveFolderStructureError",
    "LdpSheetAlreadyExistsError",
    "LdpSheetGenerationError",
    "MasterNotAccessibleError",
    "MasterRow",
    "filter_master_for_active",
    "generate_ldp_sheet",
    "parse_master_rows",
    "read_master_r04",
    "sheet_url_for",
]
