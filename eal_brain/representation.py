"""Internal representations for EAL-BRAIN.

An InternalRepresentation is an agent's private encoding of information:
continuous (vector) and/or symbolic. Representations are internal to an agent
and are not the communicated language itself (EAL-CL); they are what agents
manipulate when learning to communicate or program.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class InternalRepresentation:
    """A private internal representation.

    Attributes:
        name: Identifier for this representation within the agent.
        vector: Continuous latent representation (list of floats), or None.
        symbols: Discrete symbolic representation (list of symbol ids), or None.
        metadata: JSON-serializable annotation.
    """

    name: str
    vector: list[float] | None = None
    symbols: list[str] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def content_hash(self) -> str:
        payload = json.dumps(
            {"vector": self.vector, "symbols": self.symbols},
            sort_keys=True,
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()[:32]

    def is_empty(self) -> bool:
        return self.vector is None and self.symbols is None
