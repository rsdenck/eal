"""Independent agent for EAL-BRAIN.

An Agent is an independent cognitive unit: its own identity, state, memory,
internal representations, inference engine, learner and execution context.
Agents do not share cognitive state; communication happens exclusively through
explicit channels (EAL-CL / EAL-SC).
"""

from __future__ import annotations

from typing import Any

from eal_core.identity import AgentIdentity

from .context import ExecutionContext
from .inference import DeterministicInference, ModelInference
from .learning import Learner, ReferenceLearner
from .memory import InMemoryStore, Memory
from .representation import InternalRepresentation
from .state import AgentState


class Agent:
    """An independently operating agent.

    Attributes:
        identity: Immutable agent identity.
        state: Mutable agent state (beliefs, representations, counters).
        memory: Short-term + long-term memory.
        inference: Model inference engine.
        learner: Learning engine (separate from inference).
        context: Isolated execution context.
    """

    def __init__(self, identity: AgentIdentity,
                 state: AgentState | None = None,
                 memory: Memory | None = None,
                 inference: ModelInference | None = None,
                 learner: Learner | None = None,
                 context: ExecutionContext | None = None,
                 seed: int = 0) -> None:
        self.identity = identity
        self.state = state or AgentState(agent_id=str(identity))
        self.memory = memory or InMemoryStore()
        self.inference = inference or DeterministicInference(seed=seed)
        self.learner = learner or ReferenceLearner()
        self.context = context or ExecutionContext(
            agent_id=str(identity), seed=seed,
        )

    def observe(self, key: str, value: Any, persistent: bool = False) -> None:
        """Record an observation in memory (e.g. a received message)."""
        self.memory.write(key, value, persistent=persistent)
        self.context.advance()
        self.state.increment("observations")

    def infer(self, input_data: Any,
              parameters: dict[str, Any] | None = None) -> Any:
        """Run inference through the agent's private inference engine."""
        output = self.inference.infer(input_data, parameters=parameters)
        self.context.advance()
        self.state.increment("inferences")
        return output

    def learn(self, experience: dict[str, Any]) -> dict[str, Any]:
        """Update the agent's beliefs from an experience (training path)."""
        result = self.learner.update(self.state, experience)
        self.context.advance()
        self.state.increment("learning_updates")
        return result

    def evaluate(self, experience: dict[str, Any]) -> dict[str, float]:
        """Evaluate without updating (evaluation path, separate from training)."""
        return self.learner.evaluate(self.state, experience)

    def represent(self, name: str, vector: list[float] | None = None,
                  symbols: list[str] | None = None) -> InternalRepresentation:
        """Store an internal representation in state."""
        rep = InternalRepresentation(name=name, vector=vector, symbols=symbols)
        self.state.representations[name] = rep
        return rep

    def snapshot(self) -> dict[str, Any]:
        return {
            "identity": str(self.identity),
            "state": self.state.snapshot(),
            "memory_keys": self.memory.keys(),
            "context": self.context.snapshot(),
            "inference_backend": type(self.inference).__name__,
        }
