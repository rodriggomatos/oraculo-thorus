"""Unit tests pra classify_ldp_files (tri-state FOUND/NOT_FOUND/UNCERTAIN)."""

from mcp_drive.backend import FileNode
from mcp_drive.ldp_classifier import classify_ldp_files
from mcp_drive.schemas import LDPStatus


_GSHEET = "application/vnd.google-apps.spreadsheet"
_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_TXT = "text/plain"
_PDF = "application/pdf"


def _node(name: str, mime: str, *, node_id: str | None = None) -> FileNode:
    return FileNode(id=node_id or f"id-{name}", name=name, mime_type=mime)


def test_found_gsheet_with_ldp_marker() -> None:
    files = [_node("26003 - Lista de definições - R03", _GSHEET)]
    result = classify_ldp_files(files)
    assert result.status == LDPStatus.FOUND
    assert result.primary_kind == "gsheet"
    assert result.primary_match is files[0]


def test_found_xlsx_with_ldp_marker() -> None:
    files = [_node("Lista de definições do projeto.xlsx", _XLSX)]
    result = classify_ldp_files(files)
    assert result.status == LDPStatus.FOUND
    assert result.primary_kind == "xlsx"


def test_found_txt_link_da_lista_de_definicoes() -> None:
    files = [_node("Link da lista de definições.txt", _TXT)]
    result = classify_ldp_files(files)
    assert result.status == LDPStatus.FOUND
    assert result.primary_kind == "link_txt"


def test_uncertain_gsheet_without_marker_26007() -> None:
    files = [
        _node("26007 - Rove - Campeche Island By Rove", _GSHEET),
        _node("Consulte o Asana do projeto.txt", _TXT),
        _node("GD47-COO-EP-001-DOC-R00.pdf", _PDF),
    ]
    result = classify_ldp_files(files)
    assert result.status == LDPStatus.UNCERTAIN
    assert result.primary_match is None
    assert any("Asana" in r for r in result.uncertainty_reasons)
    assert any("Lista de definições" in r for r in result.uncertainty_reasons)


def test_uncertain_only_consulte_asana() -> None:
    files = [_node("Consulte o Asana do projeto.txt", _TXT)]
    result = classify_ldp_files(files)
    assert result.status == LDPStatus.UNCERTAIN
    assert any("Asana" in r for r in result.uncertainty_reasons)


def test_uncertain_positive_with_external_pointer_alongside() -> None:
    files = [
        _node("Lista de definições.gsheet", _GSHEET),
        _node("Consulte o Asana do projeto.txt", _TXT),
    ]
    result = classify_ldp_files(files)
    assert result.status == LDPStatus.UNCERTAIN
    assert result.primary_match is files[0]
    assert result.primary_kind == "gsheet"
    assert any("Asana" in r for r in result.uncertainty_reasons)


def test_not_found_empty_folder() -> None:
    result = classify_ldp_files([])
    assert result.status == LDPStatus.NOT_FOUND
    assert result.primary_match is None
    assert result.uncertainty_reasons == []


def test_uncertain_random_files_no_signals() -> None:
    files = [
        _node("documento.pdf", _PDF),
        _node("foto.jpg", "image/jpeg"),
    ]
    result = classify_ldp_files(files)
    assert result.status == LDPStatus.UNCERTAIN


def test_accent_insensitive_marker_detection() -> None:
    files = [_node("Lista de definicao.xlsx", _XLSX)]
    result = classify_ldp_files(files)
    assert result.status == LDPStatus.FOUND
    assert result.primary_kind == "xlsx"


def test_plural_singular_both_match() -> None:
    files_singular = [_node("Lista de definição.xlsx", _XLSX)]
    files_plural = [_node("Lista de definições.xlsx", _XLSX)]
    assert classify_ldp_files(files_singular).status == LDPStatus.FOUND
    assert classify_ldp_files(files_plural).status == LDPStatus.FOUND


def test_priority_gsheet_over_link_txt() -> None:
    files = [
        _node("Link da lista de definições.txt", _TXT),
        _node("Lista de definições - R03.gsheet", _GSHEET),
    ]
    result = classify_ldp_files(files)
    assert result.status == LDPStatus.FOUND
    assert result.primary_kind == "gsheet"


def test_consulte_a_outra_planilha_also_external() -> None:
    files = [_node("Consulte a planilha do cliente.txt", _TXT)]
    result = classify_ldp_files(files)
    assert result.status == LDPStatus.UNCERTAIN
