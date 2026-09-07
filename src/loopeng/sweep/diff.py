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
  secondary agent + loop vs reference one-shot, the pre-registered NAMED SECONDARY. The
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

**A cross-model comparison gets no p-value.** The reason given here used to be a
sampling asymmetry — one model pinned to temperature=0, the other unable to be — and
that asymmetry is gone: under the current policy neither scoring model accepts a pinned
temperature, and both carry the same class of best-effort-seed residual.

The refusal stands on the plainer ground it always really rested on. A cross-model pair
differs in model, price and training at once, so a significance claim over it would
attribute a confounded difference to whichever axis the chart happens to be about. The
guardrail is stated in `orchestrator.pre_registration` and in the DIAL caption, and
enforced here; a chart that drew the claim anyway would be a guardrail that exists in
prose and nowhere else, which is the defect this project is about.

**Below `MIN_DISCORDANT` nothing is distinguishable, structurally.** With n discordant
pairs all falling one way the two-sided exact p is 2/2**n, so below that count no split
of the data can reach significance. The threshold is computed from alpha rather than
picked.

**Every result carries both `measured_on` values**, so a live-vs-stored comparison
cannot be read as two fresh measurements.

**The clustering caveat travels with the number.** Items are clusters of
parameterisations, so a systematic weakness in one pattern can produce a whole cluster
of discordant pairs that are really one observation. Every interval here is narrower
than the evidence supports, and `paired.CLUSTERING_CAVEAT` says so on every result.
"""

from dataclasses import dataclass
from pathlib import Path

from loopeng.paired import CLUSTERING_CAVEAT, PairedComparison, compare
from loopeng.sweep.orchestrator import load_all
from loopeng.sweep.runner import Cell

ALPHA = 0.05

LIVE_STAMP = "computed this run"

CROSS_MODEL_REFUSAL = (
    "No p-value: this compares two models. Both are reasoning models that reject a "
    "pinned temperature, so both carry run-to-run variance, and this design measures "
    "that residual rather than assuming it away. A cross-model claim would be reading "
    "a difference between two noisy arms as if only one thing had changed."
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
    # How many items each arm actually ANSWERED. Carried so a reader can see
    # when a pair stands on fewer items than either arm ran — which is what an
    # arm that declines looks like from a paired test, and is invisible from
    # n_pairs alone.
    n_answered_a: int = 0
    n_answered_b: int = 0
    # Cell keys this comparison NEEDED and did not find. Empty for every pair that
    # was actually formed.
    #
    # A comparison used to be emitted only when both its cells existed, so a
    # PRE-REGISTERED result whose cell was missing did not become an empty row — it
    # stopped being a row. The pre-registration is read aloud before the first cell
    # runs and the room checks the result against it, so a claim that quietly has no
    # row is a claim nobody notices went missing. See `named_secondary_deltas`.
    missing: tuple[str, ...] = ()

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
        # Narrowed explicitly. `delta_pp` is `float | None` and is None on exactly
        # the same `n_pairs` guard above, so this is safe today — but only because
        # two properties happen to share a condition, which is the kind of coupling
        # that survives until someone changes one of them.
        delta = self.delta_pp
        if delta is None:
            return None
        b, c = self.paired.only_a_correct, self.paired.only_b_correct
        variance = ((b + c) - (b - c) ** 2 / n) / n**2
        if variance <= 0:
            return (delta, delta)
        # 1.96: the two-sided normal quantile at ALPHA. Named where it is used rather
        # than hidden in a constant, because it is the only place ALPHA becomes a number.
        half = 100.0 * 1.959963984540054 * variance**0.5
        return (delta - half, delta + half)

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
        sets. For every pair involving a FROZEN cell that was false. The items overlapped
        perfectly well when they were measured; the freeze discarded the per-item
        outcomes, so a stored cell could never be paired with anything. A diagnostic that
        misattributes its own cause sends a reader looking at the measurement for a
        defect in the freeze.

        Short, because it is what the DELTA chart prints in a row. `reading` adds the
        explanation; a row is a label, not a paragraph.
        """
        if self.missing:
            return (
                f"not run: {' and '.join(self.missing)} "
                f"{'is' if len(self.missing) == 1 else 'are'} not on disk"
            )
        stripped = [label for label, keeps in
                    ((self.label_a, self.keeps_items_a), (self.label_b, self.keeps_items_b))
                    if not keeps]
        if stripped:
            return (
                f"per-item outcomes were not retained when "
                f"{' and '.join(stripped)} {'was' if len(stripped) == 1 else 'were'} "
                f"frozen — nothing to pair"
            )
        return (
            f"{self.label_a} and {self.label_b} share no answered items — nothing to pair"
        )

    def reading(self) -> str:
        """What may be said. Directional at most, never a specific gap."""
        if self.missing:
            # BEFORE the cross-model refusal. "No p-value: this compares two models" is
            # true of the named secondary and says nothing about the fact that one of
            # its cells does not exist — a reader would take it for a measured pair
            # that merely cannot be tested, which is the more reassuring of the two.
            return (
                f"NOT MEASURED — {self.unpairable_because}. This comparison is "
                f"pre-registered, so its absence is reported rather than left as a "
                f"missing row: nothing was computed for it and nothing was substituted."
            )
        if self.cross_model:
            return CROSS_MODEL_REFUSAL
        if not self.n_pairs:
            if self.keeps_items_a and self.keeps_items_b:
                return f"{self.unpairable_because}, so nothing to compare"
            return (
                f"{self.unpairable_because}. The items are not the problem: a paired "
                f"test needs {{item_id: was_correct}} and the freeze drops it, so this "
                f"is a property of the freeze rather than of the measurement"
            )
        if self.n_discordant < MIN_DISCORDANT:
            return (
                f"not distinguishable at this n: {self.n_discordant} discordant of "
                f"{self.n_pairs}, and below {MIN_DISCORDANT} discordant no split of the "
                f"data can reach p < {ALPHA} — this is a property of the design, not of "
                f"this run"
            )
        return self.paired.render()

    def provenance(self) -> str:
        """The DENOMINATORS, on the row. A caption is read once; a row is read every time.

        This used to carry both measurement dates, and once every cell became live it
        said "both computed this run" forever — a sub-line under every row with one
        possible value.

        What belongs there instead is the n, and specifically the n that DIFFERS. This
        project's rule is that every figure carries its n; a paired delta has three of
        them — the pairs, and each arm's answered count — and they come apart exactly
        when one arm declines. The reference arm answered 36 of the 60 it was asked
        while the other answered all 60, and a reader glancing at "-75.0 pp" cannot
        infer that from the interval.
        """
        if self.n_answered_a == self.n_answered_b == self.n_pairs:
            return f"n={self.n_pairs} paired · both arms answered all of them"
        # Compact, because it has to fit the reading gutter beside the number it
        # qualifies. What the asymmetry MEANS is in the caption; what a reader needs
        # on the row is that it exists and by how much.
        return (
            f"n={self.n_pairs} paired · arms answered "
            f"{self.n_answered_a} vs {self.n_answered_b}"
        )

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
    """When this cell was computed.

    Every cell is computed in the run that renders it, so this is a constant now —
    kept as a function because the provenance row still prints it, and a row that
    silently stopped carrying a date would be indistinguishable from one that never
    had one.
    """
    return LIVE_STAMP


