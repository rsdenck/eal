"""EAL-ORG: autonomous agent factory.

Implements the EAL-FACTORY creation cycle:
1. Identify the need. 2. Define the objective. 3. Define competencies.
4. Select the base model. 5. Define identity. 6. Configure memory/context.
7. Define permissions. 8. Allocate resources. 9. Define supervisor.
10. Initialize. 11. Capacity tests. 12. Enter operation.

Distinguishes instances, configurations, adapters and effectively-trained
models; creating an agent does not necessarily mean training a new model.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from eal_brain import Agent
from eal_brain.context import ExecutionContext
from eal_brain.inference import DeterministicInference
from eal_brain.learning import ReferenceLearner
from eal_brain.memory import InMemoryStore
from eal_brain.state import AgentState
from eal_core.identity import AgentIdentity


@dataclass
class AgentSpec:
    """Specification for a new agent."""

    role: str
    specialization: str
    objective: str
    competencies: list[str] = field(default_factory=list)
    base_model: str = "stdlib-reference"
    memory_config: dict[str, Any] = field(default_factory=dict)
    resource_allocation: dict[str, Any] = field(default_factory=dict)
    supervisor: Optional[str] = None
    seed: int = 0


@dataclass
class AgentCreationRecord:
    """Audit record for a created agent."""

    agent_id: str
    spec: AgentSpec
    created_at: str
    status: str  # "created", "testing", "operational", "retired"
    capacity_test_passed: bool = False


class AgentFactory:
    """Creates agents autonomously following the EAL-FACTORY cycle."""

    def __init__(self) -> None:
        self._records: dict[str, AgentCreationRecord] = {}
        self._counter = 0

    def create_agent(self, spec: AgentSpec) -> Agent:
        """Run the full creation cycle and return a live Agent."""
        self._counter += 1
        agent_id = str(AgentIdentity.generate())

        # 1-3. Need/objective/competencies are in spec.
        # 4. Base model (reference CPU model here).
        inference = DeterministicInference(seed=spec.seed)
        # 5. Identity (generated above).
        identity = AgentIdentity(value=agent_id)
        # 6. Memory + context.
        memory = InMemoryStore()
        context = ExecutionContext(agent_id=agent_id, seed=spec.seed)
        state = AgentState(agent_id=agent_id)
        # 7-8. Permissions/resources (recorded; enforced by RoleManager/engine).
        # 9. Supervisor (recorded).
        # 10. Initialize.
        learner = ReferenceLearner()
        agent = Agent(
            identity=identity, state=state, memory=memory,
            inference=inference, learner=learner, context=context,
            seed=spec.seed,
        )
        agent.memory.write("objective", spec.objective, persistent=True)
        agent.memory.write("specialization", spec.specialization,
                           persistent=True)
        agent.memory.write("competencies", list(spec.competencies),
                           persistent=True)
        # 11. Capacity tests.
        passed = self._capacity_test(agent, spec)
        # 12. Enter operation.
        status = "operational" if passed else "testing"
        self._records[agent_id] = AgentCreationRecord(
            agent_id=agent_id, spec=spec,
            created_at=self._now(),
            status=status,
            capacity_test_passed=passed,
        )
        return agent

    def _capacity_test(self, agent: Agent, spec: AgentSpec) -> bool:
        """Basic capacity: agent can observe, infer, and learn."""
        try:
            agent.observe("test", {"ok": True})
            agent.infer("capacity-probe")
            agent.learn({"reward": 1.0, "key": "capacity"})
            return True
        except Exception:
            return False

    def record(self, agent_id: str) -> AgentCreationRecord | None:
        return self._records.get(agent_id)

    def all_records(self) -> dict[str, AgentCreationRecord]:
        return dict(self._records)

    @staticmethod
    def _now() -> str:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
