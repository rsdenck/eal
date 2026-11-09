"""Unit tests for EAL-SC (stdlib only)."""

from __future__ import annotations

import unittest

from eal_core.identity import AgentIdentity
from eal_sc import (
    AuthenticatedChannel,
    AuthenticatedMessage,
    HmacAuthenticatedChannel,
    KeyManager,
    PeerIdentity,
    ProtocolFrame,
    SessionKey,
    check_version,
)


class TestPeerIdentity(unittest.TestCase):
    def test_generate_fingerprint(self):
        aid = AgentIdentity.generate()
        peer = PeerIdentity.generate(aid)
        self.assertEqual(peer.agent_id, aid)
        self.assertEqual(len(peer.fingerprint), 64)  # SHA-256 hex
        self.assertNotEqual(peer.fingerprint, "")

    def test_matches(self):
        aid = AgentIdentity.generate()
        p1 = PeerIdentity.generate(aid)
        p2 = PeerIdentity(
            agent_id=aid, key_id=p1.key_id,
            public_key_material=p1.public_key_material,
        )
        self.assertTrue(p1.matches(p2))
        p3 = PeerIdentity.generate(AgentIdentity.generate())
        self.assertFalse(p1.matches(p3))


class TestSessionKey(unittest.TestCase):
    def test_generate_and_expiry(self):
        key = SessionKey.generate(ttl_seconds=0.001)
        self.assertFalse(key.is_expired())
        self.assertEqual(len(key.key_material), 32)

    def test_expired(self):
        import time
        key = SessionKey.generate(ttl_seconds=0.05)
        time.sleep(0.06)
        self.assertTrue(key.is_expired())


class TestKeyManager(unittest.TestCase):
    def test_generate_and_rotate(self):
        km = KeyManager()
        k1 = km.generate_session("key-a")
        k2 = km.generate_session("key-b")
        self.assertNotEqual(k1.id, k2.id)
        self.assertIs(km.active, k2)
        k3 = km.rotate("key-a")
        self.assertEqual(k3.id, "key-a")
        self.assertNotEqual(k3.key_material, k1.key_material)
        self.assertIn(k1, km.history)

    def test_derive(self):
        km = KeyManager()
        key = km.generate_session()
        derived = km.derive(key, b"context", length=16)
        self.assertEqual(len(derived), 16)
        self.assertEqual(km.derive(key, b"context", length=16), derived)  # deterministic

    def test_find_key(self):
        km = KeyManager()
        key = km.generate_session()
        self.assertIs(km.find_key(key.id), key)
        self.assertIsNone(km.find_key("nonexistent"))


class TestAuthenticatedMessage(unittest.TestCase):
    def test_verify_roundtrip(self):
        sender = AgentIdentity.generate()
        receiver = AgentIdentity.generate()
        key = b"\x01" * 32
        msg = AuthenticatedMessage.create(sender, receiver, {"x": 1}, key, 1)
        self.assertTrue(msg.verify(key))
        bad_key = b"\x02" * 32
        self.assertFalse(msg.verify(bad_key))

    def test_tampered_payload_fails(self):
        sender = AgentIdentity.generate()
        receiver = AgentIdentity.generate()
        key = b"\x01" * 32
        msg = AuthenticatedMessage.create(sender, receiver, {"x": 1}, key, 1)
        msg.payload = {"x": 99}  # tamper
        self.assertFalse(msg.verify(key))


class TestHmacAuthenticatedChannel(unittest.TestCase):
    def setUp(self):
        self.aid_a = AgentIdentity.generate()
        self.aid_b = AgentIdentity.generate()
        self.peer_a = PeerIdentity.generate(self.aid_a)
        self.peer_b = PeerIdentity.generate(self.aid_b)
        self.km = KeyManager()
        self.km.generate_session(self.peer_a.key_id, ttl_seconds=3600)
        self.km.generate_session(self.peer_b.key_id, ttl_seconds=3600)
        self.ch = HmacAuthenticatedChannel(self.peer_a, self.peer_b, self.km)

    def test_send_receive_authenticated(self):
        mid = self.ch.send(self.aid_a, self.aid_b, {"msg": "hello"})
        self.assertEqual(self.ch.sent_count, 1)
        msg = self.ch.receive(self.aid_b)
        self.assertIsNotNone(msg)
        self.assertEqual(msg.id, mid)
        self.assertEqual(msg.payload, {"msg": "hello"})
        self.assertEqual(self.ch.delivered_count, 1)
        self.assertEqual(self.ch.pending(self.aid_b), 0)

    def test_receive_empty_none(self):
        self.assertIsNone(self.ch.receive(self.aid_b))

    def test_tampered_message_rejected(self):
        self.ch.send(self.aid_a, self.aid_b, {"msg": "hello"})
        msg = self.ch._queue_b[0]  # access queued message to tamper
        msg.tag = "0" * 64
        with self.assertRaises(ValueError):
            self.ch.receive(self.aid_b)
        self.assertEqual(self.ch.rejected_count, 1)

    def test_replay_rejected(self):
        self.ch.send(self.aid_a, self.aid_b, {"msg": "once"})
        msg = self.ch._queue_b[0]
        self.ch._queue_b.append(msg)  # duplicate in queue
        self.ch.receive(self.aid_b)  # first accepted
        with self.assertRaises(ValueError):
            self.ch.receive(self.aid_b)  # replay rejected
        self.assertEqual(self.ch.rejected_count, 1)

    def test_wrong_endpoint_rejected(self):
        evil = AgentIdentity.generate()
        with self.assertRaises(ValueError):
            self.ch.send(evil, self.aid_b, {"x": 1})
        with self.assertRaises(ValueError):
            self.ch.receive(evil)

    def test_version_supported(self):
        self.assertTrue(check_version("eal-sc/1.0"))
        self.assertFalse(check_version("eal-sc/9.9"))


class TestProtocolFrame(unittest.TestCase):
    def test_binary_frame_roundtrip(self):
        frame = ProtocolFrame(
            version="eal-sc/1.0",
            type="data",
            payload_encoding="binary",
            payload=b"\x00\x01\x02",
            integrity="abc",
        )
        loaded = ProtocolFrame.from_bytes(frame.to_bytes())
        self.assertEqual(loaded.payload, b"\x00\x01\x02")
        self.assertEqual(loaded.payload_encoding, "binary")

    def test_symbolic_frame_roundtrip(self):
        frame = ProtocolFrame(
            version="eal-sc/1.0",
            type="data",
            payload_encoding="symbolic",
            payload={"k": "v"},
            integrity="abc",
        )
        loaded = ProtocolFrame.from_bytes(frame.to_bytes())
        self.assertEqual(loaded.payload, {"k": "v"})


if __name__ == "__main__":
    unittest.main()
