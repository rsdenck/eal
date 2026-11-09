"""Session key management for EAL-SC.

Generates, derives and rotates ephemeral session keys. Uses standard-library
hash-based primitives (HMAC-SHA256) as a development reference; production key
derivation should use an established KDF (e.g. HKDF from ``cryptography``)
injected behind the same :class:`KeyManager` interface.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class SessionKey:
    """An ephemeral symmetric session key.

    Attributes:
        id: Unique session-key identifier.
        key_material: Raw key bytes.
        created_at: ISO-8601 UTC creation timestamp.
        expires_at: Optional ISO-8601 UTC expiry timestamp.
    """

    id: str
    key_material: bytes
    created_at: str
    expires_at: Optional[str] = None

    @classmethod
    def generate(cls, key_bytes: int = 32,
                 ttl_seconds: Optional[float] = None) -> "SessionKey":
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        created = now.isoformat()
        expires = None
        if ttl_seconds is not None:
            expires = (now + timedelta(seconds=ttl_seconds)).isoformat()
        return cls(
            id=secrets.token_hex(8),
            key_material=secrets.token_bytes(key_bytes),
            created_at=created,
            expires_at=expires,
        )

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        from datetime import datetime, timezone
        return datetime.now(timezone.utc) > datetime.fromisoformat(self.expires_at)


class KeyManager:
    """Manages session-key generation, derivation and rotation.

    Keys are stored by their id so multiple peers can each have an active
    session key in the same manager.

    Attributes:
        active: The currently active :class:`SessionKey`, or None.
        history: Retired session keys (for in-flight message validation).
    """

    def __init__(self) -> None:
        self._keys: dict[str, SessionKey] = {}
        self.active: Optional[SessionKey] = None
        self.history: list[SessionKey] = []

    def generate_session(self, key_id: Optional[str] = None,
                         ttl_seconds: Optional[float] = None) -> SessionKey:
        """Create a session, stored under ``key_id`` (generated if omitted).

        If a key already exists under ``key_id`` it is retired to history.
        The new key becomes the active key.
        """
        if key_id is None:
            key_id = secrets.token_hex(8)
        key = SessionKey.generate(ttl_seconds=ttl_seconds)
        # Override the generated id with the requested key_id so peers can
        # address the key by a stable identifier.
        key = SessionKey(
            id=key_id, key_material=key.key_material,
            created_at=key.created_at, expires_at=key.expires_at,
        )
        if key_id in self._keys:
            self.history.append(self._keys[key_id])
        self._keys[key_id] = key
        self.active = key
        return key

    def derive(self, session_key: SessionKey, context: bytes,
               length: int = 32) -> bytes:
        """Derive a sub-key from a session key using HMAC-SHA256.

        Reference derivation only; replace with an established KDF in production.
        """
        return hmac.new(session_key.key_material, context, hashlib.sha256).digest()[:length]

    def rotate(self, key_id: Optional[str] = None) -> SessionKey:
        """Rotate a session key (active if ``key_id`` omitted)."""
        target = key_id or (self.active.id if self.active else None)
        if target is None:
            raise ValueError("no active session key to rotate")
        return self.generate_session(key_id=target)

    def find_key(self, key_id: str) -> Optional[SessionKey]:
        """Look up a key by id among active and retired keys."""
        return self._keys.get(key_id) or next(
            (k for k in self.history if k.id == key_id), None
        )

