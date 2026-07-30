"""The live charts: DIAL, COST, DELTA and ABSTENTION. Drawn with matplotlib, to PNG.

**The TIER chart is still not here.** It moved to Phase 4, where abstention exists and
"coverage" is a choice a model makes rather than a synonym for "did not crash". Shipping
it here would plot a finding that measurably did not reproduce.

**DELTA and ABSTENTION are not new figures so much as gaps closed.** DELTA is the only
chart here that shows a *difference*: DIAL and COST are per-cell absolute values, so the
sweep could show two bars and could not say whether they differed. ABSTENTION existed
only in `tools/render_readme_charts.py`, which reads frozen reference data — so a cloner
could never reproduce `assets/abstention.png` from their own run even though
`triage.abstain.curve` computes it.

Every value comes from a cell file on disk. A cell still running renders its
in-progress label and a hollow bar — never blank, never zero, never a guess, because a
zero on a chart reads as a measurement. On DELTA that rule bites hardest: zero is a real
delta, so a pair with too few discordant items renders the words rather than a bar.

The DIAL caption carries the comparability warning permanently: Haiku is pinned to
temperature=0 and Sonnet cannot be, so the two models' error bars do not mean the same
thing and cannot be compared by eye. DELTA enforces the same warning in code — a
cross-model pair renders no p-value at all.

WHY THIS IS MATPLOTLIB AND NOT HAND-BUILT SVG
---------------------------------------------

It was four hundred lines of f-string SVG geometry — `<rect x="{PAD_LEFT}" y="{y}"…>` —
carrying its own text escaping, its own caption wrapper, its own axis arithmetic and
thirty named pixel offsets. Two justifications were on file for that and neither
survives contact:

*"There is no plotting dependency to install at a venue."* There is:
`tools/render_readme_charts.py` has always rendered `assets/*.png` with matplotlib, and
`uv sync` installs it. The dependency was already on every machine that could run the
tests.

*"…for the live Gradio views, where the figure is redrawn while a sweep lands."* No view
consumes these. `views/dial.py` renders a markdown table; grep for a reader of
`results/charts/` and there is none. They are files an operator opens. The claim
justified a hand-written renderer by a consumer that does not exist — declared, not
enforced, which is this repository's own subject.

What is genuinely different from the README renderer stays different: these are drawn
from whatever is on disk *now*, degrade to "in progress, n=NN so far", and are not
required to be byte-identical between runs. `assets/*.png` are frozen measurements that
must be. So they remain two backends over one model.

WHAT IS NOT FORKED
------------------

`loopeng.sweep.chart_model`: the caption prose, the cell ordering, the role colours, the
reference convention and the cell-to-row transform. Only geometry and drawing calls are
per-backend, and a test asserts neither renderer redefines the prose.
"""

from pathlib import Path

import matplotlib

# Agg before pyplot: no display, no backend probing, no window manager. Same first line
# as tools/render_readme_charts.py, for the same reason — a chart renderer that opens a
# window at a venue is a chart renderer that hangs.
matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402

from loopeng.paired import PairedComparison  # noqa: E402
from loopeng.sweep.chart_model import (  # noqa: E402
    ABSTENTION_CAPTION,
    ABSTENTION_LIVE_NOTE,
    COST_CAPTION,
    DELTA_CAPTION,
    DIAL_CAPTION,
    NOT_MEASURED,
    REFERENCE_CAPTION,
    bar_rows,
    cache_note,
    role_colour,
)
from loopeng.sweep.diff import (  # noqa: E402
    CROSS_MODEL_REFUSAL,
    MIN_DISCORDANT,
    NO_PER_ITEM_DETAIL,
    partition,
)

render_p = PairedComparison.render_p

# ---------------------------------------------------------------------------
# Geometry. Every number below is a figure coordinate, a font size or a line width, and
# carries `# layout`, which is what exempts it from tools/lint_no_numbers.py.
#
# Named rather than typed inline for the same reason the lint rule exists: an
# unexplained `0.62` scattered through six drawing calls is a number nobody can check.
# Named once, a reader can see that BAR_HEIGHT is bar thickness and not a measurement.
# ---------------------------------------------------------------------------
FIG_W_IN = 14.0             # layout: canvas width in inches
DPI = 110                   # layout: pixels per inch
ROW_H_IN = 0.42             # layout: vertical space per bar
HEADER_H_IN = 0.80          # layout: title band
TICK_BAND_IN = 0.34         # layout: axes bottom to the first caption line. Without it
                            #         the tick labels print over the disclosure, which
                            #         is a disclosure that did not ship.
