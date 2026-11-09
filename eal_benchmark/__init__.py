"""EAL-BENCHMARK package.

Public API:
    MetricRegistry, MetricResult        # measurement metrics
    communication_success, semantic_preservation, bits_per_message,
    message_length, latency_average, computational_cost, generalization,
    vocabulary_stability, grammar_compositionality, learning_speed,
    cross_agent_interoperability, pl_expressiveness, compiler_correctness
    BaselineResult, BenchmarkResult     # benchmark outcome
    BenchmarkRunner                     # runs benchmarks vs baselines

All metrics are deterministic functions of real observed data. Conventional
baselines (e.g. random guessing) are compared against EAL results; no
synthetic data is ever presented as experimental results.
"""

from .metrics import (MetricRegistry, MetricResult,
                      communication_success, semantic_preservation,
                      bits_per_message, message_length_total as message_length,
                      latency_average, computational_cost, generalization,
                      vocabulary_stability, grammar_compositionality,
                      learning_speed, cross_agent_interoperability,
                      pl_expressiveness, compiler_correctness)
from .runner import BenchmarkResult, BenchmarkRunner, BaselineResult

__all__ = [
    "MetricRegistry",
    "MetricResult",
    "BaselineResult",
    "BenchmarkResult",
    "BenchmarkRunner",
    "communication_success",
    "semantic_preservation",
    "bits_per_message",
    "message_length",
    "latency_average",
    "computational_cost",
    "generalization",
    "vocabulary_stability",
    "grammar_compositionality",
    "learning_speed",
    "cross_agent_interoperability",
    "pl_expressiveness",
    "compiler_correctness",
]
