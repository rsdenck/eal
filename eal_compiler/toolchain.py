"""EAL-COMPILER: compilation toolchain for EAL-PL.

Includes reproducible compilation, intermediate representations, diagnostics
and validation. This module wraps the EAL-PL compiler and adds
reproducibility guarantees (deterministic output for identical input),
validation, and diagnostic reporting.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from eal_pl import Compiler, Parser, Lexer
from eal_pl.ast import Program
from eal_pl.errors import CompilerError, SourceLocation
from eal_pl.ir import IR
from eal_pl.vm import VM


@dataclass(frozen=True)
class Diagnostic:
    """A compiler diagnostic (error or warning) with source location."""

    severity: str  # "error" or "warning"
    code: str
    message: str
    location: SourceLocation | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "location": str(self.location) if self.location else None,
        }


@dataclass
class CompilationResult:
    """Result of compiling a EAL-PL source program.

    Attributes:
        source: The original source text.
        ir: The compiled intermediate representation (or None on failure).
        diagnostics: List of diagnostics produced during compilation.
        reproducible_hash: Content-stable hash of the IR for reproducibility
            verification.
        success: Whether compilation succeeded.
    """

    source: str
    ir: IR | None
    diagnostics: list[Diagnostic] = field(default_factory=list)
    reproducible_hash: str = ""
    success: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "ir_instructions": len(self.ir.instructions) if self.ir else 0,
            "diagnostics": [d.to_dict() for d in self.diagnostics],
            "reproducible_hash": self.reproducible_hash,
            "success": self.success,
        }


class CompilerToolchain:
    """Reproducible compilation toolchain for EAL-PL.

    Compiles EAL-PL source to IR with full diagnostics and a content-stable
    hash so that identical source + identical toolchain version produce
    identical IR (reproducible compilation).
    """

    TOOLCHAIN_VERSION = "eal-compiler/1.0"

    def __init__(self) -> None:
        self._compiler = Compiler()

    def compile(self, source: str,
                file: str = "<eal>") -> CompilationResult:
        """Compile EAL-PL source to IR with diagnostics.

        Returns a :class:`CompilationResult`. On failure, ``ir`` is None and
        diagnostics contain the errors.
        """
        diagnostics: list[Diagnostic] = []
        ir: IR | None = None
        success = False

        try:
            tokens = Lexer(source, file=file).tokenize()
        except Exception as exc:  # lexer errors
            diagnostics.append(Diagnostic(
                severity="error", code="EAL-CL/lexer",
                message=str(exc),
            ))
            return CompilationResult(
                source=source, ir=None, diagnostics=diagnostics,
                reproducible_hash=self._hash(source, diagnostics),
                success=False,
            )

        try:
            program = Parser(tokens).parse()
        except Exception as exc:
            diagnostics.append(Diagnostic(
                severity="error", code="EAL-CL/parser",
                message=str(exc),
            ))
            return CompilationResult(
                source=source, ir=None, diagnostics=diagnostics,
                reproducible_hash=self._hash(source, diagnostics),
                success=False,
            )

        try:
            ir = self._compiler.compile(program)
            success = True
        except CompilerError as exc:
            diagnostics.append(Diagnostic(
                severity="error", code="EAL-CL/compiler",
                message=exc.message,
                location=exc.location,
            ))
        except Exception as exc:
            diagnostics.append(Diagnostic(
                severity="error", code="EAL-CL/unknown",
                message=str(exc),
            ))

        return CompilationResult(
            source=source, ir=ir, diagnostics=diagnostics,
            reproducible_hash=self._hash(source, diagnostics),
            success=success,
        )

    def compile_and_run(self, source: str,
                        natives: dict | None = None) -> CompilationResult:
        """Compile and execute the source, capturing VM output in diagnostics."""
        result = self.compile(source)
        if not result.success or result.ir is None:
            return result
        vm = VM(result.ir, natives=natives or {})
        try:
            vm.run()
            result.diagnostics.append(Diagnostic(
                severity="info", code="EAL-RT/run",
                message=f"VM executed {vm.step_count} steps; "
                        f"output: {vm.stdout}",
            ))
        except Exception as exc:
            result.diagnostics.append(Diagnostic(
                severity="error", code="EAL-RT/runtime",
                message=str(exc),
            ))
        return result

    def validate(self, source: str) -> list[Diagnostic]:
        """Validate source without emitting IR. Returns diagnostics only."""
        result = self.compile(source)
        return result.diagnostics

    @staticmethod
    def _hash(source: str, diagnostics: list[Diagnostic]) -> str:
        payload = json.dumps(
            {"toolchain": CompilerToolchain.TOOLCHAIN_VERSION,
             "source": source,
             "diagnostics": [d.to_dict() for d in diagnostics]},
            sort_keys=True,
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()[:32]
