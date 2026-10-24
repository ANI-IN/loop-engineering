"""Two-candidate selection on the dev split: the analyzer team's output varies from run to run.

From the same failed dev items the analyzer team writes analyzer.candidates rule sets (pack.yaml),
each by its own run of the failure analyst, the rule writer, and the critic, through the overfit
guard. Each candidate runs on the dev split only, every item once, under its own retired version,
and is compared with the active version's dev results in the session's baseline experiment. The
runner keeps one by these keys, in order: fewer dev regressions, then more dev passes, then fewer
rules; on a full tie, the first written. The holdout split never takes part in the choice: only the
kept candidate goes to the candidate experiment and the gate, so the holdout still measures
questions no decision was tuned on. A dev regression here is apparent, from one run; the gate
confirms regressions of the kept candidate with its own re-runs.

Every candidate is recorded in ops.analyzer_candidates with the sentence the Improve page shows,
such as "Candidate A: 14 of 25 dev, 0 regressions, 7 rules; Candidate B: 12 of 25 dev,
1 regression, 8 rules; chosen: A".
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

import psycopg

from datapilot.config import active_pack, pack_config
from datapilot.contracts import KnowledgeVersion, Split
from datapilot.loop4_hill_climbing import versions
from datapilot.loop4_hill_climbing.analyzer import AnalyzerReport
from datapilot.loop4_hill_climbing.experiment import ExperimentResult

INSERT_CANDIDATE = """
INSERT INTO ops.analyzer_candidates (pack, session_id, request_id, from_version, saved_as, label,
    candidate_version, chosen, naive, dev_passes, dev_total, dev_regressions, rules, guard_flags,
    sentence)
VALUES (%(pack)s, %(session_id)s, %(request_id)s, %(from_version)s, %(saved_as)s, %(label)s,
    %(candidate_version)s, %(chosen)s, %(naive)s, %(dev_passes)s, %(dev_total)s,
    %(dev_regressions)s, %(rules)s, %(guard_flags)s, %(sentence)s)
"""


def count() -> int:
    """How many candidates one analyzer request writes; a pack without the setting writes one."""
    return max(1, int((pack_config().get("analyzer") or {}).get("candidates", 1)))


def label(index: int) -> str:
    return chr(ord("A") + index)


@dataclass
class CandidateRun:
    """One candidate rule set of an analyzer request and its dev-only measurement."""

    label: str
    version: str  # the version it ran under: "v7-candidate-a", or the draft itself when alone
    report: AnalyzerReport
    dev: ExperimentResult | None = None
    regressions: list[str] = field(default_factory=list)

    @property
    def dev_passes(self) -> int:
        return self.dev.passes(Split.DEV) if self.dev else 0

    @property
    def dev_total(self) -> int:
        return self.dev.total(Split.DEV) if self.dev else 0

    @property
    def rules(self) -> int:
        return len(self.report.accepted)

    @property
    def guard_flags(self) -> int:
        return sum(1 for g in self.report.guard if not g.passed)

    def as_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "version": self.version,
            "dev_passes": self.dev_passes if self.dev else None,
            "dev_total": self.dev_total if self.dev else None,
            "dev_regressions": self.regressions,
            "rules": self.rules,
        }


def selection_version(name: str, index: int) -> str:
    return f"{name}-candidate-{label(index).lower()}"


def dev_regressions(baseline: ExperimentResult, dev: ExperimentResult) -> list[str]:
    """Dev items that passed in the baseline and fail under the candidate, from one run each."""
    return [
        item_id
        for item_id, result in dev.results.items()
        if dev.splits_by_item[item_id] is Split.DEV
        and item_id in baseline.results
        and baseline.passed(item_id)
        and not result.passed
    ]


def choose(candidates: Sequence[CandidateRun]) -> CandidateRun:
    """Fewer dev regressions, then more dev passes, then fewer rules; the first one on a tie."""
    if not candidates:
        raise ValueError("no candidate to choose from")
    return min(candidates, key=lambda c: (len(c.regressions), -c.dev_passes, c.rules))


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def sentence(candidates: Sequence[CandidateRun], chosen: CandidateRun, *, naive: bool) -> str:
    if naive:
        flags = chosen.guard_flags
        return (
            f"Naive analyzer: {_plural(chosen.rules, 'rule')}, no critic; the overfit guard flags "
            f"{flags} of {chosen.rules}, not applied."
        )
    if len(candidates) == 1 and chosen.dev is None:
        return f"One candidate: {_plural(chosen.rules, 'rule')}."
    parts = [
        f"Candidate {c.label}: {c.dev_passes} of {c.dev_total} dev, "
        f"{_plural(len(c.regressions), 'regression')}, {_plural(c.rules, 'rule')}"
        for c in candidates
    ]
    return "; ".join([*parts, f"chosen: {chosen.label}"])


def save_selection_draft(conn: psycopg.Connection[Any], version: KnowledgeVersion) -> None:
    """A candidate's rules under its own name, retired at once: the target can answer under it,
    and it is never offered for approval or taken for the newest candidate."""
    created_by = "analyzer team, a candidate for the dev selection"
    versions.insert_new(conn, version, status="retired", created_by=created_by)


def save(
    conn: psycopg.Connection[Any],
    candidates: Sequence[CandidateRun],
    chosen: CandidateRun,
    *,
    session_id: UUID | None,
    request_id: UUID | str | None,
    from_version: str,
    saved_as: str,
    naive: bool,
) -> str:
    """One row per candidate, the kept one marked chosen; returns the sentence."""
    said = sentence(candidates, chosen, naive=naive)
    for candidate in candidates:
        conn.execute(
            INSERT_CANDIDATE,
            {
                "pack": active_pack(),
                "session_id": session_id,
                "request_id": request_id,
                "from_version": from_version,
                "saved_as": saved_as,
                "label": candidate.label,
                "candidate_version": candidate.version,
                "chosen": candidate is chosen,
                "naive": naive,
                "dev_passes": candidate.dev_passes if candidate.dev else None,
                "dev_total": candidate.dev_total if candidate.dev else None,
                "dev_regressions": candidate.regressions,
                "rules": candidate.rules,
                "guard_flags": candidate.guard_flags,
                "sentence": said,
            },
        )
    return said
