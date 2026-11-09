"""Versioned language: a paired grammar and vocabulary.

A Language is the combination of a :class:`~eal_cl.grammar.Grammar` and a
:class:`~eal_cl.vocabulary.Vocabulary`, captured as an immutable
:class:`LanguageVersion`. Languages are the unit of evolution: the evolution
engine mutates, compares, selects, and rolls back language versions.

No symbol meaning is hardcoded here; semantics live in the agents that use the
language.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from .grammar import Grammar
from .vocabulary import Vocabulary


@dataclass(frozen=True)
class LanguageVersion:
    """An immutable snapshot of a language at a point in time.

    Attributes:
        version_id: Content-stable identifier.
        grammar_snapshot: Serialized grammar.
        vocabulary_snapshot: Serialized vocabulary.
    """

    version_id: str
    grammar_snapshot: dict[str, Any]
    vocabulary_snapshot: dict[str, Any]


class Language:
    """A mutable language composed of a grammar and vocabulary.

    Attributes:
        grammar: The active grammar.
        vocabulary: The active vocabulary.
        version_id: Derived content-stable id of the combined state.
    """

    def __init__(self, grammar: Grammar | None = None,
                 vocabulary: Vocabulary | None = None) -> None:
        self.grammar = grammar or Grammar.create()
        self.vocabulary = vocabulary or Vocabulary.create()
        self.version_id = self._compute_version_id()

    @classmethod
    def create(cls) -> "Language":
        return cls()

    def snapshot(self) -> LanguageVersion:
        return LanguageVersion(
            version_id=self.version_id,
            grammar_snapshot=self.grammar.snapshot(),
            vocabulary_snapshot=self.vocabulary.snapshot(),
        )

    def apply(self, version: LanguageVersion) -> None:
        """Replace this language's state with an archived version (rollback)."""
        self.grammar = Grammar.load(version.grammar_snapshot)
        self.vocabulary = Vocabulary.load(version.vocabulary_snapshot)
        self.version_id = version.version_id

    def add_symbol(self, symbol) -> None:
        self.vocabulary.add(symbol)
        self.version_id = self._compute_version_id()

    def add_rule(self, rule) -> None:
        self.grammar.add_rule(rule)
        self.version_id = self._compute_version_id()

    def _content(self) -> dict[str, Any]:
        """Content used for versioning (excludes version_id)."""
        return {
            "grammar": self.grammar._content(),
            "vocabulary": self.vocabulary._content(),
        }

    def _compute_version_id(self) -> str:
        payload = json.dumps(self._content(), sort_keys=True).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()[:32]

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return (f"Language(version={self.version_id[:8]}..., "
                f"symbols={len(self.vocabulary)}, rules={len(self.grammar)})")
