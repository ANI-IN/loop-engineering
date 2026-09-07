"""The four conditions: one implementation, selected by config.

The property that matters most here is that A is not a separate code path from C. The
loops are nested, so an unverified arm is the Level 1 loop with its attempt cap set and
a verified arm is the Level 2 loop around the same generator. A second path would be a
second place for the termination policy to drift, which is what the session is about.
"""

import pytest

from loopeng.gold.build import build_gold
from loopeng.sweep.conditions import (
    CONDITION_ORDER,
    CONDITIONS,
    UnknownCondition,
    condition_for,
    run_item,
    summarise_arm,
)
from loopeng.warehouse.connect import ensure_warehouse
from tests.fakes import FakeClient


@pytest.fixture(scope="module")
def warehouse(tmp_path_factory):
    return ensure_warehouse(tmp_path_factory.mktemp("wh") / "w.duckdb", seed=20260729)


@pytest.fixture(scope="module")
def items(warehouse):
    return build_gold(warehouse)


def _item(items, key):
    return next(i for i in items if i.pattern_key == key)


# ---- the four arms are what the session says they are ------------------------


def test_the_four_conditions_are_a_b_c_d():
    assert set(CONDITIONS) == {"A", "B", "C", "D"}
    assert CONDITION_ORDER == ("A", "B", "C", "D")


def test_only_the_reference_arm_uses_the_frontier_model():
    """"Everything the agent does runs on a budget model" is the argument. If a
    second arm escalated, C vs D would be measuring something else."""
    cheap = [c for c in CONDITIONS.values() if c.role == "agent"]
    assert {c.id for c in cheap} == {"A", "B", "C"}
    assert CONDITIONS["D"].role == "reference"


def test_the_reference_arm_is_bare():
    """It is the bar. A frontier model wrapped in the same loops would answer a
    different question."""
    assert CONDITIONS["D"].max_attempts == 1
    assert not CONDITIONS["D"].verified
    assert CONDITIONS["D"].loops == "none — single shot"


def test_only_c_carries_the_verifiers():
    """A -> B isolates retry; B -> C isolates verification. If B were verified the
    two comparisons would collapse into one."""
    assert [c.id for c in CONDITIONS.values() if c.verified] == ["C"]


def test_a_is_a_single_shot_and_b_is_not():
    assert CONDITIONS["A"].max_attempts == 1
    assert CONDITIONS["B"].max_attempts > 1
    assert CONDITIONS["A"].loops == "none — single shot"
    assert CONDITIONS["B"].loops == "L1 only"


def test_every_condition_says_what_it_is_for():
    for condition in CONDITIONS.values():
        assert condition.note and len(condition.note) > 40


def test_an_unknown_condition_raises_and_names_the_four():
    with pytest.raises(UnknownCondition) as caught:
        condition_for("E")
    assert "'A', 'B', 'C', 'D'" in str(caught.value).replace('"', "'")


# ---- one implementation, not four --------------------------------------------


def test_an_unverified_arm_never_reaches_the_verification_loop(items, warehouse):
    """A and B run the Level 1 loop. If they reached Level 2 they would be able to
    reject a query that RAN, which is the capability the comparison is measuring."""
    item = _item(items, "p01_product_count")
    client = FakeClient("agent", [item.gold_sql])
    _run, _judgement, rejections = run_item(CONDITIONS["A"], item, warehouse,
                                            client=client)
    assert rejections == 0


def test_a_verified_arm_can_send_back_a_query_that_ran(items, warehouse):
    """The whole of Level 2 in one assertion: a clean, executing query rejected for
    breaking a declared rule."""
    item = _item(items, "p02_orders_in_month")
    naive = item.naive_by_rule["soft_delete"]["sql"]
    client = FakeClient("agent", [naive, item.gold_sql])

    _run, _judgement, rejections = run_item(CONDITIONS["C"], item, warehouse,
                                            client=client)
    assert rejections >= 1, "a rule-breaking query that executed was accepted"


