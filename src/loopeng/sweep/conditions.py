"""The four conditions. Everything the session compares is a comparison across these.

    id  condition  model      loops
    A   baseline   cheap      none — single shot
    B   retry      cheap      L1 only
    C   verified   cheap      L1 + L2
    D   reference  frontier   none — single shot

**One implementation, selected by config.** The loops are nested, so A is C with the
outer two removed rather than a separate code path — and a second path would be a
second place for the termination policy to drift, which is the thing the session is
about. `run_condition` dispatches on the condition's own fields and calls the same
`run_question` / `run_verified` every other caller does.

WHAT EACH COMPARISON IS FOR, STATED BEFORE THE DATA

  A -> C   the loop uplift, and the before/after the session is built on
  A -> B   what retry ALONE buys: execution errors, and very little semantic
           correctness. It is the arm that shows a loop can be working perfectly and
           moving nothing that matters
  C vs D   cheap-plus-loops against frontier-bare. Secondary, pre-committed to one of
           three readings in docs/, and reported with its discordant-pair count

**The headline is not any of these.** It is the trap — rules withheld against rules
given — measured at a 73-point gap where the largest of these is expected to be a
fraction of that. The conditions are the second act, and they are labelled as such so
a null on C vs D reads as a finding rather than as a disappointment.

WHY SILENT ERRORS ARE A FIRST-CLASS FIGURE HERE

  Accuracy is the number people ask for and it is the wrong headline for this
  comparison. Verification does not mainly make an agent right; it makes it stop
  being confidently wrong. Those are different bands and only one of them is what a
  reader of the answer is exposed to.

  So every arm reports its silent-error count beside its accuracy, and the
  outcome-shift chart is built on the bands rather than on the rate. The band is
  expected to collapse from A to C even where accuracy barely moves, and if accuracy
  moved while the silent band did not, that would be a worse result wearing a better
  number.
"""

from dataclasses import dataclass
from pathlib import Path

import structlog

from loopeng.agent.classify import (
    BAND_ABSTAINED,
    BAND_CORRECT,
    BAND_SILENT,
    BAND_UNEARNED,
    BAND_VISIBLE,
    band_counts,
    judge,
)
from loopeng.agent.loop import run_question
from loopeng.metric import Metric
from loopeng.verify.batch import as_agent_run
from loopeng.verify.governance import verify_governed
from loopeng.verify.loop import run_verified

log = structlog.get_logger(__name__)


@dataclass(frozen=True)
class Condition:
    """One arm. The fields are the axes, so a new arm is data rather than a branch."""

    id: str
    name: str
    role: str
    # How many attempts the agent gets. 1 is a single shot — the loop cannot fire, so
    # `no_progress` and `budget` are structurally unreachable and the termination
    # distribution says so rather than showing an empty branch.
    max_attempts: int
    # Whether the Level 2 verifiers sit around the loop. False is Level 1 alone: it
    # retries on EXECUTION failure and cannot see a query that ran and is wrong.
    verified: bool
    note: str

    @property
    def loops(self) -> str:
        """What a reader should understand is wrapped around the model."""
        if self.verified:
            return "L1 + L2"
        return "L1 only" if self.max_attempts > 1 else "none — single shot"


A = Condition(
    id="A", name="baseline", role="agent", max_attempts=1, verified=False,
    note="The cheap model, once, with nothing around it. The floor everything else "
         "is measured against.",
)
B = Condition(
    id="B", name="retry", role="agent", max_attempts=3, verified=False,
    note="Level 1 only. It retries when the query fails to EXECUTE and is "
         "structurally unable to notice a query that ran and returned the wrong "
         "number — which is what A -> B is here to show.",
)
C = Condition(
    id="C", name="verified", role="agent", max_attempts=3, verified=True,
    note="Level 1 plus the parse-tree verifiers. The only arm that can send back a "
         "query that ran cleanly, and the one the session's argument rests on.",
)
D = Condition(
    id="D", name="reference", role="reference", max_attempts=1, verified=False,
    note="The frontier model, bare, on the held-out set. Not a contradiction of "
         "'cheap only': without a bar there is nothing for C to be compared to.",
)

