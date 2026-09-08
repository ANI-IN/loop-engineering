"""The sweep's three load-bearing properties, tested offline."""

import json
from pathlib import Path

import pytest

from loopeng.pricing import PRICES_TAKEN_ON
from loopeng.sweep.orchestrator import detectable_effect, load_all, pre_registration, run_sweep
from loopeng.sweep.runner import (
    DEV,
    Cell,
    SweepAborted,
    build_cells,
    load_cell,
    project_remaining,
    summarise_cell,
)


class _Item:
    def __init__(self, i):
        self.item_id = f"i{i:02d}"
        self.pattern_key = "p01"
        self.question = "q"
        self.rules = ()


ITEMS = [_Item(i) for i in range(50)]


# ---- cells ------------------------------------------------------------------


def test_eight_cells_plus_replicates_on_both_l0_loop_cells():
    cells = build_cells(DEV)
    assert len(cells) == 12
    l0_loop = [c for c in cells if c.level == "L0" and c.mode == "loop"]
    assert len(l0_loop) == 6
    assert {c.role for c in l0_loop} == {"agent", "reference"}


def test_replicates_are_on_both_models_not_one():
    """They measure two different determinism floors — Haiku pinned, Sonnet not — and
    neither model's floor may be asserted for the other."""
    cells = build_cells(DEV)
    per_role = {r: len([c for c in cells if c.role == r and c.level == "L0"
                        and c.mode == "loop"]) for r in ("agent", "reference")}
    assert per_role == {"agent": 3, "reference": 3}


def test_cell_keys_are_unique():
    cells = build_cells(DEV)
    assert len({c.key for c in cells}) == len(cells)


# ---- the abort is on PROJECTED spend ----------------------------------------


def test_abort_triggers_on_projection_not_actuals(tmp_path):
    """The whole point. A cap checked against money already spent only discovers the
    breach afterwards; this refuses to start a cell whose projected total breaches."""
    with pytest.raises(SweepAborted) as exc:
        run_sweep(ITEMS, tmp_path / "w.duckdb", profile=DEV, cap_usd=0.01,
                  directory=tmp_path / "sweep", quiet=True)
    message = str(exc.value)
    assert "aborting BEFORE" in message
    assert "projected total" in message
    # Nothing ran: no cell files were written.
    assert not list((tmp_path / "sweep").glob("*.json"))


def test_abort_names_the_last_completed_cell(tmp_path):
    with pytest.raises(SweepAborted) as exc:
        run_sweep(ITEMS, tmp_path / "w.duckdb", profile=DEV, cap_usd=0.01,
                  directory=tmp_path / "sweep", quiet=True)
    assert "Last completed cell" in str(exc.value)


def test_a_generous_cap_does_not_abort_before_the_first_cell(tmp_path):
    """Guards the opposite failure: an abort that fires when it should not.

    Read off the profile rather than typed, because the cap moved when the model
    policy did — the reference role is a frontier model now — and a literal here
    would have to be edited in lockstep with a number it is supposed to be checking.
    """
    cells = build_cells(DEV)
    assert project_remaining(cells, 50) < DEV.cap_usd


def test_projection_covers_every_remaining_cell():
    cells = build_cells(DEV)
    assert project_remaining(cells, 50) > project_remaining(cells[1:], 50)


# ---- resume from results/, not LangSmith ------------------------------------


def test_a_complete_cell_is_resumed_from_disk(tmp_path):
    cell = build_cells(DEV)[0]
    directory = tmp_path / "sweep"
    directory.mkdir()
    report = summarise_cell(cell, [], complete=True, seconds=1.0)
    (directory / f"{cell.key}.json").write_text(json.dumps(report))
    assert load_cell(cell, directory) is not None


def test_an_incomplete_cell_is_not_resumed(tmp_path):
    """A partial cell must be re-run, not counted. Resuming a half-finished cell would
    report a rate over whatever happened to have landed."""
    cell = build_cells(DEV)[0]
    directory = tmp_path / "sweep"
    directory.mkdir()
    partial = summarise_cell(cell, [], complete=False, seconds=1.0)
    (directory / f"{cell.key}.json").write_text(json.dumps(partial))
    assert load_cell(cell, directory) is None


# ---- progressive rendering: never blank, never zero, never a guess ----------


def test_a_cell_with_nothing_landed_renders_not_yet_measured():
    report = summarise_cell(Cell("agent", "L0", "loop"), [], complete=False, seconds=0.0)
    assert report["silent_error_rate"] == "not yet measured"
    assert report["rate_value"] is None


