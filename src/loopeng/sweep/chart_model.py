"""What both chart renderers agree on, defined once.

There are two renderers and both reasons for that are real and documented:
`loopeng.sweep.charts` builds SVG for the live views, where a figure is redrawn while a
sweep lands and must degrade to "in progress, n=NN so far", and there is no plotting
dependency to install at a venue. `tools/render_readme_charts.py` builds static PNGs of a
frozen measurement, because that is what renders on GitHub.

What was NOT a real reason was implementing the shared layer twice. Both independently
carried cell ordering, worker/frontier colouring, the hatched-outline convention for
stored bars, the value-and-n gutter — and **their own copies of the caption prose**.
`DIAL_CAPTION` and `REFERENCE_CAPTION` existed in each file, and the Wilson and cluster
caveats were typed out twice, so a correction to one did not reach the other. That is the
drift README §6 argues against when it justifies thin demo files, applied to the two
places where a disclosure reaching a reader actually matters.

So: the prose and the cell-to-row transform live here. Only geometry and drawing calls
stay backend-specific.

THE ORDERING CHANGED, DELIBERATELY
----------------------------------

`reference` used to be the FIRST sort key, so every stored cell sorted into a block at
the bottom — live bars, then stored bars. It is now the LAST key, which puts each stored
cell immediately beneath its live counterpart. In `fill` mode the keys are disjoint and
nothing is adjacent to anything, so this only shows up in `compare` mode, which is where
"paired on the same row" is the entire point.
"""

# ---------------------------------------------------------------------------
# The prose. Defined HERE and nowhere else; a test asserts neither renderer
# redefines any of it.
# ---------------------------------------------------------------------------
from loopeng.sweep.diff import ALPHA, MIN_DISCORDANT

REFERENCE_CAPTION = (
    "Cells marked REFERENCE were NOT computed in this session. They are measurements "
    "taken on the date shown and are displayed for context only. Recomputing them here "
    "would cost roughly ten times the delivery budget, so they are cited rather than "
    "re-run — and they are drawn differently so that is impossible to miss. Presenting "
    "a stored number as though it had just been computed would break the cost "
    "constraint quietly, which is worse than not showing it at all."
)

# The two caveats that travel with every interval in this project. Composed into the
# captions below rather than restated in each, so a correction lands once.
CROSS_MODEL_CAVEAT = (
    "THE BARS ARE NOT COMPARABLE ACROSS MODELS: Haiku is pinned to temperature=0, "
    "Sonnet 5 rejects non-default sampling parameters and cannot be pinned, so Haiku's "
    "bars carry sampling noise only while Sonnet's carry sampling noise plus "
    "run-to-run variance. Within a model they are comparable."
)

CLUSTER_CAVEAT = (
    "Items are 10 clusters of 5 parameterisations, not 50 independent trials, so every "
    "interval is narrower than the evidence supports."
)

DIAL_CAPTION = (
    "Silent-error rate, over answers that ran and returned. Error bars are Wilson 95%. "
    f"{CROSS_MODEL_CAVEAT} {CLUSTER_CAVEAT}"
)

COST_CAPTION = (
    "Estimated cost per cell. Tokens are measured; dollars are those tokens times a "
    "hand-entered price table, so every figure here is an estimate and keeps the est. "
    "prefix. Failed, timed-out and budget-exhausted calls are included, because they "
    "billed."
)

DELTA_CAPTION = (
    "Paired differences in silent-error rate, in percentage points. Positive means the "
    "second arm has MORE silent errors. Zero is drawn: it is a real delta, not a missing "
    "one. The difference is computed over items BOTH arms answered, which is the same "
    "set the p-value uses — so it will not always equal the gap between the two bars on "
    "DIAL, and where it does not, the bars are the misleading pair. Significance is "
    f"exact McNemar. Below {MIN_DISCORDANT} discordant pairs no split of the data can "
    f"reach p < {ALPHA}, so those rows say so instead of showing a number. Intervals are "
    f"a normal approximation on the paired difference. {CLUSTER_CAVEAT} A systematic "
    "weakness in one pattern can produce five discordant pairs that are really one "
    "observation, so the honest statement is directional."
)

