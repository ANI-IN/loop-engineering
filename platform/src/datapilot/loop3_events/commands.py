"""The make targets of the live demos: `make demo NAME=<demo>`, `make reset NAME=<section>`,
`make reset-discarding-baseline NAME=hill-climbing-loop`, and `make open-code NAME=<section>`.
Recovery for every demo is reset, then the same trigger again.

Every reset clears run state and releases the kill switch. For the hill-climbing loop it also
clears the candidate and knowledge state: experiments of the open session other than its baseline,
gate decisions, analyzer and experiment requests, unattended-level eligibility, and candidate
knowledge versions; the baseline's version becomes the active one again, and with no baseline
kept in the open session the starting knowledge v1 does. The baseline is the open session's
earliest finished experiment, made with no planted flag on, of v1, of a version a person approved
and the gate promoted, or of one the safeguard verified (normally the one launched at the poll). It
is kept, and reported, unless the reset is the deliberate full one that discards it too. So a reset
never makes a draft, or a version the gate blocked, the active one. The baseline and the knowledge
versions are the selected pack's (DATAPILOT_PACK); another pack's versions are never touched.

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
(datapilot.finale), or while a planted flag is on in .env, in its own environment, or in a running
service, and `make autonomy LEVEL=<level>` sets the system's autonomy level through the api, as the
console's control does.

A demo's planted flags are its own, never .env's: `make demo NAME=<demo>` switches on its demo aids
(demo pacing) for its own runs, and `make demo NAME=<demo> PLANTED=1` its planted code bugs too.
A flag read while a run works (in the worker, the api, the hill-climbing runner, or this process)
travels with the demo's events and requests and is on for those alone; the api takes only the
named demo's own flags. A flag read once, as a service starts (AT_SERVICE_START), is set for that
service only: the demo restarts it with the flag and a tag only the demo's jobs carry, so the
restarted worker claims the demo's runs alone and every other run waits, queued; the demo waits
for its runs to end (Ctrl+C ends the wait), then restarts it again without, even on an error.
.env is never written.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
import uuid
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
import psycopg

from datapilot import db, finale, planted
from datapilot.config import PACKS, active_pack, pack_config
from datapilot.contracts import TERMINAL, AutonomyLevel, RunStatus, registries
from datapilot.contracts.api import AutonomyIn
from datapilot.loop3_events import archive, demos, improvement, sessions
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
# A version the reset may make active: the starting knowledge, one a person approved and the gate
# promoted, or one the class-day safeguard verified in rehearsal. Never a draft, nor a version the
# gate blocked (the over-broad rule's), whatever experiment ran on it.
APPROVED_VERSION = (
    "(k.version = %(starting)s OR (k.approved_by IS NOT NULL AND EXISTS (SELECT 1 FROM "
    "ops.promotion_decisions d WHERE d.pack = k.pack AND d.candidate_version = k.version "
    "AND d.verdict = 'promoted' AND d.kind = 'gate')) OR EXISTS (SELECT 1 FROM "
    "ops.rehearsal_verifications v WHERE v.pack = k.pack AND v.version = k.version))"
)
# The baseline: the open session's earliest finished experiment of such a version, made with no
# planted flag on (an experiment the kill switch stopped never finished).
BASELINE_SQL = (
    "SELECT e.experiment_id, e.knowledge_version, e.started_at FROM ops.experiments e "
    "JOIN ops.knowledge_versions k ON k.pack = e.pack AND k.version = e.knowledge_version "
    "WHERE e.session_id = (SELECT session_id FROM ops.live_sessions WHERE ended_at IS NULL) "
    "AND e.pack = %(pack)s AND e.finished_at IS NOT NULL AND cardinality(e.planted_active) = 0 "
    f"AND {APPROVED_VERSION} ORDER BY e.started_at, e.experiment_id LIMIT 1"
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


class DemoRefused(RuntimeError):
    """The demo cannot run as asked: the message says why and what to run instead."""


# Flags read once, as a service starts, so no run can carry them: the service they need restarted.
AT_SERVICE_START = planted.AT_SERVICE_START
# Runs a restart of the worker would stop: the demo starts only when none is under way.
UNDER_WAY_SQL = (
    "SELECT run_id FROM ops.runs WHERE status IN ('received', 'queued', 'running', 'verifying')"
)
# Runs other than the demo's that a worker is working on: the restart back waits for them (none
# should be: the restarted worker claims the demo's own jobs alone, by their tag).
OTHERS_WORKING_SQL = (
    "SELECT run_id FROM ops.runs WHERE status IN ('running', 'verifying') "
    "AND NOT (run_id::text = ANY(%s))"
)
RESTORE_WAIT_SECONDS = 120.0
Compose = Callable[[list[str]], None]


@dataclass
class DemoRestart:
    """A restart of services for one demo: the tag only the demo's jobs carry, which the restarted
    services alone claim, and the demo's run ids once it has triggered them."""

    tag: str
    run_ids: list[str] = field(default_factory=list)


