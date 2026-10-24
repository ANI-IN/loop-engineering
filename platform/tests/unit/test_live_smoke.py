"""The live smoke check on stand-ins (zero tokens): it reports wrong answers, and it fails only on
hard breakages; the activity cap stops live work like the build budget."""

from __future__ import annotations

import contextlib
import uuid
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any

import pytest
from loop4_doubles import answered, item
from typer.testing import CliRunner

from datapilot.cli import app
from datapilot.contracts import ItemResult, Split
from datapilot.loop4_hill_climbing import live_smoke as smoke
from datapilot.loop4_hill_climbing.targets import RunStats
from datapilot.observability import spend


def _stats(question: str, **kw: Any) -> RunStats:
    values: dict[str, Any] = {
        "run_id": str(uuid.uuid4()),
        "question": question,
        "knowledge_version": "v1",
        "item_id": None,
        "repetition": None,
        "status": "answered",
        "attempts": 1,
        "tokens_in": 100,
        "tokens_out": 10,
        "seconds": 1.0,
        "reviewer": None,
        "reviewer_reasons": [],
        "tool_calls": ["list_tables", "scout_schema", "run_query"],
        "final_sql": "SELECT 1",
        "reasons": [],
        "graders_passed": True,
    }
    return RunStats(**(values | kw))


@dataclass
class _Target:
    reviewer: bool = False
    stats: list[RunStats] = field(default_factory=list)
    outcomes: dict[str, dict[str, Any]] = field(default_factory=dict)
    base: Any = field(
        default_factory=lambda: SimpleNamespace(limits=SimpleNamespace(scout_enabled=True))
    )

    def with_agents(self, *, scout: bool, reviewer: bool) -> _Target:
        return _Target(reviewer, self.stats, self.outcomes, self.base)

    def __call__(self, question: str, version: str):
        extra = dict(self.outcomes.get(question[:20], {}))
        if self.reviewer:
            extra.setdefault("reviewer", "approve")
        self.stats.append(_stats(question, **extra))
        return answered("SELECT 1")


class _Team:
    def run(self, failed, knowledge, name):
        assert len(failed) == 2 and knowledge.version == "v1"
        return SimpleNamespace(diagnoses=[1, 2], proposed=[1], guard=[1], accepted=[1])


ITEMS = [
    item(smoke.SCOUT_ITEM),
    item(smoke.SPINE_ITEM),
    item("naive-one", naive_sql="SELECT 2"),
    item("naive-two", naive_sql="SELECT 3"),
    item("holdout", Split.HOLDOUT, naive_sql="SELECT 4"),
]


WEBHOOK_RUN = {
    "status": "posted",
    "tokens_in": 900,
    "tokens_out": 90,
    "cost_usd": 0.002,
    "langsmith_url": "https://smith.example/r/webhook",
    "trace_refused_at": None,
    "answer": {"envelope": {"answer_text": "There were 1,203 orders."}},
}
REFUSED_ON_RECORD = WEBHOOK_RUN | {"trace_refused_at": "2026-10-24T09:00:00+00:00"}


def _services(**overrides: Any) -> smoke.Services:
    spent = {"tokens_in": 0, "tokens_out": 0, "cost": 0.0}

    def ledger() -> tuple[int, int, float]:
        spent["tokens_in"] += 50  # each read sees the calls made since the last one
        spent["cost"] += 0.001
        return spent["tokens_in"], spent["tokens_out"], spent["cost"]

    parts: dict[str, Any] = {
        "target": _Target(),
        "items": ITEMS,
        "evaluate": lambda i, a: ItemResult(item_id=i.id, passed=False, reason="row 1 differs"),
        "team": _Team,
        "post_event": lambda question: "webhook-run",
        "read_run": lambda run_id: WEBHOOK_RUN,
        "write_refused": lambda sql: "25006",
        "orders": lambda: 2000,
        "ledger": ledger,
        "trace_url": lambda run_id: f"https://smith.example/r/{run_id}",
        "trace_found": lambda run_id: True,
        "traced": lambda name, run_id: contextlib.nullcontext(),
        "flush": lambda: None,
        "poll_seconds": 0.0,
        "timeout_seconds": 0.0,
        "refusal_wait_seconds": 0.0,
    }
    return smoke.Services(**(parts | overrides))