CONDITIONS: dict[str, Condition] = {c.id: c for c in (A, B, C, D)}

# The order they are reported and drawn in. A, B, C is the escalation; D sits beside
# C because that adjacency is the comparison a reader makes with their eyes.
CONDITION_ORDER = ("A", "B", "C", "D")


class UnknownCondition(KeyError):
    """Raised rather than defaulting, so a typo cannot silently pick an arm."""


def condition_for(condition_id: str) -> Condition:
    try:
        return CONDITIONS[condition_id]
    except KeyError as exc:
        raise UnknownCondition(
            f"unknown condition {condition_id!r}; the four are "
            f"{list(CONDITION_ORDER)}"
        ) from exc


def run_item(condition: Condition, item, warehouse: Path, *, level: str = "L3",
             client=None, verifier=verify_governed):
    """One item through one condition. Returns `(run, judgement)`.

    The dispatch is two lines and that is the whole point: an unverified arm is the
    Level 1 loop with its attempt cap set, and a verified arm is the Level 2 loop
    around the same generator. Neither is a copy.
    """
    if condition.verified:
        verified = run_verified(
            item.question, warehouse=warehouse, rules=item.rules,
            role=condition.role, level=level, max_attempts=condition.max_attempts,
            item_id=item.item_id, client=client, verifier=verifier,
        )
        run = as_agent_run(verified)
        rejections = verified.rejections
    else:
        run = run_question(
            item.question, warehouse=warehouse, role=condition.role, level=level,
            max_attempts=condition.max_attempts, item_id=item.item_id, client=client,
        )
        rejections = 0

    judgement = judge(run, item)
    return run, judgement, rejections


def summarise_arm(condition: Condition, rows: list[dict]) -> dict:
    """What one arm did, with the silent-error band as a first-class figure.

    Accuracy is reported because people ask for it. The silent band is reported
    because it is what the session actually turns on: verification does not mainly
    make an agent right, it makes it stop being confidently wrong, and those move
    independently. An arm whose accuracy rose while its silent band held would be a
    worse result wearing a better number.

    Every band is counted by enumeration — see `classify.OUTCOME_BANDS`. Nothing here
    is derived by subtracting the bands somebody remembered from the total.
    """
    bands = band_counts(row["outcome"] for row in rows)
    n = len(rows)
    answered = bands[BAND_CORRECT] + bands[BAND_UNEARNED] + bands[BAND_SILENT]

    return {
        "condition": condition.id,
        "name": condition.name,
        "role": condition.role,
        "loops": condition.loops,
        "note": condition.note,
        "n_items": n,
        "bands": bands,
        # Accuracy over EVERY item, not over the ones that answered. An arm that
        # declines half the set and is right about the rest has not scored 100%.
        "accuracy": Metric.from_counts(bands[BAND_CORRECT], n).render() if n else None,
        "accuracy_value": bands[BAND_CORRECT] / n if n else None,
        # THE number. Reported as a count as well as a rate, because the count is what
        # collapses visibly from A to C and a rate hides how many items that is.
        "n_silent_errors": bands[BAND_SILENT],
        "silent_error_rate": (
            Metric.from_counts(bands[BAND_SILENT], answered).render()
            if answered else "not yet measured"
        ),
        "n_answered": answered,
        "n_visible_failures": bands[BAND_VISIBLE],
        "n_abstained": bands[BAND_ABSTAINED],
        "n_unearned_correct": bands[BAND_UNEARNED],
        "rejections": sum(row.get("rejections", 0) for row in rows),
        "cost_usd": {"value": round(sum(row["cost_usd"] for row in rows), 6),
                     "source": "estimated"},
        "cost_per_correct_usd": (
            {"value": round(sum(row["cost_usd"] for row in rows)
                            / bands[BAND_CORRECT], 6), "source": "estimated"}
            if bands[BAND_CORRECT] else None
        ),
        "termination": {
            reason: sum(1 for row in rows if row["termination"] == reason)
            for reason in sorted({row["termination"] for row in rows})
        },
        "items": sorted(rows, key=lambda row: row["item_id"]),
    }
