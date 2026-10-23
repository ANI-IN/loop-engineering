"""The autonomy policy: which level applies to a run, what it may post, and when to demote.

- report-only level: answers are posted labelled unverified; exports are never released.
- assisted level: answers are posted; personal data and exports need human approval.
- unattended level: posted without approval, only for metric families that are eligible: cleared
  by the hill-climbing loop on the gate's confirmed standard under the active knowledge version,
  every holdout item of the family passes 2 of 3 runs, an item that fell short passing 2 of 3 more
  runs (eligibility.confirmed_clearance), as recorded in ops.autonomy_policy (mark_eligible).
  Other families get the assisted level. After the class-day safeguard activates a version verified
  in rehearsal (versions.activate_verified), a family it had cleared in rehearsal is eligible under
  it with a note saying so (mark_cleared_in_rehearsal), and that note travels with every answer
  posted at the unattended level (clearance_note).
Demotion to the report-only level: a holdout regression, the daily budget exhausted, consecutive
escalations (pack autonomy.demote_after_consecutive_escalations), or the kill switch.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

import psycopg

from datapilot.config import pack_config
from datapilot.contracts import AutonomyLevel, DemotionReason

LABELS = {
    AutonomyLevel.REPORT_ONLY: "unverified",
    AutonomyLevel.ASSISTED: "verified",
    AutonomyLevel.UNATTENDED: "unattended",
}


@dataclass(frozen=True)
class OpsAutonomyPolicy:
    """Implements contracts.AutonomyPolicy from ops.control and ops.autonomy_policy."""

    global_level: AutonomyLevel
    active_knowledge: str
    eligible: frozenset[str] = field(default_factory=frozenset)
    notes: dict[str, str] = field(default_factory=dict)  # family -> where its clearance came from

    @classmethod
    def load(cls, conn: psycopg.Connection[Any], active_knowledge: str) -> OpsAutonomyPolicy:
        level = conn.execute("SELECT autonomy_level FROM ops.control WHERE id = 1").fetchone()
        rows = conn.execute(
            "SELECT metric_family, reason FROM ops.autonomy_policy "
            "WHERE level = 'unattended' AND knowledge_version = %s",
            (active_knowledge,),
        ).fetchall()
        return cls(
            global_level=AutonomyLevel(level["autonomy_level"]),
            active_knowledge=active_knowledge,
            eligible=frozenset(r["metric_family"] for r in rows),
            notes={r["metric_family"]: r["reason"] for r in rows if r["reason"]},
        )

    def clearance_note(self, metric_family: str | None) -> str | None:
        """Where an unattended answer's clearance came from, when it was not this session's gate:
        the class-day safeguard's "cleared in rehearsal on ..." note."""
        if self.level_for(metric_family) is not AutonomyLevel.UNATTENDED:
            return None
        return self.notes.get(metric_family or "")

    def level_for(self, metric_family: str | None) -> AutonomyLevel:
        if self.global_level is not AutonomyLevel.UNATTENDED:
            return self.global_level
        if metric_family in self.eligible:
            return AutonomyLevel.UNATTENDED
        return AutonomyLevel.ASSISTED

    def needs_approval(self, metric_family: str | None, *, personal_data: bool) -> bool:
        return personal_data and self.level_for(metric_family) is not AutonomyLevel.REPORT_ONLY


Decision = Literal["post", "approve_first"]


def posting_decision(
    policy: OpsAutonomyPolicy,
    metric_family: str | None,
    *,
    personal_data: bool,
    export: bool,
    approved: bool,
) -> Decision:
    if approved:
        return "post"
    if policy.needs_approval(metric_family, personal_data=personal_data or export):
        return "approve_first"
    return "post"


def demote(
    conn: psycopg.Connection[Any],
    reason: DemotionReason,
    *,
    family: str | None = None,
    by: str = "system",
) -> None:
    """Drop to the report-only level: one family, or the whole system."""
    if family is None:
        conn.execute(
            "UPDATE ops.control SET autonomy_level = 'report_only', changed_at = now(), "
            "changed_by = %s, reason = %s WHERE id = 1",
            (by, reason.value),
        )
        return
    conn.execute(
        "INSERT INTO ops.autonomy_policy (metric_family, level, demoted_at, reason) "
        "VALUES (%s, 'report_only', now(), %s) ON CONFLICT (metric_family) DO UPDATE SET "
        "level = 'report_only', demoted_at = now(), reason = EXCLUDED.reason",
        (family, reason.value),
    )


def mark_eligible(conn: psycopg.Connection[Any], family: str, knowledge_version: str) -> None:
    """Called by the hill-climbing loop when a family is cleared on the gate's confirmed standard:
    every holdout item of the family passes 2 of 3 runs, an item that fell short passing 2 of 3
    more runs (eligibility.confirmed_clearance)."""
    conn.execute(
        "INSERT INTO ops.autonomy_policy (metric_family, level, eligible_since, knowledge_version) "
        "VALUES (%s, 'unattended', now(), %s) ON CONFLICT (metric_family) DO UPDATE SET "
        "level = 'unattended', eligible_since = now(), "
        "knowledge_version = EXCLUDED.knowledge_version, "
        "reason = NULL",
        (family, knowledge_version),
    )


def mark_cleared_in_rehearsal(
    conn: psycopg.Connection[Any], family: str, knowledge_version: str, note: str
) -> None:
    """The class-day safeguard's eligibility: `family` was cleared under `knowledge_version` on the
    gate's confirmed standard in rehearsal (eligibility.confirmed_clearance there, recorded with
    the version's rehearsal verification); the note says so wherever the level is shown."""
    conn.execute(
        "INSERT INTO ops.autonomy_policy (metric_family, level, eligible_since, knowledge_version, "
        "reason) VALUES (%s, 'unattended', now(), %s, %s) ON CONFLICT (metric_family) DO UPDATE "
        "SET level = 'unattended', eligible_since = now(), "
        "knowledge_version = EXCLUDED.knowledge_version, reason = EXCLUDED.reason",
        (family, knowledge_version, note),
    )


def demote_after_escalations(conn: psycopg.Connection[Any]) -> bool:
    """Demote when the last N finished runs were all escalated."""
    limit = int(pack_config()["autonomy"]["demote_after_consecutive_escalations"])
    rows = conn.execute(
        "SELECT status FROM ops.runs WHERE finished_at IS NOT NULL "
        "AND status IN ('posted', 'escalated', 'rejected', 'failed') "
        "ORDER BY finished_at DESC LIMIT %s",
        (limit,),
    ).fetchall()
    if len(rows) == limit and all(r["status"] == "escalated" for r in rows):
        demote(conn, DemotionReason.CONSECUTIVE_ESCALATIONS)
        return True
    return False
