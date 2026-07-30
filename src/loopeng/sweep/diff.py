"""The differences between cells, tested rather than eyeballed.

`loopeng.paired` has implemented exact McNemar correctly from the start. It was wired
into the TRAP demo and the views, and **never into the sweep** — even though
`verify/batch.py` already builds `{item_id: was_correct}`, which is exactly McNemar's
input, and cell files retain the per-item detail. So the sweep could show you two bars
and could not tell you whether they differed. This module is that missing wiring.

There is no second McNemar here. `paired.compare` does the test; this decides what is
worth comparing, and what may not be claimed from the result.

FOUR FAMILIES, AND WHY EACH ONE
-------------------------------

  mode      L0 one-shot vs L0 loop, within a model. The pre-registered headline.
  level     L0 vs L3 at a fixed mode, within a model. What the rules are worth.
  live      the same cell key, computed now against the stored baseline. The cloner's
            "did I reproduce this?", which nothing could answer before.
  secondary Haiku + loop vs Sonnet one-shot, the pre-registered NAMED SECONDARY. The
            only cross-model family, and therefore the only one whose p-value is
            refused. It exists precisely so that refusal is reachable: the first three
            families are within-model by construction, so a cross-model guard among
            them would be decoration nothing could trigger. This is also the comparison
            `views/dial.py` puts on screen, so it is the one that most needed deriving.

THE DELTA IS PAIRED, AND IT IS NOT THE DIFFERENCE BETWEEN THE BARS
------------------------------------------------------------------

Each bar's silent-error rate is over the items *that cell* ran. Two cells did not run
the same set — a query that never returned in one arm is not in its denominator — so
subtracting the bars mixes a real difference with a difference in denominators.

The delta reported here is over items **both** arms answered, which is the same set the
p-value is computed on. It will not always equal the gap between the bars, and when it
does not, the bars are the misleading pair.

WHAT IT REFUSES TO SAY
----------------------

**A cross-model comparison gets no p-value.** Haiku is pinned to temperature=0 and
Sonnet 5 rejects non-default sampling, so Haiku's intervals carry sampling noise only
while Sonnet's carry sampling noise plus run-to-run variance. That guardrail is stated
in `orchestrator.pre_registration` and in the DIAL caption; a chart that drew a
significance claim across it anyway would be a guardrail that exists in prose and
nowhere else, which is the defect this project is about.

**Below `MIN_DISCORDANT` nothing is distinguishable, structurally.** With n discordant
pairs all falling one way the two-sided exact p is 2/2**n, so below that count no split
of the data can reach significance. The threshold is computed from alpha rather than
picked.

**Every result carries both `measured_on` values**, so a live-vs-stored comparison
cannot be read as two fresh measurements.

**The clustering caveat travels with the number.** Items are 10 clusters of 5
parameterisations, so a systematic weakness in one pattern can produce five discordant
pairs that are really one observation. Every interval here is narrower than the evidence
supports, and `paired.CLUSTERING_CAVEAT` says so on every result.
"""

from dataclasses import dataclass
from pathlib import Path

from loopeng.paired import CLUSTERING_CAVEAT, PairedComparison, compare
from loopeng.sweep.orchestrator import load_all
from loopeng.sweep.reference import keeps_per_item_outcomes, paired_map

ALPHA = 0.05

LIVE_STAMP = "computed this run"

CROSS_MODEL_REFUSAL = (
    "No p-value: this compares two models, and their bars do not mean the same thing. "
    "Haiku is pinned to temperature=0; Sonnet 5 rejects non-default sampling and cannot "
    "be pinned, so its numbers carry run-to-run variance that Haiku's do not. A "
    "significance claim across that asymmetry would be measuring the asymmetry."
)


def min_discordant_for_significance(alpha: float = ALPHA) -> int:
    """Smallest discordant count at which exact McNemar CAN reach p < alpha.

    Computed rather than typed, because the reason is structural. With n discordant
    pairs all falling one way the two-sided exact p is 2/2**n. Below the n returned
    here, no arrangement of the data produces a significant result — so "not
    distinguishable at this n" is a fact about the design, not about this run.
    """
    n = 1
    while 2 / (2**n) >= alpha:
        n += 1
    return n


MIN_DISCORDANT = min_discordant_for_significance()


