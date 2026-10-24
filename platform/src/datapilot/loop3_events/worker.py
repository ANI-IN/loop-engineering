"""The worker: claim a job with a lease, run it outside the claim transaction, finish it only while
still the lease owner of the same attempt (fenced on owner and attempt).

Claim is one short transaction (UPDATE ... WHERE job_id = (SELECT ... FOR UPDATE SKIP LOCKED
LIMIT 1) RETURNING, then commit). Heartbeats extend the lease while the run works; the reaper
requeues a job whose lease expired. The kill switch and the daily budget are checked before each
claim.
"""

from __future__ import annotations

import asyncio
import contextlib
import signal
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Any

import psycopg
import structlog
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from datapilot import db
from datapilot.config import active_pack, pack_config
from datapilot.contracts import (
    AnswerEnvelope,
    AnswerStatus,
    DemotionReason,
    RunEventKind,
    RunStatus,
)
from datapilot.loop1_agent.analyst import AgentLimits
from datapilot.loop1_agent.catalog import load_snapshot
from datapilot.loop1_agent.guard import RunGuard, StopReason
from datapilot.loop1_agent.knowledge import active_knowledge
from datapilot.loop1_agent.models import ModelFactory, openai_factory
from datapilot.loop2_verification import defense
from datapilot.loop2_verification.config import VerificationConfig
from datapilot.loop2_verification.executor import Executor
from datapilot.loop2_verification.feedback import langsmith_client
from datapilot.loop2_verification.loop import (
    ApprovalRequest,
    LoopServices,
    RunOutcome,
    RunRequest,
    VerificationLoop,
)
from datapilot.loop3_events import (
    approvals,
    autonomy,
    budget,
    channel,
    extension,
    killswitch,
    lifecycle,
    pacing,
    reaper,
    router,
)
from datapilot.observability import spend
from datapilot.observability.traces import live_links
from datapilot.planted import planted
from datapilot.settings import get_settings

log = structlog.get_logger("worker")

CLAIM_SQL = """
UPDATE ops.jobs
SET status = 'running', attempts = attempts + 1, lease_owner = %(owner)s,
    lease_until = now() + make_interval(secs => %(lease)s), updated_at = now()
WHERE job_id = (
    SELECT job_id FROM ops.jobs
    WHERE status = 'queued' AND run_after <= now() AND queue = ANY(%(queues)s)
    ORDER BY run_after, job_id
    FOR UPDATE SKIP LOCKED
    LIMIT 1)
RETURNING job_id, event_id, attempts, max_attempts
"""
HEARTBEAT_SQL = (
    "UPDATE ops.jobs SET lease_until = now() + make_interval(secs => %s), updated_at = now() "
    "WHERE job_id = %s AND lease_owner = %s AND attempts = %s AND status = 'running'"
)
FINISH_SQL = (
    "UPDATE ops.jobs SET status = %s, lease_owner = NULL, lease_until = NULL, updated_at = now(), "
    "last_error = %s WHERE job_id = %s AND lease_owner = %s AND attempts = %s "
    "AND status = 'running'"
)
DEFER_SQL = (
    "UPDATE ops.jobs SET status = 'queued', run_after = now() + interval '30 seconds', "
    "lease_owner = NULL, lease_until = NULL, updated_at = now() "
    "WHERE job_id = %s AND lease_owner = %s AND attempts = %s"
)
# The queries a person approved earlier in this run: a retry with the same text is not held again.
APPROVED_SQL = (
    "SELECT sql FROM ops.approvals WHERE run_id = %s AND kind = 'tool_call' "
    "AND decision = 'approve' AND sql IS NOT NULL"
)
# Where the run left off before it paused: a resumed run keeps its attempt count (the retry cap)
# and the reviewer's one fed-back concern, so a concern after an approval holds the answer instead
# of sending the analyst back to write, and hold, yet another query.
PROGRESS_SQL = (
    "SELECT COALESCE(max((payload->>'attempt')::int) FILTER (WHERE kind = 'status_changed'), 1) "
    "AS attempt, COALESCE(bool_or(kind = 'reviewer_verdict' AND payload->>'outcome' = 'concern'), "
    "false) AS concern_fed_back FROM ops.run_events WHERE run_id = %s"
)
# spend_activity: the ledger activity the job's starter named (NULL: this process's own).
RUN_SQL = """
SELECT r.run_id, r.status, r.question, r.demo_name, r.metric_family, r.tokens_in, r.tokens_out,
       r.answer, r.knowledge_version, e.event_id, e.type, e.payload, j.spend_activity
FROM ops.runs r JOIN ops.events e ON e.event_id = r.event_id
LEFT JOIN ops.jobs j ON j.job_id = r.job_id
WHERE r.event_id = %s
"""


