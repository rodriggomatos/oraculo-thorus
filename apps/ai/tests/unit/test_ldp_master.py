"""Unit tests pro parser da Master R04 + filtro por categorias ativas."""

import json
from pathlib import Path

import pytest

from oraculo_ai.ldp.master_reader import parse_master_rows
from oraculo_ai.ldp.seed import filter_master_for_active


_FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "master_r04.json"


@pytest.fixture(scope="module")
def fixture_values() -> list[list]:
    with _FIXTURE_PATH.open(encoding="utf-8") as fh:
        data = json.load(fh)
    return list(data["values"])


def test_parse_master_skips_blank_rows_and_items_without_pergunta(fixture_values):
    rows = parse_master_rows(fixture_values)
    item_codes = {r.item_code for r in rows}
    assert "INCOMPLETO" not in item_codes  # pergunta vazia
    assert "" not in item_codes
    assert "GER01" in item_codes
    assert "HID01" in item_codes


def test_parse_master_handles_header_with_whitespace(fixture_values):
    rows = parse_master_rows(fixture_values)
    ger01 = next(r for r in rows if r.item_code == "GER01")
    assert ger01.disciplina == "Geral"
    assert ger01.fase == "Fase 00"
    assert ger01.pergunta == "Quem é o cliente?"


def test_parse_master_preserves_source_row_one_indexed(fixture_values):
    rows = parse_master_rows(fixture_values)
    ger01 = next(r for r in rows if r.item_code == "GER01")
    # GER01 is the 2nd row (header is row 1) → source_row=2
    assert ger01.source_row == 2
    hid01 = next(r for r in rows if r.item_code == "HID01")
    assert hid01.source_row == 4


def test_filter_returns_only_geral_when_no_disciplines_active(fixture_values):
    parsed = parse_master_rows(fixture_values)
    eligible = filter_master_for_active(parsed, ["Geral"])
    item_codes = sorted(r.item_code for r in eligible)
    assert item_codes == ["GER01", "GER02"]


def test_filter_combines_geral_and_active_disciplines(fixture_values):
    parsed = parse_master_rows(fixture_values)
    eligible = filter_master_for_active(parsed, ["Geral", "Hidráulica"])
    item_codes = sorted(r.item_code for r in eligible)
    assert item_codes == ["GER01", "GER02", "HID01", "HID02"]


def test_filter_drops_unknown_disciplines(fixture_values):
    parsed = parse_master_rows(fixture_values)
    eligible = filter_master_for_active(parsed, ["Geral"])
    assert all(r.disciplina != "Disciplina inventada" for r in eligible)


def test_filter_is_case_insensitive(fixture_values):
    parsed = parse_master_rows(fixture_values)
    eligible = filter_master_for_active(parsed, ["geral", "HIDRÁULICA"])
    assert len(eligible) == 4


def test_parse_master_rejects_invalid_header():
    with pytest.raises(ValueError, match="header inválido"):
        parse_master_rows([["Disciplina", "Item", "Definições"]])


def test_parse_master_handles_empty_input():
    assert parse_master_rows([]) == []