LINE_H_IN = 0.165           # layout: one wrapped caption or warning line
BLOCK_PAD_IN = 0.30         # layout: padding under the caption block
MIN_BODY_H_IN = 1.20        # layout: floor, so a one-row figure is not a sliver

TITLE_X = 0.018             # layout: left margin as a figure fraction
TITLE_Y = 0.976             # layout: title baseline
TITLE_SIZE = 15             # layout: title point size
CAPTION_SIZE = 7.6          # layout: caption point size
CAPTION_COLUMNS = 190       # layout: caption wrap width in characters
CAPTION_LEADING = 1.5       # layout: caption line spacing
LABEL_SIZE = 9.5            # layout: row label point size
VALUE_SIZE = 9.0            # layout: printed value point size
NOTE_SIZE = 8.2             # layout: warning line point size

BAR_HEIGHT = 0.62           # layout: bar thickness in row units
HATCH = "///"               # layout: the stored-measurement fill
HATCH_WIDTH = 1.8           # layout: hatched outline width
PENDING_ALPHA = 0.45        # layout: opacity while a cell is still running
VALUE_COLUMN = 1.02         # layout: printed value, in axes-x fractions past the plot
NOTE_COLUMN = 0.01          # layout: unmeasured-row note, just inside the plot
ROW_PAD = 0.5               # layout: half a row above the first bar and below the last
BAR_LEFT = 0.202            # layout: DIAL/COST label gutter
BAR_RIGHT = 0.585           # layout: DIAL/COST value gutter — the printed value carries
                            #         the cell's rate AND its reference stamp
BAR_HEADROOM = 1.02         # layout: room past the longest bar
GRID_WIDTH = 0.6            # layout: gridline width
GRID_ALPHA = 0.7            # layout: gridlines sit behind the bars
MIDPOINT = 0.5              # layout: the centre of an axes, for an empty figure
HALF = 2                    # layout: splits a padding band above and below
ERROR_WIDTH = 1.6           # layout: interval line width
CAP_SIZE = 3.5              # layout: interval end-cap half-width

INK = "#0b1220"             # layout: primary text
BODY = "#1e293b"            # layout: row labels
MUTED = "#64748b"           # layout: captions and axes
HAIRLINE = "#cbd5e1"        # layout: gridlines and empty-row outlines
WARNING = "#92400e"         # layout: the lines that must not be missed
WORSE = "#b91c1c"           # layout: a positive delta — more silent errors
BETTER = "#15803d"          # layout: a negative delta — fewer

# matplotlib's bundled font, named explicitly so a font installed on one machine and
# not another cannot change the rendering.
plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["savefig.facecolor"] = "#fbfbfd"


def _wrap(text: str, columns: int = CAPTION_COLUMNS) -> str:
    """Caption text as wrapped lines. Shared by all four figures rather than
    reimplemented per figure — a caption that wraps differently in one chart is a
    caption that gets shortened in one chart."""
    words, line, lines = text.split(), "", []
    for word in words:
        if len(line) + len(word) + 1 > columns:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    lines.append(line)
    return "\n".join(lines)


def _lines(text: str) -> int:
    return text.count("\n") + 1


def _frame(title: str, caption: str, *, body_h_in: float, notes=(),
           left: float = BAR_LEFT, right: float = BAR_RIGHT):
    """A figure sized to its content, with the title, the warnings and the caption.

    Height follows the content rather than being fixed. A figure with a scrollbar's
    worth of empty space below four bars reads as a chart that failed to draw; one with
    twelve bars crushed into a fixed box loses its labels; and a caption block sized by
    guesswork clips the last line of the disclosure, which is the failure this project
    is least entitled to. So the caption block is measured in LINES — the wrap is
    already done here — and the plot is squeezed to fit it.
    """
    notes = [_wrap(note) for note in notes]
    caption = _wrap(caption)
    block_h = (sum(_lines(n) for n in notes) + _lines(caption)) * LINE_H_IN + BLOCK_PAD_IN
    body_h = max(MIN_BODY_H_IN, body_h_in)
    height = HEADER_H_IN + body_h + TICK_BAND_IN + block_h

    fig, ax = plt.subplots(figsize=(FIG_W_IN, height), dpi=DPI)
    fig.subplots_adjust(
        left=left, right=right,
        top=1 - HEADER_H_IN / height, bottom=(TICK_BAND_IN + block_h) / height,
    )
    fig.text(TITLE_X, TITLE_Y, title, fontsize=TITLE_SIZE, fontweight="bold",
             color=INK, va="top")

    # Warnings sit ABOVE the caption and in their own colour. They are the lines that
    # say what could not be compared and why, and a reader who stops at the first
    # paragraph must still have met them.
    cursor = (block_h - BLOCK_PAD_IN / HALF) / height
    for note in notes:
        fig.text(TITLE_X, cursor, note, fontsize=NOTE_SIZE, color=WARNING, va="top",
                 linespacing=CAPTION_LEADING)
        cursor -= _lines(note) * LINE_H_IN / height
    fig.text(TITLE_X, cursor, caption, fontsize=CAPTION_SIZE, color=MUTED,
             va="top", linespacing=CAPTION_LEADING)

    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color(HAIRLINE)
    ax.tick_params(colors=MUTED, labelsize=VALUE_SIZE)
    ax.set_axisbelow(True)
    return fig, ax


