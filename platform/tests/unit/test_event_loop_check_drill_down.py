"""The Assignment 3: Event loop check's live step, zero tokens and no database: when the drill-down
run holds for approval, the check approves it, as an instructor would, waits for the posted answer,
and judges that posted answer against gold. A held answer is never judged, and a run that never
posts fails. The api here is a test double, in a unit test only; the check itself always runs
live against the real api."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from datapilot.assignments import assignment
from datapilot.assignments.report import Stop
from datapilot.assignments.runner import load_check
from datapilot.contracts import RunStatus
from datapilot.contracts.api import EventSubmitted, RunDetail

DRILL = {"event_id": "revenue-anomaly:2026-01-30:drill-down", "question": "Which category?"}
NOW = datetime(2026, 10, 23, tzinfo=UTC)


check = load_check(assignment("event-loop").check_file)  # loaded as the runner loads it
GOLD = "Water Sports"
TOP_LEVEL = ("Camping", "Hiking", "Apparel", "Footwear", "Climbing", "Water Sports")
NAMES = check.CategoryNames(TOP_LEVEL, ("Hiking Boots", "Kayaks", "Tents"))


RANKED_ROWS = [{"category": name, "rise_usd": 100.0 * n} for n, name in enumerate(TOP_LEVEL)]


def _envelope(text: str, rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {"answer_text": text, "rows_preview": rows or []}


class Api:
    """The api as the check sees it: submit, wait, run, and decide."""

    def __init__(
        self,
        *,
        hold: bool,
        held_text: str = "",
        rows: list[dict[str, Any]] | None = None,
        posted_text: str | None = None,
        end: RunStatus = RunStatus.POSTED,
        absorbed: bool = True,
        planted: list[str] | None = None,
        events: list[dict[str, Any]] | None = None,
    ) -> None:
        self.events = events or []
        self.rows = rows
        self.run_id = uuid.uuid4()
        self.hold, self.held_text, self.posted_text = hold, held_text, posted_text
        self.end, self.absorbed = end, absorbed
        self.planted = planted or []
        self.asks = 0
        self.decisions: list[str] = []

    def submit(self, type: str, payload: dict[str, Any], event: str) -> EventSubmitted:
        self.asks += 1
        again = self.asks > 1
        return EventSubmitted(
            event_id=event,
            run_id=self.run_id if self.absorbed or not again else uuid.uuid4(),
            job_id=None,
            duplicate=again and self.absorbed,
            duplicates_ignored=0,
            created_at=NOW,
        )

    def _detail(self, status: RunStatus, *, open_approval: bool) -> dict[str, Any]:
        approvals = []
        if self.hold:
            decided = None if open_approval else (self.decisions or [None])[-1]
            approvals.append(
                {
                    "approval_id": 1,
                    "kind": "held_answer",
                    "requested_at": NOW,
                    "action": f"post the answer: {self.held_text}",
                    "sql": None,
                    "row_estimate": None,
                    "reason": "the reviewer held the answer",
                    "decision": decided,
                    "decided_by": None if decided is None else "make check-assignment",
                    "decided_at": None if decided is None else NOW,
                    "comment": None,
                }
            )
        posts = []
        if status is RunStatus.POSTED and self.posted_text is not None:
            posts.append(
                {
                    "post_id": 7,
                    "channel": "analytics",
                    "label": "unverified",
                    "body": {
                        "answer": _envelope(self.posted_text, self.rows),
                        "level": "report_only",
                    },
                    "posted_at": NOW,
                }
            )
        answer_text = self.posted_text if status is RunStatus.POSTED else self.held_text
        return {
            "run_id": self.run_id,
            "event_id": DRILL["event_id"],
            "session_id": None,
            "demo_name": None,
            "question": DRILL["question"],
            "metric_family": "revenue",
            "status": status,
            "autonomy_level_applied": None,
            "knowledge_version": "v1",
            "model": "the class model",
            "planted_active": self.planted,
            "tokens_in": 0,
            "tokens_out": 0,
            "cost_usd": 0.0,
            "langsmith_url": None,
            "answer": {"envelope": _envelope(answer_text or "")},
            "created_at": NOW,
            "started_at": NOW,
            "finished_at": NOW,
            "duplicates_ignored": 0,
            "live_stamp": None,
            "events": self.events,
            "approvals": approvals,
            "posts": posts,
        }

    def _now(self) -> RunDetail:
        if self.hold and not self.decisions:
            status, open_approval = RunStatus.AWAITING_APPROVAL, True
        else:
            status, open_approval = self.end, False
        return RunDetail.model_validate(self._detail(status, open_approval=open_approval))

    def wait(self, run_id: str, *, seconds: float = 600, until: Any = None) -> RunDetail:
        assert run_id == str(self.run_id)
        return self._now()

    def run(self, run_id: str) -> RunDetail:
        return self._now()

    def decide(self, run_id: str, decision: str, comment: str = "") -> None:
        assert run_id == str(self.run_id)
        self.decisions.append(decision)


def test_a_held_answer_is_approved_and_the_posted_answer_is_judged() -> None:
    api = Api(hold=True, held_text="Water Sports led the rise", posted_text="Water Sports led it")
    outcome = check.drill_down(api, DRILL, GOLD, NAMES)
    assert api.decisions == ["approve"]
    assert outcome.passed
    assert "approved by the check" in outcome.what()
    assert outcome.fix() == ""


def test_a_held_answer_naming_gold_does_not_count_when_the_post_does_not() -> None:
    api = Api(hold=True, held_text="Water Sports led the rise", posted_text="Footwear led it")
    outcome = check.drill_down(api, DRILL, GOLD, NAMES)
    assert api.decisions == ["approve"]
    assert not outcome.passed
    assert "posted answer says Footwear rose most (its text)" in outcome.what()


@pytest.mark.parametrize("end", [RunStatus.REJECTED, RunStatus.FAILED, RunStatus.ESCALATED])
def test_a_run_that_never_posts_fails(end: RunStatus) -> None:
    api = Api(hold=True, held_text="Water Sports led the rise", end=end)
    outcome = check.drill_down(api, DRILL, GOLD, NAMES)
    assert api.decisions == ["approve"]
    assert not outcome.passed
    assert f"never posted (status {end.value})" in outcome.what()
    assert "post" in outcome.fix()


def _event(n: int, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {"id": n, "ts": NOW, "kind": kind, "payload": payload}


def test_an_escalated_run_names_why_it_ended_and_the_fix_names_the_question() -> None:
    """The 25 October 2026 failures printed only "never posted (status escalated)": the output
    now names the stop reason and what made the run retry, from the run's own events."""
    events = [
        _event(1, "grader_result", {"grader": "final_answer", "severity": "block"}),
        _event(2, "grader_result", {"grader": "final_answer", "severity": "block"}),
        _event(3, "grader_result", {"grader": "execution", "severity": "info"}),
        _event(4, "reviewer_verdict", {"outcome": "concern", "reasons": ["discounts"]}),
        _event(
            5,
            "status_changed",
            {"from": "running", "to": "escalated", "reasons": ["token budget of 60000 reached"]},
        ),
    ]
    api = Api(hold=False, end=RunStatus.ESCALATED, events=events)
    outcome = check.drill_down(api, DRILL, GOLD, NAMES)
    assert not outcome.passed
    assert (
        "never posted (status escalated: token budget of 60000 reached, final_answer blocked 2 "
        "times, the reviewer raised 1 concern)" in outcome.what()
    )
    assert "budgets.tokens_per_run" in outcome.fix()
    assert "never a change in percent" in outcome.fix()


