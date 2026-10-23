"""Knowledge versions in ops.knowledge_versions: the hill-climbing loop's knowledge store.

The pack ships v1 (the starting knowledge) and the over-broad rule's version as files; `install`
copies them into ops once and makes v1 active when no version is. Candidate versions from the
analyzer team are saved as drafts; the promotion gate activates one only after human approval.
Every row belongs to one pack: each query here reads and writes the selected pack's versions only.

The class-day safeguard lives here too (verify_in_rehearsal, activate_verified): a version verified
in rehearsal by a correct live finale can be made active in class through the same `activate`.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

import psycopg
import yaml

from datapilot.config import active_pack
from datapilot.contracts import KnowledgeVersion
from datapilot.loop4_hill_climbing.pack_files import load_knowledge, pack_root

STARTING_VERSION = "v1"
OVERBROAD_VERSION = "v2-overbroad"
_NUMBERED = re.compile(r"^v(\d+)")

INSERT_VERSION = """
INSERT INTO ops.knowledge_versions (pack, version, yaml, status, created_by)
VALUES (%(pack)s, %(version)s, %(yaml)s, %(status)s, %(created_by)s)
ON CONFLICT (pack, version) DO NOTHING
"""
ACTIVE = "SELECT version FROM ops.knowledge_versions WHERE pack = %s AND status = 'active'"
ONE = (
    "SELECT version, yaml, status, approved_by FROM ops.knowledge_versions "
    "WHERE pack = %s AND version = %s"
)
RETIRE_ACTIVE = (
    "UPDATE ops.knowledge_versions SET status = 'retired' WHERE pack = %s AND status = 'active'"
)
MAKE_ACTIVE = (
    "UPDATE ops.knowledge_versions SET status = 'active', activated_at = now() "
    "WHERE pack = %s AND version = %s"
)


def shipped() -> list[str]:
    return sorted(path.stem for path in (pack_root() / "knowledge").glob("*.yaml"))


def to_yaml(version: KnowledgeVersion) -> str:
    return yaml.safe_dump(version.model_dump(), sort_keys=False, allow_unicode=True)


def install(conn: psycopg.Connection[Any]) -> list[str]:
    """Copy the pack's shipped versions into ops; activate v1 when nothing of this pack is active.
    Returns the versions added."""
    pack, added = active_pack(), []
    for name in shipped():
        inserted = conn.execute(
            INSERT_VERSION,
            {
                "pack": pack,
                "version": name,
                "yaml": to_yaml(load_knowledge(name)),
                "status": "retired",
                "created_by": "pack",
            },
        ).rowcount
        if inserted:
            added.append(name)
    if conn.execute(ACTIVE, (pack,)).fetchone() is None:
        conn.execute(MAKE_ACTIVE, (pack, STARTING_VERSION))
    return added


def get(conn: psycopg.Connection[Any], name: str) -> KnowledgeVersion:
    row = conn.execute(ONE, (active_pack(), name)).fetchone()
    if row is None:
        return load_knowledge(name)  # a shipped file not installed yet
    data = yaml.safe_load(row["yaml"]) or {}
    return KnowledgeVersion.model_validate({**data, "version": name})


def active_name(conn: psycopg.Connection[Any]) -> str:
    row = conn.execute(ACTIVE, (active_pack(),)).fetchone()
    return row["version"] if row else STARTING_VERSION


def status_of(conn: psycopg.Connection[Any], name: str) -> dict[str, Any] | None:
    return conn.execute(ONE, (active_pack(), name)).fetchone()


def latest_candidate(conn: psycopg.Connection[Any]) -> str | None:
    """The newest draft or approved version that is not shipped with the pack."""
    row = conn.execute(
        "SELECT version FROM ops.knowledge_versions WHERE pack = %s "
        "AND status IN ('draft', 'approved') AND version <> ALL(%s) "
        "ORDER BY created_at DESC, version DESC LIMIT 1",
        (active_pack(), shipped()),
    ).fetchone()
    return row["version"] if row else None


def next_name(conn: psycopg.Connection[Any]) -> str:
    """v2, v3, ...: one more than the highest numbered version of the pack, in ops or shipped."""
    rows = conn.execute(
        "SELECT version FROM ops.knowledge_versions WHERE pack = %s", (active_pack(),)
    )
    names = [r["version"] for r in rows]
    numbers = [int(m.group(1)) for n in [*names, *shipped()] if (m := _NUMBERED.match(n))]
    return f"v{max(numbers, default=1) + 1}"


def save_draft(
    conn: psycopg.Connection[Any], version: KnowledgeVersion, *, created_by: str
) -> None:
    conn.execute(
        INSERT_VERSION,
        {
            "pack": active_pack(),
            "version": version.version,
            "yaml": to_yaml(version),
            "status": "draft",
            "created_by": created_by,
        },
    )


def with_rules_of(base: KnowledgeVersion, extra: KnowledgeVersion, name: str) -> KnowledgeVersion:
    """`base` plus every rule of `extra` it does not have (the active version plus the over-broad
    rule)."""
    have = {rule.id for rule in base.rules}
    rules = [*base.rules, *(rule for rule in extra.rules if rule.id not in have)]
    notes = f"{base.version} plus the rules of {extra.version}."
    return KnowledgeVersion(version=name, rules=rules, notes=notes)


def activate(conn: psycopg.Connection[Any], name: str) -> None:
    """The gate's last step, after human approval: the version becomes the pack's active one."""
    pack = active_pack()
    conn.execute(RETIRE_ACTIVE, (pack,))
    conn.execute(MAKE_ACTIVE, (pack, name))


# --- the class-day safeguard ------------------------------------------------------------------
# If the version promoted live in class gives a wrong finale answer, the finale runs live on the
# version promoted and verified in rehearsal. Rehearsal marks that version (verify_in_rehearsal);
# in class one command activates it through `activate` above and records a safeguard activation
# in ops.promotion_decisions beside the gate's own decisions, which stay as they are. Its metric
# families get the level they earned under its own clearance record in rehearsal, never more.
FINALE_DEMO = "improve-cleared-unattended"
FINALE_RUN = """
SELECT r.run_id, r.question, r.status, r.knowledge_version, r.autonomy_level_applied,
       r.langsmith_url, r.session_id, s.purpose
