"""The two charts: DIAL and COST. Self-contained SVG, no plotting dependency.

**Two charts, not three.** The TIER chart moved to Phase 4, where abstention exists and
"coverage" is a choice a model makes rather than a synonym for "did not crash". Shipping
it here would plot a finding that measurably did not reproduce.

Every value comes from a cell file on disk. A cell still running renders its
in-progress label and a hollow bar — never blank, never zero, never a guess, because a
zero on a chart reads as a measurement.

The DIAL caption carries the comparability warning permanently: Haiku is pinned to
temperature=0 and Sonnet cannot be, so the two models' error bars do not mean the same
thing and cannot be compared by eye.
"""

from pathlib import Path

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

REFERENCE_CAPTION = (
    "Cells marked REFERENCE were NOT computed in this session. They are measurements "
    "taken on the date shown and are displayed for context only. Recomputing them here "
    "would cost roughly ten times the delivery budget, so they are cited rather than "
    "re-run — and they are drawn differently so that is impossible to miss. Presenting "
    "a stored number as though it had just been computed would break the cost "
    "constraint quietly, which is worse than not showing it at all."
)

DIAL_CAPTION = (
    "Silent-error rate, over answers that ran and returned. Error bars are Wilson 95%. "
    "THE BARS ARE NOT COMPARABLE ACROSS MODELS: Haiku is pinned to temperature=0, "
    "Sonnet 5 rejects non-default sampling parameters and cannot be pinned, so Haiku's "
    "bars carry sampling noise only while Sonnet's carry sampling noise plus "
    "run-to-run variance. Within a model they are comparable. Items are 10 clusters of "
    "5 parameterisations, not 50 independent trials, so every interval is narrower "
    "than the evidence supports."
)

COST_CAPTION = (
    "Estimated cost per cell. Tokens are measured; dollars are those tokens times a "
    "hand-entered price table, so every figure here is an estimate and keeps the est. "
    "prefix. Failed, timed-out and budget-exhausted calls are included, because they "
    "billed."
)


def _esc(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


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
        colour = "#94a3b8" if bar["pending"] else (
            "#0ea5e9" if bar["role"] == "worker" else "#f97316"
        )
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

    words, line, lines = caption.split(), "", []
    for word in words:
        if len(line) + len(word) > WRAP_COLUMNS:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    lines.append(line)
    for offset, text in enumerate(lines):
        baseline = y + CAPTION_TOP + offset * CAPTION_LEADING
        parts.append(
            f'<text x="24" y="{baseline}" fill="#475569" font-size="11.5">'
            f'{_esc(text)}</text>'
        )
    parts.append(f'<text x="24" y="{height - FOOTER_GAP}" fill="#94a3b8" font-size="11">'
                 f'{_esc(unit)}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def _label(cell: dict) -> str:
    if cell.get("reference"):
        return f"REFERENCE · {cell['label']}"
    return cell["label"]


def _note(cell: dict, text: str) -> str:
    if cell.get("reference"):
        return f"{text}  [REFERENCE, measured {cell.get('measured_on', 'date unknown')}]"
    return text


def dial_chart(cells: list[dict]) -> str:
    bars = []
    for cell in sorted(cells, key=lambda c: (c.get("reference", False), c["role"],
                                             c["level"], c["mode"], c["replicate"])):
        pending = not cell["complete"]
        bars.append({
            "label": _label(cell),
            "role": cell["role"],
            "value": cell["rate_value"],
            "lo": cell["rate_ci_low"],
            "hi": cell["rate_ci_high"],
            "pending": pending,
            "reference": cell.get("reference", False),
            "note": _note(cell, cell["silent_error_rate"]),
        })
    return _svg("DIAL — silent-error rate by cell", DIAL_CAPTION, bars,
                "Lower is better. Bars are hollow while a cell is still running.")


def cost_chart(cells: list[dict]) -> str:
    bars = []
    for cell in sorted(cells, key=lambda c: (c.get("reference", False), c["role"],
                                             c["level"], c["mode"], c["replicate"])):
        value = cell["cost_usd"]["value"]
        bars.append({
            "label": _label(cell),
            "role": cell["role"],
            "value": value if value else None,
            "lo": None, "hi": None,
            "pending": not cell["complete"],
            "reference": cell.get("reference", False),
            "note": _note(cell, f"est. ${value:.4f}" if value else "not yet measured"),
        })
    return _svg("COST — estimated spend by cell", COST_CAPTION, bars,
                "Estimated, not billed. Includes calls that failed.")


def write_charts(cells: list[dict], directory: Path) -> list[Path]:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    written = []
    for name, svg in (("dial.svg", dial_chart(cells)), ("cost.svg", cost_chart(cells))):
        path = directory / name
        path.write_text(svg, encoding="utf-8")
        written.append(path)
    return written