def test_a_run_that_never_posts_without_events_says_only_its_status() -> None:
    api = Api(hold=False, end=RunStatus.FAILED)
    outcome = check.drill_down(api, DRILL, GOLD, NAMES)
    assert "never posted (status failed);" in outcome.what()
    assert "open its run in the console" in outcome.fix()


def test_an_answer_posted_without_a_hold_is_judged_as_posted() -> None:
    api = Api(hold=False, posted_text="Water Sports led it")
    outcome = check.drill_down(api, DRILL, GOLD, NAMES)
    assert api.decisions == []
    assert outcome.passed
    assert "approved by the check" not in outcome.what()
    assert "no approval was needed" in outcome.what()


def test_a_second_ask_that_starts_another_run_fails() -> None:
    api = Api(hold=False, posted_text="Water Sports led it", absorbed=False)
    outcome = check.drill_down(api, DRILL, GOLD, NAMES)
    assert not outcome.passed
    assert "deterministic event id" in outcome.fix()


def test_a_run_with_a_planted_bug_on_stops_the_check_before_the_second_ask() -> None:
    """The missing idempotency on the stack starts a second run for the second ask: that is the
    stack, not the solution, so the check stops (exit 2) instead of failing requirement 10."""
    flags = ["BUG_NO_IDEMPOTENCY"]
    api = Api(hold=False, posted_text="Water Sports led it", absorbed=False, planted=flags)
    with pytest.raises(Stop, match="BUG_NO_IDEMPOTENCY"):
        check.drill_down(api, DRILL, GOLD, NAMES)
    assert api.asks == 1


