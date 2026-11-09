"""EAL-ORG: autonomous organization framework.

Role-based permissions. A Role defines a named set of permissions; agents are
assigned roles within the organization. Roles are original to EAL and not
derived from any external framework.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Role:
    """An organizational role with a defined permission scope.

    Attributes:
        name: Role name (e.g. "owner", "supervisor", "worker", "researcher").
        permissions: Set of permission strings granted to this role.
        description: Human-readable description.
    """

    name: str
    permissions: frozenset[str] = field(default_factory=frozenset)
    description: str = ""

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions


# Default role templates (original to EAL).
DEFAULT_ROLES: dict[str, Role] = {
    "owner": Role(
        name="owner",
        permissions={
            "create_agent", "create_department", "create_team",
            "delegate_task", "supervise", "reorganize", "retire_agent",
            "set_policy", "view_audit", "manage_resources",
        },
        description="Top-level executive role; interprets objectives and "
        "organizes the workforce.",
    ),
    "supervisor": Role(
        name="supervisor",
        permissions={
            "create_worker", "delegate_task", "supervise",
            "evaluate_performance", "view_team",
        },
        description="Coordinates a team of workers.",
    ),
    "worker": Role(
        name="worker",
        permissions={
            "execute_task", "report_result", "view_own_tasks",
        },
        description="Executes delegated tasks.",
    ),
    "researcher": Role(
        name="researcher",
        permissions={
            "propose_experiment", "evaluate_result", "view_research",
        },
        description="Runs research experiments and reports findings.",
    ),
}


class RoleManager:
    """Manages organizational roles and agent role assignments."""

    def __init__(self) -> None:
        self._roles: dict[str, Role] = dict(DEFAULT_ROLES)
        self._assignments: dict[str, str] = {}  # agent_id -> role name

    def register_role(self, role: Role) -> None:
        self._roles[role.name] = role

    def get_role(self, name: str) -> Role | None:
        return self._roles.get(name)

    def assign(self, agent_id: str, role_name: str) -> bool:
        if role_name not in self._roles:
            return False
        self._assignments[agent_id] = role_name
        return True

    def unassign(self, agent_id: str) -> bool:
        return self._assignments.pop(agent_id, None) is not None

    def role_of(self, agent_id: str) -> Role | None:
        name = self._assignments.get(agent_id)
        if name is None:
            return None
        return self._roles.get(name)

    def has_permission(self, agent_id: str, permission: str) -> bool:
        role = self.role_of(agent_id)
        return role is not None and role.has_permission(permission)

    def agents_with_role(self, role_name: str) -> list[str]:
        return [aid for aid, rn in self._assignments.items() if rn == role_name]

    def assignments(self) -> dict[str, str]:
        return dict(self._assignments)
