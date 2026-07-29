"""The exhibit: everything that can be shown without spending anything.

**The security boundary is that this makes zero model calls**, and it is verified the
way the views were — by spying on the `anthropic.Anthropic` constructor and asserting
none is ever built. That test is required rather than nice to have: the exhibit is
public, and a path that quietly spends would spend somebody else's money.

What survives the freeze, and what does not:

  DIAL, OVERSIGHT   stored reference measurements, every figure hatched and dated
  VERIFY            FULLY LIVE, and this is the best part. V1 and V2 are pure functions
                    over SQL text, so the rule checks, the probe surface and the
                    AST-to-regex swap all work at zero cost on stored queries. Nothing
                    here is degraded.
  TRAP              stored attempts, with the reveal working as a real state flip
  AGENT, enqueue    DISABLED, with a line saying live model calls run only in the
                    session. Disabled, not hidden by CSS — a button that is merely
                    invisible is still a button.
"""

from pathlib import Path

import gradio as gr

from loopeng.sweep.reference import MEASURED_ON

BANNER = (
    f"### This is a frozen exhibit\n"
    f"Every figure below was **measured on {MEASURED_ON}** and is shown with its date. "
    f"Nothing here is computed now, and nothing here calls a model. "
    f"The live version runs from a laptop during the workshop, where the same views "
    f"compute their numbers in front of the room and stamp them with the time."
)

DISABLED_NOTE = (
    "**Disabled in the exhibit.** This path makes live model calls, which run only "
    "during the session. The verifier views beside it are fully live, because rule "
    "checking is a pure function over SQL and costs nothing."
)


def banner() -> gr.Markdown:
    return gr.Markdown(BANNER)


def disabled_panel(title: str) -> gr.Blocks:
    with gr.Column() as panel:
        gr.Markdown(f"## {title}")
        gr.Markdown(DISABLED_NOTE)
        gr.Button(f"Run {title}", interactive=False)
    return panel


def build_exhibit_app(sweep_dir: Path, gold_items, warehouse: Path) -> gr.Blocks:
    """One page, tabs per view, with the spending paths disabled rather than hidden."""
    from loopeng.views.dial import build_dial_app  # noqa: F401  (kept for parity)
    from loopeng.views.oversight import _escalation_panel, _triage_panel
    from loopeng.views.verify import _probe_table

    with gr.Blocks(title="Loop Engineering — exhibit") as app:
        gr.Markdown("# Loop Engineering")
        banner()

        with gr.Tab("VERIFY (live)"):
            gr.Markdown(
                "## The rule surface\n"
                "Fully live. Every check below runs now, on stored SQL, at zero cost — "
                "rule verification is a pure function over the query text."
            )
            gr.Markdown(_probe_table())

        with gr.Tab("DIAL"):
            gr.Markdown("## Silent-error rate by cell")
            gr.Markdown(_reference_rows())

        with gr.Tab("OVERSIGHT"):
            gr.Markdown(_frozen_curve_table())
            gr.Markdown(_escalation_panel(Path("results/phase4_escalation.json")))
            gr.Markdown(_triage_panel(Path("results/phase4_triage.json")))

        with gr.Tab("AGENT (session only)"):
            disabled_panel("the agent loop")

    return app


def _reference_rows() -> str:
    from loopeng.sweep.reference import load_reference
    from loopeng.views.dial import _rows

    return _rows(load_reference())


def _frozen_curve_table(path: Path = Path("results/reference/abstention_curve.json")) -> str:
    """The abstention curve, frozen like the reference cells.

    Reference cells have their per-item records stripped, so the curve cannot be
    recomputed on the Space. Rather than showing OVERSIGHT with its most interesting
    panel empty, the curve is frozen once and shipped with its date — the same
    treatment, for the same reason.
    """
    import json

    path = Path(path)
    if not path.is_file():
        return "_Abstention curve not yet measured._"
    body = json.loads(path.read_text())
    lines = [
        f"### The trade, at every threshold — {body['label']}",
        f"*measured {body['measured_on']}, not computed now*",
        "",
        "| threshold | answered | declined | coverage | precision |",
        "|---|---|---|---|---|",
    ]
    for point in body["points"]:
        lines.append(
            f"| {point['threshold']:.2f} | {point['n_answered']} | {point['n_declined']} "
            f"| {point['coverage']} | {point['precision']} |"
        )
    return "\n".join(lines)
