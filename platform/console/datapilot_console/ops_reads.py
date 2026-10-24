"""Every read the console makes, as the app role, from the ops schema. Live state only.

Small indexed reads, bound to the open live session: runs by (session_id, created_at), run events
by (run_id, id), experiments by (session_id, started_at). Nothing here formats a time; timestamps
stay aware datetimes and leave as UTC ISO strings for the browser. `watermark` is one cheap query
that changes whenever anything the pages show changes, so a page rebuilds its view only then.
Knowledge versions and experiments are the selected pack's (DATAPILOT_PACK).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import psycopg

from datapilot import finale
from datapilot.config import active_pack

Conn = psycopg.Connection[Any]

OPEN_SESSION = """
SELECT session_id, purpose, started_at, started_by, timezone
FROM ops.live_sessions WHERE ended_at IS NULL
"""
CONTROL = "SELECT kill_switch, autonomy_level, changed_at FROM ops.control WHERE id = 1"
# A family cleared under another knowledge version than the active one is not cleared now (the
# worker's rule, autonomy.OpsAutonomyPolicy.load); a row with no version is shown as it is.
FAMILIES = """
SELECT p.metric_family,
       CASE WHEN p.level = 'unattended' AND p.knowledge_version IS NOT NULL
                 AND p.knowledge_version IS DISTINCT FROM (
                     SELECT version FROM ops.knowledge_versions
                     WHERE pack = %(pack)s AND status = 'active')
            THEN 'assisted' ELSE p.level END AS level
FROM ops.autonomy_policy p
"""
# The class-day safeguard while its version is still the active one: the newest safeguard
# activation of the pack, with no promotion after it (versions.activate_verified).
SAFEGUARD = """
SELECT d.candidate_version, d.active_version, d.approved_by, d.decided_at, d.sentence
FROM ops.promotion_decisions d
JOIN ops.knowledge_versions k
  ON k.pack = d.pack AND k.version = d.candidate_version AND k.status = 'active'
WHERE d.pack = %(pack)s AND d.kind = 'safeguard'
  AND NOT EXISTS (SELECT 1 FROM ops.promotion_decisions newer WHERE newer.pack = d.pack
                  AND newer.verdict = 'promoted' AND newer.decision_id > d.decision_id)
ORDER BY d.decision_id DESC LIMIT 1
"""
# The newest budget row is the current Eastern time day; reading it avoids the system clock.
BUDGET = "SELECT day, token_limit, tokens_used FROM ops.budgets ORDER BY day DESC LIMIT 1"
LATEST_PLANTED = """
SELECT planted_active FROM ops.runs
WHERE session_id = %(session)s ORDER BY created_at DESC LIMIT 1
"""
WATERMARK = """
SELECT
  (SELECT max(e.id) FROM ops.run_events e) AS run_events,
  (SELECT max(p.post_id) FROM ops.posts p) AS posts,
  (SELECT max(a.approval_id)::text || coalesce(max(a.decided_at)::text, '')
     FROM ops.approvals a) AS approvals,
  (SELECT kill_switch || autonomy_level || changed_at::text FROM ops.control WHERE id = 1)
     AS control,
  (SELECT string_agg(metric_family || level, ',' ORDER BY metric_family)
     FROM ops.autonomy_policy) AS families,
  (SELECT tokens_used::text || '/' || token_limit::text FROM ops.budgets
     ORDER BY day DESC LIMIT 1) AS budget,
  (SELECT string_agg(version || status, ',' ORDER BY version) FROM ops.knowledge_versions
     WHERE pack = %(pack)s) AS versions,
  (SELECT string_agg(experiment_id::text || ':' || jsonb_array_length(per_example)::text || ':'
       || coalesce(finished_at::text, ''), ',' ORDER BY started_at)
     FROM ops.experiments WHERE session_id = %(session)s) AS experiments,
  (SELECT count(*) || ':' || coalesce(max(updated_at)::text, '') FROM ops.runs
     WHERE session_id = %(session)s) AS runs,
  (SELECT max(decision_id) FROM ops.promotion_decisions) AS gate,
  (SELECT max(id) FROM ops.event_duplicates) AS duplicates,
  (SELECT session_id::text FROM ops.live_sessions WHERE ended_at IS NULL) AS session
