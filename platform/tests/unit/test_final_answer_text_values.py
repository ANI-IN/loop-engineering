"""The final-answer grader and digits that are part of a text value, such as a phone number a
person approved for this run: they are quoted from the result, not invented numbers. Found live in
the verification of Assignment 2: Verification loop, where an approved answer quoting a phone
number was refused three times and escalated."""

from __future__ import annotations

from datapilot.contracts import AnswerEnvelope, AnswerStatus, GraderContext, QueryResult
from datapilot.loop2_verification.graders import FinalAnswerGrader

SQL = "SELECT c.phone, count(*) FROM orders o JOIN customers c USING (customer_id) GROUP BY 1"


def _check(answer_text: str, rows: list[tuple]) -> bool:
    result = QueryResult(columns=["phone", "orders"], rows=rows, total_row_count=1, truncated=False)
    answer = AnswerEnvelope(status=AnswerStatus.ANSWERED, final_sql=SQL, answer_text=answer_text)
    context = GraderContext(question="Whose phone?", sql=SQL, result=result, answer=answer)
    return FinalAnswerGrader().check(context).passed


def test_digits_quoted_from_a_text_value_are_supported() -> None:
    assert _check(
        "The phone number is (961) 555-0162; they placed 9 orders.", [("(961) 555-0162", 9)]
    )


def test_a_number_in_no_value_still_fails() -> None:
    assert not _check(
        "The phone number is (961) 555-0162; they placed 12 orders.", [("(961) 555-0162", 9)]
    )
    assert not _check("The phone number is (961) 555-0199.", [("(961) 555-0162", 9)])
