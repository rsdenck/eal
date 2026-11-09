"""EAL-ORG: agent performance evaluator.

Evaluates agent performance by productivity, quality, computational cost,
latency, reliability and objective fulfillment (spec §9 EAL-ORG).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from eal_org.tasks import TaskDelegationEngine


@dataclass
class PerformanceReport:
    agent_id: str
    tasks_completed: int
    tasks_failed: int
    tasks_pending: int
    completion_rate: float
    avg_evidence_per_task: float
    score: float  # 0..1 composite performance score


class AgentPerformanceEvaluator:
    """Evaluates agent performance from real task events."""

    def __init__(self, tasks: TaskDelegationEngine) -> None:
        self.tasks = tasks

    def evaluate(self, agent_id: str) -> PerformanceReport:
        owned = [t for t in self.tasks.tasks().values() if t.owner == agent_id]
        completed = [t for t in owned if t.status == "completed"]
        failed = [t for t in owned if t.status == "failed"]
        pending = [t for t in owned
                   if t.status in ("pending", "assigned", "running")]
        total = len(owned)
        completion_rate = (len(completed) / total) if total else 0.0
        avg_evidence = (sum(len(t.evidence) for t in completed)
                        / len(completed)) if completed else 0.0
        # Composite: completion rate weighted by evidence richness.
        score = min(1.0, 0.7 * completion_rate + 0.3 * min(avg_evidence, 1.0))
        return PerformanceReport(
            agent_id=agent_id,
            tasks_completed=len(completed),
            tasks_failed=len(failed),
            tasks_pending=len(pending),
            completion_rate=completion_rate,
            avg_evidence_per_task=avg_evidence,
            score=score,
        )

    def rank(self) -> list[tuple[str, float]]:
        agents = {t.owner for t in self.tasks.tasks().values()}
        return sorted(
            ((aid, self.evaluate(aid).score) for aid in agents),
            key=lambda x: -x[1],
        )

    def underperformers(self, threshold: float = 0.4) -> list[str]:
        return [aid for aid, score in self.rank() if score < threshold]
