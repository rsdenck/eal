"""Independent execution contexts for EAL-BRAIN.

Each agent runs in its own ExecutionContext: isolated state, a dedicated
random seed, and a step counter. Agents do not share execution contexts.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ExecutionContext:
    """Isolated execution context for one agent.

    Attributes:
        agent_id: The agent this context belongs to.
        seed: The agent's dedicated random seed.
        rng: The agent's private random number generator.
        step: Number of steps executed in this context.
    """

    agent_id: str
    seed: int
    rng: random.Random = field(init=False)
    step: int = 0

    def __post_init__(self) -> None:
        self.rng = random.Random(self.seed)

    def advance(self) -> None:
        self.step += 1

    def snapshot(self) -> dict[str, object]:
        return {
            "agent_id": self.agent_id,
            "seed": self.seed,
            "step": self.step,
        }
