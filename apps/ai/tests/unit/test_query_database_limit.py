"""Unit tests pra `apply_limit` — proteção contra resultsets grandes."""

import pytest

from oraculo_ai.agents.qa.tools.query_database import apply_limit


def test_injects_default_limit_when_absent():
    out, applied = apply_limit("SELECT * FROM projects")
    assert out == "SELECT * FROM projects LIMIT 100"
    assert applied == "default_100"


def test_keeps_existing_limit_within_bounds():
    out, applied = apply_limit("SELECT * FROM projects LIMIT 50")
    assert out == "SELECT * FROM projects LIMIT 50"
    assert applied is None


def test_caps_excessive_limit():
    out, applied = apply_limit("SELECT * FROM projects LIMIT 5000")
    assert out == "SELECT * FROM projects LIMIT 1000"
    assert applied == "capped_to_1000"


def test_strips_trailing_semicolon_before_injecting():
    out, applied = apply_limit("SELECT * FROM projects;")
    assert out == "SELECT * FROM projects LIMIT 100"
    assert applied == "default_100"


def test_keeps_offset_when_present_and_limit_is_safe():
    out, applied = apply_limit("SELECT * FROM projects LIMIT 50 OFFSET 100")
    assert "LIMIT 50" in out
    assert "OFFSET 100" in out
    assert applied is None


def test_subquery_limit_does_not_count_as_outer_limit():
    # LIMIT dentro de subquery NÃO é o limit top — devemos injetar.
    out, applied = apply_limit(
        "SELECT * FROM (SELECT * FROM projects LIMIT 5) sub"
    )
    assert out.endswith("LIMIT 100")
    assert applied == "default_100"


def test_multiline_select_with_trailing_limit():
    sql = "SELECT a,\n  b\nFROM projects\nWHERE x=1\nLIMIT 200"
    out, applied = apply_limit(sql)
    assert out.endswith("LIMIT 200")
    assert applied is None


def test_case_insensitive_limit_match():
    out, applied = apply_limit("select * from projects limit 50")
    assert applied is None
    out2, applied2 = apply_limit("select * from projects LiMiT 5000")
    assert "LIMIT 1000" in out2
    assert applied2 == "capped_to_1000"


@pytest.mark.parametrize(
    "raw,expected_tail,expected_tag",
    [
        ("SELECT 1", "LIMIT 100", "default_100"),
        ("SELECT 1 LIMIT 1", "LIMIT 1", None),
        ("SELECT 1 LIMIT 100000", "LIMIT 1000", "capped_to_1000"),
        ("  SELECT 1  ", "LIMIT 100", "default_100"),
    ],
)
def test_apply_limit_table(raw: str, expected_tail: str, expected_tag: str | None):
    out, applied = apply_limit(raw)
    assert out.rstrip().endswith(expected_tail)
    assert applied == expected_tag
