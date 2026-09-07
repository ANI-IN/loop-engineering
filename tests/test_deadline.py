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
from loopeng.sweep.runner import DEV, Cell, build_cells, load_cell, summarise_cell
from tests.figures import texts


@pytest.fixture(scope="module")
def warehouse(tmp_path_factory):
    from loopeng.warehouse.connect import ensure_warehouse

    return ensure_warehouse(tmp_path_factory.mktemp("wh") / "w.duckdb", seed=20260729)


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
    run_sweep(ITEMS, tmp_path / "w.duckdb", profile=DEV, cap_usd=99.0,
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
    report = run_sweep(ITEMS, tmp_path / "w.duckdb", profile=DEV,
                       cap_usd=99.0, directory=tmp_path / "sweep", quiet=True,
                       deadline=Deadline(seconds=0))

    assert report["stopped_at_deadline"] is True
    assert report["cells"] == [], "the clock was already out; nothing ran"
    assert report["cells_not_run"] == [c.key for c in build_cells(DEV)]
    assert report["deadline_seconds"] == 0
    assert not list((tmp_path / "sweep").glob("*.json"))


def test_a_sweep_without_a_deadline_reports_no_stop(tmp_path):
    """The opposite failure: a stop flag that fires when nothing stopped it."""
    report = run_sweep([], tmp_path / "w.duckdb", profile=DEV, cap_usd=99.0,
                       directory=tmp_path / "sweep", quiet=True)
    assert report["stopped_at_deadline"] is False
    assert report["cells_not_run"] == []
    assert report["deadline_seconds"] is None


def test_the_operator_is_told_which_cells_did_not_run(tmp_path, capsys):
    run_sweep(ITEMS, tmp_path / "w.duckdb", profile=DEV, cap_usd=99.0,
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


# ---- lookups that must fail loudly rather than plausibly ---------------------


def test_a_run_with_no_recorded_termination_is_not_scored_as_the_best_outcome():
    """`confidence_of` read `run.get("termination", "")`. Nothing matches `""`, so a
    row with no recorded termination fell through every branch to the last line —
    `clean_first_try`, the HIGHEST confidence band, described as "accepted on the first
    attempt with no revisions".

    A row too malformed to say how its loop ended was scored as the best possible
    outcome, and that score feeds the abstention curve, which is the figure about
    knowing when not to answer.
    """
    from loopeng.triage.abstain import confidence_of

    good = {"ran_and_returned": True, "termination": "success", "rejections": 0}
    best, _ = confidence_of(good)

    with pytest.raises(KeyError, match="termination"):
        confidence_of({"ran_and_returned": True, "rejections": 0})
    with pytest.raises(KeyError, match="rejections"):
        confidence_of({"ran_and_returned": True, "termination": "success"})
    with pytest.raises(KeyError, match="ran_and_returned"):
        confidence_of({"termination": "success", "rejections": 0})

    # The old default landed here, which is what made it dangerous rather than merely
    # wrong: the fallthrough was the top of the scale, not the bottom.
    assert best == max(
        confidence_of(dict(good, termination=t, rejections=0))[0]
        for t in ("success", "budget", "no_progress", "max_attempts")
    )


def test_the_n_on_an_outcome_shift_bar_is_never_reconstructed():
    """It read `arm.get("n_items", sum(bands.values()))`. Those are different numbers —
    the bands count classified outcomes — so an arm without `n_items` got an n computed
    from a different denominator and printed beside the bar as the measured one."""
    from loopeng.sweep.chart_model import outcome_shift_rows

    arm = {"condition": "A", "n_items": 60,
           "bands": {"correct": 50, "silent_error": 3}}
    assert outcome_shift_rows([arm])[0]["n"] == 60

    with pytest.raises(KeyError, match="n_items"):
        outcome_shift_rows([{"condition": "A", "bands": {"correct": 50}}])


def test_a_chart_row_cannot_default_its_own_n_to_zero():
    """`cell.get("rate_n", 0)` rendered a bar whose n silently defaulted to zero — and
    n=0 is a value this project prints for real, being what an unmeasured cell says."""
    from loopeng.sweep.chart_model import bar_rows

    cell = _cell_dict("agent_L0_loop_r0", n_items=50, n_requested=50, stopped=False)
    del cell["rate_n"]
    with pytest.raises(KeyError, match="rate_n"):
        bar_rows([cell], metric="rate")


# ---- the profile's clock reaches a run that did not ask for one ---------------


def test_a_session_run_with_no_deadline_flag_inherits_the_profile_clock(tmp_path):
    """`session` is the profile this actually protects, so it is the one asserted.

    The wall clock is on the profile precisely so it applies when nobody types
    anything — a deadline that has to be typed is one that will be forgotten at the
    venue, which is the only place it matters. This is the property that says the
    plumbing between the two delivers it.
    """
    from loopeng.sweep.runner import SESSION

    report = run_sweep([], tmp_path / "w.duckdb", profile=SESSION, cap_usd=99.0,
                       directory=tmp_path / "sweep", quiet=True)

    assert SESSION.deadline_seconds is not None, "the session profile must declare one"
    assert report["deadline_seconds"] == SESSION.deadline_seconds


def test_every_profile_that_declares_a_clock_delivers_it(tmp_path):
    """Derived across the set, so a new profile cannot declare a budget that never
    reaches a run — and cannot inherit one it did not declare."""
    from loopeng.sweep.runner import PROFILES

    for name, profile in PROFILES.items():
        report = run_sweep([], tmp_path / "w.duckdb", profile=profile, cap_usd=99.0,
                           directory=tmp_path / name, quiet=True)
        assert report["deadline_seconds"] == profile.deadline_seconds, name


def test_the_flag_overrides_the_profile_and_nothing_else_does(tmp_path):
    from loopeng.sweep.runner import SESSION

    report = run_sweep([], tmp_path / "w.duckdb", profile=SESSION, cap_usd=99.0,
                       directory=tmp_path / "sweep", quiet=True, deadline_seconds=30)
    assert report["deadline_seconds"] == 30


def test_the_entry_point_cannot_express_no_clock_by_accident():
    """The footgun this signature exists to remove.

    `deadline=None` and `Deadline(seconds=None)` are different answers one keystroke
    apart: the first means "use the profile's", the second means "no clock at all". An
    entry point building `Deadline(seconds=args.deadline)` unconditionally would
    discard the session's wall-clock protection on every run without the flag — no
    error, no warning, the guard simply absent.

    So the entry point passes a NUMBER and never constructs a clock. Checked by reading
    it, because the defect is in what the file is able to say, not in what it computes.
    """
    from pathlib import Path

    entry = (Path(__file__).resolve().parent.parent
             / "demos" / "04_hill_climbing_loop" / "sweep.py").read_text(encoding="utf-8")
    assert "deadline_seconds=args.deadline" in entry
    assert "Deadline(" not in entry, (
        "the entry point constructs a clock again; it must pass the number and let "
        "run_sweep resolve the profile's"
    )


def test_two_clocks_is_refused_rather_than_silently_ranked(tmp_path):
    """Which one wins is a question, and the answer should not be decided here."""
    from loopeng.sweep.runner import SESSION

    with pytest.raises(ValueError, match="not both"):
        run_sweep([], tmp_path / "w.duckdb", profile=SESSION, quiet=True,
                  directory=tmp_path / "sweep",
                  deadline_seconds=30, deadline=Deadline(seconds=60))


# ---- item 6: the row log, and Ctrl-C as a stop rather than a crash ------------


def test_every_cell_key_round_trips(tmp_path):
    """`Cell.from_key` is the inverse of `.key`, and `mode` contains an underscore —
    `agent_L0_one_shot_r0` splits into five pieces, not four, so a naive
    `rsplit("_", 3)` reads the role as "agent_L0" without noticing. Run over every key
    every profile produces, so the two halves cannot drift."""
    from loopeng.sweep.runner import PROFILES, Cell, build_cells

    for name, profile in PROFILES.items():
        for cell in build_cells(profile):
            assert Cell.from_key(cell.key) == cell, f"{name}: {cell.key}"


@pytest.mark.parametrize("bad", ["", "agent", "agent_L0", "agent_L0_loop",
                                 "agent_L0_loop_0", "agent_L0_loop_rX"])
def test_a_non_key_is_refused_rather_than_guessed(bad):
    from loopeng.sweep.runner import Cell

    with pytest.raises(ValueError, match="not a cell key"):
        Cell.from_key(bad)


def test_a_partial_final_line_is_dropped_and_COUNTED(tmp_path):
    """An interrupt can cut the last append mid-write. That row is lost either way;
    what must not happen is losing it silently — "59 items" and "59 items plus one we
    could not read" are different facts."""
    from loopeng.sweep.runner import append_row, read_rows

    log = tmp_path / "agent_L0_loop_r0.jsonl"
    append_row(log, {"item_id": "i1"})
    append_row(log, {"item_id": "i2"})
    with log.open("a", encoding="utf-8") as handle:
        handle.write('{"item_id": "i3", "cos')  # cut mid-write

    rows, dropped = read_rows(log)
    assert [r["item_id"] for r in rows] == ["i1", "i2"]
    assert dropped == 1


def test_a_malformed_line_in_the_middle_is_corruption_and_raises(tmp_path):
    """Only the LAST line may be partial — that is what an interrupted append looks
    like. Anything else is a different fault and must not be quietly skipped."""
    import json

    from loopeng.sweep.runner import read_rows

    log = tmp_path / "agent_L0_loop_r0.jsonl"
    log.write_text('{"item_id": "i1"}\nnot json at all\n{"item_id": "i3"}\n')
    with pytest.raises(json.JSONDecodeError):
        read_rows(log)


def test_an_atomic_write_never_leaves_a_readable_file_truncated(tmp_path):
    """`write_text` truncates and then writes, so between those two steps the only
    record on disk is an empty file. This writes beside the target and renames."""
    import json

    from loopeng.sweep.runner import write_json_atomic

    path = tmp_path / "cell.json"
    write_json_atomic(path, {"n": 1})
    write_json_atomic(path, {"n": 2})
    assert json.loads(path.read_text())["n"] == 2
    assert not list(tmp_path.glob(".*partial")), "the temporary file was left behind"


def test_a_rerun_of_a_cell_starts_a_fresh_log(tmp_path, warehouse):
    """Appending to a previous attempt's rows would double-count every item it managed
    before it stopped — the one way an append-only file can lie."""
    from loopeng.sweep.runner import Cell, append_row, read_rows, rows_path, run_cell

    cell = Cell("agent", "L0", "loop")
    log = rows_path(cell, tmp_path)
    log.parent.mkdir(parents=True, exist_ok=True)
    append_row(log, {"item_id": "from-a-previous-attempt"})

    run_cell(cell, [], warehouse, directory=tmp_path)
    rows, _ = read_rows(log)
    assert rows == []


def _interrupting_wait(monkeypatch, times: int):
    """Make `wait` raise KeyboardInterrupt its first `times` calls, then behave.

    Patching `wait` rather than raising inside a worker, because that is where a real
    Ctrl-C lands: the signal is delivered to the MAIN thread, which is blocked in
    `wait`. A first draft of these tests raised from the work function instead, which
    surfaces at `future.result()` — a different code path that happens to be caught by
    the same `except`, and which cannot reach the second-interrupt branch at all
    because a worker only raises once. It passed, and it was testing something else.
    """
    import loopeng.sweep.deadline as module

    real = module.wait
    calls = {"n": 0}

    def fake(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] <= times:
            raise KeyboardInterrupt
        return real(*args, **kwargs)

    monkeypatch.setattr(module, "wait", fake)
    return calls


def test_ctrl_c_keeps_what_was_in_flight_rather_than_paying_and_discarding(monkeypatch):
    """The old behaviour was "wait for the work, then throw it away".

    A KeyboardInterrupt escaping through the executor's context manager waits for the
    in-flight calls anyway — `shutdown(wait=True)` — and then discards their results.
    Those calls are already paid for. So the first Ctrl-C is handled exactly like the
    clock running out: stop submitting, let what is in flight land, record all of it.
    """
    _interrupting_wait(monkeypatch, times=1)
    landed = []

    result = run_bounded(range(20), lambda i: i, concurrency=4,
                         deadline=Deadline(clock=Clock()), on_result=landed.append)

    assert result.interrupted is True
    # The four that were in flight when the interrupt arrived, all recorded.
    assert result.n == len(landed) == 4
    assert result.n_not_run == 16
    assert "INTERRUPTED" in result.note()
    assert "were not estimated" in result.note()


def test_a_second_ctrl_c_propagates(monkeypatch):
    """Someone pressing it twice means now. A drain that cannot itself be interrupted
    is a hang with a good excuse."""
    _interrupting_wait(monkeypatch, times=2)

    with pytest.raises(KeyboardInterrupt):
        run_bounded(range(20), lambda i: i, concurrency=2,
                    deadline=Deadline(clock=Clock()))


def test_an_interrupted_cell_is_final_and_says_which_kind_of_final():
    """`interrupted` and `stopped_early` are both "final at a smaller n" and are
    different facts: one is the design working, the other is a person deciding."""
    stopped = summarise_cell(Cell("agent", "L0", "loop"), _rows(12), complete=False,
                             seconds=4.0, stopped_early=True, n_requested=50)
    cut = summarise_cell(Cell("agent", "L0", "loop"), _rows(12), complete=False,
                         seconds=4.0, interrupted=True, n_requested=50)

    assert "stopped at the deadline" in stopped["silent_error_rate"]
    assert "interrupted, final at n=12" in cut["silent_error_rate"]
    assert "in progress" not in cut["silent_error_rate"]
    assert cut["interrupted"] is True and cut["stopped_early"] is False


def test_a_lost_summary_is_rebuilt_from_the_log_and_stamped_as_such(tmp_path):
    """Skipping an unreadable cell would leave a chart short one cell with nothing on
    it saying which — the failure this directory exists to prevent."""
    from loopeng.sweep.orchestrator import load_all
    from loopeng.sweep.runner import Cell, append_row, cell_path, rows_path

    cell = Cell("agent", "L0", "one_shot")
    tmp_path.mkdir(parents=True, exist_ok=True)
    for row in _rows(3):
        append_row(rows_path(cell, tmp_path), row)
    cell_path(cell, tmp_path).write_text('{"key": "agent_L0_one')  # truncated

    loaded = load_all(tmp_path)
    assert len(loaded) == 1
    assert loaded[0]["recovered_from_log"] == {"rows": 3, "dropped_partial_lines": 0}
    assert loaded[0]["n_items"] == 3
    assert loaded[0]["complete"] is False


def test_an_unreadable_summary_with_no_log_raises_rather_than_vanishing(tmp_path):
    """Corruption, not an interrupted write. A chart drawn over an unreadable
    directory is worse than a traceback naming the file."""
    import json

    from loopeng.sweep.orchestrator import load_all

    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "agent_L0_loop_r0.json").write_text('{"key": "agent_L0_lo')
    with pytest.raises(json.JSONDecodeError):
        load_all(tmp_path)


def test_an_interrupted_cell_still_counts_toward_the_run_spend(tmp_path, monkeypatch):
    """Found by a real interrupt, not by reading.

    `run_cell` used to write the summary and then re-raise. That looked careful — the
    record was safe on disk — but the report never reached `run_sweep`, so the cell's
    cost was never added to the run total. A live Ctrl-C nine seconds into a sweep
    printed `spend: est. $0.0000 of $0.05` over a cell that had just cost $0.0019.
    Money spent, reported as zero, by the project whose whole argument is that a zero
    on a report reads as a measurement.
    """
    import loopeng.sweep.orchestrator as orchestrator
    from loopeng.sweep.runner import SMOKE, build_cells

    charged = {"n": 0}

    def fake_run_cell(cell, items, warehouse, **kwargs):
        charged["n"] += 1
        return summarise_cell(cell, _rows(3), complete=False, seconds=1.0,
                              interrupted=True, n_requested=20)

    monkeypatch.setattr(orchestrator, "run_cell", fake_run_cell)
    report = run_sweep(ITEMS[:5], tmp_path / "w.duckdb", profile=SMOKE, cap_usd=99.0,
                       directory=tmp_path / "sweep", quiet=True, item_limit=5)

    assert report["interrupted"] is True
    assert charged["n"] == 1, "the sweep stopped at the interrupted cell"
    assert report["spend_usd"]["value"] > 0, "the interrupted cell's spend was dropped"
    assert len(report["cells"]) == 1, "the interrupted cell is part of the run"
    assert report["cells_not_run"] == [c.key for c in build_cells(SMOKE)[1:]]


def test_the_resume_advice_is_not_given_when_there_is_nothing_to_resume():
    """"Re-run with --resume" said to an operator whose interrupt landed in the first
    cell is advice that does nothing, and advice that does nothing is how a flag gets
    a reputation."""
    base = {
        "profile": "smoke", "n_cells": 2, "n_resumed": 0,
        "spend_usd": {"value": 0.0019, "source": "estimated"}, "cap_usd": 0.05,
        "deadline_seconds": 300.0, "elapsed_seconds": 10.0,
        "stopped_at_deadline": False, "interrupted": True,
        "cells_not_run": ["agent_L0_loop_r0"],
    }
    cut = {"label": "luna · L0 · one-shot", "complete": False, "interrupted": True,
           "n_items": 9, "n_requested": 20}
    done = {"label": "luna · L0 · one-shot", "complete": True, "interrupted": False,
            "n_items": 20, "n_requested": 20}

    nothing_done = describe_outcome({**base, "cells": [cut]})
    assert "nothing to resume from" in nothing_done
    assert "9 of 20 items" in nothing_done

    some_done = describe_outcome({**base, "cells": [done, cut]})
    assert "1 cell(s) completed; --resume continues from those." in some_done
    assert "nothing to resume" not in some_done
