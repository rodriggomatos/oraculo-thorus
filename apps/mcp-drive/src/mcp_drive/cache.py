"""Cache async TTL simples — chave -> (valor, expira_em).

Não é thread-safe além do necessário pra um único event loop. Concorrência
de chat é baixa; eventualmente várias requisições podem fazer miss simultâneo
e popular o cache em paralelo — aceitável.
"""

import time
from collections.abc import Awaitable, Callable, Hashable
from typing import Generic, TypeVar


K = TypeVar("K", bound=Hashable)
V = TypeVar("V")


class TTLCache(Generic[K, V]):
    def __init__(self, *, ttl_seconds: int, max_entries: int = 1024) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        self._ttl = ttl_seconds
        self._max = max_entries
        self._store: dict[K, tuple[V, float]] = {}

    def get(self, key: K) -> V | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.monotonic() >= expires_at:
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: K, value: V) -> None:
        if len(self._store) >= self._max:
            self._evict_oldest()
        self._store[key] = (value, time.monotonic() + self._ttl)

    def invalidate(self, key: K) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()

    async def get_or_load(self, key: K, loader: Callable[[], Awaitable[V]]) -> V:
        cached = self.get(key)
        if cached is not None:
            return cached
        value = await loader()
        self.set(key, value)
        return value

    def _evict_oldest(self) -> None:
        if not self._store:
            return
        oldest_key = min(self._store, key=lambda k: self._store[k][1])
        self._store.pop(oldest_key, None)
