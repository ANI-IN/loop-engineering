"""Native, themed pieces the Agent and Verify pages share: the tool-call timeline, the gold check,
the checklist, the defense layers, and the reviewer. Status is always a shape and a word."""

from __future__ import annotations

from typing import Any

import altair as alt
import pandas as pd
import streamlit as st

from datapilot.contracts.lifecycle import RunStatus
from datapilot_console.views import waiting_line

PASSED = ":green[:material/check_box: **Passed**]"
FAILED = ":red[:material/disabled_by_default: **Failed**]"
NOT_RUN = ":gray[:material/check_box_outline_blank: **Not run**]"
SHAPE = {"passed": PASSED, "failed": FAILED, "not_run": NOT_RUN}
LAYER = {
    "Passed through": ":gray[:material/check_box_outline_blank: **Passed through**]",
    "Stopped it": ":red[:material/disabled_by_default: **Stopped it**]",
    "Not reached": ":gray[:material/check_box_outline_blank: **Not reached**]",
}


def escape(text: Any) -> str:
    """Markdown-safe text: run data never becomes markup."""
    out = str(text)
    for char in "\\`*_{}[]<>()#+-.!|$~:":
        out = out.replace(char, "\\" + char)
    return out


def run_status(view: dict[str, Any], running_note: str) -> None:
    run = view["run"]
    line = f"**{run['word']}**. {escape(run['question'])}"
    st.markdown(line)
    note = waiting_line(RunStatus(run["status"]), running_note)
    if note:
        st.caption(note)


def timeline(tools: list[dict[str, Any]], key: str) -> None:
    if not tools:
        st.write("Tool calls: none yet.")
        return
    total = sum(t["seconds"] for t in tools)
    frame = pd.DataFrame(tools)
    chart = (
        alt.Chart(frame)
        .mark_bar()  # the theme's first chart colour: ink
        .encode(
            x=alt.X("seconds:Q", title="Seconds"),
            y=alt.Y("label:N", sort=alt.EncodingSortField("order"), title=None),
            tooltip=["tool", "seconds"],
        )
        .properties(height=alt.Step(30))
        # Nothing under 14 px: axis words at the strip size, tool names never cut short.
        .configure_axis(labelFontSize=16, titleFontSize=16, labelLimit=360)
    )
    st.markdown(f"**Tool calls**, total {total:.1f} s")
    st.altair_chart(chart, width="stretch", height="content", key=key)


def gold(view: dict[str, Any]) -> None:
    found = view["gold"]
    if found is None:
        return
    st.markdown("**Answer against gold**")
    shape = (
        ":green[:material/check_box: **Match**]"
        if found["passed"]
        else ":red[:material/disabled_by_default: **Mismatch**]"
    )
    st.markdown(
        f"Agent answer: **{escape(found['agent_value'])}**  \n"
        f"Gold answer: **{escape(found['gold_value'])}**  \n"
        f"{shape} {escape(found['reason'])}"
    )


def checklist(view: dict[str, Any]) -> None:
    found = view["checklist"]
    st.markdown(f"**Checklist, attempt {found['attempt']} of {found['max_attempts']}**")
    lines = []
    for row in found["rows"]:
        reason = f": {escape(row['reason'])}" if row["reason"] else ""
        lines.append(f"{SHAPE[row['state']]} {escape(row['label'])}{reason}")
    st.markdown("  \n".join(lines))


def defense(view: dict[str, Any]) -> None:
    statements = view["defense"]
    if not statements:
        return
    st.markdown("**Defense layers**")
    for statement in statements:
        # wrapped, so a long statement (the data-modifying CTE) shows whole in its column
        st.code(statement["sql"], language="sql", wrap_lines=True)
        st.markdown(
            "  \n".join(
                f"{LAYER[layer['word']]} {escape(layer['layer'])}: {escape(layer['detail'])}"
                for layer in statement["layers"]
            )
        )


GATE = {
    "promoted": ":green[:material/check_box: **Gate: passed.**]",
    "ready": ":orange[:material/hourglass_top: **Gate: ready for human approval.**]",
    "blocked": ":red[:material/disabled_by_default: **Gate: blocked.**]",
}


def gate_line(gate: dict[str, str]) -> str:
    """The gate's verdict as one sentence with its shape and word (from views.gate_view)."""
    return f"{GATE[gate['state']]} {escape(gate['sentence'])}"


def reviewer(view: dict[str, Any]) -> None:
    found = view["reviewer"]
    if found is None:
        return
    reasons = "; ".join(found["reasons"])
    st.markdown(f"Reviewer: **{escape(found['outcome'])}**. {escape(reasons)}")
