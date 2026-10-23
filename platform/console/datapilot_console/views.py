"""View models: what each page and component receives, built from ops rows. Pure functions.

Times leave here only as UTC ISO strings (LiveStamp.to_browser(), LiveSession.to_browser()); the
components format them in the browser. Limits arrive as arguments from pack.yaml `console:`.
"""

from __future__ import annotations

import difflib
from collections.abc import Iterable, Mapping
from datetime import datetime
from typing import Any

from datapilot.contracts.lifecycle import TERMINAL, RunStatus
from datapilot.contracts.live import LiveSession, LiveStamp, SessionPurpose
from datapilot.observability.sampling import experiment_sample_rate, sample_note
from datapilot_console import sql_marks

Row = Mapping[str, Any]

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

# The verification loop's graders, in the order they run, with their checklist labels.
GRADERS = [
    ("parse", "Parse: one statement"),
    ("statement_policy", "Statement policy"),
    ("schema", "Schema allowlist"),
    ("cost", "Cost under the threshold"),
    ("execution", "Runs on the read-only role"),
    ("personal_data", "Personal data routing"),
    ("final_answer", "Final answer"),
]
GRADER_WORDS = dict(GRADERS) | {"injected_failure": "Injected failing grader", "gold": "Gold check"}
GOLD_GRADER = "gold"
DEFENSE_PREFIX = "defense:"

STEP_FOR_STATUS = {
    RunStatus.RECEIVED: "Event received",
    RunStatus.QUEUED: "Waiting for a worker",
    RunStatus.RUNNING: "Claimed by a worker",
    RunStatus.VERIFYING: "Graders running",
    RunStatus.ANSWERED: "Answered",
    RunStatus.REJECTED: "Rejected at approval",
    RunStatus.FAILED: "The run failed",
    RunStatus.ESCALATED: "Escalated to a human",
    RunStatus.BLOCKED_BUDGET: "The daily token cap was reached",
    RunStatus.BLOCKED_KILLSWITCH: "Stopped by the kill switch",
}


# --- Stamps and the session ------------------------------------------------------------------


def session_model(row: Row | None) -> LiveSession | None:
    if row is None:
        return None
    return LiveSession(
        session_id=row["session_id"],
        purpose=SessionPurpose(row.get("purpose", "development")),
        started_at=row["started_at"],
        started_by=row["started_by"],
        timezone=row["timezone"],
    )


def stamp(
    item_id: Any, session_id: Any, started_at: datetime, trace_url: str | None
) -> dict[str, str | None]:
    """The live stamp a component shows ("Started 11:59:09. Open trace"), formatted in the
    browser."""
    return LiveStamp(
        run_id=item_id, session_id=session_id, started_at=started_at, trace_url=trace_url
    ).to_browser()


def run_stamp(run: Row, session_id: Any) -> dict[str, str | None]:
    return stamp(
        run["run_id"], session_id, run.get("started_at") or run["created_at"], run["langsmith_url"]
    )


# --- The status line -------------------------------------------------------------------------


def status_line_view(
    *,
    session: LiveSession | None,
    business_date: str,
    display_tz: str | None,
    state: Row,
    families: list[str],
    tokens_cap_default: int,
    planted_chips: Mapping[str, str],
    pacing_seconds: float | None,
    disarm_seconds: int,
    notice: str | None,
) -> dict[str, Any]:
    """`state` is ops_reads.status(); `planted_chips` maps a planted id to its registry chip."""
    cap = state["token_limit"] or tokens_cap_default
    used = state["tokens_used"]
    share = used / cap if cap else 0.0
    gauge = "cap" if share >= 1 else "near" if share >= 0.8 else "ok"
    active = state["planted_active"]
    pacing = "DEMO_PACING" in active
    levels = state["family_levels"]
    return {
        "session": session.to_browser() if session else None,
        "business_date": business_date,
        "display_tz": display_tz,
        "autonomy": AUTONOMY_WORDS[state["autonomy_level"]],
        "forced": state["kill_switch"] == "engaged",
        "families": [
            {"name": FAMILY_WORDS.get(f, f), "cleared": levels.get(f) == "unattended"}
            for f in families
        ],
        "tokens_used": used,
        "tokens_cap": cap,
        "share": min(share, 1.0),
        "gauge": gauge,
        "planted": [planted_chips.get(i, i) for i in active if i != "DEMO_PACING"],
        "pacing": pacing_seconds if pacing else None,
        "kill": "engaged" if state["kill_switch"] == "engaged" else "off",
        "disarm_seconds": disarm_seconds,
        "notice": notice or safeguard_notice(state.get("safeguard")),
    }


