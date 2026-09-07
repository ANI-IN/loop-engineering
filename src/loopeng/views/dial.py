"""DIAL: the sweep's cells as they land, every one of them computed by this run.

This module used to open by explaining that the live cells and the frontier cells were
measured weeks apart, and that the gap was badged on each row so nobody compared a line
from minutes ago against one from a previous month. **There is no such gap any more.**
The stored-reference path is gone: every figure this view can draw comes from a cell
this run wrote, which is what `_refresh` says in code and what the docstring went on
contradicting.

The badge machinery went with it. What survives is the rule that produced it — a
distinction a reader must hold while looking at a row belongs IN the row, because a
caption is read once and a row is read every time.

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
from loopeng.sweep.runner import SWEEP_DIR
from loopeng.views.chrome import NOT_MEASURED, stamp

ROW_HEADER = "| cell | silent-error rate | cost |\n|---|---|---|\n"


def _rows(cells: list[dict]) -> str:
    if not cells:
        return "_No cells yet. Start the sweep and this fills in._"
    body = []
    for cell in sorted(cells, key=lambda c: (c["role"], c["level"], c["mode"],
                                             c["replicate"])):
        rate = cell["silent_error_rate"]
        if not cell["complete"] and cell["rate_value"] is None:
            rate = NOT_MEASURED
        cost = cell["cost_usd"]["value"]
        money = f"est. ${cost:.4f}" if cost else "—"
        body.append(f"| {cell['label']} | {rate} | {money} |")
    return ROW_HEADER + "\n".join(body)


AWAITING = "_awaiting measurement — this row fills in when both cells land_"

CROSS_MODEL_NOTE = (
    "**This row is cross-model, and the reading column carries no p-value on purpose.** "
    "Both models are reasoning models that reject a pinned temperature, so both arms "
    "carry run-to-run variance and a significance claim across them would be reading "
    "two noisy arms as if only one thing had changed. `loopeng.sweep.diff` refuses it "
    "in code rather than in a caption. Every reading below is computed from the cells "
    "on this screen; none is stored."
)


def _badged(cell: dict | None) -> str:
    if cell is None:
        return NOT_MEASURED
    return cell["silent_error_rate"]


def _comparison(cells: list[dict]) -> str:
    """The named secondary, derived, with the live/reference status of BOTH sides.

    Every reading comes from `loopeng.sweep.diff`. Nothing here is typed — see the module
    docstring for what was, and what the derived answer turned out to be instead.
    """
    by_key = {c["key"]: c for c in cells}
    derived = {c.key_a: c for c in named_secondary_deltas(cells)}
    lines = [
        "### Cheap + loop vs frontier one-shot — the pre-registered NAMED SECONDARY",
        "",
        "| level | cheap + loop | frontier one-shot | reading |",
        "|---|---|---|---|",
    ]
    # Levels come from the prompt module, so a new level appears here without anyone
    # remembering to add a row — and cannot appear with a stored conclusion attached.
    for level in LEVELS:
        cheap = by_key.get(f"agent_{level}_loop_r0")
        frontier = by_key.get(f"reference_{level}_one_shot_r0")
        comparison = derived.get(f"agent_{level}_loop_r0")
        # The row renders whether or not the cells landed. What it must never do is fill
        # the gap with a conclusion nothing on screen supports.
        reading = comparison.reading() if comparison else AWAITING
        lines.append(f"| {level} | {_badged(cheap)} | {_badged(frontier)} | {reading} |")
    lines.append("")
    lines.append(CROSS_MODEL_NOTE)
    return "\n".join(lines)


def build_dial_app(sweep_dir: Path = SWEEP_DIR) -> gr.Blocks:
    def _refresh(_state):
        # Cells on disk, and nothing else. There is no stored set to fold in: every
        # figure this view can draw was computed by the run that is being watched.
        cells = load_all(sweep_dir)
        done = [c for c in cells if c["complete"]]
        # A deadline-stopped cell is FINISHED at a smaller n, not unfinished. Counting
        # it with the in-progress cells dropped its items out of the stamp — so the
        # screen understated how much had actually been measured — and called it
        # incomplete, which invites a room to wait for a row that will never move.
        stopped = [c for c in cells if c.get("stopped_early")]
        landed = sum(c["rate_n"] for c in done + stopped)
        status = f"{len(done)} of {len(cells)} cells complete"
        if stopped:
            status += f", {len(stopped)} stopped at the deadline"
        return (
            _rows(cells),
            _comparison(cells),
            stamp(landed if landed else None),
            status,
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