def test_a_cell_in_progress_shows_its_n_so_far_and_an_interval():
    rows = [
        {"item_id": "a", "pattern_key": "p", "outcome": "correct", "ran_and_returned": True,
         "correct": True, "termination": "success", "n_attempts": 1, "rejections": 0,
         "cost_usd": 0.001, "tokens": {"n_calls": 1, "input_tokens": 1,
                                       "output_tokens": 1, "total_tokens": 2}},
    ]
    report = summarise_cell(Cell("agent", "L0", "loop"), rows, complete=False, seconds=1.0)
    assert "in progress" in report["silent_error_rate"]
    assert "n=1 so far" in report["silent_error_rate"]
    assert report["rate_n"] == 1


def test_a_complete_cell_renders_a_plain_metric():
    rows = [
        {"item_id": "a", "pattern_key": "p", "outcome": "silent_error",
         "ran_and_returned": True, "correct": False, "termination": "success",
         "n_attempts": 1, "rejections": 0, "cost_usd": 0.001,
         "tokens": {"n_calls": 1, "input_tokens": 1, "output_tokens": 1, "total_tokens": 2}},
    ]
    report = summarise_cell(Cell("agent", "L0", "loop"), rows, complete=True, seconds=1.0)
    assert "in progress" not in report["silent_error_rate"]
    # Carries its n, in whichever form the value calls for. One silent error out of
    # one is a boundary observation and renders as "1 of 1 — at least ...".
    assert "1 of 1" in report["silent_error_rate"]


def test_a_cell_never_reports_a_bare_zero():
    report = summarise_cell(Cell("agent", "L0", "loop"), [], complete=False, seconds=0.0)
    assert report["silent_error_rate"] != "0.0%"
    assert report["rate_value"] is not None or report["silent_error_rate"] == "not yet measured"


# ---- the pre-registration ---------------------------------------------------


def test_the_pre_registration_computes_the_detectable_effect():
    """Computed, not stated."""
    text = pre_registration(50)
    assert f"{detectable_effect(50) * 100:.0f} percentage points" in text


def test_the_detectable_effect_shrinks_as_n_grows():
    assert detectable_effect(200) < detectable_effect(50)


def test_load_all_returns_nothing_when_no_cells_exist(tmp_path):
    assert load_all(tmp_path / "absent") == []


# ---- charts: four, and TIER is still not one of them -------------------------


def test_the_shipped_charts_are_pinned_and_tier_is_not_among_them():
    """TIER moved to Phase 4. Shipping it here would plot a finding that measurably
    did not reproduce.

    DELTA and ABSTENTION are gaps closed rather than new figures: DIAL and COST are
    per-cell absolute values, so nothing showed a difference at all; and ABSTENTION
    existed only in a renderer that read frozen data.

    OUTCOME SHIFT is the headline visual and the one the session must not depend on
    anything else for. It is pinned here so that adding a chart stays a decision
    somebody makes rather than something that accumulates.
    """
    from loopeng.sweep import charts

    builders = [n for n in dir(charts) if n.endswith("_chart")]
    assert sorted(builders) == [
        "abstention_chart", "cost_chart", "cost_per_correct_chart", "delta_chart",
        "dial_chart", "outcome_shift_chart", "trap_matrix_chart",
    ]
    assert "tier_chart" not in builders


def test_the_dial_caption_names_the_models_it_is_actually_describing():
    """This test used to pin the caption's WORDING — "NOT COMPARABLE ACROSS MODELS",
    "temperature=0" — and it passed for the whole time the caption was false.

    The sentence claimed one scoring model was pinned to temperature=0 and the other
    could not be. Neither statement had been true since the model policy changed:
    neither scoring model accepts a pinned temperature, so the asymmetry the caption
    warned a room about did not exist, and the caption contradicted the
    pre-registration printed by the same run. A test that restates a string cannot
    notice that the string stopped describing anything.

    So it asks the registry instead. Both sides are derived, which is what makes it
    keep holding when the registry moves rather than becoming the next stale literal.
    """
    from loopeng.registry import SCORING_ROLES, spec_for
    from loopeng.sweep.charts import DIAL_CAPTION

    for role in SCORING_ROLES:
        assert spec_for(role).model_id in DIAL_CAPTION, (
            f"the caption describes the bars without naming the {role} model"
        )

    pins_temperature = any("temperature" in spec_for(role).request_kwargs
                           for role in SCORING_ROLES)
    # The claim has to match the configuration, in whichever direction it currently
    # points — so this keeps testing something if a future registry pins one again.
    if pins_temperature:
        assert "NOT COMPARABLE ACROSS MODELS" in DIAL_CAPTION
    else:
        assert "neither scoring model" in DIAL_CAPTION
        assert "SAME class" in DIAL_CAPTION

    assert "clusters" in DIAL_CAPTION


