"""Unit tests for EAL-PL (stdlib only)."""

from __future__ import annotations

import unittest

from eal_pl import (
    Compiler,
    Lexer,
    build_stdlib,
    format_source_context,
)
from eal_pl.ast import BlockStmt, FnStmt, LoopStmt, Program
from eal_pl.errors import (
    CompilerError,
    LexerError,
    ParseError,
    SemanticError,
    SourceLocation,
    TypeError as PlTypeError,
    format_error,
)
from eal_pl.ir import IR
from eal_pl.parser import Parser
from eal_pl.semantic import SemanticAnalyzer
from eal_pl.tokens import TT_INT, Token
from eal_pl.vm import VM


def compile_and_run(source: str, natives: dict | None = None) -> VM:
    """Helper: lex, parse, compile, run; return the VM."""
    tokens = Lexer(source).tokenize()
    program = Parser(tokens).parse()
    ir = Compiler().compile(program)
    vm = VM(ir, natives=natives)
    vm.run()
    return vm


class TestLexer(unittest.TestCase):
    def test_keywords_and_operators(self):
        src = "bind mut fn if else loop return print true false int bool string void"
        tokens = Lexer(src).tokenize()
        types = [t.type for t in tokens if t.type != "EOF"]
        self.assertIn("BIND", types)
        self.assertIn("FN", types)
        self.assertIn("IF", types)

    def test_numbers_and_strings(self):
        src = "bind x = 42; bind s = \"hi\";"
        tokens = Lexer(src).tokenize()
        ints = [t for t in tokens if t.type == TT_INT]
        self.assertEqual(ints[0].lexeme, "42")
        strs = [t for t in tokens if t.type == "STRING"]
        self.assertEqual(strs[0].lexeme, "hi")

    def test_comments(self):
        src = "bind x = 5; // comment\nbind y = 6;"
        tokens = Lexer(src).tokenize()
        lexemes = [t.lexeme for t in tokens]
        self.assertNotIn("// comment", lexemes)

    def test_unterminated_string(self):
        with self.assertRaises(LexerError):
            Lexer('bind x = "oops;').tokenize()

    def test_token_location(self):
        tokens = Lexer("bind x = 5;").tokenize()
        bind_tok = tokens[0]
        self.assertEqual(bind_tok.line, 1)
        self.assertEqual(bind_tok.column, 1)


class TestParser(unittest.TestCase):
    def test_parse_program(self):
        src = "bind x = 5;"
        program = Parser(Lexer(src).tokenize()).parse()
        self.assertIsInstance(program, Program)
        self.assertEqual(len(program.statements), 1)

    def test_function(self):
        src = "fn add(x, y) { return x + y; }"
        program = Parser(Lexer(src).tokenize()).parse()
        fn = program.statements[0]
        self.assertEqual(fn.name, "add")
        self.assertEqual(len(fn.params), 2)

    def test_if_else(self):
        src = "if true { bind a = 1; } else { bind a = 2; }"
        program = Parser(Lexer(src).tokenize()).parse()
        stmt = program.statements[0]
        self.assertIsNotNone(stmt.else_branch)

    def test_loop_break(self):
        src = "loop { break; }"
        program = Parser(Lexer(src).tokenize()).parse()
        self.assertIsInstance(program.statements[0], LoopStmt)

    def test_fn_node(self):
        src = "fn f(x) { return x; }"
        program = Parser(Lexer(src).tokenize()).parse()
        self.assertIsInstance(program.statements[0], FnStmt)
        self.assertEqual(program.statements[0].name, "f")