FROM ops.runs r LEFT JOIN ops.live_sessions s ON s.session_id = r.session_id
WHERE r.run_id = %s
"""
GOLD_CHECK = """
SELECT payload FROM ops.run_events
WHERE run_id = %s AND kind = 'grader_result' AND payload ->> 'grader' = 'gold'
ORDER BY id DESC LIMIT 1
"""
CLEARED_UNDER = """
SELECT metric_family FROM ops.autonomy_policy
WHERE level = 'unattended' AND knowledge_version = %s ORDER BY metric_family
"""
INSERT_VERIFICATION = """
INSERT INTO ops.rehearsal_verifications (pack, version, verified_by, session_id, finale_run_id,
    finale_question, finale_level, agent_value, gold_value, langsmith_url, cleared_families)
VALUES (%(pack)s, %(version)s, %(verified_by)s, %(session_id)s, %(run_id)s, %(question)s,
    %(level)s, %(agent_value)s, %(gold_value)s, %(langsmith_url)s, %(families)s)
RETURNING verified_at
"""
LATEST_VERIFICATION = """
SELECT version, verified_by, verified_at, session_id, finale_run_id, finale_question,
       finale_level, agent_value, gold_value, langsmith_url, cleared_families
FROM ops.rehearsal_verifications
WHERE pack = %(pack)s AND (%(version)s::text IS NULL OR version = %(version)s)
ORDER BY verified_at DESC, verification_id DESC LIMIT 1
"""
INSERT_SAFEGUARD_DECISION = """
INSERT INTO ops.promotion_decisions (pack, candidate_version, active_version, verdict, reasons,
    sentence, approved_by, kind)
VALUES (%(pack)s, %(version)s, %(replaced)s, 'promoted', %(reasons)s, %(sentence)s, %(by)s,
    'safeguard')
