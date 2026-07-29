"""The intervention view: what the loop declined, and why, in plain English.

An abstention nobody can inspect is just a missing answer. The operator needs to see
which questions were declined, the reason in words rather than a score, and the
attempts behind the decision — otherwise "the system declined" is indistinguishable
from "the system broke".

Per-user state lives in `gr.State`. Never module scope: it works perfectly with one
person clicking and leaks the moment two browsers are open.

Answer submission is deliberately absent. It was named as polish, and a half-built
write path that silently drops an operator's answer is worse than an obvious gap.
"""

from pathlib import Path

import gradio as gr

from loopeng.triage.abstain import CONFIDENCE, decide, operating_point

NOT_MEASURED = "not yet measured"


def _threshold_label(threshold: float) -> str:
    names = [name for name, value in CONFIDENCE.items() if value >= threshold]
    return ", ".join(sorted(names)) or "nothing"


def render_declined(runs: list[dict], threshold: float) -> str:
    point = operating_point(runs, threshold)
    if not point["declined"]:
        return (
            f"**Nothing declined at threshold {threshold:.2f}.** "
            f"All {point['n_total']} questions were answered."
        )
    lines = [
        f"### {point['n_declined']} of {point['n_total']} questions declined",
        f"*Answered only when the run ends as: {_threshold_label(threshold)}*",
        "",
    ]
    for entry in point["declined"]:
        lines.append(f"**`{entry['item_id']}`** — {entry['reason']}")
        lines.append("")
    return "\n".join(lines)


def render_attempts(run: dict) -> str:
    """What the operator inspects to decide whether the decline was fair."""
    if not run:
        return "_select a declined question_"
    confidence, reason = decide(run, 1.0).confidence, decide(run, 1.0).reason
    return "\n".join([
        f"### `{run['item_id']}`",
        f"**Why it was declined:** {reason}",
        "",
        f"- ended as `{run.get('termination')}` after {run.get('n_attempts')} attempt(s)",
        f"- the verifier sent it back {run.get('rejections', 0)} time(s)",
        f"- confidence band: {confidence:.2f}",
        "",
        "**Last query the model wrote:**",
        f"```sql\n{run.get('sql') or '(no SQL recorded)'}\n```",
        "",
        f"**What it returned:** `{str(run.get('rows'))[:300]}`",
        "",
        "_The gold answer is deliberately not shown here. An operator judging whether a "
        "decline was fair should be looking at the query and the reason, not at the "
        "answer key._",
    ])


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
        return render_attempts(by_id.get(item_id))

    with gr.Blocks(title="Level 4 — abstention and intervention") as app:
        gr.Markdown(
            "# What the loop declined, and why\n"
            "Coverage is a **choice** here, not a synonym for 'did not crash'. "
            "Move the threshold and watch the trade."
        )
        state = gr.State(1.0)  # per-user, per-session. Never module scope.
        threshold = gr.Slider(0.0, 1.0, value=1.0, step=0.05, label="Abstention threshold")
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
