"""Migrate and, when needed, seed the tests' own database (make test-stack). The connection details
live once, in the tests' stack_for_tests module, which the test conftest also uses."""

from __future__ import annotations

import sys
from pathlib import Path

TESTS = Path(__file__).resolve().parents[1] / "tests"
sys.path.insert(0, str(TESTS))

import stack_for_tests  # noqa: E402

if __name__ == "__main__":
    stack_for_tests.prepare()
