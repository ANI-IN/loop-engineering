"""Improve page (Section 4: Hill-climbing loop): experiments of this session, the holdout ledger,
the analyzer team's candidate as a knowledge diff, human approval, and the gate's verdict.

Only a baseline started in the open session counts. With none, the ledger says so and offers one
action, to run it. The ledger links to the LangSmith trace list filtered by knowledge version;
there is no experiment-comparison view.
"""

from __future__ import annotations

import streamlit as st
from datapilot_console import components, frame, improve_view, ops_reads, views, widgets
from datapilot_console.api_client import OVERBROAD_RULE
from datapilot_console.frame import Live

from datapilot.settings import get_settings

frame.check_api()


def start_baseline() -> None:
    frame.act(lambda: frame.api().run_experiment("active"))


def body(live: Live) -> None:
    view = live.view("improve", lambda: improve_view.build(live))
    components.holdout_ledger(
        view["ledger"], on_start_baseline=start_baseline, key="improve-ledger"
    )
    if view["gate"]:
        st.markdown(widgets.gate_line(view["gate"]))

    # Two rows, so no label is cut at a 1280-pixel class screen (test_console checks the widths).
    columns = st.columns(3)
    if view["has_baseline"] and columns[0].button(
        "Run experiment on the active version", key="improve-baseline"
    ):
        start_baseline()
    if columns[1].button("Run analyzer", type="primary", key="improve-analyzer"):
        frame.act(lambda: frame.api().run_analyzer())
    if columns[2].button("Run experiment on the candidate", key="improve-candidate"):
        frame.act(lambda: frame.api().run_experiment("candidate"))
    optional = st.columns([2, 1])
    if optional[0].button("Add the over-broad rule to the active version", key="improve-overbroad"):
        frame.act(lambda: frame.api().run_experiment("active", plus_rule=OVERBROAD_RULE))
    # The naive analyzer demo's planted half, for its own two requests only, shown only where the
    # api takes planted flags: what `make demo NAME=improve-naive-analyzer-blocked` queues.
    if get_settings().datapilot_allow_demo_controls and optional[1].button(
        "Run the naive analyzer (planted)", key="improve-naive-analyzer"
    ):
        frame.act(lambda: frame.api().run_naive_analyzer())
    # The finale's step after the promotion: the unattended level for the families it cleared.
    autonomy = live.view(
        "improve-autonomy", lambda: views.autonomy_control(ops_reads.finale_state(live.conn))
    )
    note, control = st.columns([3, 1.5])
    note.caption(" ".join(t for t in (autonomy["text"], autonomy["blocked"]) if t))
    if control.button(
        autonomy["label"], key="improve-autonomy", disabled=bool(autonomy["blocked"])
    ):
        frame.act(lambda: frame.api().set_autonomy(autonomy["target"]))
    frame.show_action_error()

    candidate = view["candidate"]
    if candidate is None:
        st.write(views.no_candidate_text(view["promotion"]))
        return
    st.subheader(f"Knowledge diff, active version to {candidate['version']}")
    if view["selection"]:
        st.caption(view["selection"])
    st.code(view["diff"] or "No change from the active version.", language="diff")
    if candidate["status"] == "draft":
        if st.button(f"Approve {candidate['version']}", key="improve-approve"):
            frame.act(lambda: frame.api().approve_version(candidate["version"]))
    else:
        st.write(f"{candidate['version']} is {candidate['status']}.")


frame.live_page("improve", body)
