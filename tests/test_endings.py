"""The three pre-committed readings, and the arithmetic that picks between them.

The point of committing three endings in advance is that the selection stops being a
judgement made while looking at a chart. That only holds if the selection is a function
— so these tests are about the function being decidable, ordered, and unable to score an
abstention as a failure.
"""

import json
from pathlib import Path

import pytest

from loopeng.sweep.endings import Ending, select

REPO_ROOT = Path(__file__).resolve().parent.parent


def arm(**outcomes) -> dict:
    """An arm as the conditions runner writes one: `{item_id: outcome}`."""
    return {"items": [{"item_id": item, "outcome": outcome}
                      for item, outcome in outcomes.items()]}


def test_no_gap_to_close_is_checked_FIRST():
    """The reading most easily dropped, so it is decided before the others.

    It makes the comparison uninteresting rather than lost, and a finding nobody wants
    to present is a finding that quietly does not get presented. If the frontier model
    bare is not ahead, both other readings are claims about a distance that does not
    exist.
    """
    everyone_the_same = dict(i1="correct", i2="silent_error", i3="correct")
    selection = select(
        cheap_bare=arm(**everyone_the_same),
        cheap_looped=arm(i1="correct", i2="correct", i3="correct"),
        frontier_bare=arm(**everyone_the_same),
    )
    assert selection.ending is Ending.NO_GAP_TO_CLOSE
    assert selection.gap_existed is False
    # Even though the looped arm beat the frontier outright, which would otherwise read
    # as "reached" — a claim about closing a gap there was none of.
    assert selection.only_cheap > selection.only_frontier


def test_reached_needs_a_gap_AND_no_deficit():
    selection = select(
        cheap_bare=arm(i1="silent_error", i2="silent_error", i3="correct"),
        cheap_looped=arm(i1="correct", i2="correct", i3="correct"),
        frontier_bare=arm(i1="correct", i2="correct", i3="correct"),
    )
    assert selection.ending is Ending.REACHED
    assert selection.gap_existed is True
    assert selection.only_frontier == 0


def test_approached_but_short_when_the_deficit_survives_the_loops():
    selection = select(
        cheap_bare=arm(i1="silent_error", i2="silent_error", i3="silent_error"),
        cheap_looped=arm(i1="correct", i2="silent_error", i3="silent_error"),
        frontier_bare=arm(i1="correct", i2="correct", i3="correct"),
    )
    assert selection.ending is Ending.APPROACHED_BUT_SHORT
    assert (selection.only_frontier, selection.only_cheap) == (2, 0)


def test_a_declined_item_is_excluded_from_the_pairing_not_scored_wrong():
    """Counting an abstention as a failure would rank a model that knew what it was
    missing below one that invented a number — the mistake this project spent an
    outcome category fixing. The reference arm at L0 declined nineteen items."""
    selection = select(
        cheap_bare=arm(i1="silent_error", i2="silent_error"),
        cheap_looped=arm(i1="correct", i2="correct"),
        frontier_bare=arm(i1="correct", i2="signalled_missing_information"),
    )
    assert selection.n_paired == 1, "the declined item is not a pair"
    assert selection.only_cheap == 0 and selection.only_frontier == 0


def test_a_visible_failure_is_also_not_a_pair():
    """It did not produce an answer, so it is not evidence about which arm answers
    better. It IS evidence, and it belongs in the visible band where a reader can see
    it — not smuggled into a correctness comparison as a loss."""
    selection = select(
        cheap_bare=arm(i1="silent_error", i2="silent_error"),
        cheap_looped=arm(i1="correct", i2="visible_failure"),
        frontier_bare=arm(i1="correct", i2="correct"),
    )
    assert selection.n_paired == 1


