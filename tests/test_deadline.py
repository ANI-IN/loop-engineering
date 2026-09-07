"""The deadline: what it stops, what it lets finish, and what the figures then say.

Driven by an injected clock rather than by sleeping. A test that proves a 2-second
deadline by waiting 2 seconds makes the suite slower every time it passes, and the
property under test is the ORDER of the checks, not the passage of real time.
"""

import json

import pytest

from loopeng.agent.loop import TerminationReason
from loopeng.sweep.chart_model import bar_rows, deadline_note
from loopeng.sweep.charts import cost_chart, dial_chart
from loopeng.sweep.deadline import Deadline, run_bounded
from loopeng.sweep.orchestrator import (
    describe_outcome,
    mid_cell_message,
    run_sweep,
)
from loopeng.sweep.runner import DEVELOPMENT, Cell, build_cells, load_cell, summarise_cell
from tests.figures import texts


class Clock:
    """A hand-cranked monotonic clock. `tick` is the only way time passes."""

    def __init__(self):
        self.t = 0.0

    def __call__(self) -> float:
        return self.t

    def tick(self, seconds: float) -> None:
        self.t += seconds


class _Item:
    def __init__(self, i):
        self.item_id = f"i{i:02d}"
        self.pattern_key = "p01"
        self.question = "q"
        self.rules = ()


ITEMS = [_Item(i) for i in range(50)]


# ---- the budget itself -------------------------------------------------------


def test_no_deadline_never_expires():
    """The default everywhere. Nothing acquires a time limit by accident."""
    clock = Clock()
    deadline = Deadline(clock=clock)
    clock.tick(10_000)
    assert deadline.seconds is None
    assert deadline.remaining is None
    assert deadline.expired() is False


def test_a_deadline_expires_when_the_budget_is_gone():
    clock = Clock()
    deadline = Deadline(seconds=10, clock=clock)
    clock.tick(9)
    assert deadline.expired() is False
    clock.tick(1)
    assert deadline.expired() is True, "at exactly the budget, the time is up"


def test_the_projection_is_none_before_anything_has_landed():
    """Zero observations is not a rate. The same rule `Metric` follows for a
    proportion with no denominator: report that it is not yet known, rather than a
    figure nothing supports."""
    clock = Clock()
    deadline = Deadline(seconds=10, clock=clock)
    clock.tick(3)
    assert deadline.projected_finish(0, 50) is None
    assert deadline.will_overrun(0, 50) is False
    assert "estimating" in deadline.status(0, 50)


def test_the_projection_extrapolates_from_what_has_landed():
    clock = Clock()
    deadline = Deadline(seconds=100, clock=clock)
    clock.tick(20)
    # 10 items in 20s is 2s each; 50 items projects to 100s.
    assert deadline.projected_finish(10, 50) == pytest.approx(100)


def test_the_projection_is_withheld_until_the_pipeline_is_full():
    """Found by running it, not by reading it. A live sweep at concurrency 2 printed:

        1/16 items · 2s of 18s · projected finish 32s · WILL OVERRUN
        2/16 items · 2s of 18s · projected finish 17s · on track
        4/16 items · 6s of 18s · projected finish 22s · WILL OVERRUN

    `elapsed / done` divides the wall clock by the items that have FINISHED while the
    other `concurrency - 1` are still running, so the first reading overstates per-item
    cost by roughly the concurrency and then collapses when the wave lands. Since a
    verdict flip is what triggers a status line, the least trustworthy phase produced
    the most output — and an operator watching would have reached for the abort during
    the one window where the number meant nothing.
    """
    clock = Clock()
    deadline = Deadline(seconds=60, clock=clock, warmup=4)
    clock.tick(2)

    for done in range(1, 4):
        assert deadline.projected_finish(done, 16) is None
        assert deadline.will_overrun(done, 16) is False
        assert "estimating" in deadline.status(done, 16)

    assert deadline.projected_finish(4, 16) == pytest.approx(8)


def test_the_orchestrator_sets_the_warmup_from_the_concurrency(tmp_path):
    """The caller knows the concurrency; `Deadline` should not have to be told twice.

    Set on a COPY: a function that mutates an argument to configure itself makes the
    caller's next use of that object depend on whether this ran.
    """
    mine = Deadline(seconds=0)
    run_sweep(ITEMS, tmp_path / "w.duckdb", profile=DEVELOPMENT, cap_usd=99.0,
              directory=tmp_path / "sweep", quiet=True, deadline=mine, concurrency=5)
    assert mine.warmup == 0, "the caller's deadline was mutated"


