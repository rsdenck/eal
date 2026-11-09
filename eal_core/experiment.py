"""Reproducible experiment record for EAL-CORE.

Every significant change must include: research hypothesis, implementation,
experiment configuration, baseline comparison, reproducible execution,
evaluation results, limitations, and an accept/reject/investigate decision.

Experiment records are stored under ``experiments/`` as JSON and are never
mutated after being finalized. Stable language versions are archived before
any mutation so rollback can restore the prior state byte-for-byte.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any

from .config import Config


@dataclass
class ExperimentResult:
    """Outcome measurements for an experiment.

    All fields are optional until measured; absence means "not measured" rather
    than "zero". Never fabricate values.
    """

    communication_success: float | None = None
    semantic_preservation: float | None = None
    bits_per_message: float | None = None
    message_length: int | None = None
    latency_seconds: float | None = None
    computational_cost: float | None = None
    generalization: float | None = None
    vocabulary_stability: float | None = None
    grammar_compositionality: float | None = None
    learning_speed: float | None = None
    cross_agent_interoperability: float | None = None
    pl_expressiveness: float | None = None
    compiler_correctness: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class ExperimentRecord:
    """A complete, reproducible experiment record.

    Attributes:
        experiment_id: Content-stable identifier (set at finalization).
        hypothesis: The research hypothesis under test.
        config: Snapshot of the :class:`~eal_core.config.Config` used.
        code_version: Git SHA or equivalent identifying the code under test.
        seed: Random seed used.
        baseline: Description of the baseline compared against.
        results: Measured outcomes (None until the experiment runs).
        limitations: Known limitations of the experiment.
        decision: One of ``accept``, ``reject``, ``investigate_further``.
        created_at / finalized_at: UTC timestamps.
    """

    experiment_id: str
    hypothesis: str
    config: Config
    code_version: str
    seed: int
    baseline: str
    results: ExperimentResult | None = None
    limitations: str = ""
    decision: str = "investigate_further"
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    finalized_at: str | None = None

    VALID_DECISIONS = ("accept", "reject", "investigate_further")

    def __post_init__(self) -> None:
        if self.decision not in self.VALID_DECISIONS:
            raise ValueError(
                f"decision must be one of {self.VALID_DECISIONS}, "
                f"got {self.decision!r}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "hypothesis": self.hypothesis,
            "config": self.config.to_dict(),
            "code_version": self.code_version,
            "seed": self.seed,
            "baseline": self.baseline,
            "results": self.results.to_dict() if self.results else None,
            "limitations": self.limitations,
            "decision": self.decision,
            "created_at": self.created_at,
            "finalized_at": self.finalized_at,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExperimentRecord":
        config = Config.from_dict(data["config"])
        results = None
        if data.get("results") is not None:
            results = ExperimentResult(**data["results"])
        return cls(
            experiment_id=data["experiment_id"],
            hypothesis=data["hypothesis"],
            config=config,
            code_version=data["code_version"],
            seed=data["seed"],
            baseline=data["baseline"],
            results=results,
            limitations=data.get("limitations", ""),
            decision=data.get("decision", "investigate_further"),
            created_at=data.get("created_at", ""),
            finalized_at=data.get("finalized_at"),
        )

    def finalize(self, experiment_id: str | None = None) -> "ExperimentRecord":
        """Mark the experiment as finalized; returns a finalized copy.

        If ``experiment_id`` is not provided, the record's existing id is kept
        (callers may pre-set a content-stable id before finalizing).
        """
        import hashlib

        if experiment_id is None and not self.experiment_id:
            payload = self.to_json().encode("utf-8")
            experiment_id = hashlib.sha256(payload).hexdigest()[:32]
        resolved_id = experiment_id or self.experiment_id
        finalized = ExperimentRecord(
            experiment_id=resolved_id,
            hypothesis=self.hypothesis,
            config=self.config,
            code_version=self.code_version,
            seed=self.seed,
            baseline=self.baseline,
            results=self.results,
            limitations=self.limitations,
            decision=self.decision,
            created_at=self.created_at,
        )
        finalized.finalized_at = datetime.now(timezone.utc).isoformat()
        return finalized