@dataclass(frozen=True)
class Comparison:
    """One difference, with everything needed to refuse to over-read it."""

    kind: str
    key_a: str
    key_b: str
    label_a: str
    label_b: str
    measured_on_a: str
    measured_on_b: str
    paired: PairedComparison
    cross_model: bool
    # Which sides kept the per-item outcomes a paired test needs. Carried because
    # "nothing to pair" has two causes and the message used to report only one of them
    # — see `unpairable_because`.
    keeps_items_a: bool = True
    keeps_items_b: bool = True

    @property
    def n_pairs(self) -> int:
        return self.paired.n_pairs

    @property
    def n_discordant(self) -> int:
        return self.paired.n_discordant

    @property
    def delta_pp(self) -> float | None:
        """Silent-error rate of B minus A, in percentage points, over PAIRED items.

        Signed: negative means B has fewer silent errors than A. None when the two
        cells share no answered items, because there is no pairing to difference.
        """
        if not self.n_pairs:
            return None
        only_a, only_b = self.paired.only_a_correct, self.paired.only_b_correct
        return 100.0 * (only_a - only_b) / self.n_pairs

    @property
    def interval_pp(self) -> tuple[float, float] | None:
        """Normal-approximation interval on the paired difference, in points.

        The paired standard error, not two independent Wilson intervals: the arms
        answered the same questions, and treating them as independent both throws away
        the pairing and widens the interval on the axis that carries the information.

        It is an approximation and it is optimistic, for the reason in CLUSTERING_CAVEAT.
        """
        n = self.n_pairs
        if not n:
            return None
        b, c = self.paired.only_a_correct, self.paired.only_b_correct
        variance = ((b + c) - (b - c) ** 2 / n) / n**2
        if variance <= 0:
            return (self.delta_pp, self.delta_pp)
        # 1.96: the two-sided normal quantile at ALPHA. Named where it is used rather
        # than hidden in a constant, because it is the only place ALPHA becomes a number.
        half = 100.0 * 1.959963984540054 * variance**0.5
        return (self.delta_pp - half, self.delta_pp + half)

    @property
    def p_value(self) -> float | None:
        """None for a cross-model pair, and it is a refusal rather than an absence."""
        if self.cross_model:
            return None
        return self.paired.p_value

    @property
    def distinguishable(self) -> bool:
        p = self.p_value
        return (
            p is not None
            and self.n_discordant >= MIN_DISCORDANT
            and p < ALPHA
        )

    @property
    def unpairable_because(self) -> str:
        """Why there is nothing to pair. TWO different facts, and one of them is ours.

        The message here used to be "no shared answered items between A and B" in both
        cases, which reads as a property of the data: these two arms answered disjoint
        sets. For every Sonnet pair that was false. The items overlapped perfectly well
        when they were measured; `build_reference` discards them at freeze time, so the
        stored frontier cells carry no per-item outcomes and can never be paired with
        anything. A diagnostic that misattributes its own cause sends a reader looking
        at the measurement for a defect in the freeze.
        """
        stripped = [label for label, keeps in
                    ((self.label_a, self.keeps_items_a), (self.label_b, self.keeps_items_b))
                    if not keeps]
        if stripped:
            return (
                f"per-item outcomes were not retained when "
                f"{' and '.join(stripped)} {'was' if len(stripped) == 1 else 'were'} "
                f"frozen, so this pair cannot be tested — nothing to pair. The items "
                f"themselves are not the problem: a paired test needs "
                f"{{item_id: was_correct}} and the freeze drops it"
            )
        return (
            f"{self.label_a} and {self.label_b} share no answered items — nothing to "
            f"pair, so nothing to compare"
        )

    def reading(self) -> str:
        """What may be said. Directional at most, never a specific gap."""
        if self.cross_model:
            return CROSS_MODEL_REFUSAL
        if not self.n_pairs:
            return self.unpairable_because
        if self.n_discordant < MIN_DISCORDANT:
            return (
                f"not distinguishable at this n: {self.n_discordant} discordant of "
                f"{self.n_pairs}, and below {MIN_DISCORDANT} discordant no split of the "
                f"data can reach p < {ALPHA} — this is a property of the design, not of "
                f"this run"
            )
        return self.paired.render()

    def provenance(self) -> str:
        """Both dates, on the row. A caption is read once; a row is read every time."""
        if self.measured_on_a == self.measured_on_b == LIVE_STAMP:
            return "both computed this run"
        return f"{self.label_a}: {self.measured_on_a} · {self.label_b}: {self.measured_on_b}"

    def as_dict(self) -> dict:
        return {
            "kind": self.kind,
            "key_a": self.key_a, "key_b": self.key_b,
            "label_a": self.label_a, "label_b": self.label_b,
            "measured_on_a": self.measured_on_a, "measured_on_b": self.measured_on_b,
            "cross_model": self.cross_model,
            "n_pairs": self.n_pairs, "n_discordant": self.n_discordant,
            "delta_pp": self.delta_pp, "interval_pp": self.interval_pp,
            "p_value": self.p_value, "distinguishable": self.distinguishable,
            "reading": self.reading(), "provenance": self.provenance(),
            "table": self.paired.as_dict(),
            "caveat": CLUSTERING_CAVEAT,
        }


def _stamp(cell: dict) -> str:
    return cell.get("measured_on", LIVE_STAMP) if cell.get("reference") else LIVE_STAMP


def _side(cell: dict) -> str:
    return "REFERENCE" if cell.get("reference") else "LIVE"


