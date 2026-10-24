"""The live check of Assignment 4: Hill-climbing loop. Run it with:
make check-assignment NAME=hill-climbing-loop

Deterministic first, against the real warehouses (requirements 1 to 8): the six repeat-customer
items, their gold and naive SQL on both databases, the family in the pack, the minimum-holdout rule,
and the gate, the overfit guard, and the measurement left as class wrote them. Then the cost
estimates (the analyzer team, and the benchmark separately) and the OpenAI key, then the done-when
scenario live, with the class measurement: a baseline experiment of the active version, the
analyzer team on its failed dev items with the planted over-broad rule among the proposals, written
as in class (analyzer.candidates rule sets in pack.yaml, each measured on the dev split, one kept by
fewer dev regressions, then more dev passes), a candidate experiment, confirmed regressions, the
gate, a human approval, and the class clearance for the unattended level (requirements 9 and 10).
The active knowledge version is put back at the end. The benchmark runs in this process, so the
check's spend cap and its stack's kill switch are held here: no analyst run starts once the runs
under way could take the check past the cap, the cap engages the kill switch so the runs in flight
stop at their next model call, a kill switch engaged from outside stops the check (exit 2), and an
experiment that met either is never kept. A baseline experiment is shared from earlier in the live
session only when it measured exactly today's items, each with the same question, gold SQL, split,
and tolerance (item_fingerprint); otherwise the check runs the baseline again and says why.
"""

from __future__ import annotations

import hashlib
import json
import threading
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import httpx
import yaml

from datapilot import db
from datapilot.assignments.cost import Cap, Planned
from datapilot.assignments.live import in_process_kill_switch_stop, trace_link, traced_step
from datapilot.assignments.report import LiveRun, Result, Stop
from datapilot.config import pack_config
from datapilot.contracts import (
    AnswerEnvelope,
    BenchmarkItem,
    CriticDecision,
    ProposedRule,
    Split,
)
from datapilot.contracts.live import NoLiveBaseline
from datapilot.loop3_events import autonomy, killswitch
from datapilot.loop4_hill_climbing import candidates, eligibility, extension, gate, store, targets
from datapilot.loop4_hill_climbing.analyzer import FailedItem, live_team
from datapilot.loop4_hill_climbing.evaluator import ExecutionEvaluator, compare
from datapilot.loop4_hill_climbing.experiment import ExperimentResult, ExperimentRunner
from datapilot.loop4_hill_climbing.measurement import Scheme
from datapilot.loop4_hill_climbing.pack_files import load_benchmark
from datapilot.loop4_hill_climbing.runner import candidate_overfit_flags, kill_switch_stop
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
# What a check of a working solution spent in the build's verification, as docs/costs.md gives it
# (the Assignments table there is the one source of these figures). A later check of a live session
# was measured on 23 October 2026 with two candidates, 13.58 and 23.95 cents; a first check, which
# also runs the baseline, was measured only with one candidate, 30.66 cents.
TYPICAL_LATER = "about 14 to 24 cents (13.58 and 23.95, two later checks with two candidates)"
TYPICAL_FIRST = (
    "about 38 cents as a first check (30.66 measured with one candidate, and about 7 more for the "
    "second candidate's 56 dev runs)"
)


def typical(first: bool) -> str:
    return TYPICAL_FIRST if first else TYPICAL_LATER


def fingerprint(path: Path) -> str:
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    return hashlib.sha256(text.encode()).hexdigest()


def evaluation_fingerprint() -> str:
    return hashlib.sha256(
        json.dumps(pack_config()["evaluation"], sort_keys=True).encode()
    ).hexdigest()


def family_items() -> list[BenchmarkItem]:
    return [i for i in load_benchmark() if i.metric_family == FAMILY]


