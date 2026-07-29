"""Three runs that do not succeed, because not every demo path is a success path.

A controller is only as good as its worst branch, and a branch nobody has watched
fire is a branch nobody knows works. The full Level 2 pass exercised `success` and
`no_progress` and left `max_attempts` and `budget` untouched, so these scenarios
provoke each one deliberately.

All three make **real model calls**. None of them stubs the model, because the thing
being demonstrated is the controller's behaviour under a real generator, and a
scripted client would only prove that the scripted client works.

The configurations are honest rather than contrived: a budget cap set low is a real
budget cap, and a verifier that refuses everything is a real failure mode — it is
exactly what an over-strict rule check looks like from the loop's side, and it is the
mirror of the regex verifier that accepts too much.
"""

from dataclasses import dataclass
from pathlib import Path

from loopeng.contracts import VerifyContext
from loopeng.verify.loop import run_verified
from loopeng.verify.verifiers import VerifyResult, Violation


def rejects_with_one_complaint(context: VerifyContext) -> VerifyResult:
    """Over-strict, and says the same thing every time.

    Not a strawman: this is what a rule check with a bug looks like from the loop's
    side. Because the complaint never changes, the loop recognises it is not making
    progress and stops — which is `no_progress` doing its job, and is why this
    scenario reaches that branch rather than the attempt cap.
    """
    return VerifyResult(
        violations=(
            Violation(
                rule="over_strict",
                complaint="Rejected. Try a different shape for the same question.",
            ),
        )
    )


def rejects_with_a_new_complaint(context: VerifyContext) -> VerifyResult:
    """Over-strict, but with fresh feedback each attempt.

    The distinction matters and was found by running it: with an unchanging complaint
    the loop terminates on `no_progress` long before the attempt cap, so a scenario
    meant to demonstrate `max_attempts` never reached it. Varying the complaint keeps
    the no-progress detector quiet and lets the cap be the thing that stops the run —
    which is also the realistic case, since a verifier that names a different problem
    each round looks like it is making progress when it is not.
    """
    return VerifyResult(
        violations=(
            Violation(
                rule="over_strict",
                complaint=(
                    f"Rejected on attempt {context.attempt}. Restructure the query "
                    f"differently from attempt {context.attempt}."
                ),
            ),
        )
    )


@dataclass(frozen=True)
class Scenario:
    key: str
    why: str
    expect: str
    max_attempts: int
    budget_usd: float
    verifier: object


SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        key="max_attempts",
        why=(
            "an over-strict verifier rejects every attempt with fresh feedback, so the "
            "no-progress detector stays quiet and the cap is what stops the run"
        ),
        expect="max_attempts",
        max_attempts=3,
        budget_usd=1.0,
        verifier=rejects_with_a_new_complaint,
    ),
    Scenario(
        key="budget",
        why="the cost cap is reached before the attempt cap, and is checked before spending",
        expect="budget",
        max_attempts=5,
        budget_usd=1e-6,
        verifier=rejects_with_a_new_complaint,
    ),
    Scenario(
        key="no_progress",
        why=(
            "the verifier repeats the same complaint, so the loop is going in circles "
            "and stops rather than spending three more attempts to find that out"
        ),
        expect="no_progress",
        max_attempts=5,
        budget_usd=1.0,
        verifier=rejects_with_one_complaint,
    ),
)


def run_scenario(scenario: Scenario, question: str, rules: tuple[str, ...], warehouse: Path):
    return run_verified(
        question,
        warehouse=warehouse,
        rules=rules,
        role="worker",
        level="L3",
        max_attempts=scenario.max_attempts,
        budget_usd=scenario.budget_usd,
        verifier=scenario.verifier,
    )
