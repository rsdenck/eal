"""EAL-CORE: central system architecture, lifecycle, configuration, and
subsystem coordination.

Public API:
    AgentIdentity, CORE_IDENTITY        # agent identifiers
    Config                               # validated configuration
    Event, EventBus, Subscriber          # event-driven communication
    AgentRegistry, AgentRecord           # agent lifecycle
    ExperimentRecord, ExperimentResult   # reproducible experiment records
    EALCore                              # central coordinator
"""

from .config import Config
from .core import EALCore
from .event_bus import CORE_IDENTITY, Event, EventBus, Subscriber
from .experiment import ExperimentRecord, ExperimentResult
from .identity import AgentIdentity
from .registry import AgentRegistry, AgentRecord

__all__ = [
    "AgentIdentity",
    "AgentRecord",
    "AgentRegistry",
    "CORE_IDENTITY",
    "Config",
    "EALCore",
    "Event",
    "EventBus",
    "ExperimentRecord",
    "ExperimentResult",
    "Subscriber",
]
