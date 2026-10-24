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
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

import psycopg
import structlog

from datapilot import db, finale
from datapilot.config import active_pack, pack_config
from datapilot.contracts import (
    AnswerEnvelope,
    AnswerStatus,
    BenchmarkItem,
    KnowledgeVersion,
    Split,
)
from datapilot.contracts.live import NoLiveBaseline
from datapilot.loop1_agent.guard import StopReason
from datapilot.loop3_events import autonomy, improvement, killswitch
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


ALREADY_SERVING = (
    "another hill-climbing runner already serves this database: the Compose service "
    "hill-climbing-runner, which make up starts. Read it with make logs NAME=hill-climbing-runner; "
    "do not start a second runner"
)


class RequestFailed(RuntimeError):
    """A request that cannot run, with the sentence the console shows."""


class RunnerAlreadyServing(RuntimeError):
    """Another runner holds the runner's lock on this database."""


KILL_SWITCH_STOP = "stopped: the kill switch is engaged"


class KillSwitchEngaged(RequestFailed):
    """The kill switch is engaged: the request stops, and nothing it measured counts."""


def kill_switch_stop() -> StopReason | None:
    """The kill switch as the stop source of each run the runner's target starts, so a run in
    flight stops at its next model or tool call (AnalystTarget.external_stop)."""
    return StopReason.KILL_SWITCH if killswitch.engaged() else None


@dataclass
class KillSwitchStop:
    """The kill switch as one request sees it: checked before the request starts and before
    every run of the target, so once it is engaged no further run starts (a run in flight stops
    at its next model call: AnalystTarget.external_stop). A run it stopped fails as an item, so
    the request checks again before it records or decides anything."""

    engaged: Callable[[], bool] = killswitch.engaged
    seen: threading.Event = field(default_factory=threading.Event)

    def check(self) -> None:
        if self.seen.is_set() or self.engaged():
            self.seen.set()
            raise KillSwitchEngaged(KILL_SWITCH_STOP)

    def target(self, target: Target) -> Target:
        def checked(question: str, knowledge_version: str) -> AnswerEnvelope:
            self.check()
            return target(question, knowledge_version)

        return checked

    def rerun(self, runner: ExperimentRunner, knowledge_version: str) -> eligibility.Rerun:
        """Confirming re-runs that stop the request when the switch is engaged before or during
        them: a run the switch stopped is never counted as a measured failure."""

        def checked(item: BenchmarkItem, times: int) -> list[bool]:
            self.check()
            passes = runner.rerun(item, knowledge_version, times)
            self.check()
            return passes

        return checked


