"""Assignment 3: Event loop, the drill-down question, zero tokens and no database.

On 25 October 2026 the reference's drill-down run ended escalated at its token budget in 2 of 8
live checks. The question then asked which top-level category's net revenue "changed the most":
net revenue is an order-level rule that the starting knowledge does not hold for category lines,
and the natural answers to a change, a percent above 100 or a revenue change that is negative for
most categories, are blocked by the class's final-answer grader, so the run retried until the
budget ended it. These tests pin both sides with the real grader, and pin each solution's question
to the answerable wording that SPEC.md requirement 10 now asks for.
"""

from __future__ import annotations

import sys
from datetime import date
from types import ModuleType

import pytest

from datapilot.assignments import VARIANTS, WITHHELD_REASON, assignment, solutions_withheld
from datapilot.contracts import AnswerEnvelope, AnswerStatus, GraderContext, QueryResult, Severity
from datapilot.loop2_verification.graders.final_answer import FinalAnswerGrader

DAY = date(2026, 1, 30)
EXTENSION = "platform/src/datapilot/loop3_events/extension.py"
EARLIER = (
    "Which top-level product category's net revenue changed the most on 30 January 2026, in "
    "Eastern time, compared with the average of the same weekday in the four weeks before?"
)
SQL = "SELECT 1"


def _solution(variant: str) -> ModuleType:
    """The solution's extension module, run from its source, so no bytecode cache is written into
    the solution's files/ folder (a solution's files are only the ones it replaces)."""
    path = assignment("event-loop").solution(variant) / "files" / EXTENSION
    name = f"event_loop_{variant.replace('-', '_')}"
    module = ModuleType(name)
    module.__file__ = str(path)
    sys.modules[name] = module  # its dataclasses look their module up while it loads
    try:
        exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), module.__dict__)
    finally:
        del sys.modules[name]
    return module


def _grade(question: str, columns: list[str], rows: list[tuple], text: str):
    result = QueryResult(columns, rows, total_row_count=len(rows), truncated=False)
    answer = AnswerEnvelope(status=AnswerStatus.ANSWERED, final_sql=SQL, answer_text=text)
    return FinalAnswerGrader().check(
        GraderContext(question=question, sql=SQL, result=result, answer=answer)
    )


# --- why the earlier wording escalated ----------------------------------------------------------
def test_a_revenue_change_for_every_category_is_blocked() -> None:
    rows = [("Water Sports", 3_312_000), ("Footwear", -41_250), ("Camping", -12_900)]
    verdict = _grade(
        EARLIER,
        ["category", "net_revenue_change_cents"],
        rows,
        "Water Sports changed the most, by $33,120.00.",
    )
    assert verdict.severity is Severity.BLOCK
    assert "negative revenue" in verdict.reason


def test_a_change_in_percent_above_100_is_blocked() -> None:
    verdict = _grade(
        EARLIER,
        ["category", "pct_change"],
        [("Water Sports", 412.5)],
        "Water Sports changed the most, up 412.5 percent.",
    )
    assert verdict.severity is Severity.BLOCK
    assert "percentages outside 0 to 100" in verdict.reason


# --- the answerable wording -----------------------------------------------------------------------
@pytest.mark.skipif(solutions_withheld(), reason=WITHHELD_REASON)
@pytest.mark.parametrize("variant", VARIANTS)
def test_each_solution_asks_the_answerable_question(variant: str) -> None:
    question = _solution(variant).drill_down_question(DAY)
    for part in (
        "top-level",
        "rose the most",
        "30 January 2026",
        "Eastern time",
        "same weekday in the four weeks before",
        "quantity times unit price on its order lines",
        "in dollars",
        "Return only the top category's row",
        "a column named rise_cents",
    ):
        assert part in question, part
    for word in ("net revenue", "percent", "changed"):
        assert word not in question.lower(), word


@pytest.mark.skipif(solutions_withheld(), reason=WITHHELD_REASON)
def test_every_solution_asks_the_same_question() -> None:
    asked = {_solution(variant).drill_down_question(DAY) for variant in VARIANTS}
    assert len(asked) == 1


@pytest.mark.skipif(solutions_withheld(), reason=WITHHELD_REASON)
def test_the_answer_the_question_asks_for_passes_the_grader() -> None:
    question = _solution("reference").drill_down_question(DAY)
    verdict = _grade(
        question,
        ["category", "sales_cents", "average_cents", "rise_cents"],
        [("Water Sports", 4_112_000, 800_000, 3_312_000)],
        "Water Sports rose the most: $41,120.00 of sales, $33,120.00 above its average of "
        "$8,000.00.",
    )
    assert verdict.passed, verdict.reason


EVERY_CATEGORY = [  # the other categories fell on the anomalous day: negative rises
    ("Water Sports", 4_112_000, 800_000, 3_312_000),
    ("Footwear", 158_750, 200_000, -41_250),
    ("Camping", 87_100, 100_000, -12_900),
]
TEXT = "Water Sports rose the most, $33,120.00 above its average."


@pytest.mark.skipif(solutions_withheld(), reason=WITHHELD_REASON)
def test_a_result_of_every_category_passes_under_the_column_the_question_names() -> None:
    """The tests review of 26 October: the grader blocks any column named for revenue with a
    negative value, so a result listing every category under revenue_rise_cents escalated as the
    earlier wording did. The question names rise_cents and asks for the top row alone."""
    question = _solution("reference").drill_down_question(DAY)
    columns = ["category", "sales_cents", "average_cents", "rise_cents"]
    assert _grade(question, columns, EVERY_CATEGORY, TEXT).passed
    named_for_revenue = [*columns[:3], "revenue_rise_cents"]
    blocked = _grade(question, named_for_revenue, EVERY_CATEGORY, TEXT)
    assert blocked.severity is Severity.BLOCK and "negative revenue" in blocked.reason
    # the top category's row alone passes even under a column named for revenue
    assert _grade(question, named_for_revenue, EVERY_CATEGORY[:1], TEXT).passed
