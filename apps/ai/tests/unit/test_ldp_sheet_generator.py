"""Unit tests pros helpers puros do sheet_generator (sem tocar Drive/Sheets reais)."""

# ruff: noqa: N803, E501
# Justificativa: o fake imita signatures camelCase da Drive API.

from typing import Any
from unittest.mock import MagicMock

import pytest

from oraculo_ai.ldp import sheet_generator
from oraculo_ai.ldp.sheet_generator import (
    DriveFolderStructureError,
    _column_letter,
    find_label_cell,
    map_definitions_to_rows,
    projeto_tab_updates,
    resolve_definicoes_folder,
)

_FOLDER_MIME = "application/vnd.google-apps.folder"


class _FakeDrive:
    """Fake do Drive client — só implementa files().list() pra exercer o resolve."""

    def __init__(self, tree: dict[str, list[dict[str, Any]]]) -> None:
        self.tree = tree

    def files(self) -> "_FakeDrive":
        return self

    def list(self, *, q: str, fields: str, supportsAllDrives: bool,
             includeItemsFromAllDrives: bool, pageSize: int,
             pageToken: str | None = None):  # noqa: N805
        outer = self
        parent_id = q.split("'", 2)[1]

        class _Exec:
            def execute(_self):  # noqa: N805
                return {"files": outer.tree.get(parent_id, [])}

        return _Exec()


def test_resolve_definicoes_folder_walks_two_levels():
    drive = _FakeDrive(
        {
            "ROOT": [
                {"id": "T", "name": "02 TRABALHO", "mimeType": _FOLDER_MIME},
                {"id": "X", "name": "01 ADMINISTRATIVO", "mimeType": _FOLDER_MIME},
            ],
            "T": [
                {"id": "D", "name": "DEFINIÇÕES", "mimeType": _FOLDER_MIME},
            ],
        }
    )
    assert resolve_definicoes_folder(drive, "ROOT") == "D"


def test_resolve_is_case_and_accent_insensitive():
    drive = _FakeDrive(
        {
            "ROOT": [
                {"id": "T", "name": "02 trabalho", "mimeType": _FOLDER_MIME},
            ],
            "T": [
                {"id": "D", "name": "Definicoes", "mimeType": _FOLDER_MIME},
            ],
        }
    )
    assert resolve_definicoes_folder(drive, "ROOT") == "D"


def test_resolve_raises_when_trabalho_missing():
    drive = _FakeDrive({"ROOT": []})
    with pytest.raises(DriveFolderStructureError, match="02 TRABALHO/DEFINIÇÕES"):
        resolve_definicoes_folder(drive, "ROOT")


def test_resolve_raises_when_definicoes_missing():
    drive = _FakeDrive(
        {
            "ROOT": [{"id": "T", "name": "02 TRABALHO", "mimeType": _FOLDER_MIME}],
            "T": [],
        }
    )
    with pytest.raises(DriveFolderStructureError):
        resolve_definicoes_folder(drive, "ROOT")


def test_resolve_ignores_non_folders_with_same_name():
    drive = _FakeDrive(
        {
            "ROOT": [
                {"id": "FILE", "name": "02 TRABALHO", "mimeType": "text/plain"},
                {"id": "T", "name": "02 TRABALHO", "mimeType": _FOLDER_MIME},
            ],
            "T": [{"id": "D", "name": "DEFINIÇÕES", "mimeType": _FOLDER_MIME}],
        }
    )
    assert resolve_definicoes_folder(drive, "ROOT") == "D"


def test_map_definitions_to_rows_preserves_column_order_and_count():
    defs = [
        {
            "disciplina": "Hidráulica",
            "tipo": "Apartamento",
            "fase": "Fase 01",
            "item_code": "HID01",
            "pergunta": "Material da tubulação?",
            "status": "Em análise",
            "custo": None,
            "opcao_escolhida": None,
            "observacoes": None,
            "validado": False,
            "informacao_auxiliar": "Aux",
            "apoio_1": None,
            "apoio_2": None,
            "source_row": 4,
        },
    ]
    rows = map_definitions_to_rows(defs)
    assert len(rows) == 1
    assert len(rows[0]) == 13
    assert rows[0][0] == "Hidráulica"
    assert rows[0][3] == "HID01"
    assert rows[0][9] is False  # boolean preservado


def test_map_definitions_replaces_none_with_empty_string():
    rows = map_definitions_to_rows(
        [
            {
                "disciplina": None,
                "tipo": None,
                "fase": None,
                "item_code": "X",
                "pergunta": "?",
                "status": None,
                "custo": None,
                "opcao_escolhida": None,
                "observacoes": None,
                "validado": None,
                "informacao_auxiliar": None,
                "apoio_1": None,
                "apoio_2": None,
                "source_row": 1,
            }
        ]
    )
    assert rows[0][0] == ""
    assert rows[0][9] == ""  # validado=None vira string vazia (não False)


def test_find_label_cell_normalizes_accents_and_case():
    grid = [
        ["", "DADOS DO PROJETO"],
        ["Nome", "Nome do edifício"],
        ["", ""],
    ]
    assert find_label_cell(grid, "edificio") == (1, 1)
    assert find_label_cell(grid, "edifício") == (1, 1)
    assert find_label_cell(grid, "EDIFÍCIO") == (1, 1)


def test_find_label_cell_returns_none_when_absent():
    assert find_label_cell([["foo", "bar"]], "baz") is None


def test_column_letter_handles_first_27():
    assert _column_letter(0) == "A"
    assert _column_letter(1) == "B"
    assert _column_letter(25) == "Z"
    assert _column_letter(26) == "AA"


def test_projeto_tab_updates_writes_next_to_label():
    grid = [
        ["DADOS"],
        ["Nome do edifício", ""],
        ["Cidade/UF", "", ""],
    ]
    updates = projeto_tab_updates(
        grid, empreendimento="Stylo", cidade="São José", estado="SC"
    )
    ranges = {u["range"]: u["values"] for u in updates}
    assert ranges["'Projeto'!B2"] == [["Stylo"]]
    assert ranges["'Projeto'!B3"] == [["São José / SC"]]


def test_projeto_tab_updates_skips_when_label_missing():
    grid = [["sem labels"]]
    updates = projeto_tab_updates(
        grid, empreendimento="Stylo", cidade="X", estado="SC"
    )
    assert updates == []


def test_projeto_tab_updates_skips_blank_values():
    grid = [["Nome do edifício", ""], ["Cidade/UF", ""]]
    updates = projeto_tab_updates(grid, empreendimento=None, cidade=None, estado=None)
    assert updates == []


def test_drive_copy_master_to_definicoes_handles_403_on_master(monkeypatch):
    """Erro 403 na cópia da master deve virar MasterNotAccessibleError."""
    from googleapiclient.errors import HttpError

    class _FailingDrive:
        def files(self):
            return self

        def copy(self, **kwargs):  # noqa: ARG002
            class _Exec:
                def execute(_self):  # noqa: N805
                    resp = MagicMock()
                    resp.status = 403
                    raise HttpError(resp, b"forbidden")
            return _Exec()

    with pytest.raises(sheet_generator.MasterNotAccessibleError):
        sheet_generator._drive_copy_master_to_definicoes(
            _FailingDrive(),
            master_id="MASTER",
            target_folder_id="DEST",
            new_name="LDP",
        )
