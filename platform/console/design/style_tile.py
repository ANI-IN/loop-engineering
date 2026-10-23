"""DataPilot console style tile: the real theme, native widgets, and the four custom components.

Specimen data only: no database, no api, no model. A fragment that reruns every
console.poll_seconds appends a stub run event and moves a strip across the run board. The first
screen is the Events view (status line and run board) so its fit at 1280x720 can be checked.
Rules: platform/console/DESIGN.md. Run it with `make style-tile` (platform/console/design_app.py).
Set DATAPILOT_STYLE_TILE_PROBE=<file> to write script and fragment run counts for the pin check.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import timedelta
from pathlib import Path

import streamlit as st

_CONSOLE = Path(__file__).resolve().parents[1]
if str(_CONSOLE) not in sys.path:
    sys.path.insert(0, str(_CONSOLE))

from datapilot import business_date  # noqa: E402
from datapilot.config import pack_config  # noqa: E402
from datapilot.settings import get_settings  # noqa: E402
from design import prototypes, specimen  # noqa: E402

st.set_page_config(
    page_title="DataPilot style tile", layout="wide", initial_sidebar_state="collapsed"
)

LIMITS = prototypes.console_limits()
EVALUATION = pack_config()["evaluation"]
DISPLAY_TZ = get_settings().datapilot_display_timezone or None
PLANTED = ["Naive guard", "Kill switch checked at claim only"]
FAMILIES = {"revenue": True, "orders": False, "aov": False, "customers": False, "products": False}
TOKENS_CAP = 100_000
SESSION_OPEN = "Live session open"

ss = st.session_state
if "board" not in ss:
    ss.board = specimen.seed_board()
    ss.session = specimen.new_session()
    ss.benchmark_done = specimen.BENCHMARK_START
    ss.benchmark_open = False
    ss.tick = 0
    ss.kill = False
    ss.review = None
    ss.open_review = False
    ss.full_runs = 0
    ss.fragment_runs = 0
ss.full_runs += 1


def write_probe() -> None:
    target = os.environ.get("DATAPILOT_STYLE_TILE_PROBE")
    if target:
        counts = {"full_runs": ss.full_runs, "fragment_runs": ss.fragment_runs, "tick": ss.tick}
        Path(target).write_text(json.dumps(counts))


def on_stop_all() -> None:
    ss.kill = True


def on_release() -> None:
    ss.kill = False


def on_review() -> None:
    value = ss.get("run-board")
    run = value.get("review") if value else None
    if run:
        ss.review = run
        ss.open_review = True


def on_toggle_ledger() -> None:
    ss.benchmark_open = not ss.benchmark_open


def clear_review() -> None:
    ss.review = None


def on_start_baseline() -> None:
    """The console would start the baseline experiment here; the specimen does nothing."""


def stamp_of(name: str, minutes_ago: int = 0) -> dict[str, str | None]:
    """A specimen run's live stamp, as the components receive it (UTC ISO and trace link)."""
    stamps = ss.setdefault("stamps", {})
    if name not in stamps:
        run = specimen.SpecimenRun(specimen.run_id(name), "", "")
        run.started_at -= timedelta(minutes=minutes_ago)
        stamps[name] = run.stamp(ss.session)
    return stamps[name]


@st.dialog("Approve this export?", width="large", on_dismiss=clear_review)
def approval_dialog(run_id: str) -> None:
    run = ss.board.runs[run_id]
    approval = run.approval
    if approval is None:
        st.write("This run is no longer holding for approval. Close this dialog.")
        return
    st.write(
        f"Approving runs the SQL below once and exports {approval['row_estimate']:,} rows to "
        "the marketing list. The rows include personal data: email and first name."
    )
    st.code(approval["sql"], language="sql")
    st.write(f"Run {run_id[:8]}: {run.question}.")
    approve, reject = st.columns(2)
    if approve.button("Approve and run", type="primary", width="stretch"):
        specimen.decide(ss.board, run_id, "approve")
        ss.review = None
        st.rerun()
    if reject.button("Reject", width="stretch"):
        specimen.decide(ss.board, run_id, "reject")
        ss.review = None
        st.rerun()


