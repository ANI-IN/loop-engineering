"""The hill-climbing runner: the process that serves the console's Improve page.

It implements loop3_events.improvement.ImprovementRunner. The api only records requests; this
process claims them and runs them live:

- an experiment request runs the benchmark under the named version (the active one, the newest
  candidate, or the active one plus the over-broad rule), writing each item to ops.experiments as
  it finishes; a version other than the active one then goes through the promotion gate against
  this session's experiment of the active version, apparent regressions confirmed step by step;
- an analyzer request runs the analyzer team on the failed dev items of this session's experiment
  of the active version and saves the candidate as a draft for human approval. With
  analyzer.candidates above one (pack.yaml), the team writes that many candidates, each runs on the
  dev split only, and one is kept (candidates.choose); the holdout split never takes part.

Between requests it promotes an approved candidate whose gate was ready, and writes the gold check
of every live run that answered a benchmark question. A promotion's last step clears metric families
for the unattended level on the gate's own confirmed standard (eligibility.confirmed_clearance):
every holdout item of the family passes 2 of 3 runs, an item that fell short passing 2 of 3 more.
"""

from __future__ import annotations

import threading
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import psycopg
import structlog

from datapilot import db
from datapilot.config import active_pack, pack_config
from datapilot.contracts import (
    AnswerEnvelope,
    AnswerStatus,
    BenchmarkItem,
    KnowledgeVersion,
    Split,
)
from datapilot.contracts.live import NoLiveBaseline
from datapilot.loop3_events import autonomy, improvement
from datapilot.loop4_hill_climbing import candidates, eligibility, gold, store, versions
from datapilot.loop4_hill_climbing.analyzer import (
    AnalyzerReport,
    AnalyzerTeam,
    FailedItem,
    live_team,
)
from datapilot.loop4_hill_climbing.evaluator import ExecutionEvaluator
from datapilot.loop4_hill_climbing.experiment import (
    ExperimentResult,
    ExperimentRunner,
    RunTracer,
    Target,
)
from datapilot.loop4_hill_climbing.gate import GateDecision, Regressions, decide, find_regressions
from datapilot.loop4_hill_climbing.measurement import Scheme
from datapilot.loop4_hill_climbing.overfit_guard import OverfitGuard, new_rule_flags
from datapilot.planted import planted

log = structlog.get_logger("hill_climbing_runner")

SPLITS = {"dev": [Split.DEV], "holdout": [Split.HOLDOUT], "all": [Split.DEV, Split.HOLDOUT]}
OVERBROAD = "over-broad"
SESSION_STARTED = "SELECT started_at FROM ops.live_sessions WHERE ended_at IS NULL"


class RequestFailed(RuntimeError):
    """A request that cannot run, with the sentence the console shows."""


