"""The calibration runner (`make calibrate STEP=<step>`): each step runs live, in the open live
session, under its own spend-ledger activity (calibration-<step>), and writes its raw results to
.runs/calibration/ (gitignored) and one line to the run log there.

Before a step runs, its cost is estimated from the runs it will make and the cost per run measured
so far for that model (a first guess until one is measured). A step whose estimate would take the
build's spend past the warning line in pack.yaml does not start.

Steps: canary, traps, experiment, analyzer, analyzer-high, stability, agents, confirm. Each returns
plain data; docs/calibration-report.md is written from these files only.
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from datapilot import db
from datapilot.config import pack_config
from datapilot.contracts import BenchmarkItem, ItemResult, Split
from datapilot.loop4_hill_climbing import store, versions
from datapilot.loop4_hill_climbing.analyzer import live_team
from datapilot.loop4_hill_climbing.evaluator import ExecutionEvaluator
from datapilot.loop4_hill_climbing.experiment import (
    ExperimentResult,
    ExperimentRunner,
    ItemSink,
    RunTracer,
)
from datapilot.loop4_hill_climbing.gate import find_regressions
from datapilot.loop4_hill_climbing.measurement import Scheme
from datapilot.loop4_hill_climbing.runner import experiment_summary, failed_dev_items
from datapilot.loop4_hill_climbing.stability import Limits, stability
from datapilot.loop4_hill_climbing.targets import AnalystTarget
from datapilot.observability import spend
from datapilot.observability.sampling import NOT_TRACED
from datapilot.observability.traces import ModelIds
from datapilot.settings import REPO, get_settings

RESULTS = REPO / ".runs" / "calibration"
RUN_LOG = RESULTS / "run-log.md"
EXTRA_LEDGERS = "DATAPILOT_EXTRA_SPEND_LEDGERS"  # other ledgers to count (read from a copy)

# Tokens per run until a run of that model has been measured (an analyst run with the scout and
# the reviewer; one analyzer team run).
FIRST_GUESS = {"analyst": spend.Usage(50_000, 0, 5_000), "analyzer": spend.Usage(60_000, 0, 30_000)}


class OverWarningLine(RuntimeError):
    """The step's estimate would take the build's spend past the warning line."""


# --- spend ---------------------------------------------------------------------------------------
def _ledger_rows(path: Path, sql: str, params: Sequence[Any] = ()) -> list[tuple[Any, ...]]:
    if not path.exists():
        return []
    with tempfile.TemporaryDirectory() as folder:
        copy = Path(folder) / path.name
        shutil.copy2(path, copy)
        wal = path.with_name(path.name + "-wal")
        if wal.exists():
            shutil.copy2(wal, copy.with_name(copy.name + "-wal"))
        conn = sqlite3.connect(copy)
        try:
            return conn.execute(sql, params).fetchall()
        finally:
            conn.close()


def ledgers() -> list[Path]:
    extra = [Path(p) for p in os.environ.get(EXTRA_LEDGERS, "").split(os.pathsep) if p]
    return [spend.ledger_path(), *extra]


def total_spent() -> float:
    """Spend across this process's ledger and any other ledger named in the environment."""
    return sum(
        float(row[0] or 0)
        for path in ledgers()
        for row in _ledger_rows(path, "SELECT SUM(cost_usd) FROM spend_ledger")
    )


def activity_spent(activity: str) -> float:
    rows = _ledger_rows(
        spend.ledger_path(),
        "SELECT SUM(cost_usd) FROM spend_ledger WHERE activity = ?",
        (activity,),
    )
    return float(rows[0][0] or 0) if rows else 0.0


def measured_cost_per_run(model: str, component_prefix: str = "") -> float | None:
    """The mean cost of one run of `model` so far (ledger rows grouped by run id)."""
    rows = _ledger_rows(
        spend.ledger_path(),
        "SELECT AVG(c) FROM (SELECT SUM(cost_usd) AS c FROM spend_ledger "
        "WHERE model = ? AND run_id IS NOT NULL AND component LIKE ? GROUP BY run_id)",
        (model, f"{component_prefix}%"),
    )
    return float(rows[0][0]) if rows and rows[0][0] is not None else None


