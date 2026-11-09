"""EAL-PL Abstract Syntax Tree.

Each node carries a source location for precise error reporting and debugging.
The grammar is original: `bind` (immutable), `mut` (mutable), `fn`, `loop`,
`if`/`else`, `return`, `print`. It is not a rename of Python, Rust or Go.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .errors import SourceLocation


@dataclass
class Node:
    location: SourceLocation


# -- declarations ---------------------------------------------------------

@dataclass
class Program(Node):
    statements: list


@dataclass
class BindStmt(Node):
    name: str
    type_annotation: str | None
    value: object  # Expression


@dataclass
class MutStmt(Node):
    name: str
    type_annotation: str | None
    value: object  # Expression


@dataclass
class FnStmt(Node):
    name: str
    params: list  # list of (name, type_annotation)
    return_type: str | None
    body: object  # BlockStmt


@dataclass
class BlockStmt(Node):
    statements: list


# -- statements -----------------------------------------------------------

@dataclass
class ExprStmt(Node):
    expression: object


@dataclass
class IfStmt(Node):
    condition: object
    then_branch: object
    else_branch: object | None


@dataclass
class LoopStmt(Node):
    body: object


@dataclass
class BreakStmt(Node):
    pass


@dataclass
class ContinueStmt(Node):
    pass


@dataclass
class ReturnStmt(Node):
    value: object | None


@dataclass
class PrintStmt(Node):
    expression: object


# -- expressions ----------------------------------------------------------

@dataclass
class Literal(Node):
    value: Any


@dataclass
class Variable(Node):
    name: str


@dataclass
class Assignment(Node):
    name: str
    value: object  # Expression


@dataclass
class Binary(Node):
    left: object
    operator: str  # token lexeme
    right: object


@dataclass
class Unary(Node):
    operator: str
    operand: object


@dataclass
class Call(Node):
    callee: str
    arguments: list


# -- types ----------------------------------------------------------------

@dataclass(frozen=True)
class Type:
    name: str  # "int", "bool", "string", "void"
    params: tuple = field(default_factory=tuple)  # for function types (args, ret)

    def __str__(self) -> str:
        if self.name == "fn":
            args = ", ".join(str(p) for p in self.params[0])
            return f"fn({args}) -> {self.params[1]}"
        return self.name

    def __eq__(self, other) -> bool:
        if not isinstance(other, Type):
            return NotImplemented
        return self.name == other.name and self.params == other.params

    def __hash__(self) -> int:
        return hash((self.name, self.params))


INT = Type("int")
BOOL = Type("bool")
STRING = Type("string")
VOID = Type("void")

NUMERIC_TYPES = (INT,)
BOOL_TYPES = (BOOL,)
STRING_TYPES = (STRING,)


def function_type(param_types: tuple, return_type: Type) -> Type:
    return Type("fn", params=(param_types, return_type))


@dataclass
class FunctionSignature:
    name: str
    param_types: tuple
    return_type: Type

    def as_type(self) -> Type:
        return function_type(self.param_types, self.return_type)
