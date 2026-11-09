"""EAL-SC: private communication encoding subsystem.

Public API:
    PeerIdentity           # agent-specific cryptographic identity
    SessionKey, KeyManager # ephemeral session keys, derivation, rotation
    AuthenticatedChannel   # interface for authenticated channels
    HmacAuthenticatedChannel  # reference HMAC-SHA256 channel (development only)
    ProtocolFrame, check_version  # protocol framing & versioning

Crypto transparency:
HMAC-SHA256 (standard library) provides integrity/authenticity/replay
protection but NOT confidentiality. Production authenticated encryption must be
provided by an established library (e.g. ``cryptography`` AES-GCM) injected
behind the ``AuthenticatedChannel`` interface. Never replace authenticated
encryption with a custom construction. Learned private encodings (EAL-CL) are
transported *through* this channel, not substituted for it.
"""

from .channel import AuthenticatedChannel, AuthenticatedMessage, HmacAuthenticatedChannel
from .identity import PeerIdentity
from .keys import KeyManager, SessionKey
from .protocol import PROTOCOL_VERSION, ProtocolFrame, SUPPORTED_VERSIONS, check_version

__all__ = [
    "AuthenticatedChannel",
    "AuthenticatedMessage",
    "HmacAuthenticatedChannel",
    "KeyManager",
    "PeerIdentity",
    "ProtocolFrame",
    "PROTOCOL_VERSION",
    "SUPPORTED_VERSIONS",
    "SessionKey",
    "check_version",
]