@dataclass
class HillClimbingRunner:
    items: Sequence[BenchmarkItem]
    target: Target
    evaluator: ExecutionEvaluator
    scheme: Scheme
    concurrency: int
    tracer: RunTracer | None = None
    project_url: str | None = None
    kill_switch_engaged: Callable[[], bool] = killswitch.engaged
    # Held from the moment a candidate experiment is finished until its gate has decided, and by
    # the background promotion while it decides: the two threads never decide one version at once.
    deciding: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)

    # --- requests (improvement.ImprovementRunner) -----------------------------------------------
    def run(self, request: dict[str, Any]) -> dict[str, Any]:
        session_id = request.get("session_id")
        if session_id is None:
            raise RequestFailed("no live session was open when this was requested")
        params = dict(request.get("params") or {})
        stop = KillSwitchStop(self.kill_switch_engaged)
        stop.check()  # an engaged switch fails a claimed request before it calls the model
        if request["kind"] == "analyzer":
            return self.analyzer(session_id, request.get("request_id"), stop)
        return self.experiment(params, session_id, stop)

    def experiment(
        self, params: dict[str, Any], session_id: UUID, stop: KillSwitchStop | None = None
    ) -> dict[str, Any]:
        stop = stop or KillSwitchStop(self.kill_switch_engaged)
        with db.connect(db.Role.APP) as conn:
            active = versions.active_name(conn)
            name = self._version_for(conn, params, active)
            conn.commit()
        runner = self._runner(stop=stop)
        result = runner.run(
            self.items, name, session_id=session_id, splits=SPLITS[params.get("split") or "all"]
        )
        stop.check()  # a stopped experiment is never finished, so it never becomes a baseline
        with self.deciding:  # finished and gated as one step, as the background promotion sees it
            with db.connect(db.Role.APP) as conn:
                store.finish_experiment(conn, result, langsmith_url=self.project_url)
                conn.commit()
            summary = experiment_summary(result)
            if name != active:
                decision = self.gate(result, active, runner, stop)
                summary |= {
                    "verdict": decision.verdict,
                    "ready_for_approval": decision.ready_for_approval,
                    "sentence": decision.sentence,
                    "reasons": decision.reasons,
                }
        return summary

    def analyzer(
        self,
        session_id: UUID,
        request_id: UUID | str | None = None,
        stop: KillSwitchStop | None = None,
    ) -> dict[str, Any]:
        stop = stop or KillSwitchStop(self.kill_switch_engaged)
        with db.connect(db.Role.APP) as conn:
            active = versions.active_name(conn)
            try:
                baseline = store.baseline_for(conn, active)
            except NoLiveBaseline as error:
                raise RequestFailed(str(error)) from error
            knowledge = versions.get(conn, active)
            name = versions.next_name(conn)
        failed = failed_dev_items(self.items, baseline)
        team = live_team(self.items).stopping(stop.check)  # checked before each model call
        naive = planted("BUG_NAIVE_ANALYZER")
        if naive or candidates.count() == 1:  # the naive analyzer writes the same rules each time
            runs = [candidates.CandidateRun("A", name, team.run(failed, knowledge, name))]
        else:
            runs = self.measured_candidates(
                team, failed, knowledge, name, baseline, session_id, stop
            )
        stop.check()  # nothing is saved for approval from a request the kill switch stopped
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
        stop: KillSwitchStop | None = None,
    ) -> list[candidates.CandidateRun]:
        """Each candidate from its own analyzer team run, measured on the dev split only, every
        item once, under its own retired version; never on the holdout split."""
        stop = stop or KillSwitchStop(self.kill_switch_engaged)
        # the Improve page's ledger shows the gate's runs only
        runner = self._runner(stream=False, stop=stop)
        runs = []
        for index in range(candidates.count()):
            stop.check()
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
        self,
        candidate: ExperimentResult,
        active: str,
        runner: ExperimentRunner,
        stop: KillSwitchStop | None = None,
    ) -> GateDecision:
        stop = stop or KillSwitchStop(self.kill_switch_engaged)
        with db.connect(db.Role.APP) as conn:
            baseline = store.baseline_for(conn, active)
            conn.commit()  # no transaction stays open through the confirming re-runs
            regressions = find_regressions(
                self.items,
                baseline,
                candidate,
                stop.rerun(runner, candidate.knowledge_version),
                self.scheme,
                sink=store.OpsStepSink(conn),
                active_rerun=stop.rerun(runner, active),
            )
            found = versions.status_of(conn, candidate.knowledge_version)
            approved_by = found["approved_by"] if found and found["status"] == "approved" else None
            flags = self.overfit_flags(conn, candidate.knowledge_version, active)
            decision = decide(
                baseline, candidate, regressions, approved_by=approved_by, overfit_flags=flags
            )
            save_decision(conn, decision)
            if decision.verdict == "promoted":
                self._activate(conn, decision.candidate_version, candidate, runner, stop)
            conn.commit()
        return decision

    def overfit_flags(self, conn: psycopg.Connection[Any], name: str, active: str) -> list[str]:
        """The gate's fourth condition: the candidate's new rules the overfit guard rejects."""
        return candidate_overfit_flags(
            self.items, versions.get(conn, name), versions.get(conn, active)
        )

    def promote_approved(self) -> list[str]:
        """Promote each approved candidate whose gate was ready, once, in the open session; never
        while the kill switch is engaged (a promotion's confirming re-runs call the model), and
        never while the request thread finishes or gates an experiment (`deciding`): the next
        poll after the gate decides instead."""
        if self.kill_switch_engaged():
            return []
        if not self.deciding.acquire(blocking=False):
            return []
        try:
            return self._promote_approved()
        finally:
            self.deciding.release()

    def _promote_approved(self) -> list[str]:
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
        if not gate_finished(baseline, candidate):
            return None  # its gate stopped before it confirmed every regression: never guess
        decision = decide(
            baseline,
            candidate,
            confirmed_regressions(candidate),
            approved_by=approved_by,
            overfit_flags=self.overfit_flags(conn, name, active),
        )
        save_decision(conn, decision)
        if decision.verdict == "promoted":
            stop = KillSwitchStop(self.kill_switch_engaged)
            self._activate(conn, name, candidate, self._runner(stop=stop), stop)
        return decision

    def _activate(
        self,
        conn: psycopg.Connection[Any],
        name: str,
        candidate: ExperimentResult,
        runner: ExperimentRunner,
        stop: KillSwitchStop,
    ) -> eligibility.Clearance:
        clearance = activate(
            conn,
            name,
            candidate,
            items=self.items,
            rerun=stop.rerun(runner, name),
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
    def _runner(
        self, *, stream: bool = True, stop: KillSwitchStop | None = None
    ) -> ExperimentRunner:
        sink = store.OpsItemSink(self.scheme.holdout_repeats, self.concurrency)
        return ExperimentRunner(
            target=stop.target(self.target) if stop else self.target,
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
        """Claim and run the oldest queued request, of either kind; False when none was waiting.
        In order, so an experiment on the candidate queued after the analyzer runs on its draft."""
        with db.connect(db.Role.APP) as conn:
            request = improvement.claim_next(conn)
            conn.commit()
        if request is None:
            return False
        try:
            result, failed = self.run(request), False
        except Exception as error:  # the request fails, the runner keeps serving
            log.exception("request failed", request_id=str(request["request_id"]))
            result, failed = {"error": f"{type(error).__name__}: {error}"}, True
        with db.connect(db.Role.APP) as conn:
            improvement.finish(conn, str(request["request_id"]), result=result, failed=failed)
            conn.commit()
        return True

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
        """Serve until `stop` is set, holding the runner's lock: a second runner on the same
        database refuses to start (RunnerAlreadyServing) rather than take requests from this one."""
        with db.connect(db.Role.APP, autocommit=True) as lock:
            if not improvement.hold_runner_lock(lock):
                raise RunnerAlreadyServing(ALREADY_SERVING)
            self._serve(stop, poll_seconds)

    def _serve(self, stop: threading.Event, poll_seconds: float) -> None:
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


def save_decision(conn: psycopg.Connection[Any], decision: GateDecision) -> None:
    """Record the gate's decision; an approved version it blocked is retired at once
    (versions.retire_blocked), so it holds no control while it waits for a promotion that cannot
    come."""
    store.save_decision(conn, decision)
    if decision.approved_by and decision.verdict != "promoted":
        versions.retire_blocked(conn, decision.candidate_version)


def gate_finished(active: ExperimentResult, candidate: ExperimentResult) -> bool:
    """Every apparent regression of the candidate (an item that passed under the active version
    and failed under the candidate, as find_regressions selects them) has a finished confirmation:
    confirmed or cleared. A gate the kill switch or an error stopped leaves one unfinished."""
    for item_id in candidate.results:
        if item_id not in active.results or not active.passed(item_id):
            continue
        if candidate.passed(item_id):
            continue
        confirmation = candidate.confirmations.get(item_id)
        if confirmation is None or confirmation.confirmed is None:
            return False
    return True


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
    each confirming re-run is written beside its item in the candidate experiment.

    The activation commits first, with whatever the caller wrote before it (the gate's decision),
    so no transaction or row lock is held through the confirming re-runs, which call the model;
    and a re-run that fails afterwards never rolls the decision back, so the next poll does not
    decide and spend again. The clearances are written in a second short transaction."""
    versions.activate(conn, name)
    conn.commit()
    with clearing():  # the finale waits until the families are written (datapilot.finale)
        families = pack_config()["autonomy"]["metric_families"]
        clearance = eligibility.confirmed_clearance(items, candidate, rerun, scheme, families)
        for item_id, passes in clearance.reruns.items():
            store.save_clearance_rerun(conn, candidate.experiment_id, item_id, passes)
        for family in clearance.cleared:
            autonomy.mark_eligible(conn, family, name)
        conn.commit()
    return clearance


@contextmanager
def clearing() -> Iterator[None]:
    """Hold finale.CLEARING_LOCK through the clearance re-runs, on a connection of its own in
    autocommit, so the promotion's connection holds no transaction through them. The lock goes
    when this connection closes, even if the process dies."""
    with db.connect(db.Role.APP, autocommit=True) as lock:
        lock.execute("SELECT pg_advisory_lock(%s)", (finale.CLEARING_LOCK,))
        yield
