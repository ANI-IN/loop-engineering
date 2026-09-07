"""Which of three pre-committed readings the data selects, computed not chosen.

The named secondary — cheap model plus loops against the frontier model bare — is
committed IN ADVANCE to one of three readings, written down in
`docs/three-endings.md`. This module is the arithmetic that picks between them, so the
selection is a function of the arms rather than a judgement made while looking at them.

WHY THE CRITERIA USE NO P-VALUE

`sweep/diff.py` refuses a p-value across models, and that refusal is enforced in code
rather than stated in a caption. A pre-commitment that turned on significance would
therefore be a rule the rest of the project forbids anyone to evaluate — so the criteria
are stated in DISCORDANT PAIRS, which is what a paired comparison can honestly report
across two different models: how many items each arm got that the other did not.

WHY "NO GAP TO CLOSE" IS AN ENDING RATHER THAN A FAILURE

The question is whether loops around a budget model close the distance to a frontier
model. If the frontier model bare is not ahead of the budget model bare, there is no
distance, and every other reading is a claim about a quantity that does not exist. That
is a real result and the most likely one to be quietly dropped, because it makes the
comparison uninteresting rather than making it lost — so it is named, first, and it is
checked first.
"""

from dataclasses import dataclass
from enum import StrEnum

# The bands whose items produced an answer, and the one that produced a RIGHT one. A
# pair needs both arms to have answered: an item one arm declined is not evidence about
# which arm is better, it is evidence that one of them declined.
from loopeng.agent.classify import BAND_CORRECT, band_of
from loopeng.sweep.conditions import ANSWERED_BANDS


class Ending(StrEnum):
    """The three, named before the data landed."""

    NO_GAP_TO_CLOSE = "no_gap_to_close"
    REACHED = "reached"
    APPROACHED_BUT_SHORT = "approached_but_short"


@dataclass(frozen=True)
class Selection:
    """The reading, and every number it was selected on."""

    ending: Ending
    n_paired: int
    # Items the cheap-plus-loops arm got right and the frontier arm did not, and the
    # reverse. These are the discordant pairs; the concordant ones carry no information
    # about which arm is better and are excluded from the comparison by construction.
    only_cheap: int
    only_frontier: int
    # The same, for the frontier arm against the cheap arm WITHOUT loops. This is what
    # decides whether a gap existed at all.
    gap_only_frontier: int
    gap_only_cheap: int

    @property
    def gap_existed(self) -> bool:
        return self.gap_only_frontier > self.gap_only_cheap

    def render(self) -> str:
        """One paragraph, carrying its own basis. Never a bare verdict."""
        if self.ending is Ending.NO_GAP_TO_CLOSE:
            return (
                f"NO GAP TO CLOSE. Over {self.n_paired} paired items the frontier model "
                f"bare was not ahead of the budget model bare: {self.gap_only_frontier} "
                f"items to {self.gap_only_cheap}. Whether loops close a gap is a "
                f"question about a distance this run did not find, and the other two "
                f"readings are claims about a quantity that does not exist here."
            )
        if self.ending is Ending.REACHED:
            return (
                f"REACHED. The frontier model bare was ahead of the budget model bare "
                f"({self.gap_only_frontier} items to {self.gap_only_cheap}), and with "
                f"the loops the budget model was not behind it: {self.only_cheap} items "
                f"to {self.only_frontier} over {self.n_paired} paired. No p-value: this "
                f"compares two models, and that refusal is in code."
            )
        return (
            f"APPROACHED BUT SHORT. The frontier model bare was ahead of the budget "
            f"model bare ({self.gap_only_frontier} items to {self.gap_only_cheap}), and "
            f"with the loops the budget model was still behind it by "
            f"{self.only_frontier - self.only_cheap} discordant items "
            f"({self.only_cheap} to {self.only_frontier}, over {self.n_paired} paired). "
            f"No p-value: this compares two models, and that refusal is in code."
        )


def _correct_by_item(arm: dict) -> dict[str, bool]:
    """`{item_id: was_correct}` over items this arm ANSWERED.

    An item the arm declined is absent rather than False. Scoring an abstention as
    wrong is the mistake this project spent an outcome category fixing: the reference
    arm at L0 declined nineteen items, and counting those as failures would rank a
    model that knew what it was missing below one that invented a number.
    """
    answered = {}
    for row in arm["items"]:
        band = band_of(row["outcome"])
        if band in ANSWERED_BANDS:
            answered[row["item_id"]] = band == BAND_CORRECT
    return answered


def _discordant(a: dict[str, bool], b: dict[str, bool]) -> tuple[int, int, int]:
    """`(n_paired, only_a, only_b)` over items BOTH arms answered."""
    shared = sorted(set(a) & set(b))
    only_a = sum(1 for item in shared if a[item] and not b[item])
    only_b = sum(1 for item in shared if b[item] and not a[item])
    return len(shared), only_a, only_b


def select(*, cheap_bare: dict, cheap_looped: dict, frontier_bare: dict) -> Selection:
    """Which ending this data selects. Mechanical, and checked in that order.

    `cheap_bare` is condition A, `cheap_looped` is condition C, `frontier_bare` is D.
    """
    bare = _correct_by_item(cheap_bare)
    looped = _correct_by_item(cheap_looped)
    frontier = _correct_by_item(frontier_bare)

    _, gap_cheap, gap_frontier = _discordant(bare, frontier)
    n_paired, only_cheap, only_frontier = _discordant(looped, frontier)

    if gap_frontier <= gap_cheap:
        ending = Ending.NO_GAP_TO_CLOSE
    elif only_frontier <= only_cheap:
        ending = Ending.REACHED
    else:
        ending = Ending.APPROACHED_BUT_SHORT

    return Selection(
        ending=ending, n_paired=n_paired,
        only_cheap=only_cheap, only_frontier=only_frontier,
        gap_only_frontier=gap_frontier, gap_only_cheap=gap_cheap,
    )
