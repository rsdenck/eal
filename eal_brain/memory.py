"""Memory interfaces for EAL-BRAIN.

Agents keep short-term (working) and long-term (persistent) memory. The
:class:`Memory` interface is strict so alternative backends can be swapped in
without changing agents.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Memory(ABC):
    """Abstract memory interface for an agent."""

    @abstractmethod
    def write(self, key: str, value: Any) -> None:
        raise NotImplementedError

    @abstractmethod
    def read(self, key: str) -> Any | None:
        raise NotImplementedError

    @abstractmethod
    def contains(self, key: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def delete(self, key: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def keys(self) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def clear(self) -> None:
        raise NotImplementedError


class InMemoryStore(Memory):
    """In-memory short-term + long-term store.

    short_term: working memory, evicted when it exceeds max_short_term.
    long_term: persistent memory, never auto-evicted.
    """

    def __init__(self, max_short_term: int = 1000) -> None:
        self.max_short_term = max_short_term
        self.short_term: dict[str, Any] = {}
        self.long_term: dict[str, Any] = {}
        self._short_order: list[str] = []

    def write(self, key: str, value: Any, persistent: bool = False) -> None:
        target = self.long_term if persistent else self.short_term
        target[key] = value
        if not persistent:
            if key not in self._short_order:
                self._short_order.append(key)
            while len(self._short_order) > self.max_short_term:
                evicted = self._short_order.pop(0)
                self.short_term.pop(evicted, None)

    def read(self, key: str) -> Any | None:
        if key in self.short_term:
            return self.short_term[key]
        if key in self.long_term:
            return self.long_term[key]
        return None

    def contains(self, key: str) -> bool:
        return key in self.short_term or key in self.long_term

    def delete(self, key: str) -> bool:
        removed = False
        if key in self.short_term:
            del self.short_term[key]
            self._short_order = [k for k in self._short_order if k != key]
            removed = True
        if key in self.long_term:
            del self.long_term[key]
            removed = True
        return removed

    def keys(self) -> list[str]:
        return list(self.short_term.keys()) + list(self.long_term.keys())

    def clear(self) -> None:
        self.short_term.clear()
        self.long_term.clear()
        self._short_order.clear()

    def promote(self, key: str) -> bool:
        """Move a short-term entry into long-term memory."""
        if key in self.short_term:
            self.long_term[key] = self.short_term[key]
            self.delete(key)
            return True
        return False
