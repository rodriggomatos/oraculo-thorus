"""Unit tests pra extração de metadata do nome do arquivo."""

from datetime import date

from mcp_drive.parsing import parse_filename


def test_extracts_discipline_hid() -> None:
    md = parse_filename("26009-VOF-HID-R02_TEC OK.pdf")
    assert md.discipline == "HID"


def test_extracts_revision_r02() -> None:
    md = parse_filename("26009-VOF-HID-R02_TEC OK.pdf")
    assert md.revision == "R02"


def test_extracts_revision_rv03() -> None:
    md = parse_filename("Documento RV03 final.docx")
    assert md.revision == "RV03"


def test_extracts_status_tec_ok() -> None:
    md = parse_filename("26009-VOF-HID-R02_TEC OK.pdf")
    assert md.status == "TEC OK"


def test_extracts_status_proj_ok() -> None:
    md = parse_filename("PROJETO-FINAL_PROJ OK.pdf")
    assert md.status == "PROJ OK"


def test_extracts_status_pro_ok_alias() -> None:
    md = parse_filename("VOF-CLI_PRO OK.pdf")
    assert md.status == "PROJ OK"


def test_extracts_date_full() -> None:
    md = parse_filename("Ata 25-04-2026 Kickoff.pdf")
    assert md.file_date == date(2026, 4, 25)


def test_extracts_date_short() -> None:
    md = parse_filename("Documento 15-03-26.pdf")
    assert md.file_date == date(2026, 3, 15)


def test_no_metadata_extracted() -> None:
    md = parse_filename("planilha qualquer.xlsx")
    assert md.discipline is None
    assert md.revision is None
    assert md.status is None
    assert md.file_date is None


def test_discipline_does_not_match_in_word() -> None:
    md = parse_filename("CHIDO.pdf")
    assert md.discipline is None
