"""`verify/failure_paths.py` — the three ways a Level 2 run ends without succeeding.

At 0% coverage before this file existed. The module's own docstring explains why
part of it must stay that way: all three scenarios make **real model calls** on
purpose, because "a scripted client would only prove that the scripted client
works". `run_scenario` is therefore left to the live path, deliberately.

What is covered here is everything that is pure: the two stand-in verifiers that
provoke each branch, and the scenario table itself. Those carry the actual claims
— that one verifier repeats its complaint and the other never does, and that the
three scenarios are configured to trigger three *different* terminations — and
none of them needs a key or a network to check.

The distinction matters. "This module is untested" and "this module's live half is
untestable offline, and its pure half is tested" are different statements, and only
the second one is true now.
"""

import pytest

from loopeng.contracts import VerifyContext
from loopeng.verify.failure_paths import (
    SCENARIOS,
    rejects_with_a_new_complaint,
    rejects_with_one_complaint,
)


def context(attempt: int) -> VerifyContext:
    return VerifyContext(
        question="(scenario)", sql="SELECT 1", schema_ddl="", rules=("soft_delete",),
        attempt=attempt, execution_rows=((1,),), execution_error=None,
    )


# ---- the two stand-in verifiers ----------------------------------------------


def test_both_stand_ins_reject_everything():
    """An over-strict rule check is a real failure mode, not a contrived one — it is
    the mirror of the regex verifier that accepts too much."""
    for verifier in (rejects_with_one_complaint, rejects_with_a_new_complaint):
        for attempt in (1, 2, 3):
            assert not verifier(context(attempt)).ok


def test_the_repeating_verifier_says_the_same_thing_every_time():
    """Which is what the no-progress detector keys on: identical feedback twice means
    the loop is going in circles, and three more attempts will not discover that."""
    feedback = {rejects_with_one_complaint(context(n)).feedback() for n in (1, 2, 3)}
    assert len(feedback) == 1


def test_the_escalating_verifier_never_repeats_itself():
    """The inverse, and it is what keeps the no-progress detector QUIET so the attempt
    cap is what stops the run. If these two ever produced the same feedback, two of
    the three scenarios would be exercising one branch."""
    feedback = [rejects_with_a_new_complaint(context(n)).feedback() for n in (1, 2, 3)]
    assert len(set(feedback)) == len(feedback)


def test_the_escalating_complaint_names_the_attempt_it_came_from():
    assert "attempt 2" in rejects_with_a_new_complaint(context(2)).feedback()


def test_neither_stand_in_leaks_a_result_value():
    """The rule every verifier in this repo is held to: feedback goes straight back
    into the prompt, so anything derived from the rows is a channel for the answer."""
    marker = 8675309
    for verifier in (rejects_with_one_complaint, rejects_with_a_new_complaint):
        leaky = VerifyContext(
            question="(scenario)", sql="SELECT 1", schema_ddl="", rules=("soft_delete",),
            attempt=1, execution_rows=((marker,),), execution_error=None,
        )
        assert str(marker) not in verifier(leaky).feedback()


# ---- the scenario table ------------------------------------------------------


def test_there_are_three_scenarios_and_they_expect_three_different_endings():
    """The whole point is one scenario per branch. Two that terminate the same way
    would leave a branch unwatched while looking like coverage."""
    assert len(SCENARIOS) == 3
    assert len({s.expect for s in SCENARIOS}) == 3


def test_every_scenario_key_matches_the_termination_it_expects():
    for scenario in SCENARIOS:
        assert scenario.key == scenario.expect


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.key)
def test_every_scenario_explains_why_it_ends_that_way(scenario):
    assert scenario.why.strip()
    assert scenario.max_attempts >= 1
    assert scenario.budget_usd > 0


def test_the_budget_scenario_is_configured_to_hit_cost_before_attempts():
    """Its cap must be reachable before the attempt cap, or it would terminate as
    `max_attempts` and silently duplicate the first scenario."""
    budget = next(s for s in SCENARIOS if s.key == "budget")
    max_attempts = next(s for s in SCENARIOS if s.key == "max_attempts")
    assert budget.budget_usd < max_attempts.budget_usd
    assert budget.max_attempts > max_attempts.max_attempts


def test_the_no_progress_scenario_is_the_only_one_using_the_repeating_verifier():
    """`no_progress` fires on repeated feedback; the other two must not, or the
    detector would stop them before their own cap did."""
    by_key = {s.key: s.verifier for s in SCENARIOS}
    assert by_key["no_progress"] is rejects_with_one_complaint
    assert by_key["max_attempts"] is rejects_with_a_new_complaint
    assert by_key["budget"] is rejects_with_a_new_complaint