def estimate(runs: int, model: str, kind: str = "analyst") -> float:
    per_run = measured_cost_per_run(model) if kind == "analyst" else None
    if per_run is None:
        per_run = spend.cost_usd(model, FIRST_GUESS[kind])
    return runs * per_run


def analyzer_effort_estimate(
    items: Sequence[BenchmarkItem], scheme: Scheme, analyst_model: str, analyzer_model: str
) -> float:
    """One analyzer team run and one candidate experiment (re-runs of apparent regressions come on
    top): about 0.10 dollars at the cost per run measured in calibration."""
    runs = sum(scheme.repeats(i.split) for i in items)
    return estimate(1, analyzer_model, "analyzer") + estimate(runs, analyst_model)


def guard_budget(step: str, estimate_usd: float, activity: str | None = None) -> str:
    """Refuse a step whose estimate would take its budget line past its cap (the reserve only with
    the owner's approval) or the build past the stop line; return the line to print otherwise,
    which says so when the build would pass the warning line."""
    budget = pack_config()["build_budget"]
    line = spend.line_for(activity or get_settings().datapilot_spend_activity)
    line_spent = spend.line_usage().get(line.name, (0, 0.0))[1]
    room = line.cap_usd - line_spent
    if spend.reserve_approved():
        room += spend.reserve_line().cap_usd - spend.reserve_used()
    spent = total_spent()
    projected = spent + estimate_usd
    text = (
        f"{step}: estimate ${estimate_usd:.4f}; the {line.name} line has ${max(room, 0):.4f} left "
        f"of ${line.cap_usd:.2f}; build ${spent:.4f}, projected ${projected:.4f} (warning at "
        f"${budget['warn_usd']:.2f}, stop at ${budget['stop_usd']:.2f})"
    )
    if estimate_usd > room or projected > budget["stop_usd"]:
        raise OverWarningLine(text + ": not started, ask the owner first")
    if projected > budget["warn_usd"]:
        text += "; past the warning line: report the spend to the lead"
    return text


def use_activity(step: str, *, prefix: str = "calibration-") -> str:
    """Every model call from here on is recorded under calibration-<step>."""
    activity = f"{prefix}{step}"
    os.environ["DATAPILOT_SPEND_ACTIVITY"] = activity
    get_settings.cache_clear()
    return activity


# --- results -------------------------------------------------------------------------------------
@dataclass
class StepRecord:
    step: str
    activity: str
    session_id: str
    started_at: str
    finished_at: str
    estimate_usd: float
    cost_usd: float
    summary: str
    data: dict[str, Any] = field(default_factory=dict)


def write(record: StepRecord, folder: Path = RESULTS) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    stamp = record.started_at.replace(":", "").replace("-", "")[:15]
    path = folder / f"{record.step}-{stamp}.json"
    path.write_text(json.dumps(asdict(record), indent=1, default=str), encoding="utf-8")
    with (folder / RUN_LOG.name).open("a", encoding="utf-8") as log:
        log.write(
            f"- {record.started_at} {record.step} ({record.activity}): {record.summary}; "
            f"estimate ${record.estimate_usd:.4f}, cost ${record.cost_usd:.4f}; {path.name}\n"
        )
    return path


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


# --- shared pieces -------------------------------------------------------------------------------
@dataclass
class EchoSink:
    """Implements experiment.ItemSink: one line per finished item, with its first trace link."""

    echo: Callable[[str], None]
    also: ItemSink | None = None

    def started(self, experiment: ExperimentResult) -> None:
        if self.also:
            self.also.started(experiment)
        self.echo(
            f"experiment {experiment.experiment_id} of {experiment.knowledge_version}: "
            f"{len(experiment.splits_by_item)} items"
        )

    def item_done(self, experiment: ExperimentResult, item_id: str) -> None:
        if self.also:
            self.also.item_done(experiment, item_id)
        result = experiment.results[item_id]
        runs = result.run_passes
        missing = NOT_TRACED if experiment.untraced_runs.get(item_id) else "no trace link"
        links = experiment.trace_links.get(item_id) or [missing]
        self.echo(
            f"  {item_id:42} {'pass' if result.passed else 'fail'} "
            f"({sum(runs)} of {len(runs)} runs) {links[0]}"
        )