def _bar_figure(title: str, caption: str, rows: list[dict], unit: str):
    """DIAL and COST. One row per cell, in the order `chart_model` decides."""
    if any(row.get("reference") for row in rows):
        caption = f"{caption} {REFERENCE_CAPTION}"
    fig, ax = _frame(title, f"{unit} {caption}",
                     body_h_in=max(1, len(rows)) * ROW_H_IN)

    positions = list(range(len(rows)))
    ax.set_yticks(positions)
    ax.set_yticklabels([row["label"] for row in rows], fontsize=LABEL_SIZE, color=BODY)
    # Set explicitly rather than left to the bars: a figure whose every row is
    # unmeasured has no bar to set a limit from, and its text would land outside the
    # axes — invisible, which is the one thing an unmeasured row must not be. `max(…, 1)`
    # because a chart with no cells at all still has to be a rectangle.
    ax.set_ylim(max(len(rows), 1) - ROW_PAD, -ROW_PAD)

    # No x axis. The bar is a comparison and the number beside it is the measurement;
    # an axis labelled 0.0-0.9 beside a row reading "68.3%" invites the reader to
    # convert, and an unlabelled one is decoration. The SVG backend had none either.
    biggest = max((r["value"] for r in rows if r["value"] is not None), default=0) or 1
    ax.set_xlim(0, biggest * BAR_HEADROOM)
    ax.set_xticks([])
    ax.spines["bottom"].set_visible(False)

    for position, row in zip(positions, rows, strict=True):
        colour = role_colour(row["role"], pending=row["pending"])
        if row["value"] is None:
            # Never blank, never zero. A dashed outline across the full width, with the
            # words inside it: an empty row and a measured zero must not look alike.
            ax.barh(position, biggest * BAR_HEADROOM, color="none", edgecolor=HAIRLINE,
                    linestyle="--", height=BAR_HEIGHT)
            ax.text(NOTE_COLUMN, position, row["note"],
                    transform=ax.get_yaxis_transform(), va="center", ha="left",
                    fontsize=VALUE_SIZE, color=MUTED, style="italic")
            continue
        if row["reference"]:
            # Hatched outline, never a solid bar: a stored measurement must not look
            # like one this session produced. Same rule the README renderer follows.
            ax.barh(position, row["value"], color="none", edgecolor=colour,
                    linewidth=HATCH_WIDTH, hatch=HATCH, height=BAR_HEIGHT)
        else:
            ax.barh(position, row["value"], color=colour, height=BAR_HEIGHT,
                    alpha=PENDING_ALPHA if row["pending"] else 1.0)
        if row["lo"] is not None:
            ax.errorbar(row["value"], position,
                        xerr=[[row["value"] - row["lo"]], [row["hi"] - row["value"]]],
                        fmt="none", ecolor=INK, elinewidth=ERROR_WIDTH,
                        capsize=CAP_SIZE, capthick=ERROR_WIDTH)
        ax.text(VALUE_COLUMN, position, row["note"],
                transform=ax.get_yaxis_transform(), va="center", ha="left",
                fontsize=VALUE_SIZE, color=INK)

    if not rows:
        ax.set_yticks([])
        ax.text(NOTE_COLUMN, MIDPOINT, NOT_MEASURED, transform=ax.transAxes,
                va="center", ha="left", fontsize=VALUE_SIZE, color=MUTED, style="italic")
    return fig