def test_the_status_line_names_the_decision_not_just_the_clock():
    """A countdown says how long is left. The operator's question is whether to
    intervene, and only the projection answers it."""
    clock = Clock()
    deadline = Deadline(seconds=60, clock=clock)
    clock.tick(30)
    assert "WILL OVERRUN" in deadline.status(10, 50)
    assert deadline.will_overrun(10, 50) is True
    assert "on track" in deadline.status(40, 50)


# ---- the submission gate -----------------------------------------------------


def test_no_item_is_submitted_after_the_deadline():
    clock = Clock()
    deadline = Deadline(seconds=5, clock=clock)
    seen = []

    def work(item):
        seen.append(item)
        clock.tick(1)
        return item

    result = run_bounded(range(100), work, concurrency=1, deadline=deadline)

    assert result.stopped_early is True
    assert result.n == len(seen) == 5, "one item per second against a 5s budget"
    assert result.requested == 100
    assert result.n_not_run == 95


def test_an_item_already_in_flight_is_kept_not_discarded():
    """The difference between stopping and aborting.

    A call in flight has already been paid for. Killing it would throw the money away
    AND leave the cell short by an item nobody could account for — so the work is
    allowed to land and its result is recorded, even though the clock has run out.
    """
    clock = Clock()
    deadline = Deadline(seconds=1, clock=clock)
    landed = []

    def work(item):
        clock.tick(10)  # every item overruns the budget on its own
        return item

    result = run_bounded(range(4), work, concurrency=4, deadline=deadline,
                         on_result=landed.append)

    assert len(landed) == 4, "all four were in flight when the clock ran out"
    assert result.n == 4
    assert result.stopped_early is False, "nothing was left unrun"


def test_a_run_that_finished_everything_is_not_reported_as_stopped_early():
    """The bug this assertion exists for, found by tracing rather than by running.

    `stopped_early` first asked "did the item iterator run dry?". With the last items
    already in flight the iterator is never advanced again, so a deadline expiring
    while they landed reported a stop on a cell that had measured everything — putting
    the deadline disclosure on a chart that did not need one. It asks how many results
    came back instead.
    """
    clock = Clock()
    deadline = Deadline(seconds=1, clock=clock)

    def work(item):
        clock.tick(5)
        return item

    result = run_bounded(range(8), work, concurrency=8, deadline=deadline)

    assert deadline.expired() is True
    assert result.n == result.requested == 8
    assert result.stopped_early is False


def test_without_a_deadline_every_item_runs():
    result = run_bounded(range(30), lambda i: i, concurrency=4)
    assert result.n == 30
    assert result.stopped_early is False
    assert "all 30 items measured" in result.note()


def test_the_note_says_what_was_not_measured_and_does_not_estimate_it():
    clock = Clock()
    deadline = Deadline(seconds=3, clock=clock)

    def work(item):
        clock.tick(1)
        return item

    note = run_bounded(range(20), work, concurrency=1, deadline=deadline).note()
    assert "STOPPED AT THE DEADLINE" in note
    assert "3 of 20 items measured" in note
    assert "Nothing was estimated for the 17" in note


def test_a_raising_work_function_is_not_disguised_as_a_deadline_stop():
    """`stopped_early` keys on a short result count, so a work function that dropped
    items could in principle look like a clock stop. It cannot: a failed future
    re-raises at `.result()` rather than going unrecorded."""
    def work(item):
        raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        run_bounded(range(4), work, concurrency=2, deadline=Deadline(seconds=1000))


# ---- an item is never cut short ----------------------------------------------


def test_the_deadline_is_not_a_termination_reason():
    """Recorded as a test because the design went the other way first.

    `TerminationReason` names why ONE AGENT LOOP stopped on ONE ITEM. The deadline
    stops the RUNNER between items, and an item that never started has no run, no
    attempts and no reason — so a `DEADLINE` member could never be produced. It would
    be exactly the unreachable branch that `test_every_termination_reason_is_reachable`
    exists to catch, in the enum whose own docstring is about policy branches nobody
    counts.

    Checking the clock INSIDE the loop instead — so a long item terminates as
    `deadline` with whatever it has — is worse and not because it is harder. An item
    cut off after attempt 1 of 3 did not run under the condition being measured, and
    scoring it puts an item in the accuracy figure having been given less than the arm
    it is reported under.
    """
    assert "deadline" not in {reason.value for reason in TerminationReason}
    assert not hasattr(TerminationReason, "DEADLINE")


# ---- what a stopped cell says about itself -----------------------------------


def _rows(n: int) -> list[dict]:
    return [{
        "item_id": f"i{i:02d}", "pattern_key": "p01", "outcome": "silent_error",
        "ran_and_returned": True, "correct": False, "termination": "success",
        "rejections": 0, "cost_usd": 0.001, "tokens": {},
    } for i in range(n)]