def test_five_checks_run_and_a_wrong_answer_is_reported_not_failed() -> None:
    checks = smoke.run(_services())
    assert [c.name[:3] for c in checks] == ["(a)", "(b)", "(c)", "(d)", "(e)"]
    assert all(c.ok for c in checks), [c.hard_failure for c in checks]
    assert "gold check failed" in checks[0].result and "reviewer approve" in checks[1].result
    assert checks[2].cost_usd == pytest.approx(0.002 + 0.001) and checks[2].trace_url
    assert "2 diagnoses of ['naive-one', 'naive-two']" in checks[3].result
    assert all(c.trace_url for c in checks)
    assert all(line.startswith(("(", "    ")) for c in checks for line in c.lines())


def test_an_exception_is_a_hard_breakage() -> None:
    def broken(question: str) -> str:
        raise ConnectionError("api down")

    checks = smoke.run(_services(post_event=broken))
    assert checks[2].hard_failure == "ConnectionError: api down"
    assert [c.ok for c in checks] == [True, True, False, True, True]


def test_a_run_that_never_finishes_is_a_timeout() -> None:
    stuck = {"status": "running", "tokens_in": 0, "tokens_out": 0, "cost_usd": 0}
    checks = smoke.run(_services(read_run=lambda run_id: stuck))
    assert checks[2].hard_failure and checks[2].hard_failure.startswith("timeout")


def test_a_missing_trace_is_a_hard_breakage() -> None:
    checks = smoke.run(_services(trace_found=lambda run_id: run_id == "webhook-run"))
    assert [c.ok for c in checks] == [False, False, True, False, False]
    assert checks[0].hard_failure and checks[0].hard_failure.startswith("missing trace")


def test_a_trace_refused_for_the_monthly_limit_is_reported_not_failed() -> None:
    """Live, 23 October: LangSmith's free plan refused every upload once its monthly limit was
    used up, and live-smoke reported each check as a hard failure (review round 1, F015). The
    worker's refusal of check (c) comes from its record of the run."""
    checks = smoke.run(
        _services(
            trace_found=lambda run_id: False,
            trace_refused=lambda run_id: True,
            read_run=lambda run_id: REFUSED_ON_RECORD,
        )
    )
    assert all(c.ok for c in checks), [c.hard_failure for c in checks]
    refused = [c for c in checks if c.trace_refused]
    assert [c.name[:3] for c in refused] == ["(a)", "(b)", "(c)", "(d)", "(e)"]
    assert "    trace refused by LangSmith (monthly limit): https://smith.example/r/" in "\n".join(
        refused[0].lines()
    )


def test_a_trace_missing_for_any_other_reason_stays_a_hard_breakage() -> None:
    checks = smoke.run(
        _services(trace_found=lambda run_id: False, trace_refused=lambda run_id: False)
    )
    assert not any(c.ok for c in checks) and not any(c.trace_refused for c in checks)


def test_only_the_run_langsmith_refused_reads_as_refused() -> None:
    """Review round 2: after one refusal for the monthly limit, every missing trace of the
    command was reported as refused; now only a run the refusal named is."""
    scout = next(i.question for i in ITEMS if i.id == smoke.SCOUT_ITEM)
    checks = smoke.run(
        _services(
            target=_Target(outcomes={scout[:20]: {"run_id": "scout-run"}}),
            trace_found=lambda run_id: False,
            trace_refused=lambda run_id: run_id == "scout-run",
        )
    )
    assert [c.trace_refused for c in checks] == [True, False, False, False, False]
    assert [c.ok for c in checks] == [True, False, False, False, False]
    assert checks[1].hard_failure and checks[1].hard_failure.startswith("missing trace")


def test_the_workers_trace_reads_refused_when_its_run_record_says_so() -> None:
    """Live, 24 October: the worker uploads the webhook run's trace, so this process never sees
    that refusal. The worker writes it on the run's row, and the api's run record carries it."""
    checks = smoke.run(
        _services(
            trace_found=lambda run_id: run_id != "webhook-run",
            read_run=lambda run_id: REFUSED_ON_RECORD,
        )
    )
    assert all(c.ok for c in checks), [c.hard_failure for c in checks]
    webhook = checks[2]
    assert [c.trace_refused for c in checks] == [False, False, True, False, False]
    assert "    trace refused by LangSmith (monthly limit): https://smith.example/r/webhook" in (
        webhook.lines()
    )


def test_the_workers_missing_trace_is_a_hard_failure_even_when_this_process_was_refused() -> None:
    """The owner's rule: a refusal this process saw never vouches for the worker's trace; without
    the worker's record of a refusal, check (c) is a missing trace."""
    checks = smoke.run(
        _services(
            trace_found=lambda run_id: run_id != "webhook-run",
            trace_refused=lambda run_id: True,
        )
    )
    webhook = checks[2]
    assert [c.ok for c in checks] == [True, True, False, True, True]
    assert not webhook.trace_refused
    assert webhook.hard_failure == "missing trace: LangSmith has no run webhook-run"


