"""The live check of Assignment 4: Hill-climbing loop. Run it with:
make check-assignment NAME=hill-climbing-loop

Deterministic first, against the real warehouses (requirements 1 to 8): the six repeat-customer
items, their gold and naive SQL on both databases, the family in the pack, the minimum-holdout rule,
and the gate, the overfit guard, and the measurement left as class wrote them. Then the cost
estimates (the analyzer team, and the benchmark separately) and the OpenAI key, then the done-when
scenario live, with the class measurement: a baseline experiment of the active version, the
analyzer team on its failed dev items with the planted over-broad rule among the proposals, a
candidate experiment, confirmed regressions, the gate, a human approval, and the class clearance for
the unattended level (requirements 9 and 10).
The active knowledge version is put back at the end. The benchmark runs in this process, so the
check's spend cap is held here: no analyst run starts once the runs under way could take the check
past it, and an experiment that met the cap is never kept.
"""

from __future__ import annotations

import hashlib
import json
import threading
from datetime import UTC, datetime
from pathlib import Path

import httpx
import yaml

from datapilot import db
from datapilot.assignments.cost import Cap, Planned
from datapilot.assignments.live import trace_link, traced_step
from datapilot.assignments.report import LiveRun, Result
from datapilot.config import pack_config
from datapilot.contracts import (
    AnswerEnvelope,
    BenchmarkItem,
    CriticDecision,
    ProposedRule,
    Split,
)
from datapilot.contracts.live import NoLiveBaseline
from datapilot.loop3_events import autonomy
from datapilot.loop4_hill_climbing import eligibility, extension, gate, store, targets
from datapilot.loop4_hill_climbing.analyzer import FailedItem, live_team
from datapilot.loop4_hill_climbing.evaluator import ExecutionEvaluator, compare
from datapilot.loop4_hill_climbing.experiment import ExperimentResult, ExperimentRunner
from datapilot.loop4_hill_climbing.measurement import Scheme
from datapilot.loop4_hill_climbing.pack_files import load_benchmark
from datapilot.loop4_hill_climbing.runner import candidate_overfit_flags
from datapilot.loop4_hill_climbing.sql_runner import WAREHOUSES, ReadOnlyRunner
from datapilot.settings import PLATFORM

SLUG = "hill-climbing-loop"
FAMILY = "repeat_customers"
HERE = Path(__file__).resolve().parent
LOOP4 = PLATFORM / "src" / "datapilot" / "loop4_hill_climbing"
# Fingerprints of what the assignment must not change. A unit test of the course build keeps them
# equal to the class files, so a change on the class side updates them in the same commit.
UNCHANGED = {
    "gate.py": "905f65621abe286b1b4ce57a57412381de3838b41be0f36146380e36816888d1",
    "overfit_guard.py": "4e01dcac8a2c6cd4e408193a79440c3f2b2ee7e87c9d1d5cb22abceb1f3781c8",
    "measurement.py": "03d13f5b2c2fb94ed07775b14539935e4bd92626b66be4cdfdf47be016db4323",
}
EVALUATION = "c0b5512d82d0d3ffb162146b9fec95f00dac9b20413c8984cf2519096c5025dc"
RUNNER = ReadOnlyRunner()


def fingerprint(path: Path) -> str:
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    return hashlib.sha256(text.encode()).hexdigest()


def evaluation_fingerprint() -> str:
    return hashlib.sha256(
        json.dumps(pack_config()["evaluation"], sort_keys=True).encode()
    ).hexdigest()


def family_items() -> list[BenchmarkItem]:
    return [i for i in load_benchmark() if i.metric_family == FAMILY]


def planted_rule() -> ProposedRule:
    return ProposedRule.model_validate(
        yaml.safe_load((HERE / "planted-rule.yaml").read_text(encoding="utf-8"))
    )


# --- deterministic requirements -----------------------------------------------------------------
def _six_items() -> str | None:
    items = family_items()
    incomplete = [i.id for i in items if not (i.question and i.gold_sql and i.naive_sql)]
    if len(items) != 6 or incomplete:
        return f"add 6 items with metric_family {FAMILY}, each with gold and naive SQL; found " + (
            f"{len(items)}" + (f", incomplete: {incomplete}" if incomplete else "")
        )
    return None


def _holdout() -> str | None:
    held = sum(i.split is Split.HOLDOUT for i in family_items())
    return None if held >= 3 else f"put at least 3 of the 6 in the holdout split; {held} are"


