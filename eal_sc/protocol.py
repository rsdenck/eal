"""Protocol versioning and message representations for EAL-SC.

Distinguishes learned private encodings (EAL-CL) from cryptographic security
(EAL-SC): this module defines the protocol wire format and versioning, while
any private encoding learned by agents remains in EAL-CL and is transported
*through* an authenticated channel rather than replacing it.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Any


PROTOCOL_VERSION = "eal-sc/1.0"
SUPPORTED_VERSIONS = ("eal-sc/1.0",)


@dataclass(frozen=True)
class ProtocolFrame:
    """A wire-frame for a private protocol message.

    Attributes:
        version: Protocol version.
        type: Frame type (e.g. "data", "handshake", "key-update").
        payload_encoding: "binary" or "symbolic".
        payload: Encoded payload (bytes for binary, JSON-serializable for symbolic).
        integrity: Hex integrity tag.
    """

    version: str
    type: str
    payload_encoding: str
    payload: Any
    integrity: str

    def to_bytes(self) -> bytes:
        frame = {
            "version": self.version,
            "type": self.type,
            "payload_encoding": self.payload_encoding,
            "payload": self.payload if self.payload_encoding == "symbolic"
            else base64.b64encode(self.payload).decode("ascii")
            if isinstance(self.payload, (bytes, bytearray)) else self.payload,
            "integrity": self.integrity,
        }
        return json.dumps(frame, sort_keys=True).encode("utf-8")

    @classmethod
    def from_bytes(cls, data: bytes) -> "ProtocolFrame":
        frame = json.loads(data.decode("utf-8"))
        payload = frame["payload"]
        if frame["payload_encoding"] == "binary" and isinstance(payload, str):
            payload = base64.b64decode(payload)
        return cls(
            version=frame["version"],
            type=frame["type"],
            payload_encoding=frame["payload_encoding"],
            payload=payload,
            integrity=frame["integrity"],
        )


def check_version(version: str) -> bool:
    return version in SUPPORTED_VERSIONS
