from types import SimpleNamespace

import pytest

from loopeng.agent.loop import (
    Attempt,
    TerminationReason,
    extract_sql,
    run_question,
)
from loopeng.usage import CallUsage
from loopeng.warehouse.connect import ensure_warehouse


@pytest.fixture(scope="module")
def warehouse(tmp_path_factory):
    return ensure_warehouse(tmp_path_factory.mktemp("wh") / "w.duckdb", seed=20260729)


class FakeClient:
    """Returns canned SQL in order. Counts calls, so tests can assert on spend."""

    def __init__(self, replies, usage=None):
        self._replies = list(replies)
        self.calls = 0
        self._usage = usage or {"input_tokens": 100, "output_tokens": 50}
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.calls += 1
        text = self._replies[min(self.calls - 1, len(self._replies) - 1)]
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text=text)],
            usage=SimpleNamespace(**self._usage),
        )


class ExplodingClient:
    def __init__(self):
        self.calls = 0
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.calls += 1
        raise RuntimeError("overloaded_error")


# ---- SQL extraction ---------------------------------------------------------


def test_extracts_sql_from_a_fence():
    """Models fence code even when told not to. Left in place the fence fails to
    parse, and the loop burns a retry on a formatting artefact."""
    assert extract_sql("```sql\nSELECT 1\n```") == "SELECT 1"
    assert extract_sql("```\nSELECT 1\n```") == "SELECT 1"


def test_unfenced_sql_passes_through():
    assert extract_sql("  SELECT 1  ") == "SELECT 1"


# ---- termination: each reason fires, by name --------------------------------


def test_success_terminates_immediately(warehouse):
    client = FakeClient(["SELECT COUNT(*) FROM products"])
    run = run_question("how many products?", warehouse=warehouse, client=client)
    assert run.termination is TerminationReason.SUCCESS
    assert len(run.attempts) == 1
    assert client.calls == 1
    assert run.rows


def test_retries_on_execution_failure_then_succeeds(warehouse):
    """The whole of Level 1: a query that did not run gets another go, with the
    database error as the only feedback."""
    client = FakeClient(["SELECT * FROM no_such_table", "SELECT COUNT(*) FROM products"])
    run = run_question("q", warehouse=warehouse, client=client)
    assert run.termination is TerminationReason.SUCCESS
    assert len(run.attempts) == 2
    assert run.attempts[0].error is not None
    assert run.attempts[1].error is None


def test_max_attempts_fires_and_is_named(warehouse):
    client = FakeClient(["SELECT * FROM missing_a", "SELECT * FROM missing_b",
                         "SELECT * FROM missing_c", "SELECT * FROM missing_d"])
    run = run_question("q", warehouse=warehouse, client=client, max_attempts=3)
    assert run.termination is TerminationReason.MAX_ATTEMPTS
    assert len(run.attempts) == 3


def test_no_progress_fires_on_identical_sql(warehouse):
    """Same query twice means the feedback is not moving the model; further attempts
    only spend."""
    client = FakeClient(["SELECT * FROM missing_x"])
    run = run_question("q", warehouse=warehouse, client=client, max_attempts=5)
    assert run.termination is TerminationReason.NO_PROGRESS
    assert len(run.attempts) == 2


def test_no_progress_fires_on_identical_error(warehouse):
    """Different SQL, same complaint. Also no progress."""
    client = FakeClient(["SELECT * FROM missing_x", "SELECT  * FROM missing_x "])
    run = run_question("q", warehouse=warehouse, client=client, max_attempts=5)
    assert run.termination is TerminationReason.NO_PROGRESS


def test_budget_fires_and_is_named(warehouse):
    client = FakeClient(["SELECT * FROM missing_a", "SELECT * FROM missing_b"],
                        usage={"input_tokens": 1_000_000, "output_tokens": 1_000_000})
    run = run_question("q", warehouse=warehouse, client=client, max_attempts=5,
                       budget_usd=0.001)
    assert run.termination is TerminationReason.BUDGET


def test_budget_is_checked_before_spending_not_after(warehouse):
    """A cap enforced in arrears is a report of what was overspent."""
    client = FakeClient(["SELECT * FROM missing_a"],
                        usage={"input_tokens": 10_000_000, "output_tokens": 0})
    run = run_question("q", warehouse=warehouse, client=client, max_attempts=5,
                       budget_usd=0.001)
    assert run.termination is TerminationReason.BUDGET
    assert client.calls == 1, "a second call was made after the budget was already gone"


