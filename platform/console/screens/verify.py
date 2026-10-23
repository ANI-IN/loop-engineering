"""Verify page (Section 2: Verification loop): the grader checklist with its attempts, the defense
layers that stopped a statement, the gold check beside the reviewer, and the retry cap."""

from __future__ import annotations

import streamlit as st
from datapilot_console import components, frame, run_view, widgets
from datapilot_console.api_client import SPINE_QUESTION
from datapilot_console.frame import Live

from datapilot.contracts.api import EventSubmitted

ss = st.session_state
ss.setdefault("verify-run", None)
frame.check_api()

EMPTY = "Send a check or ask the spine question to see the graders and the defense layers."
RUNNING = "Running the agent and the graders. This takes 5 to 15 seconds."


def started(reply: EventSubmitted | None) -> None:
    if reply:
        ss["verify-run"] = str(reply.run_id)


def body(live: Live) -> None:
    malicious, failing, spine, cartesian, _ = st.columns([1.2, 1.2, 1.4, 1.3, 1])
    if malicious.button("Send malicious SQL", type="primary", key="verify-malicious"):
        started(frame.act(lambda: frame.api().demo("malicious-sql")))
    if failing.button("Inject failing grader", key="verify-failing"):
        started(frame.act(lambda: frame.api().demo("failing-grader")))
    if spine.button("Ask the spine question", key="verify-spine"):
        started(
            frame.act(lambda: frame.api().ask(SPINE_QUESTION, "verify-graders-pass-still-wrong"))
        )
    if cartesian.button("Send cartesian query", key="verify-cartesian"):
        started(frame.act(lambda: frame.api().demo("cartesian-query")))
    frame.show_action_error()

    view = live.view(
        "verify-run", lambda: run_view.build(live, ss["verify-run"], "verify-"), ss["verify-run"]
    )
    if view["run"] is None:
        st.write(EMPTY)
        components.annotated_sql(view["sql"], key="verify-sql")
        return
    widgets.run_status(view, RUNNING)
    left, right = st.columns(2, gap="large")
    with left:
        if view["checklist"]["any"]:
            widgets.checklist(view)
        attempts = view["checklist"]
        if view["run"]["status"] == "escalated":
            st.markdown(
                f":red[:material/disabled_by_default: **Stopped at the cap: escalated**] after "
                f"attempt {attempts['attempt']} of {attempts['max_attempts']}."
            )
        share = min(view["tokens"] / view["tokens_cap"], 1.0) if view["tokens_cap"] else 0.0
        st.write(f"Tokens for this run: {view['tokens']:,} of the {view['tokens_cap']:,} cap")
        st.progress(share)
    with right:
        widgets.defense(view)
        widgets.gold(view)
        widgets.reviewer(view)
    components.annotated_sql(view["sql"], key="verify-sql")
    st.write(view["run"]["summary"])


frame.live_page("verify", body)