def planted_rule(failed_ids: list[str] | None = None) -> ProposedRule:
    """The planted over-broad rule. Its evidence names the learner's own repeat-customer dev item
    that failed (else their first repeat-customer dev item), so the critic judges the rule for what
    it claims, never for citing an id the learner did not write."""
    rule = ProposedRule.model_validate(
        yaml.safe_load((HERE / "planted-rule.yaml").read_text(encoding="utf-8"))
    )
    dev = [i.id for i in family_items() if i.split is Split.DEV]
    cited = [i for i in failed_ids or [] if i in dev] or dev[:1]
    return rule.model_copy(update={"evidence_example_ids": cited[:1]}) if cited else rule


NO_ITEMS = (
    "hill-climbing-loop-1: there are no repeat-customer items to judge yet; add the six items "
    "(requirement 1) first"
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
    if not family_items():
        raise NotImplementedError(NO_ITEMS)
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
    if not family_items():
        raise NotImplementedError(NO_ITEMS)
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
        return (
            "hill-climbing-loop-3: enough_holdout_items must refuse a family with fewer than "
            "three holdout items"
        )
    families = pack_config()["autonomy"]["metric_families"]
    eligible = eligibility.eligible_families(load_benchmark(), _all_passed, families)
    if "aov" in eligible:
        return (
            "hill-climbing-loop-3: aov has one holdout item, so even with it passing it is not "
            "eligible"
        )
    return None


def _eligible() -> str | None:
    benchmark = load_benchmark()
    held = eligibility.holdout_by_family(benchmark)
    largest = max((len(ids) for ids in held.values()), default=0)
    refused = [n for n in range(3, max(10, largest) + 1) if not extension.enough_holdout_items(n)]
    if refused:
        return (
            "hill-climbing-loop-3: enough_holdout_items must allow every family with three or "
            f"more holdout items; it refuses {', '.join(str(n) for n in refused)}"
        )
    families = pack_config()["autonomy"]["metric_families"]
    eligible = eligibility.eligible_families(benchmark, _all_passed, families)
    left_out = [
        f"{family} ({len(held[family])} holdout items)"
        for family in families
        if family != FAMILY and len(held.get(family, [])) >= 3 and family not in eligible
    ]
    if left_out:
        return (
            "hill-climbing-loop-3: with every holdout item passing, these families have three or "
            f"more holdout items and must be eligible: {', '.join(left_out)}"
        )
    if FAMILY in eligible:
        return None
    return (
        f"{FAMILY} must be eligible once every holdout item passes: it needs its items "
        "(hill-climbing-loop-1) and its place in autonomy.metric_families"
    )


def _unchanged() -> str | None:
    changed = [name for name, want in UNCHANGED.items() if fingerprint(LOOP4 / name) != want]
    if evaluation_fingerprint() != EVALUATION:
        changed.append("the evaluation block of pack.yaml")
    return f"put back, unchanged: {', '.join(changed)}" if changed else None


# --- the live benchmark ----------------------------------------------------------------------
class Held:
    """What may stop the in-process benchmark, checked before each analyst run and around each
    experiment and re-run: the spend cap, through the check's api, which engages the stack's kill
    switch at the cap so the runs in flight stop at their next model call (each run's
    external_stop); and a kill switch engaged from outside the check, such as on its console,
    which stops the check (exit 2), as a run the workers blocked does."""

    def __init__(self, api, *, engaged: Callable[[], bool] = killswitch.engaged) -> None:
        self.api = api
        self.engaged = engaged

    def check(self) -> None:
        self.api.guard()  # CapReached at the spend cap, the kill switch engaged once
        if not self.api.engaged_at_cap and self.engaged():
            raise Stop(in_process_kill_switch_stop(self.api.slug or SLUG))


class RecordingTarget:
    """The live analyst, keeping each dev item's answer of this experiment for its failure
    analysis (the analyzer team reads the agent's SQL). Nothing is kept across experiments."""

    def __init__(self, analyst: targets.AnalystTarget, cap: Cap | Held | None = None) -> None:
        self.analyst = analyst
        self.cap = cap
        self.answers: dict[str, AnswerEnvelope] = {}
        self.lock = threading.Lock()

    def __call__(self, question: str, version: str) -> AnswerEnvelope:
        if self.cap is not None:
            self.cap.check()  # no new analyst run at the spend cap or the kill switch
        answer = self.analyst(question, version)
        with self.lock:
            self.answers[question] = answer
        return answer


class CappedRunner(ExperimentRunner):
    """The class runner with the check's spend cap and kill switch (Held) around each experiment
    and re-run. Inside an experiment a run refused at the cap or stopped by the kill switch counts
    as a failed item, so an experiment that met either raises instead of returning, and is never
    saved or shared as a baseline."""

    def __init__(self, *args, cap: Cap | Held | None = None, **kwargs) -> None:
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


# What an item's measurement depends on: an experiment measured under other values of these says
# nothing about today's item.
MEASURED_FIELDS = {
    "id",
    "question",
    "gold_sql",
    "split",
    "numeric_tolerance",
    "order_matters",
    "expected_status",
}
FINGERPRINT_EXAMPLES = """
UPDATE ops.experiments
SET per_example = (
    SELECT jsonb_agg(
        e || jsonb_build_object('item_fingerprint', %(prints)s::jsonb -> (e ->> 'item_id'))
        ORDER BY position)
    FROM jsonb_array_elements(per_example) WITH ORDINALITY AS x(e, position))
WHERE experiment_id = %(experiment_id)s
"""


def item_fingerprint(item: BenchmarkItem) -> str:
    data = item.model_dump(mode="json", include=MEASURED_FIELDS)
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def baseline_mismatch(
    items: list[BenchmarkItem], baseline: ExperimentResult, stored: dict[str, str | None]
) -> list[str]:
    """The items the baseline did not measure as they are today: added, removed, or changed in
    question, gold SQL, split, or tolerance (or measured before fingerprints were stored)."""
    today = {i.id: item_fingerprint(i) for i in items}
    added_or_removed = set(today) ^ set(baseline.results)
    changed = {i for i, want in today.items() if i in baseline.results and stored.get(i) != want}
    return sorted(added_or_removed | changed)


def _stored_fingerprints(conn, experiment_id) -> dict[str, str | None]:
    row = conn.execute(
        "SELECT per_example FROM ops.experiments WHERE experiment_id = %s", (experiment_id,)
    ).fetchone()
    examples = (row["per_example"] if row else None) or []
    return {e["item_id"]: e.get("item_fingerprint") for e in examples}


def _experiment(runner: ExperimentRunner, items, version: str, session) -> ExperimentResult:
    result = runner.run(items, version, session_id=session)
    with db.connect(db.Role.APP) as conn:
        store.save_experiment(
            conn,
            result,
            holdout_repeats=runner.scheme.holdout_repeats,
            concurrency=runner.concurrency,
        )
        conn.execute(
            FINGERPRINT_EXAMPLES,
            {
                "prints": json.dumps({i.id: item_fingerprint(i) for i in items}),
                "experiment_id": result.experiment_id,
            },
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


def session_baseline(items: list[BenchmarkItem]) -> tuple[ExperimentResult | None, str]:
    """The open live session's baseline experiment of the active version, when it measured
    exactly today's items as they are now (item_fingerprint), and else None with the reason. As in
    class, the gate compares experiments of one live session, so every solution checked in the
    session shares one baseline instead of running it again, until an item changes."""
    with db.connect(db.Role.APP) as conn:
        try:
            baseline = store.baseline_for(conn, active_version())
        except NoLiveBaseline:
            return None, "this live session has no baseline yet"
        stored = _stored_fingerprints(conn, baseline.experiment_id)
    stale = baseline_mismatch(items, baseline, stored)
    if not stale:
        return baseline, ""
    shown = ", ".join(stale[:5]) + (f", and {len(stale) - 5} more" if len(stale) > 5 else "")
    return None, (
        f"the session's baseline {str(baseline.experiment_id)[:8]} measured these items "
        f"otherwise than they are now (question, gold SQL, split, or tolerance): {shown}"
    )


def _team_runs(team, failed, knowledge, name, baseline, runner, items, session, planted):
    """The analyzer team as in class: with analyzer.candidates above one (pack.yaml), each candidate
    from its own team run, measured on the dev split only, every item once, under its own retired
    version; the holdout split never takes part in the choice. The planted rule is among the
    proposals of every run."""
    if candidates.count() == 1:
        report = team.run(failed, knowledge, name, extra_proposals=[planted])
        return [candidates.CandidateRun("A", name, report)]
    runs = []
    for index in range(candidates.count()):
        version = candidates.selection_version(name, index)
        report = team.run(failed, knowledge, version, extra_proposals=[planted])
        with db.connect(db.Role.APP) as conn:
            candidates.save_selection_draft(conn, report.candidate)
            conn.commit()
        dev = runner.run(items, version, session_id=session, splits=[Split.DEV])
        regressions = candidates.dev_regressions(baseline, dev)
        runs.append(
            candidates.CandidateRun(candidates.label(index), version, report, dev, regressions)
        )
    return runs


def _critic_line(run, planted_id: str) -> tuple[bool, str]:
    """Whether the critic of one team run dropped the planted rule with a reason and added no rule
    of its own, and what it did."""
    report = run.report
    review = next((r for r in report.reviews if r.rule_id == planted_id), None)
    dropped = review is not None and review.decision is CriticDecision.DROP and bool(review.reason)
    adds_nothing = {r.id for r in report.accepted} <= {r.id for r in report.proposed}
    what = (
        f"candidate {run.label}: planted rule "
        + (f'{review.decision.value} ("{review.reason}")' if review else "not reviewed")
        + f"; {len(report.accepted)} of {len(report.proposed)} proposed rules accepted"
    )
    return dropped and adds_nothing, what


BLOCKED_BY_MODEL = (
    "the gate blocked the rule set the analyzer team wrote this time; the live run line says why. "
    "With requirements 1 to 9 passing, that is most often the model's rule set rather than your "
    "files, so run the check again; if the same accepted rule causes it every time, sharpen your "
    "critic's guidance (hill-climbing-loop-2)"
)


def promotion_verdict(
    verdict: str, regressions: int, missing: list[str], eligible: list[str]
) -> tuple[bool, str]:
    """Requirement 10: passed, and what to fix. A missing family item or aov at the unattended
    level fails on the solution itself; a gate that blocked the model's rule set says so."""
    if missing:
        return False, "every repeat-customer item must be measured: check its split and question"
    if "aov" in eligible:
        return (
            False,
            "aov must not reach the unattended level: enough_holdout_items needs a minimum",
        )
    if verdict != "promoted" or regressions:
        return False, BLOCKED_BY_MODEL
    return True, ""


def analyst_target() -> targets.AnalystTarget:
    """The live analyst, stopped at its next model or tool call once the stack's kill switch is
    engaged, as the class hill-climbing runner's target is."""
    return replace(
        targets.analyst(tags=["track:assignments", f"feature:{SLUG}"]),
        external_stop=kill_switch_stop,
    )


def _benchmark(ctx) -> Result:
    """Adds requirement 9 as soon as it is judged, so a stop at the spend cap keeps its line;
    returns requirement 10."""
    session = ctx.stack.session_id
    active = active_version()
    ctx.on_exit(lambda: _activate(active))
    items = load_benchmark()
    cfg = pack_config()
    ctx.api.in_process = True  # at the cap the kill switch is engaged for these runs too
    held = Held(ctx.api)
    target = RecordingTarget(analyst_target(), held)
    runner = CappedRunner(
        target=target,
        evaluator=ExecutionEvaluator.live(),
        scheme=Scheme.from_pack(),
        concurrency=int(cfg["evaluation"]["concurrency"]),
        cap=held,
    )
    by_id = {i.id: i for i in items}

    started = datetime.now(UTC)
    with traced_step("assignment check: analyzer team", {"assignment": SLUG}) as trace_id:
        shared, why = session_baseline(items)
        baseline = shared or _experiment(runner, items, active, session)
        ctx.report.say(
            f"Baseline: experiment {baseline.experiment_id} of {active}, "
            + ("shared from earlier in this live session" if shared else f"run now, since {why}")
        )
        # A shared baseline holds results, not the agent's SQL: the failure analyst then works from
        # the evaluator's reasons, the trap labels, and the reference SQL.
        failed = [
            FailedItem(by_id[item_id], target.answers.get(by_id[item_id].question), result)
            for item_id, result in baseline.results.items()
            if by_id[item_id].split is Split.DEV and not result.passed
        ]
        name = f"candidate-{datetime.now(UTC):%Y%m%d-%H%M%S}"
        planted = planted_rule([f.item.id for f in failed])
        knowledge = targets.knowledge_from_ops(active)
        runs = _team_runs(
            live_team(items), failed, knowledge, name, baseline, runner, items, session, planted
        )
        chosen = candidates.choose(runs)
        with db.connect(db.Role.APP) as conn:
            said = candidates.save(
                conn,
                runs,
                chosen,
                session_id=session,
                request_id=None,
                from_version=active,
                saved_as=name,
                naive=False,
            )
            conn.commit()
        ctx.report.say(f"Analyzer team: {said}")
    judged = [_critic_line(run, planted.id) for run in runs]
    critic_ok = all(ok for ok, _ in judged)
    critic = Result(
        9,
        "Live: the critic drops the planted over-broad rule with a reason, and adds no rule",
        critic_ok,
        "" if critic_ok else "give the critic a reason to drop over-broad rules",
        [_step_run(ctx, trace_id, started, critic_ok, "; ".join(what for _, what in judged))],
        f"{len(runs)} analyzer team runs, as in class (analyzer.candidates in pack.yaml); the "
        "critic must drop the planted rule in every one, since any of them can be kept",
    )
    ctx.report.add(critic)

    report = chosen.report
    started = datetime.now(UTC)
    with traced_step("assignment check: candidate and gate", {"assignment": SLUG}) as trace_id:
        _save_draft(name, report.candidate.model_copy(update={"version": name}))
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
        flags = candidate_overfit_flags(items, report.candidate, knowledge)
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
    missing = [i.id for i in family_items() if i.id not in candidate.results]
    ok, fix = promotion_verdict(decision.verdict, regressions.total, missing, eligible)
    family = [i for i in family_items() if i.split is Split.HOLDOUT]
    family_passes = sum(candidate.passed(i.id) for i in family)
    what = (
        f"{decision.sentence} Holdout {decision.candidate_holdout_passes} of "
        f"{decision.holdout_total} against {decision.active_holdout_passes}; confirmed "
        f"regressions {regressions.total}; the new family passes {family_passes} of "
        f"{len(family)} holdout items (measured, not required); eligible for the unattended "
        f"level: {', '.join(eligible) or 'none'}"
        + (f"; family items with no result: {', '.join(missing)}" if missing else "")
    )
    promoted = Result(
        10,
        "Live: the gate promotes a version covering the new family with zero regressions",
        ok,
        fix,
        [_step_run(ctx, trace_id, started, ok, what)],
        "the class measurement: holdout items 3 runs, passing on 2; every apparent regression "
        "confirmed by re-runs of both versions; zero confirmed regressions; human approval. "
        "Covering the family means every one of its items is measured; none has to pass",
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
    experiments = 1 if session_baseline(items)[0] else 2
    written = candidates.count()
    dev_items = sum(i.split is Split.DEV for i in items)
    selection = dev_items * written if written > 1 else 0
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
                f"analyzer team calls (failure analyst, rule writer, critic, for {written} "
                "candidates as in class)",
                3 * written,
                ctx.analyzer_model,
            ),
            Planned(
                f"analyst runs for the benchmark ({which}; {per_experiment} runs per experiment; "
                "re-runs of apparent regressions and of holdout items short at clearance come on "
                "top)",
                experiments * per_experiment,
                ctx.agent_model,
            ),
            *(
                [
                    Planned(
                        f"analyst runs choosing between the {written} candidates (the "
                        f"{dev_items} dev items once each, per candidate)",
                        selection,
                        ctx.agent_model,
                    )
                ]
                if selection
                else []
            ),
        ],
        live=list(enumerate(texts, start=9)),
        typical=typical(first=experiments == 2),
    )
    report.add(_benchmark(ctx))