@dataclass
class Context:
    session_id: UUID
    items: list[BenchmarkItem]
    evaluator: ExecutionEvaluator
    tracer: RunTracer | None
    concurrency: int
    echo: Callable[[str], None] = print

    def runner(self, target: AnalystTarget, scheme: Scheme, *, stream: bool) -> ExperimentRunner:
        ops = store.OpsItemSink(scheme.holdout_repeats, self.concurrency) if stream else None
        sink = EchoSink(self.echo, ops)
        return ExperimentRunner(target, self.evaluator, scheme, self.concurrency, self.tracer, sink)

    def by_id(self) -> dict[str, BenchmarkItem]:
        return {i.id: i for i in self.items}


def trap_items(items: Sequence[BenchmarkItem]) -> list[BenchmarkItem]:
    return [i for i in items if i.traps]


def easy_items(items: Sequence[BenchmarkItem]) -> list[BenchmarkItem]:
    return [i for i in items if not i.traps]


def run_rows(target: AnalystTarget) -> list[dict[str, Any]]:
    return [asdict(s) for s in target.stats]


def model_ids(ids: ModelIds) -> list[dict[str, Any]]:
    return ids.as_rows()


def _cells(result: ExperimentResult) -> dict[str, dict[str, Any]]:
    return {
        item_id: {
            "split": result.splits_by_item[item_id].value,
            "passed": r.passed,
            "run_passes": r.run_passes,
            "reason": r.reason,
            "trap_labels": r.trap_labels,
            "trace_urls": result.trace_links.get(item_id, []),
            "final_sql": result.final_sql.get(item_id),
        }
        for item_id, r in result.results.items()
    }


# --- steps ---------------------------------------------------------------------------------------
def traps_step(ctx: Context, target: AnalystTarget, runs: int) -> dict[str, Any]:
    """Every trap item `runs` times under the starting knowledge: each must fail every time."""
    repeated = [i.model_copy(update={"split": Split.HOLDOUT}) for i in trap_items(ctx.items)]
    scheme = replace(Scheme.from_pack(), holdout_repeats=runs)
    result = ctx.runner(target, scheme, stream=False).run(
        repeated, versions.STARTING_VERSION, session_id=ctx.session_id, splits=[Split.HOLDOUT]
    )
    per_trap: dict[str, dict[str, int]] = {}
    for item in repeated:
        passes = sum(result.results[item.id].run_passes)
        for trap in item.traps:
            counts = per_trap.setdefault(trap, {"items": 0, "runs": 0, "passed_runs": 0})
            counts["items"] += 1
            counts["runs"] += runs
            counts["passed_runs"] += passes
    passed_once = [i for i, r in result.results.items() if any(r.run_passes)]
    return {
        "knowledge_version": versions.STARTING_VERSION,
        "runs_per_item": runs,
        "items": _cells(result),
        "per_trap": per_trap,
        "passed_at_least_once": passed_once,
        "wall_seconds": round(result.wall_seconds, 1),
    }


def experiment_step(ctx: Context, target: AnalystTarget, version: str) -> dict[str, Any]:
    """The gate's measurement scheme on all 40 items, saved to ops as this session's experiment;
    a version other than the starting one is compared with this session's run of the starting
    version under the same model, apparent regressions confirmed by re-runs."""
    scheme = Scheme.from_pack()
    runner = ctx.runner(target, scheme, stream=True)
    result = runner.run(ctx.items, version, session_id=ctx.session_id)
    with db.connect(db.Role.APP) as conn:
        store.finish_experiment(conn, result)
        conn.commit()
    data: dict[str, Any] = {
        **experiment_summary(result),
        "model": target.model,
        "items": _cells(result),
        "easy_passed": sum(result.passed(i.id) for i in easy_items(ctx.items)),
        "easy_total": len(easy_items(ctx.items)),
        "trap_items_failed": sum(not result.passed(i.id) for i in trap_items(ctx.items)),
        "trap_items_total": len(trap_items(ctx.items)),
        "holdout_trap_passes": sum(
            result.passed(i.id) for i in trap_items(ctx.items) if i.split is Split.HOLDOUT
        ),
        "holdout_trap_total": sum(1 for i in trap_items(ctx.items) if i.split is Split.HOLDOUT),
        "runs": len(target.stats),
    }
    if version != versions.STARTING_VERSION:
        data["comparison"] = compare_with_start(ctx, target, runner, result)
    return data


