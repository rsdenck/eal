"""Unit tests for EAL-CORE (stdlib only)."""

from __future__ import annotations

import json
import unittest

from eal_core import (
    AgentIdentity,
    AgentRegistry,
    AgentRecord,
    Config,
    EALCore,
    Event,
    EventBus,
    ExperimentRecord,
    ExperimentResult,
)


class TestAgentIdentity(unittest.TestCase):
    def test_generate_unique(self):
        a = AgentIdentity.generate()
        b = AgentIdentity.generate()
        self.assertNotEqual(a.value, b.value)

    def test_immutable(self):
        a = AgentIdentity.generate()
        with self.assertRaises(Exception):
            a.value = "changed"

    def test_empty_rejected(self):
        with self.assertRaises(ValueError):
            AgentIdentity(value="")


class TestConfig(unittest.TestCase):
    def test_defaults_valid(self):
        cfg = Config()
        cfg.validate()
        self.assertEqual(cfg.log_level, "INFO")
        self.assertEqual(cfg.seed, 0)

    def test_invalid_log_level(self):
        with self.assertRaises(ValueError):
            Config(log_level="VERBOSE")

    def test_roundtrip_json(self):
        cfg = Config(experiment_name="exp-1", seed=42, modules={"eal_core", "eal_cl"})
        data = json.loads(cfg.to_json())
        cfg2 = Config.from_json(json.dumps(data))
        self.assertEqual(cfg2.experiment_name, "exp-1")
        self.assertEqual(cfg2.seed, 42)
        self.assertEqual(cfg2.modules, {"eal_core", "eal_cl"})

    def test_missing_eal_core(self):
        with self.assertRaises(ValueError):
            Config(modules={"eal_cl"})


class TestEventBus(unittest.TestCase):
    def test_publish_delivers_to_subscriber(self):
        bus = EventBus()
        received = []

        def handler(event: Event):
            received.append(event)

        bus.subscribe("agent.registered", handler)
        event = bus.publish("agent.registered", {"identity": "abc"})

        self.assertEqual(len(received), 1)
        self.assertIs(received[0], event)
        self.assertEqual(event.type, "agent.registered")
        self.assertEqual(event.payload["identity"], "abc")
        self.assertIsNotNone(event.timestamp)

    def test_wildcard_subscriber(self):
        bus = EventBus()
        received = []
        bus.subscribe("*", lambda e: received.append(e))
        bus.publish("a", {"x": 1})
        bus.publish("b", {"x": 2})
        self.assertEqual(len(received), 2)

    def test_history_filter(self):
        bus = EventBus()
        bus.publish("a", {})
        bus.publish("b", {})
        bus.publish("a", {})
        self.assertEqual(len(bus.history("a")), 2)
        self.assertEqual(len(bus.history()), 3)

    def test_subscriber_failure_does_not_break_bus(self):
        bus = EventBus()
        calls = []

        def bad(event: Event):
            raise RuntimeError("boom")

        def good(event: Event):
            calls.append(event)

        bus.subscribe("x", bad)
        bus.subscribe("x", good)
        bus.publish("x", {})
        self.assertEqual(len(calls), 1)
        # an error event was recorded
        self.assertTrue(any(e.type == "subscriber.error" for e in bus.history()))


class TestAgentRegistry(unittest.TestCase):
    def setUp(self):
        from eal_core.event_bus import EventBus
        self.bus = EventBus()
        self.reg = AgentRegistry(max_agents=5, event_bus=self.bus)

    def test_register_and_get(self):
        identity = AgentIdentity.generate()
        record = self.reg.register(identity, instance="obj")
        self.assertIsInstance(record, AgentRecord)
        self.assertEqual(self.reg.get_instance(identity), "obj")
        self.assertIn(identity, self.reg)
        self.assertEqual(len(self.reg), 1)

    def test_duplicate_rejected(self):
        identity = AgentIdentity.generate()
        self.reg.register(identity, instance="obj")
        with self.assertRaises(ValueError):
            self.reg.register(identity, instance="obj2")

    def test_capacity(self):
        reg = AgentRegistry(max_agents=1, event_bus=self.bus)
        reg.register(AgentIdentity.generate(), instance="a")
        with self.assertRaises(ValueError):
            reg.register(AgentIdentity.generate(), instance="b")

    def test_drop(self):
        identity = AgentIdentity.generate()
        self.reg.register(identity, instance="obj")
        record = self.reg.drop(identity)
        self.assertIsNotNone(record)
        self.assertNotIn(identity, self.reg)
        self.assertIsNone(self.reg.drop(identity))

    def test_event_published(self):
        identity = AgentIdentity.generate()
        events = []
        self.bus.subscribe("agent.registered", lambda e: events.append(e))
        self.reg.register(identity, instance="obj")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].payload["identity"], str(identity))


class TestEALCore(unittest.TestCase):
    def test_start_stop(self):
        core = EALCore(Config(experiment_name="t", seed=1))
        self.assertFalse(core.running)
        core.start()
        self.assertTrue(core.running)
        core.stop()
        self.assertFalse(core.running)

    def test_register_agent(self):
        core = EALCore()
        core.start()
        identity = core.register_agent(instance="agent-1", metadata={"role": "sender"})
        self.assertIsInstance(identity, AgentIdentity)
        self.assertEqual(core.get_agent(identity), "agent-1")
        core.stop()


class TestExperimentRecord(unittest.TestCase):
    def test_to_json_roundtrip(self):
        cfg = Config(seed=7)
        result = ExperimentResult(communication_success=0.8, latency_seconds=0.05)
        rec = ExperimentRecord(
            experiment_id="exp-abc",
            hypothesis="agents learn a convention",
            config=cfg,
            code_version="sha123",
            seed=7,
            baseline="random symbols",
            results=result,
            limitations="two agents only",
            decision="accept",
        )
        rec2 = ExperimentRecord.from_dict(json.loads(rec.to_json()))
        self.assertEqual(rec2.experiment_id, rec.experiment_id)
        self.assertEqual(rec2.decision, "accept")
        self.assertAlmostEqual(rec2.results.communication_success, 0.8)

    def test_finalize_sets_timestamp(self):
        rec = ExperimentRecord(
            experiment_id="x",
            hypothesis="h",
            config=Config(),
            code_version="v",
            seed=0,
            baseline="b",
        )
        finalized = rec.finalize()
        self.assertIsNotNone(finalized.finalized_at)
        self.assertEqual(finalized.experiment_id, "x")

    def test_invalid_decision(self):
        with self.assertRaises(ValueError):
            ExperimentRecord(
                experiment_id="x", hypothesis="h", config=Config(),
                code_version="v", seed=0, baseline="b",
                decision="maybe",
            )


if __name__ == "__main__":
    unittest.main()
