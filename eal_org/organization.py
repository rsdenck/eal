"""EAL-ORG: organization engine.

Coordinates departments, teams, agents, roles and hierarchy into a single
dynamic, evolvable organization. This is the EAL-ORG engine: agents and
structure are created and managed by the system itself (via Owner), not
permanently fixed by humans.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .department import Department, Team
from .hierarchy import HierarchyManager
from .roles import Role, RoleManager


@dataclass
class OrganizationSnapshot:
    """Immutable snapshot of the organization (for history/rollback)."""

    org_id: str
    agents: dict[str, str]  # agent_id -> role
    hierarchy: dict[str, object]
    departments: dict[str, object]
    teams: dict[str, dict[str, object]]
    created_at: str


class OrganizationEngine:
    """The EAL-ORG engine.

    Manages:
      - agents and their roles (via RoleManager)
      - hierarchy tree (via HierarchyManager)
      - departments and teams
    """

    def __init__(self) -> None:
        self.hierarchy = HierarchyManager()
        self.roles = RoleManager()
        self.departments: dict[str, Department] = {}
        self.teams: dict[str, Team] = {}
        self.agent_department: dict[str, str] = {}  # agent_id -> dept_id
        self._created_at = self._now()

    # -- agents & roles --------------------------------------------------

    def register_agent(self, agent_id: str,
                       role_name: str = "worker",
                       parent: Optional[str] = None,
                       department: Optional[str] = None) -> bool:
        """Register an agent in the organization.

        Adds to hierarchy (under parent), assigns role, optionally assigns to
        a department.
        """
        if not self.hierarchy.add_agent(agent_id, parent):
            return False
        self.roles.assign(agent_id, role_name)
        if department is not None:
            self.assign_department(agent_id, department)
        return True

    def retire_agent(self, agent_id: str,
                     reparent_children_to: Optional[str] = None) -> bool:
        """Retire an agent; its children are reparented (no orphans)."""
        if not self.hierarchy.contains(agent_id):
            return False
        dept = self.agent_department.pop(agent_id, None)
        if dept is not None:
            self.departments[dept].remove_agent(agent_id)
        self.roles.unassign(agent_id)
        return self.hierarchy.remove_agent(agent_id, reparent_children_to)

    def reparent(self, agent_id: str, new_parent: Optional[str]) -> bool:
        ok = self.hierarchy.reparent(agent_id, new_parent)
        if ok:
            # Move department membership with the agent if it changes roots.
            pass
        return ok

    def assign_department(self, agent_id: str, dept_id: str) -> bool:
        if dept_id not in self.departments:
            return False
        old = self.agent_department.get(agent_id)
        if old == dept_id:
            return True
        if old is not None:
            self.departments[old].remove_agent(agent_id)
        self.agent_department[agent_id] = dept_id
        self.departments[dept_id].add_agent(agent_id)
        return True

    # -- departments & teams --------------------------------------------

    def create_department(self, dept_id: str, name: str,
                          specialization: str) -> bool:
        if dept_id in self.departments:
            return False
        self.departments[dept_id] = Department(
            dept_id=dept_id, name=name, specialization=specialization,
        )
        return True

    def create_team(self, dept_id: str, team_id: str, name: str) -> bool:
        if dept_id not in self.departments:
            return False
        if team_id in self.teams:
            return False
        team = Team(team_id=team_id, name=name)
        self.teams[team_id] = team
        self.departments[dept_id].add_team(team)
        return True

    def assign_team(self, agent_id: str, team_id: str) -> bool:
        if team_id not in self.teams:
            return False
        team = self.teams[team_id]
        # Agent must be in the team's department.
        dept_id = self.agent_department.get(agent_id)
        if dept_id is None or team_id not in self.departments[dept_id].teams:
            return False
        # Remove from any prior team.
        for t in self.teams.values():
            t.remove_member(agent_id)
        team.add_member(agent_id)
        return True

    # -- queries ---------------------------------------------------------

    def agent_role(self, agent_id: str) -> Role | None:
        return self.roles.role_of(agent_id)

    def has_permission(self, agent_id: str, permission: str) -> bool:
        return self.roles.has_permission(agent_id, permission)

    def supervisor(self, agent_id: str) -> Optional[str]:
        return self.hierarchy.parent(agent_id)

    def subordinates(self, agent_id: str) -> list[str]:
        return self.hierarchy.children(agent_id)

    def delegation_path(self, agent_id: str) -> list[str]:
        return self.hierarchy.path_to_root(agent_id)

    def roots(self) -> list[str]:
        return self.hierarchy.roots()

    def department_of(self, agent_id: str) -> Optional[str]:
        return self.agent_department.get(agent_id)

    def snapshot(self) -> OrganizationSnapshot:
        from datetime import datetime, timezone
        return OrganizationSnapshot(
            org_id="eal-org",
            agents=self.roles.assignments(),
            hierarchy=self.hierarchy.snapshot(),
            departments={
                did: {
                    "name": d.name,
                    "specialization": d.specialization,
                    "agents": sorted(d.agents),
                    "teams": list(d.teams.keys()),
                }
                for did, d in self.departments.items()
            },
            teams={
                tid: {
                    "name": t.name,
                    "members": sorted(t.members),
                }
                for tid, t in self.teams.items()
            },
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    @staticmethod
    def _now() -> str:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