def test_every_ending_renders_its_own_basis():
    """Never a bare verdict. The reading is what gets said out loud, so the numbers it
    rests on travel with it rather than living on a slide two along."""
    for ending, arms in (
        (Ending.NO_GAP_TO_CLOSE, dict(
            cheap_bare=arm(i1="correct"), cheap_looped=arm(i1="correct"),
            frontier_bare=arm(i1="correct"))),
        (Ending.REACHED, dict(
            cheap_bare=arm(i1="silent_error"), cheap_looped=arm(i1="correct"),
            frontier_bare=arm(i1="correct"))),
        (Ending.APPROACHED_BUT_SHORT, dict(
            cheap_bare=arm(i1="silent_error", i2="silent_error"),
            cheap_looped=arm(i1="silent_error", i2="silent_error"),
            frontier_bare=arm(i1="correct", i2="correct"))),
    ):
        selection = select(**arms)
        assert selection.ending is ending
        rendered = selection.render()
        assert str(selection.n_paired) in rendered or "paired" in rendered
        if ending is not Ending.NO_GAP_TO_CLOSE:
            assert "No p-value" in rendered, (
                "a cross-model reading must carry the refusal it is subject to"
            )


def test_the_pilot_selection_matches_what_the_note_records():
    """`docs/three-endings.md` states which ending the pilot data selects, dated, before
    the rehearsal — so a different reading on the day is a visible change rather than a
    quiet one. That only means anything if the note and the arithmetic agree TODAY."""
    directory = REPO_ROOT / "results" / "experiments"
    arms = {name: json.loads((directory / f"{name}.json").read_text())
            for name in ("A-baseline", "C-verified", "D-reference")}
    selection = select(cheap_bare=arms["A-baseline"],
                       cheap_looped=arms["C-verified"],
                       frontier_bare=arms["D-reference"])

    # Whitespace collapsed before matching, the same convention `tests/figures.py`
    # settled on for chart text: prose wraps at a column, so a phrase can be split
    # mid-assertion and an assertion written against the sentence fails on a document
    # that contains it and renders it correctly. That coupling has cost this build four
    # test fixes already.
    note = " ".join(
        (REPO_ROOT / "docs" / "three-endings.md").read_text(encoding="utf-8").split()
    )
    assert selection.ending is Ending.APPROACHED_BUT_SHORT
    assert "selects **approached but short**" in note
    # Every count the note quotes, checked against the ones the function computes.
    raw_gap = selection.frontier_correct - selection.cheap_correct
    deficit = selection.only_frontier - selection.only_cheap
    assert f"{selection.cheap_correct} correct against {selection.frontier_correct}" in note
    assert f"a gap of {raw_gap}" in note
    assert f"the {selection.n_paired} items **both arms answered**" in note
    assert f"**{deficit} discordant items**, not {raw_gap}" in note
    assert f"other {raw_gap - deficit} are items the looped arm did not answer" in note


def test_the_reading_states_the_verdict_BEFORE_the_decomposition():
    """Both, and the order is load-bearing in both directions.

    Leading with the decomposition is the post-hoc reframing the pre-commitment exists
    to prevent — a kinder description chosen after seeing the result. Stopping at the
    verdict understates it, because the raw gap and the paired deficit are different
    sizes and the difference between them is a different KIND of failure.
    """
    rendered = select(
        cheap_bare=arm(i1="silent_error", i2="silent_error", i3="silent_error"),
        cheap_looped=arm(i1="correct", i2="silent_error", i3="visible_failure"),
        frontier_bare=arm(i1="correct", i2="correct", i3="correct"),
    ).render()

    assert rendered.index("APPROACHED BUT SHORT") < rendered.index("BY ACCURACY")
    assert rendered.index("BY ACCURACY") < rendered.index("DECOMPOSED")
    assert "different failure from being wrong" in rendered


@pytest.mark.parametrize("ending", list(Ending))
def test_every_ending_is_named_in_the_note(ending):
    """A reading the note does not describe is a reading nobody committed to."""
    note = (REPO_ROOT / "docs" / "three-endings.md").read_text(encoding="utf-8")
    assert ending.value.replace("_", " ") in note.lower()
