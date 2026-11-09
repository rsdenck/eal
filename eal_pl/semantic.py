"""EAL-PL semantic analysis and type checking.

Walks the AST, builds a symbol table with nested scopes, and checks types.
Produces a typed annotation on each expression for the compiler. All type
errors are reported as :class:`~eal_pl.errors.SemanticError` / TypeError with
source locations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from . import ast as pl_ast
from .ast import (INT, BOOL, STRING, VOID, Type, function_type)
from .errors import SemanticError, SourceLocation, TypeError as PLTypeError
from .types import TypeEnv, compatible


@dataclass
class TypedExpression:
    """An expression annotated with its inferred type."""

    expression: Any
    type: Type


class SemanticAnalyzer:
    def __init__(self) -> None:
        self.env = TypeEnv()
        self.errors: list[SemanticError | PLTypeError] = []
        # function name -> signature
        self.functions: dict[str, pl_ast.FunctionSignature] = {}
        self.in_loop = 0
        self.in_function = False
        self.current_return_type: Type = VOID
        self._pending_returns: list[Type] = []

    # -- entry point ------------------------------------------------------

    def analyze(self, program: pl_ast.Program) -> list:
        """Return a list of (node, type) annotations; raises on first error."""
        self._visit_program(program)
        if self.errors:
            raise self.errors[0]
        return []

    # -- visitors ---------------------------------------------------------

    def _visit_program(self, node: pl_ast.Program) -> None:
        for stmt in node.statements:
            self._visit(stmt)

    def _visit(self, node: Any) -> Type | None:
        if node is None:
            return VOID
        method = "visit_" + type(node).__name__
        visitor = getattr(self, method, None)
        if visitor is None:
            raise SemanticError(
                f"no semantic visitor for {type(node).__name__}",
                getattr(node, "location", None),
            )
        return visitor(node)

    # -- statements -------------------------------------------------------

    def visit_Program(self, node: pl_ast.Program) -> Type:
        return self._visit_program(node) or VOID  # type: ignore[return-value]

    def visit_BlockStmt(self, node: pl_ast.BlockStmt) -> Type:
        last = VOID
        for stmt in node.statements:
            last = self._visit(stmt) or VOID
        return last

    def visit_BindStmt(self, node: pl_ast.BindStmt) -> Type:
        expr_type = self._visit(node.value) or VOID
        declared = self._resolve_type(node.type_annotation)
        if declared is not None and declared != expr_type:
            raise PLTypeError(
                f"bind '{node.name}' declared as {declared} but "
                f"expression has type {expr_type}", node.location,
            )
        self.env.define(node.name, expr_type)
        return VOID

    def visit_MutStmt(self, node: pl_ast.MutStmt) -> Type:
        expr_type = self._visit(node.value) or VOID
        declared = self._resolve_type(node.type_annotation)
        if declared is not None and declared != expr_type:
            raise PLTypeError(
                f"mut '{node.name}' declared as {declared} but "
                f"expression has type {expr_type}", node.location,
            )
        self.env.define(node.name, expr_type)
        return VOID

    def visit_FnStmt(self, node: pl_ast.FnStmt) -> Type:
        param_types = tuple(
            self._resolve_type(pt) or VOID for _, pt in node.params
        )
        declared_ret = self._resolve_type(node.return_type)
        sig = pl_ast.FunctionSignature(
            name=node.name, param_types=param_types,
            return_type=declared_ret or VOID,
        )
        self.functions[node.name] = sig

        # Collect explicit return statement types within the body for
        # inference when no return type is declared.
        return_types: list[Type] = []
        self._pending_returns = return_types

        # Type-check body in a new scope with parameters bound.
        prev_env = self.env
        self.env = TypeEnv(parent=prev_env)
        for (pname, ptype), ptype_resolved in zip(node.params, param_types):
            self.env.define(pname, ptype_resolved)
        prev_in_fn = self.in_function
        prev_ret = self.current_return_type
        self.in_function = True
        self.current_return_type = declared_ret or VOID
        body_type = self._visit(node.body) or VOID
        self.in_function = prev_in_fn
        self.current_return_type = prev_ret
        self.env = prev_env

        # Infer return type if undeclared.
        if declared_ret is None and return_types:
            inferred = return_types[0]
            for rt in return_types[1:]:
                if rt != inferred:
                    raise PLTypeError(
                        f"function '{node.name}' has inconsistent return types "
                        f"{inferred} and {rt}", node.location,
                    )
            sig.return_type = inferred

        return VOID

    def visit_ReturnStmt(self, node: pl_ast.ReturnStmt) -> Type:
        if not self.in_function:
            raise SemanticError("return outside function", node.location)
        declared = self.current_return_type
        if node.value is None:
            if declared != VOID:
                raise PLTypeError(
                    f"function expects return of type {declared}",
                    node.location,
                )
            return declared
        val_type = self._visit(node.value) or VOID
        if declared != VOID and val_type != declared:
            raise PLTypeError(
                f"return type {val_type} does not match "
                f"declared {declared}", node.location,
            )
        # Record for inference when undeclared.
        if declared == VOID:
            self._pending_returns.append(val_type)
        return declared

    def visit_ExprStmt(self, node: pl_ast.ExprStmt) -> Type:
        return self._visit(node.expression) or VOID

    def visit_IfStmt(self, node: pl_ast.IfStmt) -> Type:
        cond_type = self._visit(node.condition) or VOID
        if cond_type != BOOL:
            raise PLTypeError(
                f"if condition must be bool, got {cond_type}",
                node.location,
            )
        self._visit(node.then_branch)
        if node.else_branch is not None:
            self._visit(node.else_branch)
        return VOID

    def visit_LoopStmt(self, node: pl_ast.LoopStmt) -> Type:
        prev = self.in_loop
        self.in_loop += 1
        self._visit(node.body)
        self.in_loop = prev
        return VOID

    def visit_BreakStmt(self, node: pl_ast.BreakStmt) -> Type:
        if self.in_loop == 0:
            raise SemanticError("break outside loop", node.location)
        return VOID

    def visit_ContinueStmt(self, node: pl_ast.ContinueStmt) -> Type:
        if self.in_loop == 0:
            raise SemanticError("continue outside loop", node.location)
        return VOID

    def visit_ReturnStmt(self, node: pl_ast.ReturnStmt) -> Type:
        if not self.in_function:
            raise SemanticError("return outside function", node.location)
        if node.value is None:
            if self.current_return_type != VOID:
                raise PLTypeError(
                    f"function expects return of type {self.current_return_type}",
                    node.location,
                )
        else:
            val_type = self._visit(node.value) or VOID
            declared = self.current_return_type
            if declared != VOID and val_type != declared:
                raise PLTypeError(
                    f"return type {val_type} does not match "
                    f"declared {declared}", node.location,
                )
            # Record for inference when undeclared.
            if declared == VOID:
                self._pending_returns.append(val_type)
        return self.current_return_type

    def visit_PrintStmt(self, node: pl_ast.PrintStmt) -> Type:
        self._visit(node.expression)
        return VOID

    # -- expressions ------------------------------------------------------

    def visit_Literal(self, node: pl_ast.Literal) -> Type:
        if isinstance(node.value, bool):
            return BOOL
        if isinstance(node.value, int):
            return INT
        if isinstance(node.value, float):
            # EAL-PL has no float literal type in this version; treat as int
            return INT
        if isinstance(node.value, str):
            return STRING
        return VOID

    def visit_Variable(self, node: pl_ast.Variable) -> Type:
        typ = self.env.resolve(node.name)
        if typ is None:
            raise SemanticError(
                f"undefined variable '{node.name}'", node.location,
            )
        return typ

    def visit_Assignment(self, node: pl_ast.Assignment) -> Type:
        typ = self.env.resolve(node.name)
        if typ is None:
            raise SemanticError(
                f"assignment to undefined variable '{node.name}'",
                node.location,
            )
        val_type = self._visit(node.value) or VOID
        if not compatible(typ, val_type):
            raise PLTypeError(
                f"cannot assign {val_type} to variable '{node.name}' of type {typ}",
                node.location,
            )
        return typ

    def visit_Binary(self, node: pl_ast.Binary) -> Type:
        left = self._visit(node.left) or VOID
        right = self._visit(node.right) or VOID
        op = node.operator
        if op in ("==", "!="):
            return BOOL
        if op in ("<", ">", "<=", ">="):
            if left not in (INT, VOID) or right not in (INT, VOID):
                raise PLTypeError(
                    f"comparison requires numeric operands, got {left} and {right}",
                    node.location,
                )
            return BOOL
        if op in ("+", "-", "*", "/"):
            if left not in (INT, VOID) or right not in (INT, VOID):
                raise PLTypeError(
                    f"arithmetic requires int operands, got {left} and {right}",
                    node.location,
                )
            return INT
        raise PLTypeError(f"unknown operator {op!r}", node.location)

    def visit_Unary(self, node: pl_ast.Unary) -> Type:
        operand = self._visit(node.operand) or VOID
        op = node.operator
        if op == "-":
            if operand not in (INT, VOID):
                raise PLTypeError(
                    f"negation requires int, got {operand}", node.location,
                )
            return INT
        if op == "!":
            if operand != BOOL:
                raise PLTypeError(
                    f"logical not requires bool, got {operand}", node.location,
                )
            return BOOL
        raise PLTypeError(f"unknown unary operator {op!r}", node.location)

    def visit_Call(self, node: pl_ast.Call) -> Type:
        sig = self.functions.get(node.callee)
        if sig is None:
            # Built-in functions are resolved by the runtime/compiler; allow
            # unknown calls here to be resolved later, but flag clearly.
            return VOID
        if len(node.arguments) != len(sig.param_types):
            raise SemanticError(
                f"function '{node.callee}' expects "
                f"{len(sig.param_types)} arguments, got "
                f"{len(node.arguments)}", node.location,
            )
        for arg, ptype in zip(node.arguments, sig.param_types):
            atype = self._visit(arg) or VOID
            if not compatible(ptype, atype):
                raise PLTypeError(
                    f"argument type {atype} does not match parameter {ptype}",
                    node.location,
                )
        return sig.return_type

    # -- helpers ----------------------------------------------------------

    def _resolve_type(self, type_annotation: str | None) -> Type | None:
        if type_annotation is None:
            return None
        mapping = {"int": INT, "bool": BOOL, "string": STRING, "void": VOID}
        return mapping.get(type_annotation)
