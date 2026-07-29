"""One check for an environment that silently breaks Python imports.

This exists because of a real failure, not a hypothetical one. With the project
on an iCloud-synced path, macOS set UF_HIDDEN on every file under .venv —
including the `.pth` file that puts src/ on sys.path. CPython's site.addpackage
skips hidden `.pth` files without a word, so `import loopeng` failed with a bare
ModuleNotFoundError. Running `chflags -R nohidden` fixed it for about five
seconds before iCloud set the flag again.

The failure mode is what makes it worth a guard: it is intermittent, it produces
an error message that points nowhere near the cause, and it would be very hard to
debug in front of a room.

One function, two callers. The pytest caller protects the build; the import-time
caller in settings.py protects the live session, and the session is the one that
matters — a green suite this morning says nothing about the venv's flags now.

Offline and cheap by construction: string comparisons plus a handful of stat
calls. No network, no subprocess.
"""

import stat
import sys
from collections.abc import Iterable
from pathlib import Path

# Both spellings appear in real paths: the container directory and its
# user-visible alias.
ICLOUD_MARKERS = ("Library/Mobile Documents", "com~apple~CloudDocs")

_FIX = (
    "Move the project to a path outside iCloud (for example ~/Projects/), then "
    "run `uv sync` there. iCloud sets UF_HIDDEN on .pth files, and CPython "
    "silently ignores hidden .pth files, so the editable install disappears."
)


class EnvironmentUnsafe(RuntimeError):
    """The environment will break imports or corrupt results. Names the fix."""


def _under_icloud(path: Path) -> bool:
    resolved = str(path.resolve())
    return any(marker in resolved for marker in ICLOUD_MARKERS)


def _hidden_pth_files(prefix: Path) -> list[Path]:
    """`.pth` files carrying UF_HIDDEN, which CPython's site module skips.

    st_flags is BSD-only; on platforms without it getattr returns 0 and this
    check correctly finds nothing rather than raising.
    """
    hidden = []
    for pth in prefix.glob("lib/python*/site-packages/*.pth"):
        try:
            flags = getattr(pth.stat(), "st_flags", 0)
        except OSError:
            continue
        if flags & getattr(stat, "UF_HIDDEN", 0):
            hidden.append(pth)
    return hidden


def check_environment(
    *,
    prefix: Path | None = None,
    paths: Iterable[Path] | None = None,
) -> str | None:
    """Return a problem-and-fix message, or None when the environment is sound.

    Returns rather than raises so the two callers can decide what to do: the test
    asserts on it, settings.py raises on it.
    """
    prefix = Path(sys.prefix) if prefix is None else Path(prefix)
    if paths is None:
        # Defaults match Settings' defaults. Both are relative, so they resolve
        # against the working directory the session actually runs in.
        paths = (Path("warehouse.duckdb"), Path("results"))

    problems: list[str] = []

    if _under_icloud(prefix):
        problems.append(f"The Python environment is on an iCloud-synced path: {prefix}")

    for path in paths:
        if _under_icloud(path):
            problems.append(f"A data path is on an iCloud-synced path: {path.resolve()}")

    for pth in _hidden_pth_files(prefix):
        problems.append(
            f"{pth} carries UF_HIDDEN, so CPython is ignoring it and the "
            f"editable install is not on sys.path"
        )

    if not problems:
        return None
    return "\n".join(problems) + "\n\nFix: " + _FIX
