"""Unit tests pro parser da Master R04 + filtro por categorias ativas."""

import json
from pathlib import Path

import pytest

from oraculo_ai.ldp.master_reader import (
    _REQUIRED_FIELDS,
    _load_schema,
    parse_master_rows,
)
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


def test_parse_master_accepts_verbose_header_names():
    # Esse é o header real da Master R04 R04 atual: "Informação auxiliar"
    # ganhou um sufixo descritivo. Match por prefixo deve aceitar.
    values = [
        [
            "Disciplina",
            "Tipo",
            "Fase",
            "Item",
            "Definições",
            "Status",
            "Custo",
            "Opção escolhida",
            "Observações",
            "Validado",
            "Informação auxiliar para tomada de decisão (EX: exemplo)",
            "APOIO 1",
            "APOIO 2",
        ],
        [
            "Geral",
            "Cadastro",
            "Fase 00",
            "GER01",
            "Quem é o cliente?",
            "",
            "",
            "",
            "",
            "",
            "Detalhe extra",
            "apoio A",
            "apoio B",
        ],
    ]
    rows = parse_master_rows(values)
    assert len(rows) == 1
    assert rows[0].informacao_auxiliar == "Detalhe extra"
    assert rows[0].apoio_1 == "apoio A"
    assert rows[0].apoio_2 == "apoio B"


def test_parse_master_accepts_underscored_apoio_headers():
    values = [
        [
            "Disciplina",
            "Tipo",
            "Fase",
            "Item",
            "Definições",
            "Informação auxiliar",
            "apoio_1",
            "apoio_2",
        ],
        ["Geral", "C", "F", "X1", "Pergunta?", "", "a1", "a2"],
    ]
    rows = parse_master_rows(values)
    assert len(rows) == 1
    assert rows[0].apoio_1 == "a1"
    assert rows[0].apoio_2 == "a2"


def test_parse_master_header_match_is_case_insensitive():
    values = [
        [
            "DISCIPLINA",
            "tipo",
            "FASE",
            "Item",
            "PERGUNTA",
            "Informacao Auxiliar",
            "APOIO 1",
            "APOIO 2",
        ],
        ["Geral", "C", "F", "X1", "?", "", "", ""],
    ]
    rows = parse_master_rows(values)
    assert len(rows) == 1


def test_parse_master_reports_missing_field_in_error():
    with pytest.raises(ValueError, match="apoio_2"):
        parse_master_rows(
            [
                [
                    "Disciplina",
                    "Tipo",
                    "Fase",
                    "Item",
                    "Definições",
                    "Informação auxiliar",
                    "APOIO 1",
                ],
            ]
        )


def test_yaml_schema_loads_and_covers_required_fields():
    schema = _load_schema()
    for field in _REQUIRED_FIELDS:
        assert field in schema, f"campo obrigatório {field!r} ausente do YAML"
        spec = schema[field]
        assert spec.canonical, f"{field!r} sem canonical"
        assert spec.aliases, f"{field!r} sem aliases"


def test_yaml_schema_has_all_thirteen_documented_fields():
    schema = _load_schema()
    expected = {
        "disciplina",
        "tipo",
        "fase",
        "item_code",
        "pergunta",
        "status",
        "custo",
        "opcao_escolhida",
        "observacoes",
        "validado",
        "informacao_auxiliar",
        "apoio_1",
        "apoio_2",
    }
    assert expected.issubset(set(schema.keys()))


def test_error_message_lists_aliases_canonical_and_headers_present():
    bad_header = [["Disciplina", "Tipo", "Fase", "Item", "Definições", "Informação auxiliar"]]
    with pytest.raises(ValueError) as excinfo:
        parse_master_rows(bad_header)
    msg = str(excinfo.value)
    assert "Headers presentes" in msg
    assert "Aliases aceitos" in msg
    assert "'APOIO 1'" in msg  # canonical reportado
    assert "'apoio_1'" in msg  # alias listado
    assert "'APOIO 2'" in msg
    assert "'Disciplina'" in msg  # header presente repassado pra debug


def test_load_schema_with_custom_path(tmp_path):
    custom = tmp_path / "schema.yaml"
    custom.write_text(
        """
version: 1
fields:
  disciplina:
    canonical: "Disciplina"
    aliases: ["disciplina"]
  tipo:
    canonical: "Tipo"
    aliases: ["tipo"]
  fase:
    canonical: "Fase"
    aliases: ["fase"]
  item_code:
    canonical: "Item"
    aliases: ["item"]
  pergunta:
    canonical: "Definições"
    aliases: ["definições"]
  informacao_auxiliar:
    canonical: "Informação auxiliar"
    aliases: ["info aux", "informação auxiliar"]
  apoio_1:
    canonical: "APOIO 1"
    aliases: ["apoio 1"]
  apoio_2:
    canonical: "APOIO 2"
    aliases: ["apoio 2"]
""",
        encoding="utf-8",
    )
    schema = _load_schema(str(custom))
    assert "info aux" in schema["informacao_auxiliar"].aliases


def test_malformed_yaml_raises_descriptive_error(tmp_path):
    bad = tmp_path / "broken.yaml"
    bad.write_text("fields:\n  disciplina: [unbalanced", encoding="utf-8")
    with pytest.raises(ValueError, match="YAML inválido"):
        _load_schema(str(bad))


def test_missing_yaml_file_raises_with_path(tmp_path):
    with pytest.raises(FileNotFoundError, match="não encontrado em"):
        _load_schema(str(tmp_path / "nope.yaml"))
