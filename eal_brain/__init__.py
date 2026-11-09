"""EAL-BRAIN: agent cognitive infrastructure.

Public API:
    AgentState             # mutable per-agent state
    InternalRepresentation # private continuous/symbolic representation
    Memory, InMemoryStore  # short-term + long-term memory interface
    ExecutionContext       # isolated per-agent execution context
    ModelInference, DeterministicInference, NVIDIAInferencePlaceholder  # inference
    Learner, ReferenceLearner  # learning (train/eval separate)
    Agent                  # independent cognitive unit

Each Agent owns independent state, memory and execution context. Agents
communicate only through explicit channels (EAL-CL / EAL-SC); assigning
different names to identical prompts does not create independent systems.
"""

from .agent import Agent
from .context import ExecutionContext
from .inference import DeterministicInference, ModelInference, NVIDIAInferencePlaceholder
from .learning import Learner, ReferenceLearner
from .memory import InMemoryStore, Memory
from .representation import InternalRepresentation
from .state import AgentState

__all__ = [
    "Agent",
    "AgentState",
    "DeterministicInference",
    "ExecutionContext",
    "InternalRepresentation",
    "Learner",
    "Memory",
    "ModelInference",
    "NVIDIAInferencePlaceholder",
    "ReferenceLearner",
    "InMemoryStore",
]