def test_a_stopped_cell_is_final_not_in_progress():
    """"in progress, n=NN so far" promises the number will move. It is true of a cell
    mid-flight and false of one the clock ended, and the two used to render
    identically — inviting a room to wait for a figure that was already final."""
    running = summarise_cell(Cell("agent", "L0", "loop"), _rows(12),
                             complete=False, seconds=4.0)
    stopped = summarise_cell(Cell("agent", "L0", "loop"), _rows(12), complete=False,
                             seconds=4.0, stopped_early=True, n_requested=50)

    assert "in progress" in running["silent_error_rate"]
    assert "in progress" not in stopped["silent_error_rate"]
    assert "stopped at the deadline" in stopped["silent_error_rate"]
    assert "final at n=12" in stopped["silent_error_rate"]


def test_a_stopped_cell_carries_both_counts():
    cell = summarise_cell(Cell("agent", "L0", "loop"), _rows(12), complete=False,
                          seconds=4.0, stopped_early=True, n_requested=50)
    assert cell["n_items"] == 12
    assert cell["n_requested"] == 50
    assert cell["stopped_early"] is True


def test_a_complete_cell_asks_for_exactly_what_it_ran():
    cell = summarise_cell(Cell("agent", "L0", "loop"), _rows(50), complete=True,
                          seconds=4.0)
    assert cell["n_requested"] == cell["n_items"] == 50
    assert cell["stopped_early"] is False


def test_a_stopped_cell_is_never_resumed_as_a_whole_one(tmp_path):
    """A partial cell sitting in the directory must not be able to satisfy a later
    full run. `complete` stays False, which is what `load_cell` reads."""
    cell = Cell("agent", "L0", "loop")
    body = summarise_cell(cell, _rows(12), complete=False, seconds=4.0,
                          stopped_early=True, n_requested=50)
    (tmp_path / f"{cell.key}.json").write_text(json.dumps(body))
    assert load_cell(cell, tmp_path, expect_items=50) is None
    assert load_cell(cell, tmp_path) is None


# ---- the sweep stops rather than raising -------------------------------------


def test_the_sweep_returns_a_partial_report_instead_of_raising(tmp_path):
    """The cap raises and the deadline returns, on purpose. Running out of time is
    the expected outcome of a fixed session slot, not a mistake — and raising would
    make a designed ending look like a crash AND push the partial result into an
    exception path where it is easy to drop."""
    report = run_sweep(ITEMS, tmp_path / "w.duckdb", profile=DEVELOPMENT,
                       cap_usd=99.0, directory=tmp_path / "sweep", quiet=True,
                       deadline=Deadline(seconds=0))

    assert report["stopped_at_deadline"] is True
    assert report["cells"] == [], "the clock was already out; nothing ran"
    assert report["cells_not_run"] == [c.key for c in build_cells(DEVELOPMENT)]
    assert report["deadline_seconds"] == 0
    assert not list((tmp_path / "sweep").glob("*.json"))


def test_a_sweep_without_a_deadline_reports_no_stop(tmp_path):
    """The opposite failure: a stop flag that fires when nothing stopped it."""
    report = run_sweep([], tmp_path / "w.duckdb", profile=DEVELOPMENT, cap_usd=99.0,
                       directory=tmp_path / "sweep", quiet=True)
    assert report["stopped_at_deadline"] is False
    assert report["cells_not_run"] == []
    assert report["deadline_seconds"] is None


def test_the_operator_is_told_which_cells_did_not_run(tmp_path, capsys):
    run_sweep(ITEMS, tmp_path / "w.duckdb", profile=DEVELOPMENT, cap_usd=99.0,
              directory=tmp_path / "sweep", deadline=Deadline(seconds=0))
    out = capsys.readouterr().out
    assert "DEADLINE REACHED" in out
    assert "cell(s) will not run" in out


def test_a_stop_in_the_final_cell_does_not_report_zero_later_cells():
    """It printed "0 later cell(s) will not run" — a zero rendered as a statement
    about something that did not happen, which is the sentence shape this project
    spends its whole time removing.

    Measured live: the stop landed in the second of two smoke cells, so `not_run` was
    empty and the sentence counted it anyway.
    """
    cut = {"n_items": 5, "n_requested": 8}
    last = mid_cell_message("luna · L0 · loop", cut, [])
    assert "0 later cell(s)" not in last
    assert "It was the last cell." in last

    more = mid_cell_message("luna · L0 · loop", cut, ["agent_L3_loop_r0"])
    assert "1 later cell(s) will not run." in more
    assert "5 of 8 items" in more


