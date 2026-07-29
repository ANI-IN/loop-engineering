"""McNemar's test, for the paired comparisons this project actually runs.

Every arm of the trap answers **the same** questions. That is paired data, and
comparing two proportions by asking whether their confidence intervals overlap is the
wrong test for it — it throws away the pairing, and interval overlap is a poor proxy
for significance even on unpaired data. McNemar uses only the **discordant pairs**:
the items where one arm was right and the other wrong. Items both arms got right, or
both got wrong, carry no information about which is better.

The exact binomial form is used rather than the chi-square approximation, because the
discordant counts here are small and the approximation is unreliable below about 25.

**It still overstates, and the report has to say so.** McNemar assumes the pairs are
independent. Ours are not: 50 items are 10 clusters of 5 parameterisations, so a
systematic weakness in one pattern produces up to five discordant pairs that are really
one observation. The honest on-screen statement is directional — "this arm is worse" —
never a specific gap.
"""

import math
from dataclasses import dataclass

# McNemar is defined on exactly two arms, so every caller has to check it has two
# before offering a paired comparison. Declared here, in the module that
# implements the test, rather than typed as a bare `== 2` at each call site where
# it reads as an arbitrary arity check.
PAIRED_ARM_COUNT = 2


@dataclass(frozen=True)
class PairedComparison:
    """The 2x2 table of a paired comparison, and what can be said from it."""

    both_correct: int
    only_a_correct: int
    only_b_correct: int
    both_wrong: int
    label_a: str = "A"
    label_b: str = "B"

    @property
    def n_pairs(self) -> int:
        return self.both_correct + self.only_a_correct + self.only_b_correct + self.both_wrong

    @property
    def n_discordant(self) -> int:
        """The only pairs that carry information about which arm is better."""
        return self.only_a_correct + self.only_b_correct

    @property
    def p_value(self) -> float | None:
        """Exact two-sided McNemar. None when there are no discordant pairs.

        None rather than 1.0: with nothing discordant there is no evidence either
        way, and reporting p=1.0 would look like a measured result rather than an
        absence of one.
        """
        b, c = self.only_a_correct, self.only_b_correct
        n = b + c
        if n == 0:
            return None
        smaller = min(b, c)
        tail = sum(math.comb(n, k) for k in range(smaller + 1)) / (2**n)
        return min(1.0, 2 * tail)

    def render(self) -> str:
        """Directional only. Deliberately never renders a gap."""
        if self.n_discordant == 0:
            return (
                f"{self.label_a} and {self.label_b} never disagreed "
                f"(n={self.n_pairs} pairs, 0 discordant) — no evidence either way"
            )
        better = self.label_a if self.only_a_correct > self.only_b_correct else self.label_b
        worse = self.label_b if better == self.label_a else self.label_a
        p = self.p_value
        verdict = "worse" if p is not None and p < 0.05 else "not distinguishable"
        if verdict == "not distinguishable":
            return (
                f"{self.label_a} vs {self.label_b}: {self.n_discordant} discordant of "
                f"{self.n_pairs} (p={p:.3f}) — not distinguishable at this n"
            )
        return (
            f"{worse} is worse than {better}; we cannot put a number on how much "
            f"({self.n_discordant} discordant of {self.n_pairs} pairs, McNemar exact "
            f"p={p:.3f}, clustered)"
        )

    def as_dict(self) -> dict:
        return {
            "label_a": self.label_a,
            "label_b": self.label_b,
            "both_correct": self.both_correct,
            "only_a_correct": self.only_a_correct,
            "only_b_correct": self.only_b_correct,
            "both_wrong": self.both_wrong,
            "n_pairs": self.n_pairs,
            "n_discordant": self.n_discordant,
            "p_value": self.p_value,
            "verdict": self.render(),
            "caveat": CLUSTERING_CAVEAT,
        }


CLUSTERING_CAVEAT = (
    "McNemar assumes the pairs are independent. These are not: 50 items are 10 "
    "clusters of 5 parameterisations, so a systematic weakness in one pattern can "
    "produce up to five discordant pairs that are really one observation. The p-value "
    "is therefore optimistic and the honest statement is directional only — 'this arm "
    "is worse', never a specific gap."
)


def compare(a_correct: dict[str, bool], b_correct: dict[str, bool], *, label_a="A", label_b="B"):
    """Build the paired table from two {item_id: was_correct} maps.

    Only items present in BOTH maps are paired. An item one arm never answered is not
    a pair, and silently treating a missing answer as wrong would invent evidence.
    """
    shared = sorted(set(a_correct) & set(b_correct))
    both = only_a = only_b = neither = 0
    for item_id in shared:
        a, b = a_correct[item_id], b_correct[item_id]
        if a and b:
            both += 1
        elif a:
            only_a += 1
        elif b:
            only_b += 1
        else:
            neither += 1
    return PairedComparison(both, only_a, only_b, neither, label_a=label_a, label_b=label_b)
