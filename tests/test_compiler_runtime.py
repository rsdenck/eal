"""Unit tests for EAL-COMPILER and EAL-RUNTIME (stdlib only)."""

from __future__ import annotations

import unittest

from eal_compiler import CompilationResult, CompilerToolchain, Diagnostic
from eal_runtime import ExecutionResult, ResourceLimits, Runtime, Sandbox
from eal_pl import build_stdlib
from eal_pl.ir import IR, Op


class TestDiagnostic(unittest.TestCase):
    def test_to_dict(self):
        d = Diagnostic(severity="error", code="E", message="bad",
                       location=None)
        self.assertEqual(d.to_dict()["severity"], "error")


class TestCompilerToolchain(unittest.TestCase):
    def setUp(self):
        self.tc = CompilerToolchain()

    def test_compile_valid(self):
        src = "bind x = 5; print x;"
        result = self.tc.compile(src)
        self.assertTrue(result.success)
        self.assertIsNotNone(result.ir)
        self.assertEqual(len(result.diagnostics), 0)

    def test_compile_invalid(self):
        src = "bind x = 5; bind y = x + \"hi\";"
        result = self.tc.compile(src)
        self.assertFalse(result.success)
        self.assertIsNone(result.ir)
        self.assertGreaterEqual(len(result.diagnostics), 1)

    def test_reproducible_hash(self):
        src = "bind x = 5;"
        r1 = self.tc.compile(src)
        r2 = self.tc.compile(src)
        self.assertEqual(r1.reproducible_hash, r2.reproducible_hash)

    def test_validate(self):
        src = "bind x = 5;"
        diags = self.tc.validate(src)
        self.assertEqual(len(diags), 0)


class TestVMIntegration(unittest.TestCase):
    def test_compile_and_run(self):
        tc = CompilerToolchain()
        result = tc.compile_and_run(
            "bind a = 2; bind b = 3; bind c = a + b; print c;",
            natives=build_stdlib(),
        )
        self.assertTrue(result.success)
        self.assertEqual(result.ir is not None, True)
        # Check output captured in diagnostics
        output_text = " ".join(d.message for d in result.diagnostics)
        self.assertIn("5", output_text)


class TestSandbox(unittest.TestCase):
    def test_execute_simple(self):
        ir = IR()
        ir.add(Op.CONST, ir.constant(41))
        ir.add(Op.CONST, ir.constant(1))
        ir.add(Op.ADD)
        ir.add(Op.HALT)
        sandbox = Sandbox()
        result = sandbox.execute(ir)
        self.assertTrue(result.success)
        self.assertEqual(result.result, 42)
        self.assertEqual(result.steps, 4)

    def test_step_limit(self):
        ir = IR()
        # Infinite loop: JMP to itself
        ir.add(Op.JMP, 0)
        ir.add(Op.HALT)
        sandbox = Sandbox(limits=ResourceLimits(max_steps=5))
        result = sandbox.execute(ir)
        self.assertFalse(result.success)
        self.assertTrue(result.hit_limit)
        self.assertEqual(result.steps, 5)

    def test_memory_limit_applied(self):
        sandbox = Sandbox()
        # Should not raise
        self.assertIsNotNone(sandbox.limits)


class TestRuntime(unittest.TestCase):
    def test_run_source(self):
        rt = Runtime(natives=build_stdlib())
        result = rt.run_source("bind x = 10; print x;")
        self.assertTrue(result.success)
        self.assertEqual(result.output, ["10"])

    def test_run_source_error(self):
        rt = Runtime()
        result = rt.run_source("bind x = 1 / 0;")
        self.assertFalse(result.success)


if __name__ == "__main__":
    unittest.main()
