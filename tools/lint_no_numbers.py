"""Bans numeric literals in the files that render measurements to the room.

A typed number is indistinguishable from a measured one once it is on a
projector. Everywhere else numbers are fine — the warehouse generator, the
statistics, the tests all need them. The scope below is the set of files where a
literal would reach an audience wearing the same clothes as a `Metric`.

0 and 1 are permitted. They are structural (indexing, len(x) - 1, boolean-ish
arithmetic) and cannot encode a finding.

WHAT THIS RULE GOT WRONG, THREE TIMES
-------------------------------------

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

**And then it banned the wrong syntax.** This is the third, and it is the sharpest,
because the rule was green and enforcing the opposite of its own justification.

`scan()` inspected `ast.Constant` nodes whose value was `int | float`. A number inside
a *string* is an `ast.Constant` of type `str`, so it was skipped. Verified:

    scan(Path('src/loopeng/views/dial.py'))          -> ([], 0)   ...clean
    scan(<a file containing only>)                   -> ([], 0)   ...also clean
      LABEL = "accuracy improved to 94.7% (p=0.039)"

Meanwhile `views/dial.py` — described in the target list below as "the single most
quoted screen in the session" — contained two hardcoded statistical conclusions:

    ("L0", "Haiku + loop is better (McNemar exact p=0.039)")
    ("L3", "**cannot tell apart at this n** (p=0.250) — not equal; ...")

Two typed p-values, rendered to a room, passing a rule written specifically to stop
that. The rule banned the *syntax* of a typed number while the actual failure mode is
a number **inside a display string** — which is the only form that reaches a projector
anyway. A bare `PASS_RATE = 78` never reaches anyone; `f"pass rate {78}%"` does.

So `scan()` now also inspects `str` constants, and f-string literal parts, for
measurement-shaped text. The fix to `views/dial.py` was to derive those readings from
the cells on disk through `loopeng.sweep.diff`, which is what the rule was asking for
all along.

WHAT IS AND IS NOT SCANNED AS A STRING
--------------------------------------

**Docstrings and comments are out of scope, deliberately.** Nothing in this repo renders
a docstring to a screen, and the comments here are where measured numbers get their
provenance recorded. `registry.py` explains the temperature decision with the
disagreement floor it was measured at; `gold/compare.py` pins its tolerance between two
measured values. Banning those would strip exactly the rationale that makes this codebase
reviewable, in exchange for catching nothing anyone can see.

That first clause used to end "— checked, not assumed", and nothing checked it. In this
repository that phrase means *a test enforces this*; here it meant somebody had grepped
once, which is the gap between declared and enforced appearing in the docstring of the
module written to close it. It now points at its own enforcement:

    tests/test_lint_no_numbers.py::test_nothing_in_this_repo_routes_a_docstring_to_a_rendered_surface

That test walks every module under `src/`, `demos/`, `deploy/` and `tools/` for a runtime
read of `__doc__` — including `description=__doc__`, the argparse habit that would put a
module docstring on a terminal — and for the `inspect` helpers that reach one indirectly.
The day one of them appears, every number in every docstring here is a rendered surface
and this exemption has to be revisited.

The scope is therefore: string constants that can reach a rendered surface. That is
narrower than "every string" and it is the whole failure mode.

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
project refuses, and that applies to the count of its own escape hatches. **Both**
counts are printed: `# layout` markers, and the method-allowlist hits below.
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

# ---------------------------------------------------------------------------
# Measurement-shaped text inside a string. See the module docstring: this is the
# only form of typed number that actually reaches a reader, and it was the one
# form the rule did not look at.
#
# Each pattern is a shape a reader will take as a result. Named so a violation
# message can say WHAT it thinks was typed, rather than only that something was.
# ---------------------------------------------------------------------------
MEASUREMENT_SHAPES = (
    (re.compile(r"\bp\s*[=<>]\s*0?\.\d+"), "a p-value"),
    (re.compile(r"\d+(?:\.\d+)?\s*%"), "a percentage"),
    (re.compile(r"\bn\s*=\s*\d+"), "an n"),
    (re.compile(r"\b\d+\s*/\s*\d+\b"), "a count out of a total"),
    (re.compile(r"±\s*\d+(?:\.\d+)?"), "an interval"),
    (re.compile(r"\$\s*\d"), "a dollar figure"),
)

# Measurement-shaped text that describes the METHOD rather than a result.
#
# Enumerated phrases, not a loose regex, and that is the point. A regex exemption can be
# widened by accident and nobody notices; a list of exact phrases can only be widened by
# adding a line, in a diff, with a reason. The count of hits is printed on every run
# alongside the `# layout` count, for the same reason: an escape hatch nobody counts is
# how a rule ends up exempting what it was written to catch.
#
# One comment per entry, saying why it is not a finding.
# Every entry must be reachable — a test fails the build on a dead one. Three obvious
# candidates are deliberately NOT here, because the shapes above are narrow enough not to
# need them: `temperature=0` and `alpha=0.05` are `<name>=<num>`, which no pattern matches
# (a named parameter is a setting, not a result, and catching it would create pressure to
# widen the exemptions); `power 0.80` is a bare decimal, likewise unmatched. If a future
# pattern catches a parameter assignment, that pattern is probably the mistake.
METHOD_ALLOWLIST = (
    # The confidence level of the interval, not something measured with it. Appears in
    # every caption that draws error bars, and dropping it would leave the bars
    # unlabelled — a reader cannot check an interval whose level is not stated.
    "Wilson 95%",
)


def _strip_allowlisted(text: str) -> tuple[str, int]:
    """Remove the enumerated method phrases, and count how many were removed."""
    hits = 0
    for phrase in METHOD_ALLOWLIST:
        found = text.count(phrase)
        if found:
            text = text.replace(phrase, "")
            hits += found
    return text, hits


def _docstring_nodes(tree: ast.AST) -> set[int]:
    """`id()` of every Constant that is a docstring.

    Out of scope by design — nothing here renders a docstring, and the comments and
    docstrings in this codebase are where measured numbers get their provenance. That
    premise is asserted by
    `tests/test_lint_no_numbers.py::test_nothing_in_this_repo_routes_a_docstring_to_a_rendered_surface`
    rather than grepped once; see the module docstring.
    """
    ids = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef
                          | ast.AsyncFunctionDef):
            continue
        body = getattr(node, "body", ())
        if (body and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)):
            ids.add(id(body[0].value))
    return ids


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


def scan(path: Path) -> tuple[list[tuple[int, str]], int, int]:
    """Return (violations, n_layout_exempt, n_method_exempt) for one file.

    A path that does not exist yields nothing rather than raising, so this stays
    usable for ad-hoc checks. Whether a *declared* target may be absent is a
    different question, answered by missing_targets().
    """
    if not path.is_file():
        return [], 0, 0

    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    exempt = _exempt_lines(source)
    docstrings = _docstring_nodes(tree)

    violations: list[tuple[int, str]] = []
    n_layout = 0
    n_method = 0

    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant):
            continue

        # ---- a number written as a number ----------------------------------
        # bool is a subclass of int, so this test has to come first or `if flag
        # is True` becomes a lint error and the rule gets switched off in a week.
        if isinstance(node.value, bool):
            continue
        if isinstance(node.value, int | float):
            if node.value in ALLOWED:
                continue
            if node.lineno in exempt:
                n_layout += 1
                continue
            violations.append((node.lineno, f"numeric literal {node.value!r}"))
            continue

        # ---- a number written inside a string ------------------------------
        # The form that actually reaches a projector, and the one the rule missed
        # for its whole life. f-string literal parts are Constants too, so they
        # arrive here without any special handling — and a value INTERPOLATED into
        # an f-string is not a Constant at all, which is exactly right: that is a
        # derived number and always was allowed.
        if not isinstance(node.value, str):
            continue
        if id(node) in docstrings:
            continue
        if node.lineno in exempt:
            n_layout += 1
            continue
        text, method_hits = _strip_allowlisted(node.value)
        n_method += method_hits
        for pattern, what in MEASUREMENT_SHAPES:
            match = pattern.search(text)
            if match:
                violations.append(
                    (node.lineno, f"{what} in a display string: {match.group(0)!r}")
                )
                break

    return sorted(violations), n_layout, n_method


def find_violations(path: Path) -> list[tuple[int, str]]:
    """Every banned literal in `path`, as (lineno, description)."""
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
    total_layout = 0
    total_method = 0
    for path in paths:
        violations, n_layout, n_method = scan(path)
        total_layout += n_layout
        total_method += n_method
        for lineno, what in violations:
            print(f"{path}:{lineno}: {what} — derive it from a Metric or a cell file")
            found = True

    if not found:
        # Printed on success too, and BOTH counts are. An escape hatch whose usage
        # nobody counts is how a rule ends up exempting everything it was written to
        # catch — and that applies to the second hatch as much as the first.
        print(
            f"no typed measurements in {len(paths)} rendering file(s); "
            f"{total_layout} literal(s) marked `# layout`; "
            f"{total_method} method phrase(s) exempted by "
            f"{len(METHOD_ALLOWLIST)} allowlist entries"
        )

    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
