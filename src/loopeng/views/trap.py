"""TRAP: the grid fills, then the reveal — which is a STATE FLIP, not a re-run.

Two properties are load-bearing and both are tested against this view rather than only
against the script:

**Reveal makes zero model calls.** Every cell is judged the moment its result lands and
the judgement is held unrevealed. Re-running to score would burn the whole wall-clock
again and lose the room.

**Visible failures render identically to successes until reveal.** A cell reading
"query failed" before the reveal hands the room a free answer key for that row — they
would know it was wrong without being told.
"""

from pathlib import Path

import gradio as gr

from loopeng.agent.classify import Outcome
from loopeng.agent.trap import TrapState, arm_key, arm_label, run_trap
from loopeng.gold.build import GoldItem
from loopeng.paired import PAIRED_ARM_COUNT
from loopeng.views.chrome import NOT_MEASURED, stamp

# Identical for every landed cell, whatever happened inside it.
PENDING, LANDED = "·", "▪"


def grid(state: TrapState, item_ids: list[str]) -> str:
    labels = [arm_label(role, level) for role, level in state.arms]
    lines = ["| item | " + " | ".join(labels) + " |",
             "|---|" + "---|" * len(labels)]
    for item_id in item_ids:
        cells = []
        for role, level in state.arms:
            cell = state.cells.get((item_id, arm_key(role, level)))
            if not cell or not cell.done:
                cells.append(PENDING)
            elif not state.revealed:
                cells.append(LANDED)  # successes and failures look the same
            else:
                cells.append({
                    Outcome.CORRECT: "correct",
                    Outcome.SILENT_ERROR: "**SILENTLY WRONG**",
                    Outcome.VISIBLE_FAILURE: "visible failure",
                }[cell.judgement.outcome])
        lines.append(f"| `{item_id}` | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def scoreboard(state: TrapState) -> str:
    if not state.revealed:
        return "_Scores are already computed. They are withheld, not deferred._"
    lines = []
    for role, level in state.arms:
        arm = arm_key(role, level)
        summary = state.summary(arm)
        rate = state.silent_error_rate(arm)
        lines.append(
            f"**{arm_label(role, level)}** — silent-error rate "
            f"{rate.render() if rate else NOT_MEASURED} over "
            f"{summary['n_ran_and_returned']} that ran · "
            f"visible failures {summary['n_visible_failures']} · "
            f"unclassified {summary['n_unclassified']}"
        )
    if len(state.arms) == PAIRED_ARM_COUNT:
        paired = state.paired_comparison(arm_key(*state.arms[0]), arm_key(*state.arms[1]))
        lines.append(f"**Paired (McNemar exact):** {paired.render()}")
    return "\n\n".join(lines)


def build_trap_app(items: list[GoldItem], warehouse: Path) -> gr.Blocks:
    item_ids = [item.item_id for item in items]

    def _run(_state):
        state = TrapState()
        yield grid(state, item_ids), "_running…_", stamp(None), state
        run_trap(items, warehouse, state=state)
        landed = sum(1 for c in state.cells.values() if c.done)
        yield (grid(state, item_ids),
               f"landed in {state.wall_clock_seconds:.0f}s — press reveal",
               stamp(landed), state)

    def _reveal(state):
        # A flag. No model calls; a test asserts it against this view.
        if state is None:
            return "_run the trap first_", "", stamp(None), state
        state.reveal()
        landed = sum(1 for c in state.cells.values() if c.done)
        return grid(state, item_ids), scoreboard(state), stamp(landed), state

    with gr.Blocks(title="TRAP") as app:
        gr.Markdown(
            "# TRAP — the same model, with and without the rules\n"
            "**The only difference between the columns is whether the business rules "
            "were written down.**"
        )
        state = gr.State(None)
        with gr.Row():
            go = gr.Button("Run the trap", variant="primary")
            reveal = gr.Button("Reveal scoring")
        stamped = gr.Markdown("")
        status = gr.Markdown("")
        board = gr.Markdown("")
        table = gr.Markdown("")

        go.click(_run, [state], [table, status, stamped, state])
        reveal.click(_reveal, [state], [table, board, stamped, state])

    return app