"""
BOARD_RUNS = """
SELECT r.run_id, r.event_id, r.demo_name, r.question, r.status, r.autonomy_level_applied,
       r.langsmith_url, r.created_at, r.started_at,
       (SELECT count(*) FROM ops.event_duplicates d WHERE d.event_id = r.event_id) AS duplicates
FROM ops.runs r
WHERE r.session_id = %(session)s AND r.event_id IS NOT NULL
ORDER BY r.created_at, r.run_id
"""
LAST_EVENTS = """
SELECT DISTINCT ON (run_id) run_id, kind, payload
FROM ops.run_events WHERE run_id = ANY(%(runs)s)
ORDER BY run_id, id DESC
"""
# The newest gold check of each run (the runner writes it after the answer, as a grader result).
BOARD_GOLD = """
SELECT DISTINCT ON (run_id) run_id, kind, payload
FROM ops.run_events
WHERE run_id = ANY(%(runs)s) AND kind = 'grader_result' AND payload ->> 'grader' = 'gold'
ORDER BY run_id, id DESC
"""
LATEST_RUN_FOR = """
SELECT run_id, event_id, demo_name, question, status, knowledge_version, model, tokens_in,
       tokens_out, cost_usd, langsmith_url, answer, created_at, started_at, finished_at
FROM ops.runs
WHERE session_id = %(session)s AND demo_name LIKE %(prefix)s
ORDER BY created_at DESC LIMIT 1
"""
RUN_BY_ID = """
SELECT run_id, event_id, demo_name, question, status, knowledge_version, model, tokens_in,
       tokens_out, cost_usd, langsmith_url, answer, created_at, started_at, finished_at
FROM ops.runs WHERE run_id = %(run)s AND session_id = %(session)s
"""
RUN_EVENTS = """
SELECT id, ts, kind, payload FROM ops.run_events WHERE run_id = %(run)s ORDER BY id
"""
OPEN_APPROVAL = """
SELECT a.approval_id, a.run_id, a.action, a.sql, a.row_estimate, a.reason, r.question
FROM ops.approvals a JOIN ops.runs r ON r.run_id = a.run_id
WHERE a.run_id = %(run)s AND a.decision IS NULL AND r.session_id = %(session)s
"""
POSTS = """
SELECT p.post_id, p.run_id, p.label, p.body, p.posted_at, r.autonomy_level_applied
FROM ops.posts p JOIN ops.runs r ON r.run_id = p.run_id
WHERE r.session_id = %(session)s
ORDER BY p.post_id DESC LIMIT %(limit)s
"""
EXPERIMENTS = """
SELECT e.experiment_id, e.knowledge_version, e.split, e.holdout_repeats, e.per_example,
       e.langsmith_url, e.started_at, e.finished_at, k.status AS version_status
FROM ops.experiments e
JOIN ops.knowledge_versions k ON k.pack = e.pack AND k.version = e.knowledge_version
WHERE e.session_id = %(session)s AND e.pack = %(pack)s
ORDER BY e.started_at, e.experiment_id
"""
# A version the analyzer request kept from its candidates carries that choice's sentence.
VERSIONS = """
SELECT k.version, k.yaml, k.status, k.created_at, k.approved_by,
       (SELECT c.sentence FROM ops.analyzer_candidates c
        WHERE c.pack = k.pack AND c.saved_as = k.version AND c.chosen
        ORDER BY c.created_at DESC, c.candidate_id DESC LIMIT 1) AS selection
FROM ops.knowledge_versions k
WHERE k.pack = %(pack)s ORDER BY k.created_at, k.version
"""
# The gate's own sentence for a candidate, decided during the open session.
GATE_DECISION = """
SELECT verdict, sentence, decided_at FROM ops.promotion_decisions
WHERE pack = %(pack)s AND candidate_version = %(version)s AND decided_at >= %(since)s
ORDER BY decided_at DESC LIMIT 1
"""
# The newest promotion during the open session: the gate's, or the class-day safeguard's (kind).
LAST_PROMOTION = """
SELECT candidate_version, active_version, approved_by, decided_at, kind
FROM ops.promotion_decisions
WHERE pack = %(pack)s AND verdict = 'promoted' AND decided_at >= %(since)s
ORDER BY decided_at DESC, decision_id DESC LIMIT 1
"""


def open_session(conn: Conn) -> dict[str, Any] | None:
    return conn.execute(OPEN_SESSION).fetchone()


def watermark(conn: Conn, session_id: Any) -> tuple[Any, ...]:
    row = conn.execute(WATERMARK, {"session": session_id, "pack": active_pack()}).fetchone()
    return tuple(row.values()) if row else ()


def family_levels(conn: Conn) -> dict[str, str]:
    """Each metric family's autonomy level, as the status line shows it."""
    rows = conn.execute(FAMILIES, {"pack": active_pack()}).fetchall()
    return {r["metric_family"]: r["level"] for r in rows}


