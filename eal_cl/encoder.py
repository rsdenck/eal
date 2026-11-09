"""Learnable encoder/decoder for EAL-CL.

The encoder maps a concept (any hashable meaning) to a sequence of symbol ids,
and the decoder maps a symbol sequence back to a concept. These mappings are
learnable: they are updated through interaction and carry no hardcoded symbol
meanings.

This is the minimal referential-game learning core: agents maintain concept <-
> symbol associations and reinforce mappings that lead to successful
communication.
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass, field
from typing import Any, Hashable


@dataclass
class SymbolAssociation:
    """A learned association between a concept and a symbol sequence.

    Attributes:
        concept: The communicated meaning (hashable).
        symbols: Tuple of symbol ids used to express the concept.
        strength: Learned confidence in this mapping (>= 0).
        uses: Number of times the mapping was used.
        successes: Number of times the mapping led to successful decoding.
    """

    concept: Hashable
    symbols: tuple[str, ...]
    strength: float = 1.0
    uses: int = 0
    successes: int = 0

    @property
    def success_rate(self) -> float:
        return self.successes / self.uses if self.uses else 0.0


class Encoder:
    """Encodes concepts into symbol sequences using a learnable mapping."""

    def __init__(self, rng: random.Random | None = None) -> None:
        self._associations: dict[Hashable, SymbolAssociation] = {}
        self._symbol_to_concept: dict[tuple[str, ...], Hashable] = {}
        self.rng = rng or random.Random()

    def encode(self, concept: Hashable,
               available_symbols: list[str] | None = None) -> tuple[str, ...]:
        """Return the symbol sequence for ``concept``.

        If the concept has a learned association above a threshold, reuse it
        (biased toward strongest). Otherwise, generate a fresh symbol sequence
        from ``available_symbols`` and record a new association.
        """
        assoc = self._associations.get(concept)
        if assoc is not None and assoc.strength >= 0.5:
            return assoc.symbols

        if available_symbols:
            length = self.rng.randint(1, max(1, min(3, len(available_symbols))))
            symbols = tuple(self.rng.sample(available_symbols, k=length))
        else:
            symbols = (f"sym-{self._nonce(concept)}",)

        self._associations[concept] = SymbolAssociation(
            concept=concept, symbols=symbols,
        )
        self._symbol_to_concept[symbols] = concept
        return symbols

    def stored_symbols(self, concept: Hashable) -> tuple[str, ...] | None:
        """Return the stored symbol sequence for ``concept``, if any.

        Used during evaluation so the trained convention is reused rather than
        re-generated (which could produce symbols the decoder does not know).
        """
        assoc = self._associations.get(concept)
        return assoc.symbols if assoc is not None else None

    def reinforce(self, concept: Hashable, symbols: tuple[str, ...],
                  reward: float) -> None:
        """Update association strength based on communication outcome."""
        assoc = self._associations.get(concept)
        if assoc is None:
            assoc = SymbolAssociation(concept=concept, symbols=symbols)
            self._associations[concept] = assoc
        assoc.uses += 1
        if reward > 0:
            assoc.successes += 1
        # Exponential moving average of reward into strength.
        assoc.strength = 0.7 * assoc.strength + 0.3 * reward
        self._symbol_to_concept[symbols] = concept

    def _nonce(self, concept: Hashable) -> str:
        payload = json.dumps(
            {"concept": str(concept)}, sort_keys=True
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()[:8]

    def snapshot(self) -> dict[str, Any]:
        return {
            "associations": {
                json.dumps([str(c)]): {
                    "symbols": list(a.symbols),
                    "strength": a.strength,
                    "uses": a.uses,
                    "successes": a.successes,
                }
                for c, a in self._associations.items()
            },
        }


class Decoder:
    """Decodes symbol sequences into concepts using a learnable mapping."""

    def __init__(self, rng: random.Random | None = None) -> None:
        # symbol sequence -> (concept, strength)
        self._mapping: dict[tuple[str, ...], tuple[Hashable, float]] = {}
        self.rng = rng or random.Random()

    def decode(self, symbols: tuple[str, ...],
               candidate_concepts: list[Hashable] | None = None) -> Hashable:
        """Return the concept for ``symbols``.

        If the sequence is directly mapped, return that concept. Otherwise,
        guess from candidate concepts (or return a sentinel). The guess is
        recorded so it can be reinforced later.
        """
        if symbols in self._mapping:
            return self._mapping[symbols][0]
        if candidate_concepts:
            return self.rng.choice(candidate_concepts)
        return "__unknown__"

    def reinforce(self, symbols: tuple[str, ...], concept: Hashable,
                  reward: float) -> None:
        current = self._mapping.get(symbols)
        current_strength = current[1] if current else 0.0
        new_strength = 0.7 * current_strength + 0.3 * reward
        self._mapping[symbols] = (concept, new_strength)

    def snapshot(self) -> dict[str, Any]:
        return {
            "mapping": {
                json.dumps(list(k)): {"concept": str(v[0]), "strength": v[1]}
                for k, v in self._mapping.items()
            },
        }
