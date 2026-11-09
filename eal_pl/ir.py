"""EAL-PL intermediate representation (bytecode).

The IR is a linear list of instructions executed by a stack-based virtual
machine. Each instruction carries an optional source location so runtime and
compile-time errors can be mapped back to source text.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class Op:
    CONST = "CONST"        # push constant
    LOAD = "LOAD"          # load variable
    STORE = "STORE"        # store variable
    ADD = "ADD"
    SUB = "SUB"
    MUL = "MUL"
    DIV = "DIV"
    EQ = "EQ"
    NE = "NE"
    LT = "LT"
    GT = "GT"
    LE = "LE"
    GE = "GE"
    NOT = "NOT"
    NEG = "NEG"
    JMP = "JMP"
    JMP_IF = "JMP_IF"      # jump if top is falsy
    JMP_IF_NOT = "JMP_IF_NOT"  # jump if top is truthy
    CALL = "CALL"          # call function (arity popped as operand)
    RETURN = "RETURN"
    PRINT = "PRINT"
    HALT = "HALT"


@dataclass
class Instruction:
    op: str
    arg: Any = None
    location: Any = None  # SourceLocation | None

    def __repr__(self) -> str:  # pragma: no cover - trivial
        arg = f" {self.arg!r}" if self.arg is not None else ""
        return f"{self.op}{arg}"


@dataclass
class IR:
    """A compiled IR unit: instructions plus a constant pool."""

    instructions: list[Instruction] = field(default_factory=list)
    constants: list[Any] = field(default_factory=list)

    def add(self, op: str, arg: Any = None, location: Any = None) -> int:
        self.instructions.append(Instruction(op=op, arg=arg, location=location))
        return len(self.instructions) - 1

    def patch(self, index: int, target: int) -> None:
        self.instructions[index].arg = target

    def constant(self, value: Any) -> int:
        if value in self.constants:
            return self.constants.index(value)
        self.constants.append(value)
        return len(self.constants) - 1