RETURNING decision_id
"""


class SafeguardRefused(ValueError):
    """The safeguard will not mark or activate a version: the reason is the message."""


@dataclass(frozen=True)
class RehearsalVerification:
    version: str
    verified_by: str
    verified_at: datetime
    session_id: str
    finale_run_id: str
    finale_question: str
    finale_level: str
    agent_value: str | None
    gold_value: str | None
    langsmith_url: str | None
    cleared_families: list[str]

    def describe(self) -> str:
        families = ", ".join(self.cleared_families) or "none"
        return (
            f"{self.version}: verified in rehearsal by {self.verified_by} at "
            f"{self.verified_at.isoformat(timespec='seconds')}, finale run {self.finale_run_id} "
            f"answered {self.agent_value} (gold {self.gold_value}) at the "
            f"{self.finale_level.replace('_', '-')} level; families cleared then: {families}"
        )


@dataclass(frozen=True)
class SafeguardActivation:
    decision_id: int
    version: str
    replaced: str
    activated_by: str
    verification: RehearsalVerification
    sentence: str


def _verification(row: dict[str, Any]) -> RehearsalVerification:
    return RehearsalVerification(
        version=row["version"],
        verified_by=row["verified_by"],
        verified_at=row["verified_at"],
        session_id=str(row["session_id"]),
        finale_run_id=str(row["finale_run_id"]),
        finale_question=row["finale_question"],
        finale_level=row["finale_level"],
        agent_value=row["agent_value"],
        gold_value=row["gold_value"],
        langsmith_url=row["langsmith_url"],
        cleared_families=list(row["cleared_families"] or []),
    )


def verify_in_rehearsal(
    conn: psycopg.Connection[Any], name: str, run_id: str, *, verified_by: str
) -> RehearsalVerification:
    """Mark `name` verified in rehearsal by its finale run `run_id`. Refused unless the run is a
    finale run (the spine question) of a rehearsal session, answered under `name`, posted, and its
    gold check passed. The families cleared under `name` then (ops.autonomy_policy) are recorded
    with it: the level its family earned, kept for class day."""
    from datapilot.demo_questions import QUESTIONS

    pack = active_pack()
    if status_of(conn, name) is None:
        raise SafeguardRefused(f"{name} is not a knowledge version of the pack {pack}")
    try:
        run_uuid = UUID(run_id)
    except ValueError as error:
        raise SafeguardRefused(f"{run_id!r} is not a run id") from error
    run = conn.execute(FINALE_RUN, (run_uuid,)).fetchone()
    if run is None:
        raise SafeguardRefused(f"no run {run_id} in ops.runs")
    problems = []
    if run["purpose"] != "rehearsal":
        problems.append(f"its live session is {run['purpose'] or 'unknown'}, not a rehearsal")
    if run["question"] != QUESTIONS[FINALE_DEMO]:
        problems.append("it is not the finale question")
    if run["knowledge_version"] != name:
        problems.append(f"it ran under {run['knowledge_version'] or 'no version'}, not {name}")
    if run["status"] != "posted" or not run["autonomy_level_applied"]:
        problems.append(f"it was not posted (status {run['status']})")
    gold = conn.execute(GOLD_CHECK, (run_uuid,)).fetchone()
    payload = gold["payload"] if gold else {}
    if not gold:
        problems.append("it has no gold check yet")
    elif payload.get("passed") is not True:
        problems.append(f"its gold check failed ({payload.get('reason') or 'no reason'})")
    if problems:
        raise SafeguardRefused(f"run {run_id} cannot verify {name}: " + "; ".join(problems))
    families = [r["metric_family"] for r in conn.execute(CLEARED_UNDER, (name,)).fetchall()]
    values = {
        "pack": pack,
        "version": name,
        "verified_by": verified_by,
        "session_id": run["session_id"],
        "run_id": run_uuid,
        "question": run["question"],
        "level": run["autonomy_level_applied"],
        "agent_value": payload.get("agent_value"),
        "gold_value": payload.get("gold_value"),
        "langsmith_url": run["langsmith_url"],
        "families": families,
    }
    stamped = conn.execute(INSERT_VERIFICATION, values).fetchone()
    return _verification(
        {
            **values,
            "verified_at": stamped["verified_at"],
            "finale_run_id": run_uuid,
            "finale_question": run["question"],
            "finale_level": run["autonomy_level_applied"],
            "cleared_families": families,
        }
    )


def latest_verification(
    conn: psycopg.Connection[Any], name: str | None = None
) -> RehearsalVerification | None:
    """The newest rehearsal verification of the pack, or of one version."""
    row = conn.execute(LATEST_VERIFICATION, {"pack": active_pack(), "version": name}).fetchone()
    return _verification(row) if row else None


def activate_verified(
    conn: psycopg.Connection[Any], *, activated_by: str, name: str | None = None
) -> SafeguardActivation:
    """The class-day safeguard: make the version verified in rehearsal (the newest, or `name`)
    active through `activate`, record a safeguard activation in ops.promotion_decisions, and give
    each family it had cleared in rehearsal the unattended level under it, noted as cleared in
    rehearsal. A family it had not cleared gets no clearance under it. Nothing of the gate's own
    record changes: the class candidate's experiments and decisions stay."""
    from datapilot.loop3_events import autonomy

    found = latest_verification(conn, name)
    if found is None:
        raise SafeguardRefused(
            "no knowledge version is verified in rehearsal"
            + (f" under the name {name}" if name else "")
            + ": mark one with `datapilot safeguard verify` during rehearsal"
        )
    replaced = active_name(conn)
    if replaced == found.version:
        raise SafeguardRefused(f"{found.version} is already the active version")
    activate(conn, found.version)
    day = found.verified_at.date().isoformat()
    note = (
        f"cleared in rehearsal on {day} (live session {found.session_id}); carried by the "
        "class-day safeguard"
    )
    for family in found.cleared_families:
        autonomy.mark_cleared_in_rehearsal(conn, family, found.version, note)
    families = ", ".join(found.cleared_families) or "none"
    sentence = (
        f"Safeguard activation: {found.version}, verified in rehearsal by {found.verified_by} on "
        f"{day} (finale run {found.finale_run_id[:8]}), replaces {replaced} for the finale; "
        f"families with the level they earned in rehearsal: {families}."
    )
    reasons = [
        f"safeguard: {replaced}, promoted by the gate in class, gave a wrong finale answer",
        f"verified in rehearsal: {found.describe()}",
        f"activated by {activated_by}; the gate's decisions on {replaced} are kept as they are",
    ]
    stamped = conn.execute(
        INSERT_SAFEGUARD_DECISION,
        {
            "pack": active_pack(),
            "version": found.version,
            "replaced": replaced,
            "reasons": json.dumps(reasons),
            "sentence": sentence,
            "by": activated_by,
        },
    ).fetchone()
    return SafeguardActivation(
        decision_id=int(stamped["decision_id"]),
        version=found.version,
        replaced=replaced,
        activated_by=activated_by,
        verification=found,
        sentence=sentence,
    )