def keeps_per_item_outcomes(cell: dict) -> bool:
    """Whether this cell retained the per-item outcomes a paired test needs.

    The distinction a diagnostic depends on. A cell with neither `items` nor `paired`
    can never be paired with anything; a cell that HAS the record and simply overlaps
    nothing with its partner is a different fact, about the data rather than about the
    file, and only one of the two is fixable.

    Rehomed from `sweep/reference.py` when the stored-measurement path was removed. It
    was never reference-specific — it reads a cell, and every cell is live now.
    """
    return "paired" in cell or "items" in cell


def paired_map(cell: dict) -> dict[str, bool]:
    """`{item_id: was_correct}` for a cell. McNemar's input.

    An empty map for a cell that carries neither, which `paired.compare` handles by
    pairing nothing rather than by inventing evidence.

    THE `items` TOLERANCE IS DELIBERATE AND IT IS NOT THE DEFECT THAT REMOVED THE
    ABSTENTION FALLBACK.

    `cells` here come from `load_all`, which reads whatever JSON is in the directory —
    including a cell written before the stored path was removed. A cell carrying neither
    `paired` nor `items` cannot be produced by any code path in this build any more, but
    it can still be on someone's disk, and the degradation is REPORTED: `keeps_items_a`
    and `keeps_items_b` are set from `keeps_per_item_outcomes`, and
    `unpairable_because` distinguishes "these arms share no answered items" from "the
    per-item outcomes were not retained when this was frozen".

    That is the whole difference. A lookup may degrade if something downstream says so.
    The abstention selector degraded into a DIFFERENT MEASUREMENT with nothing anywhere
    to signal it.

    `row["ran_and_returned"]` is required, though, and that part of the change stands: a
    cell that HAS items has rows carrying it, and `.get` there dropped malformed rows out
    of a paired comparison one at a time, silently, changing the denominator.
    """
    if "paired" in cell:
        return {str(k): bool(v) for k, v in cell["paired"].items()}
    return {
        row["item_id"]: bool(row["correct"])
        for row in cell.get("items", ())
        if row["ran_and_returned"]
    }


