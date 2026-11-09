"""EAL-ORG: governance & policy engine + organizational audit log.

Security boundaries (spec §11 EAL-ORG):
- Privileged changes to security policies, credentials and fundamental
  permissions require external approval (simulated via approval flag).
- Distinguish operational autonomy from administrative authority.
- All organizational changes are recorded in an append-only audit log.
- Configuration limits: max concurrent agents, resource budgets, recursion
  limits for subagent creation, delegation cycle detection, timeouts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class AuditEntry:
    kind: str
    actor: str
    target: str
    action: str
    timestamp: str
    approved: bool = False
    detail: dict = field(default_factory=dict)


class GovernancePolicyEngine:
    """Enforces governance and security boundaries."""

    def __init__(self) -> None:
        # Configurable limits (spec §11).
        self.max_concurrent_agents = 256
        self.max_agent_creation_recursion = 5
        self.delegation_max_depth = 10
        self.task_timeout_seconds = 3600
        # Privileged actions requiring external approval.
        self.privileged_actions = {
            "set_policy", "manage_resources", "retire_agent",
            "reorganize", "create_department",
        }

    def requires_approval(self, action: str) -> bool:
        return action in self.privileged_actions

    def approve(self, action: str, actor: str,
                externally_approved: bool) -> bool:
        """Grant external approval for a privileged action.

        Returns True if the action is now permitted.
        """
        if not self.requires_approval(action):
            return True
        return bool(externally_approved)

    def check_limits(self, current_agents: int,
                     creation_depth: int) -> tuple[bool, str]:
        if current_agents >= self.max_concurrent_agents:
            return False, f"max concurrent agents ({self.max_concurrent_agents}) reached"
        if creation_depth > self.max_agent_creation_recursion:
            return False, f"agent creation recursion depth ({creation_depth}) exceeds limit"
        return True, "ok"


class OrganizationalAuditLog:
    """Append-only, immutable audit log of all organizational changes."""

    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []

    def record(self, kind: str, actor: str, target: str, action: str,
               approved: bool = False,
               detail: dict | None = None) -> AuditEntry:
        entry = AuditEntry(
            kind=kind, actor=actor, target=target, action=action,
            timestamp=self._now(), approved=approved,
            detail=dict(detail or {}),
        )
        self._entries.append(entry)
        return entry

    def entries(self) -> list[AuditEntry]:
        return list(self._entries)

    def entries_for(self, agent_id: str) -> list[AuditEntry]:
        return [e for e in self._entries if e.actor == agent_id
                or e.target == agent_id]

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
