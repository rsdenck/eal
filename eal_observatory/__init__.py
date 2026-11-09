"""EAL-OBSERVATORY package.

Public API:
    TelemetrySink      # subscribes to EventBus, records real-system telemetry
    Dashboard          # text/JSON rendering of telemetry (read-only)
    AgentSnapshot      # per-agent snapshot
    TelemetryRecord    # single telemetry record

The observatory is a read-only consumer of the event bus: it observes but
never influences execution. All telemetry originates from real system events;
no synthetic data is ever presented as experimental results.
"""

from .telemetry import AgentSnapshot, Dashboard, TelemetryRecord, TelemetrySink

__all__ = [
    "AgentSnapshot",
    "Dashboard",
    "TelemetryRecord",
    "TelemetrySink",
]
