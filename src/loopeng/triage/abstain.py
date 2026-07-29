"""Abstention: coverage becomes a CHOICE rather than a synonym for "did not crash".

Gate 1 recorded that the prior tier finding — frontier models show the highest coverage
and the lowest precision — did not reproduce, and the likely reason was that "coverage"
only meant "produced something". Nothing was choosing. This module makes it a choice.

**The confidence signal costs nothing.** It is read off the loop's own telemetry —
whether the query ran, how many times the verifier sent it back, and which branch
terminated the run — rather than from an extra model call asking "are you sure?". That
is cheaper, and it is also more honest: a model's stated confidence is another
generation to be wrong about, while a `no_progress` termination is a fact about what
happened.

Because the signal is telemetry, the whole coverage/precision curve can be recomputed
over runs that were already measured. Calibrating abstention costs nothing at all.
"""

from dataclasses import dataclass

# Confidence bands, highest first. A run is scored by the first rule that matches.
# The numbers are ordinal labels for sorting, not measurements — they never reach a
# chart, and no rate is ever computed from them.
CONFIDENCE = {
    "clean_first_try": 1.00,
    "accepted_after_revision": 0.70,
    "gave_up_no_progress": 0.30,
    "hit_the_attempt_cap": 0.20,
    "budget_exhausted": 0.15,
    "never_executed": 0.00,
}

# The threshold OVERSIGHT opens on, declared once.
#
# It was typed into the view three times — the stored state, the slider default,
# and the caveat sentence naming it — so the three could drift apart with nothing
# to notice. The caveat is the one that matters: it tells a room the threshold was
# chosen to fit the escalation cap rather than on principle, and a caveat naming a
# number the slider no longer uses is worse than no caveat.
#
# `accepted_after_revision` means: answer anything the verifier eventually passed,
# decline anything that hit a cap or gave up going in circles.
DEFAULT_THRESHOLD = CONFIDENCE["accepted_after_revision"]


def confidence_of(run: dict) -> tuple[float, str]:
    """Score one recorded run. Returns (confidence, the reason in plain English)."""
    if not run.get("ran_and_returned"):
        return CONFIDENCE["never_executed"], (
            "the query never returned a usable result, so there is nothing to report"
        )
    termination = run.get("termination", "")
    rejections = run.get("rejections", 0)

    if termination == "budget":
        return CONFIDENCE["budget_exhausted"], (
            "the cost budget ran out before the query satisfied the business rules"
        )
    if termination == "no_progress":
        return CONFIDENCE["gave_up_no_progress"], (
            "the same problem kept coming back — the query stopped changing in any way "
            "that fixed it, so the loop stopped rather than spending more"
        )
    if termination == "max_attempts":
        return CONFIDENCE["hit_the_attempt_cap"], (
            "the attempt limit was reached with the business rules still unsatisfied"
        )
    if rejections:
        return CONFIDENCE["accepted_after_revision"], (
            f"accepted, but only after {rejections} revision(s) — the first attempt "
            "broke a business rule"
        )
    return CONFIDENCE["clean_first_try"], "accepted on the first attempt with no revisions"


@dataclass(frozen=True)
class Decision:
    item_id: str
    answered: bool
    confidence: float
    reason: str
    correct: bool | None

    @property
    def declined(self) -> bool:
        return not self.answered


def decide(run: dict, threshold: float) -> Decision:
    """Answer, or decline and say why.

    `threshold` is the knob the room turns. Raising it declines more and answers less.
    """
    confidence, reason = confidence_of(run)
    answered = confidence >= threshold
    return Decision(
        item_id=run["item_id"],
        answered=answered,
        confidence=confidence,
        reason=reason,
        correct=run.get("correct") if answered else None,
    )


def operating_point(runs: list[dict], threshold: float) -> dict:
    """Coverage and precision at one threshold. Both counts, never a bare rate.

    coverage  — of the questions asked, how many were answered at all
    precision — of the questions ANSWERED, how many were right

    They move in opposite directions, which is the entire point: declining the shaky
    answers raises precision by lowering coverage, and the operator chooses where to
    sit. A single accuracy number hides that trade completely.
    """
    from loopeng.metric import Metric

    decisions = [decide(run, threshold) for run in runs]
    answered = [d for d in decisions if d.answered]
    right = sum(1 for d in answered if d.correct)

    coverage = Metric.from_counts(len(answered), len(decisions)) if decisions else None
    precision = Metric.from_counts(right, len(answered)) if answered else None
    return {
        "threshold": threshold,
        "n_total": len(decisions),
        "n_answered": len(answered),
        "n_declined": len(decisions) - len(answered),
        "n_correct_of_answered": right,
        "coverage": coverage.render() if coverage else "not yet measured",
        "precision": precision.render() if precision else "not yet measured",
        "coverage_value": coverage.value if coverage else None,
        "precision_value": precision.value if precision else None,
        "precision_ci_low": precision.ci_low if precision else None,
        "precision_ci_high": precision.ci_high if precision else None,
        "declined": [
            {"item_id": d.item_id, "reason": d.reason, "confidence": d.confidence}
            for d in decisions if d.declined
        ],
    }


def curve(runs: list[dict], thresholds=None) -> list[dict]:
    """The operating points a threshold slider moves between."""
    if thresholds is None:
        thresholds = sorted({0.0, *CONFIDENCE.values()})
    return [operating_point(runs, t) for t in thresholds]
