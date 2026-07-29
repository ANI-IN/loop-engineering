"""The live charts: DIAL, COST, DELTA and ABSTENTION. Self-contained SVG, no plotting
dependency.

**The TIER chart is still not here.** It moved to Phase 4, where abstention exists and
"coverage" is a choice a model makes rather than a synonym for "did not crash". Shipping
it here would plot a finding that measurably did not reproduce.

**DELTA and ABSTENTION are new, and both closed a gap rather than adding a figure.**
DELTA is the only chart here that shows a *difference*: DIAL and COST are per-cell
absolute values, so the sweep could show two bars and could not say whether they
differed. ABSTENTION existed only in `tools/render_readme_charts.py`, which reads frozen
reference data — so a cloner could never reproduce `assets/abstention.png` from their
own run even though `triage.abstain.curve` computes it.

Every value comes from a cell file on disk. A cell still running renders its
in-progress label and a hollow bar — never blank, never zero, never a guess, because a
zero on a chart reads as a measurement. On DELTA that rule bites hardest: zero is a real
delta, so a pair with too few discordant items renders the words rather than a bar.

The DIAL caption carries the comparability warning permanently: Haiku is pinned to
temperature=0 and Sonnet cannot be, so the two models' error bars do not mean the same
thing and cannot be compared by eye. DELTA enforces the same warning in code — a
cross-model pair renders no p-value at all.
"""

from pathlib import Path

from loopeng.paired import PairedComparison
from loopeng.sweep.chart_model import (
    ABSTENTION_CAPTION,
    ABSTENTION_LIVE_NOTE,
    COST_CAPTION,
    DELTA_CAPTION,
    DIAL_CAPTION,
    NOT_MEASURED,
    REFERENCE_CAPTION,
    bar_rows,
    role_colour,
)
from loopeng.sweep.diff import (
    CROSS_MODEL_REFUSAL,
    MIN_DISCORDANT,
    NO_PER_ITEM_DETAIL,
    partition,
)

render_p = PairedComparison.render_p

# ---------------------------------------------------------------------------
# Geometry. Every number below is an SVG coordinate and carries `# layout`, which
# is what exempts it from tools/lint_no_numbers.py.
#
# They are named rather than typed inline for the same reason the lint rule
# exists: an unexplained `y + 18` scattered through six f-strings is a number
# nobody can check. Named once, a reader can see that TEXT_BASELINE is type
# metrics and not a measurement.
# ---------------------------------------------------------------------------
W = 900                 # layout: canvas width
PAD_LEFT = 300          # layout: label gutter, sized for the longest cell label
PAD_TOP = 70            # layout: below the title
BAR_H = 26              # layout: bar height
GAP = 12                # layout: space between bars
CAPTION_BLOCK = 120     # layout: height reserved for the wrapped caption
RIGHT_GUTTER = 60       # layout: space for the value printed past the bar
LABEL_GAP = 12          # layout: label to bar
TEXT_BASELINE = 18      # layout: baseline offset inside a bar row
NOTE_INDENT = 10        # layout: note inset in an unmeasured bar
MIN_BAR = 2             # layout: a nonzero value must still draw something
WHISKER = 6             # layout: interval end-cap half-height
VALUE_GAP = 8           # layout: bar to its printed value
WRAP_COLUMNS = 118      # layout: caption wrap width
CAPTION_TOP = 24        # layout: caption first baseline
CAPTION_LEADING = 17    # layout: caption line height
FOOTER_GAP = 12         # layout: unit line above the bottom edge

