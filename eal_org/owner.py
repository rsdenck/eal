"""EAL-ORG: autonomous executive agent (EAL-OWNER).

The Owner is the highest-level executive function. It interprets EAL's
overall objectives, identifies capabilities to develop, creates departments,
appoints responsible agents, creates/assigns roles, distributes resources,
delegates objectives, evaluates results, resolves conflicts and monitors
overall evolution.

The Owner coordinates and supervises; it does not necessarily execute every
task itself. Multiple Owners may exist for different units with independent
scopes.
"""

from __future__ import annotations

from typing import Optional

from eal_brain import Agent
from eal_org.orchestrator import CommandControlEngine  # noqa: F401  (typing clarity)
from eal_org.governance import GovernancePolicyEngine, OrganizationalAuditLog
from eal_org.lifecycle import AgentLifecycleManager
from eal_org.organization import OrganizationEngine


class OwnerAgent:
    """EAL-OWNER: autonomous executive agent.

    Wraps an EAL-BRAIN Agent and gives it organizational authority through
    the OrganizationEngine, lifecycle manager, orchestrator, governance and
    audit log.
    """

    def __init__(self, agent: Agent,
                 organization: OrganizationEngine,
                 lifecycle: AgentLifecycleManager,
                 orchestrator: CommandControlEngine,
                 governance: GovernancePolicyEngine,
                 audit: OrganizationalAuditLog,
                 scope: str = "global") -> None:
        self.agent = agent
        self.agent_id = str(agent.identity)
        self.organization = organization
        self.lifecycle = lifecycle
        self.orchestrator = orchestrator
        self.governance = governance
        self.audit = audit
        self.scope = scope

    def create_department(self, dept_id: str, name: str,
                          specialization: str,
                          external_approval: bool = False) -> bool:
        action = "create_department"
        if not self.governance.approve(action, self.agent_id,
                                       external_approval):
            self.audit.record("denied", self.agent_id, dept_id, action,
                              approved=False,
                          detail={"reason": "external approval required"})
            return False
        ok = self.organization.create_department(dept_id, name, specialization)
        self.audit.record("create_department", self.agent_id, dept_id, action,
                          approved=ok,
                          detail={"name": name,
                                  "specialization": specialization})
        return ok

    def create_owner_unit(self, spec, parent: Optional[str] = None,
                          department: Optional[str] = None,
                          external_approval: bool = False) -> Optional[object]:
        """Create a new Owner-led unit (sub-organization scope)."""
        action = "create_agent"
        if not self.governance.approve(action, self.agent_id,
                                       external_approval):
            self.audit.record("denied", self.agent_id, "new-owner", action,
                              approved=False,
                              detail={"reason": "external approval required"})
            return None
        from eal_org.owner import OwnerAgent as _OwnerAgent
        from eal_org.worker import WorkerAgent
        agent = self.lifecycle.create(spec, parent=parent,
                                      department=department)
        owner = OwnerAgent(agent, self.organization, self.lifecycle,
                           self.orchestrator, self.governance, self.audit,
                           scope="unit")
        self.audit.record("create_owner", self.agent_id, str(agent.identity),
                          action, approved=True,
                          detail={"role": spec.role, "scope": "unit"})
        return owner

    def create_worker(self, spec,
                      parent: Optional[str] = None,
                      department: Optional[str] = None,
                      external_approval: bool = False) -> Optional[object]:
        from eal_org.worker import WorkerAgent
        action = "create_agent"
        if not self.governance.approve(action, self.agent_id,
                                       external_approval):
            self.audit.record("denied", self.agent_id, "new-worker", action,
                              approved=False,
                              detail={"reason": "external approval required"})
            return None
        agent = self.lifecycle.create(spec, parent=parent,
                                      department=department)
        worker = WorkerAgent(agent, self.organization, self.lifecycle,
                             self.orchestrator, self.governance, self.audit)
        self.audit.record("create_worker", self.agent_id, str(agent.identity),
                          action, approved=True,
                          detail={"role": spec.role})
        return worker

    def delegate_objective(self, objective: str) -> str:
        oid = self.orchestrator.receive_objective(objective, self.agent_id)
        self.audit.record("delegate_objective", self.agent_id, oid,
                          "receive_objective", approved=True,
                          detail={"objective": objective})
        return oid

    def evaluate_organization(self) -> dict:
        tracking = self.orchestrator.track()
        self.audit.record("evaluate_organization", self.agent_id,
                          "organization", "evaluate", approved=True,
                          detail=tracking)
        return tracking

    def retire_agent(self, agent_id: str,
                     external_approval: bool = False) -> bool:
        action = "retire_agent"
        if not self.governance.approve(action, self.agent_id, external_approval):
            self.audit.record("denied", self.agent_id, agent_id, action,
                              approved=False,
                              detail={"reason": "external approval required"})
            return False
        ok = self.lifecycle.retire(agent_id)
        self.audit.record("retire_agent", self.agent_id, agent_id, action,
                          approved=ok)
        return ok

    def snapshot(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "scope": self.scope,
            "organization": self.organization.snapshot(),
            "tracking": self.orchestrator.track(),
            "audit_entries": len(self.audit.entries()),
        }
