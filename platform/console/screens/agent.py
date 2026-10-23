"""Agent page (Section 1: Agent loop): a question, its tool calls, its SQL with trap notes, and
the answer against gold. Shows the open session's runs only."""

from __future__ import annotations

import streamlit as st
from datapilot_console import components, frame, run_view, widgets
from datapilot_console.api_client import SPINE_QUESTION
from datapilot_console.frame import Live

from datapilot.contracts.api import EventSubmitted

ss = st.session_state
ss.setdefault("agent-run", None)
frame.check_api()

EMPTY = "Ask a question to see the tool calls, the SQL, and the answer."
RUNNING = "Running the agent. This takes 5 to 15 seconds."


def started(reply: EventSubmitted | None) -> None:
    if reply:
        ss["agent-run"] = str(reply.run_id)


def body(live: Live) -> None:
    question = st.text_input("Question", key="agent-question", placeholder=SPINE_QUESTION)
    ask, spine, large, _ = st.columns([0.6, 1.4, 1.2, 3])
    if ask.button("Ask", type="primary", key="agent-ask", disabled=not question.strip()):
        started(frame.act(lambda: frame.api().ask(question, "agent-simple-question")))
    if spine.button("Ask the spine question", key="agent-spine"):
        started(frame.act(lambda: frame.api().ask(SPINE_QUESTION, "agent-confident-wrong-answer")))
    if large.button("Run large query", key="agent-large"):
        started(frame.act(lambda: frame.api().demo("large-query")))
    frame.show_action_error()

    view = live.view(
        "agent-run", lambda: run_view.build(live, ss["agent-run"], "agent-"), ss["agent-run"]
    )
    if view["run"] is None:
        st.write(EMPTY)
    else:
        widgets.run_status(view, RUNNING)
        widgets.timeline(view["tools"], key="agent-timeline")
    components.annotated_sql(view["sql"], key="agent-sql")
    if view["run"] is not None:
        if view["run"]["answer_text"]:
            st.markdown(f"**Answer** {widgets.escape(view['run']['answer_text'])}")
        widgets.gold(view)
        st.write(view["run"]["summary"])


frame.live_page("agent", body)
