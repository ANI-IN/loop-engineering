"""Events page (Section 3: Event loop): the run board, approvals, the demo controls, the channel.

The first screen is the status line and the board: five lanes and the off-the-board row, with no
heading between them. Benchmarks show as one grouped strip each, which opens the holdout ledger.
"""

from __future__ import annotations

import streamlit as st
from datapilot_console import components, events_view, frame, ops_reads
from datapilot_console.api_client import webhook_demo, webhook_hold
from datapilot_console.frame import Live

from datapilot import business_date, demo_questions

ss = st.session_state
ss.setdefault("open-ledger", None)
ss.setdefault("review", None)
ss.setdefault("open-review", False)
ss.setdefault("restart-holding", None)
frame.check_api()


def on_review() -> None:
    value = ss.get("run-board")
    run_id = value.get("review") if value else None
    if run_id:
        ss["review"] = run_id
        ss["open-review"] = True


def on_toggle_ledger() -> None:
    value = ss.get("run-board")
    group = value.get("toggle_ledger") if value else None
    ss["open-ledger"] = None if ss["open-ledger"] == group else group


def close_review() -> None:
    ss["review"] = None


@st.dialog("Approve this export?", width="large", on_dismiss=close_review)
def approval_dialog(run_id: str) -> None:
    with frame.db_pool().connection() as conn:
        session = ops_reads.open_session(conn)
        approval = ops_reads.open_approval(conn, session["session_id"], run_id) if session else None
    if approval is None:
        st.write("This run is no longer holding for approval. Close this dialog.")
        return
    rows = approval["row_estimate"]
    count = f"about {rows:,} rows" if rows is not None else "the rows below"
    st.write(f"Approving runs the SQL below once and returns {count}. {approval['action']}")
    st.write(f"Why it holds: {approval['reason']}")
    if approval["sql"]:
        st.code(approval["sql"], language="sql")
    st.write(f"Run {run_id[:8]}: {approval['question']}")
    approve, reject = st.columns(2)
    if approve.button("Approve and run", type="primary", width="stretch"):
        frame.act(lambda: frame.api().decide(run_id, "approve"))
        ss["review"] = None
        st.rerun()
    if reject.button("Reject", width="stretch"):
        frame.act(lambda: frame.api().decide(run_id, "reject"))
        ss["review"] = None
        st.rerun()


if ss["review"]:
    approval_dialog(ss["review"])


def body(live: Live) -> None:
    if ss["open-review"]:
        ss["open-review"] = False
        st.rerun()  # the dialog opens on a full run, outside this fragment
    board = live.view(
        "events-board",
        lambda: events_view.board(live, open_ledger=ss["open-ledger"]),
        ss["open-ledger"],
    )
    components.run_board(board, on_review=on_review, on_toggle_ledger=on_toggle_ledger)
    ledger = live.view(
        "events-ledger", lambda: events_view.ledger_for(live, ss["open-ledger"]), ss["open-ledger"]
    )
    components.holdout_ledger(ledger, on_start_baseline=lambda: None, key="benchmark-ledger")

    # Each button sends its demo's own question, the one `make demo NAME=` sends.
    # Read on every refresh, never cached on the watermark: the end of the clearance re-runs (an
    # advisory lock released) may change nothing the watermark reads when no family clears.
    state = ops_reads.finale_state(live.conn)
    webhook = live.view(
        "events-webhook-demo",
        lambda: webhook_demo(ops_reads.family_levels(live.conn), state),
        state,
    )
    # Held while a promotion is pending, and for the finale until its starting state is right.
    hold = live.view("events-webhook-hold", lambda: webhook_hold(webhook, state), webhook, state)
    st.caption(f"Send webhook question asks: {demo_questions.question_for(webhook)}")
    if hold:
        st.caption(f"Not sent yet. {hold}")
    send, three, export, digest, restart = st.columns([1.3, 1.6, 1.4, 1.1, 1])
    if send.button("Send webhook question", type="primary", key="events-send", disabled=bool(hold)):
        frame.act(lambda: frame.api().ask_demo(webhook))
    if three.button("Send the same event three times", key="events-three"):
        duplicated = demo_questions.question_for("events-duplicate-events")
        frame.act(lambda: frame.api().send_three_times(duplicated))
    if export.button("Request California export", key="events-export"):
        frame.act(lambda: frame.api().request_export())
    if digest.button("Run digest now", key="events-digest", disabled=live.session is None):
        day = business_date.yesterday().isoformat()
        frame.act(lambda: frame.api().run_digest(day, str(live.session_id)))
    if restart.button("Restart worker", key="events-restart"):
        board_now = events_view.board(live, open_ledger=None)
        holding = [s["run_id"] for s in board_now["strips"] if s["lane"] == "holding"]
        if frame.act(lambda: frame.api().restart_worker()) is not None:
            ss["restart-holding"] = holding
    frame.show_action_error()
    if ss["restart-holding"] is not None and live.session is not None:
        st.write(events_view.restart_outcome(live, ss["restart-holding"]))

    st.subheader("Channel")
    posts = live.view("events-channel", lambda: events_view.channel(live))
    if not posts:
        st.write("No posts in this session yet. Answers appear here once they are posted.")
    for post in posts:
        with st.container(border=True):
            st.markdown(f"**{post['heading']}**")
            st.text(post["text"])


frame.live_page("events", body)
