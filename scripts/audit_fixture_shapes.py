"""Does any test fixture describe a structure no real producer emits? An AUDIT, not a test.

`cost_per_correct_chart` read `arm["label"]`. No arm summary carries that key —
`summarise_arm` does not emit it — and the chart passed every test because the fixture
invented it. It raised `KeyError` the first time it saw real data, which was after the
dress rehearsal, on the session's own cost figure.

That is a DIFFERENT failure from "the chart was never drawn with populated input", which
`test_every_chart_is_drawn_with_populated_input` covers. Here the fixture was populated,
and populated with a shape reality does not produce, so the test and the code agreed with
each other and both disagreed with the world.

    uv run python scripts/audit_fixture_shapes.py

WHY THIS IS A SCRIPT AND NOT A TEST, WHICH IS THE POINT WORTH READING

It was written as a test first. Its own meta-test — the convention this repository uses
because a checker that silently matches nothing is indistinguishable from one that passes
— immediately showed the check CANNOT CATCH THE DEFECT IT WAS WRITTEN FOR:

  * `_arm_cost` built `{"label", "level", "cost_per_correct_usd"}`. Three keys, of which
    two overlap any known shape, which is below the threshold at which a dict is taken to
    be claiming a shape at all. It would have been skipped.
  * `label` is a legitimate CELL key. An arm-shaped dict carrying it classifies as a cell,
    where `label` is not a stranger, so the check passes.

Shipping it would have added a guard that is green on its own motivating example — the
exact failure mode this repository has documented twice in a lint rule. So it is an audit
you run and read, with its blind spot written down, rather than a check that would teach
someone the question had been answered.

KNOWN BLIND SPOTS, stated rather than discovered later:

  1. A fixture with fewer than MIN_OVERLAP keys in common with a producer is ignored.
  2. Where two producers share a key name, a dict is attributed to whichever it overlaps
     more, and a stranger for one shape can be legitimate for the other.
  3. Only dict literals are examined. A fixture built by a helper, a comprehension or
     `dict(...)` is invisible.

Run at 2026-09-08 over the whole suite: no fixture carried a key no producer emits.
"""

import ast
import dataclasses
import sys
from pathlib import Path

from loopeng.agent.classify import Judgement, Outcome
from loopeng.sweep.conditions import CONDITIONS, summarise_arm
from loopeng.sweep.runner import Cell, summarise_cell

REPO_ROOT = Path(__file__).resolve().parent.parent
MIN_OVERLAP = 3

_ROW = {
    "item_id": "i1", "pattern_key": "p1", "outcome": str(Outcome.CORRECT),
    "termination": "success", "rejections": 0, "cost_usd": 0.0, "sql": "SELECT 1",
    "rows": [[1]], "error": None, "ran_and_returned": True, "correct": True,
    "unearned_correct": False, "visible_kind": None, "n_attempts": 1, "tokens": {},
}


def real_shapes() -> dict[str, set[str]]:
    """The keys each producer actually emits, read from the producers."""
    return {
        "judgement": {f.name for f in dataclasses.fields(Judgement)},
        "cell": set(summarise_cell(Cell("agent", "L0", "loop"), [_ROW], complete=True,
                                   seconds=1.0)) | {"run_fingerprint"},
        "arm": set(summarise_arm(CONDITIONS["A"], [_ROW])) | {"arm", "level", "seconds"},
        "row": set(_ROW),
    }


def classify(keys: set[str], shapes: dict[str, set[str]]) -> str | None:
    best, score = None, MIN_OVERLAP - 1
    for name, real in shapes.items():
        overlap = len(keys & real)
        if overlap > score:
            best, score = name, overlap
    return best


def main() -> int:
    shapes = real_shapes()
    findings = []
    for path in sorted((REPO_ROOT / "tests").rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.Dict):
                continue
            keys = {k.value for k in node.keys
                    if isinstance(k, ast.Constant) and isinstance(k.value, str)}
            shape = classify(keys, shapes) if keys else None
            if shape and (strangers := sorted(keys - shapes[shape])):
                findings.append(f"{path.name}:{node.lineno} ({shape}) {strangers}")

    for line in findings:
        print(line)
    print(f"\n{len(findings)} fixture(s) carrying a key no producer emits"
          if findings else "\nno fixture invents a key")
    print("Blind spots are listed in this module's docstring. Read them before "
          "concluding the question is settled.")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