def _esc(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _wrap(caption: str, columns: int = WRAP_COLUMNS) -> list[str]:
    """Caption text as lines. Shared by all four figures rather than reimplemented per
    figure — a caption that wraps differently in one chart is a caption that gets
    shortened in one chart."""
    words, line, lines = caption.split(), "", []
    for word in words:
        if len(line) + len(word) > columns:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    lines.append(line)
    return lines


def _svg(title: str, caption: str, bars: list[dict], unit: str) -> str:
    if any(bar.get("reference") for bar in bars):
        caption = f"{caption} {REFERENCE_CAPTION}"
    height = PAD_TOP + len(bars) * (BAR_H + GAP) + CAPTION_BLOCK
    span = W - PAD_LEFT - RIGHT_GUTTER
    biggest = max((b["value"] for b in bars if b["value"] is not None), default=0) or 1

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {height}" '
        f'font-family="ui-sans-serif,system-ui,sans-serif" font-size="13">',
        f'<rect width="{W}" height="{height}" fill="#fbfbfd"/>',
        f'<text x="24" y="34" font-size="19" font-weight="600">{_esc(title)}</text>',
    ]
    y = PAD_TOP
    for bar in bars:
        reference = bar.get("reference")
        colour = role_colour(bar["role"], pending=bar["pending"])
        parts.append(
            f'<text x="{PAD_LEFT - LABEL_GAP}" y="{y + TEXT_BASELINE}" '
            f'text-anchor="end">{_esc(bar["label"])}</text>'
        )
        if bar["value"] is None:
            parts.append(
                f'<rect x="{PAD_LEFT}" y="{y}" width="{span}" height="{BAR_H}" fill="none" '
                f'stroke="#cbd5e1" stroke-dasharray="4 4"/>'
                f'<text x="{PAD_LEFT + NOTE_INDENT}" y="{y + TEXT_BASELINE}" fill="#64748b">'
                f'{_esc(bar["note"])}</text>'
            )
        else:
            width = max(MIN_BAR, span * bar["value"] / biggest)
            opacity = "0.45" if bar["pending"] else "1"
            if reference:
                # Hatched outline, never a solid bar: a stored measurement must not
                # look like one this session produced.
                parts.append(
                    f'<rect x="{PAD_LEFT}" y="{y}" width="{width:.1f}" height="{BAR_H}" '
                    f'fill="none" stroke="{colour}" stroke-width="2" '
                    f'stroke-dasharray="6 3"/>'
                )
            else:
                parts.append(
                    f'<rect x="{PAD_LEFT}" y="{y}" width="{width:.1f}" height="{BAR_H}" '
                    f'fill="{colour}" opacity="{opacity}"/>'
                )
            if bar.get("lo") is not None:
                x1 = PAD_LEFT + span * bar["lo"] / biggest
                x2 = PAD_LEFT + span * bar["hi"] / biggest
                mid = y + BAR_H / 2  # layout: vertical centre of the bar
                top, bottom = mid - WHISKER, mid + WHISKER
                parts.append(
                    f'<line x1="{x1:.1f}" y1="{mid}" x2="{x2:.1f}" y2="{mid}" '
                    f'stroke="#0f172a" stroke-width="2"/>'
                    f'<line x1="{x1:.1f}" y1="{top}" x2="{x1:.1f}" y2="{bottom}" '
                    f'stroke="#0f172a" stroke-width="2"/>'
                    f'<line x1="{x2:.1f}" y1="{top}" x2="{x2:.1f}" y2="{bottom}" '
                    f'stroke="#0f172a" stroke-width="2"/>'
                )
            parts.append(
                f'<text x="{PAD_LEFT + span + VALUE_GAP}" y="{y + TEXT_BASELINE}" '
                f'fill="#0f172a">{_esc(bar["note"])}</text>'
            )
        y += BAR_H + GAP

    for offset, text in enumerate(_wrap(caption)):
        baseline = y + CAPTION_TOP + offset * CAPTION_LEADING
        parts.append(
            f'<text x="24" y="{baseline}" fill="#475569" font-size="11.5">'
            f'{_esc(text)}</text>'
        )
    parts.append(f'<text x="24" y="{height - FOOTER_GAP}" fill="#94a3b8" font-size="11">'
                 f'{_esc(unit)}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def dial_chart(cells: list[dict]) -> str:
    return _svg("DIAL — silent-error rate by cell", DIAL_CAPTION,
                bar_rows(cells, metric="rate"),
                "Lower is better. Bars are hollow while a cell is still running.")


def cost_chart(cells: list[dict]) -> str:
    return _svg("COST — estimated spend by cell", COST_CAPTION,
                bar_rows(cells, metric="cost"),
                "Estimated, not billed. Includes calls that failed.")


# ---------------------------------------------------------------------------
# DELTA. Its own geometry, because a signed value needs a zero line and the other two
# charts do not have one. The scale is symmetric around zero so the sign of a bar is
# readable without reading its number — half the canvas is spent buying that.
# ---------------------------------------------------------------------------
DELTA_W = 1180          # layout: wider canvas; each row carries a reading, not a value
DELTA_PAD_LEFT = 250    # layout: label gutter, sized for "REFERENCE Haiku · L0 · loop"
DELTA_PAD_RIGHT = 430   # layout: reading gutter
DELTA_ROW_H = 40        # layout: bar plus the provenance sub-line
DELTA_BAR_H = 18        # layout: bar height
DELTA_SUB_DY = 30       # layout: provenance baseline within a row
DELTA_MIN_SPAN = 1.0    # layout: smallest half-width in points, so an all-zero chart
                        #         still has an axis rather than dividing by zero
DELTA_HALVES = 2        # layout: the axis is split either side of zero


def _delta_svg(rows: list[dict], caption: str, notes: list[str]) -> str:
    height = PAD_TOP + len(rows) * DELTA_ROW_H + CAPTION_BLOCK + len(notes) * CAPTION_LEADING
    span = DELTA_W - DELTA_PAD_LEFT - DELTA_PAD_RIGHT
    half_span = span / DELTA_HALVES
    zero_x = DELTA_PAD_LEFT + half_span
    reach = max(
        [abs(v) for row in rows for v in (row["value"], row["lo"], row["hi"]) if v is not None]
        or [DELTA_MIN_SPAN]
    )
    scale = half_span / max(reach, DELTA_MIN_SPAN)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {DELTA_W} {height}" '
        f'font-family="ui-sans-serif,system-ui,sans-serif" font-size="13">',
        f'<rect width="{DELTA_W}" height="{height}" fill="#fbfbfd"/>',
        f'<text x="24" y="34" font-size="19" font-weight="600">'
        f'{_esc("DELTA — paired difference in silent-error rate")}</text>',
    ]
    body_height = len(rows) * DELTA_ROW_H
    # Zero, drawn. A delta of zero is a measurement; leaving the axis implicit would let
    # a bar of no width read as an absent bar.
    parts.append(
        f'<line x1="{zero_x:.1f}" y1="{PAD_TOP - GAP}" x2="{zero_x:.1f}" '
        f'y2="{PAD_TOP + body_height}" stroke="#0f172a" stroke-width="1.5"/>'
        f'<text x="{zero_x:.1f}" y="{PAD_TOP - GAP - VALUE_GAP}" text-anchor="middle" '
        f'fill="#0f172a" font-size="11">0 pp — no difference</text>'
    )

    y = PAD_TOP
    for row in rows:
        parts.append(
            f'<text x="{DELTA_PAD_LEFT - LABEL_GAP}" y="{y + TEXT_BASELINE}" '
            f'text-anchor="end">{_esc(row["label"])}</text>'
        )
        parts.append(
            f'<text x="{DELTA_PAD_LEFT - LABEL_GAP}" y="{y + DELTA_SUB_DY}" '
            f'text-anchor="end" fill="#64748b" font-size="10">'
            f'{_esc(row["provenance"])}</text>'
        )
        if row["value"] is None or not row["testable"]:
            # The words, not a bar. Zero is a real delta here, so drawing one for
            # "cannot tell" would be a claim.
            parts.append(
                f'<text x="{DELTA_PAD_LEFT + NOTE_INDENT}" y="{y + TEXT_BASELINE}" '
                f'fill="#64748b" font-style="italic">{_esc(row["note"])}</text>'
            )
        else:
            width = abs(row["value"]) * scale
            left = zero_x if row["value"] >= 0 else zero_x - width
            colour = "#b91c1c" if row["value"] > 0 else "#15803d"
            parts.append(
                f'<rect x="{left:.1f}" y="{y}" width="{max(MIN_BAR, width):.1f}" '
                f'height="{DELTA_BAR_H}" fill="{colour}" opacity="0.85"/>'
            )
            if row["lo"] is not None:
                x1 = zero_x + row["lo"] * scale
                x2 = zero_x + row["hi"] * scale
                mid = y + DELTA_BAR_H / 2  # layout: vertical centre of the bar
                top, bottom = mid - WHISKER, mid + WHISKER
                parts.append(
                    f'<line x1="{x1:.1f}" y1="{mid}" x2="{x2:.1f}" y2="{mid}" '
                    f'stroke="#0f172a" stroke-width="1.5"/>'
                    f'<line x1="{x1:.1f}" y1="{top}" x2="{x1:.1f}" y2="{bottom}" '
                    f'stroke="#0f172a" stroke-width="1.5"/>'
                    f'<line x1="{x2:.1f}" y1="{top}" x2="{x2:.1f}" y2="{bottom}" '
                    f'stroke="#0f172a" stroke-width="1.5"/>'
                )
            parts.append(
                f'<text x="{DELTA_W - DELTA_PAD_RIGHT + VALUE_GAP}" y="{y + TEXT_BASELINE}" '
                f'fill="#0f172a">{_esc(row["note"])}</text>'
            )
        y += DELTA_ROW_H

    for note in notes:
        parts.append(
            f'<text x="24" y="{y + CAPTION_TOP}" fill="#92400e" font-size="11">'
            f'{_esc(note)}</text>'
        )
        y += CAPTION_LEADING

    for offset, text in enumerate(_wrap(caption)):
        parts.append(
            f'<text x="24" y="{y + CAPTION_TOP + offset * CAPTION_LEADING}" '
            f'fill="#475569" font-size="11.5">{_esc(text)}</text>'
        )
    parts.append("</svg>")
    return "\n".join(parts)


