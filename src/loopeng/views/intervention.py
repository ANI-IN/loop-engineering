"""INTERVENTION: what the loop declined, and why, in plain English.

An abstention nobody can inspect is just a missing answer. The operator needs to see
which questions were declined, the reason in words rather than a score, and the attempts
behind the decision — otherwise "the system declined" is indistinguishable from "the
system broke".

Per-user state lives in `gr.State`. Never module scope: it works perfectly with one
person clicking and leaks the moment two browsers are open.

Answer submission is deliberately absent. It was named as polish, and a half-built write
path that silently drops an operator's answer is worse than an obvious gap.

Moved here from `triage/ui.py`: Gradio composition belongs in `views/` and nowhere else.
See `views/render.py` for what that boundary is fixing.
"""

from pathlib import Path

import gradio as gr

from loopeng.triage.abstain import DEFAULT_THRESHOLD, operating_point
from loopeng.views.chrome import NOT_MEASURED
from loopeng.views.render import render_declined, render_declined_run

# Slider bounds and step. Geometry, not a finding: the thresholds that mean anything are
# the CONFIDENCE bands, and the slider merely has to be able to land on each of them.
SLIDER_MIN, SLIDER_MAX, SLIDER_STEP = 0.0, 1.0, 0.05  # layout: slider bounds and step


def build_intervention_app(runs: list[dict], warehouse: Path | None = None) -> gr.Blocks:
    by_id = {r["item_id"]: r for r in runs}

    def _refresh(threshold, _state):
        point = operating_point(runs, threshold)
        summary = (
            f"**coverage** {point['coverage']}  \n"
            f"**precision** {point['precision']}  \n"
            f"*Raising the threshold answers fewer questions and gets more of the "
            f"answered ones right. That trade is the operator's to make.*"
        )
        choices = [entry["item_id"] for entry in point["declined"]]
        return (
            render_declined(runs, threshold),
            summary,
            gr.update(choices=choices, value=choices[0] if choices else None),
            threshold,
        )

    def _inspect(item_id):
        return render_declined_run(by_id.get(item_id))

    with gr.Blocks(title="Level 4 — abstention and intervention") as app:
        gr.Markdown(
            "# What the loop declined, and why\n"
            "Coverage is a **choice** here, not a synonym for 'did not crash'. "
            "Move the threshold and watch the trade."
        )
        # Per-user, per-session. Never module scope.
        state = gr.State(SLIDER_MAX)
        threshold = gr.Slider(SLIDER_MIN, SLIDER_MAX, value=SLIDER_MAX, step=SLIDER_STEP,
                              label="Abstention threshold")
        gr.Markdown(
            f"*The threshold OVERSIGHT opens on is {DEFAULT_THRESHOLD:.2f}, and it was "
            f"chosen to fit the escalation cap rather than on principle. This view opens "
            f"at the top of the range so the trade is visible from the first move.*"
        )
        summary = gr.Markdown(NOT_MEASURED)
        with gr.Row():
            declined = gr.Markdown("")
            with gr.Column():
                picker = gr.Dropdown([], label="Inspect a declined question")
                detail = gr.Markdown("_select a declined question_")

        threshold.change(_refresh, [threshold, state], [declined, summary, picker, state])
        picker.change(_inspect, [picker], [detail])
        app.load(_refresh, [threshold, state], [declined, summary, picker, state])

    return app
