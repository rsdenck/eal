"""EAL-EVOLUTION: language evolution engine.

Agents detect limitations in existing language versions, propose new
structures, generate grammar mutations, test new symbols/operators, experiment
with semantic changes, evaluate communication performance, compare candidate
versions, select successful ones, preserve historical versions, and revert
unsuccessful experiments.

Every experiment is reproducible. Stable language versions are never
overwritten without preserving their previous state.

Controlled evolutionary mechanisms: mutation, crossover, selection and fitness
evaluation.
"""

from __future__ import annotations

import copy
import hashlib
import json
import random
from dataclasses import dataclass, field
from typing import Any

from eal_cl import Language, LanguageVersion, Symbol, GrammarRule
from eal_core.config import Config
from eal_core.experiment import ExperimentRecord, ExperimentResult
from eal_core.identity import AgentIdentity


@dataclass
class Candidate:
    """A candidate language version produced by the evolution engine.

    Attributes:
        candidate_id: Content-stable identifier.
        language: The candidate :class:`~eal_cl.language.Language`.
        parent_ids: IDs of the language version(s) this candidate derives from.
        mutation_type: Description of the mutation applied ("symbol", "grammar",
            "semantics", "crossover").
        metadata: JSON-serializable annotation (origin agent, step, etc.).
        fitness: Evaluated fitness score (None until evaluated).
    """

    candidate_id: str
    language: Language
    parent_ids: list[str]
    mutation_type: str
    metadata: dict[str, Any] = field(default_factory=dict)
    fitness: float | None = None

    @classmethod
    def create(cls, language: Language, parent_ids: list[str],
               mutation_type: str,
               metadata: dict[str, Any] | None = None) -> "Candidate":
        return cls(
            candidate_id=language.version_id,
            language=language,
            parent_ids=list(parent_ids),
            mutation_type=mutation_type,
            metadata=dict(metadata or {}),
        )

    def snapshot(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "language": self.language.snapshot().__dict__,
            "parent_ids": self.parent_ids,
            "mutation_type": self.mutation_type,
            "metadata": self.metadata,
            "fitness": self.fitness,
        }


@dataclass
class EvolutionResult:
    """Outcome of an evolution run.

    Attributes:
        selected_candidate: The candidate selected as the new stable version,
            or None if no candidate met the selection threshold.
        evaluated: All evaluated candidates (id -> fitness).
        accepted: Whether the experiment was accepted.
        rollback_performed: Whether a rollback to a prior stable version occurred.
    """

    selected_candidate: Candidate | None
    evaluated: dict[str, float]
    accepted: bool
    rollback_performed: bool = False


class VersionStore:
    """Append-only store of archived language versions.

    Languages are content-addressed by their version_id. Once archived, a
    version is immutable and can be restored by rollback. Stable versions are
    never overwritten without preserving their previous state here.
    """

    def __init__(self) -> None:
        self._versions: dict[str, LanguageVersion] = {}
        self._stable: str | None = None
        self._history: list[str] = []  # order of archival

    def archive(self, version: LanguageVersion, stable: bool = False) -> str:
        """Archive a language version. Returns its version_id."""
        self._versions[version.version_id] = version
        if version.version_id not in self._history:
            self._history.append(version.version_id)
        if stable:
            self._stable = version.version_id
        return version.version_id

    def get(self, version_id: str) -> LanguageVersion | None:
        return self._versions.get(version_id)

    def stable(self) -> LanguageVersion | None:
        if self._stable is None:
            return None
        return self._versions.get(self._stable)

    def set_stable(self, version_id: str) -> None:
        if version_id not in self._versions:
            raise KeyError(f"unknown version {version_id}")
        self._stable = version_id

    def stable_id(self) -> str | None:
        return self._stable

    def history(self) -> list[str]:
        return list(self._history)

    def snapshot(self) -> dict[str, Any]:
        return {
            "stable": self._stable,
            "history": list(self._history),
            "versions": {
                vid: v.__dict__ for vid, v in self._versions.items()
            },
        }

    @classmethod
    def load(cls, data: dict[str, Any]) -> "VersionStore":
        store = cls()
        store._stable = data.get("stable")
        store._history = list(data.get("history", []))
        for vid, vdata in data.get("versions", {}).items():
            store._versions[vid] = LanguageVersion(
                version_id=vdata["version_id"],
                grammar_snapshot=vdata["grammar_snapshot"],
                vocabulary_snapshot=vdata["vocabulary_snapshot"],
            )
        return store