if ss.review:
    approval_dialog(ss.review)


@st.fragment(run_every=LIMITS["poll_seconds"])
def live() -> None:
    """The Events view: the status line and the run board, as the Events page shows them."""
    ss.fragment_runs += 1
    if ss.open_review:
        ss.open_review = False
        st.rerun()
    specimen.next_event(ss.board, ss.tick, kill_engaged=ss.kill)
    ss.tick += 1
    if not ss.kill and ss.tick % 3 == 0 and ss.benchmark_done < specimen.BENCHMARK_TOTAL:
        ss.benchmark_done += 1
    board = ss.board
    session_open = ss.get("session-state", SESSION_OPEN) == SESSION_OPEN
    prototypes.status_line(
        prototypes.status_line_view(
            session=ss.session.to_browser() if session_open else None,
            business_date=business_date.status_label(),
            display_tz=DISPLAY_TZ,
            autonomy="report_only" if ss.kill else "assisted",
            forced=ss.kill,
            families=FAMILIES,
            tokens_used=board.tokens_today,
            tokens_cap=TOKENS_CAP,
            planted=PLANTED,
            pacing_seconds=2,
            kill_engaged=ss.kill,
            disarm_seconds=LIMITS["kill_switch_disarm_seconds"],
        ),
        on_stop_all=on_stop_all,
        on_release=on_release,
    )
    benchmark = prototypes.benchmark_strip_view(
        group_id=specimen.run_id("baseline-benchmark"),
        name="Baseline benchmark",
        done=ss.benchmark_done,
        total=specimen.BENCHMARK_TOTAL,
        stamp=stamp_of("baseline-benchmark", 9),
        expanded=ss.benchmark_open,
    )
    strips = [benchmark] + [
        prototypes.strip_view(board.runs[r], board.runs[r].stamp(ss.session)) for r in board.order
    ]
    prototypes.run_board(
        prototypes.board_view(
            strips if session_open else [],
            per_lane=LIMITS["strips_per_lane"],
            session_open=session_open,
            display_tz=DISPLAY_TZ,
        ),
        on_review=on_review,
        on_toggle_ledger=on_toggle_ledger,
    )
    # The grouped benchmark strip expands into the live holdout ledger, filling as runs finish.
    if ss.benchmark_open and session_open:
        rows = specimen.benchmark_rows(ss.benchmark_done)
        ledger = prototypes.ledger_view(
            rows,
            baseline_stamp=stamp_of("baseline-benchmark", 9),
            candidate_stamp=None,
            row_traces={
                item: stamp_of(f"baseline-{item}")["trace_url"]
                for item, _, passes, _ in rows
                if passes is not None
            },
            trace_list_url=specimen.trace_list_url("v1"),
            candidate_version=None,
            display_tz=DISPLAY_TZ,
            runs=EVALUATION["holdout_repeats"],
            pass_threshold=EVALUATION["holdout_pass_threshold"],
        )
    else:
        ledger = prototypes.collapsed_ledger_view()
    prototypes.holdout_ledger(ledger, on_start_baseline=on_start_baseline, key="benchmark-ledger")
    write_probe()


live()

st.title("Console style tile")
st.write(
    "The flight-deck direction with specimen data: no database, api, or model. The first screen "
    "is the Events view: the status line and the run board, updating every second."
)
st.segmented_control(
    "Specimen state", [SESSION_OPEN, "No live session"], default=SESSION_OPEN, key="session-state"
)

st.header("Tokens")
SWATCHES = [
    ("chart-paper", "#EDF1F3", "App background"),
    ("strip-white", "#FBFCFC", "Strips, panels, inputs"),
    ("ink", "#17283A", "Text, rules, strip borders"),
    ("graphite", "#5B6B79", "Secondary text"),
    ("rule", "#7D8B97", "Widget borders"),
    ("airspace-magenta", "#9E2F6E", "The only accent: focus, selection, primary"),
    ("cleared-green", "#2E7A57", "Passed, cleared, posted"),
    ("holding-amber", "#B7791F", "Holding: fill only, never text"),
    ("holding-amber-text", "#8A5A12", "Amber words"),
    ("fault-red", "#B13A30", "Failed, blocked, regression"),
]
cells = "".join(
    f'<div style="display:flex;flex-direction:column;border:2px solid #17283A;min-width:0">'
    f'<div style="background:{hex_};height:40px"></div>'
    f'<div style="background:#FBFCFC;padding:6px 8px;border-top:2px solid #17283A">'
    f'<div style="font-weight:700">{name}</div><div>{hex_}</div>'
    f'<div style="color:#5B6B79">{role}</div></div></div>'
    for name, hex_, role in SWATCHES
)
st.html(
    f'<div style="display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px">{cells}</div>'
)

