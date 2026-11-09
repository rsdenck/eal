"""EAL-BENCHMARK: measurement metrics.

All metrics are deterministic functions of real observed data. No synthetic
data is ever presented as experimental results (spec §3 EAL-BENCHMARK).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class MetricResult:
    name: str
    value: float
    baseline: float | None = None
    unit: str = ""
    improved: bool | None = None  # None = not compared / not applicable

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "baseline": self.baseline,
            "unit": self.unit,
            "improved": self.improved,
        }


# -- communication metrics -------------------------------------------------

def communication_success(correct: int, total: int) -> float:
    """Fraction of messages decoded correctly by the receiver."""
    return correct / total if total else 0.0


def semantic_preservation(preserved: int, total: int) -> float:
    """Fraction of messages whose meaning was preserved end-to-end."""
    return preserved / total if total else 0.0


def bits_per_message(message_length_bits: int, num_messages: int) -> float:
    """Average bits transmitted per message."""
    return message_length_bits / num_messages if num_messages else 0.0


def message_length_total(lengths: list[int]) -> float:
    """Average message length (symbols)."""
    return sum(lengths) / len(lengths) if lengths else 0.0


def latency_average(latencies: list[float]) -> float:
    """Average end-to-end latency in seconds."""
    return sum(latencies) / len(latencies) if latencies else 0.0


def computational_cost(cost_units: float, messages: int) -> float:
    """Computational cost per message (arbitrary cost units)."""
    return cost_units / messages if messages else 0.0


# -- language quality metrics ----------------------------------------------

def generalization(train_success: float, eval_success: float) -> float:
    """How well learning generalizes (eval vs train success)."""
    return eval_success


def vocabulary_stability(current: set, prior: set) -> float:
    """Overlap of vocabulary between two versions (1.0 = identical)."""
    union = current | prior
    if not union:
        return 1.0
    return len(current & prior) / len(union)


def grammar_compositionality(rules: list[tuple[str, ...]]) -> float:
    """Proxy for grammar compositionality: fraction of rules with >1 symbol."""
    if not rules:
        return 0.0
    composed = sum(1 for r in rules if len(r) > 1)
    return composed / len(rules)


def learning_speed(success_curve: list[float]) -> float:
    """Learning speed: average success over the curve (higher = faster)."""
    return sum(success_curve) / len(success_curve) if success_curve else 0.0


def cross_agent_interoperability(pair_successes: dict[tuple[str, str], float]) -> float:
    """Average cross-agent communication success across agent pairs."""
    if not pair_successes:
        return 0.0
    return sum(pair_successes.values()) / len(pair_successes)


# -- programming language metrics ------------------------------------------

def pl_expressiveness(programs_compiled: int, programs_total: int) -> float:
    """Fraction of EAL-PL programs that compile and run."""
    return programs_compiled / programs_total if programs_total else 0.0


def compiler_correctness(correct_outputs: int, total_runs: int) -> float:
    """Fraction of compiler runs producing correct output."""
    return correct_outputs / total_runs if total_runs else 0.0


# -- registry --------------------------------------------------------------

MetricFunc = Callable[..., float]


class MetricRegistry:
    """Registry of named metric functions."""

    def __init__(self) -> None:
        self._metrics: dict[str, MetricFunc] = {}
        for name, func in _default_metrics().items():
            self.register(name, func)

    def register(self, name: str, func: MetricFunc) -> None:
        self._metrics[name] = func

    def compute(self, name: str, *args, **kwargs) -> MetricResult:
        if name not in self._metrics:
            raise KeyError(f"unknown metric {name!r}")
        value = float(self._metrics[name](*args, **kwargs))
        return MetricResult(name=name, value=value, unit="")


def _default_metrics() -> dict[str, MetricFunc]:
    return {
        "communication_success": communication_success,
        "semantic_preservation": semantic_preservation,
        "bits_per_message": bits_per_message,
        "message_length": message_length_total,
        "latency": latency_average,
        "computational_cost": computational_cost,
        "generalization": generalization,
        "vocabulary_stability": vocabulary_stability,
        "grammar_compositionality": grammar_compositionality,
        "learning_speed": learning_speed,
        "cross_agent_interoperability": cross_agent_interoperability,
        "pl_expressiveness": pl_expressiveness,
        "compiler_correctness": compiler_correctness,
    }