def test_the_dial_caption_cites_the_file_its_sampling_claim_rests_on():
    """A number typed next to its own citation is the failure the caption is warning
    the room about, so the caption cites the measurement by path and quotes none of it.
    The path has to resolve, or it is evidence nobody can check — the same defect as
    the pre-registration citing a noise-floor file `.gitignore` was dropping."""
    from pathlib import Path

    from loopeng.sweep.chart_model import NOISE_FLOOR_CITATION
    from loopeng.sweep.charts import DIAL_CAPTION

    assert NOISE_FLOOR_CITATION in DIAL_CAPTION
    root = Path(__file__).resolve().parent.parent
    assert (root / NOISE_FLOOR_CITATION).is_file(), (
        f"{NOISE_FLOOR_CITATION} is cited on the chart and is not on disk"
    )


def test_the_cost_caption_keeps_the_estimated_label():
    from loopeng.sweep.charts import COST_CAPTION

    assert "estimate" in COST_CAPTION.lower()
    assert "billed" in COST_CAPTION


def test_charts_render_from_no_data_without_inventing_a_zero():
    from loopeng.sweep.charts import cost_chart, dial_chart
    from tests.figures import texts

    empty = summarise_cell(Cell("agent", "L0", "loop"), [], complete=False, seconds=0.0)
    for figure in (dial_chart([empty]), cost_chart([empty])):
        assert "not yet measured" in texts(figure)


def test_charts_write_from_a_cold_start(tmp_path):
    """Gate 3: every chart builds live from nothing on disk.

    DELTA and ABSTENTION are written even with no input. A chart that silently does not
    exist is indistinguishable from a chart whose finding is absent.
    """
    from loopeng.sweep.charts import write_charts

    written = write_charts([summarise_cell(Cell("agent", "L0", "loop"), [],
                                           complete=False, seconds=0.0)], tmp_path / "c")
    assert [p.name for p in written] == [
        "outcome_shift.png", "trap_matrix.png", "cost_per_correct.png",
        "dial.png", "cost.png", "delta.png", "abstention.png",
    ]
    # PNG's magic bytes. A file that exists and is not an image is the same failure as
    # a chart that silently did not render.
    assert all(p.read_bytes().startswith(b"\x89PNG\r\n") for p in written)


def test_an_empty_chart_says_not_yet_measured_rather_than_drawing_nothing(tmp_path):
    """The claim README §8 makes about a fresh clone, at the figure rather than at the
    terminal. `write_charts` is handed nothing at all — no cells, no comparisons, no
    curve — which is what a clone with no results/sweep produces."""
    from loopeng.sweep.charts import abstention_chart, delta_chart, dial_chart
    from tests.figures import texts

    for figure in (dial_chart([]), delta_chart([]), abstention_chart([])):
        assert "not yet measured" in texts(figure)


# ---- profiles: delivery cannot inherit development settings ------------------


def test_session_is_four_agent_cells():
    from loopeng.sweep.runner import SESSION

    cells = build_cells(SESSION)
    assert len(cells) == 4
    assert {c.role for c in cells} == {"agent"}
    assert all(c.replicate == 0 for c in cells)


def test_session_projects_under_its_cap():
    """Cost is a hard constraint in front of a room, not a target."""
    from loopeng.sweep.runner import SESSION

    assert project_remaining(build_cells(SESSION), 50) < SESSION.cap_usd


def test_session_is_far_cheaper_than_dev():
    from loopeng.sweep.runner import DEV, SESSION

    session = project_remaining(build_cells(SESSION), 50)
    dev = project_remaining(build_cells(DEV), 50)
    assert dev > session * 5


def test_session_runs_no_ablation():
    """The ablation is a dev finding and never appears in the session."""
    from loopeng.sweep.runner import DEV, SESSION

    assert SESSION.runs_ablation is False
    assert DEV.runs_ablation is True


# ---- the smoke profile: the pipeline, on a cloner's key, for pennies ---------


def test_smoke_is_two_l0_cells():
    from loopeng.sweep.runner import SMOKE

    cells = build_cells(SMOKE)
    assert len(cells) == 2
    assert {c.key for c in cells} == {"agent_L0_one_shot_r0", "agent_L0_loop_r0"}
    assert {c.role for c in cells} == {"agent"}


def test_smoke_projects_to_a_few_cents():
    """The cheapest live path there is. Before it existed, the smallest was the
    session profile over every held-out item."""
    from loopeng.sweep.runner import SESSION, SMOKE

    smoke = project_remaining(build_cells(SMOKE), SMOKE.item_limit)
    session = project_remaining(build_cells(SESSION), 50)

    assert smoke < SMOKE.cap_usd
    assert smoke * 10 < session, f"smoke projects est. ${smoke:.4f}, not cheap enough"


