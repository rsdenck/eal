"""Agent identity primitives for EAL-CORE.

An AgentIdentity is an immutable, unforgeable identifier for an independent
agent. Identities carry no semantic meaning about the agent's role or
capabilities; they exist solely to address and isolate independent execution
contexts.

Assigning different names to identical prompts does not create independent
cognitive systems: each AgentIdentity is backed by independent state owned by
the agent instance that created it.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class AgentIdentity:
    """Immutable agent identifier.

    Attributes:
        value: A globally unique identifier (UUID4). Once created it cannot
            change, which makes identities suitable as dictionary keys and as
            stable addresses on the event bus.
    """

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("AgentIdentity.value must not be empty")

    @classmethod
    def generate(cls) -> "AgentIdentity":
        """Generate a fresh, random agent identity."""
        return cls(value=str(uuid.uuid4()))

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.value

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return f"AgentIdentity({self.value!r})"


# Reserved identity used by the EAL core itself when it emits system-level
# events (e.g. lifecycle telemetry). Agents must not use this value.
CORE_IDENTITY: Final[AgentIdentity] = AgentIdentity(value="eal-core")
