"""Unit tests for EAL-VERIFY, EAL-GEN, EAL-KNOW (stdlib only)."""

from __future__ import annotations

import random
import unittest

from eal_cl import Grammar, GrammarRule, Language, Symbol, Vocabulary
from eal_gen import GeneticLanguageEvolution, Genome
from eal_know import KnowledgeBase, KnowledgeEntry
from eal_verify import FormalVerifier, LanguageVerificationReport, VerificationExperiment, VerificationResult


class TestVerification(unittest.TestCase):
    def test_compiler_reproducibility(self):
        v = FormalVerifier()
        r = v.verify_compiler_correctness("bind x = 5; print x;")
        self.assertTrue(r.passed)
        self.assertEqual(r.check, "compiler_reproducibility")

    def test_semantic_preservation_identical(self):
        v = FormalVerifier()
        lang = Language()
        lang.add_symbol(Symbol.generate())
        r = v.verify_semantic_preservation(lang, lang)
        self.assertTrue(r.passed)

    def test_no_regression(self):
        v = FormalVerifier()
        r = v.verify_no_regression({"a": 0.8, "b": 0.5},
                                   {"a": 0.9, "b": 0.5})
        self.assertTrue(r.passed)
        r2 = v.verify_no_regression({"a": 0.8}, {"a": 0.5})
        self.assertFalse(r2.passed)

    def test_verify_language_report(self):
        v = FormalVerifier()
        ref = Language(); ref.add_symbol(Symbol.generate())
        cand = Language(); cand.add_symbol(Symbol.generate())
        report = v.verify_language(ref, cand)
        self.assertIsInstance(report, LanguageVerificationReport)
        self.assertGreaterEqual(len(report.results), 1)

    def test_verification_experiment(self):
        v = FormalVerifier()
        exp = VerificationExperiment(v)
        ref = Language(); ref.add_symbol(Symbol.generate())
        cand = Language(); cand.add_symbol(Symbol.generate())
        record = exp.run("candidate preserves semantics", ref, cand, seed=1)
        self.assertIn(record.decision, ("accept", "reject"))
        self.assertEqual(len(exp.records()), 1)


class TestGenome(unittest.TestCase):
    def test_from_language_and_id(self):
        lang = Language()
        lang.add_symbol(Symbol.generate())
        g = Genome.from_language(lang, generation=1)
        gid = g.compute_id()
        self.assertEqual(len(gid), 32)
        g2 = Genome(genome_id=gid, vocabulary=g.vocabulary,
                    grammar=g.grammar, generation=g.generation)
        lang2 = g2.to_language()
        self.assertEqual(len(lang2.vocabulary), 1)

    def test_genome_immutable_id(self):
        lang = Language()
        g = Genome.from_language(lang)
        self.assertEqual(len(g.genome_id), 32)


class TestGeneticEvolution(unittest.TestCase):
    def test_add_and_mutate(self):
        g = GeneticLanguageEvolution(rng=random.Random(0))
        lang = Language()
        lang.add_symbol(Symbol.generate())
        gid = g.add_individual(lang)
        self.assertIn(gid, g.population)
        new_g = g.mutate_genome(g.population[gid].genome)
        self.assertNotEqual(new_g.genome_id, gid)
        self.assertEqual(new_g.generation, 1)

    def test_crossover(self):
        g = GeneticLanguageEvolution(rng=random.Random(1))
        l1 = Language(); l1.add_symbol(Symbol.generate())
        l2 = Language(); l2.add_symbol(Symbol.generate())
        id1 = g.add_individual(l1)
        id2 = g.add_individual(l2)
        gen1 = g.population[id1].genome
        gen2 = g.population[id2].genome
        child = g.crossover_genomes(gen1, gen2)
        self.assertEqual(child.generation, 1)
        self.assertEqual(len(child.lineage), 2)

    def test_evolve_generation(self):
        g = GeneticLanguageEvolution(rng=random.Random(0))
        lang = Language()
        lang.add_symbol(Symbol.generate())
        g.add_individual(lang, fitness=0.5)
        summary = g.evolve_generation(fitness_fn=lambda genome: 0.7)
        self.assertIn("best_genome", summary)
        self.assertIn("population_size", summary)
        self.assertGreaterEqual(summary["population_size"], 1)

    def test_fitness_fn_used(self):
        calls = []
        g = GeneticLanguageEvolution(rng=random.Random(0))
        lang = Language()
        lang.add_symbol(Symbol.generate())
        g.add_individual(lang)
        g.evolve_generation(fitness_fn=lambda genome: calls.append(1) or 0.9)
        ind = list(g.population.values())[0]
        self.assertTrue(ind.evaluated)

    def test_snapshot(self):
        g = GeneticLanguageEvolution(rng=random.Random(0))
        lang = Language()
        g.add_individual(lang)
        snap = g.snapshot()
        self.assertIn("population", snap)
        self.assertIn("history", snap)


