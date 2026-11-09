"""Dynamic, versioned vocabulary for EAL-CL.

A Vocabulary is a mutable set of Symbols with a version identifier. Symbols can
be added or removed as agents discover or abandon them. Each mutation produces
a new version so language evolution can preserve and compare historical states.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from .symbol import Symbol


@dataclass
class Vocabulary:
    """A dynamic, versioned set of symbols.

    Attributes:
        version_id: Content-stable identifier for this vocabulary version.
        symbols: Mapping of symbol id -> Symbol.
    """

    version_id: str
    symbols: dict[str, Symbol] = field(default_factory=dict)

    @classmethod
    def create(cls) -> "Vocabulary":
        vocab = cls(version_id="v0")
        vocab.version_id = vocab._compute_version_id()
        return vocab

    def add(self, symbol: Symbol) -> None:
        self.symbols[symbol.id] = symbol
        self.version_id = self._compute_version_id()

    def remove(self, symbol_id: str) -> Symbol | None:
        removed = self.symbols.pop(symbol_id, None)
        if removed is not None:
            self.version_id = self._compute_version_id()
        return removed

    def get(self, symbol_id: str) -> Symbol | None:
        return self.symbols.get(symbol_id)

    def __len__(self) -> int:
        return len(self.symbols)

    def __iter__(self):
        return iter(self.symbols.values())

    def ids(self) -> list[str]:
        return sorted(self.symbols.keys())

    def snapshot(self) -> dict[str, Any]:
        return {
            "version_id": self.version_id,
            "symbols": {
                sid: {
                    "id": s.id,
                    "bit_pattern": s.bit_pattern.hex() if s.bit_pattern else None,
                    "metadata": s.metadata,
                }
                for sid, s in self.symbols.items()
            },
        }

    @classmethod
    def load(cls, snapshot: dict[str, Any]) -> "Vocabulary":
        vocab = cls(version_id=snapshot["version_id"])
        for sid, data in snapshot.get("symbols", {}).items():
            bits = bytes.fromhex(data["bit_pattern"]) if data.get("bit_pattern") else None
            vocab.symbols[sid] = Symbol(
                id=data["id"], bit_pattern=bits, metadata=dict(data.get("metadata") or {})
            )
        return vocab

    def _content(self) -> dict[str, Any]:
        """Content used for versioning (excludes version_id to avoid a
        self-referential hash)."""
        return {
            "symbols": {
                sid: {
                    "id": s.id,
                    "bit_pattern": s.bit_pattern.hex() if s.bit_pattern else None,
                    "metadata": s.metadata,
                }
                for sid, s in sorted(self.symbols.items())
            },
        }

    def _compute_version_id(self) -> str:
        payload = json.dumps(self._content(), sort_keys=True).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()[:32]