def compare_with_start(
    ctx: Context, target: AnalystTarget, runner: ExperimentRunner, candidate: ExperimentResult
) -> dict[str, Any]:
    base = latest_experiment(ctx.session_id, versions.STARTING_VERSION, target.model)
    if base is None:
        return {"error": f"no experiment of {versions.STARTING_VERSION} on {target.model} yet"}
    regressions = find_regressions(
        ctx.items,
        base,
        candidate,
        lambda item, times: runner.rerun(item, candidate.knowledge_version, times),
        runner.scheme,
        active_rerun=lambda item, times: runner.rerun(item, base.knowledge_version, times),
    )
    holdout_traps = [i.id for i in trap_items(ctx.items) if i.split is Split.HOLDOUT]
    flips = [i for i in holdout_traps if candidate.passed(i) and not base.passed(i)]
    return {
        "against_experiment": str(base.experiment_id),
        "holdout_passes": [base.passes(Split.HOLDOUT), candidate.passes(Split.HOLDOUT)],
        "dev_passes": [base.passes(Split.DEV), candidate.passes(Split.DEV)],
        "holdout_trap_flips": flips,
        "holdout_trap_total": len(holdout_traps),
        "regressions_dev": regressions.dev,
        "regressions_holdout": regressions.holdout,
        "apparent_not_confirmed": regressions.not_confirmed,
        "confirmations": {k: c.as_dict() for k, c in candidate.confirmations.items()},
    }


EXPERIMENT_MODEL = """
SELECT e.experiment_id FROM ops.experiments e
WHERE e.session_id = %(session)s AND e.knowledge_version = %(version)s
  AND e.finished_at IS NOT NULL
ORDER BY e.started_at DESC
"""


def latest_experiment(session_id: UUID, version: str, model: str) -> ExperimentResult | None:
    """This session's newest finished experiment of `version` whose runs used `model` (the raw
    results name the model of each experiment)."""
    wanted = {
        record["data"].get("experiment_id")
        for record in raw_records("experiment")
        if record["data"].get("model") == model
        and record["data"].get("knowledge_version") == version
    }
    with db.connect(db.Role.APP) as conn:
        rows = conn.execute(
            EXPERIMENT_MODEL, {"session": session_id, "version": version}
        ).fetchall()
        for row in rows:
            if str(row["experiment_id"]) in wanted:
                return experiment_by_id(conn, row["experiment_id"])
    return None


def experiment_by_id(conn: Any, experiment_id: UUID) -> ExperimentResult:
    row = conn.execute(
        "SELECT experiment_id, session_id, knowledge_version, per_example, started_at, "
        "wall_seconds FROM ops.experiments WHERE experiment_id = %s",
        (experiment_id,),
    ).fetchone()
    examples = row["per_example"]
    return ExperimentResult(
        experiment_id=row["experiment_id"],
        session_id=row["session_id"],
        knowledge_version=row["knowledge_version"],
        splits=sorted({Split(e["split"]) for e in examples}),
        results={e["item_id"]: ItemResult.model_validate(e) for e in examples},
        splits_by_item={e["item_id"]: Split(e["split"]) for e in examples},
        started_at=row["started_at"],
        wall_seconds=float(row["wall_seconds"] or 0),
        trace_links={e["item_id"]: list(e.get("trace_urls") or []) for e in examples},
        final_sql={e["item_id"]: e["final_sql"] for e in examples if e.get("final_sql")},
    )


def raw_records(step: str, folder: Path = RESULTS) -> list[dict[str, Any]]:
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(folder.glob(f"{step}-*.json"))
    ]