def dial_chart(cells: list[dict]):
    return _bar_figure(
        "DIAL — silent-error rate by cell", DIAL_CAPTION,
        bar_rows(cells, metric="rate"),
        "Lower is better. Bars are hollow while a cell is still running.",
    )


def cost_chart(cells: list[dict]):
    # The cache note goes on the COST chart because that is where the number it changes
    # lives. Composed at render time from the cells on screen, never stored.
    return _bar_figure(
        "COST — estimated spend by cell", f"{COST_CAPTION} {cache_note(cells)}",
        bar_rows(cells, metric="cost"),
        "Estimated, not billed. Includes calls that failed.",
    )


# ---------------------------------------------------------------------------
# DELTA. Its own frame, because a signed value needs a zero line and the other two
# charts do not have one. The scale is symmetric around zero so the sign of a bar is
# readable without reading its number.
# ---------------------------------------------------------------------------
DELTA_ROW_H_IN = 0.66       # layout: bar plus the provenance sub-line
DELTA_BAR_HEIGHT = 0.34     # layout: bar thickness in row units
DELTA_MIN_SPAN = 1.0        # layout: smallest half-width in points, so an all-zero
                            #         chart still has an axis rather than no scale
DELTA_SPAN_PAD = 1.08       # layout: room past the widest interval
DELTA_LEFT = 0.335          # layout: the label is a pair, so it is twice DIAL's length —
                            #         and both sides read REFERENCE once the frontier
                            #         cells can be paired with each other
DELTA_LABEL_SIZE = 8.5      # layout: smaller than DIAL's, for the same reason
DELTA_RIGHT = 0.612         # layout: the reading gutter carries a sentence AND both
                            #         measurement dates, which is the longest string here
SUB_DY = 0.31               # layout: provenance offset below a row, in row units
SUB_SIZE = 7.5              # layout: provenance point size
ZERO_WIDTH = 1.5            # layout: the zero line
ZERO_LABEL_PAD = 4          # layout: zero label offset above the axes, in points
DELTA_ALPHA = 0.85          # layout: bar opacity
DELTA_NOTE_COLUMNS = 62     # layout: the untestable reading wraps inside its gutter


def _delta_row(comparison) -> dict:
    """One comparison as a drawable row. The note is the reading, never a bare number."""
    testable = comparison.n_pairs and comparison.n_discordant >= MIN_DISCORDANT \
        and not comparison.cross_model
    interval = comparison.interval_pp
    if comparison.cross_model:
        note = "no p-value — cross-model, see the caption"
    elif not comparison.n_pairs:
        # Derived, not asserted. This row used to read "no per-item record on one side"
        # unconditionally, which is the right cause for the Sonnet pairs and the wrong
        # one for two arms that genuinely answered disjoint sets.
        note = comparison.unpairable_because
    elif comparison.n_discordant < MIN_DISCORDANT:
        note = (f"not distinguishable at this n "
                f"({comparison.n_discordant} discordant of {comparison.n_pairs})")
    else:
        note = (f"{comparison.delta_pp:+.1f} pp [{interval[0]:+.1f}, {interval[1]:+.1f}] · "
                f"{comparison.n_discordant}/{comparison.n_pairs} discordant · "
                f"McNemar exact p{render_p(comparison.p_value)}")
    return {
        "label": f"{comparison.label_a} → {comparison.label_b}",
        "provenance": comparison.provenance(),
        "value": comparison.delta_pp,
        "lo": interval[0] if interval else None,
        "hi": interval[1] if interval else None,
        "testable": bool(testable),
        "note": note,
    }


