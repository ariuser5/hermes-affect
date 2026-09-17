"""Regression coverage for the canonical and compatibility calibration CLIs."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


class CalibrationCliTests(unittest.TestCase):
    modules = ("hermes_affect.tools.calibration", "hermes_affect.calibration")

    @property
    def repository_root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    def run_cli(self, module: str, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", module, *arguments],
            cwd=self.repository_root,
            capture_output=True,
            text=True,
        )

    def test_both_module_paths_support_help(self) -> None:
        for module in self.modules:
            with self.subTest(module=module):
                result = self.run_cli(module, "--help")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("usage:", result.stdout.lower())

    def test_both_module_paths_produce_equivalent_group_json(self) -> None:
        outputs = []
        for module in self.modules:
            with self.subTest(module=module):
                result = self.run_cli(module, "--scenario", "group", "--compare", "--json")
                self.assertEqual(result.returncode, 0, result.stderr)
                outputs.append(json.loads(result.stdout))
        self.assertEqual(outputs[0], outputs[1])

    def test_both_module_paths_reject_invalid_arguments(self) -> None:
        for module in self.modules:
            with self.subTest(module=module):
                result = self.run_cli(module, "--not-a-real-option")
                self.assertNotEqual(result.returncode, 0)
