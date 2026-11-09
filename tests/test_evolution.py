"""Unit tests for EAL-EVOLUTION (stdlib only)."""

from __future__ import annotations

import unittest

import random

from eal_cl import Language, Symbol
from eal_core.config import Config
from eal_core.identity import AgentIdentity
from eal_evolution import Candidate, EvolutionEngine, FitnessEvaluator, MutationOperator, VersionStore


class TestVersionStore(unittest.TestCase):
    def test_archive_and_stable(self):
        store = VersionStore()
        lang = Language()
        lang.add_symbol(Symbol.generate())
        vid = store.archive(lang.snapshot(), stable=True)
        self.assertEqual(store.stable_id(), vid)
        got = store.get(vid)
        self.assertIsNotNone(got)
        self.assertEqual(got.version_id, vid)

    def set_stable_unknown_raises(self):
        store = VersionStore()
        with self.assertRaises(KeyError):
            store.set_stable("nonexistent")

    def rollback_preserves_history(self):
        store = VersionStore()
        l1 = Language.create(); l1.add_symbol(Symbol.generate())
        v1 = store.archive(l1.snapshot(), stable=True)
        l2 = Language.create(); l2.add_symbol(Symbol.generate()); l2.add_symbol(Symbol.generate())
        v2 = store.archive(l2.snapshot(), stable=True)
        self.assertEqual(store.stable_id(), v2)
        restored = store.rollback_to(v1)
        self.assertEqual(store.stable_id(), v1)
        self.assertEqual(restored.version_id, v1)


class TestMutationOperator(unittest.TestCase):
    def test_mutate_symbol(self):
        mut = MutationOperator(random.Random(0))
        lang = Language()
        cand = mut.mutate_symbol(lang, lang.version_id)
        self.assertEqual(len(cand.language.vocabulary), len(lang.vocabulary) + 1)
        self.assertEqual(cand.mutation_type, "symbol")

    def test_mutate_grammar(self):
        mut = MutationOperator(random.Random(1))
        lang = Language()
        lang.add_symbol(Symbol.generate(bit_pattern=b"\x01"))
        lang.add_symbol(Symbol.generate(bit_pattern=b"\x02"))
        cand = mut.mutate_grammar(lang, lang.version_id)
        self.assertEqual(cand.mutation_type, "grammar")

    def test_crossover(self):
        mut = MutationOperator(random.Random(2))
        a = Language(); a.add_symbol(Symbol.generate())
        b = Language(); b.add_symbol(Symbol.generate())
        cand = mut.crossover(a, b)
        self.assertEqual(cand.mutation_type, "crossover")
        self.assertEqual(len(cand.parent_ids), 2)


class TestFitnessEvaluator(unittest.TestCase):
    def test_evaluate_deterministic(self):
        ev = FitnessEvaluator(random.Random(0))
        lang = Language.create()
        lang.add_symbol(Symbol.generate())
        f1 = ev.evaluate_expressiveness(lang)
        f2 = ev.evaluate_expressiveness(lang)
        self.assertEqual(f1, f2)
        self.assertGreaterEqual(f1, 0.0)
        self.assertLessEqual(f1, 1.0)

    def test_stability_identical_is_one(self):
        ev = FitnessEvaluator()
        lang = Language()
        lang.add_symbol(Symbol.generate())
        self.assertAlmostEqual(ev.evaluate_stability(lang, lang), 1.0)

    def test_evaluate_candidate_sets_fitness(self):
        ev = FitnessEvaluator(random.Random(0))
        lang = Language()
        lang.add_symbol(Symbol.generate())
        cand = Candidate.create(lang, [lang.version_id], "symbol")
        fit = ev.evaluate(cand, rounds=50, seed=0)
        self.assertIsNotNone(cand.fitness)
        self.assertEqual(fit, cand.fitness)
        self.assertGreaterEqual(fit, 0.0)
        self.assertLessEqual(fit, 1.0)


class TestEvolutionEngine(unittest.TestCase):
    def test_stable_language_default(self):
        store = VersionStore()
        eng = EvolutionEngine(store)
        lang = eng.stable_language()
        self.assertIsInstance(lang, Language)

    def test_run_experiment_selects(self):
        store = VersionStore()
        lang = Language()
        lang.add_symbol(Symbol.generate())
        store.archive(lang.snapshot(), stable=True)
        eng = EvolutionEngine(store, rng=random.Random(0))
        result = eng.run_experiment(
            hypothesis="agents can learn a larger vocabulary",
            generations=2, candidates_per_gen=3,
            selection_threshold=0.3, rounds_per_eval=40, seed=7,
        )
        # selection_threshold low enough that something should be selected
        self.assertIsInstance(result.accepted, bool)
        self.assertIsInstance(result.evaluated, dict)
        self.assertGreaterEqual(len(result.evaluated), 1)

    def test_run_experiment_preserves_stable_on_reject(self):
        store = VersionStore()
        lang = Language()
        lang.add_symbol(Symbol.generate())
        store.archive(lang.snapshot(), stable=True)
        before_id = store.stable_id()
        eng = EvolutionEngine(store, rng=random.Random(0))
        # Very high threshold: nothing selected, stable preserved.
        result = eng.run_experiment(
            hypothesis="impossible improvement",
            generations=1, candidates_per_gen=2,
            selection_threshold=1.0, rounds_per_eval=30, seed=1,
        )
        self.assertEqual(store.stable_id(), before_id)
        self.assertFalse(result.accepted)

    def test_experiment_recorded(self):
        store = VersionStore()
        eng = EvolutionEngine(store)
        eng.run_experiment("h", generations=1, candidates_per_gen=1,
                           selection_threshold=0.0, rounds_per_eval=20, seed=0)
        self.assertEqual(len(eng.experiments()), 1)
        self.assertIn(eng.experiments()[0].decision, ("accept", "reject"))

    def test_rollback_to(self):
        store = VersionStore()
        l1 = Language(); l1.add_symbol(Symbol.generate())
        v1 = store.archive(l1.snapshot(), stable=True)
        l2 = Language(); l2.add_symbol(Symbol.generate()); l2.add_symbol(Symbol.generate())
        v2 = store.archive(l2.snapshot(), stable=True)
        eng = EvolutionEngine(store)
        restored = eng.rollback_to(v1)
        self.assertEqual(store.stable_id(), v1)
        self.assertEqual(restored.version_id, v1)


if __name__ == "__main__":
    unittest.main()