def test_smoke_carries_its_own_item_limit():
    """A cost ceiling that depends on someone typing --limit is not a ceiling."""
    from loopeng.sweep.runner import SMOKE, resolve_item_limit

    assert SMOKE.item_limit is not None
    assert resolve_item_limit(SMOKE, None) == SMOKE.item_limit


# ---- --limit was documented "development only" and applied everywhere ---------


def test_limit_is_refused_where_the_docs_said_it_was():
    """The flag's help text said "(development only)" and it was applied to any
    profile unconditionally — a declared restriction nothing enforced, in the tool
    that runs the sweep."""
    from loopeng.sweep.runner import SESSION, LimitNotAllowed, resolve_item_limit

    with pytest.raises(LimitNotAllowed) as exc:
        resolve_item_limit(SESSION, 5)
    assert "session" in str(exc.value)


def test_limit_is_accepted_where_it_is_declared():
    from loopeng.sweep.runner import DEV, SMOKE, resolve_item_limit

    assert resolve_item_limit(DEV, 5) == 5
    assert resolve_item_limit(SMOKE, 3) == 3


def test_every_profile_declares_whether_it_takes_a_limit():
    """So a new profile has to make the decision rather than inherit a default that
    happens to be permissive."""
    from loopeng.sweep.runner import PROFILES

    permissive = {p.name for p in PROFILES.values() if p.allows_limit}
    assert permissive == {"smoke", "dev"}


def test_the_limit_spreads_across_clusters_rather_than_taking_a_prefix(tmp_path):
    """items[:8] is two of the ten clusters. Round-robin maximises clusters at small
    n, which matters because clustering is the caveat everything here carries."""
    from loopeng.gold.build import build_gold
    from loopeng.warehouse.connect import ensure_warehouse

    warehouse = ensure_warehouse(tmp_path / "w.duckdb", seed=20260729)
    subset = build_gold(warehouse, limit=8)

    assert len(subset) == 8
    assert len({item.pattern_key for item in subset}) == 8


def test_the_profile_flag_is_required():
    """A delivery run must not inherit development settings by omission — that is a
    tenfold cost difference decided by a flag nobody typed.

    This ran with `cwd=tmp_path.parent`, where `demos/04_hill_climbing_loop/sweep.py`
    does not exist. Python exited 2 with "can't open file", the assertion on a
    non-zero return code passed, and argparse was never reached — so the test named
    after the required flag proved only that a missing file fails to run. It would
    have passed just as well with `--profile` deleted from the parser.

    Now run from the repository root, and the refusal is asserted on its content.
    """
    import subprocess
    import sys

    repo_root = Path(__file__).resolve().parent.parent
    result = subprocess.run(
        [sys.executable, "demos/04_hill_climbing_loop/sweep.py"],
        capture_output=True, text=True, cwd=repo_root, timeout=120,
    )
    assert result.returncode == 2, result.stdout + result.stderr
    combined = result.stdout + result.stderr
    assert "can't open file" not in combined, "still running from the wrong directory"
    assert "--profile" in combined, combined
    assert "required" in combined.lower(), combined


# ---- reference measurements are visibly not live ----------------------------


@pytest.fixture
def a_live_frontier_cell(tmp_path):
    """A sweep directory holding one complete cell, exactly as a live run writes it.

    Both tests below used to call `build_reference()` on the DEFAULT sweep directory,
    which a fresh clone does not have. `build_reference` returned no cells, both loops
    ran zero times, and both tests passed having asserted nothing — on the machine that
    matters most, the one a cloner is using. They were green on this machine only
    because an untracked results/sweep/ happened to be sitting there.

    So the input is built here. It also makes the tests stronger than they could ever
    have been: this fixture asserts the cell arrives carrying the exact sentence
    `_freeze` exists to remove, so the rewrite is now something the test watches happen
    rather than something it hopes already happened.
    """
    directory = tmp_path / "sweep"
    directory.mkdir()
    cell = Cell("reference", "L0", "loop")
    report = summarise_cell(cell, [
        {"item_id": "a", "pattern_key": "p", "outcome": "silent_error",
         "ran_and_returned": True, "correct": False, "termination": "success",
         "n_attempts": 1, "rejections": 0, "cost_usd": 0.1,
         "tokens": {"n_calls": 1, "input_tokens": 1, "output_tokens": 1, "total_tokens": 2}},
    ], complete=True, seconds=1.0)

    assert "computed" in report["silent_error_rate"] and "today" in report["silent_error_rate"], (
        "the fixture must carry what the freeze removes, or the tests below prove nothing"
    )
    (directory / f"{cell.key}.json").write_text(json.dumps(report))
    return directory


@pytest.fixture
def two_reference_cells(tmp_path):
    import json

    payload = {"measured_on": "2026-07-29", "noise_floors": {}, "cells": [
        {"key": "reference_L0_loop_r0", "label": "Sonnet · L0 · loop", "reference": True},
        {"key": "reference_L3_loop_r0", "label": "Sonnet · L3 · loop", "reference": True},
    ]}
    path = tmp_path / "ref.json"
    path.write_text(json.dumps(payload))
    return path


