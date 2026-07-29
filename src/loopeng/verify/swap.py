"""The AST-to-regex swap: the score goes up while the quality goes down.

Run the same questions through the same loop twice, changing only the verifier. The
regex verifier rejects less, so:

  - the **pass rate rises** (fewer rejections means more first-attempt acceptances)
  - the **cost falls** (fewer rejections means fewer retries)
  - the **actual correctness falls**, because the queries it waved through are wrong

Every one of the first two looks like an improvement on a dashboard. The only way to
tell an improvement from a weakened instrument is to check the instrument against
inputs whose answer is already known — the rule-surface probes — and that comparison
is reported alongside, so the two numbers sit next to each other.

`accepted` and `correct` are deliberately separate fields. Collapsing them into one
"score" is precisely the mistake being demonstrated.
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

from loopeng.agent.classify import Outcome, judge
from loopeng.agent.loop import AgentRun
from loopeng.gold.build import GoldItem
from loopeng.metric import Metric
from loopeng.usage import UsageLedger, merge
from loopeng.verify.loop import run_verified
from loopeng.verify.probes import run_probes
from loopeng.verify.regex_verifiers import verify_with_regex
from loopeng.verify.verifiers import verify

VERIFIERS = {"ast": verify, "regex": verify_with_regex}

CONCURRENCY = 8


@dataclass
class SwapArm:
    name: str
    accepted: int = 0
    correct: int = 0
    ran: int = 0
    rejections: int = 0
    ledger: UsageLedger = field(default_factory=UsageLedger)
    seconds: float = 0.0

    def acceptance_rate(self) -> Metric | None:
        """What the verifier said. The number a dashboard would show."""
        return Metric.from_counts(self.accepted, self.ran) if self.ran else None

    def correctness_rate(self) -> Metric | None:
        """What was actually true. The number that matters."""
        return Metric.from_counts(self.correct, self.ran) if self.ran else None


def _as_agent_run(verified) -> AgentRun:
    """Adapt a VerifiedRun so the Phase 1 classifier can judge it unchanged."""
    return AgentRun(
        question=verified.question,
        level=verified.level,
        role=verified.role,
        model_id=verified.model_id,
        attempts=tuple(a.attempt for a in verified.attempts),
        termination=verified.termination,
        item_id=verified.item_id,
        ledger=verified.ledger,
    )


def run_swap(
    items: list[GoldItem],
    warehouse: Path,
    *,
    level: str = "L3",
    role: str = "worker",
    max_attempts: int = 3,
    client=None,
) -> dict:
    arms = {name: SwapArm(name) for name in VERIFIERS}

    def _one(name, item):
        verified = run_verified(
            item.question,
            warehouse=warehouse,
            rules=item.rules,
            role=role,
            level=level,
            max_attempts=max_attempts,
            client=client,
            item_id=item.item_id,
            verifier=VERIFIERS[name],
        )
        return name, item, verified

    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=CONCURRENCY * len(VERIFIERS)) as pool:
        futures = [pool.submit(_one, name, item) for name in VERIFIERS for item in items]
        for future in as_completed(futures):
            name, item, verified = future.result()
            arm = arms[name]
            arm.ran += 1
            arm.rejections += verified.rejections
            arm.ledger = merge([arm.ledger, verified.ledger])
            final = verified.final
            if final and final.attempt.executed and final.verdict.ok:
                arm.accepted += 1
            judgement = judge(_as_agent_run(verified), item)
            if judgement.outcome is Outcome.CORRECT:
                arm.correct += 1
    elapsed = time.perf_counter() - start

    return {
        "n_items": len(items),
        "seconds": round(elapsed, 1),
        "arms": {
            name: {
                "accepted_by_the_verifier": arm.accepted,
                "actually_correct": arm.correct,
                "n": arm.ran,
                "rejections": arm.rejections,
                "acceptance_rate": (
                    arm.acceptance_rate().render() if arm.acceptance_rate() else "not yet measured"
                ),
                "correctness_rate": (
                    arm.correctness_rate().render()
                    if arm.correctness_rate()
                    else "not yet measured"
                ),
                "cost_usd_estimated": round(arm.ledger.cost_usd(), 6),
                "tokens": arm.ledger.totals(),
            }
            for name, arm in arms.items()
        },
        "probe_surface": {name: run_probes(fn) for name, fn in VERIFIERS.items()},
        "reading": _reading(arms),
    }


def _reading(arms: dict[str, SwapArm]) -> str:
    """Describe what actually happened, not the outcome that would be convenient.

    Written to be honest in every direction, because a demo whose narration only fits
    the flattering result is a demo that will narrate a result it did not get.
    """
    ast, regex = arms["ast"], arms["regex"]
    if not ast.ran or not regex.ran:
        return "Nothing ran; there is nothing to read."

    ast_surface = run_probes(verify)
    regex_surface = run_probes(verify_with_regex)
    weaker = regex_surface["n_missed_violations"] > ast_surface["n_missed_violations"]

    score_up = regex.accepted / regex.ran > ast.accepted / ast.ran
    cheaper = regex.ledger.cost_usd() < ast.ledger.cost_usd()
    quality_down = regex.correct / regex.ran < ast.correct / ast.ran
    quality_same = regex.correct == ast.correct

    if not weaker:
        return (
            "The probe surface does not show the regex verifier catching less on this "
            "run. Without that, nothing else here is evidence of anything — say so and "
            "move on rather than reading a story into the scores."
        )

    moved = [
        label
        for label, happened in (
            ("acceptance rate up", score_up),
            ("cost down", cheaper),
            ("rejections down", regex.rejections < ast.rejections),
        )
        if happened
    ]
    if not moved:
        return (
            "The regex verifier provably catches less, yet none of the headline numbers "
            "moved in its favour on this run. The argument still holds — the probe "
            "surface is the evidence — but do not claim a dashboard effect that did not "
            "appear at this n."
        )

    # The correctness comparison is bounded by construction: the arms can only differ
    # on items where the AST verifier actually rejected something, because every other
    # item followed an identical path through an identical loop.
    bound = ast.rejections
    ast_correct = Metric.from_counts(ast.correct, ast.ran)
    regex_correct = Metric.from_counts(regex.correct, regex.ran)
    span = (
        f"{ast_correct.ci_low * 100:.0f}-{ast_correct.ci_high * 100:.0f}%"
        if ast.ran
        else "n/a"
    )

    if quality_down:
        correctness = f"correctness fell as well ({regex_correct.render()})"
    elif quality_same:
        correctness = "correctness came out identical"
    else:
        correctness = "correctness moved the other way"

    return (
        f"The regex verifier misses {regex_surface['n_missed_violations']} violation(s) "
        f"the AST verifier catches — the probe surface drops from "
        f"{ast_surface['n_sound']}/{ast_surface['n_rules']} sound to "
        f"{regex_surface['n_sound']}/{regex_surface['n_rules']} — and on this run "
        f"{', '.join(moved)}. Every one of those is an improvement on a dashboard.\n\n"
        f"THE CORRECTNESS COMPARISON IS UNDERPOWERED AND MUST NOT BE READ AS A RESULT. "
        f"Here {correctness}, but at this n the interval on correctness spans roughly "
        f"{span} — wide enough that 'quality held' and 'quality halved' are "
        f"indistinguishable. The comparison is also bounded by construction: the AST "
        f"verifier rejected {bound} item(s), so AT MOST {bound} of {ast.ran} could "
        f"differ between the arms at all. Running more items does not fix this; the "
        f"bound is structural.\n\n"
        f"The probe surface is the load-bearing evidence, not the scores. It tests the "
        f"verifier against queries whose correctness is already known, instead of "
        f"grading it on the numbers it produces."
    )
