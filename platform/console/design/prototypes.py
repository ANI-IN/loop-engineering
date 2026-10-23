"""Prototypes of the console's four custom components (components v2, inline HTML/CSS/JS).

Status line with the guarded kill switch, run board, annotated SQL, and holdout ledger. Each one
reads Streamlit's theme CSS variables (--st-*), so config.toml drives both native widgets and
these. Rules in platform/console/DESIGN.md. Every JS module:

- builds its DOM once per mount and updates it in place on later calls (calls are idempotent);
- writes user text with textContent only, never innerHTML;
- formats every time in the browser from a UTC ISO string (the server never formats a time);
- animates only when a value changes, and not at all under prefers-reduced-motion;
- counts its calls, mounts, and cleanups in window.__dpProbe for the remount check.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

import streamlit as st

from datapilot.config import pack_config
from datapilot.contracts.lifecycle import RunStatus

# --- Configuration -------------------------------------------------------------------------------


def console_limits() -> dict[str, int]:
    """pack.yaml console: kill_switch_disarm_seconds, strips_per_lane, poll_seconds."""
    return dict(pack_config()["console"])


# --- View models (pure; the console pages reuse these) ----------------------------------------

LANES = [
    ("queued", "Queued"),
    ("running", "Running"),
    ("verifying", "Verifying"),
    ("holding", "Holding for approval"),
    ("done", "Done"),
]
OFF_BOARD = [
    ("rejected", "Rejected"),
    ("failed", "Failed"),
    ("escalated", "Escalated"),
    ("blocked_budget", "Blocked by budget"),
    ("blocked_killswitch", "Blocked by kill switch"),
]

# status -> (lane, word on the strip, edge shape)
STATUS_VIEW: dict[RunStatus, tuple[str, str, str]] = {
    RunStatus.RECEIVED: ("queued", "Received", "dashed"),
    RunStatus.QUEUED: ("queued", "Queued", "dashed"),
    RunStatus.RUNNING: ("running", "Running", "solid"),
    RunStatus.VERIFYING: ("verifying", "Verifying", "double"),
    RunStatus.AWAITING_APPROVAL: ("holding", "Holding for approval", "hold"),
    RunStatus.ANSWERED: ("done", "Answered", "done"),
    RunStatus.POSTED: ("done", "Posted", "done"),
    RunStatus.REJECTED: ("rejected", "Rejected", "struck"),
    RunStatus.FAILED: ("failed", "Failed", "struck"),
    RunStatus.ESCALATED: ("escalated", "Escalated", "struck"),
    RunStatus.BLOCKED_BUDGET: ("blocked_budget", "Blocked by budget", "struck"),
    RunStatus.BLOCKED_KILLSWITCH: ("blocked_killswitch", "Blocked by kill switch", "struck"),
}

AUTONOMY_WORDS = {
    "report_only": "report-only level",
    "assisted": "assisted level",
    "unattended": "unattended level",
}

# Metric family slugs (pack.yaml autonomy.metric_families) and the words the console shows.
FAMILY_WORDS = {
    "revenue": "revenue",
    "orders": "orders",
    "aov": "average order value",
    "customers": "customers",
    "products": "products",
}


def strip_view(run: Any, stamp: dict[str, str | None]) -> dict[str, Any]:
    """One flight strip. `stamp` is LiveStamp.to_browser(): run_id, started_at_utc, trace_url."""
    lane, word, edge = STATUS_VIEW[RunStatus(run.status)]
    return {
        "kind": "run",
        "run_id": run.run_id,
        "label": f"Run {run.run_id[:8]}",
        "question": run.question,
        "lane": lane,
        "word": word,
        "edge": edge,
        "step": run.step,
        "duplicates": run.duplicates_absorbed,
        "review": RunStatus(run.status) is RunStatus.AWAITING_APPROVAL,
        "stamp": stamp,
    }


def benchmark_strip_view(
    *,
    group_id: str,
    name: str,
    done: int,
    total: int,
    stamp: dict[str, str | None],
    expanded: bool,
) -> dict[str, Any]:
    """A running benchmark is one grouped strip, never one strip per run."""
    finished = done >= total
    return {
        "kind": "benchmark",
        "run_id": group_id,
        "label": name,
        "question": f"{name}: {done} of {total} runs done",
        "lane": "done" if finished else "running",
        "word": "Done" if finished else "Running",
        "edge": "done" if finished else "solid",
        "step": "",
        "done": done,
        "total": total,
        "duplicates": 0,
        "review": False,
        "expanded": expanded,
        "stamp": stamp,
    }


def board_view(
    strips: Iterable[dict[str, Any]],
    *,
    per_lane: int,
    session_open: bool,
    display_tz: str | None,
) -> dict[str, Any]:
    return {
        "lanes": [{"id": i, "title": t} for i, t in LANES],
        "off": [{"id": i, "title": t} for i, t in OFF_BOARD],
        "per_lane": per_lane,
        "session_open": session_open,
        "display_tz": display_tz,
        "strips": list(strips),
    }


def status_line_view(
    *,
    session: dict[str, str] | None,
    business_date: str,
    display_tz: str | None,
    autonomy: str,
    forced: bool,
    families: dict[str, bool],
    tokens_used: int,
    tokens_cap: int,
    planted: list[str],
    pacing_seconds: float | None,
    kill_engaged: bool,
    disarm_seconds: int,
) -> dict[str, Any]:
    """`session` is LiveSession.to_browser() or None; `business_date` is
    datapilot.business_date.status_label()."""
    share = tokens_used / tokens_cap if tokens_cap else 0.0
    if share >= 1:
        gauge = "cap"
    elif share >= 0.8:
        gauge = "near"
    else:
        gauge = "ok"
    return {
        "session": session,
        "business_date": business_date,
        "display_tz": display_tz,
        "autonomy": AUTONOMY_WORDS[autonomy],
        "forced": forced,
        "families": [{"name": FAMILY_WORDS.get(n, n), "cleared": c} for n, c in families.items()],
        "tokens_used": tokens_used,
        "tokens_cap": tokens_cap,
        "share": min(share, 1.0),
        "gauge": gauge,
        "planted": planted,
        "pacing": pacing_seconds,
        "kill": "engaged" if kill_engaged else "off",
        "disarm_seconds": disarm_seconds,
    }


def sql_view(
    lines: list[str],
    notes: list[dict[str, Any]],
    *,
    stamp: dict[str, str | None] | None,
    display_tz: str | None,
) -> dict[str, Any]:
    marks = []
    for number, note in enumerate(notes, start=1):
        for line, fragment in note["marks"]:
            start = lines[line].find(fragment)
            if start < 0:
                raise ValueError(f"fragment {fragment!r} not on line {line}")
            marks.append({"n": number, "line": line, "start": start, "end": start + len(fragment)})
    return {
        "stamp": stamp,
        "display_tz": display_tz,
        "lines": lines,
        "marks": marks,
        "notes": [{"n": i, "trap": n["trap"], "text": n["text"]} for i, n in enumerate(notes, 1)],
    }


def no_baseline_view() -> dict[str, Any]:
    """The ledger when the open live session has no baseline experiment yet (NoLiveBaseline)."""
    return {"state": "no_baseline"}


def collapsed_ledger_view() -> dict[str, Any]:
    """The ledger under a closed grouped benchmark strip: it takes no space."""
    return {"state": "collapsed"}


def _cell(passes: int | None, runs: int, need: int) -> dict[str, Any]:
    if passes is None:
        return {"pending": True}
    return {"passed": passes >= need, "runs": f"{passes} of {runs} runs"}


def ledger_view(
    rows: list[tuple[str, str, int | None, int | None]],
    *,
    baseline_stamp: dict[str, str | None],
    candidate_stamp: dict[str, str | None] | None,
    row_traces: dict[str, str],
    trace_list_url: str | None,
    candidate_version: str | None,
    display_tz: str | None,
    runs: int,
    pass_threshold: int,
) -> dict[str, Any]:
    """The live holdout ledger of the open session. Rows are (item id, question, baseline passes,
    candidate passes); None means not run yet. Without a candidate it shows the baseline alone."""
    out, fixed, regressions = [], 0, 0
    active_pass = candidate_pass = finished = 0
    for item, question, active, candidate in rows:
        a, c = _cell(active, runs, pass_threshold), _cell(candidate, runs, pass_threshold)
        change = ""
        if active is not None:
            finished += 1
            active_pass += a["passed"]
        if candidate is not None:
            candidate_pass += c["passed"]
        if active is not None and candidate is not None:
            if c["passed"] and not a["passed"]:
                change, fixed = "fixed", fixed + 1
            elif a["passed"] and not c["passed"]:
                change, regressions = "regression", regressions + 1
            else:
                change = "same"
        out.append(
            {
                "item": item,
                "question": question,
                "change": change,
                "active": a,
                "candidate": c if candidate_version else None,
                "trace_url": row_traces.get(item),
            }
        )
    rule = f"Each item runs {runs} times and passes on {pass_threshold} of {runs}."
    total = len(rows)
    if candidate_version:
        noun = "regression" if regressions == 1 else "regressions"
        summary = (
            f"{rule} v1 passes {active_pass} of {total}; {candidate_version} passes "
            f"{candidate_pass} of {total}: {fixed} fixed, {regressions} {noun}."
        )
    else:
        summary = (
            f"{rule} v1 passes {active_pass} of {finished} finished items; "
            f"{total - finished} not run yet."
        )
    return {
        "state": "live",
        "active_label": "v1, active",
        "candidate_label": f"{candidate_version}, candidate" if candidate_version else None,
        "candidate_version": candidate_version,
        "baseline_stamp": baseline_stamp,
        "candidate_stamp": candidate_stamp,
        "trace_list_url": trace_list_url,
        "display_tz": display_tz,
        "rows": out,
        "summary_text": summary,
    }


# --- Registration --------------------------------------------------------------------------------
# Each component's HTML, CSS, and JS live in design/components/<name>.{html,css,js}. They are read
# here and passed inline to components v2: no bundler, no build step. base.css and base.js hold
# the shared tokens, shapes, and helpers, and are prepended to every component.

_ASSETS = Path(__file__).resolve().parent / "components"


def _asset(name: str) -> str:
    return (_ASSETS / name).read_text(encoding="utf-8")


def _register(name: str) -> Any:
    return st.components.v2.component(
        f"datapilot_{name}",
        html=_asset(f"{name}.html"),
        css=_asset("base.css") + _asset(f"{name}.css"),
        js=_asset("base.js") + _asset(f"{name}.js"),
    )


_status_line = _register("status_line")
_run_board = _register("run_board")
_annotated_sql = _register("annotated_sql")
_holdout_ledger = _register("holdout_ledger")


def status_line(
    data: dict[str, Any],
    *,
    on_stop_all: Callable[[], None],
    on_release: Callable[[], None],
    key: str = "status-line",
) -> Any:
    return _status_line(
        key=key, data=data, on_stop_all_change=on_stop_all, on_release_change=on_release
    )


def run_board(
    data: dict[str, Any],
    *,
    on_review: Callable[[], None],
    on_toggle_ledger: Callable[[], None],
    key: str = "run-board",
) -> Any:
    return _run_board(
        key=key, data=data, on_review_change=on_review, on_toggle_ledger_change=on_toggle_ledger
    )


def annotated_sql(data: dict[str, Any], *, key: str = "annotated-sql") -> Any:
    return _annotated_sql(key=key, data=data)


def holdout_ledger(
    data: dict[str, Any],
    *,
    on_start_baseline: Callable[[], None],
    key: str = "holdout-ledger",
) -> Any:
    return _holdout_ledger(key=key, data=data, on_start_baseline_change=on_start_baseline)