def test_the_workers_refusal_is_read_again_until_it_arrives() -> None:
    reads: list[str] = []

    def read_run(run_id: str) -> dict[str, Any]:
        reads.append(run_id)
        return REFUSED_ON_RECORD if len(reads) > 3 else WEBHOOK_RUN

    services = _services(trace_found=lambda run_id: False, read_run=read_run)
    services.refusal_wait_seconds = 30.0
    assert smoke.refused_on_record(services, "webhook-run") and len(reads) == 4


def test_the_wait_for_the_workers_refusal_is_bounded() -> None:
    services = _services(read_run=lambda run_id: WEBHOOK_RUN, poll_seconds=0.01)
    services.refusal_wait_seconds = 0.05
    assert not smoke.refused_on_record(services, "webhook-run")


def test_an_unreadable_run_record_leaves_the_workers_trace_missing() -> None:
    reads = {"count": 0}

    def read_run(run_id: str) -> dict[str, Any]:
        reads["count"] += 1
        if reads["count"] > 1:  # the check itself read it; the read after the flush fails
            raise ConnectionError("api down")
        return WEBHOOK_RUN

    checks = smoke.run(
        _services(trace_found=lambda run_id: run_id != "webhook-run", read_run=read_run)
    )
    assert checks[2].hard_failure == (
        "missing trace: LangSmith has no run webhook-run "
        "(its run record could not be read: ConnectionError)"
    )


def test_a_write_the_database_did_not_refuse_is_a_hard_breakage() -> None:
    checks = smoke.run(_services(write_refused=lambda sql: None))
    assert checks[4].hard_failure == "a write was not refused by the database"


def test_a_refused_write_that_did_not_end_escalated_is_a_hard_breakage() -> None:
    target = _Target(
        outcomes={
            smoke.WRITE_QUESTION[:20]: {
                "status": "answered",
                "reasons": ["the database refused a write"],
            }
        }
    )
    checks = smoke.run(_services(target=target))
    assert checks[4].hard_failure == "a refused write ended the run answered, not escalated"


def test_no_answer_envelope_is_invalid_structured_output() -> None:
    question = next(i.question for i in ITEMS if i.id == smoke.SCOUT_ITEM)
    target = _Target(
        outcomes={
            question[:20]: {
                "status": "escalated",
                "reasons": ["the analyst returned no answer envelope"],
            }
        }
    )
    checks = smoke.run(_services(target=target))
    assert checks[0].hard_failure == "invalid structured output: no answer envelope"


def test_the_naive_guard_is_on_only_for_the_write_check(monkeypatch) -> None:
    monkeypatch.delenv("BUG_NAIVE_GUARD", raising=False)
    seen: list[str | None] = []

    @dataclass
    class _Watching(_Target):
        def __call__(self, question: str, version: str):
            import os

            seen.append(os.environ.get("BUG_NAIVE_GUARD"))
            return super().__call__(question, version)

        def with_agents(self, *, scout: bool, reviewer: bool) -> _Target:
            return _Watching(reviewer, self.stats, self.outcomes, self.base)

    smoke.run(_services(target=_Watching()))
    assert seen == [None, None, "1"]
    import os

    assert "BUG_NAIVE_GUARD" not in os.environ


def test_a_clarifying_question_without_sql_is_reported_not_failed() -> None:
    from datapilot.contracts import AnswerEnvelope, AnswerStatus

    @dataclass
    class _Asks(_Target):
        def __call__(self, question: str, version: str):
            self.stats.append(_stats(question, final_sql=None, reviewer=None))
            return AnswerEnvelope(status=AnswerStatus.NEEDS_CLARIFICATION)

        def with_agents(self, *, scout: bool, reviewer: bool) -> _Target:
            return _Asks(reviewer, self.stats, self.outcomes, self.base)

    check = smoke.spine_question(_services(target=_Asks()))
    assert check.ok and "answer status needs_clarification" in check.result
    assert any("clarification" in note for note in check.notes)


def test_the_smoke_spends_under_the_development_live_checks_line() -> None:
    assert spend.line_for(smoke.ACTIVITY).name == "development live checks"


def test_the_command_is_registered() -> None:
    assert CliRunner().invoke(app, ["live-smoke", "--help"]).exit_code == 0
