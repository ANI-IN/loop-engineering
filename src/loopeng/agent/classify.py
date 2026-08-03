"""What actually happened to an answer, judged against gold after the fact.

Deliberately separate from the loop. The loop never sees gold; this module does. Same
isolation the VerifyContext contract enforces in Phase 2, applied one phase early.

**The visible/silent split decides what the headline number means.**

    VISIBLE : invalid SQL, execution error, QueryTimeout, empty result.
              Something plainly went wrong and an operator would see it.
    SILENT  : the query ran, returned something plausible, and is wrong.

**Silent-error rate is computed only over answers that ran and returned something.**
Folding visible failures in would inflate the headline with failures the room can
already see, which is the opposite of what the metric is for. The two counts are
reported separately and never summed into one rate.

**The taxonomy uses the per-rule naive variants built in Phase 0.** An answer matching
the variant for rule X exactly is "ignored rule X" — a different and far more useful
statement than "wrong". For the one item whose variants collide, both rules are
reported and neither is picked: saying "soft_delete or internal_accounts" is honest,
and choosing one would be a coin flip presented as a finding.
"""

import math
from dataclasses import dataclass
from enum import StrEnum

from loopeng.agent.loop import AgentRun
from loopeng.gold.build import GoldItem
from loopeng.gold.compare import rows_equal


class Outcome(StrEnum):
    CORRECT = "correct"
    SILENT_ERROR = "silent_error"
    VISIBLE_FAILURE = "visible_failure"


class VisibleKind(StrEnum):
    EXECUTION_ERROR = "execution_error"
    TIMEOUT = "timeout"
    EMPTY_RESULT = "empty_result"
    NO_ATTEMPTS = "no_attempts"
    # Added 2026-07-29 after the first trap run. See _shape_mismatch below.
    SHAPE_MISMATCH = "shape_mismatch"
    NULL_RESULT = "null_result"
    # The call to the model failed, so no query was ever sent and the database was
    # never involved. Previously these landed in EXECUTION_ERROR — defined two
    # dozen lines up as "invalid SQL, execution error" — so a sweep run with a bad
    # key, an exhausted account or a rate-limited pool produced a cell reporting
    # that every item hit an execution error, sending the operator to the SQL and
    # the warehouse when the problem was the credential.
    #
    # Additive to `visible_failure_kinds` in stored cell files, the same
    # convention the cache token fields already established.
    MODEL_CALL_FAILED = "model_call_failed"


def _shape_mismatch(rows, gold_rows) -> bool:
    """Did the query answer with a different number of columns than was asked for?

    This is VISIBLE, not silent, and the distinction is the project's own definition
    rather than a convenience: a silent error is one you cannot detect without knowing
    the answer. A column count is knowable without the answer — you asked for one
    number and got three — so anyone consuming the result sees it immediately.

    It is a real category, not a technicality. Measured on the first Phase 1 trap: 11
    of 35 apparent silent errors were a model returning the right numbers alongside an
    extra label column, e.g. (product_id, category, units) where the gold SQL returns
    (product_id, units). Scoring those as silent errors measured how precisely the
    question pinned down an output schema, not whether the model understood the
    business rules — and it inflated the headline number by a third.

    ROW count counts too, and originally did not. Phase 4 triage found a query that
    returned 105 rows where gold had 1 — an aggregate that never collapsed — classified
    as a SILENT error because only the column count was compared. Asking for one number
    and receiving a hundred and five is as visible as receiving three columns, so it
    belongs in the same bucket. The asymmetry was ours, not the model's.

    **There is no order-sensitivity exemption, despite what this docstring used to
    say.** It claimed that "an order-sensitive item is exempt from the row check,
    because a top-N query legitimately returns many rows and a wrong N is a wrong
    ranking, not a shape". This function does not receive `order_sensitive` and
    cannot act on it: the row comparison below is unconditional, so a top-N query
    returning the wrong number of rows IS classified as a shape mismatch today.

    The claim is removed rather than implemented because implementing it is a
    decision about what the measurement means — whether a wrong N is a visible
    failure or a silent error — and that decision changes the headline number.
    Making it quietly, inside an audit, would be worse than leaving the behaviour
    alone. It is recorded as an open question rather than resolved here.

    What is NOT in doubt: the docstring described behaviour the code has never had.
    """
    if not rows or not gold_rows:
        return False
    if len(rows[0]) != len(gold_rows[0]):
        return True
    return len(rows) != len(gold_rows)


