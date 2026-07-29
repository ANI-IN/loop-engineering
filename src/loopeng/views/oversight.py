"""OVERSIGHT: abstention, escalation and triage — stage 4's view.

Three things the loop gained in Phase 4, and the caveats that travel with them. Both
caveats are rendered in the view rather than kept in a report, because a number on a
projector outlives whatever was said next to it.

  - the abstention threshold shown was chosen to fit the escalation cap, not on
    principle
  - escalation's conversion figure shows THAT escalation converts, not how often
"""

import json
from pathlib import Path

import gradio as gr

from loopeng.sweep.orchestrator import load_all
from loopeng.sweep.runner import SWEEP_DIR
from loopeng.triage.abstain import DEFAULT_THRESHOLD, curve, operating_point
from loopeng.triage.escalate import MAX_ESCALATIONS
from loopeng.views.chrome import NOT_MEASURED, stamp
from loopeng.views.render import render_declined

CELL_KEY = "worker_L0_loop_r0"

# Built from the constants rather than typed. A caveat that names a threshold the
# slider no longer opens on, or a cap the escalation no longer uses, is worse than
# no caveat: it is a disclosure that has quietly become false.
THRESHOLD_CAVEAT = (
    f"**The {DEFAULT_THRESHOLD:.2f} threshold was chosen to fit the n={MAX_ESCALATIONS} "
    "escalation cap, not on principle.** At the top of the range the decline rate is far "
    "higher and would have blown that cap immediately. A measurement shaped by a budget "
    "constraint gets said out loud."
)

ESCALATION_CAVEAT = (
    "**This shows THAT escalation converts, not how often.** The conversion figure is "
    "over a handful of escalated questions, capped deliberately so cost is a ceiling "
    "rather than something that scales with the decline rate. The interval is wide "
    "enough that the rate itself should not be quoted."
)

ABSTENTION_READING = (
    "Raising the threshold answers fewer questions and gets more of the answered ones "
    "right. The signal is informative — declining at random would leave precision at "
    "the base rate, and it climbs well above it. **But no threshold makes this safe:** "
    "precision tops out well short of certainty, so even the most confident answers are "
    "wrong a large fraction of the time. Abstention improves the trade-off; it does not "
    "substitute for the spec."
)


def _curve_table(runs: list[dict]) -> str:
    lines = ["| threshold | answered | declined | coverage | precision |",
             "|---|---|---|---|---|"]
    for point in curve(runs):
        lines.append(
            f"| {point['threshold']:.2f} | {point['n_answered']} | {point['n_declined']} "
            f"| {point['coverage']} | {point['precision']} |"
        )
    return "\n".join(lines)


def _escalation_panel(path: Path) -> str:
    path = Path(path)
    if not path.is_file():
        return f"### Escalation\n\n_{NOT_MEASURED}_"
    body = json.loads(path.read_text())
    return "\n".join([
        "### Escalation — when the cheap model declines, hand it up",
        "",
        f"- declined: **{body['n_declined']}** of {body['n_asked']} ({body['escalation_rate']})",
        f"- escalated: **{body['n_escalated']}** (capped at {body['capped_at']})",
        f"- converted: **{body['n_converted']}** ({body['conversion_rate']})",
        f"- cost: est. ${body['cost_usd']['value']:.4f}",
        "",
        ESCALATION_CAVEAT,
    ])


def _triage_panel(path: Path) -> str:
    path = Path(path)
    if not path.is_file():
        return f"### Triage\n\n_{NOT_MEASURED}_"
    body = json.loads(path.read_text())
    rows = ["| cause | n | what it means |", "|---|---|---|"]
    for cause, count in body["by_cause"].items():
        rows.append(f"| **{cause}** | {count} | {body['meanings'][cause]} |")
    return "\n".join([
        f"### Triage — {body['n_triaged']} failures classified by cause",
        "",
        *rows,
        "",
        f"**Gold:** {body['gold_verdict']}",
    ])


def build_oversight_app(sweep_dir: Path = SWEEP_DIR,
                        escalation_path: Path = Path("results/phase4_escalation.json"),
                        triage_path: Path = Path("results/phase4_triage.json")) -> gr.Blocks:
    def _load():
        cells = {c["key"]: c for c in load_all(sweep_dir)}
        return cells.get(CELL_KEY, {}).get("items", [])

    def _refresh(threshold, _state):
        runs = _load()
        if not runs:
            return (f"_{NOT_MEASURED} — run the sweep first._", "", "", "",
                    stamp(None), threshold)
        point = operating_point(runs, threshold)
        summary = "\n".join([
            f"**coverage** {point['coverage']}",
            "",
            f"**precision** {point['precision']}",
            "",
            ABSTENTION_READING,
            "",
            THRESHOLD_CAVEAT,
        ])
        return (
            summary, _curve_table(runs), render_declined(runs, threshold),
            f"{_escalation_panel(escalation_path)}\n\n---\n\n{_triage_panel(triage_path)}",
            stamp(point["n_total"]), threshold,
        )

    with gr.Blocks(title="OVERSIGHT") as app:
        gr.Markdown("# OVERSIGHT — declining, escalating, and classifying failures")
        state = gr.State(DEFAULT_THRESHOLD)
        stamped = gr.Markdown("")
        threshold = gr.Slider(0.0, 1.0, value=DEFAULT_THRESHOLD,
                              step=0.05,  # layout: slider granularity
                              label="Abstention threshold — coverage is a CHOICE")
        summary = gr.Markdown("")
        with gr.Row():
            with gr.Column():
                gr.Markdown("### The trade, at every threshold")
                table = gr.Markdown("")
            with gr.Column():
                panels = gr.Markdown("")
        declined = gr.Markdown("")

        outputs = [summary, table, declined, panels, stamped, state]
        threshold.change(_refresh, [threshold, state], outputs)
        app.load(_refresh, [threshold, state], outputs)

    return app
