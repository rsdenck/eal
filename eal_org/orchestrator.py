"""EAL-ORG: command & control engine (EAL-ORCHESTRATOR).

Receives objectives, decomposes them into tasks, identifies dependencies,
selects responsible agents, delegates, tracks execution, validates delivery,
reassigns on failure, and reports results. Event-driven and asynchronous.
"""

from __future__ import annotations

from typing import Optional

from eal_org.factory import AgentSpec
from eal_org.lifecycle import AgentLifecycleManager
from eal_org.organization import OrganizationEngine
from eal_org.tasks import TaskDelegationEngine


class CommandControlEngine:
    """EAL-ORCHESTRATOR: original command & control mechanism."""

    def __init__(self, organization: OrganizationEngine,
                 lifecycle: AgentLifecycleManager,
                 tasks: TaskDelegationEngine) -> None:
        self.org = organization
        self.lifecycle = lifecycle
        self.tasks = tasks
        self._objectives: list[dict] = []

    def receive_objective(self, objective: str, requester: str) -> str:
        """Register a top-level objective. Returns objective id."""
        oid = f"obj-{len(self._objectives)+1}"
        self._objectives.append({
            "id": oid, "objective": objective, "requester": requester,
            "status": "open", "tasks": [],
        })
        return oid

    def decompose_and_delegate(self, objective_id: str) -> list[str]:
        """Decompose an objective into tasks and delegate them.

        Selection of responsible agents is based on role permissions and
        current load; delegation is traceable to the objective.
        """
        obj = next((o for o in self._objectives if o["id"] == objective_id),
                   None)
        if obj is None:
            return []
        # Decompose heuristically into sub-tasks (original decomposition).
        subtasks = self._decompose(obj["objective"])
        task_ids = []
        for i, st in enumerate(subtasks):
            owner = self._select_agent("worker")
            supervisor = self._select_agent("supervisor") or owner
            tid = self.tasks.create_task(
                objective=st, owner=owner, supervisor=supervisor,
                priority=1 if i == 0 else 2,
            )
            self.tasks.assign(tid, owner)
            self.tasks.start(tid)
            task_ids.append(tid)
        obj["tasks"] = task_ids
        obj["status"] = "delegated"
        return task_ids

    def _decompose(self, objective: str) -> list[str]:
        """Original task decomposition: split objective into steps."""
        # Simple keyword-agnostic decomposition for demonstration.
        return [f"step 1: analyze '{objective}'",
                f"step 2: execute '{objective}'",
                f"step 3: report result of '{objective}'"]

    def _select_agent(self, role_name: str) -> Optional[str]:
        candidates = self.org.roles.agents_with_role(role_name)
        if not candidates:
            return None
        # Pick the candidate with fewest pending tasks (least loaded).
        best = None
        best_load = None
        for aid in candidates:
            load = sum(1 for t in self.tasks.tasks().values()
                       if t.owner == aid and t.status in ("pending", "running"))
            if best_load is None or load < best_load:
                best, best_load = aid, load
        return best

    def track(self) -> dict[str, object]:
        """Return current execution tracking state."""
        return {
            "objectives": len(self._objectives),
            "tasks": len(self.tasks.tasks()),
            "pending": len(self.tasks.pending_or_running()),
            "failed": len(self.tasks.failed_tasks()),
            "completed": sum(1 for t in self.tasks.tasks().values()
                             if t.status == "completed"),
        }

    def reassign_failed(self) -> int:
        """Reassign failed tasks to other available workers (failure mgmt)."""
        reassigned = 0
        for tid in list(self.tasks.failed_tasks()):
            task = self.tasks.get(tid)
            if task is None:
                continue
            new_owner = self._select_agent("worker")
            if new_owner is not None and new_owner != task.owner:
                self.tasks.assign(tid, new_owner)
                self.tasks.start(tid)
                reassigned += 1
        return reassigned