def status(conn: Conn, session_id: Any | None) -> dict[str, Any]:
    """What the status line shows: control, clearance per family, tokens, planted items."""
    control = conn.execute(CONTROL).fetchone() or {
        "kill_switch": "released",
        "autonomy_level": "report_only",
    }
    families = family_levels(conn)
    safeguard = conn.execute(SAFEGUARD, {"pack": active_pack()}).fetchone()
    budget = conn.execute(BUDGET).fetchone()
    planted: list[str] = []
    if session_id is not None:
        row = conn.execute(LATEST_PLANTED, {"session": session_id}).fetchone()
        planted = list(row["planted_active"]) if row else []
    return {
        "kill_switch": control["kill_switch"],
        "autonomy_level": control["autonomy_level"],
        "family_levels": families,
        "tokens_used": int(budget["tokens_used"]) if budget else 0,
        "token_limit": int(budget["token_limit"]) if budget else None,
        "planted_active": planted,
        "safeguard": safeguard,
    }


def board_runs(conn: Conn, session_id: Any) -> list[dict[str, Any]]:
    """Every event-loop run of the session (oldest first) with its newest run event and its gold
    check, when it has one."""
    runs = conn.execute(BOARD_RUNS, {"session": session_id}).fetchall()
    if not runs:
        return []
    ids = {"runs": [r["run_id"] for r in runs]}
    last = {r["run_id"]: r for r in conn.execute(LAST_EVENTS, ids).fetchall()}
    gold = {r["run_id"]: r for r in conn.execute(BOARD_GOLD, ids).fetchall()}
    return [
        {**run, "last_event": last.get(run["run_id"]), "gold_event": gold.get(run["run_id"])}
        for run in runs
    ]


def latest_run(conn: Conn, session_id: Any, prefix: str) -> dict[str, Any] | None:
    """The newest run of the session whose demo name starts with `prefix` (agent-, verify-)."""
    return conn.execute(LATEST_RUN_FOR, {"session": session_id, "prefix": f"{prefix}%"}).fetchone()


def run_by_id(conn: Conn, session_id: Any, run_id: str) -> dict[str, Any] | None:
    return conn.execute(RUN_BY_ID, {"session": session_id, "run": run_id}).fetchone()


def run_events(conn: Conn, run_id: Any) -> list[dict[str, Any]]:
    return conn.execute(RUN_EVENTS, {"run": run_id}).fetchall()


def open_approval(conn: Conn, session_id: Any, run_id: str) -> dict[str, Any] | None:
    return conn.execute(OPEN_APPROVAL, {"session": session_id, "run": run_id}).fetchone()


def posts(conn: Conn, session_id: Any, limit: int = 5) -> list[dict[str, Any]]:
    return conn.execute(POSTS, {"session": session_id, "limit": limit}).fetchall()


def experiments(conn: Conn, session_id: Any) -> list[dict[str, Any]]:
    return conn.execute(EXPERIMENTS, {"session": session_id, "pack": active_pack()}).fetchall()


def knowledge_versions(conn: Conn) -> list[dict[str, Any]]:
    return conn.execute(VERSIONS, {"pack": active_pack()}).fetchall()


def gate_decision(conn: Conn, version: str, since: datetime) -> dict[str, Any] | None:
    params = {"pack": active_pack(), "version": version, "since": since}
    return conn.execute(GATE_DECISION, params).fetchone()


def finale_state(conn: Conn) -> finale.FinaleState:
    """The kill switch, the system's level, and an approved version whose promotion is pending:
    what Events > Send webhook question checks before it sends the finale (datapilot.finale)."""
    return finale.read(conn, active_pack())


def last_promotion(conn: Conn, since: datetime) -> dict[str, Any] | None:
    return conn.execute(LAST_PROMOTION, {"pack": active_pack(), "since": since}).fetchone()
