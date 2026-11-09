"""EAL-ORG: autonomous worker agent (EAL-WORKER).

Workers are specialized agents created dynamically to execute tasks. Each
worker has a unique identity, role, specialization, objectives, internal
state, individual memory, execution context, permissions, allocated
resources, a supervisor, task history and performance indicators.
"""

from __future__ import annotations

from typing import Optional

from eal_brain import Agent
from eal_org.orchestrator import CommandControlEngine  # noqa: F401
from eal_org.governance import GovernancePolicyEngine, OrganizationalAuditLog
from eal_org.lifecycle import AgentLifecycleManager
from eal_org.organization import OrganizationEngine


class WorkerAgent:
    """EAL-WORKER: autonomous worker agent."""

    def __init__(self, agent: Agent,
                 organization: OrganizationEngine,
                 lifecycle: AgentLifecycleManager,
                 orchestrator: CommandControlEngine,
                 governance: GovernancePolicyEngine,
                 audit: OrganizationalAuditLog) -> None:
        self.agent = agent
        self.agent_id = str(agent.identity)
        self.organization = organization
        self.lifecycle = lifecycle
        self.orchestrator = orchestrator
        self.governance = governance
        self.audit = audit
        self.specialization = agent.state.get_belief("specialization",
                                                     "general")
        self.objective = agent.state.get_belief("objective", "")

    def execute_task(self, task_id: str,
                     tasks) -> bool:
        """Execute a delegated task; record result and evidence."""
        from eal_org.tasks import TaskDelegationEngine
        if not isinstance(tasks, TaskDelegationEngine):
            return False
        task = tasks.get(task_id)
        if task is None or task.status != "running":
            return False
        if task.owner != self.agent_id:
            return False
        # Perform the task (deterministic simulation of work).
        result = f"completed '{task.objective}' by worker {self.agent_id[:8]}"
        evidence = [f"task-{task_id}-output", f"agent-{self.agent_id[:8]}"]
        ok = tasks.complete(task_id, result, evidence)
        if ok:
            self.agent.memory.write(f"task:{task_id}", result,
                                    persistent=True)
            self.audit.record("execute_task", self.agent_id, task_id,
                              "complete", approved=True,
                              detail={"result": result})
        return ok

    def report_result(self, task_id: str,
                      tasks) -> bool:
        from eal_org.tasks import TaskDelegationEngine
        if not isinstance(tasks, TaskDelegationEngine):
            return False
        task = tasks.get(task_id)
        if task is None:
            return False
        self.audit.record("report_result", self.agent_id, task_id,
                          "report", approved=True,
                          detail={"status": task.status})
        return task.status == "completed"

    def snapshot(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "specialization": self.specialization,
            "role": self.organization.agent_role(self.agent_id),
            "supervisor": self.organization.supervisor(self.agent_id),
            "department": self.organization.department_of(self.agent_id),
        }