def analyzer_step(ctx: Context, analyst_model: str, effort: str | None = None) -> dict[str, Any]:
    """The analyzer team (OPENAI_ANALYZER_MODEL), from the failed dev items of this session's
    experiment of the starting version; the candidate is saved as a draft. `effort` replaces the
    pack's reasoning effort for this run only."""
    model = get_settings().analyzer_model
    base = latest_experiment(ctx.session_id, versions.STARTING_VERSION, analyst_model)
    if base is None:
        raise RuntimeError(f"run the experiment of {versions.STARTING_VERSION} first")
    ids = ModelIds()
    with db.connect(db.Role.APP) as conn:
        knowledge = versions.get(conn, versions.STARTING_VERSION)
        name = versions.next_name(conn)
    failed = failed_dev_items(ctx.items, base)
    team = live_team(ctx.items, callbacks=[ids.for_component("analyzer_team")], effort=effort)
    report = team.run(failed, knowledge, name)
    with db.connect(db.Role.APP) as conn:
        versions.save_draft(conn, report.candidate, created_by="analyzer team")
        conn.commit()
    return {
        "model": model,
        "reasoning_effort": effort or pack_config()["models"]["analyzer_team"]["reasoning_effort"],
        "model_ids": ids.as_rows(),
        "candidate_version": name,
        "from_experiment": str(base.experiment_id),
        "failed_dev_items": [f.item.id for f in failed],
        "diagnoses": [d.model_dump() for d in report.diagnoses],
        "proposed": [r.model_dump() for r in report.proposed],
        "critic": [r.model_dump() for r in report.reviews],
        "kept_by_critic": [r.id for r in report.kept],
        "guidance_rejections": report.guidance_rejections,
        "guard": [asdict(g) for g in report.guard],
        "accepted": [r.model_dump() for r in report.accepted],
        "candidate": report.candidate.model_dump(),
    }


def analyzer_effort_step(ctx: Context, target: AnalystTarget, effort: str) -> dict[str, Any]:
    """The analyzer team at another reasoning effort, from the same failed dev items as the
    analyzer step (this session's experiment of the starting version), then the candidate
    experiment against that same experiment, so its holdout passes compare with the runs at the
    pack's effort recorded by the analyzer step."""
    analyzer = analyzer_step(ctx, target.model, effort=effort)
    measured = experiment_step(ctx, target, analyzer["candidate_version"])
    comparison = measured.get("comparison") or {}
    earlier = [r["data"] for r in raw_records("analyzer") if r.get("step") == "analyzer"]
    return {
        "reasoning_effort": effort,
        "candidate_version": analyzer["candidate_version"],
        "failed_dev_items": analyzer["failed_dev_items"],
        "same_failed_items_as_analyzer_runs": sum(
            e.get("failed_dev_items") == analyzer["failed_dev_items"] for e in earlier
        ),
        "holdout_passes": comparison.get("holdout_passes"),
        "holdout_trap_flips": comparison.get("holdout_trap_flips"),
        "regressions": [comparison.get("regressions_dev"), comparison.get("regressions_holdout")],
        "analyzer": analyzer,
        "experiment": measured,
    }


def stability_step(
    ctx: Context, target: AnalystTarget, version: str, limits: Limits
) -> dict[str, Any]:
    runner = ctx.runner(target, Scheme.from_pack(), stream=False)
    report = stability(runner, ctx.items, version, session_id=ctx.session_id, limits=limits)
    return {
        "knowledge_version": version,
        "limits": asdict(report.limits),
        "items": [asdict(i) for i in report.items],
        "unstable": [i.item_id for i in report.unstable],
        "lines": report.lines(),
    }


AGENT_CONFIGS = {
    "scout and reviewer on": (True, True),
    "scout off": (False, True),
    "reviewer off": (True, False),
    "both off": (False, False),
}


AMBIGUOUS = (
    "How many loyal customers do we have?",
    "Who are our VIP customers? Give their customer ids.",
)


