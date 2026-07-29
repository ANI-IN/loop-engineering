"""VERIFY: the AST verifier, and the swap that makes the score rise while it catches less.

The narration is generated, not written: `loopeng.verify.swap._reading` computes what to
say from what actually happened, refuses to claim a dashboard effect that did not
appear, and always labels the correctness comparison underpowered with the structural
bound on how many items could possibly have differed.
"""

from pathlib import Path

import gradio as gr

from loopeng.gold.build import GoldItem
from loopeng.verify.governance import run_governance_probes
from loopeng.verify.loop import DEFAULT_MAX_ATTEMPTS, run_verified
from loopeng.verify.swap import run_swap
from loopeng.views.chrome import NOT_MEASURED, stamp


def _attempts(run) -> str:
    lines = [f"**termination** `{run.termination}` · rejections **{run.rejections}**", ""]
    for step in run.attempts:
        head = "ran" if step.attempt.executed else "failed to execute"
        lines.append(f"### Attempt {step.attempt.n} — {head}")
        lines.append(f"```sql\n{step.attempt.sql or '(no SQL)'}\n```")
        if step.attempt.error:
            lines.append(f"**database said:** `{step.attempt.error}`")
        elif not step.verdict.ok:
            lines.append("**VERIFIER REJECTED — this ran cleanly and is still wrong:**")
            lines.append(step.verdict.feedback())
        else:
            lines.append(
                f"**accepted**, returned `{str(step.attempt.rows)[:140]}`"  # layout: row preview
            )
        lines.append("")
    return "\n".join(lines)


def _probe_table() -> str:
    report = run_governance_probes()
    lines = [f"### Rule surface — {report['n_sound']}/{report['n_rules']} sound", "",
             "| rule | catches the violation | accepts a nearby-legitimate query |",
             "|---|---|---|"]
    for rule, body in report["by_rule"].items():
        lines.append(f"| {rule} | {body['caught_the_violation']} | "
                     f"{body['accepted_the_nearby_legitimate']} |")
    return "\n".join(lines)


def build_verify_app(items: list[GoldItem], warehouse: Path) -> gr.Blocks:
    by_id = {item.item_id: item for item in items}
    rule_bearing = [i.item_id for i in items if i.rules]
    fan_out_items = [i for i in items if "fan_out" in i.rules][:6]  # layout: fits one screen

    def _run(item_id, _state):
        item = by_id[item_id]
        run = run_verified(item.question, warehouse=warehouse, rules=item.rules,
                           item_id=item.item_id, max_attempts=DEFAULT_MAX_ATTEMPTS)
        return (f"**{item.question}**\n\nrules: `{', '.join(item.rules)}`",
                _attempts(run), stamp(len(run.attempts)), run)

    def _swap(_state):
        report = run_swap(fan_out_items, warehouse, level="L3",
                          max_attempts=DEFAULT_MAX_ATTEMPTS)
        rows = ["| verifier | accepted | actually correct | rejections | cost | probe surface |",
                "|---|---|---|---|---|---|"]
        for name, arm in report["arms"].items():
            surface = report["probe_surface"][name]
            rows.append(
                f"| **{name.upper()}** | {arm['acceptance_rate']} | "
                f"{arm['correctness_rate']} | {arm['rejections']} | "
                f"est. ${arm['cost_usd_estimated']:.4f} | "
                f"{surface['n_sound']}/{surface['n_rules']} sound, "
                f"{surface['n_missed_violations']} missed |"
            )
        return ("\n".join(rows), report["reading"], stamp(report["n_items"]), report)

    with gr.Blocks(title="VERIFY") as app:
        gr.Markdown(
            "# VERIFY — catching a query that ran and is still wrong\n"
            "Level 1 retries when SQL *crashes*. This catches SQL that *runs* and "
            "breaks a business rule."
        )
        state = gr.State(None)
        swap_state = gr.State(None)
        stamped = gr.Markdown("")

        with gr.Row():
            picker = gr.Dropdown(rule_bearing, value=rule_bearing[0] if rule_bearing else None,
                                 label="Gold item", scale=3)  # layout: column width
            go = gr.Button("Run through the verifiers", variant="primary")
        header = gr.Markdown("")
        attempts = gr.Markdown("_no run yet_")

        gr.Markdown("---\n## The swap — AST verifier vs regex verifier")
        swap_go = gr.Button("Swap the verifier and re-run")
        swap_table = gr.Markdown("")
        swap_reading = gr.Markdown(NOT_MEASURED)
        gr.Markdown(_probe_table())

        go.click(_run, [picker, state], [header, attempts, stamped, state])
        swap_go.click(_swap, [swap_state], [swap_table, swap_reading, stamped, swap_state])

    return app