st.header("Type and native widgets")
left, right = st.columns(2, gap="large")
with left:
    st.subheader("Section label, 20 px bold")
    st.write(
        "Body text is Atkinson Hyperlegible Next at 18 px. Numbers use tabular figures: "
        "41,230,118.07."
    )
    st.caption("Caption and secondary text, graphite.")
    st.text_input("Question", value="What was our net revenue in fiscal year 2025?")
    run, large = st.columns([1, 2])
    run.button("Ask", type="primary")
    large.button("Run large query")
    st.error(
        "The api did not answer within 2 seconds. Start it with make up, then reload this page."
    )
with right:
    st.subheader("Checklist, attempt 2 of 3")
    st.markdown(
        ":green[:material/check_box: **Passed**] Parse: one statement  \n"
        ":green[:material/check_box: **Passed**] Statement policy  \n"
        ":green[:material/check_box: **Passed**] Schema existence  \n"
        ":red[:material/disabled_by_default: **Failed**] Cost under the threshold: "
        "estimated 1.2 million rows  \n"
        ":gray[:material/check_box_outline_blank: **Not run**] Personal data routing  \n"
        ":gray[:material/check_box_outline_blank: **Not run**] Final answer"
    )
    st.subheader("Answer against gold")
    st.markdown(
        "Agent answer: **\\$41,230,118.07**  \n"
        "Gold answer: **\\$36,904,551.20**  \n"
        ":red[:material/disabled_by_default: **Mismatch**] by \\$4,325,566.87"
    )

st.header("Annotated SQL")
prototypes.annotated_sql(
    prototypes.sql_view(
        specimen.WRONG_SQL,
        specimen.WRONG_SQL_NOTES,
        stamp=stamp_of("spine-question"),
        display_tz=DISPLAY_TZ,
    )
)

st.header("Holdout ledger")
ledger_state = st.segmented_control(
    "Specimen state",
    ["Baseline and candidate in this session", "No baseline in this session"],
    default="Baseline and candidate in this session",
    key="ledger-state",
)
if ledger_state == "No baseline in this session":
    ledger = prototypes.no_baseline_view()
else:
    rows = specimen.ledger_rows()
    ledger = prototypes.ledger_view(
        rows,
        baseline_stamp=stamp_of("baseline-experiment", 9),
        candidate_stamp=stamp_of("candidate-experiment", 2),
        row_traces={row[0]: stamp_of(f"candidate-{row[0]}")["trace_url"] for row in rows},
        trace_list_url=specimen.trace_list_url("v2"),
        candidate_version="v2",
        display_tz=DISPLAY_TZ,
        runs=EVALUATION["holdout_repeats"],
        pass_threshold=EVALUATION["holdout_pass_threshold"],
    )
prototypes.holdout_ledger(ledger, on_start_baseline=on_start_baseline)
if ledger["state"] == "live":
    # The gate's three states, in the Improve page's words (datapilot_console.widgets.GATE).
    st.markdown(
        ":red[:material/disabled_by_default: **Gate: blocked.**] v2 fixes 4 holdout items but "
        "breaks 1 that v1 passed (orders on Black Friday 2025), so it is not promoted.  \n"
        ":orange[:material/hourglass_top: **Gate: ready for human approval.**] v2 passes 9 of 15 "
        "holdout items against 6, with no regressions.  \n"
        ":green[:material/check_box: **Gate: passed.**] Promoted: v2 passes 9 of 15 holdout "
        "items against 6, with no regressions, approved by ani."
    )
write_probe()
