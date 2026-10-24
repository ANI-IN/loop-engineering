"""The make targets of the live demos: `make demo NAME=<demo>`, `make reset NAME=<section>`,
`make reset-discarding-baseline NAME=hill-climbing-loop`, and `make open-code NAME=<section>`.
Recovery for every demo is reset, then the same trigger again.

Every reset clears run state and releases the kill switch. For the hill-climbing loop it also
clears the candidate and knowledge state: experiments of the open session other than its baseline,
gate decisions, analyzer and experiment requests, unattended-level eligibility, and candidate
knowledge versions; the baseline's version becomes the active one again. The baseline (the first
experiment started in the open session, the one launched at the poll) is kept, and reported, unless
the reset is the deliberate full one that discards it too. The baseline and the knowledge versions
are the selected pack's (DATAPILOT_PACK); another pack's versions are never touched.

Before the hill-climbing reset deletes or retires any of that state, it copies every row it changes
into the reset archive (loop3_events/archive.py, migration 015), stamped with the reset time and the
live session, and its report says how many rows it archived and where. The full reset archives the
baseline too. A knowledge version verified in rehearsal (the class-day safeguard) is never deleted,
nor is one a person approved or the gate promoted: it stays, retired, so its name and its rules stay
one pair in every trace and report (a reset never frees a version name; versions.next_name).

The hill-climbing reset refuses while the runner is running a request, since it would delete the
experiment that request still writes to; a request left running by a runner that stopped is closed
as failed and cleared.

`make demo NAME=improve-cleared-unattended` refuses while the finale cannot show its moment
(datapilot.finale), and `make autonomy LEVEL=<level>` sets the system's autonomy level through the
api, as the console's control does.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import httpx
import psycopg

from datapilot import db, finale
from datapilot.config import PACKS, active_pack, pack_config
from datapilot.contracts import AutonomyLevel, registries
from datapilot.contracts.api import AutonomyIn
from datapilot.loop3_events import archive, demos, improvement
from datapilot.names import SECTIONS_BY_SLUG
from datapilot.observability import spend
from datapilot.settings import REPO, get_settings

# Run state, children first. Live sessions and budgets always stay.
RESET_TABLES = (
    "ops.posts",
    "ops.approvals",
    "ops.run_events",
    "ops.event_duplicates",
    "ops.runs",
    "ops.jobs",
    "ops.events",
)
HILL_CLIMBING = "hill-climbing-loop"
BASELINE_SQL = (
    "SELECT experiment_id, knowledge_version, started_at FROM ops.experiments "
    "WHERE session_id = (SELECT session_id FROM ops.live_sessions WHERE ended_at IS NULL) "
    "AND pack = %s ORDER BY started_at, experiment_id LIMIT 1"
)
ACTIVE_VERSION_SQL = (
    "SELECT version FROM ops.knowledge_versions WHERE pack = %s AND status = 'active'"
)
# Versions a person approved or the gate (or the safeguard) promoted: read before the reset deletes
# this session's decisions, and never deleted.
DECIDED_VERSIONS_SQL = (
    "SELECT version FROM ops.knowledge_versions k WHERE pack = %s AND (k.approved_by IS NOT NULL "
    "OR k.activated_at IS NOT NULL OR EXISTS (SELECT 1 FROM ops.promotion_decisions d "
    "WHERE d.pack = k.pack AND d.candidate_version = k.version AND d.verdict = 'promoted')) "
    "ORDER BY version"
)
RUNNING_REQUESTS_SQL = (
    "SELECT request_id, kind, started_at FROM ops.improvement_requests WHERE status = 'running' "
    "ORDER BY started_at, request_id"
)
CLOSE_ORPHANED_SQL = (
    "UPDATE ops.improvement_requests SET status = 'failed', finished_at = now(), "
    "result = jsonb_build_object('error', %s::text) WHERE status = 'running'"
)
ORPHANED = "the hill-climbing runner stopped while this request ran; closed by make reset"


class ResetRefused(RuntimeError):
    """The reset would destroy work still in progress: the message names it and what to do."""


class FinaleRefused(RuntimeError):
    """The finale cannot show its moment now: the message says the step that fixes it."""


@dataclass(frozen=True)
class Baseline:
    experiment_id: str
    knowledge_version: str
    started_at: datetime

    def describe(self) -> str:
        started = self.started_at.isoformat(timespec="seconds")
        return f"experiment {self.experiment_id} of {self.knowledge_version}, started {started}"


@dataclass
class ResetReport:
    section: str
    cleared: list[str] = field(default_factory=list)
    kept_baseline: Baseline | None = None
    discarded_baseline: Baseline | None = None
    removed_versions: list[str] = field(default_factory=list)
    kept_versions: list[str] = field(default_factory=list)  # approved or promoted, now retired
    closed_requests: list[str] = field(default_factory=list)  # left running by a stopped runner
    active_version: str | None = None
    archived: archive.Archive | None = None

    def lines(self) -> list[str]:
        out = [f"reset {self.section}: cleared {', '.join(self.cleared)}"]
        if self.section != HILL_CLIMBING:
            return out
        if self.kept_baseline:
            out.append(f"kept this session's baseline: {self.kept_baseline.describe()}")
        elif self.discarded_baseline:
            out.append(f"discarded this session's baseline: {self.discarded_baseline.describe()}")
        else:
            out.append("no baseline experiment in this session to keep")
        if self.closed_requests:
            out.append(
                "closed requests the stopped runner left running: "
                + ", ".join(self.closed_requests)
            )
        if self.removed_versions:
            out.append(f"removed candidate versions: {', '.join(self.removed_versions)}")
        if self.kept_versions:
            out.append(
                "kept, retired, the versions a person approved or the gate promoted (their names "
                f"are never reused): {', '.join(self.kept_versions)}"
            )
        out.append(f"active knowledge version: {self.active_version or 'none'}")
        if self.archived is not None:
            out.append(
                f"archived {self.archived.total} row{'' if self.archived.total == 1 else 's'} "
                f"before the reset changed them ({self.archived.describe()}) in "
                f"{archive.ARCHIVE_TABLE}, reset archive {self.archived.reset_id}; read them with "
                "`datapilot archive list` and `datapilot archive show <experiment id>`"
            )
        return out


def demo(name: str, *, client: Any = None) -> demos.Triggered:
    found = registries.demos().by_id(name)
    if found.id == finale.FINALE_DEMO:
        check_finale()
    if client is None:  # the worker records the demo's calls under this command's activity
        url, headers = get_settings().datapilot_api_url, spend.activity_headers()
        with httpx.Client(base_url=url, timeout=30, headers=headers) as http:
            return demos.trigger(http, found)
    return demos.trigger(client, found)


def check_finale() -> None:
    """FinaleRefused unless the finale can show its moment: no promotion still pending, the kill
    switch released, the system at the unattended level (datapilot.finale)."""
    with db.connect(db.Role.APP) as conn:
        state = finale.read(conn, active_pack())
    reason = finale.refusal(state)
    if reason:
        raise FinaleRefused(reason)


def set_autonomy(level: str, *, by: str, client: Any = None) -> AutonomyLevel:
    """`make autonomy LEVEL=<level> BY=<name>`: the system's autonomy level, set by a person through
    POST /control/autonomy (refused while the kill switch is engaged). The finale needs the
    unattended level; a family not cleared then gets the assisted level."""
    try:
        chosen = AutonomyLevel(level.strip().replace("-", "_"))
    except ValueError as error:
        names = ", ".join(v.value.replace("_", "-") for v in AutonomyLevel)
        raise ValueError(f"unknown autonomy level {level!r}; use one of {names}") from error
    body = AutonomyIn(level=chosen, by=by).model_dump(mode="json")
    if client is None:
        with httpx.Client(base_url=get_settings().datapilot_api_url, timeout=30) as http:
            return _set_autonomy(http, body)
    return _set_autonomy(client, body)


def _set_autonomy(client: Any, body: dict[str, Any]) -> AutonomyLevel:
    response = client.post("/control/autonomy", json=body)
    if response.status_code >= 400:
        detail = response.json().get("detail", response.text) if response.content else ""
        raise ValueError(f"the api refused the autonomy level ({response.status_code}): {detail}")
    return AutonomyLevel(response.json()["autonomy_level"])


def pre_authored_versions(pack: str | None = None) -> set[str]:
    """Versions shipped as files in the pack (v1, the over-broad rule's version): never deleted."""
    return {path.stem for path in (PACKS / (pack or active_pack()) / "knowledge").glob("*.yaml")}


def reset(section: str, *, discard_baseline: bool = False) -> ResetReport:
    if section not in SECTIONS_BY_SLUG:
        raise KeyError(f"unknown section {section!r}; use one of {sorted(SECTIONS_BY_SLUG)}")
    if discard_baseline and section != HILL_CLIMBING:
        raise ValueError("only the hill-climbing loop has a baseline to discard")
    report = ResetReport(section, cleared=list(RESET_TABLES))
    with db.connect(db.Role.APP) as conn:
        if section == HILL_CLIMBING:
            report.closed_requests = _close_running_requests(conn)
        for table in RESET_TABLES:
            conn.execute(f"DELETE FROM {table}")  # a fixed list of table names, no input
        if section == HILL_CLIMBING:
            _reset_hill_climbing(conn, report, discard_baseline=discard_baseline)
        conn.execute(
            "UPDATE ops.control SET kill_switch = 'released', autonomy_level = %s, "
            "changed_at = now(), changed_by = 'reset', reason = %s, "
            "worker_restart_requested_at = NULL WHERE id = 1",
            (pack_config()["autonomy"]["default_level"], f"make reset NAME={section}"),
        )
        conn.commit()
    return report


def _close_running_requests(conn: psycopg.Connection[Any]) -> list[str]:
    """ResetRefused while the runner runs a request (the reset would delete the experiment it still
    writes to, and its result would be lost); a request left running by a runner that stopped is
    closed as failed, so the reset clears it. Returns the ids it closed."""
    running = conn.execute(RUNNING_REQUESTS_SQL).fetchall()
    if not running:
        return []
    if improvement.runner_serving(conn):
        named = ", ".join(
            f"{r['kind']} request {str(r['request_id'])[:8]} (started "
            f"{r['started_at'].isoformat(timespec='seconds')})"
            for r in running
        )
        raise ResetRefused(
            f"not reset: the hill-climbing runner is running the {named}, and the reset would "
            "delete its experiment while it still writes to it. Wait until the Improve page shows "
            "it finished, then reset; or stop it first with docker compose restart "
            "hill-climbing-runner, then reset."
        )
    conn.execute(CLOSE_ORPHANED_SQL, (ORPHANED,))
    return [str(r["request_id"]) for r in running]


def _reset_hill_climbing(
    conn: psycopg.Connection[Any], report: ResetReport, *, discard_baseline: bool
) -> None:
    pack = active_pack()  # knowledge state is the selected pack's; run state is cleared for all
    row = conn.execute(BASELINE_SQL, (pack,)).fetchone()
    baseline = (
        Baseline(str(row["experiment_id"]), row["knowledge_version"], row["started_at"])
        if row
        else None
    )
    active = conn.execute(ACTIVE_VERSION_SQL, (pack,)).fetchone()
    keep_version = (
        baseline.knowledge_version if baseline else (active["version"] if active else None)
    )
    kept = archive.open_archive(
        conn,
        section=HILL_CLIMBING,
        pack=pack,
        discarded_baseline=bool(discard_baseline and baseline),
        reset_by=f"make {'reset-discarding-baseline' if discard_baseline else 'reset'} "
        f"NAME={HILL_CLIMBING}",
    )
    report.archived = kept
    decided = [r["version"] for r in conn.execute(DECIDED_VERSIONS_SQL, (pack,)).fetchall()]
    session_experiments = (
        "session_id = (SELECT session_id FROM ops.live_sessions WHERE ended_at IS NULL)"
    )
    if discard_baseline or baseline is None:
        experiments, params = session_experiments, ()
        report.discarded_baseline = baseline
    else:
        experiments = f"{session_experiments} AND experiment_id <> %s"
        params = (baseline.experiment_id,)
        report.kept_baseline = baseline
    archive.keep(conn, kept, "ops.experiments", experiments, params)
    conn.execute(f"DELETE FROM ops.experiments WHERE {experiments}", params)
    # this session's gate decisions; earlier sessions keep their record
    decisions = "decided_at >= (SELECT started_at FROM ops.live_sessions WHERE ended_at IS NULL)"
    archive.keep(conn, kept, "ops.promotion_decisions", decisions)
    conn.execute(f"DELETE FROM ops.promotion_decisions WHERE {decisions}")
    archive.keep(conn, kept, "ops.improvement_requests", "status <> 'running'")
    conn.execute("DELETE FROM ops.improvement_requests WHERE status <> 'running'")
    archive.keep(conn, kept, "ops.autonomy_policy", "true")
    conn.execute("DELETE FROM ops.autonomy_policy")
    # this session's analyzer candidates and the choice the Improve page shows
    archive.keep(conn, kept, "ops.analyzer_candidates", session_experiments)
    conn.execute(f"DELETE FROM ops.analyzer_candidates WHERE {session_experiments}")
    report.cleared += [
        "ops.experiments (this session, except the baseline)"
        if report.kept_baseline
        else "ops.experiments (this session)",
        "ops.promotion_decisions",
        "ops.improvement_requests",
        "ops.autonomy_policy",
        "ops.analyzer_candidates (this session)",
    ]
    if keep_version and (active is None or active["version"] != keep_version):
        archive.keep(
            conn,
            kept,
            "ops.knowledge_versions",
            "pack = %s AND status = 'active'",
            (pack,),
            action="retired",
        )
        conn.execute(
            "UPDATE ops.knowledge_versions SET status = 'retired' "
            "WHERE pack = %s AND status = 'active'",
            (pack,),
        )
        conn.execute(
            "UPDATE ops.knowledge_versions SET status = 'active', activated_at = now() "
            "WHERE pack = %s AND version = %s",
            (pack, keep_version),
        )
    shipped = sorted(pre_authored_versions(pack))
    unused = conn.execute(
        "SELECT version FROM ops.knowledge_versions k WHERE pack = %s AND status <> 'active' "
        "AND version <> ALL(%s) AND NOT EXISTS (SELECT 1 FROM ops.experiments e "
        "WHERE e.pack = k.pack AND e.knowledge_version = k.version) "
        "AND NOT EXISTS (SELECT 1 FROM ops.promotion_decisions d "
        "WHERE d.pack = k.pack AND k.version IN (d.candidate_version, d.active_version)) "
        "AND NOT EXISTS (SELECT 1 FROM ops.rehearsal_verifications v "
        "WHERE v.pack = k.pack AND v.version = k.version) "
        "ORDER BY version",
        (pack, shipped),
    ).fetchall()
    # a version a person approved or the gate promoted keeps its row: only drafts nobody decided go
    report.kept_versions = [r["version"] for r in unused if r["version"] in decided]
    report.removed_versions = [r["version"] for r in unused if r["version"] not in decided]
    removed = "pack = %s AND version = ANY(%s)"
    archive.keep(conn, kept, "ops.knowledge_versions", removed, (pack, report.removed_versions))
    conn.execute(
        f"DELETE FROM ops.knowledge_versions WHERE {removed}", (pack, report.removed_versions)
    )
    drafts = "pack = %s AND status IN ('draft', 'approved') AND version <> ALL(%s)"
    archive.keep(conn, kept, "ops.knowledge_versions", drafts, (pack, shipped), action="retired")
    conn.execute(
        f"UPDATE ops.knowledge_versions SET status = 'retired' WHERE {drafts}", (pack, shipped)
    )
    now_active = conn.execute(ACTIVE_VERSION_SQL, (pack,)).fetchone()
    report.active_version = now_active["version"] if now_active else None


def code_refs(section: str) -> list[str]:
    refs = []
    for item in registries.demos().for_section(section):
        refs += [f"{ref.path}:{ref.lines.split('-')[0]}" for ref in item.code]
    return list(dict.fromkeys(refs))


def open_code(section: str) -> list[str]:
    refs = code_refs(section)
    editor = shutil.which("code")
    if editor:
        for ref in refs:
            subprocess.run([editor, "--goto", str(REPO / ref)], check=False)
    return refs
