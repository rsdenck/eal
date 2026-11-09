"""EAL-PL errors with source locations.

Every error carries a source location (file, line, column) so debugging
reports point at the exact program text. Errors are structured, not formatted
strings, so consumers (compiler, observatory, tests) can inspect them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SourceLocation:
    file: str
    line: int
    column: int

    def __str__(self) -> str:
        return f"{self.file}:{self.line}:{self.column}"


class EALPlError(Exception):
    """Base error for EAL-PL with a source location and a structured message."""

    def __init__(self, message: str, location: SourceLocation | None = None,
                 code: str = "EAL-PL") -> None:
        super().__init__(message)
        self.message = message
        self.location = location
        self.code = code

    def __str__(self) -> str:
        prefix = f"{self.code}" if self.location is None else f"{self.code} {self.location}"
        return f"{prefix}: {self.message}"


class LexerError(EALPlError):
    pass


class ParseError(EALPlError):
    pass


class SemanticError(EALPlError):
    pass


class TypeError(EALPlError):
    pass


class RuntimeError(EALPlError):
    pass


class CompilerError(EALPlError):
    pass


def format_error(error: EALPlError, source_line: str | None = None) -> str:
    """Human-readable rendering of an error, optionally with source context."""
    lines = [str(error)]
    if source_line is not None and error.location is not None:
        col = error.location.column
        lines.append(f"    {source_line}")
        lines.append(f"    {' ' * max(col - 1, 0)}^")
    return "\n".join(lines)
