"""Agent registry for EAL-CORE.

Owns the mapping from :class:`~eal_core.identity.AgentIdentity` to live agent
instances. Provides create/register/resolve/drop operations with strict
capacity limits from :class:`~eal_core.config.Config`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from .event_bus import Event, EventBus
from .identity import AgentIdentity, CORE_IDENTITY

T = TypeVar("T")


@dataclass
class AgentRecord(Generic[T]):
    """A registered agent and its associated metadata.

    Attributes:
        identity: The agent's immutable identity.
        instance: The live agent object (type ``T`` is module-specific).
        metadata: JSON-serializable agent metadata (role, created_at, etc.).
    """

    identity: AgentIdentity
    instance: T
    metadata: dict[str, Any] = field(default_factory=dict)


class AgentRegistry(Generic[T]):
    """Thread-safe registry of live agents by identity.

    Agents are independent: each entry holds a distinct instance with its own
    state. The registry does not create cognitive systems; it only addresses
    and isolates existing ones.
    """

    def __init__(self, max_agents: int, event_bus: EventBus) -> None:
        if max_agents < 1:
            raise ValueError("max_agents must be a positive int")
        self._max_agents = max_agents
        self._bus = event_bus
        self._agents: dict[AgentIdentity, AgentRecord[T]] = {}
        self._lock = __import__("threading").RLock()

    # -- queries ----------------------------------------------------------

    def __contains__(self, identity: AgentIdentity) -> bool:
        with self._lock:
            return identity in self._agents

    def __len__(self) -> int:
        with self._lock:
            return len(self._agents)

    def get(self, identity: AgentIdentity) -> AgentRecord[T] | None:
        """Return the record for ``identity``, or ``None`` if unregistered."""
        with self._lock:
            return self._agents.get(identity)

    def get_instance(self, identity: AgentIdentity) -> T | None:
        """Return the live agent instance for ``identity``, or ``None``."""
        record = self.get(identity)
        return record.instance if record is not None else None

    def identities(self) -> list[AgentIdentity]:
        """Return a snapshot of all registered identities."""
        with self._lock:
            return list(self._agents.keys())

    # -- mutation ---------------------------------------------------------

    def register(self, identity: AgentIdentity, instance: T,
                 metadata: dict[str, Any] | None = None) -> AgentRecord[T]:
        """Register ``instance`` under ``identity``.

        Raises:
            ValueError: if the identity is already registered or capacity is
                exhausted.
        """
        with self._lock:
            if identity in self._agents:
                raise ValueError(f"agent {identity} already registered")
            if len(self._agents) >= self._max_agents:
                raise ValueError(f"agent capacity exhausted ({self._max_agents})")
            record = AgentRecord(
                identity=identity,
                instance=instance,
                metadata=dict(metadata or {}),
            )
            self._agents[identity] = record

        self._bus.publish(
            "agent.registered",
            {"identity": str(identity), "metadata": record.metadata},
            source=CORE_IDENTITY,
        )
        return record

    def create_identity(self) -> AgentIdentity:
        """Generate and register a fresh identity with no instance attached."""
        identity = AgentIdentity.generate()
        self.register(identity, None)  # type: ignore[arg-type]
        return identity

    def drop(self, identity: AgentIdentity) -> AgentRecord[T] | None:
        """Remove ``identity`` from the registry and return its record.

        Returns ``None`` if the identity was not registered.
        """
        with self._lock:
            record = self._agents.pop(identity, None)

        if record is not None:
            self._bus.publish(
                "agent.dropped",
                {"identity": str(identity)},
                source=CORE_IDENTITY,
            )
        return record

    def clear(self) -> list[AgentRecord[T]]:
        """Drop all agents and return their records (used in tests/reset)."""
        with self._lock:
            records = list(self._agents.values())
            self._agents.clear()
        for record in records:
            self._bus.publish(
                "agent.dropped",
                {"identity": str(record.identity)},
                source=CORE_IDENTITY,
            )
        return records
