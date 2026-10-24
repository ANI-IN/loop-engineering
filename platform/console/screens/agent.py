"""Agent page (Section 1: Agent loop): a question, its tool calls, its SQL with trap notes, and
the answer against gold. Shows the open session's runs only."""

from __future__ import annotations

import streamlit as st
from datapilot_console import components, frame, run_view, widgets
from datapilot_console.api_client import SPINE_QUESTION
from datapilot_console.frame import Live

from datapilot import demo_questions
from datapilot.contracts.api import EventSubmitted

ss = st.session_state
ss.setdefault("agent-run", None)
frame.check_api()

EMPTY = "Ask a question to see the tool calls, the SQL, and the answer."
# Measured in calibration (docs/calibration-report.md): 14 to 39 seconds for the simple question,
# 37 to 76 for the confident wrong answer.
RUNNING = "Running the agent. In calibration a run took 14 to 76 seconds."


def started(reply: EventSubmitted | None) -> None:
    if reply:
        ss["agent-run"] = str(reply.run_id)


def body(live: Live) -> None:
    # The placeholder is the simple question's own words, the question `make demo` sends.
    question = st.text_input(
        "Question", key="agent-question", placeholder=demo_questions.DEFAULT_QUESTION
    )
    ask, spine, large, _ = st.columns([0.6, 1.4, 1.2, 3])
    if ask.button("Ask", type="primary", key="agent-ask", disabled=not question.strip()):
        # Labelled with the Section 1 demo that asks these words, or with no demo.
        typed = demo_questions.demo_asking(question, demo_questions.AGENT_ASK_DEMOS)
        started(frame.act(lambda: frame.api().ask(question, typed)))
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