def delta_chart(comparisons):
    """One row per compared pair. Zero is drawn; nothing untestable gets a bar."""
    testable, untestable = partition(comparisons)
    rows = [_delta_row(c) for c in testable + untestable]
    notes = []
    if untestable:
        # Counted and named, never dropped quietly. A chart showing fewer comparisons
        # than the cells imply is the same failure as a bar that renders zero.
        notes.append(f"{len(untestable)} comparison(s) {NO_PER_ITEM_DETAIL}")
    if any(c.cross_model for c in comparisons):
        notes.append(CROSS_MODEL_REFUSAL)
    if not rows:
        rows = [{
            "label": "no comparable cells yet", "provenance": "",
            "value": None, "lo": None, "hi": None, "testable": False,
            "note": f"{NOT_MEASURED} — run a sweep, or render with --reference=compare",
        }]

    fig, ax = _frame("DELTA — paired difference in silent-error rate", DELTA_CAPTION,
                     body_h_in=len(rows) * DELTA_ROW_H_IN, notes=notes,
                     left=DELTA_LEFT, right=DELTA_RIGHT)
    ax.grid(axis="x", color=HAIRLINE, linewidth=GRID_WIDTH, alpha=GRID_ALPHA)

    reach = max(
        [abs(v) for row in rows for v in (row["value"], row["lo"], row["hi"])
         if v is not None] or [DELTA_MIN_SPAN]
    )
    span = max(reach, DELTA_MIN_SPAN) * DELTA_SPAN_PAD
    ax.set_xlim(-span, span)
    ax.set_xlabel("percentage points", fontsize=SUB_SIZE, color=MUTED)

    positions = list(range(len(rows)))
    ax.set_yticks(positions)
    ax.set_yticklabels([row["label"] for row in rows], fontsize=DELTA_LABEL_SIZE,
                       color=BODY)
    ax.set_ylim(len(rows) - ROW_PAD, -ROW_PAD)

    # Zero, drawn. A delta of zero is a measurement; leaving the axis implicit would let
    # a bar of no width read as an absent bar.
    ax.axvline(0, color=INK, linewidth=ZERO_WIDTH)
    ax.annotate("0 pp — no difference", xy=(0, 1), xycoords=("data", "axes fraction"),
                xytext=(0, ZERO_LABEL_PAD), textcoords="offset points",
                ha="center", va="bottom", fontsize=SUB_SIZE, color=INK)

    for position, row in zip(positions, rows, strict=True):
        # Both dates, in the reading gutter under the number rather than under the
        # label. A caption is read once and a row is read every time — and this line is
        # the longest string on the figure, so in the label gutter it ran off the edge.
        ax.text(VALUE_COLUMN, position + SUB_DY, row["provenance"],
                transform=ax.get_yaxis_transform(), va="center", ha="left",
                fontsize=SUB_SIZE, color=MUTED)
        if row["value"] is None or not row["testable"]:
            # The words, not a bar. Zero is a real delta here, so drawing one for
            # "cannot tell" would be a claim.
            ax.text(VALUE_COLUMN, position, _wrap(row["note"], DELTA_NOTE_COLUMNS),
                    transform=ax.get_yaxis_transform(), va="center", ha="left",
                    fontsize=VALUE_SIZE, color=MUTED, style="italic")
            continue
        ax.barh(position, row["value"], height=DELTA_BAR_HEIGHT, alpha=DELTA_ALPHA,
                color=WORSE if row["value"] > 0 else BETTER)
        if row["lo"] is not None:
            ax.errorbar(row["value"], position,
                        xerr=[[row["value"] - row["lo"]], [row["hi"] - row["value"]]],
                        fmt="none", ecolor=INK, elinewidth=ERROR_WIDTH,
                        capsize=CAP_SIZE, capthick=ERROR_WIDTH)
        ax.text(VALUE_COLUMN, position, row["note"],
                transform=ax.get_yaxis_transform(), va="center", ha="left",
                fontsize=VALUE_SIZE, color=INK)
    return fig


# ---------------------------------------------------------------------------
# ABSTENTION. A scatter with a line, not bars, so it needs its own frame.
# ---------------------------------------------------------------------------
ABSTAIN_H_IN = 4.8          # layout: plot height, excluding the caption block
ABSTAIN_LEFT = 0.06         # layout: y-axis gutter — a percentage, not a cell label
ABSTAIN_RIGHT = 0.965       # layout: no value gutter; the labels sit on the points
AXIS_PAD = 4                # layout: room past 0% and 100% so a point label at the
                            #         edge is not clipped in half
ABSTAIN_DOT = 34            # layout: marker area in points squared
ABSTAIN_LINE = 1.8          # layout: the connecting line
ABSTAIN_LINE_ALPHA = 0.7    # layout: the line sits behind the points
ABSTAIN_LABEL_DY = 9        # layout: point label offset in points
ABSTAIN_LABEL_SIZE = 7.5    # layout: point label point size
ABSTAIN_COLOUR = "#0ea5e9"  # layout: the curve
Z_LINE = 1                  # layout: the connecting line, behind everything
Z_INTERVAL = 2              # layout: intervals over the line
Z_POINT = 3                 # layout: the measurements on top
AXIS_PERCENT = 100          # layout: proportion to axis-label percentage. An axis tick
                            #         is furniture; the measurement is the point it
                            #         locates.


