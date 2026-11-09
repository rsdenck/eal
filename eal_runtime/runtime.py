"""EAL-RUNTIME: execution environment for EAL-PL.

Includes memory management, process isolation, execution control, resource
limits, sandboxing, runtime diagnostics and standard execution interfaces.

This module wraps the EAL-PL VM and adds sandboxing, resource limits and
process isolation so that EAL-PL programs execute safely.
"""

from __future__ import annotations

import resource
from dataclasses import dataclass, field
from typing import Any

from eal_pl import Compiler, Lexer, Parser, VM, build_stdlib
from eal_pl.errors import RuntimeError as PlRuntimeError
from eal_pl.ir import IR


@dataclass
class ResourceLimits:
    """Resource limits for sandboxed execution.

    Attributes:
        max_steps: Maximum VM instruction steps before aborting.
        max_memory_bytes: Approximate memory cap (enforced best-effort via
            ``resource`` on Unix where available).
        max_output_chars: Maximum captured stdout characters.
        timeout_seconds: Wall-clock timeout (best-effort).
    """

    max_steps: int = 100000
    max_memory_bytes: int = 64 * 1024 * 1024
    max_output_chars: int = 1_000_000
    timeout_seconds: float = 30.0


@dataclass
class RuntimeDiagnostic:
    """A runtime diagnostic event."""

    kind: str  # "step", "limit", "error", "sandbox"
    message: str
    step: int
    detail: dict = field(default_factory=dict)


@dataclass
class ExecutionResult:
    """Result of executing a EAL-PL program in the runtime.

    Attributes:
        success: Whether execution completed without hitting a limit/error.
        output: Captured stdout lines.
        steps: Number of VM steps executed.
        diagnostics: Runtime diagnostics.
        result: Final value left on the VM stack (or None).
        hit_limit: Whether a resource limit was hit.
    """

    success: bool
    output: list[str]
    steps: int
    diagnostics: list[RuntimeDiagnostic] = field(default_factory=list)
    result: Any = None
    hit_limit: bool = False


class Sandbox:
    """Sandboxed execution environment for EAL-PL programs.

    Provides process isolation (via separate VM instance), resource limits,
    and best-effort memory enforcement. The VM is deterministic, so repeated
    executions of the same IR produce the same result.
    """

    def __init__(self, limits: ResourceLimits | None = None,
                 natives: dict | None = None) -> None:
        self.limits = limits or ResourceLimits()
        self.natives = dict(natives or {})
        self._step_count = 0

    def execute(self, ir: IR) -> ExecutionResult:
        """Execute IR in the sandbox.

        Enforces max_steps and max_output_chars. Memory limits are enforced
        best-effort via ``resource`` where available.
        """
        self._apply_memory_limit()
        vm = VM(ir, capture_output=True, debug=False, natives=self.natives)

        diagnostics: list[RuntimeDiagnostic] = []
        result_value = None
        hit_limit = False
        success = False

        try:
            # Run with step monitoring by overriding execution loop manually.
            result_value = self._run_monitored(vm, diagnostics)
            success = True
        except PlRuntimeError as exc:
            diagnostics.append(RuntimeDiagnostic(
                kind="error", message=str(exc),
                step=vm.step_count,
                detail={"location": str(exc.location)
                        if exc.location else None},
            ))
        except RuntimeError as exc:
            diagnostics.append(RuntimeDiagnostic(
                kind="limit", message=str(exc), step=vm.step_count,
            ))
            hit_limit = True
        except Exception as exc:
            diagnostics.append(RuntimeDiagnostic(
                kind="error", message=str(exc), step=vm.step_count,
            ))

        output = list(vm.stdout)
        if len("".join(output)) > self.limits.max_output_chars:
            output = ["".join(output)[: self.limits.max_output_chars]]
            diagnostics.append(RuntimeDiagnostic(
                kind="limit", message="output truncated",
                step=vm.step_count,
            ))

        return ExecutionResult(
            success=success and not hit_limit,
            output=output,
            steps=vm.step_count,
            diagnostics=diagnostics,
            result=result_value,
            hit_limit=hit_limit,
        )

    def _run_monitored(self, vm: VM,
                       diagnostics: list[RuntimeDiagnostic]) -> Any:
        """Run the VM with step-limit monitoring."""
        # Re-implement the run loop with a step cap so we can enforce limits
        # and record diagnostics.
        vm.frames = [vm.frames[0]] if vm.frames else []
        if not vm.frames:
            from eal_pl.vm import Frame
            vm.frames = [Frame(locals=vm.globals, return_ip=-1,
                               stack_base=0, function_name="<top-level>")]
        vm.ip = 0
        vm.halted = False
        vm.stack = []
        while not vm.halted:
            if vm.step_count >= self.limits.max_steps:
                raise RuntimeError("max steps exceeded")
            if vm.ip < 0 or vm.ip >= len(vm.instructions):
                raise PlRuntimeError(
                    f"instruction pointer out of bounds: {vm.ip}",
                    vm.last_location,
                )
            instr = vm.instructions[vm.ip]
            vm.last_location = instr.location
            vm.ip += 1
            vm.step_count += 1
            vm._execute(instr)
        return vm.stack[-1] if vm.stack else None

    def _apply_memory_limit(self) -> None:
        """Best-effort memory limit via resource module (Unix only)."""
        try:
            soft, hard = resource.getrlimit(resource.RLIMIT_AS)
            new_soft = min(soft, self.limits.max_memory_bytes)
            resource.setrlimit(resource.RLIMIT_AS, (new_soft, hard))
        except (ImportError, AttributeError, OSError, ValueError):
            # Not available on this platform; skip enforcement.
            pass


class Runtime:
    """Standard execution interface for EAL-PL programs.

    Compiles source and executes it in the sandbox, returning an
    :class:`ExecutionResult`. This is the main entry point for running
    EAL-PL programs safely.
    """

    def __init__(self, limits: ResourceLimits | None = None,
                 natives: dict | None = None) -> None:
        self.limits = limits or ResourceLimits()
        self.natives = dict(natives or {})
        self.toolchain = __import__("eal_compiler.toolchain", fromlist=["x"]).CompilerToolchain()

    def run_source(self, source: str,
                   file: str = "<eal>",
                   natives: dict | None = None) -> ExecutionResult:
        """Compile and run a EAL-PL source program in the sandbox."""
        merged_natives = dict(self.natives)
        merged_natives.update(natives or {})
        result = self.toolchain.compile(source, file=file)
        if not result.success or result.ir is None:
            return ExecutionResult(
                success=False, output=[], steps=0,
                diagnostics=[RuntimeDiagnostic(
                    kind="error", message=d.message, step=0,
                    detail={"code": d.code, "severity": d.severity,
                            "location": str(d.location)
                            if d.location else None},
                ) for d in result.diagnostics],
            )
        sandbox = Sandbox(limits=self.limits, natives=merged_natives)
        return sandbox.execute(result.ir)