def agents_step(
    ctx: Context,
    target: AnalystTarget,
    item_ids: Sequence[str],
    questions: Sequence[str] = AMBIGUOUS,
) -> dict[str, Any]:
    """Tokens and latency per question with the schema scout and the reviewer on and off, the
    reviewer's verdict on each answer under the starting knowledge, and what the class analyst
    does with questions no business rule defines (the premise of Assignment 2)."""
    chosen = [ctx.by_id()[i].model_copy(update={"split": Split.DEV}) for i in item_ids]
    configs = {}
    for label, (scout, reviewer) in AGENT_CONFIGS.items():
        variant = target.with_agents(scout=scout, reviewer=reviewer)
        result = ctx.runner(variant, Scheme.from_pack(), stream=False).run(
            chosen, versions.STARTING_VERSION, session_id=ctx.session_id, splits=[Split.DEV]
        )
        rows = run_rows(variant)
        undefined = []
        for question in questions:
            envelope = variant(question, versions.STARTING_VERSION)
            stats = variant.stats[-1]
            undefined.append(
                {
                    "question": question,
                    "run_status": stats.status,
                    "answer_status": envelope.status.value,
                    "answer_text": envelope.answer_text,
                    "assumptions": envelope.assumptions,
                    "final_sql": envelope.final_sql,
                    "reviewer": stats.reviewer,
                    "reviewer_reasons": stats.reviewer_reasons,
                    "run_id": stats.run_id,
                }
            )
        configs[label] = {
            "undefined_terms": undefined,
            "scout": scout,
            "reviewer": reviewer,
            "runs": rows,
            "passed": {i: result.passed(i) for i in result.results},
            "trace_urls": result.trace_links,
            "mean_tokens": round(sum(r["tokens_in"] + r["tokens_out"] for r in rows) / len(rows)),
            "mean_seconds": round(sum(r["seconds"] for r in rows) / len(rows), 1),
        }
    return {
        "knowledge_version": versions.STARTING_VERSION,
        "items": list(item_ids),
        "configs": configs,
    }


def confirm_choice(folder: Path = RESULTS, known: set[str] | None = None) -> tuple[str, str]:
    """(holdout item, version) for the confirming re-run: a real apparent holdout regression from
    the newest candidate experiment when there is one, else the holdout item whose stability pass
    count sat closest to the middle (a flaky item, chosen on purpose). Only items in `known` (the
    current benchmark) are chosen."""
    allowed = (lambda item_id: item_id in known) if known is not None else (lambda item_id: True)
    for record in reversed(raw_records("experiment", folder)):
        comparison = record["data"].get("comparison") or {}
        for item_id, found in (comparison.get("confirmations") or {}).items():
            if found.get("split") == Split.HOLDOUT.value and allowed(item_id):
                return item_id, record["data"]["knowledge_version"]
    for record in reversed(raw_records("stability", folder)):
        rows = [r for r in record["data"]["items"] if allowed(r["item_id"])]
        if rows:
            middle = min(rows, key=lambda r: abs(r["passes"] - r["runs"] / 2))
            return middle["item_id"], record["data"]["knowledge_version"]
    raise RuntimeError("run an experiment of a candidate or the stability filter first")


def confirm_step(ctx: Context, target: AnalystTarget, item_id: str, version: str) -> dict[str, Any]:
    """The confirming re-run on one holdout item, through the gate's own code: the item is taken
    as an apparent regression (passed under the starting version, failed under `version`), and
    the scheme's re-runs under `version` confirm or clear it."""
    item = ctx.by_id()[item_id]
    scheme = Scheme.from_pack()
    runner = ctx.runner(target, scheme, stream=False)
    first = runner.run([item], version, session_id=ctx.session_id, splits=[item.split])
    active = ExperimentResult(
        experiment_id=first.experiment_id,
        session_id=ctx.session_id,
        knowledge_version=versions.STARTING_VERSION,
        splits=[item.split],
        results={item_id: ItemResult(item_id=item_id, passed=True, reason="declared as passed")},
        splits_by_item={item_id: item.split},
        started_at=first.started_at,
        wall_seconds=0.0,
    )
    regressions = find_regressions(
        [item], active, first, lambda i, n: runner.rerun(i, version, n), scheme
    )
    return {
        "item_id": item_id,
        "knowledge_version": version,
        "first_runs": first.results[item_id].run_passes,
        "first_passed": first.passed(item_id),
        "apparent_regression": not first.passed(item_id),
        "confirmation": {k: c.as_dict() for k, c in first.confirmations.items()},
        "confirmed": regressions.holdout,
        "cleared": regressions.not_confirmed,
        "trace_urls": first.trace_links.get(item_id, []),
    }
