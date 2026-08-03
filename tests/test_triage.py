"""Phase 4: abstention as a choice, escalation, and triage by cause."""

import pytest

from loopeng.triage.abstain import CONFIDENCE, confidence_of, curve, decide, operating_point
from loopeng.triage.escalate import MAX_ESCALATIONS, escalation_rate, select_for_escalation
from loopeng.triage.failures import CAUSES, TriagedFailure, summarise


def _run(item_id, *, ran=True, correct=False, termination="success", rejections=0):
    return {"item_id": item_id, "ran_and_returned": ran, "correct": correct,
            "termination": termination, "rejections": rejections, "pattern_key": "p"}


# ---- the confidence signal costs nothing ------------------------------------


def test_confidence_is_read_from_telemetry_not_from_another_model_call():
    """A model's stated confidence is another generation to be wrong about; a
    no_progress termination is a fact about what happened."""
    import inspect

    source = inspect.getsource(confidence_of)
    assert "client" not in source
    assert "messages" not in source


def test_a_clean_first_try_scores_highest():
    score, reason = confidence_of(_run("a"))
    assert score == CONFIDENCE["clean_first_try"]
    assert "first attempt" in reason


def test_a_run_that_needed_revision_scores_lower():
    assert confidence_of(_run("a", rejections=2))[0] < CONFIDENCE["clean_first_try"]


def test_giving_up_scores_lower_still():
    assert (confidence_of(_run("a", termination="no_progress"))[0]
            < confidence_of(_run("a", rejections=2))[0])


def test_a_run_that_never_returned_scores_zero():
    assert confidence_of(_run("a", ran=False))[0] == 0.0


def test_every_reason_is_plain_english_not_a_code():
    """Gate 4 requires a declined question visible WITH ITS REASON in plain English.

    "Plain English" means a sentence an operator can act on, not the enum name spelled
    out. It does NOT mean banning the words the enum happens to use — an explanation of
    a budget stop should be free to say "budget". So the check is that the reason is a
    real sentence and is never merely the identifier.
    """
    seen = set()
    for termination in ("success", "no_progress", "max_attempts", "budget"):
        _, reason = confidence_of(_run("a", termination=termination))
        assert len(reason.split()) >= 8, f"{termination}: too terse to act on"
        assert reason != termination
        assert reason != termination.replace("_", " ")
        assert "_" not in reason, f"{termination}: reads like an identifier"
        seen.add(reason)
    assert len(seen) == 4, "each branch needs its own explanation, not a shared one"


# ---- coverage is a CHOICE ---------------------------------------------------


def test_raising_the_threshold_lowers_coverage_and_raises_precision():
    """The trade that makes the tier finding actionable rather than an observation."""
    runs = [_run("a", correct=True), _run("b", correct=False, rejections=1),
            _run("c", correct=False, termination="no_progress")]
    low = operating_point(runs, 0.0)
    high = operating_point(runs, 1.0)
    assert high["n_answered"] < low["n_answered"]
    assert high["precision_value"] > low["precision_value"]


def test_coverage_and_precision_have_different_denominators():
    """Coverage is over everything asked; precision is over what was ANSWERED. Sharing
    a denominator would hide the trade entirely."""
    runs = [_run("a", correct=True), _run("b", termination="no_progress")]
    point = operating_point(runs, 1.0)
    assert point["n_total"] == 2
    assert point["n_answered"] == 1


def test_declining_everything_reports_precision_as_not_measured():
    """A precision over zero answers is not a precision."""
    runs = [_run("a", termination="no_progress")]
    point = operating_point(runs, 1.0)
    assert point["n_answered"] == 0
    assert point["precision"] == "not yet measured"


def test_the_curve_gives_the_operator_more_than_one_place_to_stand():
    runs = [_run("a", correct=True), _run("b", correct=False, rejections=1),
            _run("c", correct=False, termination="no_progress")]
    points = curve(runs)
    assert len({p["n_answered"] for p in points}) > 1


def test_a_declined_item_reports_no_correctness():
    """Whether a declined answer would have been right is not knowable to the
    operator at decision time, and recording it would invite scoring the decision
    against the answer key."""
    decision = decide(_run("a", correct=True, termination="no_progress"), 1.0)
    assert decision.declined
    assert decision.correct is None