# ---- the worker baseline: what makes `compare` mean anything ------------------


# ---- the guard never checked the cells it was freezing ----------------------
#
# `assert_same_run` compared _RUN_IDENTITY_FIELDS for the FRONTIER keys against the
# committed measurements.json, and `build_worker_baseline` then globbed worker_*.json
# out of the same directory and froze whatever was there. So the guard established
# "this directory's frontier cells are the committed frontier reference" and inferred
# the worker half from shared directory membership. Nothing about the six cells it was
# freezing was verified, and a worker cell re-run at any later date — different code,
# different pricing table, different gold set — in that directory passed untouched,
# because the cells it checked were never involved.
#
# The fixture builds its frontier cells FROM the committed reference rather than
# copying results/sweep/, which a fresh clone does not have. A guard's own test must
# not depend on the author's untracked working directory.


@pytest.fixture
def matching_sweep_dir(tmp_path):
    """A directory whose frontier cells ARE the committed reference, field for field."""
    from loopeng.sweep.reference import REFERENCE_PATH, WORKER_BASELINE_PATH

    directory = tmp_path / "sweep"
    directory.mkdir()
    for source in (REFERENCE_PATH, WORKER_BASELINE_PATH):
        for cell in json.loads(source.read_text())["cells"]:
            cell = {k: v for k, v in cell.items()
                    if k not in ("reference", "measured_on", "paired")}
            (directory / f"{cell['key']}.json").write_text(json.dumps(cell))
    return directory


def _stamp(path, **fields):
    body = json.loads(path.read_text())
    body["run_fingerprint"] = {
        "run_id": "aaaa", "warehouse_seed": 20260729, "gold_sha256": "beef",
        "prices_taken_on": "2026-07-29", "code_revision": "9738b85", **fields,
    }
    path.write_text(json.dumps(body))


def test_a_run_fingerprint_is_stamped_into_every_cell_file(tmp_path, monkeypatch):
    """Run identity as a recorded fact rather than an inference from which directory a
    file happens to sit in. Stamped at write time in `run_cell`, so a cell carries it
    whether or not anything ever freezes it."""
    from loopeng.agent.classify import Outcome
    from loopeng.sweep import runner
    from loopeng.sweep.fingerprint import RunFingerprint

    class _Ledger:
        def cost_usd(self):
            return 0.0

        def totals(self):
            return {"n_calls": 1, "input_tokens": 1, "output_tokens": 1, "total_tokens": 2}

    class _Run:
        sql, rows, error, termination, attempts = "SELECT 1", [[1]], None, "success", (1,)
        ledger = _Ledger()

    class _Judgement:
        # Every field `run_cell` reads off a judgement. A stub short of one is a stub
        # teaching a shape that does not exist, and it fails the moment the real thing
        # grows a field — which is how this one caught `visible_kind` being added.
        outcome, ran_and_returned = Outcome.CORRECT, True
        unearned = False
        visible_kind = None

    monkeypatch.setattr(runner, "run_question", lambda *a, **k: _Run())
    monkeypatch.setattr(runner, "judge", lambda *a, **k: _Judgement())

    fingerprint = RunFingerprint.for_run(ITEMS, warehouse_seed=20260729)
    report = runner.run_cell(Cell("agent", "L0", "one_shot"), ITEMS[:2],
                             tmp_path / "w.duckdb", directory=tmp_path / "cells",
                             fingerprint=fingerprint)

    stored = json.loads((tmp_path / "cells" / "agent_L0_one_shot_r0.json").read_text())
    assert stored["run_fingerprint"] == report["run_fingerprint"]
    assert stored["run_fingerprint"]["warehouse_seed"] == 20260729
    assert stored["run_fingerprint"]["prices_taken_on"] == PRICES_TAKEN_ON
    assert len(stored["run_fingerprint"]["gold_sha256"]) == 64


def test_a_cell_written_without_a_fingerprint_simply_has_no_key(tmp_path):
    """Additive, like the two cache token classes before it: a cell recorded before this
    existed carries no fingerprint, and absence is read as 'unverifiable' rather than as
    a match against a default."""
    report = summarise_cell(Cell("agent", "L0", "loop"), [], complete=True, seconds=0.0)

    assert "run_fingerprint" not in report


