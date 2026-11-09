"""Versioned grammar for EAL-CL.

Grammar rules describe how symbols compose into structures. They carry no
hardcoded semantics: a rule is a structural pattern only. Meaning is assigned
by the agents that use the grammar, not by the rule definition.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class GrammarRule:
    """An immutable structural composition rule.

    Attributes:
        id: Unique rule identifier.
        pattern: Tuple of symbol ids describing the left-hand composition.
        structure: String describing the resulting structure (semantics-free).
        metadata: JSON-serializable annotation.
    """

    id: str
    pattern: tuple[str, ...]
    structure: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Grammar:
    """A mutable, versioned collection of grammar rules.

    Attributes:
        version_id: Content-stable identifier for this grammar version.
        rules: Mapping of rule id -> GrammarRule.
    """

    version_id: str
    rules: dict[str, GrammarRule] = field(default_factory=dict)

    @classmethod
    def create(cls) -> "Grammar":
        grammar = cls(version_id="v0")
        grammar.version_id = grammar._compute_version_id()
        return grammar

    def add_rule(self, rule: GrammarRule) -> None:
        self.rules[rule.id] = rule
        self.version_id = self._compute_version_id()

    def remove_rule(self, rule_id: str) -> GrammarRule | None:
        removed = self.rules.pop(rule_id, None)
        if removed is not None:
            self.version_id = self._compute_version_id()
        return removed

    def get(self, rule_id: str) -> GrammarRule | None:
        return self.rules.get(rule_id)

    def __len__(self) -> int:
        return len(self.rules)

    def ids(self) -> list[str]:
        return sorted(self.rules.keys())

    def snapshot(self) -> dict[str, Any]:
        return {
            "version_id": self.version_id,
            "rules": {
                rid: {
                    "id": r.id,
                    "pattern": list(r.pattern),
                    "structure": r.structure,
                    "metadata": r.metadata,
                }
                for rid, r in self.rules.items()
            },
        }

    @classmethod
    def load(cls, snapshot: dict[str, Any]) -> "Grammar":
        grammar = cls(version_id=snapshot["version_id"])
        for rid, data in snapshot.get("rules", {}).items():
            grammar.rules[rid] = GrammarRule(
                id=data["id"],
                pattern=tuple(data["pattern"]),
                structure=data["structure"],
                metadata=dict(data.get("metadata") or {}),
            )
        grammar.version_id = grammar._compute_version_id()
        return grammar

    def _content(self) -> dict[str, Any]:
        """Content used for versioning (excludes version_id to avoid a
        self-referential hash)."""
        return {
            "rules": {
                rid: {
                    "id": r.id,
                    "pattern": list(r.pattern),
                    "structure": r.structure,
                    "metadata": r.metadata,
                }
                for rid, r in sorted(self.rules.items())
            },
        }

    def _compute_version_id(self) -> str:
        payload = json.dumps(self._content(), sort_keys=True).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()[:32]