def _delta_row(comparison) -> dict:
    """One comparison as a drawable row. The note is the reading, never a bare number."""
    testable = comparison.n_pairs and comparison.n_discordant >= MIN_DISCORDANT \
        and not comparison.cross_model
    interval = comparison.interval_pp
    if comparison.cross_model:
        note = "no p-value — cross-model, see the caption"
    elif not comparison.n_pairs:
        note = "nothing to pair — no per-item record on one side"
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


def delta_chart(comparisons) -> str:
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
    return _delta_svg(rows, DELTA_CAPTION, notes)


# ---------------------------------------------------------------------------
# ABSTENTION. A scatter with a line, not bars, so it needs its own frame.
# ---------------------------------------------------------------------------
ABSTAIN_W = 900         # layout: canvas width
ABSTAIN_H = 420         # layout: plot height, excluding the caption block
ABSTAIN_PAD_LEFT = 70   # layout: y-axis gutter
ABSTAIN_PAD_RIGHT = 30  # layout: right margin
ABSTAIN_DOT = 5         # layout: marker radius
ABSTAIN_TICKS = 5       # layout: gridlines per axis
ABSTAIN_LABEL_DY = 14   # layout: point label offset
AXIS_PERCENT = 100      # layout: proportion to axis-label percentage. An axis tick is
                        #         furniture; the measurement is the point it locates.