def _gold_runs() -> str | None:
    for item in family_items():
        for warehouse in WAREHOUSES:
            first = RUNNER.run(item.gold_sql or "", warehouse, max_rows=1000)
            again = RUNNER.run(item.gold_sql or "", warehouse, max_rows=1000)
            if not first.rows or any(v is None for r in first.rows for v in r):
                return f"{item.id}: the gold SQL returns no rows or a null on {warehouse}"
            if first.rows != again.rows:
                return f"{item.id}: the gold SQL is not deterministic on {warehouse}"
    return None


def _traps() -> str | None:
    for item in family_items():
        if not item.traps:
            return f"{item.id}: name the traps it touches"
        for warehouse in WAREHOUSES:
            gold = RUNNER.run(item.gold_sql or "", warehouse, max_rows=1000).rows
            naive = RUNNER.run(item.naive_sql or "", warehouse, max_rows=1000).rows
            same, _ = compare(naive, gold, tolerance=item.numeric_tolerance, order_matters=False)
            if same:
                return f"{item.id}: the naive SQL gives the gold answer on {warehouse}"
    return None


def _in_pack() -> str | None:
    families = pack_config()["autonomy"]["metric_families"]
    return None if FAMILY in families else f"add {FAMILY} to autonomy.metric_families in pack.yaml"


def _all_passed(_item_id: str) -> bool:
    return True  # a policy probe: the most favourable holdout results there could be


def _minimum() -> str | None:
    if any(extension.enough_holdout_items(n) for n in (0, 1, 2)):
        return "a family with fewer than three holdout items must not reach the unattended level"
    families = pack_config()["autonomy"]["metric_families"]
    eligible = eligibility.eligible_families(load_benchmark(), _all_passed, families)
    if "aov" in eligible:
        return "aov has one holdout item: even with it passing, aov is not eligible"
    return None


def _eligible() -> str | None:
    if not extension.enough_holdout_items(3):
        return "three holdout items, all passing, are enough"
    families = pack_config()["autonomy"]["metric_families"]
    eligible = eligibility.eligible_families(load_benchmark(), _all_passed, families)
    return None if FAMILY in eligible else f"{FAMILY}, with every holdout item passing, is eligible"


def _unchanged() -> str | None:
    changed = [name for name, want in UNCHANGED.items() if fingerprint(LOOP4 / name) != want]
    if evaluation_fingerprint() != EVALUATION:
        changed.append("the evaluation block of pack.yaml")
    return f"put back, unchanged: {', '.join(changed)}" if changed else None


# --- the live benchmark ----------------------------------------------------------------------
class RecordingTarget:
    """The live analyst, keeping each dev item's answer of this experiment for its failure
    analysis (the analyzer team reads the agent's SQL). Nothing is kept across experiments."""

    def __init__(self, analyst: targets.AnalystTarget, cap: Cap | None = None) -> None:
        self.analyst = analyst
        self.cap = cap
        self.answers: dict[str, AnswerEnvelope] = {}
        self.lock = threading.Lock()

    def __call__(self, question: str, version: str) -> AnswerEnvelope:
        if self.cap is not None:
            self.cap.check()  # no new analyst run at the spend cap
        answer = self.analyst(question, version)
        with self.lock:
            self.answers[question] = answer
        return answer