# ---- escalation -------------------------------------------------------------


def test_escalation_is_capped_at_a_fixed_n_not_a_rate():
    """A fixed cap makes cost a ceiling; a rate makes it scale when abstention fires
    more often than expected."""
    runs = [_run(f"i{i}", termination="no_progress") for i in range(40)]
    selected, declined = select_for_escalation(runs, 1.0, limit=MAX_ESCALATIONS)
    assert declined == 40
    assert len(selected) == MAX_ESCALATIONS


def test_the_escalation_rate_is_reported_over_everything_declined():
    """Not over what the budget allowed — otherwise the cap would flatter the rate."""
    runs = [_run(f"i{i}", termination="no_progress") for i in range(40)]
    assert escalation_rate(runs, 1.0).n == 40
    assert escalation_rate(runs, 1.0).value == 1.0


def test_the_handoff_does_not_carry_the_declined_query():
    """Passing the shaky SQL forward would anchor the frontier model to it, and any
    improvement would then be partly ours rather than the model's."""
    import dataclasses

    from loopeng.triage.escalate import Handoff

    fields = {f.name for f in dataclasses.fields(Handoff)}
    assert "sql" not in fields
    assert fields == {"item_id", "question", "rules", "declined_because"}


# ---- triage by cause --------------------------------------------------------


def test_the_four_causes_need_four_different_fixes():
    assert set(CAUSES) == {"model", "gold", "question", "harness"}


def test_an_unknown_cause_is_rejected():
    with pytest.raises(ValueError):
        TriagedFailure("i", "arm", "vibes", "n", "m", "g")


def test_gold_defects_are_reported_even_when_there_are_none():
    """An absence stated is evidence; an absence omitted is nothing. The prior build
    found four."""
    report = summarise([TriagedFailure("i", "a", "model", "n", "m", "g")])
    assert report["gold_defects_found"] == 0
    assert "prior build found four" in report["gold_verdict"]


def test_gold_defects_are_called_out_when_present():
    report = summarise([TriagedFailure("i", "a", "gold", "n", "m", "g")])
    assert report["gold_defects_found"] == 1
    assert "poisons every comparison" in report["gold_verdict"]


# ---- escalation is implemented but not run, and the panel must say so --------


def test_nothing_in_the_repository_runs_escalation():
    """The guard on the claim the OVERSIGHT panel now makes.

    `run_escalation` was the function this module exists for, and it had no
    callers — no demo, no view, no test — so the artifact the escalation panels
    read could not be produced by any shipped entry point. The panels said "not
    yet measured", which claims a measurement is PENDING rather than absent.

    If escalation is ever wired up, this test fails and the panel text must be
    revisited in the same change. That is the point: the claim and the capability
    are now coupled.
    """
    import pathlib

    root = pathlib.Path(__file__).resolve().parent.parent
    hits = []
    for directory in ("src", "demos", "tools", "deploy"):
        for path in (root / directory).rglob("*.py"):
            for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if line.lstrip().startswith("#"):
                    continue
                if "run_escalation" in line:
                    hits.append(f"{path.relative_to(root)}:{n}")
    assert not hits, (
        f"escalation is now invoked at {hits} — update "
        f"views/oversight.py::NOT_SHIPPED_ESCALATION, which currently tells the "
        f"room escalation is not measured in this build"
    )


def test_the_escalation_panel_says_not_shipped_rather_than_not_yet_measured(tmp_path):
    from loopeng.views.oversight import _escalation_panel

    panel = _escalation_panel(tmp_path / "absent.json")
    assert "not measured in this build" in panel
    assert "not yet measured" not in panel


def test_the_escalation_policy_itself_is_still_implemented_and_tested():
    """Deleting the runner must not read as deleting the idea. Selection, the rate
    and the cap are all still here and still covered."""
    from loopeng.triage.escalate import (
        MAX_ESCALATIONS,
        Handoff,
        escalation_rate,
        select_for_escalation,
    )

    assert MAX_ESCALATIONS > 0
    assert callable(select_for_escalation) and callable(escalation_rate)
    assert Handoff is not None
