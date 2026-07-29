"""Triage: classify failures by CAUSE, not by count.

A failure rate says how often something went wrong. It does not say whether the model
was wrong, the gold answer was wrong, the question was ambiguous, or the harness
mangled a comparison — and those need entirely different fixes. Counting them together
produces a number that improves when you fix the wrong thing.

Four causes:

  model    — the model wrote a query that genuinely answers the wrong question
  gold     — OUR expected answer is wrong. In the prior build this happened four times.
             It is listed first among the things to look for, because it is the one a
             failure rate will never surface: a wrong gold answer makes a correct model
             look broken, forever, and every "improvement" measured against it is noise.
  question — the question admits more than one defensible reading
  harness  — the comparison, classification or plumbing mishandled a correct answer

Classification is done BY HAND, on real failures, with the SQL and both answers in
front of you. There is deliberately no automatic classifier: one would inherit the
harness's own blind spots and would never assign `harness` to anything.
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

CAUSES = ("model", "gold", "question", "harness")

CAUSE_MEANING = {
    "model": "the model answered a different question than the one asked",
    "gold": "our expected answer is wrong — the model may well be right",
    "question": "the question admits more than one defensible reading",
    "harness": "a correct answer was mishandled by comparison, classification or plumbing",
}


@dataclass(frozen=True)
class TriagedFailure:
    item_id: str
    arm: str
    cause: str
    note: str
    model_rows: str
    gold_rows: str

    def __post_init__(self):
        if self.cause not in CAUSES:
            raise ValueError(f"unknown cause {self.cause!r}; expected one of {CAUSES}")


def summarise(failures: list[TriagedFailure]) -> dict:
    counts = {cause: sum(1 for f in failures if f.cause == cause) for cause in CAUSES}
    gold_wrong = counts["gold"]
    return {
        "n_triaged": len(failures),
        "by_cause": counts,
        "meanings": CAUSE_MEANING,
        "gold_defects_found": gold_wrong,
        "gold_verdict": (
            f"{gold_wrong} of {len(failures)} triaged failures were OUR gold answer "
            "being wrong. Every one of those makes a correct model look broken and "
            "poisons every comparison measured against it."
            if gold_wrong
            else f"No gold defects found in {len(failures)} triaged failures. The prior "
            "build found four, so this is worth stating explicitly rather than "
            "leaving as an absence."
        ),
        "failures": [asdict(f) for f in failures],
    }


def save(failures: list[TriagedFailure], path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summarise(failures), indent=2), encoding="utf-8")
    return path


def candidates(cells: list[dict], limit: int = 20) -> list[dict]:
    """Silent errors worth a human look, spread across patterns.

    Spread deliberately: twenty failures from one pattern would triage one bug twenty
    times and say nothing about the rest.
    """
    pool = [
        {**row, "arm": cell["key"]}
        for cell in cells
        for row in cell.get("items", [])
        if row.get("outcome") == "silent_error"
    ]
    by_pattern: dict[str, list[dict]] = {}
    for row in pool:
        by_pattern.setdefault(row["pattern_key"], []).append(row)

    picked, index = [], 0
    while len(picked) < limit and any(len(v) > index for v in by_pattern.values()):
        for pattern in sorted(by_pattern):
            if len(picked) >= limit:
                break
            if len(by_pattern[pattern]) > index:
                picked.append(by_pattern[pattern][index])
        index += 1
    return picked
