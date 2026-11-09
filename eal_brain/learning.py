"""Learning interfaces for EAL-BRAIN.

Separates training, evaluation and inference (spec §3 EAL-LEARNING).
:class:`Learner` is the interface; :class:`ReferenceLearner` is a stdlib
reference (deterministic belief update) so experiments run without ML libs.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Learner(ABC):
    """Strict learning interface.

    update(agent_state, experience) -> updated state / metrics.
    evaluate(...) -> metrics (separate from training).
    """

    @abstractmethod
    def update(self, state: Any, experience: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def evaluate(self, state: Any, experience: dict[str, Any]) -> dict[str, float]:
        raise NotImplementedError


class ReferenceLearner(Learner):
    """Deterministic reference learner (stdlib only).

    Updates beliefs as a running average of observed rewards. Not a real RL
    algorithm; keeps EAL-BRAIN runnable without ML libraries. Real algorithms
    (multi-agent RL, GRPO, contrastive) implement Learner behind this interface.
    """

    def __init__(self, learning_rate: float = 0.1) -> None:
        self.learning_rate = learning_rate
        self.updates = 0

    def update(self, state: Any, experience: dict[str, Any]) -> dict[str, Any]:
        reward = float(experience.get("reward", 0.0))
        key = str(experience.get("key", "default"))
        current = float(state.get_belief(key, 0.0))
        updated = current + self.learning_rate * (reward - current)
        state.set_belief(key, updated)
        state.last_reward = reward
        self.updates += 1
        return {"key": key, "belief": updated, "reward": reward, "updates": self.updates}

    def evaluate(self, state: Any,
                 experience: dict[str, Any]) -> dict[str, float]:
        reward = float(experience.get("reward", 0.0))
        key = str(experience.get("key", "default"))
        current = float(state.get_belief(key, 0.0))
        return {"predicted": current, "observed": reward,
                "error": abs(current - reward)}