class _Tagged:
    """The api client with the demo's headers on every request: its planted flags and the demo
    they belong to, and, while a service runs restarted for it, the tag of its runs."""

    def __init__(self, client: Any, headers: dict[str, str]) -> None:
        self.client, self.headers = client, headers

    def post(self, url: str, **kwargs: Any) -> Any:
        return self.client.post(url, **{**kwargs, "headers": self._merged(kwargs)})

    def get(self, url: str, **kwargs: Any) -> Any:
        return self.client.get(url, **kwargs)

    def _merged(self, kwargs: dict[str, Any]) -> dict[str, str]:
        return {**(kwargs.get("headers") or {}), **self.headers}


# The starting knowledge (loop4_hill_climbing.versions.STARTING_VERSION; the event loop does not
# import the hill-climbing loop, and a unit test keeps the two equal).
STARTING_VERSION = "v1"


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


def demo(
    name: str,
    *,
    planted_bugs: bool = False,
    client: Any = None,
    compose: Compose | None = None,
    say: Callable[[str], None] = print,
    wait_seconds: float = 900.0,
) -> demos.Triggered:
    """Trigger a registry demo; with `planted_bugs` (PLANTED=1) its planted half."""
    found = registries.demos().by_id(name)
    if found.id == finale.FINALE_DEMO:
        check_finale()
    flags = demo_flags(found, planted_bugs=planted_bugs)
    at_start = {flag: AT_SERVICE_START[flag] for flag in flags if flag in AT_SERVICE_START}
    if flags:
        say(f"{name}: planted flags on for this demo's runs only: {', '.join(flags)}")
    if client is None:  # the worker records the demo's calls under this command's activity
        url = get_settings().datapilot_api_url
        with httpx.Client(base_url=url, timeout=30, headers=spend.activity_headers()) as http:
            return _run_demo(http, found, flags, at_start, compose, say, wait_seconds)
    return _run_demo(client, found, flags, at_start, compose, say, wait_seconds)


def demo_flags(found: Any, *, planted_bugs: bool) -> list[str]:
    """The flags the demo switches on for its own runs; DemoRefused for PLANTED=1 on a demo with
    no planted code bug. A demo whose only half is planted (planted.ONLY_PLANTED_HALF) switches
    its bugs on with or without PLANTED=1."""
    planted_bugs = planted_bugs or found.id in planted.ONLY_PLANTED_HALF
    flags = planted.for_demo(found.planted, bugs=planted_bugs)
    if planted_bugs and flags == planted.for_demo(found.planted, bugs=False):
        raise DemoRefused(
            f"{found.id} has no planted bug to switch on: run make demo NAME={found.id} "
            "without PLANTED=1"
        )
    return flags


def _run_demo(
    client: Any,
    found: Any,
    flags: Sequence[str],
    at_start: dict[str, str],
    compose: Compose | None,
    say: Callable[[str], None],
    wait_seconds: float,
) -> demos.Triggered:
    with _triggered(client, found, flags, at_start, compose, say) as (done, restarted):
        if restarted:
            wait_for_runs(client, done.run_ids, wait_seconds, say)
    return done


def require_session(client: Any) -> None:
    """DemoRefused with no live session open, before any service restart or model call: the
    demo's runs would belong to no session, and the console would never show them."""
    if client.get("/sessions/current").status_code == 404:
        raise DemoRefused(sessions.NO_SESSION)


