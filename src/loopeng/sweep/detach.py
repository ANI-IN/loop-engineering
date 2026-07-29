"""Relaunch the sweep in its own session and hand the terminal straight back.

**Detaching is the default and that is deliberate.** A sweep that holds the terminal
cannot be started at the top of a stage while you keep talking, which is the entire reason
it exists.

This lives in `src/` rather than in the entry point because it is process management, not
argument wiring — the demo's job is to parse flags, call in, and print.
"""

import os
import subprocess
import sys
from pathlib import Path


def detach(script: Path, argv: list[str] | None, log_path: str) -> int:
    """Start `script` detached, log to `log_path`, and print how to watch it."""
    log = Path(log_path)
    log.parent.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, str(script), *(argv or sys.argv[1:]), "--foreground"]
    with log.open("w") as handle:
        process = subprocess.Popen(
            command, stdout=handle, stderr=subprocess.STDOUT,
            start_new_session=True,  # survives the terminal closing
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
    print(f"sweep detached: pid {process.pid}")
    print(f"  progress : tail -f {log}")
    print("  charts   : uv run python demos/04_hill_climbing_loop/charts.py")
    print("  the terminal is yours again.")
    return 0
