"""Authenticated communication channel for EAL-SC.

Provides message authentication and integrity verification between two peers,
plus replay protection via nonces/sequence numbers.

CRYPTO TRANSPARENCY:
This reference implementation authenticates messages with HMAC-SHA256
(standard library). HMAC is a message-authentication code; it provides
integrity and authenticity but is NOT authenticated encryption (it does not
confidentiality-encrypt the payload). For production, replace
:class:`HmacAuthenticatedChannel` with a channel backed by an established AEAD
construction (e.g. AES-GCM or ChaCha20-Poly1305 from ``cryptography``)
exposing the same :class:`AuthenticatedChannel` interface. Never rely on this
reference channel as a substitute for authenticated encryption.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from eal_core.identity import AgentIdentity
from .identity import PeerIdentity
from .keys import SessionKey


@dataclass
class AuthenticatedMessage:
    """A message with authentication metadata.

    Attributes:
        id: Unique message identifier.
        sender / receiver: Agent identities.
        payload: JSON-serializable message content.
        nonce: Single-use random value (replay protection).
        sequence: Monotonic sequence number (replay protection).
        tag: HMAC authentication tag (hex).
        timestamp: ISO-8601 UTC emission time.
        protocol_version: Protocol version in use.
    """

    id: str
    sender: str
    receiver: str
    payload: dict[str, Any]
    nonce: str
    sequence: int
    tag: str
    timestamp: str
    protocol_version: str = "eal-sc/1.0"

    @classmethod
    def create(cls, sender: AgentIdentity, receiver: AgentIdentity,
               payload: dict[str, Any], key_material: bytes,
               sequence: int,
               protocol_version: str = "eal-sc/1.0") -> "AuthenticatedMessage":
        nonce = secrets.token_hex(16)
        tag = _compute_tag(key_material, sender, receiver, payload, nonce,
                           sequence, protocol_version)
        return cls(
            id=secrets.token_hex(8),
            sender=str(sender),
            receiver=str(receiver),
            payload=dict(payload),
            nonce=nonce,
            sequence=sequence,
            tag=tag,
            timestamp=datetime.now(timezone.utc).isoformat(),
            protocol_version=protocol_version,
        )

    def verify(self, key_material: bytes) -> bool:
        """Verify the HMAC authentication tag."""
        expected = _compute_tag(
            key_material, self.sender, self.receiver, self.payload,
            self.nonce, self.sequence, self.protocol_version,
        )
        return hmac.compare_digest(self.tag, expected)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "sender": self.sender,
            "receiver": self.receiver,
            "payload": self.payload,
            "nonce": self.nonce,
            "sequence": self.sequence,
            "tag": self.tag,
            "timestamp": self.timestamp,
            "protocol_version": self.protocol_version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AuthenticatedMessage":
        return cls(**data)


def _compute_tag(key_material: bytes, sender: Any, receiver: Any,
                 payload: dict[str, Any], nonce: str, sequence: int,
                 protocol_version: str) -> str:
    import json
    message = {
        "sender": str(sender),
        "receiver": str(receiver),
        "payload": payload,
        "nonce": nonce,
        "sequence": sequence,
        "protocol_version": protocol_version,
    }
    payload_bytes = json.dumps(message, sort_keys=True).encode("utf-8")
    return hmac.new(key_material, payload_bytes, hashlib.sha256).hexdigest()


class AuthenticatedChannel:
    """Interface for an authenticated, replay-protected channel.

    Concrete implementations must authenticate and integrity-protect every
    message and reject replays. Subscribers (e.g. the observatory) observe
    channel events but cannot forge messages.
    """

    def send(self, sender: AgentIdentity, receiver: AgentIdentity,
             payload: dict[str, Any]) -> str:
        """Authenticate and send ``payload`` to ``receiver``. Returns message id."""
        raise NotImplementedError

    def receive(self, receiver: AgentIdentity) -> Optional[AuthenticatedMessage]:
        """Receive and verify the next message for ``receiver``.

        Returns None if no message is available. Raises ValueError if the
        message fails authentication or replay checks.
        """
        raise NotImplementedError

    def pending(self, receiver: AgentIdentity) -> int:
        raise NotImplementedError


class HmacAuthenticatedChannel(AuthenticatedChannel):
    """Reference HMAC-SHA256 authenticated channel (development only).

    See module docstring for crypto-transparency caveats. Provides integrity,
    authenticity and replay protection, but NOT confidentiality.
    """

    PROTOCOL_VERSION = "eal-sc/1.0"

    def __init__(self, peer_a: PeerIdentity, peer_b: PeerIdentity,
                 key_manager) -> None:
        self.peer_a = peer_a
        self.peer_b = peer_b
        self.key_manager = key_manager
        self._queue_a: list[AuthenticatedMessage] = []
        self._queue_b: list[AuthenticatedMessage] = []
        self._seq_a = 0  # messages sent by a
        self._seq_b = 0  # messages sent by b
        self._seen_nonces: set[str] = set()
        self._max_seen_nonces = 10000
        self.sent_count = 0
        self.delivered_count = 0
        self.rejected_count = 0

    def _key_for(self, sender: AgentIdentity) -> bytes:
        peer = self.peer_a if sender == self.peer_a.agent_id else self.peer_b
        key = self.key_manager.find_key(peer.key_id)
        if key is None or key.is_expired():
            raise ValueError(f"No valid session key for peer {sender}")
        return key.key_material

    def _other(self, sender: AgentIdentity) -> AgentIdentity:
        if sender == self.peer_a.agent_id:
            return self.peer_b.agent_id
        if sender == self.peer_b.agent_id:
            return self.peer_a.agent_id
        raise ValueError(f"{sender} is not an endpoint of this channel")

    def send(self, sender: AgentIdentity, receiver: AgentIdentity,
             payload: dict[str, Any]) -> str:
        if sender not in (self.peer_a.agent_id, self.peer_b.agent_id):
            raise ValueError(f"{sender} is not an endpoint of this channel")
        key_material = self._key_for(sender)
        if sender == self.peer_a.agent_id:
            self._seq_a += 1
            seq = self._seq_a
        else:
            self._seq_b += 1
            seq = self._seq_b
        message = AuthenticatedMessage.create(
            sender, receiver, payload, key_material, seq,
            protocol_version=self.PROTOCOL_VERSION,
        )
        if receiver == self.peer_a.agent_id:
            self._queue_a.append(message)
        else:
            self._queue_b.append(message)
        self.sent_count += 1
        return message.id

    def receive(self, receiver: AgentIdentity) -> Optional[AuthenticatedMessage]:
        if receiver not in (self.peer_a.agent_id, self.peer_b.agent_id):
            raise ValueError(f"{receiver} is not an endpoint of this channel")
        queue = self._queue_a if receiver == self.peer_a.agent_id else self._queue_b
        if not queue:
            return None
        message = queue.pop(0)

        # Verify authentication tag with the sender's session key.
        sender_peer = self.peer_a if message.sender == str(self.peer_a.agent_id) else self.peer_b
        key = self.key_manager.find_key(sender_peer.key_id)
        if key is None or key.is_expired():
            self.rejected_count += 1
            raise ValueError("No valid session key for sender")
        if not message.verify(key.key_material):
            self.rejected_count += 1
            raise ValueError("Authentication tag verification failed")

        # Replay protection: reject repeated nonces.
        if message.nonce in self._seen_nonces:
            self.rejected_count += 1
            raise ValueError("Replay detected: nonce already seen")
        self._seen_nonces.add(message.nonce)
        if len(self._seen_nonces) > self._max_seen_nonces:
            self._seen_nonces = set(list(self._seen_nonces)[-self._max_seen_nonces // 2:])

        self.delivered_count += 1
        return message

    def pending(self, receiver: AgentIdentity) -> int:
        if receiver not in (self.peer_a.agent_id, self.peer_b.agent_id):
            raise ValueError(f"{receiver} is not an endpoint of this channel")
        return len(self._queue_a if receiver == self.peer_a.agent_id else self._queue_b)
