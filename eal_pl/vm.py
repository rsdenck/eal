"""EAL-PL virtual machine: executes IR bytecode.

A stack-based VM with call frames for functions. Captures `print` output and
reports runtime errors with source locations. The VM is deterministic given
the same IR, which keeps experiments reproducible.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .errors import EALPlError, RuntimeError as PlRuntimeError, SourceLocation
from .ir import IR, Op


@dataclass
class Frame:
    """A call frame: locals, return address, and stack base."""

    locals: dict[str, Any]
    return_ip: int
    stack_base: int
    function_name: str


class VM:
    def __init__(self, ir: IR,
                 capture_output: bool = True,
                 debug: bool = False,
                 natives: dict[str, Any] | None = None) -> None:
        self.ir = ir
        self.instructions = ir.instructions
        self.constants = ir.constants
        self.globals: dict[str, Any] = {}
        self.stdout: list[str] = []
        self.capture_output = capture_output
        self.debug = debug
        self.ip = 0
        self.stack: list[Any] = []
        self.frames: list[Frame] = []
        self.halted = False
        self.step_count = 0
        self.last_location: SourceLocation | None = None
        self.natives = dict(natives or {})

    def register_native(self, name: str, func: Any) -> None:
        self.natives[name] = func

    # -- execution --------------------------------------------------------

    def run(self) -> Any:
        """Execute the IR from the top-level program frame.

        Returns the value left on the stack (or None). Captures prints to
        :attr:`stdout`.
        """
        self.frames = [Frame(locals=self.globals, return_ip=-1,
                             stack_base=0, function_name="<top-level>")]
        self.ip = 0
        self.halted = False
        while not self.halted:
            if self.ip < 0 or self.ip >= len(self.instructions):
                raise PlRuntimeError(
                    f"instruction pointer out of bounds: {self.ip}",
                    self.last_location,
                )
            instr = self.instructions[self.ip]
            self.last_location = instr.location
            self.ip += 1
            self.step_count += 1
            if self.debug:
                self._trace(instr)
            self._execute(instr)
        # result is top of stack if anything remains
        return self.stack[-1] if self.stack else None

    def _execute(self, instr) -> None:
        op = instr.op
        arg = instr.arg

        if op == Op.CONST:
            self.stack.append(self.constants[arg])
        elif op == Op.LOAD:
            name = arg
            value = self._lookup(name)
            self.stack.append(value)
        elif op == Op.STORE:
            name = arg
            value = self.stack.pop()
            self._bind(name, value)
        elif op == Op.ADD:
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(a + b)
        elif op == Op.SUB:
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(a - b)
        elif op == Op.MUL:
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(a * b)
        elif op == Op.DIV:
            b, a = self.stack.pop(), self.stack.pop()
            if b == 0:
                raise PlRuntimeError("division by zero", instr.location)
            self.stack.append(a // b)
        elif op == Op.EQ:
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(a == b)
        elif op == Op.NE:
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(a != b)
        elif op == Op.LT:
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(a < b)
        elif op == Op.GT:
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(a > b)
        elif op == Op.LE:
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(a <= b)
        elif op == Op.GE:
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(a >= b)
        elif op == Op.NOT:
            self.stack.append(not self.stack.pop())
        elif op == Op.NEG:
            self.stack.append(-self.stack.pop())
        elif op == Op.JMP:
            self.ip = arg
        elif op == Op.JMP_IF:
            condition = self.stack.pop()
            if not condition:
                self.ip = arg
        elif op == Op.JMP_IF_NOT:
            condition = self.stack.pop()
            if condition:
                self.ip = arg
        elif op == Op.PRINT:
            value = self.stack.pop()
            text = self._format(value)
            if self.capture_output:
                self.stdout.append(text)
            else:
                print(text)
        elif op == Op.CALL:
            self._call(arg)
        elif op == Op.RETURN:
            self._ret()
        elif op == Op.HALT:
            self.halted = True
        else:
            raise PlRuntimeError(f"unknown opcode {op!r}", instr.location)

    # -- calls / frames ---------------------------------------------------

    def _call(self, arg: Any) -> None:
        name = arg["name"] if isinstance(arg, dict) else arg
        arity = arg["arity"] if isinstance(arg, dict) else 0
        address = arg.get("address") if isinstance(arg, dict) else None

        # Built-in functions
        if name == "print":
            values = [self.stack.pop() for _ in range(arity)]
            values.reverse()
            text = " ".join(self._format(v) for v in values)
            if self.capture_output:
                self.stdout.append(text)
            else:
                print(text)
            self.stack.append(None)
            return

        if name in self.natives:
            values = [self.stack.pop() for _ in range(arity)]
            values.reverse()
            try:
                result = self.natives[name](*values)
            except TypeError as exc:
                raise PlRuntimeError(
                    f"native '{name}' argument error: {exc}", self.last_location,
                ) from exc
            self.stack.append(result)
            return

        if address is None:
            raise PlRuntimeError(
                f"undefined function '{name}'", self.last_location,
            )

        # Pop arguments (pushed left-to-right; pop gives reverse order).
        args = [self.stack.pop() for _ in range(arity)]
        args.reverse()
        param_locals = {}
        param_names = arg.get("params") if isinstance(arg, dict) else None
        for i, value in enumerate(args):
            key = param_names[i] if param_names and i < len(param_names) else f"${i}"
            param_locals[key] = value

        self.frames.append(Frame(
            locals=param_locals, return_ip=self.ip,
            stack_base=len(self.stack) - arity,
            function_name=name,
        ))
        self.ip = address

    def _ret(self) -> None:
        result = self.stack.pop()
        if not self.frames:
            self.halted = True
            self.stack.append(result)
            return
        frame = self.frames.pop()
        # Truncate stack to the base (removing args/locals), then push result.
        self.stack = self.stack[:frame.stack_base]
        self.stack.append(result)
        self.ip = frame.return_ip

    # -- variable scope ---------------------------------------------------

    def _lookup(self, name: str) -> Any:
        # Check innermost frame first, then globals.
        for frame in reversed(self.frames):
            if name in frame.locals:
                return frame.locals[name]
        if name in self.globals:
            return self.globals[name]
        raise PlRuntimeError(f"undefined variable '{name}'", self.last_location)

    def _bind(self, name: str, value: Any) -> None:
        # Store in the innermost frame if it has locals, else globals.
        if self.frames:
            self.frames[-1].locals[name] = value
        else:
            self.globals[name] = value

    def _format(self, value: Any) -> str:
        if value is None:
            return "nil"
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value)

    def _trace(self, instr) -> None:
        print(f"[vm:{self.ip-1:04d}] {instr.op} "
              f"{'' if instr.arg is None else instr.arg!r}")
