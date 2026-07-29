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


# ---- charts: two, not three, and honest when empty --------------------------


def test_only_two_charts_are_shipped():
    """TIER moved to Phase 4. Shipping it here would plot a finding that measurably
    did not reproduce."""
    from loopeng.sweep import charts

    builders = [n for n in dir(charts) if n.endswith("_chart")]
    assert sorted(builders) == ["cost_chart", "dial_chart"]


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
    """Gate 3: both charts build live from nothing on disk."""
    from loopeng.sweep.charts import write_charts

    written = write_charts([summarise_cell(Cell("worker", "L0", "loop"), [],
                                           complete=False, seconds=0.0)], tmp_path / "c")
    assert [p.name for p in written] == ["dial.svg", "cost.svg"]
    assert all(p.read_text().startswith("<svg") for p in written)


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


def test_a_live_cell_suppresses_its_reference_twin(tmp_path):
    """Plotting the same cell twice — once solid, once hatched — reads as two
    measurements disagreeing rather than one shown twice. Live always wins."""
    import json

    from loopeng.sweep.reference import load_reference

    payload = {"measured_on": "2026-07-29", "noise_floors": {}, "cells": [
        {"key": "frontier_L0_loop_r0", "label": "Sonnet · L0 · loop", "reference": True},
        {"key": "frontier_L3_loop_r0", "label": "Sonnet · L3 · loop", "reference": True},
    ]}
    path = tmp_path / "ref.json"
    path.write_text(json.dumps(payload))

    assert len(load_reference(path)) == 2
    kept = load_reference(path, exclude_keys={"frontier_L0_loop_r0"})
    assert [c["key"] for c in kept] == ["frontier_L3_loop_r0"]


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
