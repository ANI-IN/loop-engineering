"""The exhibit's security boundary: zero model calls, verified by spying.

This is required rather than nice to have. The exhibit is public; a path that quietly
spends would spend somebody else's money, and "we checked the code" is not a control.
"""

from pathlib import Path

import pytest

from loopeng.gold.build import build_gold
from loopeng.sweep.runner import EXHIBIT, PROFILES, build_cells, project_remaining
from loopeng.warehouse.connect import ensure_warehouse


@pytest.fixture(scope="module")
def warehouse(tmp_path_factory):
    return ensure_warehouse(tmp_path_factory.mktemp("wh") / "w.duckdb", seed=20260729)


@pytest.fixture
def constructor_spy(monkeypatch):
    """Count every anthropic.Anthropic ever constructed."""
    import anthropic

    built = []
    original = anthropic.Anthropic.__init__

    def spy(self, *args, **kwargs):
        built.append(1)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(anthropic.Anthropic, "__init__", spy)
    return built


# ---- THE security boundary --------------------------------------------------


def test_building_the_exhibit_constructs_no_model_client(constructor_spy, warehouse):
    from loopeng.views.exhibit import build_exhibit_app

    build_exhibit_app(Path("results/sweep"), build_gold(warehouse), warehouse)
    assert constructor_spy == [], "the exhibit constructed a model client"


def test_the_exhibit_profile_runs_no_cells():
    """No roles means no cells, so there is nothing for a sweep to spend on."""
    assert EXHIBIT.roles == ()
    assert build_cells(EXHIBIT) == ()
    assert project_remaining(build_cells(EXHIBIT), 50) == 0.0


def test_the_exhibit_cap_is_zero():
    """Any attempt to run a cell under this profile refuses immediately."""
    assert EXHIBIT.cap_usd == 0.0
    assert EXHIBIT.escalation_allowance == 0
    assert EXHIBIT.runs_ablation is False


def test_the_exhibit_profile_is_selectable_by_name():
    assert PROFILES["exhibit"] is EXHIBIT


def test_a_sweep_under_the_exhibit_profile_cannot_spend(warehouse, constructor_spy):
    from loopeng.sweep.orchestrator import run_sweep

    report = run_sweep([], warehouse, profile=EXHIBIT, directory=Path("/tmp/exhibit_none"),
                       quiet=True)
    assert report["n_cells"] == 0
    assert report["spend_usd"]["value"] == 0.0
    assert constructor_spy == []


# ---- what the exhibit shows, and what it refuses to imply -------------------


def test_every_exhibit_figure_carries_a_measured_date_not_today():
    from loopeng.sweep.reference import load_reference

    for cell in load_reference():
        assert "today" not in cell["silent_error_rate"]
        assert cell["measured_on"] in cell["silent_error_rate"]


def test_the_banner_says_it_is_frozen_and_names_the_date():
    from loopeng.sweep.reference import MEASURED_ON
    from loopeng.views.exhibit import BANNER

    assert "frozen exhibit" in BANNER
    assert MEASURED_ON in BANNER
    assert "nothing here calls a model" in BANNER


def test_the_spending_path_is_disabled_not_hidden():
    """A button that is merely invisible is still a button."""
    import inspect

    from loopeng.views import exhibit

    source = inspect.getsource(exhibit.disabled_panel)
    assert "interactive=False" in source
    assert "visible=False" not in source


def test_the_disabled_note_explains_rather_than_apologises():
    from loopeng.views.exhibit import DISABLED_NOTE

    assert "only" in DISABLED_NOTE and "session" in DISABLED_NOTE
    assert "fully live" in DISABLED_NOTE


def test_verify_stays_fully_live_in_the_exhibit(constructor_spy):
    """The best part of the exhibit. Rule checking is a pure function over SQL, so it
    must not be degraded to a screenshot."""
    from loopeng.verify.governance import run_governance_probes

    report = run_governance_probes()
    assert report["n_sound"] == report["n_rules"]
    assert constructor_spy == [], "the probe surface should need no model"


# ---- a fresh clone must not render finished numbers ------------------------


def test_a_fresh_checkout_renders_not_yet_measured(tmp_path):
    """REQUIRED. A committed sweep cell would arrive on every clone and make the first
    live sweep resume-and-complete instantly, rendering finished numbers to a room told
    nothing is precomputed. This asserts the gitignore is right."""
    from loopeng.sweep.orchestrator import load_all
    from loopeng.views.dial import _rows

    empty = tmp_path / "sweep"          # a clone has no results/sweep at all
    assert load_all(empty) == []
    assert "No cells yet" in _rows(load_all(empty))


def test_no_live_cell_output_is_tracked_by_git():
    """The same property, checked against git rather than the filesystem."""
    import subprocess

    tracked = subprocess.run(
        ["git", "ls-files", "results/sweep", "results/ablation", "results/charts"],
        capture_output=True, text=True, cwd=Path(__file__).resolve().parent.parent,
    ).stdout.strip()
    assert tracked == "", f"live cell output is tracked: {tracked}"


def test_the_reference_measurements_ARE_tracked():
    """The other half: without these the delivery chart has nothing to cite."""
    import subprocess

    tracked = subprocess.run(
        ["git", "ls-files", "results/reference"],
        capture_output=True, text=True, cwd=Path(__file__).resolve().parent.parent,
    ).stdout.strip()
    assert "measurements.json" in tracked


def test_the_warehouse_checksum_is_asserted_not_assumed():
    """A Space silently serving different data than the session would make every
    figure on it wrong in a way nobody could see."""
    from loopeng.warehouse.expected import EXPECTED_CONTENT_CHECKSUM, assert_matches

    assert len(EXPECTED_CONTENT_CHECKSUM) == 64
    import inspect
    assert "WarehouseMismatch" in inspect.getsource(assert_matches)
