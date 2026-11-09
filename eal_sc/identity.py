"""Agent-specific cryptographic identities for EAL-SC.

A PeerIdentity binds an EAL agent identity (from EAL-CORE) to cryptographic key
material used for private communication. The fingerprint is a content-stable
hash of the public key material, usable for identity verification without
exposing the key itself.

NOTE: This module uses only the Python standard library
(hmac/hashlib/secrets). Real public-key/asymmetric cryptography (e.g. X25519,
Ed25519) requires an established library such as ``cryptography`` and must be
injected behind the same interface before any production use. Never replace
authenticated encryption with a custom construction.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass, field

from eal_core.identity import AgentIdentity


@dataclass(frozen=True)
class PeerIdentity:
    """Cryptographic identity of a peer agent.

    Attributes:
        agent_id: The EAL-CORE agent identity.
        key_id: Identifier for the active cryptographic key.
        public_key_material: Opaque public key material (bytes). In this
            reference implementation it is random bytes; in production it is a
            serialized public key from an established library.
        fingerprint: SHA-256 of the public key material, hex-encoded.
    """

    agent_id: AgentIdentity
    key_id: str
    public_key_material: bytes
    fingerprint: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "fingerprint",
            hashlib.sha256(self.public_key_material).hexdigest(),
        )

    @classmethod
    def generate(cls, agent_id: AgentIdentity) -> "PeerIdentity":
        """Create a fresh peer identity with random reference key material."""
        key_id = secrets.token_hex(8)
        material = secrets.token_bytes(32)
        return cls(
            agent_id=agent_id,
            key_id=key_id,
            public_key_material=material,
        )

    def matches(self, other: "PeerIdentity") -> bool:
        """True if both identities refer to the same agent and key."""
        return self.agent_id == other.agent_id and self.key_id == other.key_id