def test_a_resumed_sweep_keeps_the_run_id_it_is_resuming(tmp_path):
    """Resume is the whole point of the runner: a dropped connection costs the cell in
    flight, never the cells behind it. A fresh run id per invocation would make the
    author's own resumed development run impossible to freeze."""
    from loopeng.sweep.fingerprint import RunFingerprint, resolve_run_id

    directory = tmp_path / "cells"
    directory.mkdir()
    first = RunFingerprint.for_run(ITEMS, warehouse_seed=20260729)
    (directory / "agent_L0_loop_r0.json").write_text(
        json.dumps({"key": "agent_L0_loop_r0", "complete": True,
                    "run_fingerprint": first.as_dict()})
    )

    second = RunFingerprint.for_run(ITEMS, warehouse_seed=20260729)
    assert second.run_id != first.run_id
    assert resolve_run_id(second, directory).run_id == first.run_id


def test_a_resumed_sweep_will_not_adopt_a_run_it_does_not_match(tmp_path):
    """Only inherited when the inputs agree. Otherwise this is a different measurement
    continuing in the same directory, and saying so is the entire job."""
    from loopeng.sweep.fingerprint import RunFingerprint, resolve_run_id

    directory = tmp_path / "cells"
    directory.mkdir()
    stale = RunFingerprint.for_run(ITEMS, warehouse_seed=1).as_dict()
    (directory / "agent_L0_loop_r0.json").write_text(
        json.dumps({"key": "agent_L0_loop_r0", "complete": True,
                    "run_fingerprint": stale})
    )

    current = RunFingerprint.for_run(ITEMS, warehouse_seed=20260729)
    assert resolve_run_id(current, directory).run_id == current.run_id


# ---- the frontier cells get their per-item outcomes back --------------------
#
# `build_reference` strips `items` — SQL and rows are development-only bulk — and with
# them went `{item_id: was_correct}`, which is McNemar's entire input. Six of the ten
# comparisons were therefore dead: every Sonnet pair reported nothing to pair, not
# because the arms answered disjoint sets but because the outcomes were discarded.
#
# The fix is a SIBLING file, not a wider measurements.json. That file is what
# assets/*.png is rendered from, so adding anything to it redraws three committed
# images. The sidecar carries item ids and booleans and nothing else, and it is
# reattached at load, so every reader downstream sees a cell that carries `paired`
# exactly as the worker baseline's cells do.


@pytest.fixture
def a_frozen_frontier_run(tmp_path):
    """A sweep directory and the reference file frozen from it, both synthetic.

    Not a copy of results/sweep: a fresh clone has none, and this is the guard's own
    test.
    """
    from loopeng.sweep.reference import build_reference

    directory = tmp_path / "sweep"
    directory.mkdir()
    cell = Cell("reference", "L0", "loop")
    report = summarise_cell(cell, [
        {"item_id": item_id, "pattern_key": "p", "outcome": "o",
         "ran_and_returned": True, "correct": correct, "termination": "success",
         "n_attempts": 1, "rejections": 0, "cost_usd": 0.1,
         "tokens": {"n_calls": 1, "input_tokens": 1, "output_tokens": 1, "total_tokens": 2}}
        for item_id, correct in (("a", True), ("b", True), ("c", False))
    ], complete=True, seconds=1.0)
    (directory / f"{cell.key}.json").write_text(json.dumps(report))

    reference_path = tmp_path / "measurements.json"
    reference_path.write_text(json.dumps(build_reference(directory)))
    return directory, reference_path


# ---- the freshness default: a checklist line is not enforcement -------------
#
# These used to be named for `--fresh`, the flag that switched the guard ON. The
# default is inverted now: refusing is what you get by typing nothing, and RESUMING is
# what has to be asked for. A guard you have to remember to enable is a checklist line,
# and a checklist line is not enforcement — which is the defect this project is about,
# so having it behind a flag was that defect inside the guard against it.


def test_refuses_when_completed_cells_exist(tmp_path):
    """The single most damaging mistake available on the day: the live sweep resumes
    from yesterday's cells and renders finished numbers to a room that was just told
    nothing is precomputed."""
    import json

    from loopeng.sweep.runner import StaleCellsPresent, require_fresh

    directory = tmp_path / "sweep"
    directory.mkdir()
    cell = build_cells(DEV)[0]
    (directory / f"{cell.key}.json").write_text(
        json.dumps(summarise_cell(cell, [], complete=True, seconds=1.0))
    )
    with pytest.raises(StaleCellsPresent) as exc:
        require_fresh(directory)
    assert cell.key in str(exc.value)


def test_it_refuses_rather_than_deleting(tmp_path):
    """Those files are the outage insurance for stages 0, 2-probes and 4. Silently
    removing them to satisfy a flag trades one failure for a worse one."""
    import json

    from loopeng.sweep.runner import StaleCellsPresent, require_fresh

    directory = tmp_path / "sweep"
    directory.mkdir()
    cell = build_cells(DEV)[0]
    path = directory / f"{cell.key}.json"
    path.write_text(json.dumps(summarise_cell(cell, [], complete=True, seconds=1.0)))
    with pytest.raises(StaleCellsPresent):
        require_fresh(directory)
    assert path.is_file(), "the guard must not delete the outage insurance"