@dataclass(frozen=True)
class Job:
    job_id: int
    event_id: str
    attempts: int
    max_attempts: int


@dataclass
class WorkerSettings:
    worker_id: str = field(default_factory=lambda: f"worker-{uuid.uuid4().hex[:8]}")
    lease_seconds: float = 30.0
    poll_seconds: float = 1.0
    queues: tuple[str, ...] = ("default", "scheduled")


# (run id, the job's spend activity or None) -> the model factory for that run
ModelsFor = Callable[[str, str | None], ModelFactory]
TraceUrl = Callable[[str], str | None]


def _no_trace_url(_trace_id: str) -> str | None:
    return None


class DbHooks:
    """Run hooks that write ops.runs and ops.run_events, each change in its own transaction."""

    def __init__(self, run_id: str) -> None:
        self.run_id = run_id

    def status(self, new: RunStatus, **payload: Any) -> None:
        with db.connect(db.Role.APP) as conn:
            lifecycle.transition(conn, self.run_id, new, by="worker", **payload)
            conn.commit()

    def event(self, kind: RunEventKind, payload: dict[str, Any]) -> None:
        with db.connect(db.Role.APP) as conn:
            lifecycle.record(conn, self.run_id, kind, payload)
            conn.commit()


class Worker:
    def __init__(
        self,
        base: LoopServices,
        *,
        models_for: ModelsFor,
        settings: WorkerSettings | None = None,
        trace_url: TraceUrl = _no_trace_url,
    ) -> None:
        self.base = base
        self.models_for = models_for
        self.settings = settings or WorkerSettings()
        self.trace_url = trace_url
        self.started_at = datetime.now(UTC)
        self.lost_lease = False

    # --- the job queue -------------------------------------------------------------------------
    def _claim(self) -> tuple[Job, psycopg.Connection[Any] | None] | None:
        params = {
            "owner": self.settings.worker_id,
            "lease": self.settings.lease_seconds,
            "queues": list(self.settings.queues),
        }
        conn = psycopg.connect(db.url_for(db.Role.APP), row_factory=dict_row)
        row = conn.execute(CLAIM_SQL, params).fetchone()
        if row is None:
            conn.rollback()
            conn.close()
            return None
        job = Job(**row)
        if planted("BUG_LOCK_DURING_LLM"):
            return job, conn  # planted: the claim transaction stays open through the whole run
        conn.commit()
        conn.close()
        return job, None

    def _finish(
        self, job: Job, held: psycopg.Connection[Any] | None, status: str, error: str = ""
    ) -> bool:
        params = (status, error or None, job.job_id, self.settings.worker_id, job.attempts)
        if held is not None:
            try:
                done = held.execute(FINISH_SQL, params).rowcount == 1
                held.commit()
            except psycopg.Error:  # the held claim transaction died with its connection
                return False
            return done
        with db.connect(db.Role.APP) as conn:
            done = conn.execute(FINISH_SQL, params).rowcount == 1
            conn.commit()
        if not done:
            log.warning("lease lost before finishing; result discarded", job_id=job.job_id)
        return done

    async def _heartbeat(self, job: Job) -> None:
        interval = max(self.settings.lease_seconds / 3, 0.05)
        while True:
            await asyncio.sleep(interval)
            if not self.heartbeat_once(job):
                self.lost_lease = True
                return

    def heartbeat_once(self, job: Job) -> bool:
        """Extend the lease; False when this worker no longer holds this attempt of the job."""
        params = (self.settings.lease_seconds, job.job_id, self.settings.worker_id, job.attempts)
        with db.connect(db.Role.APP) as conn:
            extended = conn.execute(HEARTBEAT_SQL, params).rowcount == 1
            conn.commit()
        return extended

    def reap(self) -> list[dict[str, Any]]:
        with db.connect(db.Role.APP) as conn:
            reaped = reaper.reap(conn)
            conn.commit()
        return reaped

    # --- one job -------------------------------------------------------------------------------
    async def run_once(self) -> bool:
        """Reap, then claim and process one job. False when the queue was empty."""
        self.reap()
        claimed = self._claim()
        if claimed is None:
            return False
        job, held = claimed
        try:
            await self._process(job, held)
        except Exception as error:
            log.exception("run failed", job_id=job.job_id)
            try:
                self._fail(job, held, error)
            except Exception:
                log.exception("could not record the failure", job_id=job.job_id)
        finally:
            if held is not None and not held.closed:
                held.close()
        return True

    def _load(self, event_id: str) -> dict[str, Any]:
        with db.connect(db.Role.APP) as conn:
            return conn.execute(RUN_SQL, (event_id,)).fetchone()

    def _fail(self, job: Job, held: psycopg.Connection[Any] | None, error: Exception) -> None:
        run = self._load(job.event_id)
        with db.connect(db.Role.APP) as conn:
            status = RunStatus(run["status"])
            if status is RunStatus.VERIFYING:
                lifecycle.transition(conn, str(run["run_id"]), RunStatus.RUNNING, by="worker")
                status = RunStatus.RUNNING
            if status is RunStatus.RUNNING:
                lifecycle.transition(
                    conn, str(run["run_id"]), RunStatus.FAILED, by="worker", error=str(error)
                )
            conn.commit()
        self._finish(job, held, "done", str(error))

    async def _process(self, job: Job, held: psycopg.Connection[Any] | None) -> None:
        run = self._load(job.event_id)
        run_id, status = str(run["run_id"]), RunStatus(run["status"])
        route = router.route(run["type"], run["payload"])
        with db.connect(db.Role.APP) as conn:
            if killswitch.state(conn) == "engaged":
                deferred = self._block_at_claim(conn, run_id, status, job)
                conn.commit()
                if not deferred:
                    self._finish(job, held, "done")
                return
            if status is RunStatus.QUEUED and budget.exhausted(conn):
                lifecycle.transition(
                    conn, run_id, RunStatus.BLOCKED_BUDGET, by="worker: budget check before claim"
                )
                lifecycle.record(conn, run_id, RunEventKind.BUDGET_BLOCKED, {"at": "claim"})
                autonomy.demote(conn, DemotionReason.BUDGET_EXHAUSTED)
                conn.commit()
                self._finish(job, held, "done")
                return
            if status is RunStatus.ANSWERED:
                parked = self._post_or_hold(conn, run, route.export)
                conn.commit()
                self._finish(job, held, "parked" if parked else "done")
                return
        self.lost_lease = False
        beat = None if held is not None else asyncio.create_task(self._heartbeat(job))
        try:
            outcome = await self._run(run, route, status)
        finally:
            if beat is not None:
                beat.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await beat
        if outcome is None:
            self._finish(job, held, "done")
            return
        if self.lost_lease:
            log.warning("lease lost during the run; result discarded", job_id=job.job_id)
            return
        await pacing.pause()
        parked = self._apply(run, route.export, outcome)
        self._finish(job, held, "parked" if parked else "done")

    def _block_at_claim(
        self, conn: psycopg.Connection[Any], run_id: str, status: RunStatus, job: Job
    ) -> bool:
        """Returns True when the job was deferred instead of finished."""
        if status in (RunStatus.QUEUED, RunStatus.AWAITING_APPROVAL):
            by = "worker: kill switch check at claim"
            lifecycle.transition(conn, run_id, RunStatus.BLOCKED_KILLSWITCH, by=by)
            lifecycle.record(conn, run_id, RunEventKind.KILLSWITCH_BLOCKED, {"at": "claim"})
            return False
        conn.execute(
            DEFER_SQL, (job.job_id, self.settings.worker_id, job.attempts)
        )  # post after release
        return True

    async def _run(
        self, run: dict[str, Any], route: router.Route, status: RunStatus
    ) -> RunOutcome | None:
        run_id = str(run["run_id"])
        hooks = DbHooks(run_id)
        if status is RunStatus.QUEUED:
            hooks.status(RunStatus.RUNNING, attempt=1)
            await pacing.pause()
            if route.handler == "defense_check":
                return await asyncio.to_thread(self._defense_check, run, hooks)
            if route.handler.startswith("job:"):
                await asyncio.to_thread(self._job, run, route.handler.removeprefix("job:"))
                return None
            return await self._loop(run, hooks).start(self._request(run, route.export))
        if status is RunStatus.AWAITING_APPROVAL:
            with db.connect(db.Role.APP) as conn:
                decided = approvals.latest(conn, run_id)
            if not decided or decided["decision"] != "approve" or decided["kind"] != "tool_call":
                return None
            lifecycle_by = "worker: approval resumed the run"
            with db.connect(db.Role.APP) as conn:
                lifecycle.transition(conn, run_id, RunStatus.RUNNING, by=lifecycle_by)
                conn.commit()
            return await self._loop(run, hooks).resume(
                self._request(run, route.export), approve=True
            )
        return None

    def _request(self, run: dict[str, Any], export: bool) -> RunRequest:
        with db.connect(db.Role.APP) as conn:
            level = conn.execute("SELECT autonomy_level FROM ops.control WHERE id = 1").fetchone()
            approved = conn.execute(APPROVED_SQL, (str(run["run_id"]),)).fetchall()
            progress = conn.execute(PROGRESS_SQL, (str(run["run_id"]),)).fetchone()
        return RunRequest(
            approved_sql=tuple(row["sql"] for row in approved),
            attempt=progress["attempt"],
            concern_fed_back=progress["concern_fed_back"],
            run_id=str(run["run_id"]),
            question=run["question"] or "",
            event_id=run["event_id"],
            demo_name=run["demo_name"],
            export=export,
            inject_failing_grader=bool(run["payload"].get("inject_failing_grader")),
            autonomy_level=level["autonomy_level"],
            tokens_in=run["tokens_in"],
            tokens_out=run["tokens_out"],
        )

    def _refresh_empty_snapshot(self) -> None:
        """A worker started before `make seed` holds an empty catalog: read it again until the
        warehouse has tables, so a fresh install answers without restarting the worker."""
        if not self.base.snapshot.tables:
            self.base = replace(
                self.base, snapshot=load_snapshot(self.base.executor.url, self.base.config.schema)
            )

    def _loop(self, run: dict[str, Any], hooks: DbHooks) -> VerificationLoop:
        run_id = str(run["run_id"])
        self._refresh_empty_snapshot()
        services = replace(self.base, models=self.models_for(run_id, run.get("spend_activity")))

        def middleware(guard: RunGuard) -> list[Any]:
            return [pacing.PacingMiddleware(), killswitch.KillSwitchMiddleware(guard)]

        def stop() -> StopReason | None:
            # A worker that lost its lease stops at the next model or tool call: its result
            # would be discarded, and another worker may hold the requeued job by now.
            return StopReason.LOST_LEASE if self.lost_lease else _daily_budget_stop()

        return VerificationLoop(
            services,
            hooks,
            external_stop=stop,
            on_usage=lambda usage: self._usage(run_id, usage),
            extra_middleware=middleware,
        )

    def _usage(self, run_id: str, usage: spend.Usage) -> None:
        tokens_in, tokens_out = usage.input_tokens, usage.output_tokens
        cost = call_cost(self.base.model_name, usage)
        with db.connect(db.Role.APP) as conn:
            conn.execute(
                "UPDATE ops.runs SET tokens_in = tokens_in + %s, tokens_out = tokens_out + %s, "
                "cost_usd = cost_usd + %s, updated_at = now() WHERE run_id = %s",
                (tokens_in, tokens_out, cost, run_id),
            )
            budget.add_usage(conn, tokens_in + tokens_out)
            conn.commit()

    def _job(self, run: dict[str, Any], job: str) -> None:
        """A scheduled job the router table names: no agent. The job posts its own result (one
        alert per key, updated in place), so the run only records what it did."""
        run_id = str(run["run_id"])
        with db.connect(db.Role.APP) as conn:
            result = extension.run_job(
                job, conn, run["payload"], run_id=run_id, event_id=run["event_id"]
            )
            answer = {
                "envelope": AnswerEnvelope(
                    status=AnswerStatus.ANSWERED, answer_text=result.text
                ).model_dump(mode="json"),
                "job": {"outcome": result.outcome, "alert_key": result.alert_key},
            }
            conn.execute(
                "UPDATE ops.runs SET answer = %s, updated_at = now() WHERE run_id = %s",
                (Jsonb(answer), run_id),
            )
            if result.outcome == "blocked_killswitch":
                by = "worker: kill switch before the job posted"
                lifecycle.transition(conn, run_id, RunStatus.BLOCKED_KILLSWITCH, by=by)
                lifecycle.record(
                    conn, run_id, RunEventKind.KILLSWITCH_BLOCKED, {"at": "before posting"}
                )
            else:
                for status in (RunStatus.VERIFYING, RunStatus.ANSWERED, RunStatus.POSTED):
                    lifecycle.transition(conn, run_id, status, by=f"worker: job {job}")
            conn.commit()

    def _defense_check(self, run: dict[str, Any], hooks: DbHooks) -> RunOutcome:
        check = str(run["payload"].get("check"))
        executor, config = self.base.executor, self.base.config
        report = (
            defense.malicious_sql(executor, config)
            if check == "malicious-sql"
            else defense.cartesian_query(executor, config)
        )
        for statement in report["statements"]:
            hooks.event(
                RunEventKind.GRADER_RESULT,
                {
                    "grader": f"defense: {statement['stopped_by'] or 'none'}",
                    "passed": statement["stopped_by"] is not None,
                    "severity": "info",
                    "reason": statement["layers"][-1]["detail"],
                    "sql": statement["sql"],
                    "layers": statement["layers"],
                },
            )
        hooks.status(RunStatus.VERIFYING, attempt=1)
        statements = report["statements"]
        stopped = sum(1 for s in statements if s["stopped_by"])
        envelope = AnswerEnvelope(
            status=AnswerStatus.ANSWERED,
            answer_text=f"{stopped} of {len(statements)} statements stopped by a defense layer.",
            columns=["sql", "stopped_by"],
            rows_preview=[[s["sql"], s["stopped_by"]] for s in statements],
            row_count=len(statements),
            assumptions=[f"orders unchanged: {report['unchanged']}"]
            if "unchanged" in report
            else [],
        )
        return RunOutcome(status=RunStatus.ANSWERED, envelope=envelope, attempts=1)

    # --- outcomes and posting --------------------------------------------------------------------
    def _apply(self, run: dict[str, Any], export: bool, outcome: RunOutcome) -> bool:
        """Write the outcome; returns True when the job is parked for an approval."""
        run_id = str(run["run_id"])
        answer = {
            "envelope": outcome.envelope.model_dump(mode="json") if outcome.envelope else None,
            "personal_data": outcome.personal_data,
            "reasons": outcome.reasons,
            "verdict": outcome.verdict.model_dump(mode="json") if outcome.verdict else None,
            "attempts": outcome.attempts,
        }
        with db.connect(db.Role.APP) as conn:
            conn.execute(
                "UPDATE ops.runs SET answer = %s, knowledge_version = %s, model = %s, "
                "langsmith_url = COALESCE(langsmith_url, %s), updated_at = now() WHERE run_id = %s",
                (
                    Jsonb(answer),
                    outcome.knowledge_version or None,
                    self.base.model_name,
                    self.trace_url(run_id),
                    run_id,
                ),
            )
            status = outcome.status
            if status is RunStatus.AWAITING_APPROVAL and outcome.approval is not None:
                lifecycle.transition(
                    conn, run_id, status, by="worker", reason=outcome.approval.reason
                )
                approvals.request(conn, run_id, outcome.approval)
                conn.commit()
                return True
            lifecycle.transition(conn, run_id, status, by="worker", reasons=outcome.reasons)
            parked = False
            if status is RunStatus.BLOCKED_KILLSWITCH:
                lifecycle.record(conn, run_id, RunEventKind.KILLSWITCH_BLOCKED, {"at": "in flight"})
            elif status is RunStatus.BLOCKED_BUDGET:
                lifecycle.record(conn, run_id, RunEventKind.BUDGET_BLOCKED, {"at": "in flight"})
                autonomy.demote(conn, DemotionReason.BUDGET_EXHAUSTED)
            elif status is RunStatus.ESCALATED:
                autonomy.demote_after_escalations(conn)
            elif status is RunStatus.ANSWERED:
                run = {**run, "answer": answer}
                parked = self._post_or_hold(conn, run, export)
            conn.commit()
        return parked

    def _post_or_hold(
        self, conn: psycopg.Connection[Any], run: dict[str, Any], export: bool
    ) -> bool:
        run_id = str(run["run_id"])
        answer = run["answer"] or {}
        knowledge = conn.execute(
            "SELECT version FROM ops.knowledge_versions WHERE pack = %s AND status = 'active'",
            (active_pack(),),
        ).fetchone()
        policy = autonomy.OpsAutonomyPolicy.load(conn, knowledge["version"] if knowledge else "")
        family = run["metric_family"]
        level = policy.level_for(family)
        decision = autonomy.posting_decision(
            policy,
            family,
            personal_data=bool(answer.get("personal_data")),
            export=export,
            approved=approvals.approved(conn, run_id),
        )
        if decision == "approve_first":
            lifecycle.transition(
                conn,
                run_id,
                RunStatus.AWAITING_APPROVAL,
                by="worker: autonomy policy needs approval",
            )
            envelope = answer.get("envelope") or {}
            approvals.request(
                conn,
                run_id,
                ApprovalRequest(
                    kind="held_answer",
                    action=f"post the answer: {envelope.get('answer_text', '')}",
                    reason=f"personal data and exports need human approval at the {level.label}",
                    sql=envelope.get("final_sql"),
                    row_estimate=envelope.get("row_count"),
                ),
            )
            return True
        body: dict[str, Any] = {"answer": answer.get("envelope"), "level": level.value}
        note = policy.clearance_note(family)
        if note:  # the class-day safeguard: the clearance came from rehearsal, and the post says so
            body["clearance"] = note
        if export and level is autonomy.AutonomyLevel.REPORT_ONLY and body["answer"]:
            body["answer"] = {**body["answer"], "rows_preview": []}
            body["note"] = f"Exports are not released at the {level.label}."
        channel.post(
            conn, run_id=run_id, event_id=run["event_id"], label=autonomy.LABELS[level], body=body
        )
        conn.execute(
            "UPDATE ops.runs SET autonomy_level_applied = %s WHERE run_id = %s",
            (level.value, run_id),
        )
        lifecycle.transition(
            conn, run_id, RunStatus.POSTED, by="worker: posted to the channel per autonomy policy"
        )
        return False

    # --- the process ---------------------------------------------------------------------------
    def restart_requested(self) -> bool:
        with db.connect(db.Role.APP) as conn:
            row = conn.execute(
                "SELECT worker_restart_requested_at AS at FROM ops.control WHERE id = 1"
            ).fetchone()
        return bool(row["at"] and row["at"] > self.started_at)

    async def serve(self, stop: asyncio.Event) -> str:
        """Work until stopped; returns "restart" when a restart was requested."""
        while not stop.is_set():
            if self.restart_requested():
                return "restart"
            if not await self.run_once():
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(stop.wait(), self.settings.poll_seconds)
        return "stopped"


