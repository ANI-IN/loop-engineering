"""AGENT: one question, live, with the attempt timeline — and the room's enqueue box.

The enqueue box is how the room participates. It writes a row to `question_queue` and
returns immediately; **it does not need the worker to be running.** A row submitted
with no worker up sits in `queued`, which is correct behaviour and worth showing: a
queue whose consumer is down is not a queue that lost your question.

A QR to whichever URL is live is rendered here, because nobody types a URL off a
projector.
"""

from pathlib import Path

import gradio as gr

from loopeng.agent.loop import DEFAULT_MAX_ATTEMPTS, run_question
from loopeng.agent.ui import render_attempts, render_cost
from loopeng.queue import store
from loopeng.views.chrome import NOT_MEASURED, stamp


def _queue_table(queue_path: Path) -> str:
    con = store.connect(queue_path)
    rows = store.all_rows(con)
    con.close()
    if not rows:
        return "_The queue is empty._"
    lines = ["| id | status | question | result |", "|---|---|---|---|"]
    for row in rows[-12:]:  # layout: last screenful
        result = (row.result or "")[:60]  # layout: column width
        lines.append(
            f"| {row.id} | **{row.status}** | {row.question[:52]} | {result} |"  # layout
        )
    counts = store.counts(con := store.connect(queue_path))
    con.close()
    return "\n".join(lines) + f"\n\n`{counts}`"


def build_agent_app(warehouse: Path, queue_path: Path = store.DEFAULT_QUEUE_PATH,
                    level: str = "L3", share_url: str | None = None) -> gr.Blocks:
    def _ask(question, role, max_attempts, _state):
        if not question.strip():
            return "_enter a question_", NOT_MEASURED, stamp(None), None
        run = run_question(question, warehouse=warehouse, role=role, level=level,
                           max_attempts=int(max_attempts))
        return (render_attempts(run), render_cost(run.ledger),
                stamp(len(run.attempts)), run)

    def _enqueue(question, _state):
        if not question.strip():
            return "_enter a question first_", _queue_table(queue_path), _state
        con = store.connect(queue_path)
        row_id = store.enqueue(con, question.strip())
        con.close()
        return (
            f"**Queued as id {row_id}.** If no worker is running it stays `queued` — "
            "the queue did not lose it, nothing has picked it up yet.",
            _queue_table(queue_path), _state,
        )

    with gr.Blocks(title="AGENT") as app:
        gr.Markdown(
            f"# AGENT — one question, live\n"
            f"Retries **only on execution failure**. Prompt level `{level}`. "
            "Nothing here checks whether a query that ran is *right*."
        )
        last_run = gr.State(None)
        queue_state = gr.State(None)

        with gr.Row():
            question = gr.Textbox(label="Question", scale=4, lines=2)  # layout: row split
            role = gr.Dropdown(["worker", "frontier"], value="worker", label="Model")
            attempts = gr.Number(value=DEFAULT_MAX_ATTEMPTS, label="Max attempts", precision=0)
        with gr.Row():
            ask = gr.Button("Run it here", variant="primary")
            send = gr.Button("Send to the queue")
        stamped = gr.Markdown("")
        cost = gr.Markdown(NOT_MEASURED)
        timeline = gr.Markdown("_no run yet_")

        gr.Markdown("---\n## The queue — submit from your phone")
        if share_url:
            gr.Markdown(f"**{share_url}**")
            qr = Path("results/share_qr.png")
            if qr.is_file():
                gr.Image(str(qr), height=240,  # layout: scannable from the back row
                         show_label=False, show_download_button=False)
        note = gr.Markdown("")
        table = gr.Markdown("")

        ask.click(_ask, [question, role, attempts, last_run],
                  [timeline, cost, stamped, last_run])
        send.click(_enqueue, [question, queue_state], [note, table, queue_state])
        app.load(lambda s: (_queue_table(queue_path), s), [queue_state], [table, queue_state])

    return app