def test_an_answer_naming_the_wrong_category_fails_though_its_rows_hold_gold() -> None:
    """Rows without the question's rise_cents column are never judged: a ranking of every
    category holds gold in its rows whatever the text names."""
    api = Api(hold=False, posted_text="Camping rose the most yesterday.", rows=RANKED_ROWS)
    outcome = check.drill_down(api, DRILL, GOLD, NAMES)
    assert not outcome.passed
    assert "posted answer says Camping rose most (its text)" in outcome.what()
    silent = Api(hold=False, posted_text="Sales rose sharply yesterday.", rows=RANKED_ROWS)
    assert "posted answer did not name it" in check.drill_down(silent, DRILL, GOLD, NAMES).what()


def test_a_ranking_that_names_another_category_first_fails() -> None:
    text = (
        "Camping rose the most, by $4,100; then Water Sports, Hiking, Footwear, Apparel and "
        "Climbing."
    )
    api = Api(hold=False, posted_text=text, rows=RANKED_ROWS)
    outcome = check.drill_down(api, DRILL, GOLD, NAMES)
    assert not outcome.passed
    assert "says Camping rose most (its text), not the gold category" in outcome.what()
    assert "which top-level category's sales rose most" in outcome.fix()


def test_a_ranking_with_gold_first_passes() -> None:
    text = "Water Sports rose the most, by $41,000, ahead of Camping and Hiking."
    api = Api(hold=False, posted_text=text, rows=RANKED_ROWS)
    outcome = check.drill_down(api, DRILL, GOLD, NAMES)
    assert outcome.passed, outcome.what()
    assert "the posted answer says it rose most (its text)" in outcome.what()


def test_a_subcategory_holding_a_top_level_name_is_not_that_category() -> None:
    """A Footwear subcategory, Hiking Boots, is never a mention of the Hiking category."""
    named = check.categories_named("Hiking Boots sold well; Water Sports rose most", NAMES, GOLD)
    assert named == ["Water Sports"]


# --- the category the answer says rose most (session 6 review, round 2) ---------------------
@pytest.mark.parametrize(
    ("text", "said"),
    [
        ("Footwear fell the most; Water Sports rose most.", "Water Sports"),
        ("Not Footwear: Water Sports rose most.", "Water Sports"),
        ("Camping fell; Water Sports rose the most.", "Water Sports"),
        ("Unlike Footwear, Water Sports rose most.", "Water Sports"),
        ("Water Sports fell the most; Footwear rose most.", "Footwear"),
        ("Not Water Sports: Camping rose most.", "Camping"),
        ("Water Sports and Camping both sold.", "Water Sports"),  # no rise said: the first named
    ],
)
def test_the_text_is_judged_by_the_category_it_says_rose_most(text: str, said: str) -> None:
    """The review's probes: the first category named decided, so a falling or negated first
    mention passed a wrong answer and failed a right one."""
    assert check.rose_most(text, NAMES, GOLD) == said
    api = Api(hold=False, posted_text=text)
    assert check.drill_down(api, DRILL, GOLD, NAMES).passed is (said == GOLD)