def _axis_position(value: float, *, lo: int, size: int) -> float:
    """A percentage onto a pixel axis. `value` is a proportion, not a percentage."""
    return lo + size * value


def abstention_chart(points: list[dict]) -> str:
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
    plot_w = ABSTAIN_W - ABSTAIN_PAD_LEFT - ABSTAIN_PAD_RIGHT
    plot_h = ABSTAIN_H - PAD_TOP
    notes = []
    if dropped:
        notes.append(
            f"{dropped} threshold(s) not plotted: they answered nothing, so precision "
            f"is undefined. A dot on the floor would read as 'always wrong'."
        )

    caption_lines = _wrap(f"{ABSTENTION_LIVE_NOTE} {ABSTENTION_CAPTION}")
    height = (ABSTAIN_H + CAPTION_BLOCK + len(notes) * CAPTION_LEADING
              + len(caption_lines) * CAPTION_LEADING)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ABSTAIN_W} {height}" '
        f'font-family="ui-sans-serif,system-ui,sans-serif" font-size="13">',
        f'<rect width="{ABSTAIN_W}" height="{height}" fill="#fbfbfd"/>',
        f'<text x="24" y="34" font-size="19" font-weight="600">'
        f'{_esc("ABSTENTION — coverage against precision as the threshold moves")}</text>',
    ]
    for tick in range(ABSTAIN_TICKS + 1):
        fraction = tick / ABSTAIN_TICKS
        x = _axis_position(fraction, lo=ABSTAIN_PAD_LEFT, size=plot_w)
        y = _axis_position(1 - fraction, lo=PAD_TOP, size=plot_h)
        parts.append(
            f'<line x1="{x:.1f}" y1="{PAD_TOP}" x2="{x:.1f}" y2="{ABSTAIN_H}" '
            f'stroke="#e2e8f0"/>'
            f'<line x1="{ABSTAIN_PAD_LEFT}" y1="{y:.1f}" x2="{ABSTAIN_W - ABSTAIN_PAD_RIGHT}" '
            f'y2="{y:.1f}" stroke="#e2e8f0"/>'
            f'<text x="{x:.1f}" y="{ABSTAIN_H + TEXT_BASELINE}" text-anchor="middle" '
            f'fill="#64748b" font-size="11">{fraction * AXIS_PERCENT:.0f}%</text>'
            f'<text x="{ABSTAIN_PAD_LEFT - VALUE_GAP}" y="{y:.1f}" text-anchor="end" '
            f'fill="#64748b" font-size="11">{fraction * AXIS_PERCENT:.0f}%</text>'
        )

    path = []
    for point in usable:
        x = _axis_position(point["coverage_value"], lo=ABSTAIN_PAD_LEFT, size=plot_w)
        y = _axis_position(1 - point["precision_value"], lo=PAD_TOP, size=plot_h)
        path.append(f"{x:.1f},{y:.1f}")
        lo = point.get("precision_ci_low")
        hi = point.get("precision_ci_high")
        if lo is not None and hi is not None:
            y_lo = _axis_position(1 - lo, lo=PAD_TOP, size=plot_h)
            y_hi = _axis_position(1 - hi, lo=PAD_TOP, size=plot_h)
            parts.append(
                f'<line x1="{x:.1f}" y1="{y_hi:.1f}" x2="{x:.1f}" y2="{y_lo:.1f}" '
                f'stroke="#0f172a" stroke-width="1.2" opacity="0.6"/>'
            )
        parts.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{ABSTAIN_DOT}" fill="#0ea5e9"/>'
            f'<text x="{x:.1f}" y="{y - ABSTAIN_LABEL_DY:.1f}" text-anchor="middle" '
            f'fill="#1e293b" font-size="10">'
            f'{_esc(f"t={point["threshold"]:.2f} · n={point["n_answered"]}")}</text>'
        )
    if len(path) > 1:
        parts.insert(
            -1,
            f'<polyline points="{" ".join(path)}" fill="none" stroke="#0ea5e9" '
            f'stroke-width="1.8" opacity="0.7"/>',
        )

    parts.append(
        f'<text x="{ABSTAIN_PAD_LEFT}" y="{ABSTAIN_H + CAPTION_TOP + CAPTION_LEADING}" '
        f'fill="#64748b" font-size="11">'
        f'{_esc("coverage (%) — share of questions answered at all")}</text>'
    )
    y = ABSTAIN_H + CAPTION_TOP + CAPTION_LEADING
    for note in notes:
        y += CAPTION_LEADING
        parts.append(f'<text x="24" y="{y}" fill="#92400e" font-size="11">{_esc(note)}</text>')
    for text in caption_lines:
        y += CAPTION_LEADING
        parts.append(f'<text x="24" y="{y}" fill="#475569" font-size="11.5">{_esc(text)}</text>')
    parts.append(
        f'<text x="24" y="{y + CAPTION_LEADING}" fill="#94a3b8" font-size="11">'
        f'{_esc("Vertical axis: precision (%) — share of ANSWERED that are right.")}</text>'
    )
    parts.append("</svg>")
    return "\n".join(parts)


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
        ("dial.svg", dial_chart(cells)),
        ("cost.svg", cost_chart(cells)),
        ("delta.svg", delta_chart(list(comparisons))),
        ("abstention.svg", abstention_chart(list(abstention_points))),
    )
    for name, svg in figures:
        path = directory / name
        path.write_text(svg, encoding="utf-8")
        written.append(path)
    return written