def test_the_outcome_counts_a_partial_cell_apart_from_a_complete_one():
    """"measured: 2 of 2 cells" was the first version, and on a run whose second cell
    was cut at 5 of 8 items it was the most misleading line on the screen: 2-of-2 is
    what a COMPLETE sweep says."""
    report = {
        "profile": "smoke", "n_cells": 2, "n_resumed": 0,
        "spend_usd": {"value": 0.0033, "source": "estimated"}, "cap_usd": 0.05,
        "deadline_seconds": 18.0, "elapsed_seconds": 19.0,
        "stopped_at_deadline": True, "cells_not_run": [],
        "cells": [
            {"label": "a · L0 · one-shot", "stopped_early": False,
             "n_items": 8, "n_requested": 8},
            {"label": "a · L0 · loop", "stopped_early": True,
             "n_items": 5, "n_requested": 8},
        ],
    }
    text = describe_outcome(report)
    assert "1 complete, 1 partial (of 2)" in text
    assert "2 of 2 cells" not in text
    assert "never started" not in text, "a category that did not happen is not listed"


def test_the_outcome_description_names_the_partial_cells():
    report = {
        "profile": "development", "n_cells": 12, "n_resumed": 0,
        "spend_usd": {"value": 0.42, "source": "estimated"}, "cap_usd": 12.0,
        "deadline_seconds": 300.0, "elapsed_seconds": 301.4,
        "stopped_at_deadline": True, "cells_not_run": ["agent_L3_loop_r0"],
        "cells": [{"label": "gpt-5.6-luna · L0 · loop", "stopped_early": True,
                   "n_items": 12, "n_requested": 50}],
    }
    text = describe_outcome(report)
    assert "STOPPED AT THE DEADLINE" in text
    assert "12 of 50 items" in text
    assert "agent_L3_loop_r0" in text
    assert "1 never started" in text
    assert "Nothing was estimated" in text


# ---- the reduced n reaches the figure ----------------------------------------


def _cell_dict(key: str, *, n_items: int, n_requested: int, stopped: bool) -> dict:
    return {
        "key": key, "label": key, "role": "agent", "level": "L0", "mode": "loop",
        "replicate": 0, "complete": not stopped, "stopped_early": stopped,
        "seconds": 4.0, "n_items": n_items, "n_requested": n_requested,
        "n_done": n_items, "ran_and_returned": n_items, "correct": 0,
        "unearned_correct": 0, "silent_errors": 1, "bands": {},
        "silent_error_rate": "x", "rate_value": 0.1, "rate_ci_low": 0.0,
        "rate_ci_high": 0.3, "rate_n": n_items,
        "cost_usd": {"value": 0.01, "source": "estimated"}, "tokens": {},
        "rejections": 0, "termination": {}, "patterns_with_interventions": [],
        "items": [],
    }


def test_no_deadline_note_when_nothing_was_cut_short():
    cells = [_cell_dict("agent_L0_loop_r0", n_items=50, n_requested=50, stopped=False)]
    assert deadline_note(cells) is None


def test_the_deadline_note_names_every_short_cell_and_its_two_counts():
    cells = [
        _cell_dict("agent_L0_loop_r0", n_items=12, n_requested=50, stopped=True),
        _cell_dict("agent_L0_one_shot_r0", n_items=50, n_requested=50, stopped=False),
    ]
    note = deadline_note(cells)
    assert "1 of 2 cell(s)" in note
    assert "(12 of 50)" in note
    assert "no bar was scaled" in note


def test_every_row_carries_its_n_once_any_cell_is_short():
    """The rows no longer share a denominator, so the n goes where the reader's eye
    already is. On EVERY row, not only the short ones: "the row without the annotation
    is the full one" is a convention the reader would have to be taught."""
    cells = [
        _cell_dict("agent_L0_loop_r0", n_items=12, n_requested=50, stopped=True),
        _cell_dict("agent_L0_one_shot_r0", n_items=50, n_requested=50, stopped=False),
    ]
    notes = [row["note"] for row in bar_rows(cells, metric="cost")]
    assert any("n=12 of 50" in note for note in notes)
    assert any(note.endswith("n=50") for note in notes)


def test_a_complete_sweep_does_not_annotate_every_cost_row_with_n():
    """The n belongs in the caption when the cells share it. Annotating regardless
    would train a reader to ignore it, which is the state this is trying to leave."""
    cells = [_cell_dict("agent_L0_loop_r0", n_items=50, n_requested=50, stopped=False)]
    assert "n=" not in bar_rows(cells, metric="cost")[0]["note"]


@pytest.mark.parametrize("chart", [dial_chart, cost_chart])
def test_the_deadline_disclosure_reaches_the_drawn_figure(chart):
    """Not just the cell file and not just the caption — the image."""
    cells = [_cell_dict("agent_L0_loop_r0", n_items=12, n_requested=50, stopped=True)]
    drawn = texts(chart(cells))
    assert "STOPPED AT A DEADLINE" in drawn
    assert "12 of 50" in drawn
