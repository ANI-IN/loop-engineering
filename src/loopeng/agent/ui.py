"""Gradio views for Level 1. Crude on purpose; the content is the point.

**Per-user state lives in `gr.State` and nowhere else.** No module-level dict, no
`os.environ`. Module-scope state works perfectly with one person clicking and leaks
across sessions the moment two browsers are open — which is exactly the configuration
at Gate 6, and exactly the kind of bug that does not show up until it is in front of
people.

**Every number rendered here comes from a `Metric`.** A missing measurement renders
"not yet measured", never zero, never a placeholder. `Metric.render()` carries the n
and the interval, so precision cannot be overstated by accident.

**Visible failures render identically to successes until reveal.** A cell reading
"query failed" before the reveal would tell the room that row is wrong for free, which
leaks the answer the trap exists to withhold. They are counted separately and shown in
the reveal, where the distinction between a failure you can see and one you cannot is
the entire lesson.
"""

from pathlib import Path

import gradio as gr

from loopeng.agent.classify import Outcome
from loopeng.agent.loop import run_question
from loopeng.agent.trap import TrapState, arm_key, arm_label, run_trap
from loopeng.gold.build import GoldItem
from loopeng.metric import Metric

NOT_MEASURED = "not yet measured"

# Identical for every finished cell, whatever happened inside it. See the module
# docstring: a distinguishable "failed" cell is a free answer key.
_PENDING = "·"
_LANDED = "▪"


def render_metric(metric: Metric | None) -> str:
    return metric.render() if metric else NOT_MEASURED


def render_cost(ledger) -> str:
    """Always the est. prefix. Tokens are measured; dollars are a price table."""
    total = ledger.cost_usd()
    tokens = ledger.totals()
    return (
        f"est. ${total:.4f} · {tokens['n_calls']} calls · "
        f"{tokens['total_tokens']} tokens (in {tokens['input_tokens']}, "
        f"out {tokens['output_tokens']}, cache-w {tokens['cache_creation_input_tokens']}, "
        f"cache-r {tokens['cache_read_input_tokens']})"
    )


def render_attempts(run) -> str:
    """The attempt timeline.

    **A failed model call is never labelled `database said`.** It used to be: a typo'd
    API key rendered three attempts reading `database said: AuthenticationError`, which
    blames the warehouse for a credential problem and sends the reader to the wrong
    file. The two failures are told apart by `Attempt.model_call_failed`, which reads
    the recorded call outcome rather than guessing from an empty SQL string.
    """
    if run is None:
        return "_no run yet_"
    lines = [f"**termination:** `{run.termination}` · **model:** `{run.model_id}`", ""]
    for attempt in run.attempts:
        if attempt.model_call_failed:
            lines.append(f"### Attempt {attempt.n} — the model call failed")
            lines.append(f"**the API said:** `{attempt.error}`")
            lines.append("")
            continue
        status = "ran" if attempt.executed else "failed to execute"
        lines.append(f"### Attempt {attempt.n} — {status}")
        lines.append(f"```sql\n{attempt.sql or '(no SQL returned)'}\n```")
        if attempt.error:
            lines.append(f"**database said:** `{attempt.error}`")
        elif attempt.rows is not None:
            lines.append(f"**returned:** `{attempt.rows[:5]}`")
        lines.append("")
    return "\n".join(lines)


def build_run_app(warehouse: Path, level: str = "L3") -> gr.Blocks:
    """One question, one model, showing the attempt timeline and cost ticking."""

    def _go(question, role, max_attempts, _state):
        if not question.strip():
            return "_enter a question_", NOT_MEASURED, None
        run = run_question(
            question,
            warehouse=warehouse,
            role=role,
            level=level,
            max_attempts=int(max_attempts),
        )
        return render_attempts(run), render_cost(run.ledger), run

    with gr.Blocks(title="Level 1 — the agent loop") as app:
        gr.Markdown(
            f"# Level 1 — the agent loop\n"
            f"Retries **only on execution failure**. Prompt level `{level}`. "
            "Nothing here checks whether a query that ran is *right*."
        )
        # Per-user, per-session. Never module scope.
        last_run = gr.State(None)

        with gr.Row():
            question = gr.Textbox(label="Question", scale=4)
            role = gr.Dropdown(["worker", "frontier"], value="worker", label="Model")
            attempts = gr.Number(value=3, label="Max attempts", precision=0)
        go = gr.Button("Run", variant="primary")
        cost = gr.Markdown(NOT_MEASURED)
        timeline = gr.Markdown("_no run yet_")

        go.click(_go, [question, role, attempts, last_run], [timeline, cost, last_run])

    return app


