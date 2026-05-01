"""Unit tests pro TTLCache."""

import time

import pytest

from mcp_drive.cache import TTLCache


def test_get_returns_none_for_missing_key() -> None:
    cache: TTLCache[str, int] = TTLCache(ttl_seconds=60)
    assert cache.get("missing") is None


def test_set_then_get_returns_value() -> None:
    cache: TTLCache[str, int] = TTLCache(ttl_seconds=60)
    cache.set("k", 42)
    assert cache.get("k") == 42


def test_invalidate_removes_entry() -> None:
    cache: TTLCache[str, int] = TTLCache(ttl_seconds=60)
    cache.set("k", 42)
    cache.invalidate("k")
    assert cache.get("k") is None


def test_clear_drops_all() -> None:
    cache: TTLCache[str, int] = TTLCache(ttl_seconds=60)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.clear()
    assert cache.get("a") is None
    assert cache.get("b") is None


def test_zero_ttl_raises() -> None:
    with pytest.raises(ValueError):
        TTLCache[str, int](ttl_seconds=0)


def test_max_entries_evicts_oldest() -> None:
    cache: TTLCache[int, int] = TTLCache(ttl_seconds=60, max_entries=2)
    cache.set(1, 100)
    time.sleep(0.001)
    cache.set(2, 200)
    time.sleep(0.001)
    cache.set(3, 300)
    assert cache.get(1) is None
    assert cache.get(2) == 200
    assert cache.get(3) == 300


async def test_get_or_load_hits_cache_on_second_call() -> None:
    cache: TTLCache[str, int] = TTLCache(ttl_seconds=60)
    calls = {"n": 0}

    async def loader() -> int:
        calls["n"] += 1
        return 99

    v1 = await cache.get_or_load("k", loader)
    v2 = await cache.get_or_load("k", loader)
    assert v1 == 99
    assert v2 == 99
    assert calls["n"] == 1
