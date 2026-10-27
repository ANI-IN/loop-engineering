"""Check that the slide outline is up to date: it builds cleanly and equals the committed copy.

Usage: python platform/scripts/check_outline.py [--root PATH]

Builds the outline from its block modules (slides/source/build.py, which ships with the outline)
into a temporary file, as the outline check of the verification gate (platform/scripts/verify.sh)
does, then requires the build's "problems: 0" line and a byte-for-byte match with
slides/outline.md. On a mismatch it prints the first lines that differ. Writes no tracked file.
Exits 1 on any problem, else 0.
"""

from __future__ import annotations

import argparse
import difflib
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").is_file())
BUILD = "slides/source/build.py"
OUTLINE = "slides/outline.md"
DIFF_LINES = 20


def outline_problems(report: str, built: str, committed: str | None) -> list[str]:
    """The problems of one build: its report, the outline it wrote, and the committed outline."""
    problems: list[str] = []
    if "problems: 0" not in report.splitlines():
        problems.append(f"{BUILD} reports problems: fix the block modules, then run make outline")
    if committed is None:
        problems.append(f"{OUTLINE} is missing: run make outline and commit it")
    elif built != committed:
        diff = list(
            difflib.unified_diff(
                committed.splitlines(),
                built.splitlines(),
                f"{OUTLINE} (committed)",
                f"{OUTLINE} (built)",
                lineterm="",
                n=1,
            )
        )
        shown = "\n".join(diff[:DIFF_LINES])
        more = f"\n... {len(diff) - DIFF_LINES} more diff lines" if len(diff) > DIFF_LINES else ""
        problems.append(f"{OUTLINE} is out of date: run make outline and commit it\n{shown}{more}")
    return problems


def build(root: Path) -> tuple[int, str, str]:
    """(exit code, report, built outline) of the root's own outline build."""
    with tempfile.TemporaryDirectory() as folder:
        out = Path(folder) / "outline.md"
        done = subprocess.run(
            [sys.executable, str(root / BUILD), str(out)],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        built = out.read_bytes().decode("utf-8") if out.is_file() else ""
    return done.returncode, done.stdout + done.stderr, built


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=REPO, help="the tree to check")
    root = parser.parse_args(argv).root.resolve()
    code, report, built = build(root)
    print("\n".join(report.splitlines()[-3:]))
    committed_path = root / OUTLINE
    committed = committed_path.read_bytes().decode("utf-8") if committed_path.is_file() else None
    problems = outline_problems(report, built, committed)
    if code != 0 and not problems:
        problems.append(f"{BUILD} exited with {code}")
    for problem in problems:
        print(f"x {problem}")
    print(f"outline check: {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