def _is_all_null(rows) -> bool:
    """A row of NULLs or NaNs is not a plausible answer; it is a visible non-answer.

    NaN counts because it is what a division by zero produces here, and a rate that
    came back NaN is visibly broken to whoever reads it — it does not need the gold
    answer to be recognised as wrong.
    """
    if not rows:
        return False

    def is_nothing(value) -> bool:
        if value is None:
            return True
        return isinstance(value, float) and math.isnan(value)

    return all(is_nothing(value) for row in rows for value in row)


def _is_monotonic(values) -> bool:
    """Does this column carry the ranking? Ties are allowed; direction is not mixed."""
    numeric = []
    for value in values:
        try:
            numeric.append(float(value))
        except (TypeError, ValueError):
            return False
    if len(numeric) < 2:
        return False
    return all(a >= b for a, b in zip(numeric, numeric[1:], strict=False)) or all(
        a <= b for a, b in zip(numeric, numeric[1:], strict=False)
    )


def _tie_break_only(rows, gold_rows, order_sensitive: bool) -> bool:
    """Do these differ only in how a tie was broken?

    "Which five products sold the most units?" does not say what to do when two
    products both sold 120. The gold SQL breaks the tie on product_id because SQL
    demands *some* total order, but that choice is an artefact of writing the query,
    not part of the question — so both orderings are correct answers.

    Measured on the Phase 1 trap: p06_top_products__04 returned the same five products
    with the same five counts, ordering the two products tied at 120 the other way,
    and was scored a silent error. Scoring that as wrong measures whether the model
    guessed our tie-break convention.

    The test is narrow on purpose: the rows must be the same multiset, and every
    column that actually carries the ranking — monotonic in gold — must appear in the
    identical order. A model that returns a different top five, or ranks them
    genuinely differently, fails both checks.
    """
    if not order_sensitive or not rows or not gold_rows:
        return False
    if len(rows) != len(gold_rows) or len(rows[0]) != len(gold_rows[0]):
        return False
    if not rows_equal(rows, gold_rows, order_sensitive=False):
        return False

    for column in range(len(gold_rows[0])):
        gold_column = [row[column] for row in gold_rows]
        if not _is_monotonic(gold_column):
            continue  # a label column; ties may permute it freely
        model_column = [row[column] for row in rows]
        if not rows_equal(
            [[v] for v in gold_column], [[v] for v in model_column], order_sensitive=True
        ):
            return False  # the ranking itself differs, not just the tie-break
    return True


@dataclass(frozen=True)
class Judgement:
    item_id: str
    model_id: str
    outcome: Outcome
    termination: str
    visible_kind: VisibleKind | None = None
    # Rules this answer can be attributed to. More than one means the item's variants
    # are indistinguishable and the honest report names them all.
    attributed_rules: tuple[str, ...] = ()
    ambiguous: bool = False

    @property
    def ran_and_returned(self) -> bool:
        """The denominator of silent-error rate."""
        return self.outcome in (Outcome.CORRECT, Outcome.SILENT_ERROR)

    @property
    def unclassified(self) -> bool:
        """A wrong answer matching no naive variant."""
        return self.outcome is Outcome.SILENT_ERROR and not self.attributed_rules


def _attribute(run_rows, item: GoldItem) -> tuple[tuple[str, ...], bool]:
    """Which rule's naive variant this answer matches, if any.

    Every matching variant is returned, not the first. For the ambiguous item the
    variants are equal, so both rules match and both are reported.
    """
    matched = [
        rule
        for rule, naive in item.naive_by_rule.items()
        if rows_equal(run_rows, naive["rows"], order_sensitive=item.order_sensitive)
    ]
    if not matched:
        return (), False

    # Expand through the item's recorded ambiguity groups: if the matched rule is in a
    # group, every rule in that group is an equally valid attribution.
    expanded = set(matched)
    for group in item.ambiguous_rule_groups:
        if expanded & set(group):
            expanded.update(group)

    return tuple(sorted(expanded)), len(expanded) > 1