def call_cost(model: str, usage: spend.Usage) -> float:
    """One call's cost on the run, priced as the spend ledger prices it (cached input at the cached
    rate, cache writes at theirs), so ops.runs.cost_usd matches the ledger; 0 for an unpriced
    model (the tests' scripted one)."""
    return spend.cost_usd(model, usage) if model in pack_config()["prices"] else 0.0


def _daily_budget_stop() -> StopReason | None:
    with db.connect(db.Role.APP) as conn:
        spent = budget.exhausted(conn)
        conn.commit()
    return StopReason.DAILY_BUDGET if spent else None


def _unset_models(component: str) -> Any:
    raise RuntimeError("models come from the worker's models_for")


async def _main() -> str:
    cfg = pack_config()
    config = VerificationConfig.from_pack(cfg)
    executor = Executor(db.url_for(db.Role.AGENT), config.schema, config.statement_timeout_ms)
    db.wait_until_ready(db.Role.APP)
    executor.probe_read_only()  # raises, so the process refuses to start, unless it is read-only
    settings = get_settings()
    async with approvals.checkpointer() as saver:
        base = LoopServices(
            models=_unset_models,
            executor=executor,
            snapshot=load_snapshot(executor.url, config.schema),
            config=config,
            limits=AgentLimits.from_pack(cfg),
            knowledge=active_knowledge,
            checkpointer=saver,
            model_name=settings.agent_model,
            feedback=langsmith_client(settings),
        )
        # every run carries its LangSmith link (its run id is its trace id), for the live stamp
        found = live_links(settings, settings.langsmith_project)
        if found:  # a trace LangSmith refuses for its monthly limit is noted on the run's row
            from datapilot.loop3_events.trace_refusals import record_refusals

            record_refusals()
        worker = Worker(
            base,
            models_for=lambda run_id, activity: openai_factory(run_id=run_id, activity=activity),
            trace_url=found[1].url if found else _no_trace_url,
        )
        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, stop.set)
        log.info("worker ready", worker_id=worker.settings.worker_id)
        return await worker.serve(stop)


def main() -> None:
    reason = asyncio.run(_main())
    log.info(
        "worker stopped", reason=reason
    )  # Compose restarts the process after a restart request
