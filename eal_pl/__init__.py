"""EAL-PL: an original programming language.

Public API:
    tokens            # Lexer, Token
    parser            # Parser
    ast               # AST nodes + Type system (INT, BOOL, STRING, VOID, Type)
    types             # TypeEnv
    semantic          # SemanticAnalyzer, TypedExpression
    ir                # IR, Op, Instruction
    compiler          # Compiler (AST -> IR)
    vm                # VM (interpreter)
    stdlib            # build_stdlib
    package           # Package, PackageLoader
    debug             # DebugVM, format_source_context
    errors            # EALPlError and subclasses, SourceLocation

The grammar is original (bind / mut / fn / loop / if / else / return / print)
and is not a rename of Python, Rust, Go or any other existing language.
A working compiler and interpreter are provided; self-hosting is a
long-term objective, not an initial assumption (spec §3 EAL-PL).
"""

from .ast import BOOL, INT, STRING, Type, VOID, function_type
from .compiler import Compiler
from .debug import DebugVM, format_source_context
from .parser import Parser
from .errors import (CompilerError, EALPlError, LexerError, ParseError,
                     RuntimeError as PlRuntimeError, SemanticError,
                     SourceLocation, TypeError as PlTypeError, format_error)
from .ir import IR, Instruction, Op
from .package import Package, PackageLoader
from .semantic import SemanticAnalyzer, TypedExpression
from .stdlib import build_stdlib
from .tokens import Lexer, Token
from .types import TypeEnv
from .vm import VM

__all__ = [
    "BOOL",
    "Compiler",
    "DebugVM",
    "Parser",
    "INT",
    "IR",
    "Instruction",
    "Lexer",
    "Op",
    "Package",
    "PackageLoader",
    "PlRuntimeError",
    "PlTypeError",
    "SemanticAnalyzer",
    "SourceLocation",
    "STRING",
    "Type",
    "TypeEnv",
    "TypedExpression",
    "VM",
    "VOID",
    "build_stdlib",
    "format_error",
    "format_source_context",
    "function_type",
]