def test_an_empty_directory_is_allowed(tmp_path):
    from loopeng.sweep.runner import require_fresh

    require_fresh(tmp_path / "absent")
    (tmp_path / "sweep").mkdir()
    require_fresh(tmp_path / "sweep")


def test_incomplete_cells_are_ignored(tmp_path):
    """A partial cell is re-run anyway, so it is not the hazard this guards. That now
    includes a cell the deadline stopped, which stays `complete: False` for exactly
    this reason."""
    import json

    from loopeng.sweep.runner import require_fresh

    directory = tmp_path / "sweep"
    directory.mkdir()
    cell = build_cells(DEV)[0]
    (directory / f"{cell.key}.json").write_text(
        json.dumps(summarise_cell(cell, [], complete=False, seconds=1.0))
    )
    require_fresh(directory)


def test_resume_still_works_when_asked_for(tmp_path):
    """The outage path DEPENDS on resume working. Inverting the default must not have
    removed the capability, only moved it behind a name."""
    import json

    from loopeng.sweep.runner import load_cell

    directory = tmp_path / "sweep"
    directory.mkdir()
    cell = build_cells(DEV)[0]
    (directory / f"{cell.key}.json").write_text(
        json.dumps(summarise_cell(cell, [], complete=True, seconds=1.0))
    )
    assert load_cell(cell, directory) is not None, "resume must still work when asked"


def test_run_sweep_refuses_before_printing_the_pre_registration(tmp_path, capsys):
    """Refusing after printing a hypothesis to the room reads as a crash, not a guard."""
    import json

    from loopeng.sweep.runner import StaleCellsPresent

    directory = tmp_path / "sweep"
    directory.mkdir()
    cell = build_cells(DEV)[0]
    (directory / f"{cell.key}.json").write_text(
        json.dumps(summarise_cell(cell, [], complete=True, seconds=1.0))
    )
    with pytest.raises(StaleCellsPresent):
        # No flag. Refusing is the default, which is the whole change.
        run_sweep(ITEMS, tmp_path / "w.duckdb", directory=directory)
    assert "PRE-REGISTRATION" not in capsys.readouterr().out


def test_the_dangerous_behaviour_is_the_one_you_have_to_ask_for(tmp_path, capsys):
    """The inversion itself, stated as a test.

    Before: typing nothing resumed, and `--fresh` refused. So the failure mode — a
    sweep completing in a second and rendering finished numbers to a room told nothing
    was precomputed — was what you got by forgetting a flag. Now it takes an explicit
    `--resume` to reach it.
    """
    import json

    from loopeng.sweep.runner import StaleCellsPresent

    directory = tmp_path / "sweep"
    directory.mkdir()
    cell = build_cells(DEV)[0]
    (directory / f"{cell.key}.json").write_text(
        json.dumps(summarise_cell(cell, [], complete=True, seconds=1.0))
    )

    with pytest.raises(StaleCellsPresent):
        run_sweep([], tmp_path / "w.duckdb", directory=directory, quiet=True)

    report = run_sweep([], tmp_path / "w.duckdb", directory=directory, quiet=True,
                       resume=True)
    assert cell.key in report["resumed"]


def test_the_refusal_names_all_three_ways_out(tmp_path):
    """An operator hitting this is mid-session with a room watching. A refusal that
    says only "no" costs more than one that says what to type."""
    import json

    from loopeng.sweep.runner import StaleCellsPresent, require_fresh

    directory = tmp_path / "sweep"
    directory.mkdir()
    cell = build_cells(DEV)[0]
    (directory / f"{cell.key}.json").write_text(
        json.dumps(summarise_cell(cell, [], complete=True, seconds=1.0))
    )
    with pytest.raises(StaleCellsPresent) as exc:
        require_fresh(directory)
    message = str(exc.value)
    assert "rm -rf" in message
    assert "--resume" in message
    assert "--dir" in message
    assert "outage insurance" in message


# ---- one profile must not inherit another's cells ----------------------------


def _stored_cell(directory: Path, key: str, *, n_items: int, cost: float):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{key}.json").write_text(json.dumps({
        "key": key, "label": key, "role": "agent", "level": "L0",
        "mode": key.split("_")[2], "replicate": 0,
        "complete": True, "seconds": 1.0, "n_items": n_items,
        "n_done": n_items, "ran_and_returned": n_items,
        "correct": n_items, "silent_errors": 0,
        "silent_error_rate": "0.0%", "rate_value": 0.0,
        "rate_ci_low": 0.0, "rate_ci_high": 0.0, "rate_n": n_items,
        "cost_usd": {"value": cost, "source": "estimated"},
        "items": {f"i{n}": True for n in range(n_items)},
    }))


