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

from loopeng.agent.trap import TrapState, run_trap
from loopeng.gold.build import GoldItem
from loopeng.views.chrome import NOT_MEASURED, stamp
from loopeng.views.render import grid, render_cost, scoreboard


def build_trap_app(items: list[GoldItem], warehouse: Path) -> gr.Blocks:
    """The one TRAP view. There were two, and they had drifted — see views/render.py."""
    item_ids = [item.item_id for item in items]

    def _run(_state):
        state = TrapState()
        yield grid(state, item_ids), "_running…_", NOT_MEASURED, stamp(None), state
        run_trap(items, warehouse, state=state)
        landed = sum(1 for c in state.cells.values() if c.done)
        yield (grid(state, item_ids),
               f"landed in {state.wall_clock_seconds:.0f}s — press reveal",
               render_cost(state.ledger()), stamp(landed), state)

    def _reveal(state):
        # A flag. No model calls; a test asserts it against this view.
        if state is None:
            return "_run the trap first_", "", NOT_MEASURED, stamp(None), state
        state.reveal()
        landed = sum(1 for c in state.cells.values() if c.done)
        return (grid(state, item_ids), scoreboard(state),
                render_cost(state.ledger()), stamp(landed), state)

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
        # Cost ticking while the grid fills was in the version this view replaced, and
        # it is the better of the two: the trap's whole point is what the two arms cost
        # to be wrong in different ways.
        cost = gr.Markdown(NOT_MEASURED)
        status = gr.Markdown("")
        board = gr.Markdown("")
        table = gr.Markdown("")

        go.click(_run, [state], [table, status, cost, stamped, state])
        reveal.click(_reveal, [state], [table, board, cost, stamped, state])

    return app
