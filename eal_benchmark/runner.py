"""EAL-BENCHMARK: reproducible experiment runner and baseline comparison.

Runs benchmarks against conventional baselines (random communication,
unguided search) and records whether EAL shows measurable improvement. All
inputs and outputs are recorded for reproducibility; no synthetic results.
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass
from typing import Any

from eal_cl import Channel
from eal_core.config import Config
from eal_core.experiment import ExperimentRecord, ExperimentResult
from eal_core.identity import AgentIdentity
from eal_learning import MultiAgentLearningLoop, ReferenceRL

from .metrics import MetricRegistry, MetricResult


@dataclass
class BaselineResult:
    name: str
    metrics: dict[str, float]


@dataclass
class BenchmarkResult:
    """Complete benchmark outcome.

    Attributes:
        benchmark_id: Content-stable identifier.
        eal_metrics: Metrics measured for the EAL system.
        baselines: Baseline results compared against.
        comparison: metric -> {"eal": v, "baseline": v, "improved": bool}.
        accepted: Whether the benchmark hypothesis was accepted.
    """

    benchmark_id: str
    eal_metrics: dict[str, MetricResult]
    baselines: list[BaselineResult]
    comparison: dict[str, dict[str, Any]]
    accepted: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "benchmark_id": self.benchmark_id,
            "eal_metrics": {k: v.to_dict() for k, v in self.eal_metrics.items()},
            "baselines": [{"name": b.name, "metrics": b.metrics}
                          for b in self.baselines],
            "comparison": self.comparison,
            "accepted": self.accepted,
        }


class BenchmarkRunner:
    """Runs EAL benchmarks and compares against conventional baselines."""

    def __init__(self, registry: MetricRegistry | None = None,
                 rng: random.Random | None = None,
                 config: Config | None = None) -> None:
        self.registry = registry or MetricRegistry()
        self.rng = rng or random.Random()
        self.config = config or Config()
        self._experiments: list[ExperimentRecord] = []

    def _bench_id(self, kind: str, seed: int, rounds: int) -> str:
        payload = json.dumps(
            {"kind": kind, "seed": seed, "rounds": rounds},
            sort_keys=True,
        ).encode("utf-8")
        return "bench-" + hashlib.sha256(payload).hexdigest()[:32]

    def run_communication_benchmark(self, agents,
                                    rounds: int = 200,
                                    concepts: list[Any] | None = None,
                                    seed: int = 0) -> BenchmarkResult:
        """Benchmark communication: EAL vs random-guessing baseline."""
        rng = random.Random(seed)
        if concepts is None:
            concepts = [f"c-{i}" for i in range(6)]

        # EAL: multi-agent learning loop.
        loop = MultiAgentLearningLoop(list(agents),
                                      algorithm=ReferenceRL(seed=seed),
                                      rng=rng)
        result = loop.run_experiment(
            hypothesis="EAL communication beats random baseline",
            rounds=rounds, concepts=concepts, seed=seed,
        )

        eal_metrics: dict[str, MetricResult] = {
            "communication_success": self.registry.compute(
                "communication_success",
                int(result.evaluation_success * rounds), rounds),
            "learning_speed": self.registry.compute(
                "learning_speed", [result.training_success]),
            "generalization": self.registry.compute(
                "generalization", result.training_success,
                result.evaluation_success),
        }

        # Baseline: random guessing among concepts.
        baseline_value = 1.0 / len(concepts)
        baselines = [BaselineResult(
            name="random_guessing",
            metrics={"communication_success": baseline_value,
                     "learning_speed": baseline_value,
                     "generalization": baseline_value},
        )]

        comparison: dict[str, dict[str, Any]] = {}
        all_improved = True
        for name, metric in eal_metrics.items():
            base = baselines[0].metrics.get(name, baseline_value)
            improved = metric.value > base
            comparison[name] = {
                "eal": metric.value,
                "baseline": base,
                "improved": improved,
            }
            metric.improved = improved
            metric.baseline = base
            if not improved:
                all_improved = False

        benchmark_id = self._bench_id("communication", seed, rounds)
        accepted = all_improved and result.accepted

        record = self._experiment_record(
            benchmark_id, "EAL communication beats random baseline", seed,
            eal_metrics, baselines, comparison, accepted,
        )
        self._experiments.append(record)

        return BenchmarkResult(
            benchmark_id=benchmark_id,
            eal_metrics=eal_metrics,
            baselines=baselines,
            comparison=comparison,
            accepted=accepted,
        )

    def _experiment_record(self, benchmark_id: str, hypothesis: str,
                           seed: int, eal_metrics, baselines, comparison,
                           accepted) -> ExperimentRecord:
        return ExperimentRecord(
            experiment_id=benchmark_id,
            hypothesis=hypothesis,
            config=self.config.with_seed(seed),
            code_version="eal-benchmark/1.0",
            seed=seed,
            baseline="; ".join(b.name for b in baselines),
            results=ExperimentResult(
                communication_success=next(
                    (m.value for m in eal_metrics.values()
                     if m.name == "communication_success"), None),
            ),
            limitations="CPU-only reference; no NVIDIA backend",
            decision="accept" if accepted else "reject",
        ).finalize()
