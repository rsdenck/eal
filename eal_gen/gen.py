"""EAL-GEN: genetic mechanisms for language evolution.

Controls mutations, combinations, branching and selection of versions of
vocabularies, grammars, operators and semantic rules.

Provides:
- Genetic representation of language versions (genome).
- Mutation operators on the genome.
- Crossover (recombination) between two language genomes.
- Selection based on fitness.
- Branching: multiple parallel language lineages.
- Generation tracking.
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass, field
from typing import Any

from eal_cl import Grammar, GrammarRule, Language, Symbol, Vocabulary


@dataclass(frozen=True)
class Genome:
    """Genetic representation of a language version.

    Attributes:
        genome_id: Content-stable hash of the genome.
        vocabulary: Serialized vocabulary.
        grammar: Serialized grammar.
        generation: Generation number.
        lineage: List of ancestor genome ids.
    """

    genome_id: str
    vocabulary: dict[str, Any]
    grammar: dict[str, Any]
    generation: int
    lineage: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def from_language(cls, language: Language,
                      generation: int = 0,
                      lineage: tuple[str, ...] = ()) -> "Genome":
        vocab = language.vocabulary.snapshot()
        gram = language.grammar.snapshot()
        payload = json.dumps(
            {"vocabulary": vocab, "grammar": gram},
            sort_keys=True,
        ).encode("utf-8")
        gid = hashlib.sha256(payload).hexdigest()[:32]
        return cls(
            genome_id=gid,
            vocabulary=vocab,
            grammar=gram,
            generation=generation,
            lineage=lineage,
        )

    def compute_id(self) -> str:
        """Recompute the content-stable id (should match genome_id)."""
        payload = json.dumps(
            {"vocabulary": self.vocabulary, "grammar": self.grammar},
            sort_keys=True,
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()[:32]

    def to_language(self) -> Language:
        lang = Language(
            grammar=Grammar.load(self.grammar),
            vocabulary=Vocabulary.load(self.vocabulary),
        )
        lang.version_id = self.genome_id or self.compute_id()
        return lang


@dataclass
class GeneticIndividual:
    """An individual in the genetic population: a genome plus fitness."""

    genome: Genome
    fitness: float | None = None
    evaluated: bool = False


class GeneticLanguageEvolution:
    """Genetic evolution of language versions.

    Maintains a population of language genomes and applies:
    - mutation (symbol, grammar, semantics)
    - crossover (recombination of two genomes)
    - selection (fitness-based)
    - branching (lineages)
    """

    def __init__(self, rng: random.Random | None = None,
                 mutation_rate: float = 0.1,
                 crossover_rate: float = 0.3) -> None:
        self.rng = rng or random.Random()
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.population: dict[str, GeneticIndividual] = {}
        self.generation = 0
        self._history: list[str] = []  # genome ids in order of creation

    def add_individual(self, language: Language,
                       fitness: float | None = None) -> str:
        """Add a language to the population. Returns genome id."""
        genome = Genome.from_language(
            language, generation=self.generation)
        gid = genome.compute_id()
        genome = Genome(
            genome_id=gid, vocabulary=genome.vocabulary,
            grammar=genome.grammar, generation=genome.generation,
            lineage=genome.lineage,
        )
        self.population[gid] = GeneticIndividual(
            genome=genome, fitness=fitness)
        self._history.append(gid)
        return gid

    def get(self, genome_id: str) -> GeneticIndividual | None:
        return self.population.get(genome_id)

    def mutate_genome(self, genome: Genome) -> Genome:
        """Apply a random mutation to a genome, returning a new genome."""
        lang = genome.to_language()
        # Choose mutation type.
        kind = self.rng.choice(["symbol", "grammar", "semantics"])
        if kind == "symbol":
            symbol = Symbol.generate(
                metadata={"origin": "genetic_mutation",
                          "generation": self.generation + 1})
            lang.add_symbol(symbol)
        elif kind == "grammar":
            rule = GrammarRule(
                id=f"g{self.rng.randint(0, 10**6)}",
                pattern=(),
                structure="genetic_rule",
                metadata={"origin": "genetic_mutation"},
            )
            lang.add_rule(rule)
        else:
            # Semantics: adjust metadata bias on symbols.
            for sym in lang.vocabulary:
                sym.metadata = dict(sym.metadata or {})
                sym.metadata["bias"] = self.rng.random()
            lang.version_id = lang._compute_version_id()
        new_genome = Genome.from_language(
            lang, generation=self.generation + 1,
            lineage=(genome.genome_id,))
        gid = new_genome.compute_id()
        new_genome = Genome(
            genome_id=gid, vocabulary=new_genome.vocabulary,
            grammar=new_genome.grammar, generation=new_genome.generation,
            lineage=new_genome.lineage,
        )
        return new_genome

    def crossover_genomes(self, g1: Genome, g2: Genome) -> Genome:
        """Recombine two genomes into a new offspring genome."""
        lang1 = g1.to_language()
        lang2 = g2.to_language()
        # Start from lang1, merge symbols and rules from lang2.
        for sym in lang2.vocabulary:
            if sym.id not in lang1.vocabulary.symbols:
                lang1.vocabulary.symbols[sym.id] = sym
        for rule in lang2.grammar.rules.values():
            if rule.id not in lang1.grammar.rules:
                lang1.grammar.rules[rule.id] = rule
        new_genome = Genome.from_language(
            lang1, generation=self.generation + 1,
            lineage=(g1.genome_id, g2.genome_id),
        )
        gid = new_genome.compute_id()
        new_genome = Genome(
            genome_id=gid, vocabulary=new_genome.vocabulary,
            grammar=new_genome.grammar, generation=new_genome.generation,
            lineage=new_genome.lineage,
        )
        return new_genome

    def evolve_generation(self,
                          fitness_fn) -> dict[str, Any]:
        """Evolve the population by one generation.

        Args:
            fitness_fn: Function(Genome) -> float fitness.

        Returns:
            Summary of the generation (ids, best, etc.).
        """
        # Evaluate fitness for all individuals.
        for gid, ind in self.population.items():
            if not ind.evaluated:
                ind.fitness = fitness_fn(ind.genome)
                ind.evaluated = True

        # Selection: keep top individuals as parents.
        sorted_ids = sorted(
            self.population.keys(),
            key=lambda gid: (self.population[gid].fitness or 0.0),
            reverse=True,
        )
        top_count = max(1, len(sorted_ids) // 2)
        parents = sorted_ids[:top_count]

        # Generate offspring via mutation and crossover.
        offspring: list[Genome] = []
        for pid in parents:
            parent = self.population[pid].genome
            if self.rng.random() < self.mutation_rate:
                offspring.append(self.mutate_genome(parent))
            if self.rng.random() < self.crossover_rate and len(parents) >= 2:
                other_pid = self.rng.choice([p for p in parents if p != pid])
                offspring.append(
                    self.crossover_genomes(parent,
                                           self.population[other_pid].genome))

        # Add offspring to population.
        new_ids = []
        for genome in offspring:
            gid = self.add_individual(genome.to_language())
            new_ids.append(gid)

        self.generation += 1
        # Best individual.
        best_gid = sorted_ids[0] if sorted_ids else None
        best_fitness = (self.population[best_gid].fitness
                        if best_gid else None)
        return {
            "generation": self.generation - 1,
            "population_size": len(self.population),
            "new_offspring": len(new_ids),
            "best_genome": best_gid,
            "best_fitness": best_fitness,
        }

    def snapshot(self) -> dict[str, Any]:
        return {
            "generation": self.generation,
            "population": {
                gid: {
                    "genome_id": ind.genome.genome_id,
                    "generation": ind.genome.generation,
                    "lineage": list(ind.genome.lineage),
                    "fitness": ind.fitness,
                    "evaluated": ind.evaluated,
                }
                for gid, ind in self.population.items()
            },
            "history": list(self._history),
        }
