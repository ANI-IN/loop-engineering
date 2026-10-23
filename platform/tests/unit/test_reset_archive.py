"""The reset archive's words, with no database: what the reset report says it archived, and how an
archived experiment reads back (the rows themselves are tested on the tests' own database)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from datapilot.loop3_events import archive

ROW = {
    "experiment_id": "407ff720",
    "knowledge_version": "v3",
    "session_id": "s1",
    "started_at": "2026-10-23T09:00:00+00:00",
    "finished_at": "2026-10-23T09:05:00+00:00",
    "per_example": [
        {"item_id": "d1", "split": "dev", "passed": True, "run_passes": [True]},
        {
            "item_id": "d2",
            "split": "dev",
            "passed": False,
            "run_passes": [False],
            "confirmation": {
                "steps": [
                    "Apparent regression: confirming with 2 more runs of each version",
                    "Not a regression: the candidate failed 2 of 2 more runs, the active version "
                    "passed 1 of 2",
                ]
            },
        },
        {"item_id": "h1", "split": "holdout", "passed": True, "run_passes": [True, False, True]},
    ],
}


def test_the_report_names_each_kind_of_row_it_archived() -> None:
    kept = archive.Archive(uuid.uuid4())
    kept.counts = {
        ("ops.experiments", "deleted"): 2,
        ("ops.promotion_decisions", "deleted"): 1,
        ("ops.knowledge_versions", "retired"): 0,
    }
    assert kept.total == 3
    assert kept.describe() == "2 experiments deleted, 1 promotion decision deleted"
    assert archive.Archive(uuid.uuid4()).describe() == "nothing"


def test_an_archived_experiment_reads_back_with_its_confirmations() -> None:
    brief = archive.summary(ROW)
    assert brief["dev"] == (1, 2) and brief["holdout"] == (1, 1) and brief["confirmations"] == 1
    lines = archive.experiment_lines(
        {
            "row": ROW,
            "summary": brief,
            "reset_id": "r1",
            "reset_at": datetime(2026, 10, 23, 10, tzinfo=UTC),
            "reset_by": "make reset NAME=hill-climbing-loop",
            "reset_session": "s1",
            "decisions": [{"decision_id": 26, "verdict": "promoted", "sentence": "Promoted: v3"}],
        }
    )
    assert lines[0].startswith("experiment 407ff720 of v3, session s1")
    assert "archived by make reset NAME=hill-climbing-loop at 2026-10-23T10:00:00+00:00" in lines[1]
    assert any("d2: fail (0 of 1 runs); Not a regression" in line for line in lines)
    assert any("h1: pass (2 of 3 runs)" in line for line in lines)
    assert lines[-1] == "decision 26: promoted, Promoted: v3"
