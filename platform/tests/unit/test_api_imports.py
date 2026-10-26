"""Each service's entry module imports on its own in a fresh interpreter, as its container starts
it. Live, 26 October 2026: a circular import (api.events -> demos -> scheduler -> api.events) kept
the api from starting, while the unit suite passed because it imported the modules in another
order (zero tokens)."""

from __future__ import annotations

import subprocess
import sys

import pytest


@pytest.mark.parametrize(
    "module",
    [
        "datapilot.loop3_events.api.app",
        "datapilot.loop3_events.worker",
        "datapilot.loop3_events.scheduler",
        "datapilot.loop4_hill_climbing.runner",
        "datapilot.cli",
    ],
)
def test_a_service_entry_module_imports_alone(module: str) -> None:
    done = subprocess.run(
        [sys.executable, "-c", f"import {module}"], capture_output=True, text=True, timeout=120
    )
    assert done.returncode == 0, done.stderr[-2000:]
