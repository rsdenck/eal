"""EAL-ORG: agent lifecycle manager.

Handles create, promote, demote, suspend, replace and retire operations,
preserving historical relationships for reorganization rollback.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from eal_org.factory import AgentSpec, AgentFactory
from eal_org.hierarchy import HierarchyManager
from eal_org.organization import OrganizationEngine
from eal_org.roles import RoleManager


@dataclass
class LifecycleEvent:
    kind: str  # "create", "promote", "demote", "suspend", "replace", "retire"
    agent_id: str
    timestamp: str
    detail: dict


class AgentLifecycleManager:
    """Manages the full lifecycle of organizational agents."""

    def __init__(self, organization: OrganizationEngine,
                 factory: AgentFactory,
                 hierarchy: HierarchyManager,
                 roles: RoleManager) -> None:
        self.org = organization
        self.factory = factory
        self.hierarchy = hierarchy
        self.roles = roles
        self._events: list[LifecycleEvent] = []
        self._suspended: set[str] = set()

    def _event(self, kind: str, agent_id: str,
               detail: dict) -> LifecycleEvent:
        ev = LifecycleEvent(kind=kind, agent_id=agent_id,
                            timestamp=self._now(), detail=detail)
        self._events.append(ev)
        return ev

    def create(self, spec: AgentSpec,
               parent: Optional[str] = None,
               department: Optional[str] = None) -> Agent:
        agent = self.factory.create_agent(spec)
        self.org.register_agent(str(agent.identity), spec.role, parent,
                                department)
        self._event("create", str(agent.identity),
                    {"role": spec.role, "parent": parent,
                     "department": department})
        return agent

    def promote(self, agent_id: str, new_role: str) -> bool:
        if not self.org.hierarchy.contains(agent_id):
            return False
        self.roles.assign(agent_id, new_role)
        self._event("promote", agent_id, {"new_role": new_role})
        return True

    def demote(self, agent_id: str, new_role: str) -> bool:
        if not self.org.hierarchy.contains(agent_id):
            return False
        self.roles.assign(agent_id, new_role)
        self._event("demote", agent_id, {"new_role": new_role})
        return True

    def suspend(self, agent_id: str) -> bool:
        if not self.org.hierarchy.contains(agent_id):
            return False
        self._suspended.add(agent_id)
        self._event("suspend", agent_id, {})
        return True

    def unsuspend(self, agent_id: str) -> bool:
        self._suspended.discard(agent_id)
        self._event("unsuspend", agent_id, {})
        return True

    def is_suspended(self, agent_id: str) -> bool:
        return agent_id in self._suspended

    def replace(self, agent_id: str, new_spec: AgentSpec,
                parent: Optional[str] = None) -> Optional[Agent]:
        """Replace an underperforming agent; retire old, create new."""
        if not self.org.hierarchy.contains(agent_id):
            return None
        self.retire(agent_id)
        return self.create(new_spec, parent=parent,
                           department=self.org.department_of(agent_id))

    def retire(self, agent_id: str,
               reparent_children_to: Optional[str] = None) -> bool:
        if not self.org.hierarchy.contains(agent_id):
            return False
        self._suspended.discard(agent_id)
        ok = self.org.retire_agent(agent_id, reparent_children_to)
        if ok:
            self._event("retire", agent_id,
                        {"reparent_children_to": reparent_children_to})
        return ok

    def events(self) -> list[LifecycleEvent]:
        return list(self._events)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
