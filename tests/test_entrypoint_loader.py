"""Regression coverage for Hermes' directory-based plugin loading."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


class EntrypointLoaderTests(unittest.TestCase):
    def test_root_entrypoint_loads_without_checkout_on_python_path(self) -> None:
        repository_root = Path(__file__).resolve().parents[1]
        script = """
import importlib.util
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()
sys.path = [
    entry
    for entry in sys.path
    if Path(entry or '.').resolve() != root
]
spec = importlib.util.spec_from_file_location(
    'hermes_affect_directory_entrypoint',
    root / '__init__.py',
)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
spec.loader.exec_module(module)
assert callable(module.register)
"""

        subprocess.run(
            [sys.executable, "-c", script, str(repository_root)],
            check=True,
            capture_output=True,
            text=True,
        )
