"""What both chart renderers agree on, defined once.

There are two renderers, and the reason is lifetime rather than medium.
`loopeng.sweep.charts` draws whatever is on disk NOW: a figure has to degrade to "in
progress, n=NN so far" and is redrawn as a sweep lands, so it is not required to be
byte-identical between runs. `tools/render_readme_charts.py` draws a frozen measurement
that ships in the README, where byte-identity is the property that makes a change to an
image always a change to the data. Both are matplotlib.

(That was not the reason on file. The live backend hand-assembled SVG, justified by
"no plotting dependency to install at a venue" — untrue, matplotlib rendered `assets/`
and `uv sync` installed it — and by "the live Gradio views", which do not consume these
figures at all. See `sweep/charts.py`.)

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
from loopeng.registry import SCORING_ROLES, spec_for
from loopeng.sweep.diff import ALPHA, MIN_DISCORDANT

# The measurement the sampling caveat rests on, cited by path rather than quoted. Same
# rule the pre-registration follows: a number typed next to its own citation is the
# failure the caption is warning the room about.
NOISE_FLOOR_CITATION = "results/noise_floor_seeded.json"

def _sampling_caveat() -> str:
    """What the error bars carry, READ OFF the registry rather than described beside it.

    This was a fixed sentence and it had gone false in three separate ways at once:

      "Haiku is pinned to temperature=0"  — the agent role is not Haiku and pins no
                                            temperature; it pins `seed`.
      "Sonnet 5 rejects non-default …"    — the reference role is not Sonnet either.
      "…so one carries sampling noise      — THE ASYMMETRY IS GONE. Neither scoring
       only while the other carries          model accepts a pinned temperature now,
       sampling noise plus run-to-run"       so both bars carry the same class of
                                             residual.

    The third is the one that matters. A caption naming the wrong model is embarrassing;
    a caption warning a room about an asymmetry that no longer exists is telling them to
    discount a comparison for a reason that is not true — while staying silent about the
    residual both bars DO carry. And it contradicted the pre-registration printed by the
    same run, which has said "neither scoring model can be pinned" since the model policy
    changed.

    Derived, so the caption cannot disagree with the configuration it describes.
    """
    pinned = [spec_for(role) for role in SCORING_ROLES
              if "temperature" in spec_for(role).request_kwargs]
    named = ", ".join(spec_for(role).model_id for role in SCORING_ROLES)
    if not pinned:
        return (
            f"WHAT THE INTERVALS DO NOT COVER: neither scoring model ({named}) accepts "
            f"a pinned temperature — both reject a non-default sampling parameter — so "
            f"both pin a seed instead, which the vendor documents as best-effort rather "
            f"than a guarantee. Both bars therefore carry the SAME class of run-to-run "
            f"residual, and it is measured rather than assumed away: see "
            f"{NOISE_FLOOR_CITATION}. Across models the bars are still not a controlled "
            f"comparison — different model, different price, different training — which "
            f"is why a cross-model pair gets no p-value anywhere in this project."
        )
    unpinned = [spec_for(role) for role in SCORING_ROLES
                if "temperature" not in spec_for(role).request_kwargs]
    return (
        "THE BARS ARE NOT COMPARABLE ACROSS MODELS: "
        + ", ".join(spec.model_id for spec in pinned)
        + " pin a temperature and "
        + (", ".join(spec.model_id for spec in unpinned) or "no other model")
        + " cannot, so the first carry sampling noise only while the second carry "
          "sampling noise plus run-to-run variance. Within a model they are comparable."
    )


# The two caveats that travel with every interval in this project. Composed into the
# captions below rather than restated in each, so a correction lands once.
CROSS_MODEL_CAVEAT = _sampling_caveat()

CLUSTER_CAVEAT = (
    "Items are clusters of parameterisations over a small number of question "
    "patterns, not independent trials, so every "
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

# A proportion becomes a percentage for display. Furniture, not a finding:
# the measurement is the proportion, and this only changes its units.
PERCENT = 100  # layout: proportion to display percentage

# The palette, shared so a role is the same colour in both media.
WORKER_COLOUR = "#0ea5e9"
FRONTIER_COLOUR = "#f97316"
PENDING_COLOUR = "#94a3b8"


def role_colour(role: str, *, pending: bool = False) -> str:
    """One colour per role, in both media. Pending overrides, because "still running"
    is more important to see than which model is running."""
    if pending:
        return PENDING_COLOUR
    return WORKER_COLOUR if role == "agent" else FRONTIER_COLOUR


def ordered_cells(cells) -> list[dict]:
    """Sorted explicitly.

    File order is not a contract and a reordered input must not silently produce a
    different image.
    """
    return sorted(
        cells,
        key=lambda c: (c["role"], c["level"], c["mode"], c["replicate"]),
    )


def label_for(cell: dict) -> str:
    """The row label.

    There is no stored-cell case any more. Every cell a chart draws was computed in
    the run that is drawing it, so there is nothing here to badge — and the badge is
    gone rather than left as an unreachable branch, because a rendering path that can
    still express "stored" is a rendering path that can still show one.
    """
    return cell["label"]


def note_for(cell: dict, text: str) -> str:
    """The value printed beside a bar. Live, like everything else."""
    return text


def money(value: float | None) -> str:
    """Always `est.`. Tokens are measured; dollars are a hand-entered price table."""
    return f"est. ${value:.4f}" if value else NOT_MEASURED


def cache_note(cells) -> str:
    """What caching achieved across these cells, or why it did not apply.

    Reported on the COST chart because that is where the number it changes lives. It is a
    teaching beat as much as a figure: the apparatus for this — cache pricing, cache token
    accounting, a probe that measured which prefixes clear which model's minimum — was all
    present and `cache_control` was never set anywhere. The instrument existed, the number
    was known, and the optimisation was never switched on.

    Never a zero. A cell where caching could not apply did not achieve a nil hit rate; it
    had no cache to hit, and the note says which.
    """
    from loopeng.caching import hit_rate, saving_usd
    from loopeng.registry import spec_for

    read = written = 0
    saved = 0.0
    applied = []
    for cell in cells:
        tokens = cell.get("tokens") or {}
        cell_read = tokens.get("cache_read_input_tokens", 0)
        cell_written = tokens.get("cache_creation_input_tokens", 0)
        if not cell_read and not cell_written:
            continue
        applied.append(cell["key"])
        read += cell_read
        written += cell_written
        saved += saving_usd(tokens, spec_for(cell["role"]).model_id) or 0.0

    if not applied:
        # This paragraph described a vendor this project no longer calls. It said the
        # frontier role at L3 DOES clear the minimum, quoted two token counts from the
        # Anthropic-only design, and compared "Haiku's minimum" to "Sonnet's" — models
        # that hold no scoring role here. It was also the opposite of the measurement
        # that settled the question: the prefixes are SHORTER than the minimum for every
        # role and level in this build, at every cell, which is why prompt caching was
        # dropped from the plan rather than tuned.
        #
        # No token counts typed here. `chart_model` is a rendering surface and the lint
        # is right about it — a measurement in a caption is exactly the shape that goes
        # stale in silence, which is what happened to the sentence being replaced.
        return (
            "PROMPT CACHING did not fire in any cell here, and that is measured rather "
            "than assumed. Caching on this vendor is automatic — there is no marker to "
            "set — but it applies only above a minimum cacheable prefix length, and "
            "every prefix in this project is shorter than that minimum at every role "
            "and level. So the schema-and-rules block is re-sent at full input price on "
            "every call. Nothing here is a nil hit rate: there was no cache to hit, and "
            "a zero would read as a measurement of one."
        )
    rate = hit_rate({"cache_read_input_tokens": read,
                     "cache_creation_input_tokens": written})
    # `rate` cannot be None here, and this is the only place that is true.
    #
    # A type checker flags `rate * PERCENT` because `hit_rate` returns
    # `float | None`. The invariant that rules it out is established by the loop
    # above rather than by anything local: `applied` is appended to only when a
    # cell reported read or written tokens, so reaching this line at all means
    # `read + written > 0`, which is exactly the condition under which `hit_rate`
    # returns a float.
    #
    # Left as a narrowing note instead of a guard. A branch for a state this
    # function cannot produce would be dead code that asserts a false
    # possibility, and `or 0.0` would be worse still — it would turn "no cache to
    # hit" into a measured zero, which is the one thing the whole caching caption
    # exists to avoid.
    return (
        f"PROMPT CACHING applied to {len(applied)} of {len(cells)} cell(s): "
        f"{rate * PERCENT:.0f}% of prefix tokens served from cache "
        f"({read} read, {written} written), saving est. ${saved:.4f} against paying full "
        f"input price. Estimated, like every dollar here — the same hand-entered table. "
        f"It applies only where the prefix clears the model's minimum, which is the "
        f"frontier role at L3 and nothing else."
    )


def deadline_note(cells) -> str | None:
    """The warning naming every cell the clock cut short, or None if none were.

    Returned as a chart-level WARNING rather than folded into the caption because the
    caption describes what the figure measures and this describes what it could not.
    A reader who stops after the first paragraph must still have met it.
    """
    stopped = [cell for cell in cells if cell.get("stopped_early")]
    if not stopped:
        return None
    parts = ", ".join(
        f"{label_for(cell)} ({cell['n_items']} of {cell.get('n_requested', cell['n_items'])})"
        for cell in ordered_cells(stopped)
    )
    return (
        f"STOPPED AT A DEADLINE: {len(stopped)} of {len(cells)} cell(s) ran fewer items "
        f"than they were asked for — {parts}. Every bar is computed over the items that "
        f"ACTUALLY RAN and each row carries its own n, because the rows no longer share "
        f"a denominator. Nothing was estimated for the items that never started, and no "
        f"bar was scaled to make the cells look comparable."
    )


def bar_rows(cells, *, metric: str) -> list[dict]:
    """Cells as drawable rows, for either backend.

    `metric` is "rate" or "cost". Both backends get the same rows for the same payload,
    which is what stops the two figures from disagreeing about ordering, colour, the
    reference convention, or what a cell with nothing landed should say.

    **When any cell was deadline-stopped, EVERY row carries its n.** On a complete
    sweep the cells share a denominator and it belongs in the caption once; the moment
    one cell is short, the bars are no longer commensurable and a reader comparing two
    of them needs each one's n where their eye already is. Applied to every row rather
    than only the short ones, because "the row without the annotation is the full one"
    is a convention the reader has to be taught, and the point of putting it on the row
    was to stop asking them to hold something in their head.
    """
    cells = list(cells)
    any_stopped = any(cell.get("stopped_early") for cell in cells)
    rows = []
    for cell in ordered_cells(cells):
        # STRICTLY still running. The pale bar means provisional — the chart's own unit
        # line says "hollow while a cell is still running" — and a deadline-stopped cell
        # is not provisional, it is final at a smaller n. Reading `not complete` drew it
        # pale and told the room to wait for a bar that would never fill.
        pending = not cell["complete"] and not cell.get("stopped_early")
        if metric == "rate":
            value = cell["rate_value"]
            lo, hi = cell["rate_ci_low"], cell["rate_ci_high"]
            # Already carries its own n and its own "stopped at the deadline" —
            # `summarise_cell` builds it, so the figure and the cell file cannot
            # disagree about what happened.
            note = note_for(cell, cell["silent_error_rate"])
        elif metric == "cost":
            value = cell["cost_usd"]["value"] or None
            lo = hi = None
            note = note_for(cell, money(value))
            if any_stopped:
                ran, asked = cell["n_items"], cell.get("n_requested", cell["n_items"])
                note = f"{note} · n={ran}" + (f" of {asked}" if ran != asked else "")
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
            "stopped_early": bool(cell.get("stopped_early")),
            "note": note,
        })
    return rows


# ---------------------------------------------------------------------------
# OUTCOME SHIFT — the session's headline visual.
#
# It was specified as A vs C, and A vs C turned out to be a null: measured
# 2026-09-07 on the 60 held-out items, condition A terminated `success` 60/60, so
# retry had nothing to retry and B fired zero retries. C's verifiers rejected 2 of
# 60. Three runs of A alone scored 46, 51 and 52 — the six-item "uplift" is inside
# the arm's own run-to-run spread, and McNemar's p=0.031 is correct arithmetic over
# a mechanism that never fired.
#
# **That is a finding rather than a disappointment, and it is the trap seen from the
# other side.** Verification exists to catch rule violations. Supply the rules and
# there are barely any violations left to catch. The loops have almost nothing to do
# at L3, which is exactly what a 73-point trap gap predicts.
#
# So the chart is built on the arms where the bands actually separate: the same
# model-agnostic task, the same 60 items, the same withheld-rules prompt, and two
# models with opposite failure modes.
# ---------------------------------------------------------------------------

# Order matters and it is not alphabetical. Reading left to right the bands go from
# "fine" through "wrong and you would not know" to "declined" — so the eye crosses
# the silent band on the way, which is the band the session is about.
SHIFT_BAND_ORDER = (
    "correct",
    "unearned",
    "wrong_and_silent",
    "wrong_and_caught",
    "abstained",
)

SHIFT_BAND_LABELS = {
    "correct": "correct",
    "unearned": "right, could not have known",
    "wrong_and_silent": "WRONG AND SILENT",
    "wrong_and_caught": "wrong and visible",
    "abstained": "declined — named what was missing",
}

OUTCOME_SHIFT_CAPTION = (
    "Every band counted by enumeration, never derived by subtracting the others. "
    "The two arms answer the SAME items with the SAME prompt; only the model "
    "differs. Read the WRONG AND SILENT band: it is the one a reader of the answer "
    "cannot detect without already knowing the answer, and it is the only band this "
    "project treats as dangerous. `declined` is not a failure — the model named the "
    "input it was not given rather than inventing one — and it was scored as a crash "
    "until 2026-09-07. See docs/instrument-ranked-honesty-backwards.md."
)

# Shown on the figure rather than in a runbook, because a row that looks like a
# broken comparison invites the wrong question from the floor.
RULE_FREE_NOTE = (
    "A rule-free pattern scores the same at both prompt levels by construction — it "
    "requires no rules, so withholding them changes nothing. That is the L0 floor "
    "doing its job: without it the withheld arm would sit at zero by construction "
    "and the comparison would be rigged rather than measured."
)


def outcome_shift_rows(arms: list[dict]) -> list[dict]:
    """One row per arm, with every band as a count. Reads `bands` and nothing else.

    Takes the arm summaries `sweep.conditions.summarise_arm` produces, so the chart
    cannot disagree with the results file about what happened — it is the same dict.
    """
    rows = []
    for arm in arms:
        bands = arm.get("bands") or {}
        rows.append({
            "label": arm.get("arm") or arm.get("condition", "?"),
            "n": arm.get("n_items", sum(bands.values())),
            "counts": [bands.get(band, 0) for band in SHIFT_BAND_ORDER],
        })
    return rows


# ---------------------------------------------------------------------------
# THESIS — the trap matrix. Four cells, read on the diagonal.
# ---------------------------------------------------------------------------

TRAP_CAPTION = (
    "Read the DIAGONAL. The cheap model WITH the rules beats the frontier model "
    "WITHOUT them, on the same items, at a fraction of the cost. Columns are the "
    "trap; rows are the model upgrade. Every bar is one live run over the held-out "
    "set."
)

# Most people in a room have seen exactly one kind of error bar, so the figure says
# which is which rather than assuming the distinction is read off the styling.
TRAP_TWO_ERRORS_NOTE = (
    "TWO different uncertainties, drawn differently. The thin capped line is the "
    "Wilson interval — sampling error, what this n can resolve. The open bracket is "
    "the observed RUN-TO-RUN spread across repeat runs of the same arm on the same "
    "items. One is invisible to the other: a Wilson interval on a single run says "
    "nothing about whether a second run would land elsewhere, and the cheap L3 arm "
    "moved by six items across five runs. A cell with NO bracket was run once — that "
    "is different from a flat bracket, which would claim we ran it repeatedly and "
    "measured no variance."
)

TRAP_NO_STAR_NOTE = (
    "No significance marks on the ROW comparison: rows are cross-model, both models "
    "carry run-to-run variance, and `loopeng.sweep.diff` refuses a p-value across "
    "that in code. The paired test belongs to the COLUMNS and is on the DELTA chart."
)


def trap_matrix_rows(cells: list[dict]) -> list[dict]:
    """Order the four cells so the grid reads model-major, level-minor.

    `cells` are dicts of model, level, correct, n and an optional (lo, hi) spread.
    Sorted explicitly: file order is not a contract, and a reordered input must not
    silently produce a different picture of the same data.
    """
    return sorted(cells, key=lambda c: (c["model"], c["level"]))


# ---------------------------------------------------------------------------
# COST PER CORRECT ANSWER
# ---------------------------------------------------------------------------

COST_PER_CORRECT_CAPTION = (
    "Cost per CORRECT answer, not per call. Failed calls are included — they billed. "
    "Every figure is estimated: tokens are measured, dollars are those tokens times a "
    "hand-entered price table, and the est. prefix never comes off. An arm that "
    "answered nothing correctly has an undefined cost per correct answer, not an "
    "infinite one, and renders as text rather than as a bar."
)

COST_PER_CORRECT_NOTE = (
    "The two WITHHELD bars are what make this an argument rather than a price list. "
    "Buying a better model without supplying the rules is the most expensive way to "
    "be wrong on this chart."
)


# Carried on the DELTA chart so the removed comparisons are accounted for on the
# figure rather than only in a commit message. A reader who expects to see the loop
# uplift and does not find it should learn why from the chart.
DELTA_LOOPS_NOTE = (
    "The loop comparisons are NOT drawn here, and their absence is a finding rather "
    "than an omission. With the rules supplied, the agent's SQL executed on every "
    "held-out item — so retry had nothing to retry, verification rejected almost "
    "nothing, and repeat runs of the same arm moved further than the arms moved from "
    "each other. Verification exists to catch rule violations; supply the rules and "
    "there are barely any violations left to catch. That is this chart's own finding "
    "seen from the other side, and a p-value over a mechanism that never fired would "
    "have given a dead comparison the visual weight of a live one."
)


# Shown on the DELTA chart when the two arms answered materially different numbers of
# items — which is what an abstaining arm looks like from a paired test.
#
# The silent-error rate is computed over answers that RAN AND RETURNED, which is the
# right denominator for that metric and the wrong one to leave unexplained. An arm
# that declined a third of the set is then scored only on the items it chose to
# answer, and a reader comparing two bars will not guess that one of them stood on
# fewer items unless the row says so.
COVERAGE_ASYMMETRY_NOTE = (
    "One arm answered materially fewer items than the other, so this pair is scored "
    "on the subset BOTH answered. That is the correct denominator for a silent-error "
    "rate — an unanswered question has no answer to be silently wrong about — and it "
    "flatters an arm that declines, because declining removes an item from its own "
    "denominator rather than counting against it. The pair count on each row is the "
    "honest n. Coverage against precision is the ABSTENTION chart."
)


