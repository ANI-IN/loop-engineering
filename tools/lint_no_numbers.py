"""Bans numeric literals in the files that render measurements to the room.

A typed number is indistinguishable from a measured one once it is on a
projector. Everywhere else numbers are fine — the warehouse generator, the
statistics, the tests all need them. The scope below is the set of files where a
literal would reach an audience wearing the same clothes as a `Metric`.

0 and 1 are permitted. They are structural (indexing, len(x) - 1, boolean-ish
arithmetic) and cannot encode a finding.

WHAT THIS RULE GOT WRONG, TWICE
-------------------------------

**It pointed at a path that no longer existed.** `app/views.py` moved into
`src/loopeng/views/` during the restructure and the rule kept naming the old
path. It scanned nothing there, found nothing, and exited 0 — a green build that
had inspected nothing. That is the declared-versus-enforced defect this project
is about, in our own tooling. A declared target that does not resolve is now a
build failure: see `missing_targets()`.

**The test written to prevent that could not.** It planted a violation by
*writing* the target file, which CREATED the missing path — so it proved the AST
walker worked while never once checking the target was real.

**And the surviving target caught nothing.** `demos/.../charts.py` is a thin
entry point that renders through `loopeng.sweep.charts`; it has no literals
because it has almost no code. Live coverage was zero across the whole rule. The
targets below are the modules that actually build what a room reads.

THE LAYOUT EXEMPTION
--------------------

Widening the scope to the real renderers pulls in geometry — SVG viewBox bounds,
bar heights, string truncation widths, slider steps. None of those can encode a
finding, and banning them would make the rule irritating enough to be switched
off, which protects less than a narrow rule people keep.

So a literal is exempt when its line carries a trailing `# layout` comment. One
mechanism, per line, at the site — the same shape as `# noqa`, so it needs no
explanation. It is deliberately NOT a file-level or block-level opt-out: an
author has to make the claim "this is geometry, not a measurement" on the exact
line, where a reviewer and `git diff` both see it.

Exemptions are counted and printed. A number that grows quietly is the thing this
project refuses, and that applies to the count of its own escape hatches.
"""

import ast
import re
import sys
from pathlib import Path

# Anchored to the repo root via this file's own location, not to the working
# directory. A cwd-relative target would make the rule pass silently when invoked
# from a subdirectory — a lint rule that reports success without having looked at
# anything is the exact defect this project exists to teach about, so it does not
# get to have that failure mode itself.
REPO_ROOT = Path(__file__).resolve().parent.parent

_VIEWS = REPO_ROOT / "src" / "loopeng" / "views"

# The modules that build what a room reads.
#
#   sweep/charts.py    the DIAL, COST, DELTA and ABSTENTION SVGs — the densest
#                      numeric surface here
#   sweep/chart_model.py the captions and the cell-to-row transform BOTH renderers
#                      consume; a typed number here reaches the projector and the README
#   views/render.py    every string renderer the views share — the reveal scoreboard,
#                      the attempt timeline, the declined list. Added when the
#                      duplicated renderers were consolidated into it: moving that
#                      prose out of a scanned file into an unscanned one would have
#                      quietly reduced the rule's coverage while looking like cleanup.
#   views/dial.py      silent-error rate per cell and the named-secondary table,
#                      the single most quoted screen in the session
#   views/oversight.py the coverage/precision curve and the escalation panel
#   views/trap.py      the reveal grid
#   views/verify.py    the swap table and the probe surface
#   views/agent.py     the attempt timeline and the queue table
#   views/intervention.py what the loop declined and why
#   views/exhibit.py   the public frozen exhibit, which outlives the session
#   demos/.../charts.py the entry point that renders them live
#
# NOT in scope: views/chrome.py. It is furniture and infrastructure — queue
# bounds, a socket probe, a CSS string — and renders no measurement of its own.
TARGETS = (
    REPO_ROOT / "src" / "loopeng" / "sweep" / "charts.py",
    REPO_ROOT / "src" / "loopeng" / "sweep" / "chart_model.py",
    _VIEWS / "render.py",
    _VIEWS / "dial.py",
    _VIEWS / "oversight.py",
    _VIEWS / "trap.py",
    _VIEWS / "verify.py",
    _VIEWS / "agent.py",
    _VIEWS / "intervention.py",
    _VIEWS / "exhibit.py",
    REPO_ROOT / "demos" / "04_hill_climbing_loop" / "charts.py",
)

ALLOWED = {0, 1}

# Trailing `# layout`, optionally with a reason after it. Anchored to a comment
# so the word appearing inside a string cannot exempt anything.
LAYOUT_MARKER = re.compile(r"#\s*layout\b")


def missing_targets() -> list[Path]:
    """Declared targets that are not on disk.

    A target that moved or was deleted makes the rule vacuous. Reported as a
    failure rather than skipped, because a green build that checked nothing is
    worse than a red one.
    """
    return [path for path in TARGETS if not path.is_file()]


def _exempt_lines(source: str) -> set[int]:
    """1-indexed line numbers carrying a `# layout` marker."""
    return {
        number
        for number, line in enumerate(source.splitlines(), start=1)
        if LAYOUT_MARKER.search(line)
    }


def scan(path: Path) -> tuple[list[tuple[int, str]], int]:
    """Return (violations, n_exempt) for one file.

    A path that does not exist yields nothing rather than raising, so this stays
    usable for ad-hoc checks. Whether a *declared* target may be absent is a
    different question, answered by missing_targets().
    """
    if not path.is_file():
        return [], 0

    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    exempt = _exempt_lines(source)

    violations: list[tuple[int, str]] = []
    n_exempt = 0

    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant):
            continue
        # bool is a subclass of int, so this test has to come first or `if flag
        # is True` becomes a lint error and the rule gets switched off in a week.
        if isinstance(node.value, bool):
            continue
        if not isinstance(node.value, int | float):
            continue
        if node.value in ALLOWED:
            continue
        if node.lineno in exempt:
            n_exempt += 1
            continue
        violations.append((node.lineno, repr(node.value)))

    return sorted(violations), n_exempt


def find_violations(path: Path) -> list[tuple[int, str]]:
    """Every banned numeric literal in `path`, as (lineno, literal_repr)."""
    return scan(path)[0]


def main(argv: list[str] | None = None) -> int:
    """Check the given paths, or the real targets when given none."""
    if argv:
        paths = [Path(arg) for arg in argv]
    else:
        absent = missing_targets()
        if absent:
            for path in absent:
                print(
                    f"{path}: declared lint target does not exist. The rule would "
                    f"scan nothing here and report success — fix the path in "
                    f"tools/lint_no_numbers.py or remove the target."
                )
            return 1
        paths = list(TARGETS)

    found = False
    total_exempt = 0
    for path in paths:
        violations, n_exempt = scan(path)
        total_exempt += n_exempt
        for lineno, literal in violations:
            print(f"{path}:{lineno}: numeric literal {literal} — use a Metric instead")
            found = True

    if not found:
        # Printed on success too. An escape hatch whose usage nobody counts is
        # how a rule ends up exempting everything it was written to catch.
        print(
            f"no typed measurements in {len(paths)} rendering file(s); "
            f"{total_exempt} literal(s) marked `# layout`"
        )

    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