@dataclass
class HillClimbingRunner:
    items: Sequence[BenchmarkItem]
    target: Target
    evaluator: ExecutionEvaluator
    scheme: Scheme
    concurrency: int
    tracer: RunTracer | None = None
    project_url: str | None = None

    # --- requests (improvement.ImprovementRunner) -----------------------------------------------
    def run(self, request: dict[str, Any]) -> dict[str, Any]:
        session_id = request.get("session_id")
        if session_id is None:
            raise RequestFailed("no live session was open when this was requested")
        params = dict(request.get("params") or {})
        if request["kind"] == "analyzer":
            return self.analyzer(session_id, request.get("request_id"))
        return self.experiment(params, session_id)

    def experiment(self, params: dict[str, Any], session_id: UUID) -> dict[str, Any]:
        with db.connect(db.Role.APP) as conn:
            active = versions.active_name(conn)
            name = self._version_for(conn, params, active)
            conn.commit()
        runner = self._runner()
        result = runner.run(
            self.items, name, session_id=session_id, splits=SPLITS[params.get("split") or "all"]
        )
        with db.connect(db.Role.APP) as conn:
            store.finish_experiment(conn, result, langsmith_url=self.project_url)
            conn.commit()
        summary = experiment_summary(result)
        if name != active:
            decision = self.gate(result, active, runner)
            summary |= {
                "verdict": decision.verdict,
                "ready_for_approval": decision.ready_for_approval,
                "sentence": decision.sentence,
                "reasons": decision.reasons,
            }
        return summary

    def analyzer(self, session_id: UUID, request_id: UUID | str | None = None) -> dict[str, Any]:
        with db.connect(db.Role.APP) as conn:
            active = versions.active_name(conn)
            try:
                baseline = store.baseline_for(conn, active)
            except NoLiveBaseline as error:
                raise RequestFailed(str(error)) from error
            knowledge = versions.get(conn, active)
            name = versions.next_name(conn)
        failed = failed_dev_items(self.items, baseline)
        team = live_team(self.items)
        naive = planted("BUG_NAIVE_ANALYZER")
        if naive or candidates.count() == 1:  # the naive analyzer writes the same rules each time
            runs = [candidates.CandidateRun("A", name, team.run(failed, knowledge, name))]
        else:
            runs = self.measured_candidates(team, failed, knowledge, name, baseline, session_id)
        chosen = candidates.choose(runs)
        report = chosen.report
        draft = report.candidate.model_copy(update={"version": name})
        created_by = "naive analyzer" if report.planted_active else "analyzer team"
        with db.connect(db.Role.APP) as conn:
            versions.save_draft(conn, draft, created_by=created_by)
            said = candidates.save(
                conn,
                runs,
                chosen,
                session_id=session_id,
                request_id=request_id,
                from_version=active,
                saved_as=name,
                naive=naive,
            )
            conn.commit()
        return analyzer_summary(report, name, active, len(failed)) | {
            "candidates": [c.as_dict() for c in runs],
            "chosen": chosen.label,
            "selection": said,
        }

    def measured_candidates(
        self,
        team: AnalyzerTeam,
        failed: Sequence[FailedItem],
        knowledge: KnowledgeVersion,
        name: str,
        baseline: ExperimentResult,
        session_id: UUID,
    ) -> list[candidates.CandidateRun]:
        """Each candidate from its own analyzer team run, measured on the dev split only, every
        item once, under its own retired version; never on the holdout split."""
        runner = self._runner(stream=False)  # the Improve page's ledger shows the gate's runs only
        runs = []
        for index in range(candidates.count()):
            version = candidates.selection_version(name, index)
            report = team.run(failed, knowledge, version)
            with db.connect(db.Role.APP) as conn:
                candidates.save_selection_draft(conn, report.candidate)
                conn.commit()
            dev = runner.run(self.items, version, session_id=session_id, splits=[Split.DEV])
            runs.append(
                candidates.CandidateRun(
                    candidates.label(index),
                    version,
                    report,
                    dev,
                    candidates.dev_regressions(baseline, dev),
                )
            )
        return runs

    # --- the gate -------------------------------------------------------------------------------
    def gate(
        self, candidate: ExperimentResult, active: str, runner: ExperimentRunner
    ) -> GateDecision:
        with db.connect(db.Role.APP) as conn:
            baseline = store.baseline_for(conn, active)
            regressions = find_regressions(
                self.items,
                baseline,
                candidate,
                lambda item, times: runner.rerun(item, candidate.knowledge_version, times),
                self.scheme,
                sink=store.OpsStepSink(conn),
                active_rerun=lambda item, times: runner.rerun(item, active, times),
            )
            found = versions.status_of(conn, candidate.knowledge_version)
            approved_by = found["approved_by"] if found and found["status"] == "approved" else None
            flags = self.overfit_flags(conn, candidate.knowledge_version, active)
            decision = decide(
                baseline, candidate, regressions, approved_by=approved_by, overfit_flags=flags
            )
            store.save_decision(conn, decision)
            if decision.verdict == "promoted":
                self._activate(conn, decision.candidate_version, candidate, runner)
            conn.commit()
        return decision

    def overfit_flags(self, conn: psycopg.Connection[Any], name: str, active: str) -> list[str]:
        """The gate's fourth condition: the candidate's new rules the overfit guard rejects."""
        return candidate_overfit_flags(
            self.items, versions.get(conn, name), versions.get(conn, active)
        )

    def promote_approved(self) -> list[str]:
        """Promote each approved candidate whose gate was ready, once, in the open session."""
        promoted = []
        with db.connect(db.Role.APP) as conn:
            started = conn.execute(SESSION_STARTED).fetchone()
            if started is None:
                return []
            rows = conn.execute(
                "SELECT version, approved_by FROM ops.knowledge_versions k "
                "WHERE pack = %s AND status = 'approved' AND NOT EXISTS "
                "(SELECT 1 FROM ops.promotion_decisions d WHERE d.pack = k.pack "
                "AND d.candidate_version = k.version AND d.approved_by IS NOT NULL "
                "AND d.decided_at >= %s)",
                (active_pack(), started["started_at"]),
            ).fetchall()
            for row in rows:
                decision = self._decide_approved(conn, row["version"], row["approved_by"])
                if decision is not None and decision.verdict == "promoted":
                    promoted.append(row["version"])
                conn.commit()
        return promoted

    def _decide_approved(
        self, conn: psycopg.Connection[Any], name: str, approved_by: str
    ) -> GateDecision | None:
        active = versions.active_name(conn)
        try:
            candidate = store.baseline_for(conn, name)
            baseline = store.baseline_for(conn, active)
        except NoLiveBaseline:
            return None  # approved before its experiment ran in this session: wait for it
        decision = decide(
            baseline,
            candidate,
            confirmed_regressions(candidate),
            approved_by=approved_by,
            overfit_flags=self.overfit_flags(conn, name, active),
        )
        store.save_decision(conn, decision)
        if decision.verdict == "promoted":
            self._activate(conn, name, candidate, self._runner())
        return decision

    def _activate(
        self,
        conn: psycopg.Connection[Any],
        name: str,
        candidate: ExperimentResult,
        runner: ExperimentRunner,
    ) -> eligibility.Clearance:
        clearance = activate(
            conn,
            name,
            candidate,
            items=self.items,
            rerun=lambda item, times: runner.rerun(item, name, times),
            scheme=self.scheme,
        )
        log.info(
            "families cleared",
            version=name,
            cleared=clearance.cleared,
            below_minimum=clearance.below_minimum,
            reruns=clearance.reruns,
        )
        return clearance

    # --- helpers --------------------------------------------------------------------------------
    def _runner(self, *, stream: bool = True) -> ExperimentRunner:
        sink = store.OpsItemSink(self.scheme.holdout_repeats, self.concurrency)
        return ExperimentRunner(
            target=self.target,
            evaluator=self.evaluator,
            scheme=self.scheme,
            concurrency=self.concurrency,
            tracer=self.tracer,
            sink=sink if stream else None,
        )

    def _version_for(
        self, conn: psycopg.Connection[Any], params: dict[str, Any], active: str
    ) -> str:
        if params.get("knowledge_version"):
            return str(params["knowledge_version"])
        if params.get("plus_rule") == OVERBROAD:
            return overbroad_version(conn, active)
        if params.get("target") == "candidate":
            candidate = versions.latest_candidate(conn)
            if candidate is None:
                raise RequestFailed("no candidate version yet: run the analyzer team first")
            return candidate
        return active

    def tick(self) -> bool:
        """Claim and run one queued request; False when none was waiting."""
        for kind in ("experiment", "analyzer"):
            with db.connect(db.Role.APP) as conn:
                request = improvement.claim(conn, kind)  # type: ignore[arg-type]
                conn.commit()
            if request is None:
                continue
            try:
                result, failed = self.run(request), False
            except Exception as error:  # the request fails, the runner keeps serving
                log.exception("request failed", request_id=str(request["request_id"]))
                result, failed = {"error": f"{type(error).__name__}: {error}"}, True
            with db.connect(db.Role.APP) as conn:
                improvement.finish(conn, str(request["request_id"]), result=result, failed=failed)
                conn.commit()
            return True
        return False

    def background(self) -> None:
        """Between requests: promotions after approval, and gold checks of live runs. A failing
        promotion never stops the gold checks."""
        try:
            self.promote_approved()
        except Exception:
            log.exception("promotion step failed")
        with db.connect(db.Role.APP) as conn:
            gold.check_new_runs(conn, self.items, self.evaluator)
            conn.commit()

    def serve(self, stop: threading.Event, poll_seconds: float = 1.0) -> None:
        def watch() -> None:
            while not stop.is_set():
                try:
                    self.background()
                except Exception:
                    log.exception("background step failed")
                stop.wait(poll_seconds)

        watcher = threading.Thread(target=watch, name="gold-and-promotions", daemon=True)
        watcher.start()
        while not stop.is_set():
            if not self.tick():
                stop.wait(poll_seconds)
        watcher.join(timeout=poll_seconds * 2)