class TestSemantic(unittest.TestCase):
    def test_variable_type_inference(self):
        src = "bind x = 5; bind y = x + 3;"
        program = Parser(Lexer(src).tokenize()).parse()
        SemanticAnalyzer().analyze(program)  # should not raise

    def test_type_mismatch_raises(self):
        src = 'bind x = 5; bind y = "hi"; bind z = x + y;'
        program = Parser(Lexer(src).tokenize()).parse()
        with self.assertRaises((SemanticError, PlTypeError)):
            SemanticAnalyzer().analyze(program)

    def test_undefined_variable(self):
        src = "bind x = y;"
        program = Parser(Lexer(src).tokenize()).parse()
        with self.assertRaises(SemanticError):
            SemanticAnalyzer().analyze(program)

    def test_return_type_inference(self):
        src = "fn add(x, y) { return x + y; } bind z = add(1, 2);"
        program = Parser(Lexer(src).tokenize()).parse()
        SemanticAnalyzer().analyze(program)  # return type inferred as int

    def test_break_outside_loop(self):
        src = "break;"
        program = Parser(Lexer(src).tokenize()).parse()
        with self.assertRaises(SemanticError):
            SemanticAnalyzer().analyze(program)


class TestCompiler(unittest.TestCase):
    def test_compiles_to_ir(self):
        src = "bind x = 5;"
        program = Parser(Lexer(src).tokenize()).parse()
        ir = Compiler().compile(program)
        self.assertIsInstance(ir, IR)
        self.assertGreater(len(ir.instructions), 0)

    def test_compile_error_on_semantic(self):
        src = "bind x = 5; bind y = x + \"hi\";"
        program = Parser(Lexer(src).tokenize()).parse()
        with self.assertRaises(CompilerError):
            Compiler().compile(program)


class TestVM(unittest.TestCase):
    def test_arithmetic(self):
        vm = compile_and_run("bind x = 2 + 3 * 4; print x;")
        self.assertEqual(vm.stdout, ["14"])

    def test_function_call(self):
        vm = compile_and_run(
            "fn add(x, y) { return x + y; } bind r = add(2, 3); print r;")
        self.assertEqual(vm.stdout, ["5"])

    def test_loop(self):
        vm = compile_and_run(
            "mut acc = 0; mut i = 0; loop { bind b = i < 3; if b { acc = acc + 1; i = i + 1; } else { break; } } print acc;")
        self.assertEqual(vm.stdout, ["3"])

    def test_if_else(self):
        vm = compile_and_run("bind x = 1; if x == 1 { print 1; } else { print 2; }")
        self.assertEqual(vm.stdout, ["1"])

    def test_natives(self):
        natives = build_stdlib()
        vm = compile_and_run('bind s = "abc"; print length(s);', natives=natives)
        self.assertEqual(vm.stdout, ["3"])

    def test_division_by_zero_raises(self):
        with self.assertRaises(Exception):
            compile_and_run("bind x = 1 / 0;")


class TestStdlib(unittest.TestCase):
    def test_build_stdlib(self):
        stdlib = build_stdlib()
        self.assertIn("print", stdlib)
        self.assertIn("to_string", stdlib)
        self.assertIn("length", stdlib)
        self.assertEqual(stdlib["length"]("abc"), 3)
        self.assertEqual(stdlib["to_string"](True), "true")

    def test_to_string_bool(self):
        self.assertEqual(build_stdlib()["to_string"](False), "false")


class TestErrors(unittest.TestCase):
    def test_source_location(self):
        loc = SourceLocation(file="test.eal", line=3, column=5)
        self.assertEqual(str(loc), "test.eal:3:5")

    def test_error_str(self):
        err = ParseError("bad token", SourceLocation("f.eal", 1, 2))
        self.assertIn("EAL-PL f.eal:1:2", str(err))
        self.assertIn("bad token", str(err))

    def test_format_error_with_source(self):
        err = ParseError("unexpected token", SourceLocation("f.eal", 2, 4))
        out = format_error(err, "  bind x = 5;")
        self.assertIn("^", out)


class TestDebug(unittest.TestCase):
    def test_format_source_context(self):
        source = "line one\nline two\nline three\n"
        out = format_source_context(
            source, SourceLocation(file="f.eal", line=2, column=3))
        self.assertIn("line two", out)
        self.assertIn("^", out)


if __name__ == "__main__":
    unittest.main()
