"""The sweep's three load-bearing properties, tested offline."""

import json

import pytest

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

    empty = summarise_cell(Cell("worker", "L0", "loop"), [], complete=False, seconds=0.0)
    for svg in (dial_chart([empty]), cost_chart([empty])):
        assert "not yet measured" in svg
        assert svg.startswith("<svg")


def test_charts_write_from_a_cold_start(tmp_path):
    """Gate 3: every chart builds live from nothing on disk.

    DELTA and ABSTENTION are written even with no input. A chart that silently does not
    exist is indistinguishable from a chart whose finding is absent.
    """
    from loopeng.sweep.charts import write_charts

    written = write_charts([summarise_cell(Cell("worker", "L0", "loop"), [],
                                           complete=False, seconds=0.0)], tmp_path / "c")
    assert [p.name for p in written] == [
        "dial.svg", "cost.svg", "delta.svg", "abstention.svg",
    ]
    assert all(p.read_text().startswith("<svg") for p in written)
    assert "not yet measured" in (tmp_path / "c" / "delta.svg").read_text()


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


def test_the_profile_flag_is_required(tmp_path):
    """A delivery run must not inherit development settings by omission — that is a
    tenfold cost difference decided by a flag nobody typed."""
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "demos/04_hill_climbing_loop/sweep.py"],
        capture_output=True, text=True, cwd=tmp_path.parent, timeout=120,
    )
    assert result.returncode != 0


# ---- reference measurements are visibly not live ----------------------------


def test_a_reference_cell_never_claims_it_was_computed_today():
    """Metric.render() bakes in 'computed HH:MM today'. On a stored measurement that
    sentence is false in exactly the way that makes a cited number look computed."""
    from loopeng.sweep.reference import build_reference

    for cell in build_reference().get("cells", []):
        assert "today" not in cell["silent_error_rate"]
        assert cell["measured_on"] in cell["silent_error_rate"]


def test_reference_cells_are_flagged_and_dated():
    from loopeng.sweep.reference import build_reference

    for cell in build_reference().get("cells", []):
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

    svg = dial_chart([live, ref])
    assert "REFERENCE" in svg
    assert "2026-07-29" in svg
    # Hatched outline, never a solid fill.
    assert "stroke-dasharray" in svg


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
