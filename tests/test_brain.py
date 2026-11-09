"""Unit tests for EAL-BRAIN (stdlib only)."""

from __future__ import annotations

import unittest

from eal_core.identity import AgentIdentity
from eal_brain import (
    Agent,
    AgentState,
    DeterministicInference,
    ExecutionContext,
    InMemoryStore,
    InternalRepresentation,
    ReferenceLearner,
)


class TestAgentState(unittest.TestCase):
    def test_beliefs_and_increment(self):
        aid = AgentIdentity.generate()
        st = AgentState(agent_id=str(aid))
        st.set_belief("x", 1)
        self.assertEqual(st.get_belief("x"), 1)
        st.increment("msgs")
        self.assertEqual(st.counters["msgs"], 1)
        self.assertEqual(st.step_count, 1)

    def test_snapshot_load(self):
        st = AgentState(agent_id="a")
        st.set_belief("k", "v")
        st.increment("n", 5)
        loaded = AgentState.load(st.snapshot())
        self.assertEqual(loaded.get_belief("k"), "v")
        self.assertEqual(loaded.counters["n"], 5)
        self.assertEqual(loaded.step_count, 1)  # one increment call = one step


class TestInternalRepresentation(unittest.TestCase):
    def test_content_hash(self):
        r = InternalRepresentation(name="r", vector=[0.1, 0.2], symbols=["s1"])
        self.assertFalse(r.is_empty())
        h1 = r.content_hash()
        h2 = InternalRepresentation(name="r", vector=[0.1, 0.2], symbols=["s1"]).content_hash()
        self.assertEqual(h1, h2)
        self.assertNotEqual(h1, InternalRepresentation(name="r", vector=[0.3]).content_hash())

    def test_empty(self):
        self.assertTrue(InternalRepresentation(name="e").is_empty())


class TestInMemoryStore(unittest.TestCase):
    def test_write_read_delete(self):
        m = InMemoryStore()
        m.write("k", "v")
        self.assertTrue(m.contains("k"))
        self.assertEqual(m.read("k"), "v")
        self.assertTrue(m.delete("k"))
        self.assertFalse(m.contains("k"))

    def test_persistent_not_evicted(self):
        m = InMemoryStore(max_short_term=2)
        m.write("a", 1)
        m.write("b", 2)
        m.write("c", 3)  # evicts "a"
        self.assertIsNone(m.read("a"))
        m.write("p", 9, persistent=True)
        m.write("q", 10)  # evicts "b"
        m.write("r", 11)  # evicts "c"
        self.assertEqual(m.read("p"), 9)  # persistent survives eviction
        self.assertIn("p", m.long_term)


class TestExecutionContext(unittest.TestCase):
    def test_isolated_rng(self):
        c1 = ExecutionContext(agent_id="a", seed=5)
        c2 = ExecutionContext(agent_id="b", seed=5)
        # Same seed -> same sequence; independent instances
        self.assertEqual(c1.rng.random(), c2.rng.random())
        c1.advance()
        self.assertEqual(c1.step, 1)
        self.assertEqual(c2.step, 0)


class TestDeterministicInference(unittest.TestCase):
    def test_deterministic(self):
        inf = DeterministicInference(seed=42)
        o1 = inf.infer("hello")
        o2 = inf.infer("hello")
        self.assertEqual(o1, o2)
        self.assertTrue(o1["deterministic"])
        self.assertFalse(inf.supports_gpu())

    def test_different_input_different_output(self):
        inf = DeterministicInference(seed=1)
        self.assertNotEqual(inf.infer("a"), inf.infer("b"))


class TestReferenceLearner(unittest.TestCase):
    def test_update_and_evaluate_separate(self):
        st = AgentState(agent_id="a")
        learner = ReferenceLearner(learning_rate=0.5)
        exp = {"reward": 1.0, "key": "k"}
        learner.update(st, exp)
        self.assertAlmostEqual(st.get_belief("k"), 0.5)
        # evaluate does not change state
        metrics = learner.evaluate(st, {"reward": 0.0, "key": "k"})
        self.assertAlmostEqual(st.get_belief("k"), 0.5)
        self.assertIn("error", metrics)


class TestAgent(unittest.TestCase):
    def test_independent_agents(self):
        a = Agent(AgentIdentity.generate(), seed=1)
        b = Agent(AgentIdentity.generate(), seed=2)
        a.infer("x")
        b.observe("k", "v")
        self.assertEqual(a.state.counters.get("inferences"), 1)
        self.assertEqual(b.state.counters.get("observations"), 1)
        # Independent memory
        self.assertFalse(a.memory.contains("k"))
        self.assertEqual(b.memory.read("k"), "v")

    def test_learn_then_snapshot(self):
        agent = Agent(AgentIdentity.generate(), seed=0)
        agent.learn({"reward": 1.0, "key": "k"})
        snap = agent.snapshot()
        self.assertEqual(snap["identity"], str(agent.identity))
        self.assertAlmostEqual(snap["state"]["beliefs"]["k"], 0.1)
        self.assertEqual(snap["context"]["step"], 1)


if __name__ == "__main__":
    unittest.main()
