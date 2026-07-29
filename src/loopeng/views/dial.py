"""DIAL: the sweep's cells, live ones and reference ones, visibly different.

**At delivery the live cells are Haiku and the frontier cells are reference.** That
means the named secondary — Haiku-plus-loop against Sonnet one-shot — compares a line
measured minutes ago against one measured weeks ago. That distinction is rendered ON
THE CHART, in the row itself, not in a caption someone reads afterwards. A caption is
read once; a badge is read every time the row is.

The comparison table carries the same treatment, because the L3 comparison has exactly
the same problem and is the one most likely to be quoted.

THE READINGS USED TO BE TYPED IN, AND THE LINT RULE LET THEM
-----------------------------------------------------------

This module's comparison table carried two hardcoded conclusions:

    ("L0", "Haiku + loop is better (McNemar exact p=0.039)")
    ("L3", "**cannot tell apart at this n** (p=0.250) — not equal; Sonnet is still ahead")

Two typed p-values, on the screen `tools/lint_no_numbers.py` calls "the single most
quoted screen in the session", in a file that rule has always scanned — and it passed,
because it only inspected numeric literals and a number inside a string is a `str`
constant. See that module's docstring for the whole story.

They are now derived from the cells on disk through `loopeng.sweep.diff`, and the derived
answer is **not** what was typed. This comparison is Haiku against Sonnet, so it is
cross-model, and `pre_registration` already says in words that cross-model comparisons
carry the temperature asymmetry — Haiku is pinned to temperature=0, Sonnet 5 cannot be.
`diff` refuses to report a p-value across that, which means the typed readings were
asserting exactly the significance claim the repo's own guardrail forbids. The guardrail
existed in prose; the screen contradicted it.

When a cell is missing the row still renders, with an explicit *awaiting measurement*
reading. That preserves the concern the original comment recorded — a missing "cannot
tell apart" row invites the room to fill the gap themselves — without keeping a stored
conclusion to fill it with.
"""

from pathlib import Path

import gradio as gr

from loopeng.prompts import LEVELS
from loopeng.sweep.chart_model import COST_CAPTION, DIAL_CAPTION
from loopeng.sweep.diff import named_secondary_deltas
from loopeng.sweep.orchestrator import load_all
from loopeng.sweep.reference import MEASURED_ON, MODE_FILL, load_reference
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


AWAITING = "_awaiting measurement — this row fills in when both cells land_"

CROSS_MODEL_NOTE = (
    "**Read the badges before reading the numbers.** Where one side is LIVE and the "
    "other REFERENCE, this compares a measurement taken minutes ago against one taken "
    "weeks ago, on a model that cannot be pinned to a fixed temperature. That is a real "
    "comparison and a weaker one than it looks — which is why the reading column carries "
    "no p-value: this is the NAMED SECONDARY, it is cross-model, and "
    "`loopeng.sweep.diff` refuses to put a significance claim across that asymmetry. "
    "Every reading below is computed from the cells on this screen; none is stored."
)


def _badged(cell: dict | None) -> str:
    if cell is None:
        return NOT_MEASURED
    badge = live_or_reference_badge(cell.get("reference", False),
                                   cell.get("measured_on", MEASURED_ON))
    return f"{badge} {cell['silent_error_rate']}"


def _comparison(cells: list[dict]) -> str:
    """The named secondary, derived, with the live/reference status of BOTH sides.

    Every reading comes from `loopeng.sweep.diff`. Nothing here is typed — see the module
    docstring for what was, and what the derived answer turned out to be instead.
    """
    by_key = {c["key"]: c for c in cells}
    derived = {c.key_a: c for c in named_secondary_deltas(cells)}
    lines = [
        "### Haiku + loop vs Sonnet one-shot — the pre-registered NAMED SECONDARY",
        "",
        "| level | Haiku + loop | Sonnet one-shot | reading |",
        "|---|---|---|---|",
    ]
    # Levels come from the prompt module, so a new level appears here without anyone
    # remembering to add a row — and cannot appear with a stored conclusion attached.
    for level in LEVELS:
        haiku = by_key.get(f"worker_{level}_loop_r0")
        sonnet = by_key.get(f"frontier_{level}_one_shot_r0")
        comparison = derived.get(f"worker_{level}_loop_r0")
        # The row renders whether or not the cells landed. What it must never do is fill
        # the gap with a conclusion nothing on screen supports.
        reading = comparison.reading() if comparison else AWAITING
        lines.append(f"| {level} | {_badged(haiku)} | {_badged(sonnet)} | {reading} |")
    lines.append("")
    lines.append(CROSS_MODEL_NOTE)
    return "\n".join(lines)


def build_dial_app(sweep_dir: Path = SWEEP_DIR, *,
                   reference_mode: str = MODE_FILL) -> gr.Blocks:
    def _refresh(_state):
        cells = load_all(sweep_dir)
        cells = cells + load_reference(mode=reference_mode,
                                       live_keys={c["key"] for c in cells})
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