class MutationOperator:
    """Generates grammar/symbol mutations of a language."""

    def __init__(self, rng: random.Random | None = None) -> None:
        self.rng = rng or random.Random()

    def mutate_symbol(self, language: Language,
                      parent_id: str) -> Candidate:
        """Add a fresh discrete symbol to the vocabulary."""
        new_lang = Language(
            grammar=copy.deepcopy(language.grammar),
            vocabulary=copy.deepcopy(language.vocabulary),
        )
        symbol = Symbol.generate(
            metadata={"origin": "mutation", "type": "symbol", "parent": parent_id}
        )
        new_lang.add_symbol(symbol)
        return Candidate.create(
            new_lang, [parent_id], "symbol",
            metadata={"added_symbol": symbol.id},
        )

    def mutate_grammar(self, language: Language,
                       parent_id: str) -> Candidate:
        """Add a fresh structural composition rule to the grammar."""
        new_lang = Language(
            grammar=copy.deepcopy(language.grammar),
            vocabulary=copy.deepcopy(language.vocabulary),
        )
        # Build a rule from existing symbols if any, else a placeholder.
        symbol_ids = new_lang.vocabulary.ids()
        if len(symbol_ids) >= 2:
            pattern = tuple(self.rng.sample(symbol_ids, k=2))
        elif symbol_ids:
            pattern = (symbol_ids[0],)
        else:
            pattern = ()
        rule = GrammarRule(
            id="rule-" + hashlib.sha256(
                json.dumps(pattern, sort_keys=True).encode()
            ).hexdigest()[:8],
            pattern=pattern,
            structure="composed",
            metadata={"origin": "mutation", "type": "grammar", "parent": parent_id},
        )
        new_lang.add_rule(rule)
        return Candidate.create(
            new_lang, [parent_id], "grammar",
            metadata={"added_rule": rule.id},
        )

    def mutate_semantics(self, language: Language,
                         parent_id: str) -> Candidate:
        """Experiment with a semantic change: reorder symbol metadata hints.

        Semantics live in agents; here we only mutate the metadata hints that
        agents may use to bias learning. No symbol meaning is hardcoded.
        """
        new_lang = Language(
            grammar=copy.deepcopy(language.grammar),
            vocabulary=copy.deepcopy(language.vocabulary),
        )
        # Symbols are frozen (hashable for use as vocabulary keys), so a
        # "semantic change" is modeled by replacing each symbol with a new one
        # carrying an updated metadata hint. No symbol meaning is hardcoded.
        for symbol in list(new_lang.vocabulary):
            new_sym = Symbol(
                id=symbol.id,
                bit_pattern=symbol.bit_pattern,
                metadata={**symbol.metadata, "semantic_bias": self.rng.random()},
            )
            new_lang.vocabulary.symbols[symbol.id] = new_sym
        new_lang.version_id = new_lang._compute_version_id()
        return Candidate.create(
            new_lang, [parent_id], "semantics",
            metadata={"semantic_bias": True},
        )

    def crossover(self, parent_a: Language, parent_b: Language) -> Candidate:
        """Combine vocabularies and grammars of two language versions."""
        new_lang = Language(
            grammar=copy.deepcopy(parent_a.grammar),
            vocabulary=copy.deepcopy(parent_a.vocabulary),
        )
        # Merge symbols from parent_b not already present.
        for symbol in parent_b.vocabulary:
            if symbol.id not in new_lang.vocabulary.symbols:
                new_lang.vocabulary.symbols[symbol.id] = symbol
        # Merge rules from parent_b not already present.
        for rule in parent_b.grammar.rules.values():
            if rule.id not in new_lang.grammar.rules:
                new_lang.grammar.rules[rule.id] = rule
        new_lang.version_id = new_lang._compute_version_id()
        return Candidate.create(
            new_lang, [parent_a.version_id, parent_b.version_id], "crossover",
        )

    def generate_candidates(self, language: Language,
                            count: int = 4) -> list[Candidate]:
        """Generate a set of candidate mutations from a language."""
        candidates: list[Candidate] = []
        for i in range(count):
            kind = self.rng.choice(["symbol", "grammar", "semantics"])
            if kind == "symbol":
                candidates.append(self.mutate_symbol(language, language.version_id))
            elif kind == "grammar":
                candidates.append(self.mutate_grammar(language, language.version_id))
            else:
                candidates.append(self.mutate_semantics(language, language.version_id))
        return candidates