def test_the_attempt_cap_is_the_only_difference_between_a_and_b(items, warehouse):
    """One implementation. If A and B were separate paths this could not hold."""
    a, b = CONDITIONS["A"], CONDITIONS["B"]
    assert (a.role, a.verified) == (b.role, b.verified)
    assert a.max_attempts != b.max_attempts

    # Distinct failing queries, because repeating one trips `no_progress` at the
    # second attempt — correct behaviour, and it would hide whether the cap binds.
    replies = ["SELECT * FROM missing_a", "SELECT * FROM missing_b",
               "SELECT * FROM missing_c"]
    item = _item(items, "p01_product_count")
    for condition, expected in ((a, 1), (b, 3)):
        client = FakeClient("agent", replies)
        run_item(condition, item, warehouse, client=client)
        assert client.calls == expected, condition.id


# ---- the silent-error band is a first-class figure ---------------------------


def _row(item_id, outcome, cost=0.001, termination="success", rejections=0):
    return {"item_id": item_id, "outcome": outcome, "cost_usd": cost,
            "termination": termination, "rejections": rejections}


def test_the_arm_summary_reports_silent_errors_as_a_count_and_a_rate():
    """The count is what collapses visibly from A to C. A rate alone hides how many
    items that is, and the count is what a reader of the answers was exposed to."""
    arm = summarise_arm(CONDITIONS["A"], [
        _row("a", "correct"), _row("b", "silent_error"), _row("c", "silent_error"),
        _row("d", "visible_failure"),
    ])

    assert arm["n_silent_errors"] == 2
    assert "2 of 3" in arm["silent_error_rate"] or "66.7%" in arm["silent_error_rate"]
    assert arm["n_answered"] == 3, "visible failures are not in the denominator"


def test_accuracy_is_over_every_item_not_over_the_ones_that_answered():
    """An arm that declines half the set and is right about the rest has not scored
    100%, and a denominator that quietly shrinks flatters exactly the arm that
    declines most."""
    arm = summarise_arm(CONDITIONS["C"], [
        _row("a", "correct"),
        _row("b", "signalled_missing_information"),
        _row("c", "signalled_missing_information"),
        _row("d", "visible_failure"),
    ])
    assert arm["accuracy_value"] == pytest.approx(0.25)
    assert arm["n_abstained"] == 2


def test_every_band_is_carried_so_nothing_is_derived_downstream():
    from loopeng.agent.classify import BANDS

    arm = summarise_arm(CONDITIONS["A"], [_row("a", "correct")])
    assert set(arm["bands"]) == set(BANDS)
    assert sum(arm["bands"].values()) == arm["n_items"]


def test_an_unearned_correct_is_not_counted_as_accuracy():
    """Right, and the model could not have known it. Counting it as accuracy records
    a guess that landed as knowledge."""
    arm = summarise_arm(CONDITIONS["A"], [
        _row("a", "correct"), _row("b", "unearned_correct"),
    ])
    assert arm["accuracy_value"] == pytest.approx(0.5)
    assert arm["n_unearned_correct"] == 1
    assert arm["n_silent_errors"] == 0, "it is right; it is not a silent error"


def test_cost_per_correct_is_none_rather_than_infinite_when_nothing_is_right():
    """A division that cannot be done renders as "not yet measured", never as a
    number. Zero correct answers at any price is not an infinite cost, it is an
    undefined one."""
    arm = summarise_arm(CONDITIONS["A"], [_row("a", "silent_error")])
    assert arm["cost_per_correct_usd"] is None


def test_dollars_keep_the_estimated_source():
    arm = summarise_arm(CONDITIONS["A"], [_row("a", "correct", cost=0.01)])
    assert arm["cost_usd"]["source"] == "estimated"
    assert arm["cost_per_correct_usd"]["source"] == "estimated"


def test_termination_reasons_are_reported_by_name():
    """A policy branch nobody counts is a branch nobody knows fires."""
    arm = summarise_arm(CONDITIONS["B"], [
        _row("a", "correct", termination="success"),
        _row("b", "silent_error", termination="no_progress"),
        _row("c", "visible_failure", termination="max_attempts"),
    ])
    assert arm["termination"] == {"max_attempts": 1, "no_progress": 1, "success": 1}
