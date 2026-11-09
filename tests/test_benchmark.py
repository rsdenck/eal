"""Unit tests for EAL-BENCHMARK (stdlib only)."""

from __future__ import annotations

import random
import unittest

from eal_core.config import Config
from eal_core.identity import AgentIdentity
from eal_brain import Agent
from eal_benchmark import (BenchmarkRunner, MetricRegistry,
                           communication_success, semantic_preservation,
                           vocabulary_stability, compiler_correctness,
                           pl_expressiveness, MetricResult)
from eal_learning import ReferenceRL


class TestMetrics(unittest.TestCase):
    def test_communication_success(self):
        self.assertEqual(communication_success(8, 10), 0.8)
        self.assertEqual(communication_success(0, 10), 0.0)
        self.assertEqual(communication_success(0, 0), 0.0)

    def test_semantic_preservation(self):
        self.assertEqual(semantic_preservation(5, 5), 1.0)

    def test_vocabulary_stability(self):
        self.assertEqual(vocabulary_stability({"a", "b"}, {"a", "b"}), 1.0)
        self.assertEqual(vocabulary_stability({"a"}, {"b"}), 0.0)
        self.assertEqual(vocabulary_stability(set(), set()), 1.0)

    def test_compiler_correctness(self):
        self.assertEqual(compiler_correctness(9, 10), 0.9)

    def test_pl_expressiveness(self):
        self.assertEqual(pl_expressiveness(8, 10), 0.8)

    def test_metric_result_dict(self):
        m = MetricResult(name="x", value=0.5, baseline=0.3, unit="ratio",
                         improved=True)
        d = m.to_dict()
        self.assertEqual(d["value"], 0.5)
        self.assertTrue(d["improved"])

    def test_registry_compute(self):
        reg = MetricRegistry()
        m = reg.compute("communication_success", 4, 5)
        self.assertEqual(m.value, 0.8)
        self.assertEqual(m.name, "communication_success")

    def test_registry_unknown(self):
        reg = MetricRegistry()
        with self.assertRaises(KeyError):
            reg.compute("nonexistent", 1)


class TestBenchmarkRunner(unittest.TestCase):
    def _two_agents(self, seed=0):
        return [Agent(AgentIdentity.generate(), seed=seed),
                Agent(AgentIdentity.generate(), seed=seed + 1)]

    def test_run_communication_benchmark(self):
        agents = self._two_agents(seed=1)
        runner = BenchmarkRunner(rng=random.Random(0))
        result = runner.run_communication_benchmark(agents, rounds=40, seed=2)
        self.assertIsNotNone(result.benchmark_id)
        self.assertIn("communication_success", result.eal_metrics)
        self.assertGreaterEqual(len(result.baselines), 1)
        self.assertIn(result.accepted, (True, False))
        self.assertGreaterEqual(len(result.comparison), 1)

    def test_deterministic(self):
        def run(seed):
            agents = self._two_agents(seed=seed)
            runner = BenchmarkRunner(rng=random.Random(0))
            return runner.run_communication_benchmark(agents, rounds=30, seed=seed)
        r1 = run(7)
        r2 = run(7)
        self.assertEqual(r1.benchmark_id, r2.benchmark_id)
        self.assertEqual(r1.eal_metrics["communication_success"].value,
                         r2.eal_metrics["communication_success"].value)
        self.assertEqual(r1.accepted, r2.accepted)

    def test_comparison_has_baseline(self):
        agents = self._two_agents(seed=3)
        runner = BenchmarkRunner(rng=random.Random(0))
        result = runner.run_communication_benchmark(agents, rounds=30, seed=4)
        for name, comp in result.comparison.items():
            self.assertIn("eal", comp)
            self.assertIn("baseline", comp)
            self.assertIn("improved", comp)

    def test_config_with_seed(self):
        cfg = Config(seed=1, modules={"eal_core", "eal_benchmark"})
        cfg2 = cfg.with_seed(2)
        self.assertEqual(cfg2.seed, 2)


if __name__ == "__main__":
    unittest.main()