def _build(kind: str, a: dict, b: dict) -> Comparison:
    return Comparison(
        kind=kind,
        key_a=a["key"], key_b=b["key"],
        label_a=a["label"], label_b=b["label"],
        measured_on_a=_stamp(a), measured_on_b=_stamp(b),
        paired=compare(paired_map(a), paired_map(b),
                       label_a=a["label"], label_b=b["label"]),
        cross_model=a["role"] != b["role"],
        keeps_items_a=keeps_per_item_outcomes(a),
        keeps_items_b=keeps_per_item_outcomes(b),
        # How many items each arm actually ANSWERED. Carried so a reader can see when
        # a pair stands on fewer items than either arm ran — which is what an arm that
        # declines looks like from a paired test, and is invisible from n_pairs alone.
        n_answered_a=len(paired_map(a)),
        n_answered_b=len(paired_map(b)),
    )


def _complete(cells) -> list[dict]:
    """Incomplete cells are excluded. A partial cell differenced against a finished one
    reports a gap that is mostly the missing items."""
    return [c for c in cells if c.get("complete")]


def _index(cells) -> dict[tuple, dict]:
    """One cell per slot. Every cell is live now, so the last one written wins."""
    indexed: dict[tuple, dict] = {}
    for cell in cells:
        slot = (cell["role"], cell["level"], cell["mode"], cell["replicate"])
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
SECONDARY_A = ("agent", "loop")
SECONDARY_B = ("reference", "one_shot")


def _absent(kind: str, slots: tuple[tuple, tuple], found: tuple) -> Comparison:
    """A pre-registered pair that could not be formed, as a row rather than a gap.

    Labels come from `Cell`, so a missing cell is named exactly as it would have been
    had it landed — the reader compares the row against the pre-registration without
    translating between two vocabularies.
    """
    cells = [Cell(role, level, mode, rep) for role, level, mode, rep in slots]
    return Comparison(
        kind=kind,
        key_a=cells[0].key, key_b=cells[1].key,
        label_a=cells[0].label, label_b=cells[1].label,
        measured_on_a=_stamp({}), measured_on_b=_stamp({}),
        # An empty paired comparison: n_pairs is 0, so `partition` files this under
        # untestable and no arithmetic anywhere treats it as evidence.
        paired=compare({}, {}),
        cross_model=cells[0].role != cells[1].role,
        missing=tuple(cell.key for cell, present in zip(cells, found, strict=True)
                      if present is None),
    )


def named_secondary_deltas(cells) -> list[Comparison]:
    """The agent with loops against the frontier model bare, at each level.

    Cross-model, so no p-value — see WHAT IT REFUSES TO SAY above. The models are named
    nowhere in this docstring on purpose: `SECONDARY_A` and `SECONDARY_B` are role slots,
    and the previous version spelled them out as two specific models, both of which had
    since stopped holding the roles.

    `orchestrator.pre_registration` names this as the NAMED SECONDARY. It is the family
    that makes the cross-model refusal reachable in code instead of only in prose: the
    other three families are within-model by construction, so a guard among them would be
    decoration nothing could trigger.
    """
    indexed = _index(_complete(cells))
    levels = sorted({level for _role, level, _mode, _rep in indexed})
    out = []
    for level in levels:
        slots = ((SECONDARY_A[0], level, SECONDARY_A[1], 0),
                 (SECONDARY_B[0], level, SECONDARY_B[1], 0))
        found = tuple(indexed.get(slot) for slot in slots)
        # EVERY level the sweep produced cells for gets a row, formed or not. Skipping
        # the unformed ones is what let a pre-registered comparison disappear from both
        # the DELTA chart and the terminal summary with nothing to mark its place.
        #
        # A profile that cannot produce this family at all — smoke runs the agent role
        # only — therefore reports it as not run rather than omitting it. That is the
        # honest reading: the pre-registration is printed whatever the profile, so a
        # profile that cannot deliver it should say so.
        out.append(_build("secondary", *found) if all(found)
                   else _absent("secondary", slots, found))
    return out


