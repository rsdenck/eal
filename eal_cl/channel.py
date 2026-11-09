"""Bidirectional communication channel for EAL-CL.

A Channel transports symbol sequences between two agents. It is the
communication primitive: agents encode concepts into symbols on one end and
decode symbols into concepts on the other. The channel itself does not
interpret symbol meanings.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Message:
    """A message in transit on a channel.

    Attributes:
        id: Unique message identifier.
        sender: Identity of the sending agent.
        receiver: Identity of the receiving agent.
        symbols: Tuple of symbol ids (the encoded message).
        concept: The intended meaning (known to sender; hint to receiver).
        timestamp: ISO-8601 UTC emission time.
    """

    id: str
    sender: str
    receiver: str
    symbols: tuple[str, ...]
    concept: Any
    timestamp: str

    @classmethod
    def create(cls, sender: str, receiver: str, symbols: tuple[str, ...],
               concept: Any) -> "Message":
        from datetime import datetime, timezone
        return cls(
            id=str(uuid.uuid4()),
            sender=sender,
            receiver=receiver,
            symbols=symbols,
            concept=concept,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


class Channel:
    """A bidirectional FIFO channel between two agents.

    Attributes:
        id: Channel identifier.
        agent_a / agent_b: The two endpoint identities.
    """

    def __init__(self, agent_a: str, agent_b: str) -> None:
        self.id = str(uuid.uuid4())
        self.agent_a = agent_a
        self.agent_b = agent_b
        self._queue_a: list[Message] = []  # messages destined for agent_a
        self._queue_b: list[Message] = []  # messages destined for agent_b
        self.sent_count = 0
        self.delivered_count = 0

    def other(self, agent: str) -> str:
        return self.agent_b if agent == self.agent_a else self.agent_a

    def send(self, sender: str, symbols: tuple[str, ...], concept: Any) -> str:
        """Send a symbol sequence from ``sender`` to the other endpoint.

        Returns the message id.
        """
        if sender not in (self.agent_a, self.agent_b):
            raise ValueError(f"{sender} is not an endpoint of this channel")
        receiver = self.other(sender)
        message = Message.create(sender, receiver, symbols, concept)
        if receiver == self.agent_a:
            self._queue_a.append(message)
        else:
            self._queue_b.append(message)
        self.sent_count += 1
        return message.id

    def receive(self, agent: str) -> Message | None:
        """Retrieve the oldest message for ``agent``, or None if empty."""
        if agent not in (self.agent_a, self.agent_b):
            raise ValueError(f"{agent} is not an endpoint of this channel")
        queue = self._queue_a if agent == self.agent_a else self._queue_b
        if not queue:
            return None
        message = queue.pop(0)
        self.delivered_count += 1
        return message

    def pending(self, agent: str) -> int:
        if agent not in (self.agent_a, self.agent_b):
            raise ValueError(f"{agent} is not an endpoint of this channel")
        return len(self._queue_a if agent == self.agent_a else self._queue_b)