def judge(run: AgentRun, item: GoldItem) -> Judgement:
    base = {
        "item_id": item.item_id,
        "model_id": run.model_id,
        "termination": str(run.termination),
    }

    if not run.attempts:
        return Judgement(
            **base, outcome=Outcome.VISIBLE_FAILURE, visible_kind=VisibleKind.NO_ATTEMPTS
        )

    final = run.final
    # Asked BEFORE the error text is inspected. `Attempt.model_call_failed` exists
    # precisely to tell "the database rejected this SQL" from "no SQL was ever
    # sent", and `views/render.py` consulted it while this function did not — so
    # the renderer and the classifier disagreed about the same attempt.
    if final.model_call_failed:
        return Judgement(
            **base, outcome=Outcome.VISIBLE_FAILURE,
            visible_kind=VisibleKind.MODEL_CALL_FAILED,
        )

    if final.error is not None:
        kind = (
            VisibleKind.TIMEOUT
            if final.error.startswith("QueryTimeout")
            else VisibleKind.EXECUTION_ERROR
        )
        return Judgement(**base, outcome=Outcome.VISIBLE_FAILURE, visible_kind=kind)

    if not final.rows:
        # A query that runs and returns nothing is visibly odd, not silently wrong.
        return Judgement(
            **base, outcome=Outcome.VISIBLE_FAILURE, visible_kind=VisibleKind.EMPTY_RESULT
        )

    if _is_all_null(final.rows):
        return Judgement(
            **base, outcome=Outcome.VISIBLE_FAILURE, visible_kind=VisibleKind.NULL_RESULT
        )

    if _shape_mismatch(final.rows, item.gold_rows):
        return Judgement(
            **base, outcome=Outcome.VISIBLE_FAILURE, visible_kind=VisibleKind.SHAPE_MISMATCH
        )

    if rows_equal(final.rows, item.gold_rows, order_sensitive=item.order_sensitive):
        return Judgement(**base, outcome=Outcome.CORRECT)

    if _tie_break_only(final.rows, item.gold_rows, item.order_sensitive):
        return Judgement(**base, outcome=Outcome.CORRECT)

    rules, ambiguous = _attribute(final.rows, item)
    return Judgement(
        **base,
        outcome=Outcome.SILENT_ERROR,
        attributed_rules=rules,
        ambiguous=ambiguous,
    )


def summarise(judgements: list[Judgement]) -> dict:
    """Counts, split the way the report needs them. No rates computed here.

    Rates are built by the caller through Metric.from_counts, so every number that
    reaches a screen carries its own n and interval.
    """
    ran = [j for j in judgements if j.ran_and_returned]
    silent = [j for j in ran if j.outcome is Outcome.SILENT_ERROR]
    visible = [j for j in judgements if j.outcome is Outcome.VISIBLE_FAILURE]

    attribution: dict[str, int] = {}
    for judgement in silent:
        if judgement.attributed_rules:
            attribution[" or ".join(judgement.attributed_rules)] = (
                attribution.get(" or ".join(judgement.attributed_rules), 0) + 1
            )

    termination: dict[str, int] = {}
    for judgement in judgements:
        termination[judgement.termination] = termination.get(judgement.termination, 0) + 1

    visible_kinds: dict[str, int] = {}
    for judgement in visible:
        key = str(judgement.visible_kind)
        visible_kinds[key] = visible_kinds.get(key, 0) + 1

    return {
        "n_total": len(judgements),
        "n_ran_and_returned": len(ran),
        "n_correct": sum(1 for j in ran if j.outcome is Outcome.CORRECT),
        "n_silent_errors": len(silent),
        "n_visible_failures": len(visible),
        "visible_failure_kinds": dict(sorted(visible_kinds.items())),
        "termination_reasons": dict(sorted(termination.items())),
        "attribution": dict(sorted(attribution.items(), key=lambda kv: -kv[1])),
        "n_unclassified": sum(1 for j in silent if j.unclassified),
        "n_ambiguous_attributions": sum(1 for j in silent if j.ambiguous),
    }