def experiment_summary(result: ExperimentResult) -> dict[str, Any]:
    return {
        "experiment_id": str(result.experiment_id),
        "knowledge_version": result.knowledge_version,
        "holdout_passes": result.passes(Split.HOLDOUT),
        "holdout_total": result.total(Split.HOLDOUT),
        "dev_passes": result.passes(Split.DEV),
        "dev_total": result.total(Split.DEV),
        "wall_seconds": round(result.wall_seconds, 1),
    }


def analyzer_summary(report: AnalyzerReport, name: str, active: str, failed: int) -> dict[str, Any]:
    """What the analyzer request reports: every stage's count and each rejection's reason."""
    return {
        "candidate_version": name,
        "from_version": active,
        "failed_dev_items": failed,
        "diagnoses": len(report.diagnoses),
        "proposed": [r.id for r in report.proposed],
        "kept_by_critic": len(report.kept),
        "guidance_rejections": report.guidance_rejections,
        "passed_overfit_guard": [g.rule_id for g in report.guard if g.passed],
        "guard_rejections": {g.rule_id: g.reasons for g in report.guard if not g.passed},
        # the naive analyzer keeps every rule: its guard results are reported, never applied
        "accepted": [r.id for r in report.accepted],
        "critic": {r.rule_id: r.decision.value for r in report.reviews},
        "planted_active": report.planted_active,
    }


