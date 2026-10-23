"""Grader 7, final answer: the envelope is consistent with the result it claims to describe.

Checks: a valid status with what that status needs; every number in the answer text appears in the
result within rounding (money in cents may be shown in dollars, ratios as percentages); a top-N
question returns at most N rows; revenue is never negative; percentages lie between 0 and 100.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

from datapilot.contracts import AnswerStatus, GraderContext, GraderResult, QueryResult, Stage
from datapilot.loop2_verification.graders._sql import blocked, passed

_DATES = re.compile(r"\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?)?|\b\d{1,2}:\d{2}\b")
_NUMBER = re.compile(
    r"(?<![\w.])(-?)\$?(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?\s*"
    r"(%|percent|thousand|million|billion|bn|k|m)?(?!\w)",
    re.IGNORECASE,
)
_MULTIPLIERS = {"thousand": 1e3, "k": 1e3, "million": 1e6, "m": 1e6, "billion": 1e9, "bn": 1e9}
_TOP_N = re.compile(r"\btop\s+(\d+)\b", re.IGNORECASE)
_NUMBER_WORDS = (
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
)
_WORDS = {w: i for i, w in enumerate(_NUMBER_WORDS)}
_TOP_WORD = re.compile(r"\btop\s+(" + "|".join(_WORDS) + r")\b", re.IGNORECASE)


@dataclass(frozen=True)
class Mention:
    text: str
    value: float
    tolerance: float
    percent: bool


def mentions(text: str) -> list[Mention]:
    found = []
    for match in _NUMBER.finditer(_DATES.sub(" ", text)):
        sign, whole, fraction, unit = match.groups()
        unit = (unit or "").lower()
        decimals = len(fraction) - 1 if fraction else 0
        scale = _MULTIPLIERS.get(unit, 1.0)
        value = float(f"{sign}{whole.replace(',', '')}{fraction or ''}") * scale
        found.append(
            Mention(
                text=match.group(0).strip(),
                value=value,
                tolerance=0.5 * 10**-decimals * scale + 1e-9,
                percent=unit in ("%", "percent"),
            )
        )
    return found


def _numbers(result: QueryResult) -> list[float]:
    values = [float(v) for row in result.rows for v in row if _is_number(v)]
    return values + [float(result.total_row_count), float(len(result.rows))]


def _is_number(value: object) -> bool:
    return isinstance(value, int | float | Decimal) and not isinstance(value, bool)


def _exempt(mention: Mention, question: str) -> bool:
    """Years, and numbers the question itself contains, are context, not results."""
    whole = mention.value == int(mention.value)
    if whole and 1900 <= mention.value <= 2100 and not mention.percent:
        return True
    return mention.text.replace("$", "").replace(",", "") in question.replace(",", "")


def supported(mention: Mention, values: list[float]) -> bool:
    for v in values:
        candidates = [v, v / 100]  # money in cents may be shown in dollars
        if mention.percent:
            candidates.append(v * 100)  # a ratio shown as a percentage
        if any(abs(abs(c) - abs(mention.value)) <= mention.tolerance for c in candidates):
            return True
    return False


def _top_n(question: str) -> int | None:
    if match := _TOP_N.search(question):
        return int(match.group(1))
    if match := _TOP_WORD.search(question):
        return _WORDS[match.group(1).lower()]
    return None


class FinalAnswerGrader:
    name = "final_answer"
    stage = Stage.FINAL_ANSWER

    def check(self, context: GraderContext) -> GraderResult:
        answer = context.answer
        if answer is None:
            return blocked(self.name, "no answer envelope", "Return an AnswerEnvelope.")
        if answer.status is AnswerStatus.NEEDS_CLARIFICATION:
            if not answer.clarifying_question:
                return blocked(
                    self.name, "clarification without a question", "Set clarifying_question."
                )
            return passed(self.name, "asks a clarifying question")
        if answer.status is not AnswerStatus.ANSWERED:
            return passed(self.name, f"status {answer.status.value}")
        if not answer.final_sql or not answer.answer_text.strip():
            return blocked(
                self.name,
                "answered without SQL or text",
                "An answered envelope needs final_sql and answer_text.",
            )
        result = context.result
        if result is None:
            return blocked(self.name, "no result for the final SQL", "Run the final SQL first.")
        problems = self._result_problems(context.question, result)
        values = _numbers(result)
        texts = [v for row in result.rows for v in row if isinstance(v, str)]
        unsupported = [
            m.text
            for m in mentions(answer.answer_text)
            if not _exempt(m, context.question)
            and not supported(m, values)
            and not any(m.text in text for text in texts)  # digits quoted from a text value
        ]
        out_of_range = [
            m.text for m in mentions(answer.answer_text) if m.percent and not 0 <= m.value <= 100
        ]
        if unsupported:
            problems.append(f"numbers not in the result: {', '.join(unsupported)}")
        if out_of_range:
            problems.append(f"percentages outside 0 to 100: {', '.join(out_of_range)}")
        if problems:
            reason = "; ".join(problems)
            return blocked(
                self.name,
                reason,
                f"The answer does not match the final SQL's result ({reason}). Quote only "
                "numbers from the result, or fix the SQL.",
            )
        return passed(self.name, "the answer matches the result")

    @staticmethod
    def _result_problems(question: str, result: QueryResult) -> list[str]:
        problems = []
        limit = _top_n(question)
        if limit is not None and result.total_row_count > limit:
            problems.append(f"top {limit} asked, {result.total_row_count} rows returned")
        for index, column in enumerate(result.columns):
            name = column.lower()
            values = [row[index] for row in result.rows if _is_number(row[index])]
            if "revenue" in name and any(v < 0 for v in values):
                problems.append(f"negative revenue in {column}")
            if ("pct" in name or "percent" in name) and any(not 0 <= v <= 100 for v in values):
                problems.append(f"percentages outside 0 to 100 in {column}")
        return problems
