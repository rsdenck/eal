"""EAL-PL type system.

A simple, original type system: int, bool, string, void, and function types.
Type environments map names to types during semantic analysis. Subtyping is
minimal (no implicit coercion) so type errors are caught early and precisely.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .ast import Type, INT, BOOL, STRING, VOID, function_type


@dataclass
class TypeEnv:
    """A lexical type environment with nested scopes."""

    bindings: dict[str, Type] = field(default_factory=dict)
    parent: "TypeEnv | None" = None

    def define(self, name: str, typ: Type) -> None:
        self.bindings[name] = typ

    def resolve(self, name: str) -> Type | None:
        if name in self.bindings:
            return self.bindings[name]
        if self.parent is not None:
            return self.parent.resolve(name)
        return None

    def child(self) -> "TypeEnv":
        return TypeEnv(parent=self)


def compatible(param_type: Type, arg_type: Type) -> bool:
    """Argument type compatibility with a parameter type (no implicit coercion).

    An untyped parameter (VOID) accepts any argument type.
    """
    if param_type == VOID:
        return True
    if param_type == arg_type:
        return True
    return False