def safeguard_notice(safeguard: Mapping[str, Any] | None) -> str:
    """The status line's honest note while the class-day safeguard's version is active: which
    version runs the finale, where its clearance came from, and which version it replaced."""
    if not safeguard:
        return ""
    return (
        f"Class-day safeguard: {safeguard['candidate_version']} is active, the version verified "
        f"in rehearsal; its families keep the level they earned there. It replaced "
        f"{safeguard['active_version']}, which the gate promoted in class."
    )


# --- The run board ---------------------------------------------------------------------------


def step_of(run: Row) -> tuple[str, str, str]:
    """The strip's one-line step from the run's newest event: (text, tool name, text after); the
    component sets the tool name in mono."""
    status = RunStatus(run["status"])
    if status is RunStatus.POSTED:
        level = AUTONOMY_WORDS.get(run.get("autonomy_level_applied") or "", "")
        return (f"Posted at the {level}" if level else "Posted to the channel"), "", ""
    event = run.get("last_event")
    if not event:
        return STEP_FOR_STATUS.get(status, ""), "", ""
    kind, payload = event["kind"], event["payload"] or {}
    if kind == "tool_call_started":
        return "Calling ", str(payload.get("tool", "")), ""
    if kind == "tool_call_finished":
        seconds = (payload.get("ms") or 0) / 1000
        return "", str(payload.get("tool", "")), f" finished in {seconds:.1f} s"
    if kind == "grader_result":
        grader = str(payload.get("grader", ""))
        word = GRADER_WORDS.get(grader, grader.replace("_", " "))
        if grader.startswith(DEFENSE_PREFIX):
            word = "Defense check"
        if payload.get("passed"):
            return f"Passed: {word}", "", ""
        return f"Failed: {word}. {payload.get('reason', '')}".strip(), "", ""
    if kind == "reviewer_verdict":
        return f"Reviewer: {payload.get('outcome', 'no verdict')}", "", ""
    if kind == "approval_requested":
        return str(payload.get("reason") or "Needs human approval"), "", ""
    if kind == "approval_decided":
        decided = "Approved" if payload.get("decision") == "approve" else "Rejected"
        return f"{decided} by {payload.get('by', 'a human')}", "", ""
    if kind == "killswitch_blocked":
        return f"Stopped by the kill switch {payload.get('at', '')}".strip(), "", ""
    if kind == "budget_blocked":
        return f"The daily token cap was reached {payload.get('at', '')}".strip(), "", ""
    reasons = payload.get("reasons")
    reason = (
        payload.get("reason") or payload.get("error") or ("; ".join(reasons) if reasons else "")
    )
    return (str(reason) if reason else STEP_FOR_STATUS.get(status, "")), "", ""


def strip_view(run: Row, session_id: Any, duplicates: int = 0) -> dict[str, Any]:
    status = RunStatus(run["status"])
    lane, word, edge = STATUS_VIEW[status]
    step, tool, after = step_of(run)
    return {
        "kind": "run",
        "run_id": str(run["run_id"]),
        "label": f"Run {str(run['run_id'])[:8]}",
        "question": run.get("question") or "",
        "lane": lane,
        "word": word,
        "edge": edge,
        "step": step,
        "step_code": tool,
        "step_after": after,
        "duplicates": duplicates,
        "review": status is RunStatus.AWAITING_APPROVAL,
        "stamp": run_stamp(run, session_id),
    }


