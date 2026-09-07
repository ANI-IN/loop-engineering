"""Relaunch the sweep in its own session and hand the terminal straight back.

**Detaching is the default and that is deliberate.** A sweep that holds the terminal
cannot be started at the top of a stage while you keep talking, which is the entire reason
it exists.

This lives in `src/` rather than in the entry point because it is process management, not
argument wiring — the demo's job is to parse flags, call in, and print.

CALLERS MUST VALIDATE CREDENTIALS BEFORE CALLING THIS

Detaching first meant a keyless sweep printed `sweep detached: pid 41293`, exited 0, and
died in a log file the operator had no reason to open — at the top of the most expensive
stage, in front of a room, with the terminal handed back looking like success. The one
failure the fail-fast design exists to prevent was the one failure detaching hid.

So `load_settings()` runs in the process the operator is still watching, and its
`MissingCredential` reaches them as the sentence naming the variable and the fix. The
constraint is recorded here rather than only at the one call site, because it binds
every caller of this function and the next one will not have read that call site.
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