def _build(kind: str, a: dict, b: dict) -> Comparison:
    return Comparison(
        kind=kind,
        key_a=a["key"], key_b=b["key"],
        label_a=f"{_side(a)} {a['label']}", label_b=f"{_side(b)} {b['label']}",
        measured_on_a=_stamp(a), measured_on_b=_stamp(b),
        paired=compare(paired_map(a), paired_map(b),
                       label_a=a["label"], label_b=b["label"]),
        cross_model=a["role"] != b["role"],
        keeps_items_a=keeps_per_item_outcomes(a),
        keeps_items_b=keeps_per_item_outcomes(b),
    )


def _complete(cells) -> list[dict]:
    """Incomplete cells are excluded. A partial cell differenced against a finished one
    reports a gap that is mostly the missing items."""
    return [c for c in cells if c.get("complete")]


def _index(cells) -> dict[tuple, dict]:
    """Live cells win the slot. A stored twin is compared separately, by live_vs_reference."""
    indexed: dict[tuple, dict] = {}
    for cell in cells:
        slot = (cell["role"], cell["level"], cell["mode"], cell["replicate"])
        if slot not in indexed or not cell.get("reference"):
            indexed[slot] = cell
    return indexed


def mode_deltas(cells) -> list[Comparison]:
    """L0 one-shot vs L0 loop, within a model. The pre-registered headline."""
    indexed = _index(_complete(cells))
    out = []
    for (role, level, mode, replicate), cell in sorted(indexed.items()):
        if mode != "one_shot":
            continue
        looped = indexed.get((role, level, "loop", replicate))
        if looped:
            out.append(_build("mode", cell, looped))
    return out


def level_deltas(cells) -> list[Comparison]:
    """L0 vs L3 at a fixed mode, within a model. What writing the rules down is worth."""
    indexed = _index(_complete(cells))
    out = []
    for (role, level, mode, replicate), cell in sorted(indexed.items()):
        if level != "L0":
            continue
        complete_spec = indexed.get((role, "L3", mode, replicate))
        if complete_spec:
            out.append(_build("level", cell, complete_spec))
    return out


# The pre-registered NAMED SECONDARY, declared as a pair of slots rather than as two
# cell keys, so it follows the level rather than being typed once per level.
SECONDARY_A = ("worker", "loop")
SECONDARY_B = ("frontier", "one_shot")


def named_secondary_deltas(cells) -> list[Comparison]:
    """Haiku + loop vs Sonnet one-shot, at each level. Cross-model, so no p-value.

    `orchestrator.pre_registration` names this as the NAMED SECONDARY and says in words
    that it is "underpowered AND carries the variance asymmetry". This is the family that
    makes the asymmetry refusal reachable in code instead of only in prose.
    """
    indexed = _index(_complete(cells))
    levels = sorted({level for _role, level, _mode, _rep in indexed})
    out = []
    for level in levels:
        a = indexed.get((SECONDARY_A[0], level, SECONDARY_A[1], 0))
        b = indexed.get((SECONDARY_B[0], level, SECONDARY_B[1], 0))
        if a and b:
            out.append(_build("secondary", a, b))
    return out


def live_vs_reference(cells) -> list[Comparison]:
    """The same cell key, computed now against the stored baseline.

    The cloner's question, and the one `fill` mode made unanswerable by deleting the
    stored cell as soon as a live one existed.
    """
    live = {c["key"]: c for c in _complete(cells) if not c.get("reference")}
    stored = {c["key"]: c for c in cells if c.get("reference")}
    return [
        _build("live_vs_reference", stored[key], live[key])
        for key in sorted(live.keys() & stored.keys())
    ]


def all_comparisons(cells) -> list[Comparison]:
    """Every difference these cells support, in a stable order.

    Includes the ones that cannot be tested. Filtering them out here would let a chart
    quietly show fewer rows than the data implies — see `partition`.
    """
    return (live_vs_reference(cells) + mode_deltas(cells) + level_deltas(cells)
            + named_secondary_deltas(cells))


NO_PER_ITEM_DETAIL = (
    "not shown: one side keeps no per-item record, so there is nothing to pair. The "
    "stored FRONTIER cells strip their items — SQL and rows are development-only bulk — "
    "and a paired test needs {item_id: was_correct}. The stored WORKER baseline keeps "
    "that map, which is why the Haiku comparisons work and the Sonnet ones do not."
)


def partition(comparisons) -> tuple[list[Comparison], list[Comparison]]:
    """(testable, untestable). Both returned, so neither can be dropped silently.

    A chart that rendered only the testable rows would show fewer comparisons than the
    cells on screen imply and say nothing about the difference — which is the same
    failure as a bar that renders zero for "not measured".
    """
    testable = [c for c in comparisons if c.n_pairs]
    return testable, [c for c in comparisons if not c.n_pairs]


def from_disk(sweep_dir: Path, reference_cells=()) -> list[Comparison]:
    """Comparisons over the cell files on disk, plus whatever reference set is supplied."""
    return all_comparisons(load_all(sweep_dir) + list(reference_cells))