def all_comparisons(cells) -> list[Comparison]:
    """The comparisons the DELTA chart draws: L0 against L3, within each model.

    **Two families are deliberately not here, and both were measured before being
    dropped.** `mode_deltas` and `named_secondary_deltas` are still implemented, still
    correct, and still tested — a caller who wants them can have them. They are not
    fed to the chart.

    *Mode deltas* — one-shot against looped, within a model — is the A -> B and A -> C
    family. Measured on the 60 held-out items: condition A terminated `success` 60/60,
    so retry had nothing to retry and B fired zero retries; C's verifiers rejected 2.
    Five runs of the cheap arm scored 46, 51, 52, 52, 52, so the six-item difference
    is the arm's own spread. Exact McNemar returns p=0.031 over a mechanism that never
    fired.

    Drawing that would be worse than omitting it. The arithmetic is right and the
    subject is wrong, so the chart would be honest about its statistics and wrong
    about what it was showing — and a p-value on a row gives a dead comparison the
    visual weight of a live one. The finding travels as a caption sentence instead.

    *The named secondary* — cheap-plus-loops against frontier-bare — has no gap left
    to measure: the frontier model scored 60/60 on two separate runs. It stays
    implemented because the cross-model p-value refusal lives in that path and is
    worth keeping reachable.

    What remains is the comparison that is still paired, still large, and still real.
    Untestable rows are kept rather than filtered: dropping them would let the chart
    quietly show fewer rows than the data implies — see `partition`.
    """
    return level_deltas(cells)


# The footnote counts; the ROW names the cause. It used to do both, asserting "one side
# keeps no per-item record" over every untestable row — which is right for a cell the
# freeze stripped and wrong for two arms that answered nothing in common. Naming one
# cause for two different facts is the defect `Comparison.unpairable_because` exists to
# fix, so the footnote stops claiming to know which.
NO_PER_ITEM_DETAIL = (
    "not shown: nothing to pair, and each row says which of the two reasons applies — "
    "per-item outcomes discarded at freeze time, or two arms with no answered item in "
    "common. A paired test needs {item_id: was_correct}, and `build_reference` drops it "
    "along with the rest of `items`, because SQL and rows are development-only bulk. "
    "The COMMITTED reference set keeps that map in a sibling file for every cell it "
    "carries, so a cell frozen from your own sweep is the one that cannot be paired."
)


def partition(comparisons) -> tuple[list[Comparison], list[Comparison]]:
    """(testable, untestable). Both returned, so neither can be dropped silently.

    A chart that rendered only the testable rows would show fewer comparisons than the
    cells on screen imply and say nothing about the difference — which is the same
    failure as a bar that renders zero for "not measured".
    """
    testable = [c for c in comparisons if c.n_pairs]
    return testable, [c for c in comparisons if not c.n_pairs]


def from_disk(sweep_dir: Path) -> list[Comparison]:
    """Comparisons over the cell files on disk. There is no other source."""
    return all_comparisons(load_all(sweep_dir))


# How much of an arm's answered set a pair may lose before the DELTA chart says so.
#
# Lives here rather than in `chart_model` because it is a predicate about comparisons,
# not a caption or a row transform — and `chart_model` is a numeric-literal lint
# target, where a display-policy threshold is neither geometry nor a measurement and
# would have had to be exempted as something it is not.
#
# Not zero: arms differ by an item or two constantly, and a note that fires every time
# is a note nobody reads.
COVERAGE_TOLERANCE = 0.8


def coverage_is_asymmetric(comparisons, tolerance: float = COVERAGE_TOLERANCE) -> bool:
    """Did some pair lose a meaningful share of its items to one arm not answering?

    An arm that declines is scored only on the items it chose to answer, because the
    silent-error rate is computed over answers that ran and returned. That is the
    right denominator for the metric and the wrong thing to leave unexplained.
    """
    for comparison in comparisons:
        pairs = comparison.n_pairs
        if not pairs:
            continue
        largest = max(pairs, comparison.n_answered_a, comparison.n_answered_b)
        if pairs < largest * tolerance:
            return True
    return False
