"""EAL-ORG: management framework (EAL-MANAGER).

The EAL-MANAGER is the original agent-management framework controlling the
organizational lifecycle without permanent dependence on external frameworks.
It integrates agent management, workforce management, organization management,
task management, scheduling, resource management, memory management, model
management, communication management, performance management, failure
management and policy management.

It exposes stable interfaces for integration with other EAL modules.
"""

from __future__ import annotations

from typing import Optional

from eal_org.governance import GovernancePolicyEngine, OrganizationalAuditLog
from eal_org.lifecycle import AgentLifecycleManager
from eal_org.organization import OrganizationEngine
from eal_org.orchestrator import CommandControlEngine
from eal_org.performance import AgentPerformanceEvaluator
from eal_org.tasks import TaskDelegationEngine


class OrganizationManager:
    """EAL-MANAGER: original agent-management framework.

    Coordinates all organizational subsystems through stable interfaces.
    """

    def __init__(self) -> None:
        self.organization = OrganizationEngine()
        self.hierarchy = self.organization.hierarchy
        self.roles = self.organization.roles
        self.lifecycle = AgentLifecycleManager(self.organization,
                                               self._factory(),
                                               self.hierarchy, self.roles)
        self.factory = self.lifecycle.factory
        self.tasks = TaskDelegationEngine()
        self.orchestrator = CommandControlEngine(self.organization,
                                                 self.lifecycle, self.tasks)
        self.performance = AgentPerformanceEvaluator(self.tasks)
        self.governance = GovernancePolicyEngine()
        self.audit = OrganizationalAuditLog()
        self.owner: Optional[object] = None  # set via appoint_owner

    def _factory(self):
        from eal_org.factory import AgentFactory
        return AgentFactory()

    def appoint_owner(self, spec, scope: str = "global") -> object:
        from eal_org.owner import OwnerAgent
        agent = self.lifecycle.create(spec)
        owner = OwnerAgent(agent, self.organization, self.lifecycle,
                           self.orchestrator, self.governance, self.audit,
                           scope=scope)
        self.owner = owner
        self.audit.record("appoint_owner", "system", str(agent.identity),
                          "appoint_owner", approved=True,
                          detail={"scope": scope})
        return owner

    def create_worker(self, spec, parent: Optional[str] = None,
                      department: Optional[str] = None) -> object:
        from eal_org.worker import WorkerAgent
        agent = self.lifecycle.create(spec, parent=parent,
                                      department=department)
        return WorkerAgent(agent, self.organization, self.lifecycle,
                           self.orchestrator, self.governance, self.audit)

    def run_objective(self, objective: str) -> dict:
        if self.owner is None:
            raise RuntimeError("no owner appointed")
        oid = self.owner.delegate_objective(objective)
        task_ids = self.owner.orchestrator.decompose_and_delegate(oid)
        # Workers execute their assigned running tasks.
        for tid in task_ids:
            task = self.tasks.get(tid)
            if task is not None and task.status == "running":
                # Find the worker owning this task.
                for aid in self.organization.hierarchy.agents():
                    if self.organization.hierarchy.children(aid):
                        pass
                # Direct: owner's workers execute.
                w = self._find_worker_for(task.owner)
                if w is not None:
                    w.execute_task(tid, self.tasks)
        tracking = self.orchestrator.track()
        return {"objective_id": oid, "tracking": tracking}

    def _find_worker_for(self, agent_id: str):
        # Return a WorkerAgent if one wraps this agent, else None.
        if self.owner and self.owner.agent_id == agent_id:
            return self.owner
        return None

    def evaluate_workforce(self) -> dict:
        reports = {}
        for aid in self.organization.hierarchy.agents():
            rep = self.performance.evaluate(aid)
            reports[aid] = {
                "score": rep.score,
                "completed": rep.tasks_completed,
                "failed": rep.tasks_failed,
                "completion_rate": rep.completion_rate,
            }
        return {"reports": reports,
                "underperformers": self.performance.underperformers()}

    def reorganize(self, agent_id: str,
                   new_parent: Optional[str]) -> bool:
        ok = self.lifecycle.org.reparent(agent_id, new_parent)
        self.audit.record("reorganize", "manager", agent_id,
                          "reparent", approved=ok,
                          detail={"new_parent": new_parent})
        return ok

    def snapshot(self) -> dict:
        return {
            "organization": self.organization.snapshot(),
            "tracking": self.orchestrator.track(),
            "performance": self.evaluate_workforce(),
            "audit_entries": len(self.audit.entries()),
            "owner": self.owner.agent_id if self.owner else None,
        }