def benchmark_name(experiment: Row, promotion: Mapping[str, Any] | None = None) -> str:
    """ "Baseline benchmark" or "Candidate benchmark"; after a promotion (promotion_view) the
    promoted version's is "v2 benchmark, active" and the replaced one's "v1 benchmark, replaced",
    the same words as the Improve page's ledger."""
    version = str(experiment["knowledge_version"])
    if promotion is not None and version == promotion["version"]:
        return f"{version} benchmark, active"
    if promotion is not None and version == promotion["replaced"]:
        return f"{version} benchmark, replaced"
    kind = "Baseline" if experiment["version_status"] == "active" else "Candidate"
    return f"{kind} benchmark"


def planned_runs(split: str, dev_items: int, holdout_items: int, repeats: int) -> int:
    """How many runs an experiment makes: dev items once, holdout items `repeats` times."""
    return {"dev": dev_items, "holdout": holdout_items * repeats}.get(
        split, dev_items + holdout_items * repeats
    )


def runs_done(experiment: Row) -> int:
    return sum(len(e.get("run_passes") or []) or 1 for e in experiment["per_example"] or [])


def benchmark_strip_view(
    experiment: Row,
    session_id: Any,
    *,
    total: int,
    expanded: bool,
    promotion: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """A running benchmark is one grouped strip, never one strip per run."""
    finished = experiment["finished_at"] is not None
    done = total if finished else min(runs_done(experiment), total)
    name = benchmark_name(experiment, promotion)
    return {
        "kind": "benchmark",
        "run_id": str(experiment["experiment_id"]),
        "label": name,
        "question": f"{name}: {done} of {total} runs done",
        "lane": "done" if finished else "running",
        "word": "Done" if finished else "Running",
        "edge": "done" if finished else "solid",
        "step": "",
        "step_code": "",
        "step_after": "",
        "done": done,
        "total": total,
        "duplicates": 0,
        "review": False,
        "expanded": expanded,
        "stamp": stamp(
            experiment["experiment_id"],
            session_id,
            experiment["started_at"],
            experiment["langsmith_url"],
        ),
    }


def board_view(
    strips: Iterable[dict[str, Any]], *, per_lane: int, session_open: bool, display_tz: str | None
) -> dict[str, Any]:
    return {
        "lanes": [{"id": i, "title": t} for i, t in LANES],
        "off": [{"id": i, "title": t} for i, t in OFF_BOARD],
        "per_lane": per_lane,
        "session_open": session_open,
        "display_tz": display_tz,
        "strips": list(strips),
    }


# --- Annotated SQL ---------------------------------------------------------------------------


def sql_view(
    sql: str | None,
    labels: list[str],
    *,
    stamp: dict[str, str | None] | None,
    display_tz: str | None,
) -> dict[str, Any]:
    """The annotated SQL; with no SQL yet it shows only the live stamp ("waiting")."""
    lines = sql.strip("\n").splitlines() if sql else []
    notes = sql_marks.annotate(lines, labels) if lines else []
    marks = [
        {"n": n, "line": line, "start": start, "end": end}
        for n, note in enumerate(notes, start=1)
        for line, start, end in note.marks
    ]
    return {
        "state": "sql" if lines else "waiting",
        "stamp": stamp,
        "display_tz": display_tz,
        "lines": lines,
        "marks": marks,
        "notes": [
            {"n": n, "trap": note.trap, "text": note.text} for n, note in enumerate(notes, 1)
        ],
    }


# --- Agent and Verify results ----------------------------------------------------------------


def tool_calls(events: list[Row]) -> list[dict[str, Any]]:
    """One bar per finished tool call, in order, with its duration in seconds."""
    calls = []
    for event in events:
        if event["kind"] == "tool_call_finished":
            payload = event["payload"] or {}
            seconds = round((payload.get("ms") or 0) / 1000, 2)
            tool = str(payload.get("tool", ""))
            calls.append(
                {
                    "order": len(calls) + 1,
                    "tool": tool,
                    "seconds": seconds,
                    "label": f"{tool} {seconds:.1f} s",
                }
            )
    return calls


def grader_events(events: list[Row]) -> list[dict[str, Any]]:
    return [e["payload"] or {} for e in events if e["kind"] == "grader_result"]


def checklist(events: list[Row], max_attempts: int) -> dict[str, Any]:
    """The grader checklist of the newest attempt: each grader Passed, Failed, or Not run."""
    results = [
        g
        for g in grader_events(events)
        if not str(g.get("grader", "")).startswith(DEFENSE_PREFIX)
        and g.get("grader") != GOLD_GRADER
    ]
    attempt = max((int(g.get("attempt") or 1) for g in results), default=1)
    latest = {str(g["grader"]): g for g in results if int(g.get("attempt") or 1) == attempt}
    names = [n for n, _ in GRADERS] + [
        n for n in latest if n not in GRADER_WORDS or n == "injected_failure"
    ]
    rows = []
    for name in dict.fromkeys(names):
        found = latest.get(name)
        state = "not_run" if found is None else "passed" if found.get("passed") else "failed"
        rows.append(
            {
                "grader": name,
                "label": GRADER_WORDS.get(name, name.replace("_", " ")),
                "state": state,
                "reason": ""
                if found is None or found.get("passed")
                else str(found.get("reason", "")),
            }
        )
    return {"attempt": attempt, "max_attempts": max_attempts, "rows": rows, "any": bool(results)}


def defense_layers(events: list[Row]) -> list[dict[str, Any]]:
    """For each statement a defense check ran: its SQL and what each layer did with it."""
    statements = []
    for g in grader_events(events):
        if not str(g.get("grader", "")).startswith(DEFENSE_PREFIX):
            continue
        layers = []
        stopped = False
        for layer in g.get("layers") or []:
            if stopped:
                word = "Not reached"
            elif layer.get("stopped"):
                word, stopped = "Stopped it", True
            else:
                word = "Passed through"
            layers.append(
                {
                    "layer": str(layer.get("layer", "")),
                    "word": word,
                    "detail": str(layer.get("detail", "")),
                }
            )
        statements.append({"sql": str(g.get("sql", "")), "layers": layers, "stopped": stopped})
    return statements


def gold_check(events: list[Row]) -> dict[str, Any] | None:
    """The run's answer against gold, when the run was checked against a gold query."""
    found = [g for g in grader_events(events) if g.get("grader") == GOLD_GRADER]
    if not found:
        return None
    g = found[-1]
    return {
        "passed": bool(g.get("passed")),
        "agent_value": g.get("agent_value"),
        "gold_value": g.get("gold_value"),
        "reason": str(g.get("reason", "")),
        "trap_labels": list(g.get("trap_labels") or []),
    }


def reviewer_verdict(events: list[Row]) -> dict[str, Any] | None:
    found = [e["payload"] or {} for e in events if e["kind"] == "reviewer_verdict"]
    if not found:
        return None
    return {
        "outcome": str(found[-1].get("outcome", "")),
        "reasons": list(found[-1].get("reasons") or []),
    }


def run_summary(run: Row) -> str:
    """Tokens, cost, and latency as one line of text."""
    tokens = int(run["tokens_in"] or 0) + int(run["tokens_out"] or 0)
    # Four decimals: a run can cost a few hundredths of a cent, which three decimals show as $0.000.
    parts = [f"{tokens:,} tokens", f"${float(run['cost_usd'] or 0):.4f}"]
    if run.get("started_at") and run.get("finished_at"):
        parts.append(f"{(run['finished_at'] - run['started_at']).total_seconds():.1f} s")
    return ", ".join(parts)


HOLDING_LINE = (
    "Waiting for a person's approval. Select Review on its strip on the Events page to approve or "
    "reject it."
)
QUEUED_LINE = "Queued: waiting for a worker to start it."


def waiting_line(status: RunStatus, running_note: str) -> str | None:
    """The line under a run's status: the page's waiting note only while the run works, what it
    waits for while it is queued or holding, and nothing once it is finished."""
    if status in {RunStatus.RUNNING, RunStatus.VERIFYING}:
        return running_note
    if status is RunStatus.AWAITING_APPROVAL:
        return HOLDING_LINE
    if status in {RunStatus.RECEIVED, RunStatus.QUEUED}:
        return QUEUED_LINE
    return None


def is_finished(run: Row) -> bool:
    return RunStatus(run["status"]) in TERMINAL or RunStatus(run["status"]) is RunStatus.ANSWERED


# --- The holdout ledger ----------------------------------------------------------------------


def no_baseline_view() -> dict[str, Any]:
    """The ledger when the open live session has no baseline experiment yet (NoLiveBaseline)."""
    return {"state": "no_baseline"}


def collapsed_ledger_view() -> dict[str, Any]:
    """The ledger under a closed grouped benchmark strip: it takes no space."""
    return {"state": "collapsed"}


def holdout_cells(experiment: Row | None) -> dict[str, dict[str, Any]]:
    """item id -> {passes, runs, trace_url} for the experiment's finished holdout items."""
    if experiment is None:
        return {}
    cells = {}
    for e in experiment["per_example"] or []:
        if e.get("split") != "holdout":
            continue
        run_passes = list(e.get("run_passes") or [e.get("passed", False)])
        traces = e.get("trace_urls") or ([e["trace_url"]] if e.get("trace_url") else [])
        cells[str(e["item_id"])] = {
            "passes": sum(bool(p) for p in run_passes),
            "runs": len(run_passes),
            "trace_url": traces[0] if traces else None,
            # the trace sample left every run of the item out: the ledger says so in words
            "not_traced": not traces and bool(e.get("runs_not_traced")),
            "confirmation": e.get("confirmation"),
        }
    return cells


def confirm_regression(confirmation: Mapping[str, Any] | None) -> tuple[str, str]:
    """An apparent regression is confirmed with more runs before it counts (the evaluator
    records each step on the item): (change, the words the ledger shows)."""
    if not confirmation:
        return "regression", ""
    runs = int(confirmation.get("runs") or 0)
    failures = int(confirmation.get("failures") or 0)
    state = confirmation.get("state")
    active_runs = int(confirmation.get("active_runs") or 0)  # a dev item re-runs both versions
    if active_runs:
        both = (
            f"the candidate failed {failures} of {runs} more runs, the active version passed "
            f"{int(confirmation.get('active_passes') or 0)} of {active_runs}"
        )
        if state == "confirming":
            return (
                "confirming",
                f"Apparent regression: confirming with {runs} more runs of each version",
            )
        if state == "cleared":
            return "same", f"Not a regression: {both}"
        return "regression", f"Regression: confirmed, {both}"
    if state == "confirming":
        return "confirming", f"Apparent regression: confirming with {runs} more runs"
    if state == "cleared":
        return "same", f"Not a regression: failed {failures} of {runs} more runs"
    return "regression", f"Regression: confirmed, failed {failures} of {runs} more runs"


def _cell(found: dict[str, Any] | None, need: int) -> dict[str, Any]:
    if found is None:
        return {"pending": True}
    return {"passed": found["passes"] >= need, "runs": f"{found['passes']} of {found['runs']} runs"}


def ledger_view(
    items: list[tuple[str, str]],
    *,
    baseline: Row,
    candidate: Row | None,
    session_id: Any,
    display_tz: str | None,
    repeats: int,
    pass_threshold: int,
    promotion: Mapping[str, Any] | None = None,
    sample_rate: float | None = None,
) -> dict[str, Any]:
    """The live holdout ledger of the open session. `items` are (holdout item id, question);
    a cell reads "Not run yet" until its item's runs finish. With `promotion` (promotion_view),
    the candidate is the promoted, now active, version and the baseline the version it replaced.
    Experiment runs are traced as a sample (`sample_rate`, the pack's by default): a row none of
    whose runs was traced reads "Not traced", never a broken link."""
    rate = experiment_sample_rate() if sample_rate is None else sample_rate
    active_cells, candidate_cells = holdout_cells(baseline), holdout_cells(candidate)
    base_version = str(baseline["knowledge_version"])
    cand_version = str(candidate["knowledge_version"]) if candidate else None
    out, fixed, regressions, base_pass, cand_pass, finished = [], 0, 0, 0, 0, 0
    for item, question in items:
        a, c = active_cells.get(item), candidate_cells.get(item)
        a_cell, c_cell = _cell(a, pass_threshold), _cell(c, pass_threshold)
        change, change_text = "", ""
        if a is not None:
            finished += 1
            base_pass += a_cell["passed"]
        if c is not None:
            cand_pass += c_cell["passed"]
        if a is not None and c is not None:
            if c_cell["passed"] and not a_cell["passed"]:
                change, fixed = "fixed", fixed + 1
            elif a_cell["passed"] and not c_cell["passed"]:
                change, change_text = confirm_regression(c.get("confirmation"))
                regressions += change == "regression"
            else:
                change = "same"
        trace = (c or {}).get("trace_url") or (a or {}).get("trace_url")
        not_traced = trace is None and any(x and x.get("not_traced") for x in (c, a))
        out.append(
            {
                "item": item,
                "question": question,
                "change": change,
                "change_text": change_text,
                "active": a_cell,
                "candidate": c_cell if cand_version else None,
                "trace_url": trace,
                "not_traced": not_traced,
            }
        )
    rule = f"Each item runs {repeats} times and passes on {pass_threshold} of {repeats}."
    total = len(items)
    if cand_version:
        noun = "regression" if regressions == 1 else "regressions"
        summary = (
            f"{rule} {base_version} passes {base_pass} of {total}; {cand_version} passes "
            f"{cand_pass} of {total}: {fixed} fixed, {regressions} {noun}."
        )
    else:
        summary = (
            f"{rule} {base_version} passes {base_pass} of {finished} finished items; "
            f"{total - finished} not run yet."
        )
    list_source = candidate or baseline
    if promotion is not None and cand_version:
        by = f" by {promotion['approved_by']}" if promotion.get("approved_by") else ""
        active_label, candidate_label = f"{base_version}, replaced", f"{cand_version}, active"
        baseline_heading = f"Replaced, {base_version}"
        candidate_heading = f"Active, {cand_version}, promoted{by}"
    else:
        is_active = baseline["version_status"] == "active"
        active_label = f"{base_version}, active" if is_active else base_version
        candidate_label = f"{cand_version}, candidate" if cand_version else None
        baseline_heading = f"Baseline, {active_label}"
        candidate_heading = f"Candidate, {cand_version}" if cand_version else None
    return {
        "state": "live",
        "active_label": active_label,
        "candidate_label": candidate_label,
        "baseline_heading": baseline_heading,
        "candidate_heading": candidate_heading,
        "candidate_version": cand_version,
        "list_version": cand_version or base_version,
        "baseline_stamp": stamp(
            baseline["experiment_id"], session_id, baseline["started_at"], baseline["langsmith_url"]
        ),
        "candidate_stamp": stamp(
            candidate["experiment_id"],
            session_id,
            candidate["started_at"],
            candidate["langsmith_url"],
        )
        if candidate
        else None,
        "trace_list_url": list_source["langsmith_url"],
        "trace_sample_note": sample_note(rate),
        "display_tz": display_tz,
        "rows": out,
        "summary_text": summary,
    }


def pick_experiments(
    experiments: list[Row], promotion: Row | None = None
) -> tuple[Row | None, Row | None]:
    """(baseline, candidate) of the open session: the baseline is the newest experiment of the
    active version; the candidate is the newest experiment of another version started after it.

    After a promotion with no newer candidate experiment, the pair is the version it replaced and
    the promoted version, so the ledger still shows what the promotion changed."""
    baseline = next((e for e in reversed(experiments) if e["version_status"] == "active"), None)
    if baseline is None:
        return None, None
    candidate = next(
        (
            e
            for e in reversed(experiments)
            if e["version_status"] != "active" and e["started_at"] >= baseline["started_at"]
        ),
        None,
    )
    if candidate is not None or promotion is None:
        return baseline, candidate
    promoted = _newest(experiments, str(promotion["candidate_version"]), None)
    replaced = _newest(
        experiments,
        str(promotion["active_version"]),
        promoted["started_at"] if promoted else None,
    )
    if promoted is None or replaced is None:
        return baseline, None
    return replaced, promoted


def _newest(experiments: list[Row], version: str, before: datetime | None) -> Row | None:
    return next(
        (
            e
            for e in reversed(experiments)
            if e["knowledge_version"] == version and (before is None or e["started_at"] <= before)
        ),
        None,
    )


def is_promotion_pair(candidate: Row | None, promotion: Row | None) -> bool:
    """Whether the ledger's candidate is the version the gate promoted (now the active one)."""
    return (
        candidate is not None
        and promotion is not None
        and str(candidate["knowledge_version"]) == str(promotion["candidate_version"])
        and candidate["version_status"] == "active"
    )


def active_promotion(found: Row | None, versions: list[Row]) -> Row | None:
    """The session's newest promotion (ops_reads.last_promotion), while the version it promoted
    is still the active one."""
    active = next((v for v in versions if v["status"] == "active"), None)
    if found is None or active is None or found["candidate_version"] != active["version"]:
        return None
    return found


def promotion_pair(
    experiments: list[Row], chosen: Row, promotion: Row | None
) -> tuple[Row, Row] | None:
    """For an experiment of the promoted or the replaced version: (the replaced version's,
    the promoted version's) experiment, so its ledger shows what the promotion changed."""
    if promotion is None:
        return None
    version = str(chosen["knowledge_version"])
    promoted, replaced = str(promotion["candidate_version"]), str(promotion["active_version"])
    if version == promoted:
        before = _newest(experiments, replaced, chosen["started_at"])
        return (before, chosen) if before else None
    if version == replaced:
        after = _newest(experiments, promoted, None)
        return (chosen, after) if after else None
    return None


def promotion_view(promotion: Row | None) -> dict[str, Any] | None:
    if promotion is None:
        return None
    out = {
        "version": str(promotion["candidate_version"]),
        "replaced": str(promotion["active_version"]),
        "approved_by": promotion["approved_by"],
    }
    if promotion.get("kind") == "safeguard":  # the class-day safeguard, not a gate promotion
        out["safeguard"] = True
    return out


def no_candidate_text(promotion: Mapping[str, Any] | None) -> str:
    """What the Improve page says when no candidate version exists yet: since the session started,
    or, after a promotion, since that promotion."""
    if promotion is None:
        return "No candidate version in this session yet. Run the analyzer to propose one."
    by = f", approved by {promotion['approved_by']}" if promotion["approved_by"] else ""
    if promotion.get("safeguard"):
        who = f" (run by {promotion['approved_by']})" if promotion["approved_by"] else ""
        return (
            f"{promotion['version']} is the active version: the version verified in rehearsal, "
            f"activated by the class-day safeguard{who} in place of "
            f"{promotion['replaced']}, which the gate promoted in class. Its families keep the "
            "level they earned in rehearsal."
        )
    return (
        f"{promotion['version']} is the active version, promoted from {promotion['replaced']}"
        f"{by}. No candidate version since the promotion. Run the analyzer to propose one."
    )


# The gate stores only "promoted" or "blocked"; a candidate that clears every check but human
# approval is stored as blocked with this sentence (loop4_hill_climbing/gate.py decide).
READY_PREFIX = "Ready for human approval: "
BLOCKED_PREFIX = "Blocked: "


def gate_view(verdict: str, sentence: str) -> dict[str, str]:
    """The gate's state: promoted, ready (waiting only for a person's approval), or blocked, with
    its sentence less the word the state already says."""
    if verdict == "promoted":
        return {"state": "promoted", "sentence": sentence}
    if sentence.startswith(READY_PREFIX):
        return {"state": "ready", "sentence": sentence.removeprefix(READY_PREFIX)}
    return {"state": "blocked", "sentence": sentence.removeprefix(BLOCKED_PREFIX)}


def knowledge_diff(active: Row | None, candidate: Row | None) -> str:
    if active is None or candidate is None:
        return ""
    return "\n".join(
        difflib.unified_diff(
            str(active["yaml"]).splitlines(),
            str(candidate["yaml"]).splitlines(),
            fromfile=str(active["version"]),
            tofile=str(candidate["version"]),
            lineterm="",
        )
    )