def test_a_cell_measured_over_a_different_item_count_is_not_resumed(tmp_path):
    """`smoke` run after `delivery` used to resume delivery's 50-item cells,
    report them as the smoke measurement, make ZERO model calls, and print
    `spend: est. $0.8642 of $0.05` — seventeen times its own cap — then exit 0.

    The cell key is `role_level_mode_rN`: it encodes neither the profile nor the
    item count, and every profile defaults to the same directory.
    """
    from loopeng.sweep.runner import Cell, load_cell

    _stored_cell(tmp_path, "agent_L0_loop_r0", n_items=50, cost=0.4321)
    cell = Cell(role="agent", level="L0", mode="loop", replicate=0)

    assert load_cell(cell, tmp_path, expect_items=50) is not None, "same size resumes"
    assert load_cell(cell, tmp_path, expect_items=8) is None, "8-item run resumed a 50-item cell"


def test_a_cell_stored_before_n_items_existed_still_resumes(tmp_path):
    """Absence means unverifiable, not mismatched — the same treatment a missing
    fingerprint already gets. Refusing these would silently invalidate every
    measurement committed before the field existed."""
    from loopeng.sweep.runner import Cell, load_cell

    _stored_cell(tmp_path, "agent_L0_loop_r0", n_items=50, cost=0.4)
    path = tmp_path / "agent_L0_loop_r0.json"
    body = json.loads(path.read_text())
    del body["n_items"]
    path.write_text(json.dumps(body))

    cell = Cell(role="agent", level="L0", mode="loop", replicate=0)
    assert load_cell(cell, tmp_path, expect_items=8) is not None


def test_a_completed_cell_still_resumes_when_no_expectation_is_given(tmp_path):
    from loopeng.sweep.runner import Cell, load_cell

    _stored_cell(tmp_path, "agent_L0_loop_r0", n_items=50, cost=0.4)
    cell = Cell(role="agent", level="L0", mode="loop", replicate=0)
    assert load_cell(cell, tmp_path) is not None


# ---- labels are derived, never restated -------------------------------------


def test_a_cell_label_names_the_model_the_registry_actually_holds():
    """The label read `"Haiku" if role == "agent" else "Sonnet"`, and both names were
    wrong: the roles resolve to a different vendor's models now. Every dial and cost
    bar in the sweep was labelled with the models from two registries ago, and nothing
    failed, because a hardcoded string cannot disagree with anything.

    Derived on both sides — the assertion reads the registry too — so this keeps
    holding when the registry changes rather than becoming the next stale literal.
    """
    from loopeng.registry import SCORING_ROLES, spec_for

    for role in SCORING_ROLES:
        label = Cell(role, "L0", "loop").label
        assert spec_for(role).model_id in label, (
            f"the {role} label says {label!r}, which does not name its model"
        )


def test_every_cell_the_sweep_builds_has_a_label_naming_its_own_model():
    """The property that matters is per-cell, not per-role: a cell is what gets drawn."""
    from loopeng.registry import spec_for

    for cell in build_cells(DEV):
        assert spec_for(cell.role).model_id in cell.label


def test_no_shipped_module_carries_a_cell_key_as_a_literal():
    """`Cell.key` is the only place a cell key is spelled.

    The same literal — `worker_L0_loop_r0` — was hardcoded in THREE modules:
    `sweep/render.py` chose which cell the abstention curve is drawn from,
    `views/oversight.py` chose which cell that screen reads, and
    `demos/02_verification_loop/abstain.py` defaulted its `--cell` flag. No sweep has
    produced a `worker_*` key since the roles were renamed, so all three could never
    match, and all three printed some variant of "run the sweep first" over a directory
    full of cells.

    Three instances of one string is not three mistakes; it is one mistake copied. This
    is the door closed: a key belongs to `Cell`, and anything else that needs one asks
    for it.

    Comments may still QUOTE the dead key — all three modules do, recording what they
    used to say — because the AST carries no comments and a docstring naming it would
    be prose about history rather than a value anything reads.
    """
    import ast
    import re
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    shaped = re.compile(r"^[a-z_]+_L[0-9]_(one_shot|loop)_r[0-9]+$")
    offenders = []
    for tree_dir in ("src", "demos", "tools", "scripts"):
        for path in sorted((root / tree_dir).rglob("*.py")):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                        and shaped.match(node.value.strip())):
                    offenders.append(
                        f"{path.relative_to(root)}:{node.lineno} {node.value!r}")
    assert not offenders, (
        "these spell a cell key rather than asking `Cell` for one, which is how the "
        "same dead key ended up in three modules:\n  " + "\n  ".join(offenders)
    )