@contextmanager
def _triggered(
    client: Any,
    found: Any,
    flags: Sequence[str],
    at_start: dict[str, str],
    compose: Compose | None,
    say: Callable[[str], None],
) -> Iterator[tuple[demos.Triggered, bool]]:
    """The demo triggered, its flags still on for its runs until the block ends; with True when a
    service was restarted for it. The api takes the per-run flags in a header, as the demo's own
    (planted.allowed_for); a flag read at a service's start goes to that service alone
    (services_with). A flag this process reads (the random digest id) is on here alone. With
    no live session open it refuses first, before any restart (require_session)."""
    require_session(client)
    per_run = [flag for flag in flags if flag not in at_start]
    headers = planted.header(per_run, demo=found.id)
    with (
        planted.for_this_run(per_run),
        services_with(at_start, compose=compose, say=say, demo=found.id) as restart,
    ):
        if restart is not None:
            headers[planted.TAG_HEADER] = restart.tag
        done = demos.trigger(_Tagged(client, headers) if headers else client, found)
        if restart is not None:
            restart.run_ids += done.run_ids
        yield done, restart is not None


@contextmanager
def demo_running(
    name: str,
    flags: Sequence[str],
    *,
    client: Any,
    compose: Compose | None = None,
    say: Callable[[str], None] = print,
) -> Iterator[demos.Triggered]:
    """make demo's own path, for a caller that acts during the demo's runs (the capture runner):
    the demo triggered with exactly `flags` on for its own runs, which must be among its own
    (its planted bugs and demo aids, such as only some of its bugs for a guide step), held until
    the block ends, when any service restarted for it is put back."""
    found = registries.demos().by_id(name)
    if found.id == finale.FINALE_DEMO:
        check_finale()
    own = planted.for_demo(found.planted, bugs=True)
    chosen = planted.checked(flags)
    if others := [flag for flag in chosen if flag not in own]:
        raise DemoRefused(f"{', '.join(others)} is not a planted flag of {name}")
    at_start = {flag: AT_SERVICE_START[flag] for flag in chosen if flag in AT_SERVICE_START}
    if chosen:
        say(f"{name}: planted flags on for this demo's runs only: {', '.join(chosen)}")
    with _triggered(client, found, chosen, at_start, compose, say) as (done, _restarted):
        yield done


def wait_for_runs(
    client: Any, run_ids: Sequence[str], seconds: float, say: Callable[[str], None]
) -> None:
    """Until every run has ended, or `seconds` pass, or Ctrl+C: while a service runs with a
    demo's flag, this command holds it, and the restart after it puts the service back."""
    say(
        "The service keeps the flag until this demo's runs end; then this command restarts it "
        "without the flag. Press Ctrl+C to end the wait sooner."
    )
    deadline = time.monotonic() + seconds
    try:
        while time.monotonic() < deadline:
            states = [client.get(f"/runs/{run_id}").json()["status"] for run_id in run_ids]
            if all(RunStatus(state) in TERMINAL for state in states):
                return
            time.sleep(2.0)
        say(f"The demo's runs had not ended after {seconds:.0f} seconds: the flag goes off now.")
    except KeyboardInterrupt:
        say("Stopped waiting: the flag goes off now.")


def _docker_compose(args: list[str]) -> None:
    done = subprocess.run(["docker", "compose", *args], cwd=REPO, capture_output=True, text=True)
    if done.returncode != 0:
        tail = "\n".join((done.stdout + done.stderr).strip().splitlines()[-10:])
        raise DemoRefused(f"docker compose {' '.join(args[-6:])} failed:\n{tail}")