class TestKnowledgeBase(unittest.TestCase):
    def test_record_and_dedup_experiment(self):
        kb = KnowledgeBase()
        eid1 = kb.record_experiment("hyp", {"seed": 1}, {"success": 0.8},
                                    "accept", "good result")
        eid2 = kb.record_experiment("hyp", {"seed": 1}, {"success": 0.8},
                                    "accept", "duplicate")
        self.assertEqual(eid1, eid2)  # deduplicated
        self.assertEqual(len(kb.entries()), 1)

    def test_different_experiment_not_deduped(self):
        kb = KnowledgeBase()
        eid1 = kb.record_experiment("hyp", {"seed": 1}, {"success": 0.8},
                                    "accept", "r1")
        eid2 = kb.record_experiment("hyp", {"seed": 2}, {"success": 0.9},
                                    "accept", "r2")
        self.assertNotEqual(eid1, eid2)
        self.assertEqual(len(kb.entries()), 2)

    def test_record_language_version(self):
        kb = KnowledgeBase()
        eid = kb.record_language_version("v1", {"syms": 1}, "accepted",
                                         "best version")
        entry = kb.get(eid)
        self.assertIsNotNone(entry)
        self.assertEqual(entry.kind, "language_version")
        self.assertEqual(len(kb.accepted_languages()), 1)

    def test_rejected_languages(self):
        kb = KnowledgeBase()
        kb.record_language_version("v1", {}, "rejected", "bad")
        kb.record_language_version("v2", {}, "accepted", "good")
        self.assertEqual(len(kb.rejected_languages()), 1)
        self.assertEqual(len(kb.accepted_languages()), 1)

    def test_record_decision(self):
        kb = KnowledgeBase()
        eid = kb.record_decision("d1", "reject", "not good enough",
                                 context={"score": 0.3})
        entry = kb.get(eid)
        self.assertIsNotNone(entry)
        self.assertEqual(entry.kind, "decision")

    def test_experiment_decision_lookup(self):
        kb = KnowledgeBase()
        kb.record_experiment("hyp", {"seed": 1}, {"success": 0.8},
                             "accept", "good")
        found = kb.experiment_decision("hyp", {"seed": 1})
        self.assertIsNotNone(found)
        self.assertEqual(found["content"]["decision"], "accept")
        not_found = kb.experiment_decision("other", {"seed": 1})
        self.assertIsNone(not_found)

    def test_snapshot(self):
        kb = KnowledgeBase()
        kb.record_experiment("h", {"s": 1}, {"r": 1}, "accept", "ok")
        snap = kb.snapshot()
        self.assertEqual(snap["total_entries"], 1)
        self.assertEqual(snap["by_kind"]["experiment"], 1)


class TestKnowledgeEntry(unittest.TestCase):
    def test_to_dict(self):
        e = KnowledgeEntry(entry_id="e1", kind="experiment",
                           content={"a": 1}, timestamp="t",
                           rationale="r")
        d = e.to_dict()
        self.assertEqual(d["entry_id"], "e1")
        self.assertEqual(d["content"]["a"], 1)


if __name__ == "__main__":
    unittest.main()
