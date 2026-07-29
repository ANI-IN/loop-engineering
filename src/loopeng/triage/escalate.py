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
from pathlib import Path

import structlog

from loopeng.agent.classify import Outcome, judge
from loopeng.gold.build import GoldItem
from loopeng.metric import Metric
from loopeng.triage.abstain import decide
from loopeng.verify.batch import as_agent_run
from loopeng.verify.governance import verify_governed
from loopeng.verify.loop import run_verified

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


def run_escalation(
    runs: list[dict],
    items_by_id: dict[str, GoldItem],
    warehouse: Path,
    *,
    threshold: float,
    role: str = "frontier",
    level: str = "L0",
    limit: int = MAX_ESCALATIONS,
    client=None,
    verifier=verify_governed,
) -> dict:
    """Escalate the declined questions and measure whether it helped."""
    selected, n_declined = select_for_escalation(runs, threshold, limit)
    by_id = {r["item_id"]: r for r in runs}

    results = []
    for run in selected:
        item = items_by_id[run["item_id"]]
        decision = decide(run, threshold)
        handoff = Handoff(item.item_id, item.question, item.rules, decision.reason)
        escalated = run_verified(
            handoff.question, warehouse=warehouse, rules=handoff.rules, role=role,
            level=level, max_attempts=3, item_id=handoff.item_id,
            client=client, verifier=verifier,
        )
        judgement = judge(as_agent_run(escalated), item)
        was_correct = bool(by_id[run["item_id"]].get("correct"))
        now_correct = judgement.outcome is Outcome.CORRECT
        results.append({
            "item_id": item.item_id,
            "declined_because": handoff.declined_because,
            "cheap_model_was_correct": was_correct,
            "frontier_model_correct": now_correct,
            "converted": now_correct and not was_correct,
            "cost_usd": escalated.cost_usd(),
            "termination": str(escalated.termination),
        })
        log.info("escalated", item_id=item.item_id, converted=results[-1]["converted"])

    converted = sum(1 for r in results if r["converted"])
    conversion = Metric.from_counts(converted, len(results)) if results else None
    rate = Metric.from_counts(n_declined, len(runs)) if runs else None

    return {
        "threshold": threshold, "role": role, "level": level,
        "n_asked": len(runs),
        "n_declined": n_declined,
        "n_escalated": len(results),
        "capped_at": limit,
        "was_capped": n_declined > limit,
        "escalation_rate": rate.render() if rate else "not yet measured",
        "n_converted": converted,
        "conversion_rate": conversion.render() if conversion else "not yet measured",
        "cost_usd": {"value": round(sum(r["cost_usd"] for r in results), 6),
                     "source": "estimated"},
        "underpowered_note": (
            f"Conversion is measured over {len(results)} escalated questions, capped at "
            f"{limit} to make the cost a ceiling rather than something that scales with "
            "the decline rate. At this n the interval is roughly +/-25 points: this "
            "shows THAT escalation converts, not how often. Do not quote the rate."
        ),
        "results": results,
    }