def candidate_overfit_flags(
    items: Sequence[BenchmarkItem], candidate: KnowledgeVersion, active: KnowledgeVersion
) -> list[str]:
    """The rules the candidate adds to the active version that the overfit guard rejects."""
    return new_rule_flags(OverfitGuard.from_pack(items), candidate, active)


def failed_dev_items(
    items: Sequence[BenchmarkItem], baseline: ExperimentResult
) -> list[FailedItem]:
    """The dev items the baseline failed, with the SQL of the run that decided each one."""
    out = []
    for item in items:
        if item.split is not Split.DEV or item.id not in baseline.results:
            continue
        if baseline.passed(item.id):
            continue
        sql = baseline.final_sql.get(item.id)
        answer = AnswerEnvelope(status=AnswerStatus.ANSWERED, final_sql=sql) if sql else None
        out.append(FailedItem(item, answer, baseline.results[item.id]))
    return out


def confirmed_regressions(candidate: ExperimentResult) -> Regressions:
    """The regressions the gate already confirmed on this experiment, read back from its ledger."""
    found = candidate.confirmations.values()
    return Regressions(
        dev=[c.item_id for c in found if c.confirmed and c.split is Split.DEV],
        holdout=[c.item_id for c in found if c.confirmed and c.split is Split.HOLDOUT],
        not_confirmed=[c.item_id for c in found if c.confirmed is False],
    )


def overbroad_version(conn: psycopg.Connection[Any], active: str) -> str:
    """The active version plus the pre-authored over-broad rule, saved as a draft once."""
    if active == versions.STARTING_VERSION:
        return versions.OVERBROAD_VERSION
    name = f"{active}-plus-over-broad-rule"
    if versions.status_of(conn, name) is None:
        combined = versions.with_rules_of(
            versions.get(conn, active), versions.get(conn, versions.OVERBROAD_VERSION), name
        )
        versions.save_draft(conn, combined, created_by="over-broad rule demo")
    return name


def activate(
    conn: psycopg.Connection[Any],
    name: str,
    candidate: ExperimentResult,
    *,
    items: Sequence[BenchmarkItem],
    rerun: eligibility.Rerun,
    scheme: Scheme,
) -> eligibility.Clearance:
    """Make the version active and clear each metric family of the pack on the confirmed standard;
    each confirming re-run is written beside its item in the candidate experiment."""
    versions.activate(conn, name)
    families = pack_config()["autonomy"]["metric_families"]
    clearance = eligibility.confirmed_clearance(items, candidate, rerun, scheme, families)
    for item_id, passes in clearance.reruns.items():
        store.save_clearance_rerun(conn, candidate.experiment_id, item_id, passes)
    for family in clearance.cleared:
        autonomy.mark_eligible(conn, family, name)
    return clearance
