"""Escalation: when the cheap model declines, hand the question to the expensive one.

**The answer is rarely "use the big model". It is "use the big model HERE."** Measured
after the p07/p08 wording fix:

  - **rules withheld (L0):** Haiku-plus-loop beats Sonnet one-shot (9 discordant,
    McNemar exact p=0.039)
  - **rules given (L3):** the two are **not distinguishable** (3 discordant, p=0.250).
    Sonnet is still numerically ahead, so this is CANNOT TELL at this n, not EQUAL.

The decision rule that follows: **the cheap model with a loop is never measurably
worse, and is measurably better when the spec is incomplete.** A blanket "use the
frontier model" pays frontier prices everywhere to buy an advantage that is only
visible where the spec is already good; escalating what the cheap model declined pays
them only on the questions that earned it.

(An earlier version of this docstring claimed Sonnet one-shot beat Haiku-plus-loop at
L3. That was true of the pre-fix measurement and was an artefact of two under-specified
questions penalising the arm that had been told about refund netting.)

Two numbers matter and are reported separately:

  escalation rate — how often the cheap model declined, out of everything asked
  conversion      — of the escalated questions, how many the frontier model got right
                    that the cheap model had not

Conversion is the one that decides whether escalation is worth anything. A policy that
escalates constantly and converts nothing is a more expensive way to be wrong.

Everything here takes an injectable client, so the whole policy — decline detection,
handoff construction, logging — is developed and tested offline against stubs. The real
frontier calls are spent once, on the measurement run, behind the live marker.
"""

from dataclasses import dataclass

import structlog

from loopeng.metric import Metric
from loopeng.triage.abstain import decide

log = structlog.get_logger(__name__)

# A hard ceiling, not a rate. At n≈15 the "did it help" measurement is already ±25pp,
# so 12 costs almost no power and makes the cost a ceiling rather than something that
# scales when abstention fires more often than expected.
MAX_ESCALATIONS = 12


@dataclass(frozen=True)
class Handoff:
    """What the frontier model is given. Deliberately not the cheap model's answer.

    Passing the declined SQL forward would anchor the frontier model to a query that
    was already judged shaky, and any improvement would then be partly ours rather than
    the model's. It gets the question and the rules, exactly as a fresh attempt would.
    """

    item_id: str
    question: str
    rules: tuple[str, ...]
    declined_because: str


def select_for_escalation(runs: list[dict], threshold: float,
                          limit: int = MAX_ESCALATIONS) -> tuple[list[dict], int]:
    """Which declined runs to escalate, and how many were declined in total.

    Returns the capped selection AND the full declined count, so the escalation rate is
    reported over everything declined rather than over what the budget allowed.
    """
    declined = [r for r in runs if decide(r, threshold).declined]
    return declined[:limit], len(declined)


def escalation_rate(runs: list[dict], threshold: float) -> Metric | None:
    _, n_declined = select_for_escalation(runs, threshold, limit=len(runs))
    return Metric.from_counts(n_declined, len(runs)) if runs else None


# `run_escalation` lived here and had no callers.
#
# It was the function this module exists for: it took the declined questions, asked
# the frontier model, and produced the artifact the OVERSIGHT and exhibit escalation
# panels read. Nothing anywhere invoked it — no demo, no test, no view — so the
# artifact could not be produced by any shipped entry point, and the panels' "not
# yet measured" was a claim that a measurement was pending rather than absent.
#
# Deleted rather than wired, because wiring it is a feature decision about what the
# session should spend, not a repair. The panels now say the artifact is not shipped.
# `select_for_escalation`, `escalation_rate`, `Handoff` and `MAX_ESCALATIONS` are all
# genuinely used and remain.
