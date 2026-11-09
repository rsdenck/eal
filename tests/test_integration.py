"""Integration tests for PHASE 10 end-to-end experiment (stdlib only)."""

from __future__ import annotations

import subprocess
import sys
import unittest


class TestIntegrationRuns(unittest.TestCase):
    def test_integration_experiment_runs(self):
        """The end-to-end experiment script runs and reports PASS."""
        result = subprocess.run(
            [sys.executable, "experiments/integration.py"],
            capture_output=True, text=True, cwd="/root/eal-repo",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Overall: PASS", result.stdout)
        self.assertIn("Definition of Done", result.stdout)


if __name__ == "__main__":
    unittest.main()
