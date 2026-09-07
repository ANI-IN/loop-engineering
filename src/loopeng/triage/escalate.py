"""Escalation: when the cheap model declines, hand the question to the expensive one.

**The answer is rarely "use the big model". It is "use the big model HERE."**

**The findings this docstring used to quote are gone rather than restated, and that is
deliberate.** They were measured on two Anthropic models that are no longer in this
build, with typed discordant counts and p-values in prose — so they described a system
that does not exist, in the form this project bans everywhere a reader can see it.

What the current measurement supports is narrower and stronger. On the held-out set
with the rules SUPPLIED, the frontier model scored 60/60 on two separate runs: at that
prompt level the task is solved and escalation buys nothing. With the rules WITHHELD it
scored 9/60 — no better than the cheap model's 7/60 in any way this n can resolve.

So the decision rule is not about which model. **Escalating a question the cheap model
declined is worth doing; escalating because the spec is incomplete is paying frontier
prices for a problem no model solves.** Spend on the rules first.

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