def abstention_chart(points: list[dict]):
    """Coverage against precision, from `triage.abstain.curve` over a cell's items.

    A point with no measurable precision is dropped rather than plotted at zero, and the
    count dropped is reported — a threshold that answered nothing has no precision, and
    a dot on the floor would read as "always wrong".
    """
    usable = sorted(
        (p for p in points
         if p.get("coverage_value") is not None and p.get("precision_value") is not None),
        key=lambda p: p["coverage_value"],
    )
    dropped = len(points) - len(usable)
    notes = []
    if dropped:
        notes.append(
            f"{dropped} threshold(s) not plotted: they answered nothing, so precision "
            f"is undefined. A dot on the floor would read as 'always wrong'."
        )

    fig, ax = _frame(
        "ABSTENTION — coverage against precision as the threshold moves",
        "Vertical axis: precision (%) — share of ANSWERED that are right. "
        f"{ABSTENTION_LIVE_NOTE} {ABSTENTION_CAPTION}",
        body_h_in=ABSTAIN_H_IN, notes=notes,
        left=ABSTAIN_LEFT, right=ABSTAIN_RIGHT,
    )
    ax.grid(visible=True, color=HAIRLINE, linewidth=GRID_WIDTH, alpha=GRID_ALPHA)
    ax.set_xlim(-AXIS_PAD, AXIS_PERCENT + AXIS_PAD)
    ax.set_ylim(-AXIS_PAD, AXIS_PERCENT + AXIS_PAD)
    ax.set_xlabel("coverage (%) — share of questions answered at all",
                  fontsize=SUB_SIZE, color=MUTED)

    if not usable:
        ax.text(MIDPOINT, MIDPOINT, NOT_MEASURED, transform=ax.transAxes,
                va="center",
                ha="center", fontsize=LABEL_SIZE, color=MUTED, style="italic")
        return fig

    xs = [p["coverage_value"] * AXIS_PERCENT for p in usable]
    ys = [p["precision_value"] * AXIS_PERCENT for p in usable]
    lo = [(p["precision_value"] - p["precision_ci_low"]) * AXIS_PERCENT
          if p.get("precision_ci_low") is not None else 0 for p in usable]
    hi = [(p["precision_ci_high"] - p["precision_value"]) * AXIS_PERCENT
          if p.get("precision_ci_high") is not None else 0 for p in usable]

    ax.plot(xs, ys, color=ABSTAIN_COLOUR, linewidth=ABSTAIN_LINE,
            alpha=ABSTAIN_LINE_ALPHA, zorder=Z_LINE)
    ax.errorbar(xs, ys, yerr=[lo, hi], fmt="none", ecolor=INK,
                elinewidth=ERROR_WIDTH, alpha=ABSTAIN_LINE_ALPHA, zorder=Z_INTERVAL)
    ax.scatter(xs, ys, s=ABSTAIN_DOT, color=ABSTAIN_COLOUR, zorder=Z_POINT)
    for x, y, point in zip(xs, ys, usable, strict=True):
        ax.annotate(f"t={point['threshold']:.2f} · n={point['n_answered']}",
                    xy=(x, y), xytext=(0, ABSTAIN_LABEL_DY), textcoords="offset points",
                    ha="center", fontsize=ABSTAIN_LABEL_SIZE, color=BODY)
    return fig


def write_charts(cells: list[dict], directory: Path, *,
                 comparisons=(), abstention_points=()) -> list[Path]:
    """Every chart the supplied data supports.

    DELTA and ABSTENTION are written even when their inputs are empty: they render "not
    yet measured" and say what would fill them. A chart that silently does not exist is
    indistinguishable from a chart whose finding is absent.
    """
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    written = []
    figures = (
        ("dial.png", dial_chart(cells)),
        ("cost.png", cost_chart(cells)),
        ("delta.png", delta_chart(list(comparisons))),
        ("abstention.png", abstention_chart(list(abstention_points))),
    )
    for name, figure in figures:
        path = directory / name
        # Software=None strips the matplotlib version stamp, the only nondeterminism
        # matplotlib writes into a PNG by default. These files are not required to be
        # byte-identical — assets/*.png are — but a diff that is only a version string
        # is noise in either place.
        figure.savefig(path, format="png", metadata={"Software": None})
        plt.close(figure)
        written.append(path)
    return written
