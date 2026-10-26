"""Assignment 3: Event loop: the stored verdicts of the verification of 25 October 2026, from 22:47
Coordinated Universal Time, read again with the current judge, at zero cost.

Each capture (solution/captured/<variant>-run-<n>.txt) stores requirement 10's verdict line: the
category the check read and whether it read it from the answer's row or its text. It stores no
answer text, SQL, or rows, and the stack kept none either: each check clears the drill-down's
earlier runs before its own (clear_drill_down), so every one of these runs was deleted by the
check after it. So the current judge can re-judge only what the stored line decides:

- a row that names another category than gold fails under any text, since the row decides;
- a check that never reached the live step fails as it did;
- a pass, on the row or the text, depends on the answer text, which is not stored: the current
  judge cannot re-judge it, and the table says so.

Run with `-s` to print the table the captured README and the evidence page record.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pytest

from datapilot.assignments import WITHHELD_REASON, assignment, solutions_withheld
from datapilot.assignments.runner import load_check
from datapilot.contracts import RunStatus
from datapilot.contracts.api import RunDetail

pytestmark = pytest.mark.skipif(solutions_withheld(), reason=WITHHELD_REASON)

check = load_check(assignment("event-loop").check_file)
CAPTURED = assignment("event-loop").check_file.parent / "solution" / "captured"
GOLD = "Water Sports"
VARIANTS = ("reference", "alternative-one", "alternative-two")
NAMES = check.CategoryNames(
    ("Camping", "Hiking", "Apparel", "Footwear", "Climbing", "Water Sports"), ("Hiking Boots",)
)
VERDICT = re.compile(r"^(PASS|FAIL)\s+10\. ", re.M)
LIVE = re.compile(r"live run 1: (PASS|FAIL), (.*)$", re.M)
SAID = re.compile(
    r"says (?:it|(?P<category>[A-Z][\w ]+?)) rose most \((?P<where>its row|its text)\)"
)
RUN = re.compile(r"trace id ([0-9a-f]{8})")
# Texts a stored row is tried under: one agreeing with gold, one with the row, and one silent.
TEXTS = ("Water Sports rose the most.", "Hiking rose the most.", "Sales rose sharply.")


@dataclass(frozen=True)
class Stored:
    capture: str
    run: str | None
    verdict: str
    where: str | None  # "its row", "its text", or None when no live run judged an answer
    said: str | None  # the category the old judge read; None for "it" (gold)

    def now(self) -> str:
        """The current judge's verdict, where the stored record decides one."""
        if self.where is None:
            return "FAIL: no live step ran, under any judge"
        if self.where == "its row" and self.said not in (None, GOLD):
            return f"FAIL: its row says {self.said}, so it fails under any text"
        return "not re-judged: the answer text is not stored"


def _stored(path: Path) -> Stored:
    text = path.read_text(encoding="utf-8")
    verdict = VERDICT.search(text)
    assert verdict, f"{path.name} holds no requirement 10 line"
    live = LIVE.search(text)
    said = SAID.search(live.group(2)) if live else None
    run = RUN.search(text)
    return Stored(
        path.stem,
        run.group(1) if run else None,
        verdict.group(1),
        said.group("where") if said else None,
        said.group("category") if said else None,
    )


def stored_verdicts() -> list[Stored]:
    return [_stored(path) for path in sorted(CAPTURED.glob("*.txt"))]


def _detail() -> RunDetail:
    """A posted run as the judge reads it; only its status matters here."""
    from datetime import UTC, datetime
    from uuid import uuid4

    now = datetime(2026, 10, 25, 22, 52, tzinfo=UTC)
    return RunDetail.model_validate(
        {
            "run_id": uuid4(),
            "event_id": "revenue-anomaly:2026-01-30:drill-down",
            "session_id": None,
            "demo_name": None,
            "question": "Which category?",
            "metric_family": "revenue",
            "status": RunStatus.POSTED,
            "autonomy_level_applied": None,
            "knowledge_version": "v1",
            "model": "the class model",
            "planted_active": [],
            "tokens_in": 0,
            "tokens_out": 0,
            "cost_usd": 0.0,
            "langsmith_url": None,
            "answer": {},
            "created_at": now,
            "started_at": now,
            "finished_at": now,
            "duplicates_ignored": 0,
            "live_stamp": None,
            "events": [],
            "approvals": [],
            "posts": [],
        }
    )


def test_the_stored_verdicts_are_the_seven_checks_the_pages_record() -> None:
    found = {s.capture: s for s in stored_verdicts()}
    assert set(found) == {
        "starter",
        *(f"{v}-run-{n}" for v in VARIANTS for n in (1, 2)),
    }
    assert found["starter"].verdict == "FAIL" and found["starter"].where is None
    assert found["alternative-one-run-1"] == Stored(
        "alternative-one-run-1", "ca5c5e3c", "FAIL", "its row", "Hiking"
    )
    assert found["alternative-two-run-1"].where == "its text"
    passes = [s for s in found.values() if s.verdict == "PASS"]
    assert len(passes) == 5 and all(s.said is None for s in passes)


def test_a_stored_row_of_another_category_fails_under_the_current_judge_whatever_its_text() -> None:
    """Alternative one's run 1 (ca5c5e3c) is FAIL under the current judge too: its own top row
    named Hiking, and the row decides, whatever the text said."""
    for stored in stored_verdicts():
        if stored.where != "its row" or stored.said in (None, GOLD):
            continue
        for text in TEXTS:
            outcome = check.DrillDown(_detail(), GOLD, True, [], text, True, NAMES, stored.said)
            assert not outcome.passed, (stored.capture, text)


def test_print_the_re_judging_table(capsys: pytest.CaptureFixture[str]) -> None:
    rows = [
        f"| {s.capture} | {s.run or 'none'} | {s.verdict}"
        f"{f' ({s.where})' if s.where else ''} | {s.now()} |"
        for s in stored_verdicts()
    ]
    with capsys.disabled():
        print("\n| Capture | Drill-down run | Stored verdict | The current judge |")
        print("|---|---|---|---|")
        print("\n".join(rows))
    assert len(rows) == 7