# The canonical abstention caption, and it is deliberately WORD FOR WORD what
# assets/abstention.png already carries. The committed images are the author's measured
# figures and must stay byte-identical, so unifying this string had to mean adopting the
# existing one rather than writing a better one. Anything the live chart wants to add
# goes in ABSTENTION_LIVE_NOTE below, where it cannot reach the PNG.
ABSTENTION_CAPTION = (
    "Each point is one abstention threshold. Moving right answers more questions; "
    "moving up gets more of the answered ones right. The trade is the point — a "
    "single accuracy number hides it completely. Error bars are Wilson 95% on "
    "precision. Items are clustered parameterisations rather than independent "
    "trials, so every interval is narrower than the evidence supports."
)

# Only true of the live chart: the README figure is a frozen curve, so "free to
# recompute" would be a claim about something the reader cannot do with that image.
ABSTENTION_LIVE_NOTE = (
    "Computed from the cell's own per-item telemetry — whether the query ran, how many "
    "times the verifier sent it back, and which branch terminated the run. No extra "
    "model call, so the whole curve is free to recompute over runs already measured."
)

NOT_MEASURED = "not yet measured"

# The palette, shared so a role is the same colour in both media.
WORKER_COLOUR = "#0ea5e9"
FRONTIER_COLOUR = "#f97316"
PENDING_COLOUR = "#94a3b8"


def role_colour(role: str, *, pending: bool = False) -> str:
    """One colour per role, in both media. Pending overrides, because "still running"
    is more important to see than which model is running."""
    if pending:
        return PENDING_COLOUR
    return WORKER_COLOUR if role == "worker" else FRONTIER_COLOUR


def ordered_cells(cells) -> list[dict]:
    """Sorted explicitly, with `reference` LAST.

    File order is not a contract and a reordered input must not silently produce a
    different image. `reference` sorts last so a stored cell lands beside its live
    counterpart rather than in a block at the bottom — see the module docstring.
    """
    return sorted(
        cells,
        key=lambda c: (c["role"], c["level"], c["mode"], c["replicate"],
                       bool(c.get("reference"))),
    )


def label_for(cell: dict) -> str:
    """The row label. A stored cell says so in the label, not only in a caption."""
    if cell.get("reference"):
        return f"REFERENCE · {cell['label']}"
    return cell["label"]


def note_for(cell: dict, text: str) -> str:
    """The value printed beside a bar, with the date on it when it is stored."""
    if cell.get("reference"):
        return f"{text}  [REFERENCE, measured {cell.get('measured_on', 'date unknown')}]"
    return text


def money(value: float | None) -> str:
    """Always `est.`. Tokens are measured; dollars are a hand-entered price table."""
    return f"est. ${value:.4f}" if value else NOT_MEASURED


def bar_rows(cells, *, metric: str) -> list[dict]:
    """Cells as drawable rows, for either backend.

    `metric` is "rate" or "cost". Both backends get the same rows for the same payload,
    which is what stops the two figures from disagreeing about ordering, colour, the
    reference convention, or what a cell with nothing landed should say.
    """
    rows = []
    for cell in ordered_cells(cells):
        pending = not cell["complete"]
        if metric == "rate":
            value = cell["rate_value"]
            lo, hi = cell["rate_ci_low"], cell["rate_ci_high"]
            note = note_for(cell, cell["silent_error_rate"])
        elif metric == "cost":
            value = cell["cost_usd"]["value"] or None
            lo = hi = None
            note = note_for(cell, money(value))
        else:
            raise ValueError(f"unknown metric {metric!r}; expected 'rate' or 'cost'")
        rows.append({
            "key": cell["key"],
            "label": label_for(cell),
            "role": cell["role"],
            "value": value,
            "lo": lo,
            "hi": hi,
            "n": cell.get("rate_n", 0),
            "pending": pending,
            "reference": bool(cell.get("reference")),
            "note": note,
        })
    return rows
