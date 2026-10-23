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


def _services(**overrides: Any) -> smoke.Services:
    spent = {"tokens_in": 0, "tokens_out": 0, "cost": 0.0}

    def ledger() -> tuple[int, int, float]:
        spent["tokens_in"] += 50  # each read sees the calls made since the last one
        spent["cost"] += 0.001
        return spent["tokens_in"], spent["tokens_out"], spent["cost"]

    run = {
        "status": "posted",
        "tokens_in": 900,
        "tokens_out": 90,
        "cost_usd": 0.002,
        "langsmith_url": "https://smith.example/r/webhook",
        "answer": {"envelope": {"answer_text": "There were 1,203 orders."}},
    }
    parts: dict[str, Any] = {
        "target": _Target(),
        "items": ITEMS,
        "evaluate": lambda i, a: ItemResult(item_id=i.id, passed=False, reason="row 1 differs"),
        "team": _Team,
        "post_event": lambda question: "webhook-run",
        "read_run": lambda run_id: run,
        "write_refused": lambda sql: "25006",
        "orders": lambda: 2000,
        "ledger": ledger,
        "trace_url": lambda run_id: f"https://smith.example/r/{run_id}",
        "trace_found": lambda run_id: True,
        "traced": lambda name, run_id: contextlib.nullcontext(),
        "flush": lambda: None,
        "poll_seconds": 0.0,
        "timeout_seconds": 0.0,
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