def _rise_rows(*rises: tuple[str, int]) -> list[dict[str, Any]]:
    return [{"category": name, "rise_cents": rise} for name, rise in rises]


def test_the_answers_own_row_decides_when_it_returns_rise_cents() -> None:
    gold_top = _rise_rows(("Camping", 410_000), ("Water Sports", 3_312_000))
    text = "Camping rose, and Water Sports rose the most."
    outcome = check.drill_down(Api(hold=False, posted_text=text, rows=gold_top), DRILL, GOLD, NAMES)
    assert outcome.passed and "(its row)" in outcome.what()
    other_top = _rise_rows(("Camping", 3_312_000), ("Water Sports", 410_000))
    outcome = check.drill_down(
        Api(hold=False, posted_text=text, rows=other_top), DRILL, GOLD, NAMES
    )
    assert not outcome.passed
    assert "says Camping rose most (its row)" in outcome.what()


def test_a_row_naming_gold_still_needs_the_text_to_name_it() -> None:
    rows = _rise_rows(("Water Sports", 3_312_000))
    api = Api(hold=False, posted_text="The top category rose by $33,120.00.", rows=rows)
    assert not check.drill_down(api, DRILL, GOLD, NAMES).passed


def test_a_row_given_as_columns_and_values_is_read_too() -> None:
    answer = {
        "columns": ["category", "sales_cents", "average_cents", "rise_cents"],
        "rows_preview": [["Water Sports", 4_112_000, 800_000, "3312000.00"], ["Camping", 1, 2, 9]],
    }
    assert check.row_category(answer, NAMES, GOLD) == "Water Sports"
    assert (
        check.row_category({"columns": ["category"], "rows_preview": [["x"]]}, NAMES, GOLD) is None
    )


def test_the_check_never_rejects() -> None:
    source = assignment("event-loop").check_file.read_text(encoding="utf-8")
    assert "reject_all" not in source


# --- the text judge reads what each phrase is said of (session 6 review, round 3) -----------
@pytest.mark.parametrize(
    ("text", "said"),
    [
        # the review's two probes: the category nearest "most" by characters was Camping
        ("Water Sports rose the most, well ahead of Camping.", "Water Sports"),
        (
            "Among top-level categories, Camping trailed while Water Sports rose most.",
            "Water Sports",
        ),
        ("Water Sports saw the biggest increase, about $9,000 more than Camping.", "Water Sports"),
        ("Water Sports had the largest rise, at $12,345.67.", "Water Sports"),
        ("Water Sports rose most; Camping did not change.", "Water Sports"),
        # the wording of the failed capture (alternative-one-run-1.txt): a wrong answer
        ("Hiking rose most.", "Hiking"),
        # plain right and wrong answers
        ("Water Sports rose the most yesterday, by $33,120.00.", "Water Sports"),
        ("Camping rose the most yesterday, by $4,100.00.", "Camping"),
        ("The largest rise was in Water Sports, ahead of Camping.", "Water Sports"),
        ("The top category: Water Sports, up $33,120.00.", "Water Sports"),
        ("Water Sports, not Camping, rose the most.", "Water Sports"),
        ("Camping did not rise the most; Water Sports did.", "Water Sports"),
        # "top-level" is never "top": the top category here is the one said to rise most
        ("Of the top-level categories, Water Sports was the top category.", "Water Sports"),
        ("Camping is a top-level category; Water Sports rose most.", "Water Sports"),
    ],
)
def test_the_rise_belongs_to_the_category_it_is_said_of(text: str, said: str) -> None:
    assert check.rose_most(text, NAMES, GOLD) == said
    outcome = check.drill_down(Api(hold=False, posted_text=text), DRILL, GOLD, NAMES)
    assert outcome.passed is (said == GOLD), outcome.what()
    if said != GOLD:
        assert f"says {said} rose most (its text), not the gold category" in outcome.what()


def test_top_is_matched_as_a_whole_word_only() -> None:
    """The word "top" inside "top-level" is not "top": the earlier pattern matched it."""
    assert check.SAID_MOST.search("Among top-level categories, sales were flat") is None
    assert check.SAID_MOST.search("the top category") is not None


