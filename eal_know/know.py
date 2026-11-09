"""EAL-KNOW: evolutionary knowledge store.

Stores discoveries, experiments, rejected languages, winning versions and
reasons for decisions. Avoids repeating experiments unnecessarily.

Provides:
- Append-only knowledge base of experiment outcomes.
- Language version registry (accepted / rejected).
- Decision rationale storage.
- Experiment deduplication (avoid repeating equivalent experiments).
- Query interface for the evolution engine and learning loop.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class KnowledgeEntry:
    """An immutable entry in the knowledge base."""

    entry_id: str
    kind: str  # "experiment", "language_version", "decision", "rejection"
    content: dict[str, Any]
    timestamp: str
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "kind": self.kind,
            "content": self.content,
            "timestamp": self.timestamp,
            "rationale": self.rationale,
        }


class KnowledgeBase:
    """EAL-KNOW: evolutionary knowledge store.

    All entries are append-only and immutable. The knowledge base supports
    deduplication: equivalent experiments (same hypothesis + config hash) are
    not recorded twice.
    """

    def __init__(self) -> None:
        self._entries: dict[str, KnowledgeEntry] = {}
        self._order: list[str] = []
        self._experiment_hashes: set[str] = set()

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _entry_id(self, kind: str, content: dict[str, Any]) -> str:
        payload = json.dumps({"kind": kind, "content": content},
                             sort_keys=True).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()[:32]

    def record_experiment(self, hypothesis: str,
                          config: dict[str, Any],
                          results: dict[str, Any],
                          decision: str,
                          rationale: str) -> str:
        """Record an experiment outcome. Returns entry id.

        Deduplicates by hypothesis + config hash.
        """
        dedupe_hash = hashlib.sha256(
            json.dumps({"hypothesis": hypothesis, "config": config},
                       sort_keys=True).encode()).hexdigest()
        if dedupe_hash in self._experiment_hashes:
            # Return existing entry id for this experiment.
            for eid in self._order:
                entry = self._entries[eid]
                if (entry.kind == "experiment" and
                        entry.content.get("_dedupe_hash") == dedupe_hash):
                    return eid
        entry = KnowledgeEntry(
            entry_id=self._entry_id("experiment", {
                "hypothesis": hypothesis, "config": config,
                "results": results, "decision": decision}),
            kind="experiment",
            content={
                "hypothesis": hypothesis,
                "config": config,
                "results": results,
                "decision": decision,
                "_dedupe_hash": dedupe_hash,
            },
            timestamp=self._now(),
            rationale=rationale,
        )
        self._entries[entry.entry_id] = entry
        self._order.append(entry.entry_id)
        self._experiment_hashes.add(dedupe_hash)
        return entry.entry_id

    def record_language_version(self, version_id: str,
                                language_snapshot: dict[str, Any],
                                status: str,  # "accepted", "rejected", "candidate"
                                rationale: str) -> str:
        """Record a language version and its status."""
        entry = KnowledgeEntry(
            entry_id=self._entry_id("language_version", {
                "version_id": version_id, "status": status}),
            kind="language_version",
            content={
                "version_id": version_id,
                "snapshot": language_snapshot,
                "status": status,
            },
            timestamp=self._now(),
            rationale=rationale,
        )
        self._entries[entry.entry_id] = entry
        self._order.append(entry.entry_id)
        return entry.entry_id

    def record_decision(self, decision_id: str,
                        decision: str,  # "accept", "reject", "investigate"
                        rationale: str,
                        context: dict[str, Any] | None = None) -> str:
        """Record a high-level decision with rationale."""
        entry = KnowledgeEntry(
            entry_id=self._entry_id("decision", {
                "decision_id": decision_id, "decision": decision}),
            kind="decision",
            content={
                "decision_id": decision_id,
                "decision": decision,
                "context": context or {},
            },
            timestamp=self._now(),
            rationale=rationale,
        )
        self._entries[entry.entry_id] = entry
        self._order.append(entry.entry_id)
        return entry.entry_id

    def get(self, entry_id: str) -> KnowledgeEntry | None:
        return self._entries.get(entry_id)

    def entries(self) -> list[KnowledgeEntry]:
        return [self._entries[eid] for eid in self._order]

    def entries_by_kind(self, kind: str) -> list[KnowledgeEntry]:
        return [e for e in self.entries() if e.kind == kind]

    def accepted_languages(self) -> list[dict[str, Any]]:
        return [e.content for e in self.entries_by_kind("language_version")
                if e.content.get("status") == "accepted"]

    def rejected_languages(self) -> list[dict[str, Any]]:
        return [e.content for e in self.entries_by_kind("language_version")
                if e.content.get("status") == "rejected"]

    def experiment_decision(self, hypothesis: str,
                            config: dict[str, Any]) -> dict[str, Any] | None:
        """Return the recorded decision for an equivalent experiment, if any."""
        dedupe_hash = hashlib.sha256(
            json.dumps({"hypothesis": hypothesis, "config": config},
                       sort_keys=True).encode()).hexdigest()
        for eid in self._order:
            entry = self._entries[eid]
            if (entry.kind == "experiment" and
                    entry.content.get("_dedupe_hash") == dedupe_hash):
                return entry.to_dict()
        return None

    def snapshot(self) -> dict[str, Any]:
        return {
            "total_entries": len(self._entries),
            "by_kind": {
                k: len(self.entries_by_kind(k))
                for k in ("experiment", "language_version", "decision",
                          "rejection")
            },
            "accepted_languages": len(self.accepted_languages()),
            "rejected_languages": len(self.rejected_languages()),
        }
