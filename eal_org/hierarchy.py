"""EAL-ORG: hierarchy management.

Agents are organized in a tree hierarchy. Rules (spec §5 EAL-ORG):
- Every agent has a unique identifier and a defined role/scope.
- Every subordinate has an identifiable supervision relationship.
- Delegation is traceable to the original objective.
- Agents cannot assume permissions above those granted.
- New hierarchy levels may be created.
- Cycles of dependency/delegation are detected and prevented.
- Orphan hierarchies are prevented.
- Reorganization preserves historical relationships.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class HierarchyNode:
    """A node in the organization hierarchy."""

    agent_id: str
    parent: Optional[str] = None
    children: list[str] = field(default_factory=list)
    depth: int = 0

    def add_child(self, child_id: str) -> None:
        if child_id not in self.children:
            self.children.append(child_id)

    def remove_child(self, child_id: str) -> None:
        self.children = [c for c in self.children if c != child_id]


class HierarchyManager:
    """Manages the organization hierarchy tree.

    Guarantees: single root (or forest), no cycles, no orphans (every
    non-root node has a parent that exists), supervision traceability.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, HierarchyNode] = {}

    def add_agent(self, agent_id: str,
                  parent_id: Optional[str] = None) -> bool:
        """Add ``agent_id`` under ``parent_id`` (or as root if None).

        Returns False if the agent already exists, the parent is missing, or
        adding would create a cycle.
        """
        if agent_id in self._nodes:
            return False
        if parent_id is not None and parent_id not in self._nodes:
            return False
        # Cycle check: agent must not be an ancestor of parent.
        if parent_id is not None and self._is_ancestor(agent_id, parent_id):
            return False
        node = HierarchyNode(agent_id=agent_id, parent=parent_id,
                             depth=0)
        self._nodes[agent_id] = node
        if parent_id is not None:
            self._nodes[parent_id].add_child(agent_id)
            node.depth = self._nodes[parent_id].depth + 1
            self._update_depths(agent_id)
        return True

    def _is_ancestor(self, possible_ancestor: str, node_id: str) -> bool:
        """True if ``possible_ancestor`` is an ancestor of ``node_id``."""
        visited = set()
        current = node_id
        while current is not None and current in self._nodes:
            if current == possible_ancestor:
                return True
            if current in visited:  # safety against unexpected cycles
                return False
            visited.add(current)
            current = self._nodes[current].parent
        return False

    def _update_depths(self, agent_id: str) -> None:
        node = self._nodes[agent_id]
        for child_id in node.children:
            self._nodes[child_id].depth = node.depth + 1
            self._update_depths(child_id)

    def reparent(self, agent_id: str, new_parent: Optional[str]) -> bool:
        """Move ``agent_id`` under ``new_parent`` (reorganization).

        Preserves the historical parent relationship implicitly via audit log
        (handled by GovernancePolicyEngine). Returns False on invalid move.
        """
        if agent_id not in self._nodes:
            return False
        if new_parent is not None and new_parent not in self._nodes:
            return False
        if new_parent is not None and self._is_ancestor(agent_id, new_parent):
            return False
        old_parent = self._nodes[agent_id].parent
        if old_parent is not None:
            self._nodes[old_parent].remove_child(agent_id)
        self._nodes[agent_id].parent = new_parent
        if new_parent is not None:
            self._nodes[new_parent].add_child(agent_id)
            self._nodes[agent_id].depth = self._nodes[new_parent].depth + 1
            self._update_depths(agent_id)
        else:
            self._nodes[agent_id].depth = 0
            self._update_depths(agent_id)
        return True

    def remove_agent(self, agent_id: str,
                     reparent_children_to: Optional[str] = None) -> bool:
        """Remove ``agent_id``; orphans are prevented by reparenting children."""
        if agent_id not in self._nodes:
            return False
        node = self._nodes[agent_id]
        children = list(node.children)
        for child_id in children:
            if reparent_children_to is not None:
                self.reparent(child_id, reparent_children_to)
            else:
                # Promote to root (avoids orphan).
                self.reparent(child_id, None)
        # Remove from parent's children.
        if node.parent is not None:
            self._nodes[node.parent].remove_child(agent_id)
        del self._nodes[agent_id]
        return True

    def parent(self, agent_id: str) -> Optional[str]:
        node = self._nodes.get(agent_id)
        return node.parent if node else None

    def children(self, agent_id: str) -> list[str]:
        node = self._nodes.get(agent_id)
        return list(node.children) if node else []

    def is_root(self, agent_id: str) -> bool:
        node = self._nodes.get(agent_id)
        return node is not None and node.parent is None

    def roots(self) -> list[str]:
        return [aid for aid, n in self._nodes.items() if n.parent is None]

    def depth(self, agent_id: str) -> int:
        node = self._nodes.get(agent_id)
        return node.depth if node else -1

    def path_to_root(self, agent_id: str) -> list[str]:
        """Delegation trace from ``agent_id`` up to its root supervisor."""
        path: list[str] = []
        current = agent_id
        visited = set()
        while current is not None and current in self._nodes:
            if current in visited:
                break
            visited.add(current)
            path.append(current)
            current = self._nodes[current].parent
        return path

    def agents(self) -> list[str]:
        return list(self._nodes.keys())

    def contains(self, agent_id: str) -> bool:
        return agent_id in self._nodes

    def snapshot(self) -> dict[str, object]:
        return {
            "nodes": {
                aid: {
                    "parent": n.parent,
                    "children": list(n.children),
                    "depth": n.depth,
                }
                for aid, n in self._nodes.items()
            },
            "roots": self.roots(),
        }
