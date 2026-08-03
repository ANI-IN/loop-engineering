"""The sweep's three load-bearing properties, tested offline."""

import json
from pathlib import Path

import pathlib

import pytest

from loopeng.pricing import PRICES_TAKEN_ON
from loopeng.sweep.orchestrator import detectable_effect, load_all, pre_registration, run_sweep
from loopeng.sweep.runner import (
    DEVELOPMENT,
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
    cells = build_cells(DEVELOPMENT)
    assert len(cells) == 12
    l0_loop = [c for c in cells if c.level == "L0" and c.mode == "loop"]
    assert len(l0_loop) == 6
    assert {c.role for c in l0_loop} == {"worker", "frontier"}


def test_replicates_are_on_both_models_not_one():
    """They measure two different determinism floors — Haiku pinned, Sonnet not — and
    neither model's floor may be asserted for the other."""
    cells = build_cells(DEVELOPMENT)
    per_role = {r: len([c for c in cells if c.role == r and c.level == "L0"
                        and c.mode == "loop"]) for r in ("worker", "frontier")}
    assert per_role == {"worker": 3, "frontier": 3}


def test_cell_keys_are_unique():
    cells = build_cells(DEVELOPMENT)
    assert len({c.key for c in cells}) == len(cells)


# ---- the abort is on PROJECTED spend ----------------------------------------


def test_abort_triggers_on_projection_not_actuals(tmp_path):
    """The whole point. A cap checked against money already spent only discovers the
    breach afterwards; this refuses to start a cell whose projected total breaches."""
    with pytest.raises(SweepAborted) as exc:
        run_sweep(ITEMS, tmp_path / "w.duckdb", profile=DEVELOPMENT, cap_usd=0.01,
                  directory=tmp_path / "sweep", quiet=True)
    message = str(exc.value)
    assert "aborting BEFORE" in message
    assert "projected total" in message
    # Nothing ran: no cell files were written.
    assert not list((tmp_path / "sweep").glob("*.json"))


def test_abort_names_the_last_completed_cell(tmp_path):
    with pytest.raises(SweepAborted) as exc:
        run_sweep(ITEMS, tmp_path / "w.duckdb", profile=DEVELOPMENT, cap_usd=0.01,
                  directory=tmp_path / "sweep", quiet=True)
    assert "Last completed cell" in str(exc.value)


def test_a_generous_cap_does_not_abort_before_the_first_cell(tmp_path):
    """Guards the opposite failure: an abort that fires when it should not."""
    cells = build_cells(DEVELOPMENT)
    assert project_remaining(cells, 50) < 8.0


def test_projection_covers_every_remaining_cell():
    cells = build_cells(DEVELOPMENT)
    assert project_remaining(cells, 50) > project_remaining(cells[1:], 50)


# ---- resume from results/, not LangSmith ------------------------------------


def test_a_complete_cell_is_resumed_from_disk(tmp_path):
    cell = build_cells(DEVELOPMENT)[0]
    directory = tmp_path / "sweep"
    directory.mkdir()
    report = summarise_cell(cell, [], complete=True, seconds=1.0)
    (directory / f"{cell.key}.json").write_text(json.dumps(report))
    assert load_cell(cell, directory) is not None


def test_an_incomplete_cell_is_not_resumed(tmp_path):
    """A partial cell must be re-run, not counted. Resuming a half-finished cell would
    report a rate over whatever happened to have landed."""
    cell = build_cells(DEVELOPMENT)[0]
    directory = tmp_path / "sweep"
    directory.mkdir()
    partial = summarise_cell(cell, [], complete=False, seconds=1.0)
    (directory / f"{cell.key}.json").write_text(json.dumps(partial))
    assert load_cell(cell, directory) is None


# ---- progressive rendering: never blank, never zero, never a guess ----------


def test_a_cell_with_nothing_landed_renders_not_yet_measured():
    report = summarise_cell(Cell("worker", "L0", "loop"), [], complete=False, seconds=0.0)
    assert report["silent_error_rate"] == "not yet measured"
    assert report["rate_value"] is None


def test_a_cell_in_progress_shows_its_n_so_far_and_an_interval():
    rows = [
        {"item_id": "a", "pattern_key": "p", "outcome": "correct", "ran_and_returned": True,
         "correct": True, "termination": "success", "n_attempts": 1, "rejections": 0,
         "cost_usd": 0.001, "tokens": {"n_calls": 1, "input_tokens": 1,
                                       "output_tokens": 1, "total_tokens": 2}},
    ]
    report = summarise_cell(Cell("worker", "L0", "loop"), rows, complete=False, seconds=1.0)
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
    report = summarise_cell(Cell("worker", "L0", "loop"), rows, complete=True, seconds=1.0)
    assert "in progress" not in report["silent_error_rate"]
    assert "n=1" in report["silent_error_rate"]


def test_a_cell_never_reports_a_bare_zero():
    report = summarise_cell(Cell("worker", "L0", "loop"), [], complete=False, seconds=0.0)
    assert report["silent_error_rate"] != "0.0%"
    assert report["rate_value"] is not None or report["silent_error_rate"] == "not yet measured"


# ---- the pre-registration ---------------------------------------------------


def test_the_pre_registration_names_all_four_categories():
    text = pre_registration(50)
    for heading in ("HEADLINE", "NAMED SECONDARY", "EXPLICITLY UNDERPOWERED",
                    "NOT DETECTABLE"):
        assert heading in text


def test_the_pre_registration_computes_the_detectable_effect():
    """Computed, not stated."""
    text = pre_registration(50)
    assert f"{detectable_effect(50) * 100:.0f} percentage points" in text


def test_the_detectable_effect_shrinks_as_n_grows():
    assert detectable_effect(200) < detectable_effect(50)


def test_the_pre_registration_cites_the_measured_l3_result():
    text = pre_registration(50)
    assert "p=0.219" in text
    assert "will not claim" in text


def test_the_pre_registration_states_the_temperature_asymmetry():
    text = pre_registration(50)
    assert "NOT comparable across models" in text
    assert "16.2%" in text


def test_load_all_returns_nothing_when_no_cells_exist(tmp_path):
    assert load_all(tmp_path / "absent") == []


# ---- charts: four, and TIER is still not one of them -------------------------


def test_the_shipped_charts_are_pinned_and_tier_is_not_among_them():
    """TIER moved to Phase 4. Shipping it here would plot a finding that measurably
    did not reproduce.

    DELTA and ABSTENTION are the two that arrived, and neither is a new figure so much
    as a gap closed: DIAL and COST are per-cell absolute values, so nothing here showed
    a difference at all; and ABSTENTION existed only in the README renderer, which reads
    frozen data, so a cloner could not reproduce assets/abstention.png from their own run.
    """
    from loopeng.sweep import charts

    builders = [n for n in dir(charts) if n.endswith("_chart")]
    assert sorted(builders) == [
        "abstention_chart", "cost_chart", "delta_chart", "dial_chart",
    ]
    assert "tier_chart" not in builders


def test_the_dial_caption_warns_the_bars_are_not_cross_comparable():
    from loopeng.sweep.charts import DIAL_CAPTION

    assert "NOT COMPARABLE ACROSS MODELS" in DIAL_CAPTION
    assert "temperature=0" in DIAL_CAPTION
    assert "clusters" in DIAL_CAPTION


def test_the_cost_caption_keeps_the_estimated_label():
    from loopeng.sweep.charts import COST_CAPTION

    assert "estimate" in COST_CAPTION.lower()
    assert "billed" in COST_CAPTION


def test_charts_render_from_no_data_without_inventing_a_zero():
    from loopeng.sweep.charts import cost_chart, dial_chart
    from tests.figures import texts

    empty = summarise_cell(Cell("worker", "L0", "loop"), [], complete=False, seconds=0.0)
    for figure in (dial_chart([empty]), cost_chart([empty])):
        assert "not yet measured" in texts(figure)


def test_charts_write_from_a_cold_start(tmp_path):
    """Gate 3: every chart builds live from nothing on disk.

    DELTA and ABSTENTION are written even with no input. A chart that silently does not
    exist is indistinguishable from a chart whose finding is absent.
    """
    from loopeng.sweep.charts import write_charts

    written = write_charts([summarise_cell(Cell("worker", "L0", "loop"), [],
                                           complete=False, seconds=0.0)], tmp_path / "c")
    assert [p.name for p in written] == [
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


def test_delivery_is_four_haiku_cells():
    from loopeng.sweep.runner import DELIVERY

    cells = build_cells(DELIVERY)
    assert len(cells) == 4
    assert {c.role for c in cells} == {"worker"}
    assert all(c.replicate == 0 for c in cells)


def test_delivery_projects_under_its_cap():
    """Cost is a hard constraint at delivery, not a target."""
    from loopeng.sweep.runner import DELIVERY

    assert project_remaining(build_cells(DELIVERY), 50) < DELIVERY.cap_usd


def test_delivery_is_far_cheaper_than_development():
    from loopeng.sweep.runner import DELIVERY, DEVELOPMENT

    delivery = project_remaining(build_cells(DELIVERY), 50)
    development = project_remaining(build_cells(DEVELOPMENT), 50)
    assert development > delivery * 5


def test_delivery_runs_no_ablation():
    """The ablation is a development finding and never appears in the session."""
    from loopeng.sweep.runner import DELIVERY, DEVELOPMENT

    assert DELIVERY.runs_ablation is False
    assert DEVELOPMENT.runs_ablation is True


# ---- the smoke profile: the pipeline, on a cloner's key, for pennies ---------


def test_smoke_is_two_l0_cells():
    from loopeng.sweep.runner import SMOKE

    cells = build_cells(SMOKE)
    assert len(cells) == 2
    assert {c.key for c in cells} == {"worker_L0_one_shot_r0", "worker_L0_loop_r0"}
    assert {c.role for c in cells} == {"worker"}


def test_smoke_projects_to_a_few_cents():
    """The cheapest live path there is. Before it existed, the smallest was `delivery`
    at 4 cells x 50 items."""
    from loopeng.sweep.runner import DELIVERY, SMOKE

    smoke = project_remaining(build_cells(SMOKE), SMOKE.item_limit)
    delivery = project_remaining(build_cells(DELIVERY), 50)

    assert smoke < SMOKE.cap_usd
    assert smoke * 10 < delivery, f"smoke projects est. ${smoke:.4f}, not cheap enough"


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
    from loopeng.sweep.runner import DELIVERY, LimitNotAllowed, resolve_item_limit

    with pytest.raises(LimitNotAllowed) as exc:
        resolve_item_limit(DELIVERY, 5)
    assert "delivery" in str(exc.value)


def test_limit_is_accepted_where_it_is_declared():
    from loopeng.sweep.runner import DEVELOPMENT, SMOKE, resolve_item_limit

    assert resolve_item_limit(DEVELOPMENT, 5) == 5
    assert resolve_item_limit(SMOKE, 3) == 3


def test_every_profile_declares_whether_it_takes_a_limit():
    """So a new profile has to make the decision rather than inherit a default that
    happens to be permissive."""
    from loopeng.sweep.runner import PROFILES

    permissive = {p.name for p in PROFILES.values() if p.allows_limit}
    assert permissive == {"smoke", "development"}


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

    repo_root = pathlib.Path(__file__).resolve().parent.parent
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
    cell = Cell("frontier", "L0", "loop")
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


def test_a_reference_cell_never_claims_it_was_computed_today(a_live_frontier_cell):
    """Metric.render() bakes in 'computed HH:MM today'. On a stored measurement that
    sentence is false in exactly the way that makes a cited number look computed."""
    from loopeng.sweep.reference import build_reference

    cells = build_reference(a_live_frontier_cell)["cells"]

    assert cells, "no cell was frozen, so the loop below asserts nothing"
    for cell in cells:
        assert "today" not in cell["silent_error_rate"]
        assert cell["measured_on"] in cell["silent_error_rate"]


def test_no_committed_measurement_under_results_claims_it_was_computed_today():
    """The general form of the test above, and the reason it has to be general.

    `sweep/reference.py` carries the pattern and rewrites it at freeze time, so a cell
    that goes through `_freeze` is safe. Files that reach `results/` any other way never
    touch it — and `results/noise_floor_haiku_default_temp.json` shipped saying
    "computed 18:55 today", which is false every day anybody opens it, in the exact way
    that module exists to prevent.

    Scoped to what git TRACKS, which is the definition of stored: an untracked cell in
    results/sweep/ was computed today and is entitled to say so.
    """
    import subprocess

    from loopeng.sweep.reference import _COMPUTED_TODAY

    root = Path(__file__).resolve().parent.parent
    tracked = subprocess.run(["git", "ls-files", "results"], capture_output=True,
                             text=True, cwd=root).stdout.split()

    offenders = []
    for name in tracked:
        if not name.endswith(".json"):
            continue
        for found in _COMPUTED_TODAY.findall((root / name).read_text(encoding="utf-8")):
            offenders.append(f"{name}: {found!r}")

    assert offenders == [], (
        "a committed measurement claims it was computed today:\n  "
        + "\n  ".join(sorted(set(offenders)))
        + "\nRewrite it with loopeng.sweep.reference.as_stored, which is what _freeze "
          "uses. Editing the literal fixes one file; the writer is what recurs."
    )


def test_reference_cells_are_flagged_and_dated(a_live_frontier_cell):
    from loopeng.sweep.reference import build_reference

    cells = build_reference(a_live_frontier_cell)["cells"]

    assert cells, "no cell was frozen, so the loop below asserts nothing"
    for cell in cells:
        assert cell["reference"] is True
        assert cell["measured_on"]


def test_reference_bars_are_drawn_differently_from_live_ones():
    from loopeng.sweep.charts import dial_chart

    live = summarise_cell(Cell("worker", "L0", "loop"), [
        {"item_id": "a", "pattern_key": "p", "outcome": "silent_error",
         "ran_and_returned": True, "correct": False, "termination": "success",
         "n_attempts": 1, "rejections": 0, "cost_usd": 0.1,
         "tokens": {"n_calls": 1, "input_tokens": 1, "output_tokens": 1, "total_tokens": 2}},
    ], complete=True, seconds=1.0)
    ref = dict(live, reference=True, measured_on="2026-07-29", role="frontier")

    figure = dial_chart([live, ref])

    from tests.figures import texts
    drawn = texts(figure)
    assert "REFERENCE" in drawn
    assert "2026-07-29" in drawn

    # Hatched outline, never a solid fill: the stored bar is the one with a hatch and
    # no face colour. Asserted on the patches rather than on markup, and the live bar
    # is checked too — "at least one hatched bar" would pass on a figure that hatched
    # everything, which loses the distinction entirely.
    from matplotlib.patches import Rectangle
    bars = [p for p in figure.axes[0].patches if isinstance(p, Rectangle)]
    hatched = [p for p in bars if p.get_hatch()]
    assert len(hatched) == 1, "exactly one of the two bars is a stored measurement"
    assert hatched[0].get_facecolor()[-1] == 0, "a stored bar must not be filled"
    assert [p for p in bars if not p.get_hatch()], "the live bar must not be hatched"


def test_the_reference_caption_explains_why_they_are_not_recomputed():
    from loopeng.sweep.charts import REFERENCE_CAPTION

    assert "NOT computed in this session" in REFERENCE_CAPTION
    assert "quietly" in REFERENCE_CAPTION


def test_the_ablation_is_not_a_reference_measurement():
    """It is a development finding and does not appear in the session at all."""
    from loopeng.sweep import reference

    assert not hasattr(reference, "ABLATION")
    assert "ablation" in reference.__doc__.lower()


@pytest.fixture
def two_reference_cells(tmp_path):
    import json

    payload = {"measured_on": "2026-07-29", "noise_floors": {}, "cells": [
        {"key": "frontier_L0_loop_r0", "label": "Sonnet · L0 · loop", "reference": True},
        {"key": "frontier_L3_loop_r0", "label": "Sonnet · L3 · loop", "reference": True},
    ]}
    path = tmp_path / "ref.json"
    path.write_text(json.dumps(payload))
    return path


def test_fill_mode_lets_a_live_cell_suppress_its_reference_twin(two_reference_cells):
    """The behaviour that was correct for a development sweep re-measuring its own
    frontier cells: plotting the same cell solid and hatched reads as two measurements
    disagreeing rather than one shown twice."""
    from loopeng.sweep.reference import MODE_FILL, load_reference

    assert len(load_reference(two_reference_cells, mode=MODE_FILL)) == 2
    kept = load_reference(two_reference_cells, mode=MODE_FILL,
                          live_keys={"frontier_L0_loop_r0"})
    assert [c["key"] for c in kept] == ["frontier_L3_loop_r0"]


def test_compare_mode_keeps_both_so_a_delta_is_possible(two_reference_cells):
    """THE fix. `fill` made the cloner's comparison structurally impossible: measuring
    a cell on your own key deleted its stored counterpart from the chart, so your run
    could never be shown beside the baseline."""
    from loopeng.sweep.reference import MODE_COMPARE, load_reference

    kept = load_reference(two_reference_cells, mode=MODE_COMPARE,
                          live_keys={"frontier_L0_loop_r0"})
    assert [c["key"] for c in kept] == ["frontier_L0_loop_r0", "frontier_L3_loop_r0"]


def test_hide_mode_shows_live_cells_only(two_reference_cells):
    from loopeng.sweep.reference import MODE_HIDE, load_reference

    assert load_reference(two_reference_cells, mode=MODE_HIDE) == []


def test_auto_mode_hides_the_baseline_until_this_run_has_one_of_its_own(two_reference_cells):
    """The default, and it is a mode rather than a hardcoded choice because the right
    answer depends on the caller. Sitting next to its three siblings so a reader meets
    all four in one place; the property it exists for is asserted through the entry
    point in tests/test_exhibit.py."""
    from loopeng.sweep.reference import MODE_AUTO, load_reference

    assert load_reference(two_reference_cells, mode=MODE_AUTO) == []
    kept = load_reference(two_reference_cells, mode=MODE_AUTO,
                          live_keys={"frontier_L0_loop_r0"})
    assert [c["key"] for c in kept] == ["frontier_L0_loop_r0", "frontier_L3_loop_r0"]


def test_an_unknown_reference_mode_is_refused(two_reference_cells):
    """Silently falling back to a default would make a typo'd flag render a different
    chart than the one asked for."""
    from loopeng.sweep.reference import load_reference

    with pytest.raises(ValueError, match="unknown reference mode"):
        load_reference(two_reference_cells, mode="compair")


# ---- the worker baseline: what makes `compare` mean anything ------------------


def test_the_worker_baseline_covers_every_delivery_and_smoke_cell():
    """Without it, a cloner running delivery got four solid worker bars beside six
    hatched frontier bars: ten unrelated bars and no difference computable."""
    from loopeng.sweep.reference import load_reference
    from loopeng.sweep.runner import DELIVERY, SMOKE

    stored = {cell["key"] for cell in load_reference()}
    for profile in (SMOKE, DELIVERY):
        for cell in build_cells(profile):
            assert cell.key in stored, (
                f"{cell.key} has no stored counterpart, so --reference=compare cannot "
                f"pair it with anything"
            )


def test_the_worker_baseline_keeps_mcnemars_input():
    """The frontier cells strip `items` entirely, which made a paired comparison
    against the baseline impossible. The baseline keeps item ids and a boolean —
    the minimum McNemar needs, and none of the SQL-and-rows bulk."""
    import json

    from loopeng.sweep.reference import WORKER_BASELINE_PATH, paired_map

    payload = json.loads(WORKER_BASELINE_PATH.read_text())
    for cell in payload["cells"]:
        assert "items" not in cell, "the development bulk must not be committed"
        pairs = paired_map(cell)
        assert len(pairs) == cell["rate_n"], f"{cell['key']} paired map is not its n"
        assert all(isinstance(v, bool) for v in pairs.values())


def test_the_worker_baseline_is_the_same_run_as_the_frontier_reference():
    """Provenance, checked rather than asserted."""
    import json

    from loopeng.sweep.reference import REFERENCE_PATH, WORKER_BASELINE_PATH

    payload = json.loads(WORKER_BASELINE_PATH.read_text())
    assert payload["provenance"]["same_run_as"] == str(REFERENCE_PATH)
    assert payload["provenance"]["verified_by_matching"]
    assert payload["measured_on"] == json.loads(REFERENCE_PATH.read_text())["measured_on"]


def test_the_committed_baseline_says_what_was_NOT_established_about_it():
    """`verified_by_matching` names six FRONTIER keys. That is accurate and it read as
    though the six worker cells in this file had been verified — they had not, and
    these cells predate the fingerprint that would have. The file has to say so."""
    import json

    from loopeng.sweep.reference import WORKER_BASELINE_PATH

    provenance = json.loads(WORKER_BASELINE_PATH.read_text())["provenance"]
    assert set(provenance["unverifiable_for"]) == {
        cell["key"] for cell in
        json.loads(WORKER_BASELINE_PATH.read_text())["cells"]
    }, "every cell in this file is unverified, and every one of them must be named"
    assert provenance["worker_cells_verified_by"].startswith("NOTHING")
    assert provenance["run_fingerprint"] is None


def test_freezing_from_a_different_run_is_refused():
    """results/prefix_v1/sweep/ is committed, inviting, and PRE-FIX: up to 19pp apart
    on the worker L3 cells. Freezing it beside post-fix frontier cells would hand a
    cloner a baseline whose difference from their run is mostly a bug we fixed."""
    from pathlib import Path

    from loopeng.sweep.reference import NotTheSameRun, build_worker_baseline

    with pytest.raises(NotTheSameRun) as exc:
        build_worker_baseline(Path("results/prefix_v1/sweep"))
    assert "DIFFERENT measurement run" in str(exc.value)
    assert "prefix_v1" in str(exc.value)


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


def test_a_worker_cell_from_a_later_run_is_refused(matching_sweep_dir):
    """THE gap. The frontier cells match — so the old guard passed — and one worker
    cell was measured by different code. Worker cells are the cheap ones; re-running
    one is the single most likely thing to have happened."""
    from loopeng.sweep.reference import NotTheSameRun, build_worker_baseline

    for path in sorted(matching_sweep_dir.glob("*.json")):
        _stamp(path)
    _stamp(matching_sweep_dir / "worker_L3_loop_r0.json", code_revision="deadbee")

    with pytest.raises(NotTheSameRun) as exc:
        build_worker_baseline(matching_sweep_dir)
    assert "worker_L3_loop_r0" in str(exc.value)
    assert "code_revision" in str(exc.value)


def test_a_stamped_cell_beside_an_unstamped_one_is_refused(matching_sweep_dir):
    """Half-stamped is not one run. A directory where the frontier cells carry no
    fingerprint and a worker cell does was written by two different versions of this
    code, which is exactly the re-run this guard exists to catch."""
    from loopeng.sweep.reference import NotTheSameRun, build_worker_baseline

    _stamp(matching_sweep_dir / "worker_L3_loop_r0.json")

    with pytest.raises(NotTheSameRun) as exc:
        build_worker_baseline(matching_sweep_dir)
    assert "worker_L3_loop_r0" in str(exc.value)


def test_cells_sharing_one_fingerprint_are_frozen_and_say_so(matching_sweep_dir):
    """The passing case, and what it is allowed to claim: the worker cells are
    verified by the fingerprint they share with the frontier cells, recorded as the
    actual basis rather than left to be inferred from `verified_by_matching`."""
    from loopeng.sweep.reference import build_worker_baseline

    for path in sorted(matching_sweep_dir.glob("*.json")):
        _stamp(path)

    provenance = build_worker_baseline(matching_sweep_dir)["provenance"]
    assert provenance["run_fingerprint"]["run_id"] == "aaaa"
    assert "fingerprint" in provenance["worker_cells_verified_by"]
    assert provenance["unverifiable_for"] == []


def test_unstamped_cells_are_frozen_but_named_as_unverifiable(matching_sweep_dir):
    """The committed baseline predates the fingerprint and cannot carry one. Refusing
    would make it unreproducible; claiming it was verified would be the defect this
    finding is about. So it is frozen and the provenance says which cells nothing
    checked — an honest `unverifiable_for` beats a check that reads stronger than it
    is."""
    from loopeng.sweep.reference import build_worker_baseline

    provenance = build_worker_baseline(matching_sweep_dir)["provenance"]
    assert provenance["run_fingerprint"] is None
    assert provenance["unverifiable_for"] == [
        "worker_L0_loop_r0", "worker_L0_loop_r1", "worker_L0_loop_r2",
        "worker_L0_one_shot_r0", "worker_L3_loop_r0", "worker_L3_one_shot_r0",
    ]
    assert "predate" in provenance["worker_cells_verified_by"]


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
        outcome, ran_and_returned = Outcome.CORRECT, True

    monkeypatch.setattr(runner, "run_question", lambda *a, **k: _Run())
    monkeypatch.setattr(runner, "judge", lambda *a, **k: _Judgement())

    fingerprint = RunFingerprint.for_run(ITEMS, warehouse_seed=20260729)
    report = runner.run_cell(Cell("worker", "L0", "one_shot"), ITEMS[:2],
                             tmp_path / "w.duckdb", directory=tmp_path / "cells",
                             fingerprint=fingerprint)

    stored = json.loads((tmp_path / "cells" / "worker_L0_one_shot_r0.json").read_text())
    assert stored["run_fingerprint"] == report["run_fingerprint"]
    assert stored["run_fingerprint"]["warehouse_seed"] == 20260729
    assert stored["run_fingerprint"]["prices_taken_on"] == PRICES_TAKEN_ON
    assert len(stored["run_fingerprint"]["gold_sha256"]) == 64


def test_a_cell_written_without_a_fingerprint_simply_has_no_key(tmp_path):
    """Additive, like the two cache token classes before it: a cell recorded before this
    existed carries no fingerprint, and absence is read as 'unverifiable' rather than as
    a match against a default."""
    report = summarise_cell(Cell("worker", "L0", "loop"), [], complete=True, seconds=0.0)

    assert "run_fingerprint" not in report


def test_a_resumed_sweep_keeps_the_run_id_it_is_resuming(tmp_path):
    """Resume is the whole point of the runner: a dropped connection costs the cell in
    flight, never the cells behind it. A fresh run id per invocation would make the
    author's own resumed development run impossible to freeze."""
    from loopeng.sweep.fingerprint import RunFingerprint, resolve_run_id

    directory = tmp_path / "cells"
    directory.mkdir()
    first = RunFingerprint.for_run(ITEMS, warehouse_seed=20260729)
    (directory / "worker_L0_loop_r0.json").write_text(
        json.dumps({"key": "worker_L0_loop_r0", "complete": True,
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
    (directory / "worker_L0_loop_r0.json").write_text(
        json.dumps({"key": "worker_L0_loop_r0", "complete": True,
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
    cell = Cell("frontier", "L0", "loop")
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


def test_the_frontier_outcomes_are_frozen_beside_the_cells_they_belong_to(
    a_frozen_frontier_run,
):
    from loopeng.sweep.reference import build_frontier_paired

    directory, reference_path = a_frozen_frontier_run
    payload = build_frontier_paired(directory, reference_path)

    assert payload["paired"] == {"frontier_L0_loop_r0": {"a": True, "b": True, "c": False}}


def test_a_paired_map_that_does_not_add_up_to_its_cell_is_refused(a_frozen_frontier_run):
    """The check `assert_same_run` cannot make. Its identity fields are the cell's
    SUMMARY counts, so flipping one item's outcome without touching them passes it
    untouched — and the resulting map would say a cell got 1 right where the bar beside
    it says 2. Two independent aggregates of the per-item data have to equal the
    committed ones."""
    from loopeng.sweep.reference import (
        PairedDoesNotReconcile,
        assert_same_run,
        build_frontier_paired,
    )

    directory, reference_path = a_frozen_frontier_run
    path = directory / "frontier_L0_loop_r0.json"
    body = json.loads(path.read_text())
    body["items"][0]["correct"] = False           # summary counts untouched
    path.write_text(json.dumps(body))

    assert assert_same_run(directory, reference_path), "the old guard sees nothing wrong"
    with pytest.raises(PairedDoesNotReconcile) as exc:
        build_frontier_paired(directory, reference_path)
    assert "frontier_L0_loop_r0" in str(exc.value)
    assert "correct" in str(exc.value)


def test_the_committed_sidecar_covers_every_frontier_cell_and_adds_up():
    """The shipped artifact, reconciled against the shipped measurements it belongs to.

    Runs on a fresh clone: both files are committed, and neither needs results/sweep.
    """
    from loopeng.sweep.reference import (
        FRONTIER_PAIRED_PATH,
        REFERENCE_PATH,
        frontier_paired,
    )

    committed = {c["key"]: c for c in json.loads(REFERENCE_PATH.read_text())["cells"]}
    sidecar = frontier_paired(FRONTIER_PAIRED_PATH)

    assert set(sidecar) == set(committed), "every frontier cell, or the gap is silent"
    for key, outcomes in sorted(sidecar.items()):
        assert len(outcomes) == committed[key]["ran_and_returned"], key
        assert sum(outcomes.values()) == committed[key]["correct"], key
        assert all(isinstance(v, bool) for v in outcomes.values())


def test_the_sidecar_carries_no_sql_and_no_rows():
    """Item ids and booleans, which is McNemar's input and none of the bulk."""
    from loopeng.sweep.reference import FRONTIER_PAIRED_PATH

    body = json.loads(FRONTIER_PAIRED_PATH.read_text())
    assert "sql" not in body and "rows" not in body
    assert set(body) == {"measured_on", "paired", "provenance", "how"}


def test_loading_the_reference_puts_the_outcomes_back_on_the_cells():
    """Reattached at load, so nothing downstream has to know the storage is split."""
    from loopeng.sweep.reference import MODE_COMPARE, load_reference, paired_map

    frontier = [c for c in load_reference(mode=MODE_COMPARE)
                if c["key"].startswith("frontier_")]

    assert frontier
    for cell in frontier:
        assert paired_map(cell), f"{cell['key']} still cannot be paired"


def test_the_sonnet_comparisons_are_testable_now():
    """The finding, closed. Six of ten comparisons reported nothing to pair; the arms
    had answered overlapping sets all along."""
    from loopeng.sweep.diff import all_comparisons, partition
    from loopeng.sweep.reference import MODE_COMPARE, load_reference

    testable, untestable = partition(all_comparisons(load_reference(mode=MODE_COMPARE)))
    frontier = [c for c in testable if c.key_a.startswith("frontier_")]

    assert frontier, "the frontier pairs are still dead"
    assert not [c for c in untestable if c.key_a.startswith("frontier_")]


def test_the_readme_images_are_rendered_from_measurements_json_alone():
    """The baseline is a second file for this reason: adding cells to measurements.json
    would redraw three committed PNGs, and the author's images are keepers."""
    from tools import render_readme_charts as charts

    keys = {cell["key"] for cell in charts.load_reference()["cells"]}
    assert all(key.startswith("frontier_") for key in keys), (
        "a worker cell reached the README renderer; assets/ would change"
    )


# ---- --fresh: a checklist line is not enforcement ---------------------------


def test_fresh_refuses_when_completed_cells_exist(tmp_path):
    """The single most damaging mistake available on the day: the live sweep resumes
    from yesterday's cells and renders finished numbers to a room that was just told
    nothing is precomputed."""
    import json

    from loopeng.sweep.runner import StaleCellsPresent, require_fresh

    directory = tmp_path / "sweep"
    directory.mkdir()
    cell = build_cells(DEVELOPMENT)[0]
    (directory / f"{cell.key}.json").write_text(
        json.dumps(summarise_cell(cell, [], complete=True, seconds=1.0))
    )
    with pytest.raises(StaleCellsPresent) as exc:
        require_fresh(directory)
    assert cell.key in str(exc.value)


def test_fresh_refuses_rather_than_deleting(tmp_path):
    """Those files are the outage insurance for stages 0, 2-probes and 4. Silently
    removing them to satisfy a flag trades one failure for a worse one."""
    import json

    from loopeng.sweep.runner import StaleCellsPresent, require_fresh

    directory = tmp_path / "sweep"
    directory.mkdir()
    cell = build_cells(DEVELOPMENT)[0]
    path = directory / f"{cell.key}.json"
    path.write_text(json.dumps(summarise_cell(cell, [], complete=True, seconds=1.0)))
    with pytest.raises(StaleCellsPresent):
        require_fresh(directory)
    assert path.is_file(), "--fresh must not delete the outage insurance"


def test_fresh_allows_an_empty_directory(tmp_path):
    from loopeng.sweep.runner import require_fresh

    require_fresh(tmp_path / "absent")
    (tmp_path / "sweep").mkdir()
    require_fresh(tmp_path / "sweep")


def test_fresh_ignores_incomplete_cells(tmp_path):
    """A partial cell is re-run anyway, so it is not the hazard --fresh guards."""
    import json

    from loopeng.sweep.runner import require_fresh

    directory = tmp_path / "sweep"
    directory.mkdir()
    cell = build_cells(DEVELOPMENT)[0]
    (directory / f"{cell.key}.json").write_text(
        json.dumps(summarise_cell(cell, [], complete=False, seconds=1.0))
    )
    require_fresh(directory)


def test_plain_sweep_still_resumes(tmp_path):
    """The outage path DEPENDS on resume working, so --fresh must not have broken it."""
    import json

    from loopeng.sweep.runner import load_cell

    directory = tmp_path / "sweep"
    directory.mkdir()
    cell = build_cells(DEVELOPMENT)[0]
    (directory / f"{cell.key}.json").write_text(
        json.dumps(summarise_cell(cell, [], complete=True, seconds=1.0))
    )
    assert load_cell(cell, directory) is not None, "resume must still work without --fresh"


def test_run_sweep_refuses_before_printing_the_pre_registration(tmp_path, capsys):
    """Refusing after printing a hypothesis to the room reads as a crash, not a guard."""
    import json

    from loopeng.sweep.runner import StaleCellsPresent

    directory = tmp_path / "sweep"
    directory.mkdir()
    cell = build_cells(DEVELOPMENT)[0]
    (directory / f"{cell.key}.json").write_text(
        json.dumps(summarise_cell(cell, [], complete=True, seconds=1.0))
    )
    with pytest.raises(StaleCellsPresent):
        run_sweep(ITEMS, tmp_path / "w.duckdb", directory=directory, fresh=True)
    assert "PRE-REGISTRATION" not in capsys.readouterr().out