def _grid(state: TrapState, item_ids: list[str]) -> str:
    labels = [arm_label(role, level) for role, level in state.arms]
    header = "| item | " + " | ".join(labels) + " |\n|---|" + "---|" * len(labels) + "\n"
    rows = []
    for item_id in item_ids:
        cells = []
        for role, level in state.arms:
            cell = state.cells.get((item_id, arm_key(role, level)))
            if not cell or not cell.done:
                cells.append(_PENDING)
            elif not state.revealed:
                # Identical for every landed cell — see the module docstring.
                cells.append(_LANDED)
            else:
                outcome = cell.judgement.outcome
                cells.append(
                    {
                        Outcome.CORRECT: "✅ correct",
                        Outcome.SILENT_ERROR: "🟥 **silently wrong**",
                        Outcome.VISIBLE_FAILURE: "⚠️ visible failure",
                    }[outcome]
                )
        rows.append(f"| `{item_id}` | " + " | ".join(cells) + " |")
    return header + "\n".join(rows)


def _scoreboard(state: TrapState) -> str:
    if not state.revealed:
        return "_scores withheld until reveal — they are already computed_"
    lines = []
    for role, level in state.arms:
        arm = arm_key(role, level)
        summary = state.summary(arm)
        rate = state.silent_error_rate(arm)
        lines.append(
            f"**{arm_label(role, level)}** — silent-error rate {render_metric(rate)} "
            f"(over {summary['n_ran_and_returned']} that ran) · "
            f"visible failures {summary['n_visible_failures']} · "
            f"unclassified {summary['n_unclassified']}"
        )
    if len(state.arms) == 2:
        paired = state.paired_comparison(arm_key(*state.arms[0]), arm_key(*state.arms[1]))
        lines.append(f"**Paired (McNemar exact):** {paired.render()}")
    return "\n\n".join(lines)


def build_trap_app(items: list[GoldItem], warehouse: Path) -> gr.Blocks:
    """The grid. Cells stream in; scoring is withheld, not deferred."""
    item_ids = [item.id if hasattr(item, "id") else item.item_id for item in items]

    def _run(state):
        state = TrapState()
        yield _grid(state, item_ids), NOT_MEASURED, "_running_", state
        run_trap(items, warehouse, state=state)
        yield (
            _grid(state, item_ids),
            render_cost(state.ledger()),
            f"landed in {state.wall_clock_seconds:.1f}s — press reveal",
            state,
        )

    def _reveal(state):
        # A state flip. No model calls; a test asserts it.
        if state is None:
            return "_run the trap first_", NOT_MEASURED, "", state
        state.reveal()
        return _grid(state, item_ids), render_cost(state.ledger()), _scoreboard(state), state

    with gr.Blocks(title="Level 1 — the trap") as app:
        gr.Markdown(
            "# The trap — the same model, with and without the rules\n"
            "**The only difference between the columns is whether the business rules "
            "were written down.** The L3 column is the baseline that makes L0 legible."
        )
        state = gr.State(None)
        with gr.Row():
            go = gr.Button("Run the trap", variant="primary")
            reveal = gr.Button("Reveal scoring")
        cost = gr.Markdown(NOT_MEASURED)
        status = gr.Markdown("")
        grid = gr.Markdown("")

        go.click(_run, [state], [grid, cost, status, state])
        reveal.click(_reveal, [state], [grid, cost, status, state])

    return app
