"""EAL-PL compiler: AST + semantic analysis -> IR (bytecode).

The compiler runs semantic analysis first (type checking), then emits IR
instructions. It supports functions with local frames, calls, and returns.
"""

from __future__ import annotations

from typing import Any

from . import ast as pl_ast
from .ast import INT, BOOL, STRING, VOID
from .errors import CompilerError, SemanticError, TypeError as PlTypeError
from .ir import IR, Op
from .semantic import SemanticAnalyzer


class Compiler:
    def __init__(self) -> None:
        self.ir = IR()
        self.semantic = SemanticAnalyzer()
        # function name -> {"address": int|None, "params": [str, ...]}
        self.functions: dict[str, dict[str, Any]] = {}
        self._return_address_stack: list[int] = []
        # Stack of active loops: {"start": ip, "breaks": [placeholder_ip, ...]}
        self._loop_stack: list[dict] = []

    def compile(self, program: pl_ast.Program) -> IR:
        """Type-check and compile a program to IR.

        Raises CompilerError (wrapping semantic errors) on failure.
        """
        try:
            self.semantic.analyze(program)
        except (SemanticError, PlTypeError) as exc:
            raise CompilerError(
                f"semantic error: {exc.message}",
                exc.location,
                code="EAL-PL/compile",
            ) from exc

        # Registration pass: collect function names and param names.
        self._register_functions(program)

        # Emit a jump at the very start that skips over all function bodies,
        # landing at the top-level program. Functions are placed first so
        # their addresses are known when CALL instructions are emitted below.
        main_jump_index = self.ir.add(Op.JMP, None)

        for stmt in program.statements:
            if isinstance(stmt, pl_ast.FnStmt):
                self.functions[stmt.name]["address"] = len(self.ir.instructions)
                self._emit_statements(stmt.body.statements)
                self.ir.add(Op.RETURN, None, stmt.location)

        # Patch the initial jump to land at the top-level program.
        self.ir.patch(main_jump_index, len(self.ir.instructions))

        # Emit all top-level statements except function definitions.
        for stmt in program.statements:
            if not isinstance(stmt, pl_ast.FnStmt):
                self._emit(stmt)
        self.ir.add(Op.HALT)

        return self.ir

    # -- registration pass ------------------------------------------------

    def _register_functions(self, node: pl_ast.Program) -> None:
        for stmt in node.statements:
            if isinstance(stmt, pl_ast.FnStmt):
                self.functions[stmt.name] = {
                    "address": None,
                    "params": [pname for pname, _ in stmt.params],
                }

    # -- emission ---------------------------------------------------------

    def _emit_statements(self, statements) -> None:
        for stmt in statements:
            self._emit(stmt)

    def _emit(self, node: Any) -> None:
        if node is None:
            return
        method = "emit_" + type(node).__name__
        emitter = getattr(self, method, None)
        if emitter is None:
            raise CompilerError(f"no emitter for {type(node).__name__}",
                                getattr(node, "location", None))
        emitter(node)

    def emit_Program(self, node: pl_ast.Program) -> None:
        self._emit_statements(node.statements)

    def emit_BlockStmt(self, node: pl_ast.BlockStmt) -> None:
        self._emit_statements(node.statements)

    def emit_BindStmt(self, node: pl_ast.BindStmt) -> None:
        self._emit_expression(node.value)
        self.ir.add(Op.STORE, node.name, node.location)

    def emit_MutStmt(self, node: pl_ast.MutStmt) -> None:
        self._emit_expression(node.value)
        self.ir.add(Op.STORE, node.name, node.location)

    def emit_ExprStmt(self, node: pl_ast.ExprStmt) -> None:
        # Expression statements evaluate but do not auto-print; `print` is
        # explicit. Evaluating may still have side effects (e.g. assignment).
        self._emit_expression(node.expression)

    def emit_IfStmt(self, node: pl_ast.IfStmt) -> None:
        self._emit_expression(node.condition)
        jump_false = self.ir.add(Op.JMP_IF, None, node.location)
        self._emit_statements([node.then_branch] if not isinstance(
            node.then_branch, pl_ast.BlockStmt) else node.then_branch.statements)
        end = self.ir.add(Op.JMP, None, node.location)
        self.ir.patch(jump_false, len(self.ir.instructions))
        if node.else_branch is not None:
            self._emit_statements([node.else_branch] if not isinstance(
                node.else_branch, pl_ast.BlockStmt) else node.else_branch.statements)
        self.ir.patch(end, len(self.ir.instructions))

    def emit_LoopStmt(self, node: pl_ast.LoopStmt) -> None:
        loop_start = len(self.ir.instructions)
        loop_ctx = {"start": loop_start, "breaks": []}
        self._loop_stack.append(loop_ctx)
        try:
            self._emit_statements(node.body.statements)
        finally:
            self._loop_stack.pop()
        # Jump back to the top of the loop.
        self.ir.add(Op.JMP, loop_start, node.location)
        loop_end = len(self.ir.instructions)
        # Patch all break targets to continue after the loop.
        for break_ip in loop_ctx["breaks"]:
            self.ir.patch(break_ip, loop_end)

    def emit_BreakStmt(self, node: pl_ast.BreakStmt) -> None:
        if not self._loop_stack:
            raise CompilerError("break outside loop", node.location)
        # Placeholder jump; patched when the enclosing loop is emitted.
        break_ip = self.ir.add(Op.JMP, None, node.location)
        self._loop_stack[-1]["breaks"].append(break_ip)

    def emit_ContinueStmt(self, node: pl_ast.ContinueStmt) -> None:
        if not self._loop_stack:
            raise CompilerError("continue outside loop", node.location)
        self.ir.add(Op.JMP, self._loop_stack[-1]["start"], node.location)


    def emit_ReturnStmt(self, node: pl_ast.ReturnStmt) -> None:
        if node.value is not None:
            self._emit_expression(node.value)
        else:
            self.ir.add(Op.CONST, None, node.location)
        self.ir.add(Op.RETURN, None, node.location)

    def emit_PrintStmt(self, node: pl_ast.PrintStmt) -> None:
        self._emit_expression(node.expression)
        self.ir.add(Op.PRINT, None, node.location)

    def emit_Literal(self, node: pl_ast.Literal) -> None:
        self.ir.add(Op.CONST, self.ir.constant(node.value), node.location)

    def emit_Variable(self, node: pl_ast.Variable) -> None:
        self.ir.add(Op.LOAD, node.name, node.location)

    def emit_Assignment(self, node: pl_ast.Assignment) -> None:
        self._emit_expression(node.value)
        self.ir.add(Op.STORE, node.name, node.location)

    def emit_Binary(self, node: pl_ast.Binary) -> None:
        self._emit_expression(node.left)
        self._emit_expression(node.right)
        op_map = {"+": Op.ADD, "-": Op.SUB, "*": Op.MUL, "/": Op.DIV,
                  "==": Op.EQ, "!=": Op.NE, "<": Op.LT, ">": Op.GT,
                  "<=": Op.LE, ">=": Op.GE}
        self.ir.add(op_map[node.operator], None, node.location)

    def emit_Unary(self, node: pl_ast.Unary) -> None:
        self._emit_expression(node.operand)
        if node.operator == "-":
            self.ir.add(Op.NEG, None, node.location)
        elif node.operator == "!":
            self.ir.add(Op.NOT, None, node.location)

    def emit_Call(self, node: pl_ast.Call) -> None:
        for arg in node.arguments:
            self._emit_expression(arg)
        info = self.functions.get(node.callee)
        arity = len(node.arguments)
        if info is None or info["address"] is None:
            # built-in call; the VM handles it by name
            self.ir.add(Op.CALL, {"name": node.callee, "arity": arity},
                        node.location)
        else:
            self.ir.add(Op.CALL, {
                "name": node.callee,
                "arity": arity,
                "address": info["address"],
                "params": info["params"],
            }, node.location)

    # -- helpers ----------------------------------------------------------

    def _emit_expression(self, expr: Any) -> None:
        self._emit(expr)
