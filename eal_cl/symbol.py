"""Discrete learnable symbols for EAL-CL.

A Symbol is an opaque, discrete token with no hardcoded meaning. Meaning
emerges through interaction between agents, never from the symbol definition
itself. Each symbol may carry an optional binary bit pattern (for symbolic/binary
representation) and metadata.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Symbol:
    """An immutable discrete symbol.

    Attributes:
        id: Globally unique symbol identifier.
        bit_pattern: Optional binary representation of the symbol.
        metadata: JSON-serializable annotation (e.g. origin agent, birth step).
    """

    id: str
    bit_pattern: bytes | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def generate(cls, bit_pattern: bytes | None = None,
                 metadata: dict[str, Any] | None = None) -> "Symbol":
        return cls(
            id=str(uuid.uuid4()),
            bit_pattern=bit_pattern,
            metadata=dict(metadata or {}),
        )

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return f"Symbol(id={self.id[:8]}..., bits={self.bit_pattern})"
