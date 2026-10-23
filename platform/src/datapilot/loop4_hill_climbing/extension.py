"""Extension points of Assignment 4: Hill-climbing loop, the critic and the unattended level.

The analyzer team and the eligibility rule call every hook below. Each is inert here, so class
runs are unchanged; the assignment fills them in (section-4-hill-climbing-loop/assignment/starter/
README.md). Its benchmark items go in a new file in platform/packs/datapilot_us/benchmark/
(hill-climbing-loop-1). The course build's boundary test keeps this file in this state on the class
branch.
"""

from __future__ import annotations

from collections.abc import Sequence

from datapilot.contracts import BenchmarkItem, CriticReview, Diagnosis, ProposedRule

# EXTENSION POINT, TODO 1 (hill-climbing-loop-1): six repeat-customer items in a new file in
# platform/packs/datapilot_us/benchmark/, and the family in pack.yaml; no code here.

# EXTENSION POINT, TODO 2 (hill-climbing-loop-2): the critic's judgement.
# Appended to the critic's system prompt; the class critic has no more guidance than its prompt.
CRITIC_GUIDANCE = ""


def screen(
    proposed: Sequence[ProposedRule],
    diagnoses: Sequence[Diagnosis],
    failed_items: Sequence[BenchmarkItem],
) -> tuple[list[ProposedRule], list[CriticReview]]:
    """Rules the critic stage drops before the model reads them: returns the rules left for the
    critic and a CriticReview (decision drop, with its reason) for each rule dropped here."""
    return list(proposed), []


# EXTENSION POINT, TODO 3 (hill-climbing-loop-3): may a metric family with this many holdout
# items reach the unattended level once every one of them passes?
def enough_holdout_items(count: int) -> bool:
    return True  # the class rule has no minimum