class FitnessEvaluator:
    """Evaluates candidate language versions.

    Fitness combines:
      - communication success (referential game between two agents using the
        candidate language),
      - language expressiveness (ability to encode/compile sample programs),
      - vocabulary stability (penalty for excessive growth).

    All evaluations are deterministic given a seed.
    """

    def __init__(self, rng: random.Random | None = None) -> None:
        self.rng = rng or random.Random()

    def evaluate_communication(self, language: Language,
                               rounds: int = 200,
                               seed: int = 0) -> float:
        """Referential-game communication success for a language.

        Two agents encode/decode concepts using the candidate language's
        vocabulary. Returns success rate in [0, 1].
        """
        from eal_cl import Channel, Encoder, Decoder
        from eal_brain import Agent
        from eal_core.identity import AgentIdentity

        rng = random.Random(seed)
        concepts = [f"c-{i}" for i in range(6)]
        symbol_pool = list(language.vocabulary.ids()) or [f"fallback-{i}" for i in range(6)]

        alice = Agent(AgentIdentity.generate(), seed=seed)
        bob = Agent(AgentIdentity.generate(), seed=seed + 1)
        # Seed both agents' vocabularies with the candidate language symbols.
        for sym in language.vocabulary:
            alice.state.set_belief(f"sym:{sym.id}", 1.0)
            bob.state.set_belief(f"sym:{sym.id}", 1.0)

        channel = Channel("alice", "bob")
        successes = 0
        for _ in range(rounds):
            concept = rng.choice(concepts)
            symbols = alice.encoder.encode(concept, available_symbols=symbol_pool)
            channel.send("alice", symbols, concept)
            msg = channel.receive("bob")
            if msg is None:
                continue
            guess = bob.decoder.decode(msg.symbols, candidate_concepts=concepts)
            correct = guess == concept
            reward = 1.0 if correct else 0.0
            alice.encoder.reinforce(concept, symbols, reward)
            bob.decoder.reinforce(msg.symbols, guess, reward)
            successes += int(correct)
        return successes / rounds if rounds else 0.0

    def evaluate_expressiveness(self, language: Language) -> float:
        """Language expressiveness proxy: symbol/rule richness.

        A language with at least some symbols and rules is more expressive.
        Returns a value in [0, 1].
        """
        symbols = len(language.vocabulary)
        rules = len(language.grammar)
        # Diminishing returns; cap at a modest target.
        symbol_score = min(symbols / 8.0, 1.0)
        rule_score = min(rules / 4.0, 1.0)
        return 0.6 * symbol_score + 0.4 * rule_score

    def evaluate_stability(self, language: Language,
                           prior: Language | None) -> float:
        """Vocabulary/grammar stability relative to a prior version.

        Returns 1.0 if identical, lower if many symbols/rules changed.
        """
        if prior is None:
            return 1.0
        sym_a = set(language.vocabulary.ids())
        sym_b = set(prior.vocabulary.ids())
        rule_a = set(language.grammar.ids())
        rule_b = set(prior.grammar.ids())
        if not sym_a and not rule_a:
            return 0.0
        def overlap(a: set, b: set) -> float:
            union = a | b
            if not union:
                return 1.0  # both empty: perfectly stable in this category
            return len(a & b) / len(union)

        sym_overlap = overlap(sym_a, sym_b)
        rule_overlap = overlap(rule_a, rule_b)
        return 0.5 * sym_overlap + 0.5 * rule_overlap

    def evaluate(self, candidate: Candidate,
                 prior: Language | None = None,
                 rounds: int = 200,
                 seed: int = 0,
                 weights: dict[str, float] | None = None) -> float:
        """Overall fitness in [0, 1]. Higher is better."""
        w = {"communication": 0.5, "expressiveness": 0.3, "stability": 0.2}
        if weights:
            w.update(weights)
        comm = self.evaluate_communication(candidate.language, rounds=rounds,
                                           seed=seed)
        expr = self.evaluate_expressiveness(candidate.language)
        stab = self.evaluate_stability(candidate.language, prior)
        fitness = w["communication"] * comm + w["expressiveness"] * expr + w["stability"] * stab
        candidate.fitness = fitness
        return fitness


