"""Guarda contra reintrodução do nome de coluna legado `google_sheet_id`.

A coluna foi renomeada pra `ldp_sheets_id` na migration 20260502130000.
Tudo em `src/` (código produtivo) e em `scripts/` deve usar o nome novo.
Migrations ficam de fora — elas mantêm histórico do schema.
"""

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[4]
_AI_SRC = _REPO_ROOT / "apps" / "ai" / "src"
_AI_SCRIPTS = _REPO_ROOT / "apps" / "ai" / "scripts"
_API_SRC = _REPO_ROOT / "apps" / "api" / "src"


def _python_files(*roots: Path) -> list[Path]:
    out: list[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        out.extend(p for p in root.rglob("*.py") if "__pycache__" not in p.parts)
    return out


@pytest.mark.parametrize("path", _python_files(_AI_SRC, _AI_SCRIPTS, _API_SRC))
def test_no_google_sheet_id_in_production_code(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    assert "google_sheet_id" not in text, (
        f"{path}: ainda referencia coluna legada `google_sheet_id`. "
        "Renomeie pra `ldp_sheets_id` (ver migration 20260502130000)."
    )
