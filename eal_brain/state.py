"""Agent state management for EAL-BRAIN.

AgentState holds the mutable, per-agent state. Each agent owns an independent
instance; no state is shared between agents unless explicitly communicated
through a channel (EAL-CL / EAL-SC).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


@dataclass
class AgentState:
    """Mutable state of a single agent.

    Attributes:
        agent_id: The agent this state belongs to.
        beliefs: Learned internal beliefs (symbol -> value, concept -> weight, ...).
        representations: Internal representations keyed by name.
        counters: Agent-defined counters (e.g. messages sent, successes).
        step_count: Number of execution steps this agent has performed.
        last_reward: Reward from the most recent learning update (None if none).
        updated_at: ISO-8601 UTC timestamp of last mutation.
    """

    agent_id: str
    beliefs: dict[str, Any] = field(default_factory=dict)
    representations: dict[str, Any] = field(default_factory=dict)
    counters: dict[str, int] = field(default_factory=dict)
    step_count: int = 0
    last_reward: float | None = None
    updated_at: str = field(default_factory=_now)

    def increment(self, counter: str, amount: int = 1) -> None:
        self.counters[counter] = self.counters.get(counter, 0) + amount
        self.step_count += 1
        self.updated_at = _now()

    def set_belief(self, key: str, value: Any) -> None:
        self.beliefs[key] = value
        self.updated_at = _now()

    def get_belief(self, key: str, default: Any = None) -> Any:
        return self.beliefs.get(key, default)

    def snapshot(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "beliefs": dict(self.beliefs),
            "representations": dict(self.representations),
            "counters": dict(self.counters),
            "step_count": self.step_count,
            "last_reward": self.last_reward,
            "updated_at": self.updated_at,
        }

    @classmethod
    def load(cls, data: dict[str, Any]) -> "AgentState":
        return cls(
            agent_id=data["agent_id"],
            beliefs=dict(data.get("beliefs") or {}),
            representations=dict(data.get("representations") or {}),
            counters=dict(data.get("counters") or {}),
            step_count=int(data.get("step_count", 0)),
            last_reward=data.get("last_reward"),
            updated_at=data.get("updated_at", _now()),
        )