class CappedRunner(ExperimentRunner):
    """The class runner with the check's spend cap around each experiment and re-run. Inside an
    experiment a run refused at the cap counts as a failed item, so an experiment that met the cap
    raises instead of returning, and is never saved or shared as a baseline."""

    def __init__(self, *args, cap: Cap | None = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.cap = cap

    def _held(self) -> None:
        if self.cap is not None:
            self.cap.check()

    def run(self, *args, **kwargs) -> ExperimentResult:
        self._held()
        result = super().run(*args, **kwargs)
        self._held()
        return result

    def rerun(self, item: BenchmarkItem, knowledge_version: str, times: int) -> list[bool]:
        self._held()
        passes = super().rerun(item, knowledge_version, times)
        self._held()
        return passes


def _experiment(runner: ExperimentRunner, items, version: str, session) -> ExperimentResult:
    result = runner.run(items, version, session_id=session)
    with db.connect(db.Role.APP) as conn:
        store.save_experiment(
            conn,
            result,
            holdout_repeats=runner.scheme.holdout_repeats,
            concurrency=runner.concurrency,
        )
        conn.commit()
    return result


def _step_run(ctx, trace_id: str, started: datetime, passed: bool, what: str) -> LiveRun:
    return LiveRun(
        passed,
        what,
        run_id=trace_id,
        started_at_utc=started.isoformat(timespec="seconds"),
        session_id=str(ctx.stack.session_id),
        trace=trace_link(trace_id),
    )


def _save_draft(version_name: str, candidate) -> None:
    with db.connect(db.Role.APP) as conn:
        conn.execute(
            "INSERT INTO ops.knowledge_versions (version, yaml, status, created_by) "
            "VALUES (%s, %s, 'draft', 'analyzer team')",
            (version_name, yaml.safe_dump(candidate.model_dump(), sort_keys=False)),
        )
        conn.commit()


def _activate(version_name: str) -> None:
    with db.connect(db.Role.APP) as conn:
        conn.execute("UPDATE ops.knowledge_versions SET status = 'retired' WHERE status = 'active'")
        conn.execute(
            "UPDATE ops.knowledge_versions SET status = 'active', activated_at = now() "
            "WHERE version = %s",
            (version_name,),
        )
        conn.commit()


def active_version() -> str:
    with db.connect(db.Role.APP) as conn:
        return conn.execute(
            "SELECT version FROM ops.knowledge_versions WHERE status = 'active'"
        ).fetchone()["version"]


def session_baseline(items: list[BenchmarkItem]) -> ExperimentResult | None:
    """The open live session's baseline experiment of the active version, when it measured every
    item of today's benchmark. As in class, the gate compares experiments of one live session, so
    every solution checked in the session shares one baseline instead of running it again."""
    with db.connect(db.Role.APP) as conn:
        try:
            baseline = store.baseline_for(conn, active_version())
        except NoLiveBaseline:
            return None
    return baseline if {i.id for i in items} <= set(baseline.results) else None


def _benchmark(ctx) -> Result:
    """Adds requirement 9 as soon as it is judged, so a stop at the spend cap keeps its line;
    returns requirement 10."""
    session = ctx.stack.session_id
    active = active_version()
    ctx.on_exit(lambda: _activate(active))
    items = load_benchmark()
    cfg = pack_config()
    target = RecordingTarget(
        targets.analyst(tags=["track:assignments", f"feature:{SLUG}"]), ctx.cap
    )
    runner = CappedRunner(
        target=target,
        evaluator=ExecutionEvaluator.live(),
        scheme=Scheme.from_pack(),
        concurrency=int(cfg["evaluation"]["concurrency"]),
        cap=ctx.cap,
    )
    by_id = {i.id: i for i in items}

    started = datetime.now(UTC)
    with traced_step("assignment check: analyzer team", {"assignment": SLUG}) as trace_id:
        shared = session_baseline(items)
        baseline = shared or _experiment(runner, items, active, session)
        ctx.report.say(
            f"Baseline: experiment {baseline.experiment_id} of {active}, "
            + ("shared from earlier in this live session" if shared else "run now")
        )
        # A shared baseline holds results, not the agent's SQL: the failure analyst then works from
        # the evaluator's reasons, the trap labels, and the reference SQL.
        failed = [
            FailedItem(by_id[item_id], target.answers.get(by_id[item_id].question), result)
            for item_id, result in baseline.results.items()
            if by_id[item_id].split is Split.DEV and not result.passed
        ]
        name = f"candidate-{datetime.now(UTC):%Y%m%d-%H%M%S}"
        planted = planted_rule()
        report = live_team(items).run(
            failed, targets.knowledge_from_ops(active), name, extra_proposals=[planted]
        )
    review = next((r for r in report.reviews if r.rule_id == planted.id), None)
    proposed_ids = {r.id for r in report.proposed}
    dropped = review is not None and review.decision is CriticDecision.DROP and bool(review.reason)
    adds_nothing = {r.id for r in report.accepted} <= proposed_ids
    what = (
        f"planted rule: {review.decision.value if review else 'no review'}"
        + (f' ("{review.reason}")' if review else "")
        + f"; {len(report.accepted)} of {len(report.proposed)} proposed rules accepted"
    )
    critic = Result(
        9,
        "Live: the critic drops the planted over-broad rule with a reason, and adds no rule",
        dropped and adds_nothing,
        "" if dropped and adds_nothing else "give the critic a reason to drop over-broad rules",
        [_step_run(ctx, trace_id, started, dropped and adds_nothing, what)],
        "one analyzer run, as in class",
    )
    ctx.report.add(critic)

    started = datetime.now(UTC)
    with traced_step("assignment check: candidate and gate", {"assignment": SLUG}) as trace_id:
        _save_draft(name, report.candidate)
        candidate = _experiment(runner, items, name, session)
        with db.connect(db.Role.APP) as conn:
            regressions = gate.find_regressions(
                items,
                baseline,
                candidate,
                lambda item, times: runner.rerun(item, name, times),
                runner.scheme,
                sink=store.OpsStepSink(conn),
                active_rerun=lambda item, times: runner.rerun(item, active, times),
            )
        # the class gate's fourth condition: the candidate's new rules pass the overfit guard
        flags = candidate_overfit_flags(items, report.candidate, targets.knowledge_from_ops(active))
        decision = gate.decide(
            baseline, candidate, regressions, approved_by=None, overfit_flags=flags
        )
        if decision.ready_for_approval:
            httpx.post(
                f"{ctx.stack.api_url}/knowledge/{name}/approve",
                json={"approved_by": "make check-assignment"},
                timeout=30,
            ).raise_for_status()
            decision = gate.decide(
                baseline,
                candidate,
                regressions,
                approved_by="make check-assignment",
                overfit_flags=flags,
            )
        with db.connect(db.Role.APP) as conn:
            store.save_decision(conn, decision)
            conn.commit()
        eligible: list[str] = []
        if decision.verdict == "promoted":
            _activate(name)
            # the class clearance: the minimum number of holdout items first, then every holdout
            # item at 2 of 3 runs, an item that fell short re-run 3 more times
            eligible = eligibility.confirmed_clearance(
                items,
                candidate,
                lambda item, times: runner.rerun(item, name, times),
                runner.scheme,
                cfg["autonomy"]["metric_families"],
            ).cleared
            with db.connect(db.Role.APP) as conn:
                for family in eligible:
                    autonomy.mark_eligible(conn, family, name)
                conn.commit()
    covered = all(i.id in candidate.results for i in family_items())
    ok = decision.verdict == "promoted" and regressions.total == 0 and covered
    ok = ok and "aov" not in eligible
    family = [i for i in family_items() if i.split is Split.HOLDOUT]
    family_passes = sum(candidate.passed(i.id) for i in family)
    what = (
        f"{decision.sentence} Holdout {decision.candidate_holdout_passes} of "
        f"{decision.holdout_total} against {decision.active_holdout_passes}; confirmed "
        f"regressions {regressions.total}; the new family passes {family_passes} of "
        f"{len(family)} holdout items; eligible for the unattended level: "
        f"{', '.join(eligible) or 'none'}"
    )
    promoted = Result(
        10,
        "Live: the gate promotes a version covering the new family with zero regressions",
        ok,
        "" if ok else "the candidate must beat the active version on holdout with no regression",
        [_step_run(ctx, trace_id, started, ok, what)],
        "the class measurement: holdout items 3 runs, passing on 2; every apparent regression "
        "confirmed by re-runs; zero confirmed regressions; human approval",
    )
    return promoted


def run(ctx) -> None:
    report = ctx.report
    items_ok = report.check(
        1, "Six repeat-customer items, each with gold and naive SQL", _six_items
    )
    report.check(2, "At least three of them are in the holdout split", _holdout)
    report.check(
        3, "Every gold query runs on both warehouses, with rows, the same twice", _gold_runs
    )
    report.check(4, "Every naive query gives a different answer from gold on both", _traps)
    report.check(5, "The family is in autonomy.metric_families", _in_pack)
    report.check(
        6, "Fewer than three holdout items keep a family below the unattended level", _minimum
    )
    report.check(7, "Three or more holdout items, all passing, make a family eligible", _eligible)
    report.check(8, "The gate, the overfit guard, and the measurement are unchanged", _unchanged)

    texts = [
        "Live: the critic drops the planted over-broad rule with a reason, and adds no rule",
        "Live: the gate promotes a version covering the new family with zero regressions",
    ]
    if not items_ok.passed:
        ctx.live_gate([], none_because="requirement 1 failed, so the family has no items")
        for offset, text in enumerate(texts):
            report.not_run(9 + offset, text, "requirement 1 failed first")
        return
    items = load_benchmark()
    scheme = Scheme.from_pack()
    per_experiment = sum(scheme.repeats(i.split) for i in items)
    experiments = 1 if session_baseline(items) else 2
    which = (
        "the candidate only: this live session's baseline is shared"
        if experiments == 1
        else ("the baseline and the candidate")
    )
    report.say()
    report.say("The benchmark is the costly part of this check; its estimate is given on its own.")
    ctx.live_gate(
        [
            Planned(
                "analyzer team calls (failure analyst, rule writer, critic)", 3, ctx.analyzer_model
            ),
            Planned(
                f"analyst runs for the benchmark ({which}; {per_experiment} runs per experiment; "
                "re-runs of apparent regressions and of holdout items short at clearance come on "
                "top)",
                experiments * per_experiment,
                ctx.agent_model,
            ),
        ],
        live=list(enumerate(texts, start=9)),
    )
    report.add(_benchmark(ctx))