@contextmanager
def services_with(
    flags: dict[str, str],
    *,
    compose: Compose | None = None,
    say: Callable[[str], None] = print,
    demo: str = "demo",
    restore_wait_seconds: float = RESTORE_WAIT_SECONDS,
) -> Iterator[DemoRestart | None]:
    """Restart the services `flags` names (flag -> service) with those flags on, for the block
    alone: a Compose override sets them, and .env is never written. The override also sets a tag
    that only this demo's jobs carry (the block sends it with them): the restarted worker claims
    those jobs alone, so another run never gets the flag; it waits, queued, for the restart back.
    Afterwards, even on an error or Ctrl+C, the services are restarted from compose.yaml and .env
    alone, once no other run is being worked on (or after `restore_wait_seconds`). Refused while a
    run is under way, since a restart would stop it."""
    if not flags:
        yield None
        return
    run = compose or _docker_compose
    with db.connect(db.Role.APP) as conn:
        going = [str(row["run_id"]) for row in conn.execute(UNDER_WAY_SQL)]
    if going:
        raise DemoRefused(
            f"not started: {len(going)} run(s) are under way ({', '.join(going[:3])}), and the "
            "demo restarts a service, which would stop them. Wait until they end, then run it "
            "again."
        )
    restarted = DemoRestart(tag=f"{demo}-{uuid.uuid4().hex[:12]}")
    services = sorted(set(flags.values()))
    base = ["-f", str(REPO / "compose.yaml")]
    restart = ["up", "--detach", "--wait", "--no-deps", "--no-build", *services]
    override = _override_file(flags, restarted.tag)
    say(
        f"Restarting {', '.join(services)} with {', '.join(flags)} on, for this demo's runs only: "
        "every other run waits, queued, until the restart back"
    )
    try:
        run([*base, "-f", str(override), *restart])
        yield restarted
    finally:
        try:
            _wait_for_others(restarted.run_ids, restore_wait_seconds, say)
        finally:
            say(f"Restarting {', '.join(services)} without the demo's flags (as .env sets them)")
            try:
                run([*base, *restart])
            except DemoRefused as error:
                raise DemoRefused(
                    f"{error}\n{', '.join(services)} may still run with the demo's flags: run "
                    "make up, which restarts every service from .env."
                ) from None
            finally:
                shutil.rmtree(override.parent, ignore_errors=True)


def _wait_for_others(ours: Sequence[str], seconds: float, say: Callable[[str], None]) -> None:
    """Before the restart back: until no run but the demo's is being worked on, or `seconds`."""
    deadline = time.monotonic() + seconds
    while True:
        with db.connect(db.Role.APP) as conn:
            others = [str(r["run_id"]) for r in conn.execute(OTHERS_WORKING_SQL, (list(ours),))]
        if not others:
            return
        if time.monotonic() >= deadline:
            say(
                f"{len(others)} other run(s) still under way ({', '.join(others[:3])}): the "
                "restart back stops them now, and the reaper queues them again."
            )
            return
        say(f"Waiting for {len(others)} other run(s) under way before the restart back")
        time.sleep(2.0)


def _override_file(flags: dict[str, str], tag: str) -> Path:
    lines = ["services:"]
    for service in sorted(set(flags.values())):
        lines += [f"  {service}:", "    environment:", f'      {planted.TAG_VARIABLE}: "{tag}"']
        lines += [f'      {flag}: "1"' for flag, where in flags.items() if where == service]
    folder = Path(tempfile.mkdtemp(prefix="datapilot-demo-"))
    path = folder / "compose.demo.yaml"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def check_finale() -> None:
    """FinaleRefused unless the finale can show its moment: no planted flag on (in .env, this
    process's environment, or a running service), no promotion still pending, the kill switch
    released, the system at the unattended level (datapilot.finale)."""
    with db.connect(db.Role.APP) as conn:
        state = finale.read(conn, active_pack())
    here = planted.switched_on(env_file=planted.ENV_FILE, environ=os.environ)
    extra = tuple((flag, where) for flag, places in here.items() for where in places)
    reason = finale.refusal(replace(state, planted_on=extra + state.planted_on))
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
    row = conn.execute(BASELINE_SQL, {"pack": pack, "starting": STARTING_VERSION}).fetchone()
    baseline = (
        Baseline(str(row["experiment_id"]), row["knowledge_version"], row["started_at"])
        if row
        else None
    )
    active = conn.execute(ACTIVE_VERSION_SQL, (pack,)).fetchone()
    # With no baseline kept in the open session, the starting knowledge: a version promoted or made
    # active by the safeguard in an earlier session must not carry into the next class.
    keep_version = (
        baseline.knowledge_version if baseline and not discard_baseline else STARTING_VERSION
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
    exists = conn.execute(
        "SELECT 1 FROM ops.knowledge_versions WHERE pack = %s AND version = %s",
        (pack, keep_version),
    ).fetchone()
    # a pack without its starting knowledge loaded keeps its active version rather than none
    if exists and (active is None or active["version"] != keep_version):
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
