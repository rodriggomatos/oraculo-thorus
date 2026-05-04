"""Unit tests pros helpers do parser (sem chamar Sheets API real)."""

from decimal import Decimal

from oraculo_ai.scope.parser import (
    _normalize_bool,
    _normalize_optional_bool,
    _parse_decimal,
    _parse_decimal_required,
    _trim,
)


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


def test_normalize_optional_bool() -> None:
    assert _normalize_optional_bool(None) is None
    assert _normalize_optional_bool("") is None
    assert _normalize_optional_bool("true") is True
    assert _normalize_optional_bool(False) is False


def test_parse_decimal_handles_brazilian_format() -> None:
    assert _parse_decimal("1.234,56") == Decimal("1234.56")
    assert _parse_decimal("147387,50") == Decimal("147387.50")


def test_parse_decimal_handles_plain_numbers() -> None:
    assert _parse_decimal("123") == Decimal("123")
    assert _parse_decimal(42.5) == Decimal("42.5")


def test_parse_decimal_returns_none_for_garbage() -> None:
    assert _parse_decimal(None) is None
    assert _parse_decimal("") is None
    assert _parse_decimal("abc") is None


def test_parse_decimal_required_falls_back() -> None:
    assert _parse_decimal_required(None) == Decimal("0")
    assert _parse_decimal_required("123,45") == Decimal("123.45")


def test_trim() -> None:
    assert _trim("  hello  ") == "hello"
    assert _trim("") is None
    assert _trim(None) is None
