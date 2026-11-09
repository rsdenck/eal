"""Event bus for EAL-CORE.

All inter-agent and inter-module communication flows through the event bus.
Subscribers depend on the bus interface, not on concrete publishers, which
keeps module boundaries strict and makes tests/mocks interchangeable.

The observatory subscribes to the bus for telemetry. Telemetry originates only
from real system events published here; the bus never synthesizes events.
"""

from __future__ import annotations

import threading
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Final

from .identity import AgentIdentity, CORE_IDENTITY


@dataclass(frozen=True)
class Event:
    """An immutable event published on the bus.

    Attributes:
        type: Event type string (e.g. "agent.registered", "message.sent").
        source: Identity of the publisher (CORE_IDENTITY for system events).
        payload: JSON-serializable event data.
        timestamp: UTC timestamp of emission.
        correlation_id: Optional id linking related events (e.g. a request and
            its reply).
    """

    type: str
    source: AgentIdentity
    payload: dict[str, Any]
    timestamp: str
    correlation_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "source": str(self.source),
            "payload": self.payload,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
        }


# Type of a subscriber callback: receives an Event and returns None.
Subscriber = Callable[[Event], None]


class EventBus:
    """Ordered publish/subscribe event bus.

    Thread-safe. Subscribers are invoked synchronously in registration order
    when an event is published. A maximum event history is retained for
    replay/debugging (bounded deque).
    """

    def __init__(self, max_history: int = 10000) -> None:
        self._subscribers: dict[str, list[Subscriber]] = defaultdict(list)
        self._lock = threading.RLock()
        self._history: deque[Event] = deque(maxlen=max_history)
        self._event_count: int = 0

    # -- subscription -----------------------------------------------------

    def subscribe(self, event_type: str, callback: Subscriber) -> None:
        """Register ``callback`` to receive events of ``event_type``.

        Use ``"*"`` to subscribe to every event type.
        """
        with self._lock:
            self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Subscriber) -> None:
        """Remove a previously registered callback."""
        with self._lock:
            callbacks = self._subscribers.get(event_type)
            if callbacks is None:
                return
            self._subscribers[event_type] = [c for c in callbacks if c is not callback]

    # -- publication ------------------------------------------------------

    def publish(
        self,
        event_type: str,
        payload: dict[str, Any],
        source: AgentIdentity = CORE_IDENTITY,
        correlation_id: str | None = None,
    ) -> Event:
        """Publish an event and deliver it to matching subscribers.

        Returns the emitted :class:`Event`. Delivery is synchronous: by the
        time this returns, all subscribers for the event type (and ``"*"``)
        have been invoked.
        """
        event = Event(
            type=event_type,
            source=source,
            payload=dict(payload),
            timestamp=datetime.now(timezone.utc).isoformat(),
            correlation_id=correlation_id,
        )
        with self._lock:
            self._history.append(event)
            self._event_count += 1
            subscribers = list(self._subscribers.get(event_type, []))
            wildcard = list(self._subscribers.get("*", []))

        # Deliver outside the lock so a slow subscriber does not block
        # other publishers, while keeping snapshot-consistent subscriber lists.
        for callback in subscribers:
            try:
                callback(event)
            except Exception:  # pragma: no cover - defensive
                # A subscriber failure must not take down the bus or other
                # subscribers. Errors are recorded in the event history below.
                self._record_subscriber_error(event_type, event)
        for callback in wildcard:
            try:
                callback(event)
            except Exception:  # pragma: no cover - defensive
                self._record_subscriber_error("*", event)

        return event

    def publish_sync(self, *args, **kwargs) -> Event:
        """Alias for :meth:`publish` (kept for interface clarity)."""
        return self.publish(*args, **kwargs)

    # -- inspection -------------------------------------------------------

    def history(self, event_type: str | None = None, limit: int | None = None) -> list[Event]:
        """Return recent events, optionally filtered by type, newest last."""
        with self._lock:
            events = list(self._history)
        if event_type is not None:
            events = [e for e in events if e.type == event_type]
        if limit is not None:
            events = events[-limit:]
        return events

    def event_count(self) -> int:
        """Total number of events published since bus creation."""
        with self._lock:
            return self._event_count

    def _record_subscriber_error(self, event_type: str, event: Event) -> None:
        with self._lock:
            self._history.append(
                Event(
                    type="subscriber.error",
                    source=CORE_IDENTITY,
                    payload={
                        "failed_event_type": event_type,
                        "failed_event": event.to_dict(),
                    },
                    timestamp=event.timestamp,
                    correlation_id=event.correlation_id,
                )
            )