@pytest.mark.parametrize(
    ("text", "could_mean"),
    [
        ("Water Sports and Camping rose the most.", ("Water Sports", "Camping")),
        ("Water Sports rose the most. Camping had the largest rise.", ("Water Sports", "Camping")),
        ("Camping rose, and Water Sports rose too.", ("Camping", "Water Sports")),
    ],
)
def test_an_ambiguous_text_names_no_category_and_fails_with_its_reason(
    text: str, could_mean: tuple[str, ...]
) -> None:
    """The check refuses to guess: a text that says several categories rose most names none,
    so it fails requirement 10 even when gold is among them, and says why."""
    reading = check.read_rise(text, NAMES, GOLD)
    assert reading.category is None and reading.ambiguous
    assert reading.could_mean == could_mean
    assert check.rose_most(text, NAMES, GOLD) is None
    outcome = check.drill_down(Api(hold=False, posted_text=text), DRILL, GOLD, NAMES)
    assert not outcome.passed
    assert "does not say which one category rose most" in outcome.what()
    assert " or ".join(could_mean) in outcome.what()
    assert "name one top-level category" in outcome.fix()


def test_an_ambiguous_text_is_still_judged_by_its_rise_cents_row() -> None:
    """The row path is unchanged: the answer's own top row decides when it returns rise_cents."""
    rows = _rise_rows(("Camping", 410_000), ("Water Sports", 3_312_000))
    text = "Water Sports and Camping rose the most."
    outcome = check.drill_down(Api(hold=False, posted_text=text, rows=rows), DRILL, GOLD, NAMES)
    assert outcome.passed and "(its row)" in outcome.what()


# --- the session 6 review, round 3: code, security and tests ---------------------------------
FOOTWEAR_NAMES = check.CategoryNames(("Footwear", "Outdoor", "Apparel"), ("Hiking Boots",))


@pytest.mark.parametrize(
    ("text", "said"),
    [
        # the review's probe: "most" is nearer Outdoor by characters, but Footwear is the subject
        ("Footwear rose the most, ahead of Outdoor.", "Footwear"),
        ("Sales rose in every category; Outdoor led, Footwear was second.", "Outdoor"),
        ("The largest rise was in Outdoor (+$120), while Footwear grew by $80.", "Outdoor"),
    ],
)
def test_the_text_fallback_judges_the_subject_of_the_rise(text: str, said: str) -> None:
    assert check.rose_most(text, FOOTWEAR_NAMES, "Footwear") == said
    outcome = check.drill_down(Api(hold=False, posted_text=text), DRILL, "Footwear", FOOTWEAR_NAMES)
    assert outcome.passed is (said == "Footwear"), outcome.what()


def test_a_gold_row_fails_when_the_text_says_another_category_rose_most() -> None:
    """The review: with a gold top row, any text naming gold passed, even one that says another
    category rose most. The text must not contradict the row (SPEC.md, requirement 10: the answer
    names the category whose sales rose most)."""
    rows = _rise_rows(("Water Sports", 3_312_000), ("Camping", 410_000))
    text = "Camping rose the most; Water Sports was second."
    outcome = check.drill_down(Api(hold=False, posted_text=text, rows=rows), DRILL, GOLD, NAMES)
    assert outcome.contradicted == "Camping"
    assert not outcome.passed
    assert "row says Water Sports rose most, but its text says Camping rose most" in outcome.what()
    assert "never another one" in outcome.fix()
    # The same row with a text that agrees, or one that says no single category rose most, passes.
    for agrees in ("Water Sports rose the most; Camping was second.", "Water Sports rose."):
        api = Api(hold=False, posted_text=agrees, rows=rows)
        assert check.drill_down(api, DRILL, GOLD, NAMES).passed, agrees
    # A text that only names a category first, never saying it rose most, never contradicts.
    first_named = "Camping and Water Sports sold well; see the rows."
    outcome = check.drill_down(
        Api(hold=False, posted_text=first_named, rows=rows), DRILL, GOLD, NAMES
    )
    assert outcome.contradicted is None and outcome.passed
