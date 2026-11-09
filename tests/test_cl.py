"""Unit tests for EAL-CL (stdlib only)."""

from __future__ import annotations

import random
import unittest

from eal_cl import (
    Channel,
    Decoder,
    Encoder,
    Grammar,
    GrammarRule,
    Language,
    Message,
    Symbol,
    Vocabulary,
)


class TestSymbol(unittest.TestCase):
    def test_generate_unique(self):
        self.assertNotEqual(Symbol.generate().id, Symbol.generate().id)

    def test_immutable(self):
        s = Symbol.generate()
        with self.assertRaises(Exception):
            s.id = "changed"


class TestVocabulary(unittest.TestCase):
    def test_add_remove_version(self):
        v = Vocabulary.create()
        s1 = Symbol.generate()
        v.add(s1)
        self.assertEqual(len(v), 1)
        self.assertIsNotNone(v.get(s1.id))
        v.remove(s1.id)
        self.assertEqual(len(v), 0)
        self.assertIsNone(v.get(s1.id))
        # version changes on mutation
        v2 = Vocabulary.create()
        v2.add(s1)
        self.assertNotEqual(v2.version_id, "v0")

    def test_snapshot_load_roundtrip(self):
        v = Vocabulary.create()
        s = Symbol.generate(bit_pattern=b"\x01\x02", metadata={"origin": "a"})
        v.add(s)
        loaded = Vocabulary.load(v.snapshot())
        self.assertEqual(loaded.version_id, v.version_id)
        self.assertEqual(len(loaded), 1)
        got = loaded.get(s.id)
        self.assertIsNotNone(got)
        self.assertEqual(got.bit_pattern, b"\x01\x02")


class TestGrammar(unittest.TestCase):
    def test_add_rule(self):
        g = Grammar.create()
        rule = GrammarRule(id="r1", pattern=("s1", "s2"), structure="pair")
        g.add_rule(rule)
        self.assertEqual(len(g), 1)
        self.assertEqual(g.get("r1").structure, "pair")

    def test_snapshot_load_roundtrip(self):
        g = Grammar.create()
        g.add_rule(GrammarRule(id="r1", pattern=("a", "b"), structure="seq"))
        loaded = Grammar.load(g.snapshot())
        self.assertEqual(loaded.version_id, g.version_id)
        self.assertEqual(len(loaded), 1)


class TestLanguage(unittest.TestCase):
    def test_snapshot_and_apply_rollback(self):
        lang = Language()
        lang.add_symbol(Symbol.generate())
        before = lang.snapshot()
        lang.add_symbol(Symbol.generate())
        self.assertNotEqual(lang.version_id, before.version_id)
        lang.apply(before)
        self.assertEqual(lang.version_id, before.version_id)
        self.assertEqual(len(lang.vocabulary), len(before.vocabulary_snapshot["symbols"]))


class TestChannel(unittest.TestCase):
    def test_send_receive_bidirectional(self):
        ch = Channel("alice", "bob")
        mid = ch.send("alice", ("s1", "s2"), {"concept": 3})
        msg = ch.receive("bob")
        self.assertIsNotNone(msg)
        self.assertEqual(msg.id, mid)
        self.assertEqual(msg.symbols, ("s1", "s2"))
        self.assertEqual(msg.concept, {"concept": 3})
        self.assertEqual(ch.pending("bob"), 0)
        self.assertEqual(ch.sent_count, 1)
        self.assertEqual(ch.delivered_count, 1)

    def test_receive_empty_returns_none(self):
        ch = Channel("alice", "bob")
        self.assertIsNone(ch.receive("bob"))

    def test_wrong_endpoint_rejected(self):
        ch = Channel("alice", "bob")
        with self.assertRaises(ValueError):
            ch.send("eve", ("s1",), 1)
        with self.assertRaises(ValueError):
            ch.receive("eve")


class TestEncoderDecoder(unittest.TestCase):
    def test_encode_decode_roundtrip_same_agent(self):
        rng = random.Random(0)
        enc = Encoder(rng=rng)
        dec = Decoder(rng=rng)
        symbols = enc.encode("concept-A", available_symbols=["a", "b", "c"])
        dec.reinforce(symbols, "concept-A", reward=1.0)
        self.assertEqual(dec.decode(symbols, candidate_concepts=["concept-A"]), "concept-A")

    def test_encoder_reinforce_updates_strength(self):
        rng = random.Random(1)
        enc = Encoder(rng=rng)
        enc.encode("c", available_symbols=["x", "y"])
        enc.reinforce("c", ("x",), reward=1.0)
        assoc = enc._associations["c"]
        self.assertGreater(assoc.strength, 0.0)


if __name__ == "__main__":
    unittest.main()
