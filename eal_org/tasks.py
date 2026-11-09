"""EAL-ORG: task delegation engine.

Tasks are traceable to their original objective, have an owner/supervisor,
priority, dependencies, deadline, resources, state, result and event history.
Execution is asynchronous and event-driven.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class Task:
    task_id: str
    objective: str
    owner: str  # agent_id responsible
    supervisor: str  # agent_id supervising
    priority: int = 1
    dependencies: list[str] = field(default_factory=list)
    deadline: Optional[str] = None
    resources: dict = field(default_factory=dict)
    status: str = "pending"  # pending, assigned, running, completed, failed
    result: Optional[str] = None
    evidence: list[str] = field(default_factory=list)
    events: list[dict] = field(default_factory=list)

    def add_event(self, kind: str, detail: dict) -> None:
        self.events.append({"kind": kind, "detail": detail,
                            "timestamp": self._now()})

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()


class TaskDelegationEngine:
    """Receives objectives, decomposes into tasks, delegates, and tracks them."""

    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}
        self._counter = 0

    def create_task(self, objective: str, owner: str, supervisor: str,
                    priority: int = 1,
                    dependencies: list[str] | None = None,
                    deadline: Optional[str] = None,
                    resources: dict | None = None) -> str:
        self._counter += 1
        task_id = f"task-{uuid.uuid4().hex[:8]}"
        task = Task(
            task_id=task_id, objective=objective, owner=owner,
            supervisor=supervisor, priority=priority,
            dependencies=list(dependencies or []),
            deadline=deadline, resources=resources or {},
        )
        task.add_event("created", {"owner": owner, "supervisor": supervisor})
        self._tasks[task_id] = task
        return task_id

    def assign(self, task_id: str, owner: str) -> bool:
        task = self._tasks.get(task_id)
        if task is None:
            return False
        task.owner = owner
        task.status = "assigned"
        task.add_event("assigned", {"owner": owner})
        return True

    def start(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if task is None or task.status != "assigned":
            return False
        # Dependencies must be completed.
        for dep in task.dependencies:
            dep_task = self._tasks.get(dep)
            if dep_task is None or dep_task.status != "completed":
                return False
        task.status = "running"
        task.add_event("started", {})
        return True

    def complete(self, task_id: str, result: str,
                 evidence: list[str] | None = None) -> bool:
        task = self._tasks.get(task_id)
        if task is None or task.status != "running":
            return False
        task.status = "completed"
        task.result = result
        task.evidence = list(evidence or [])
        task.add_event("completed", {"result": result})
        return True

    def fail(self, task_id: str, reason: str) -> bool:
        task = self._tasks.get(task_id)
        if task is None:
            return False
        task.status = "failed"
        task.result = None
        task.add_event("failed", {"reason": reason})
        return True

    def get(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)

    def tasks(self) -> dict[str, Task]:
        return dict(self._tasks)

    def pending_or_running(self) -> list[str]:
        return [tid for tid, t in self._tasks.items()
                if t.status in ("pending", "assigned", "running")]

    def failed_tasks(self) -> list[str]:
        return [tid for tid, t in self._tasks.items() if t.status == "failed"]
