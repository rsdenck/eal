"""EAL-OBSERVATORY: telemetry sink and dashboard.

Subscribes to the eal_core EventBus and records telemetry that originates
exclusively from real system events. The observatory is a read-only consumer:
it observes but never influences execution. No synthetic data is ever
presented as experimental results.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any

from eal_core.event_bus import Event, EventBus


@dataclass
class AgentSnapshot:
    """Real-time snapshot of an active agent (from observed events)."""

    identity: str
    events_seen: int = 0
    last_event: str | None = None
    last_event_time: str | None = None
    messages_sent: int = 0
    messages_received: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TelemetryRecord:
    """A single telemetry record from a real system event."""

    event_type: str
    source: str
    payload: dict[str, Any]
    timestamp: str
    correlation_id: str | None = None


class TelemetrySink:
    """Subscribes to the event bus and records real system events as telemetry.

    Read-only: it never publishes or modifies agent state. All telemetry
    originates from events actually emitted on the bus.
    """

    def __init__(self, bus: EventBus, max_history: int = 10000) -> None:
        self.bus = bus
        self._history: deque[TelemetryRecord] = deque(maxlen=max_history)
        self._agents: dict[str, AgentSnapshot] = {}
        self._event_counts: dict[str, int] = defaultdict(int)
        self._symbols_seen: dict[str, int] = defaultdict(int)
        self._language_versions: list[str] = []
        self._compilation_activity: int = 0
        self._started = False

        # Subscribe to all event types.
        bus.subscribe("*", self._on_event)

    # -- internal event handler ------------------------------------------

    def _on_event(self, event: Event) -> None:
        record = TelemetryRecord(
            event_type=event.type,
            source=str(event.source),
            payload=dict(event.payload),
            timestamp=event.timestamp,
            correlation_id=event.correlation_id,
        )
        self._history.append(record)
        self._event_counts[event.type] += 1

        src = str(event.source)
        if src not in ("eal-core",):
            snap = self._agents.setdefault(
                src, AgentSnapshot(identity=src))
            snap.events_seen += 1
            snap.last_event = event.type
            snap.last_event_time = event.timestamp

        # Derive domain-specific telemetry from event types.
        et = event.type
        if et == "message.sent":
            snap = self._agents.setdefault(
                str(event.source), AgentSnapshot(identity=str(event.source)))
            snap.messages_sent += 1
            syms = event.payload.get("symbols")
            if isinstance(syms, (list, tuple)):
                for s in syms:
                    self._symbols_seen[str(s)] += 1
        if et == "message.received":
            snap = self._agents.setdefault(
                str(event.source), AgentSnapshot(identity=str(event.source)))
            snap.messages_received += 1
        if et in ("language.versioned", "grammar.mutated",
                  "language.evolved"):
            self._language_versions.append(event.timestamp)
        if et in ("compilation.started", "program.compiled",
                  "ir.emitted"):
            self._compilation_activity += 1

    # -- queries ---------------------------------------------------------

    def history(self, event_type: str | None = None,
                limit: int | None = None) -> list[TelemetryRecord]:
        records = list(self._history)
        if event_type is not None:
            records = [r for r in records if r.event_type == event_type]
        if limit is not None:
            records = records[-limit:]
        return records

    def event_counts(self) -> dict[str, int]:
        return dict(self._event_counts)

    def agents(self) -> dict[str, AgentSnapshot]:
        return dict(self._agents)

    def active_agent_count(self) -> int:
        return len(self._agents)

    def symbols_seen(self) -> dict[str, int]:
        return dict(self._symbols_seen)

    def language_versions(self) -> list[str]:
        return list(self._language_versions)

    def compilation_activity(self) -> int:
        return self._compilation_activity

    def snapshot(self) -> dict[str, Any]:
        return {
            "active_agents": self.active_agent_count(),
            "agent_details": {
                aid: {
                    "events_seen": s.events_seen,
                    "last_event": s.last_event,
                    "last_event_time": s.last_event_time,
                    "messages_sent": s.messages_sent,
                    "messages_received": s.messages_received,
                }
                for aid, s in self._agents.items()
            },
            "event_counts": self.event_counts(),
            "symbols_seen": self.symbols_seen(),
            "language_versions": self.language_versions(),
            "compilation_activity": self.compilation_activity(),
            "total_events": len(self._history),
        }


class Dashboard:
    """Renders a text/JSON dashboard from real telemetry.

    Read-only rendering of TelemetrySink state. Suitable for terminal or
    log-based observability; a web GUI can be added in PHASE 10 without
    changing the sink.
    """

    def __init__(self, sink: TelemetrySink) -> None:
        self.sink = sink

    def render_text(self) -> str:
        snap = self.sink.snapshot()
        lines = [
            "=== EAL Observatory (real telemetry only) ===",
            f"Active agents: {snap['active_agents']}",
            f"Total events: {snap['total_events']}",
            f"Compilation activity: {snap['compilation_activity']}",
            f"Language versions: {len(snap['language_versions'])}",
            "",
            "Event counts:",
        ]
        for et, count in sorted(snap["event_counts"].items()):
            lines.append(f"  {et}: {count}")
        lines.append("")
        lines.append("Symbols seen:")
        for sym, count in sorted(snap["symbols_seen"].items(),
                                 key=lambda kv: -kv[1])[:10]:
            lines.append(f"  {sym}: {count}")
        lines.append("")
        lines.append("Agent details:")
        for aid, detail in snap["agent_details"].items():
            lines.append(
                f"  {aid[:8]}... events={detail['events_seen']} "
                f"sent={detail['messages_sent']} "
                f"received={detail['messages_received']}"
            )
        return "\n".join(lines)

    def render_json(self) -> str:
        import json
        return json.dumps(self.sink.snapshot(), indent=2, sort_keys=True)
