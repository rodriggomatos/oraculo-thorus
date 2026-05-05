"""Unit tests pros helpers do parser (sem chamar Sheets API real)."""

from oraculo_ai.scope.parser import _normalize_bool, _trim


def test_normalize_bool_truthy_strings() -> None:
    assert _normalize_bool("TRUE")
    assert _normalize_bool("verdadeiro")
    assert _normalize_bool("Sim")
    assert _normalize_bool("X")
    assert _normalize_bool(1)


def test_normalize_bool_falsy() -> None:
    assert not _normalize_bool("FALSE")
    assert not _normalize_bool(None)
    assert not _normalize_bool("")
    assert not _normalize_bool("não")


def test_trim() -> None:
    assert _trim("  hello  ") == "hello"
    assert _trim("") is None
    assert _trim(None) is None
