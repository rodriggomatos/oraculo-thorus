# ruff: noqa: N803, N805, E501
# Justificativa: o fake imita signatures camelCase da Drive API e usa `_self`
# em classes aninhadas pra não sombrear o `self` do método externo.
"""Unit tests pro folder_creator com Drive API totalmente mockado."""

from typing import Any
from unittest.mock import MagicMock

import pytest

from oraculo_ai.drive import folder_creator
from oraculo_ai.drive.folder_creator import (
    DriveFolderAlreadyExistsError,
    DriveTemplateNotAccessibleError,
)

_FOLDER_MIME = "application/vnd.google-apps.folder"


class _FakeDrive:
    """Cliente fake do Drive: árvore in-memory com escopos mínimos pra exercer o copy.

    Tracking via list de operações (`history`) pra asserts de cópia recursiva.
    """

    def __init__(self, *, template_tree: dict[str, list[dict]] | None = None,
                 parent_existing_names: tuple[str, ...] = (),
                 template_accessible: bool = True) -> None:
        self.template_tree = template_tree or {}
        self.parent_existing_names = set(parent_existing_names)
        self.template_accessible = template_accessible
        self.history: list[tuple[str, dict[str, Any]]] = []
        self._next_id = 100

    def _new_id(self) -> str:
        self._next_id += 1
        return f"new-{self._next_id}"

    def files(self) -> "_FakeDrive":
        return self

    def get(self, *, fileId: str, fields: str, supportsAllDrives: bool):  # noqa: N803
        op = self
        if fileId == "TEMPLATE" and not op.template_accessible:
            from googleapiclient.errors import HttpError
            resp = MagicMock()
            resp.status = 403
            raise HttpError(resp, b"forbidden")

        class _Exec:
            def execute(_self):
                return {"id": fileId, "name": "template"}
        return _Exec()

    def list(self, *, q: str, fields: str, supportsAllDrives: bool,
             includeItemsFromAllDrives: bool, pageSize: int,
             pageToken: str | None = None):  # noqa: N803
        outer = self

        class _Exec:
            def execute(_self):
                if "name = " in q:
                    name = q.split("name = '", 1)[1].split("'", 1)[0]
                    return {
                        "files": [{"id": "DUP", "name": name}]
                        if name in outer.parent_existing_names
                        else []
                    }
                parent_id = q.split("'", 2)[1]
                return {"files": outer.template_tree.get(parent_id, [])}

        return _Exec()

    def create(self, *, body: dict[str, Any], fields: str, supportsAllDrives: bool):  # noqa: N803
        outer = self
        new_id = outer._new_id()
        outer.history.append(("create", {"id": new_id, **body}))

        class _Exec:
            def execute(_self):
                return {"id": new_id, "name": body["name"]}

        return _Exec()

    def copy(self, *, fileId: str, body: dict[str, Any], fields: str,
             supportsAllDrives: bool):  # noqa: N803
        outer = self
        new_id = outer._new_id()
        outer.history.append(("copy", {"source": fileId, "id": new_id, **body}))

        class _Exec:
            def execute(_self):
                return {"id": new_id, "name": body["name"]}

        return _Exec()


@pytest.fixture
def patch_settings(monkeypatch):
    fake_settings = MagicMock()
    fake_settings.thorus_drive_template_folder_id = "TEMPLATE"
    fake_settings.thorus_drive_root_id = "PARENT"
    monkeypatch.setattr(folder_creator, "get_settings", lambda: fake_settings)
    return fake_settings


def _patch_service(monkeypatch, drive: _FakeDrive) -> None:
    monkeypatch.setattr(folder_creator, "build_drive_service_rw", lambda: drive)


def test_pre_check_blocks_when_name_already_exists(patch_settings, monkeypatch):
    drive = _FakeDrive(parent_existing_names=("26032 - Cliente - Empreendimento",))
    _patch_service(monkeypatch, drive)
    with pytest.raises(DriveFolderAlreadyExistsError) as excinfo:
        folder_creator._copy_template_blocking("26032 - Cliente - Empreendimento")
    assert excinfo.value.folder_name == "26032 - Cliente - Empreendimento"
    # Não deve ter criado nada
    assert all(op != "create" for op, _ in drive.history)


def test_template_inaccessible_raises_specific_error(patch_settings, monkeypatch):
    drive = _FakeDrive(template_accessible=False)
    _patch_service(monkeypatch, drive)
    with pytest.raises(DriveTemplateNotAccessibleError):
        folder_creator._copy_template_blocking("26032 - Cliente - Emp")


def test_recursive_copy_replicates_subfolders_and_files(patch_settings, monkeypatch):
    template_tree = {
        "TEMPLATE": [
            {"id": "F1", "name": "01 ADMINISTRATIVO", "mimeType": _FOLDER_MIME},
            {"id": "F2", "name": "02 TRABALHO", "mimeType": _FOLDER_MIME},
            {"id": "FILE1", "name": "README.txt", "mimeType": "text/plain"},
        ],
        "F1": [
            {"id": "FILE2", "name": "checklist.gdoc", "mimeType": "application/vnd.google-apps.document"},
        ],
        "F2": [
            {"id": "F3", "name": "DEFINIÇÕES", "mimeType": _FOLDER_MIME},
        ],
        "F3": [],
    }
    drive = _FakeDrive(template_tree=template_tree)
    _patch_service(monkeypatch, drive)

    result = folder_creator._copy_template_blocking("26032 - Cliente - Emp")
    assert result.folder_name == "26032 - Cliente - Emp"
    assert result.folder_url.endswith(result.folder_id)

    creates = [payload for op, payload in drive.history if op == "create"]
    copies = [payload for op, payload in drive.history if op == "copy"]

    # Pasta-raiz + 3 subpastas (F1, F2, F3 = DEFINIÇÕES) = 4 creates
    assert len(creates) == 4
    folder_names = {c["name"] for c in creates}
    assert folder_names == {
        "26032 - Cliente - Emp",
        "01 ADMINISTRATIVO",
        "02 TRABALHO",
        "DEFINIÇÕES",
    }

    # 2 arquivos copiados
    assert {c["name"] for c in copies} == {"README.txt", "checklist.gdoc"}


def test_folder_url_uses_drive_folders_path():
    assert (
        folder_creator.folder_url_for("abc123")
        == "https://drive.google.com/drive/folders/abc123"
    )
