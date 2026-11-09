"""Unit tests for EAL-LEARNING (stdlib only)."""

from __future__ import annotations

import random
import unittest

from eal_core.config import Config
from eal_core.identity import AgentIdentity
from eal_brain import Agent
from eal_learning import (Experience, MultiAgentLearningLoop, ReferenceRL,
                          RLAlgorithm)


class _TwoAgents:
    def __init__(self, seed: int = 0) -> None:
        self.a = Agent(AgentIdentity.generate(), seed=seed)
        self.b = Agent(AgentIdentity.generate(), seed=seed + 1)


class TestReferenceRL(unittest.TestCase):
    def test_update_and_evaluate_separate(self):
        agents = _TwoAgents(seed=0)
        rl = ReferenceRL(seed=1)
        exp = [Experience(
            agent_id=str(agents.a.identity), concept="c-0", symbols=("s1",),
            reward=1.0, round=0,
        )]
        metrics = rl.update(agents.a, exp)
        self.assertIn("avg_reward", metrics)
        # evaluate must not change training outcome metrics structure
        em = rl.evaluate(agents.a, exp)
        self.assertIn("success_rate", em)

    def test_evaluate_empty(self):
        rl = ReferenceRL()
        agent = Agent(AgentIdentity.generate())
        self.assertEqual(rl.evaluate(agent, []), {"success_rate": 0.0,
                                                   "experiences": 0.0})


class TestMultiAgentLearningLoop(unittest.TestCase):
    def test_run_experiment_two_agents(self):
        agents = _TwoAgents(seed=0)
        loop = MultiAgentLearningLoop([agents.a, agents.b], rng=random.Random(0))
        result = loop.run_experiment(
            hypothesis="two agents learn to communicate",
            rounds=60, seed=3,
        )
        self.assertEqual(result.agents, 2)
        self.assertEqual(result.rounds, 60)
        self.assertGreaterEqual(result.training_success, 0.0)
        self.assertLessEqual(result.training_success, 1.0)
        self.assertGreaterEqual(result.evaluation_success, 0.0)
        self.assertLessEqual(result.evaluation_success, 1.0)
        self.assertIn(result.accepted, (True, False))

    def test_deterministic_given_seed(self):
        def run(seed):
            agents = _TwoAgents(seed=seed)
            loop = MultiAgentLearningLoop([agents.a, agents.b],
                                          rng=random.Random(0))
            return loop.run_experiment("h", rounds=40, seed=seed)
        r1 = run(5)
        r2 = run(5)
        self.assertEqual(r1.training_success, r2.training_success)
        self.assertEqual(r1.evaluation_success, r2.evaluation_success)
        self.assertEqual(r1.accepted, r2.accepted)

    def test_single_agent_degenerate(self):
        agent = Agent(AgentIdentity.generate())
        loop = MultiAgentLearningLoop([agent], rng=random.Random(0))
        result = loop.run_experiment("solo", rounds=10, seed=0)
        self.assertEqual(result.training_success, 0.0)
        self.assertEqual(result.evaluation_success, 0.0)

    def test_experiment_recorded(self):
        agents = _TwoAgents(seed=0)
        loop = MultiAgentLearningLoop([agents.a, agents.b],
                                      rng=random.Random(0))
        loop.run_experiment("h", rounds=20, seed=1)
        self.assertEqual(len(loop.experiments()), 1)
        self.assertIn(loop.experiments()[0].decision, ("accept", "reject"))

    def test_config_with_seed(self):
        cfg = Config(seed=5, modules={"eal_core", "eal_learning"})
        cfg2 = cfg.with_seed(9)
        self.assertEqual(cfg2.seed, 9)
        self.assertEqual(cfg2.modules, {"eal_core", "eal_learning"})


if __name__ == "__main__":
    unittest.main()