class EvolutionEngine:
    """Autonomous language evolution engine.

    Detects limitations in the current stable language, proposes candidate
    structures, evaluates them, selects the best, preserves history, and can
    roll back unsuccessful experiments.
    """

    def __init__(self, store: VersionStore,
                 mutator: MutationOperator | None = None,
                 evaluator: FitnessEvaluator | None = None,
                 rng: random.Random | None = None,
                 config: Config | None = None) -> None:
        self.store = store
        self.mutator = mutator or MutationOperator(rng=rng)
        self.evaluator = evaluator or FitnessEvaluator(rng=rng)
        self.rng = rng or random.Random()
        self.config = config or Config()
        self._experiments: list[ExperimentRecord] = []

    def stable_language(self) -> Language:
        """Return the current stable language as a mutable Language."""
        version = self.store.stable()
        if version is None:
            return Language.create()
        lang = Language.create()
        lang.apply(version)
        return lang

    def run_experiment(self, hypothesis: str,
                       generations: int = 3,
                       candidates_per_gen: int = 4,
                       selection_threshold: float = 0.6,
                       rounds_per_eval: int = 150,
                       seed: int = 0) -> EvolutionResult:
        """Run a controlled evolution experiment.

        Each generation: generate candidates from the current stable language,
        evaluate fitness, select the best above threshold, promote to stable,
        archive all candidates. If no candidate meets the threshold, the
        experiment is rejected and (optionally) the prior stable version is
        preserved unchanged (no rollback needed because stable was never
        overwritten).
        """
        rng = random.Random(seed)
        current = self.stable_language()
        evaluated: dict[str, float] = {}
        selected: Candidate | None = None
        rollback = False
        accepted = False

        for gen in range(generations):
            candidates = self.mutator.generate_candidates(current,
                                                          count=candidates_per_gen)
            # Also try crossover if we have history.
            prior_versions = [self.store.get(vid) for vid in self.store.history()]
            prior_langs = []
            for vd in prior_versions:
                if vd is None:
                    continue
                l = Language.create()
                l.apply(vd)
                prior_langs.append(l)
            if len(prior_langs) >= 2:
                a, b = self.rng.sample(prior_langs, k=2)
                candidates.append(self.mutator.crossover(a, b))

            best: Candidate | None = None
            best_fitness = -1.0
            prior_lang = current

            for cand in candidates:
                fit = self.evaluator.evaluate(
                    cand, prior=prior_lang, rounds=rounds_per_eval,
                    seed=seed + len(evaluated),
                )
                evaluated[cand.candidate_id] = fit
                self.store.archive(cand.language.snapshot())
                if fit > best_fitness:
                    best_fitness = fit
                    best = cand

            if best is not None and best_fitness >= selection_threshold:
                # Promote best candidate to stable.
                self.store.set_stable(best.candidate_id)
                selected = best
                current = best.language
                accepted = True
            else:
                # No candidate good enough this generation; keep current stable.
                rollback = True  # experiment did not improve; stable preserved
                break

        # Record the experiment.
        record = ExperimentRecord(
            experiment_id="evo-" + hashlib.sha256(
                json.dumps({"hypothesis": hypothesis, "seed": seed},
                           sort_keys=True).encode()).hexdigest()[:32],
            hypothesis=hypothesis,
            config=self.config.with_seed(seed),
            code_version="eal-evolution/1.0",
            seed=seed,
            baseline="current stable language",
            results=ExperimentResult(
                communication_success=selected.fitness if selected else None,
            ),
            limitations="referential-game proxy only; no NVIDIA RL backend",
            decision="accept" if accepted else "reject",
        )
        self._experiments.append(record.finalize())
        return EvolutionResult(
            selected_candidate=selected,
            evaluated=evaluated,
            accepted=accepted,
            rollback_performed=rollback,
        )

    def rollback_to(self, version_id: str) -> LanguageVersion:
        """Restore an archived version as the new stable (rollback)."""
        version = self.store.get(version_id)
        if version is None:
            raise KeyError(f"unknown version {version_id}")
        self.store.set_stable(version_id)
        return version

    def experiments(self) -> list[ExperimentRecord]:
        return list(self._experiments)
