"""Unit tests for EAL-OBSERVATORY (stdlib only)."""

from __future__ import annotations

import unittest

from eal_core.event_bus import EventBus
from eal_core.identity import AgentIdentity
from eal_observatory import Dashboard, TelemetrySink


class TestTelemetrySink(unittest.TestCase):
    def setUp(self):
        self.bus = EventBus()
        self.sink = TelemetrySink(self.bus)

    def test_records_real_event(self):
        aid = AgentIdentity.generate()
        self.bus.publish("message.sent", {"symbols": ["s1", "s2"]},
                         source=aid)
        records = self.sink.history("message.sent")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].event_type, "message.sent")
        self.assertEqual(records[0].source, str(aid))
        self.assertEqual(records[0].payload["symbols"], ["s1", "s2"])

    def test_read_only_no_publish(self):
        aid = AgentIdentity.generate()
        before = self.bus.event_count()
        self.bus.publish("message.sent", {"symbols": ["s1"]}, source=aid)
        after = self.bus.event_count()
        self.assertEqual(after, before + 1)
        # sink should not add its own events to the bus
        self.assertEqual(self.bus.event_count(), after)

    def test_agent_snapshot(self):
        aid = AgentIdentity.generate()
        self.bus.publish("message.sent", {"symbols": ["a", "b"]}, source=aid)
        self.bus.publish("message.received", {}, source=aid)
        agents = self.sink.agents()
        self.assertIn(str(aid), agents)
        snap = agents[str(aid)]
        self.assertEqual(snap.messages_sent, 1)
        self.assertEqual(snap.messages_received, 1)

    def test_symbols_seen(self):
        aid = AgentIdentity.generate()
        self.bus.publish("message.sent", {"symbols": ["s1", "s2"]}, source=aid)
        self.bus.publish("message.sent", {"symbols": ["s2", "s3"]}, source=aid)
        syms = self.sink.symbols_seen()
        self.assertEqual(syms.get("s2"), 2)
        self.assertEqual(syms.get("s1"), 1)
        self.assertEqual(syms.get("s3"), 1)

    def test_event_counts(self):
        self.bus.publish("message.sent", {}, source=AgentIdentity.generate())
        self.bus.publish("message.sent", {}, source=AgentIdentity.generate())
        self.bus.publish("compilation.started", {}, source=AgentIdentity.generate())
        counts = self.sink.event_counts()
        self.assertEqual(counts.get("message.sent"), 2)
        self.assertEqual(counts.get("compilation.started"), 1)

    def test_core_source_excluded_from_agents(self):
        from eal_core.event_bus import CORE_IDENTITY
        self.bus.publish("system.started", {}, source=CORE_IDENTITY)
        self.assertEqual(self.sink.active_agent_count(), 0)


class TestDashboard(unittest.TestCase):
    def test_render_text(self):
        bus = EventBus()
        sink = TelemetrySink(bus)
        aid = AgentIdentity.generate()
        bus.publish("message.sent", {"symbols": ["s1"]}, source=aid)
        dash = Dashboard(sink)
        text = dash.render_text()
        self.assertIn("EAL Observatory", text)
        self.assertIn("message.sent", text)

    def test_render_json(self):
        bus = EventBus()
        sink = TelemetrySink(bus)
        dash = Dashboard(sink)
        import json
        data = json.loads(dash.render_json())
        self.assertIn("active_agents", data)
        self.assertIn("event_counts", data)


if __name__ == "__main__":
    unittest.main()
