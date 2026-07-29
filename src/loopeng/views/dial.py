"""DIAL: the sweep's cells, live ones and reference ones, visibly different.

**At delivery the live cells are Haiku and the frontier cells are reference.** That
means the named secondary — Haiku-plus-loop against Sonnet one-shot — compares a line
measured minutes ago against one measured weeks ago. That distinction is rendered ON
THE CHART, in the row itself, not in a caption someone reads afterwards. A caption is
read once; a badge is read every time the row is.

The comparison table carries the same treatment, because the L3 comparison has exactly
the same problem and is the one most likely to be quoted.
"""

from pathlib import Path

import gradio as gr

from loopeng.sweep.charts import COST_CAPTION, DIAL_CAPTION
from loopeng.sweep.orchestrator import load_all
from loopeng.sweep.reference import MEASURED_ON, load_reference
from loopeng.sweep.runner import SWEEP_DIR
from loopeng.views.chrome import NOT_MEASURED, live_or_reference_badge, stamp

ROW_HEADER = "| | cell | silent-error rate | cost |\n|---|---|---|---|\n"


def _rows(cells: list[dict]) -> str:
    if not cells:
        return "_No cells yet. Start the sweep and this fills in._"
    body = []
    for cell in sorted(cells, key=lambda c: (c.get("reference", False), c["role"],
                                             c["level"], c["mode"], c["replicate"])):
        badge = live_or_reference_badge(cell.get("reference", False),
                                        cell.get("measured_on", MEASURED_ON))
        rate = cell["silent_error_rate"]
        if not cell["complete"] and cell["rate_value"] is None:
            rate = NOT_MEASURED
        cost = cell["cost_usd"]["value"]
        money = f"est. ${cost:.4f}" if cost else "—"
        body.append(f"| {badge} | {cell['label']} | {rate} | {money} |")
    return ROW_HEADER + "\n".join(body)


def _comparison(cells: list[dict]) -> str:
    """The named secondary, with the live/reference status of BOTH sides on the row."""
    by_key = {c["key"]: c for c in cells}
    lines = [
        "### Haiku + loop vs Sonnet one-shot",
        "",
        "| level | Haiku + loop | Sonnet one-shot | reading |",
        "|---|---|---|---|",
    ]
    for level, reading in (
        ("L0", "Haiku + loop is better (McNemar exact p=0.039)"),
        ("L3", "**cannot tell apart at this n** (p=0.250) — not equal; Sonnet is still ahead"),
    ):
        haiku = by_key.get(f"worker_{level}_loop_r0")
        sonnet = by_key.get(f"frontier_{level}_one_shot_r0")
        if not haiku or not sonnet:
            # The reading is a recorded conclusion, not something derived from the
            # cells on screen, so it shows even before they land. Otherwise the row
            # that says "cannot tell apart" is missing exactly when someone is
            # waiting for the chart and most likely to fill the gap themselves.
            lines.append(f"| {level} | {NOT_MEASURED} | {NOT_MEASURED} | {reading} |")
            continue
        h_badge = live_or_reference_badge(
            haiku.get("reference", False), haiku.get("measured_on", MEASURED_ON)
        )
        s_badge = live_or_reference_badge(
            sonnet.get("reference", False), sonnet.get("measured_on", MEASURED_ON)
        )
        h = f"{h_badge} {haiku['silent_error_rate']}"
        s = f"{s_badge} {sonnet['silent_error_rate']}"
        lines.append(f"| {level} | {h} | {s} | {reading} |")
    lines.append("")
    lines.append(
        "**Read the badges before reading the numbers.** Where one side is LIVE and the "
        "other REFERENCE, this compares a measurement taken minutes ago against one "
        "taken weeks ago, on a model that cannot be pinned to a fixed temperature. That "
        "is a real comparison and a weaker one than it looks."
    )
    return "\n".join(lines)


def build_dial_app(sweep_dir: Path = SWEEP_DIR, *, with_reference: bool = True) -> gr.Blocks:
    def _refresh(_state):
        cells = load_all(sweep_dir)
        if with_reference:
            cells = cells + load_reference(exclude_keys={c["key"] for c in cells})
        done = [c for c in cells if c["complete"]]
        landed = sum(c["rate_n"] for c in done)
        return (
            _rows(cells),
            _comparison(cells),
            stamp(landed if landed else None),
            f"{len(done)} of {len(cells)} cells complete",
            cells,
        )

    with gr.Blocks(title="DIAL") as app:
        gr.Markdown("# DIAL — silent-error rate by cell")
        state = gr.State([])
        status = gr.Markdown("")
        stamped = gr.Markdown("")
        refresh = gr.Button("Refresh", variant="primary")
        rows = gr.Markdown("")
        comparison = gr.Markdown("")
        gr.Markdown(f"<span class='stamp'>{DIAL_CAPTION}</span>")
        gr.Markdown(f"<span class='stamp'>{COST_CAPTION}</span>")

        outputs = [rows, comparison, stamped, status, state]
        refresh.click(_refresh, [state], outputs)
        app.load(_refresh, [state], outputs)

    return app