def test_every_termination_reason_is_reachable():
    """A policy branch nothing can reach is decoration."""
    assert {r.value for r in TerminationReason} == {
        "success", "max_attempts", "budget", "no_progress"
    }


# ---- Level 1 catches syntactic failure, NOT semantic -------------------------


def test_a_wrong_but_valid_query_terminates_as_success(warehouse):
    """THE teaching point. This query runs perfectly and answers the wrong question,
    and Level 1 has no way to know: it sees rows, so it stops. Catching this is
    Level 2's job, and the gap is the entire reason Phase 2 exists."""
    client = FakeClient(["SELECT COUNT(*) FROM orders"])
    run = run_question("how many products?", warehouse=warehouse, client=client)
    assert run.termination is TerminationReason.SUCCESS
    assert run.error is None
    assert run.rows


def test_the_loop_never_receives_gold():
    """The loop's signature has nowhere to put an expected answer.

    Checked against the project's own FORBIDDEN_FIELD_PATTERN rather than a fresh
    list, so Phase 1 and the Phase 2 VerifyContext contract cannot drift apart into
    two different ideas of what "gold" means.

    item_id is deliberately allowed: it is a correlation label typed str | None, and
    an id carries no answer. The type assertion below is what keeps it that way.
    """
    import inspect

    from loopeng.contracts import FORBIDDEN_FIELD_PATTERN

    signature = inspect.signature(run_question)
    for name in signature.parameters:
        assert not FORBIDDEN_FIELD_PATTERN.search(name), f"run_question exposes {name}"


def test_the_loop_cannot_be_handed_a_gold_item():
    """The stronger version: no parameter is typed to accept one, so gold cannot
    reach the loop even under a differently-spelled name."""
    import inspect

    for name, param in inspect.signature(run_question).parameters.items():
        annotation = str(param.annotation)
        assert "GoldItem" not in annotation, f"run_question accepts a GoldItem as {name}"
    assert "GoldItem" not in inspect.getsource(run_question)


# ---- cost: every call counts ------------------------------------------------


def test_failed_model_calls_are_still_recorded(warehouse):
    """Tokens generated by a call that errored still bill."""
    client = ExplodingClient()
    run = run_question("q", warehouse=warehouse, client=client, max_attempts=3)
    assert client.calls == 3
    assert len(run.ledger) == 3
    assert run.ledger.by_outcome() == {"error": 3}


def test_usage_is_recorded_for_every_attempt(warehouse):
    client = FakeClient(["SELECT * FROM missing_a", "SELECT COUNT(*) FROM products"])
    run = run_question("q", warehouse=warehouse, client=client)
    assert len(run.ledger) == 2
    assert run.ledger.totals()["output_tokens"] == 100


def test_run_cost_reconciles_with_its_attempts(warehouse):
    """Asserted rather than eyeballed."""
    from loopeng.usage import reconcile

    client = FakeClient(["SELECT * FROM missing_a", "SELECT COUNT(*) FROM products"])
    run = run_question("q", warehouse=warehouse, client=client)
    per_attempt = sum(a.usage.input_tokens for a in run.attempts)
    reconcile(run.ledger, {"input_tokens": per_attempt})


def test_all_four_token_classes_survive_into_the_run(warehouse):
    client = FakeClient(
        ["SELECT COUNT(*) FROM products"],
        usage={
            "input_tokens": 10,
            "output_tokens": 20,
            "cache_creation_input_tokens": 30,
            "cache_read_input_tokens": 40,
        },
    )
    run = run_question("q", warehouse=warehouse, client=client)
    totals = run.ledger.totals()
    assert totals["cache_creation_input_tokens"] == 30
    assert totals["cache_read_input_tokens"] == 40


def test_a_timeout_is_recorded_as_an_error_not_a_success(warehouse):
    runaway = "SELECT COUNT(*) FROM range(100000000) a, range(1000) b, range(1000) c"
    client = FakeClient([runaway])
    run = run_question("q", warehouse=warehouse, client=client, max_attempts=1,
                       timeout_s=0.5)
    assert run.termination is not TerminationReason.SUCCESS
    assert run.error.startswith("QueryTimeout")


def test_attempt_reports_whether_it_executed():
    usage = CallUsage("claude-haiku-4-5", "ok")
    assert Attempt(1, "SELECT 1", [[1]], None, usage).executed
    assert not Attempt(1, "SELECT 1", None, "boom", usage).executed
