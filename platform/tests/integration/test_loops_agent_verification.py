"""The agent and verification loops end to end on the fixture warehouse, with scripted models."""

from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import Sequence

import loops_paths  # noqa: F401  (before loops_support)
import psycopg
import pytest
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from loops_support import (
    FIXTURE_SCHEMA,
    ListHooks,
    call,
    envelope,
    human_messages,
    query_then_answer,
    tool_messages,
    usage,
)

from datapilot import db, tests_database_guard
from datapilot.contracts import KnowledgeRule, KnowledgeVersion, RunStatus
from datapilot.loop1_agent.catalog import PERSONAL_SAMPLE
from datapilot.loop1_agent.tools import Warehouse
from datapilot.loop2_verification.executor import ExecutionError, ReadOnlyProbeFailed
from datapilot.loop2_verification.loop import RunRequest, VerificationLoop

pytest_plugins = ["loops_fixtures"]
pytestmark = pytest.mark.integration

COUNT_SQL = "SELECT count(*) AS orders FROM orders"


def request(question: str = "How many orders are there?", **kw: object) -> RunRequest:
    return RunRequest(run_id=str(uuid.uuid4()), question=question, **kw)  # type: ignore[arg-type]


def run(loop: VerificationLoop, req: RunRequest):
    return asyncio.run(loop.start(req))


# --- executor ---
def test_the_executor_reads_and_always_rolls_back(executor) -> None:
    result = executor.run(COUNT_SQL)
    assert result.columns == ["orders"] and result.rows == [(2000,)]


def test_a_write_reaching_the_executor_is_refused_by_the_read_only_transaction(
    monkeypatch, executor
) -> None:
    monkeypatch.delenv("BUG_NAIVE_GUARD", raising=False)
    with pytest.raises(ExecutionError) as error:
        executor.run("DELETE FROM orders")
    assert error.value.sqlstate == "25006"
    assert executor.run(COUNT_SQL).rows == [(2000,)]


def test_the_executor_sends_one_statement_only_unless_the_naive_guard_is_planted(
    monkeypatch, executor
) -> None:
    """Review round 1 (F069): the executor sent the agent's text by the simple protocol, so a
    stacked statement reached the server whenever the parse grader was not in front; EXPLAIN did
    too (psycopg sends a query with no parameters by the simple protocol). Both now send one
    prepared statement, and PostgreSQL refuses a second statement (42601) before anything runs;
    only the naive guard's demo keeps the simple protocol, so its stacked write meets the
    read-only transaction (25006). Before this change, a test pinned 25006 with the flag off."""
    stacked = "SELECT 1; DELETE FROM orders"
    monkeypatch.delenv("BUG_NAIVE_GUARD", raising=False)
    for send in (executor.run, executor.explain):
        with pytest.raises(ExecutionError) as one_only:
            send(stacked)
        assert one_only.value.sqlstate == "42601" and not one_only.value.refused_write
    assert executor.run("SELECT count(*) FROM customers WHERE email LIKE '%@example.com'").rows
    assert executor.explain("SELECT count(*) FROM customers WHERE email LIKE '%@x.com'")
    monkeypatch.setenv("BUG_NAIVE_GUARD", "1")
    with pytest.raises(ExecutionError) as planted_path:
        executor.run(stacked)
    assert planted_path.value.sqlstate == "25006"
    assert executor.run(COUNT_SQL).rows == [(2000,)]


def test_the_statement_timeout_stops_a_runaway_query(executor) -> None:
    with pytest.raises(ExecutionError) as error:
        executor.run("SELECT count(*) FROM (SELECT generate_series(1, (SELECT 2000000000))) AS s")
    assert error.value.sqlstate == "57014" and "timeout" in error.value.feedback


def test_the_startup_probe_passes_on_the_read_only_role(executor) -> None:
    executor.probe_read_only()


def test_the_startup_probe_refuses_a_connection_that_is_not_read_only(executor) -> None:
    """Review round 1 (F008): this test asserted that the owner role passed, because the probe
    tried a write inside a read-only transaction it opened itself, which fails for any role. The
    probe now checks the role, so the writable owner role must fail it, naming what it can do."""
    from dataclasses import replace

    owner = replace(executor, url=db.url_for(db.Role.OWNER))
    with pytest.raises(ReadOnlyProbeFailed) as refused:
        owner.probe_read_only()
    assert "not read-only" in str(refused.value) and "it can write" in str(refused.value)
    app = replace(executor, url=db.url_for(db.Role.APP))
    with pytest.raises(ReadOnlyProbeFailed, match="temporary tables"):
        app.probe_read_only()
    # a role and database that do not exist, on the tests' own server: no other address is reached
    port = tests_database_guard.tests_port()
    broken = replace(executor, url=f"postgresql://nobody:nobody@localhost:{port}/none")
    with pytest.raises(ReadOnlyProbeFailed, match="could not connect"):
        broken.probe_read_only()


def test_the_agent_role_cannot_write_even_outside_a_read_only_transaction() -> None:
    with (
        db.connect(db.Role.AGENT, autocommit=True) as conn,
        pytest.raises(psycopg.errors.InsufficientPrivilege),
    ):
        conn.execute("SET default_transaction_read_only = off")
        conn.execute(f"DELETE FROM {FIXTURE_SCHEMA}.orders")


# --- tools ---
def test_describe_table_gives_types_samples_and_few_distinct_values(warehouse, executor) -> None:
    text = Warehouse(warehouse, executor.url).describe_table("orders")
    described = json.loads(text)
    assert {
        "name": "status",
        "type": "smallint",
        "nullable": False,
        "comment": "Order status code.",
    } in (described["columns"])
    assert len(described["sample_rows"]) == 3
    assert described["distinct_values"]["status"] == [1, 2, 3, 4, 5]


def test_describe_table_never_sends_personal_data_to_the_model(warehouse, executor) -> None:
    """Review round 1 (F002): describing customers sent three people's names, emails, and phones
    to the model with no grader and no approval. The pack's personal-data columns are now masked
    in the sample rows and left out of the distinct values, in the base table and the view."""
    for name in ("customers", "customers_marketable"):
        text = Warehouse(warehouse, executor.url).describe_table(name)
        described = json.loads(text)
        assert "@" not in text and "555-01" not in text and "First1" not in text, name
        rows = described["sample_rows"]
        assert len(rows) == 3 and all(r["email"] == PERSONAL_SAMPLE for r in rows), name
        assert all(r["state"] in ("CA", "TX", "NY") for r in rows), "other columns stay visible"
        assert not {"email", "first_name", "last_name", "phone"} & set(described["distinct_values"])
    products = Warehouse(warehouse, executor.url).describe_table("products")
    assert "Ignore previous instructions" in products, "the planted injected name stays visible"


def test_planted_names_only_schema(monkeypatch, warehouse, executor) -> None:
    monkeypatch.setenv("BUG_NAMES_ONLY_SCHEMA", "1")
    text = Warehouse(warehouse, executor.url).describe_table("orders")
    assert text.startswith("orders: order_id, customer_id") and "smallint" not in text
    monkeypatch.setenv("BUG_NAMES_ONLY_SCHEMA", "0")
    assert "smallint" in Warehouse(warehouse, executor.url).describe_table("orders")


def big_query_script(messages: Sequence[BaseMessage]) -> AIMessage:
    if isinstance(messages[-1], HumanMessage):
        return call("run_query", {"sql": "SELECT * FROM order_items"}, "big")
    return envelope(COUNT_SQL, "There are 2000 orders.")


@pytest.mark.parametrize("flag", ["0", "1"])
def test_planted_unbounded_rows(monkeypatch, services_for, flag: str) -> None:
    monkeypatch.setenv("BUG_UNBOUNDED_ROWS", flag)
    seen: list[str] = []

    def script(messages: Sequence[BaseMessage]) -> AIMessage:
        seen.extend(m.content for m in tool_messages(messages) if m.content not in seen)
        return big_query_script(messages)

    outcome = run(VerificationLoop(services_for({"analyst": script}), ListHooks()), request())
    assert outcome.status is RunStatus.ANSWERED
    payload = json.loads(seen[0])
    assert payload["total_row_count"] == 12000
    if flag == "1":
        assert len(payload["rows"]) == 12000 and not payload["truncated"]
    else:
        assert len(payload["rows"]) == 50 and payload["truncated"] and "notice" in payload


# --- the verification loop ---
def test_a_simple_question_is_answered_with_its_events(services_for) -> None:
    script = query_then_answer(COUNT_SQL, "There are 2000 orders.")
    hooks = ListHooks()
    outcome = run(VerificationLoop(services_for({"analyst": script}), hooks), request())
    assert outcome.status is RunStatus.ANSWERED
    assert outcome.envelope and outcome.envelope.rows_preview == [[2000]]
    assert hooks.statuses == [RunStatus.RUNNING, RunStatus.VERIFYING]
    assert [p["tool"] for p in hooks.kinds("tool_call_finished")] == ["run_query"]
    graders = [p["grader"] for p in hooks.kinds("grader_result")]
    assert graders[:6] == [
        "parse",
        "statement_policy",
        "schema",
        "cost",
        "personal_data",
        "execution",
    ]
    assert graders[-1] == "final_answer"
    assert outcome.tokens_in > 0


def test_the_active_knowledge_is_injected_into_the_system_prompt(services_for) -> None:
    prompts: list[str] = []
    knowledge = KnowledgeVersion(
        version="v9",
        rules=[
            KnowledgeRule(
                id="r1", title="Fiscal year", rule_text="Starts in February.", applies_when="always"
            )
        ],
    )

    def script(messages: Sequence[BaseMessage]) -> AIMessage:
        prompts.append(next(str(m.content) for m in messages if isinstance(m, SystemMessage)))
        return query_then_answer(COUNT_SQL, "There are 2000 orders.")(messages)

    services = services_for({"analyst": script}, knowledge=knowledge)
    outcome = run(VerificationLoop(services, ListHooks()), request())
    assert outcome.knowledge_version == "v9"
    assert all(
        "Business knowledge (version v9)" in p and "Starts in February." in p for p in prompts
    )
    assert "You are the analyst" in prompts[0]


def test_a_number_not_in_the_result_is_fed_back_and_corrected(services_for) -> None:
    def script(messages: Sequence[BaseMessage]) -> AIMessage:
        if isinstance(messages[-1], ToolMessage):
            wrong = len(human_messages(messages)) == 1
            return envelope(
                COUNT_SQL, "There are 2500 orders." if wrong else "There are 2000 orders."
            )
        return call("run_query", {"sql": COUNT_SQL}, f"q{len(messages)}")

    hooks = ListHooks()
    outcome = run(VerificationLoop(services_for({"analyst": script}), hooks), request())
    assert outcome.status is RunStatus.ANSWERED and outcome.attempts == 2, outcome.reasons
    assert hooks.statuses == [
        RunStatus.RUNNING,
        RunStatus.VERIFYING,
        RunStatus.RUNNING,
        RunStatus.VERIFYING,
    ]


def test_a_blocked_query_returns_feedback_to_the_analyst(services_for) -> None:
    feedback: list[str] = []

    def script(messages: Sequence[BaseMessage]) -> AIMessage:
        tools = tool_messages(messages)
        if not tools:
            return call(
                "run_query",
                {"sql": "WITH d AS (DELETE FROM orders RETURNING *) SELECT * FROM d"},
                "bad",
            )
        feedback.append(str(tools[-1].content))
        if len(tools) == 1:
            return call("run_query", {"sql": COUNT_SQL}, "good")
        return envelope(COUNT_SQL, "There are 2000 orders.")

    outcome = run(VerificationLoop(services_for({"analyst": script}), ListHooks()), request())
    assert outcome.status is RunStatus.ANSWERED
    assert feedback[0].startswith("Query blocked by the statement_policy check")


WRITE_CTE = "WITH d AS (DELETE FROM orders RETURNING *) SELECT count(*) FROM d"


def test_a_final_sql_write_the_database_refuses_ends_the_run_without_a_retry(
    monkeypatch, services_for
) -> None:
    monkeypatch.setenv("BUG_NAIVE_GUARD", "1")  # only the database stands between it and a write
    calls: list[int] = []

    def script(messages: Sequence[BaseMessage]) -> AIMessage:
        calls.append(len(human_messages(messages)))
        return envelope(WRITE_CTE, "There are 2000 orders.")

    hooks = ListHooks()
    outcome = run(VerificationLoop(services_for({"analyst": script}), hooks), request())
    assert outcome.status is RunStatus.ESCALATED and outcome.attempts == 1
    assert calls == [1], "the refused write was never sent back to the analyst"
    assert any("SQLSTATE 25006" in r for r in outcome.reasons)
    assert hooks.statuses[-1] is RunStatus.VERIFYING, "no retry: the run never went back"


def test_the_retry_cap_escalates_after_three_attempts(monkeypatch, services_for) -> None:
    monkeypatch.delenv("BUG_NO_RETRY_CAP", raising=False)
    script = query_then_answer(COUNT_SQL, "There are 2000 orders.")
    hooks = ListHooks()
    loop = VerificationLoop(services_for({"analyst": script}), hooks)
    outcome = run(loop, request(inject_failing_grader=True))
    assert outcome.status is RunStatus.ESCALATED and outcome.attempts == 3
    assert any("retry cap" in r for r in outcome.reasons)
    assert len([p for p in hooks.kinds("grader_result") if p["grader"] == "injected_failure"]) == 3


def test_planted_missing_retry_cap_keeps_looping_until_the_token_budget(
    monkeypatch, services_for
) -> None:
    monkeypatch.setenv("BUG_NO_RETRY_CAP", "1")
    script = query_then_answer(COUNT_SQL, "There are 2000 orders.")
    services = services_for({"analyst": script}, tokens_per_run=2000)
    outcome = run(VerificationLoop(services, ListHooks()), request(inject_failing_grader=True))
    assert outcome.status is RunStatus.ESCALATED
    assert outcome.attempts > 3
    assert any("token budget" in r for r in outcome.reasons)


def test_grader_feedback_goes_to_langsmith_without_extended_retention(services_for) -> None:
    class Recorder:
        def __init__(self) -> None:
            self.calls: list[dict] = []

        def create_feedback(self, run_id=None, key="", **kwargs):
            self.calls.append({"run_id": run_id, "key": key, **kwargs})

    client = Recorder()
    script = query_then_answer(COUNT_SQL, "There are 2000 orders.")
    req = request()
    run(VerificationLoop(services_for({"analyst": script}, feedback=client), ListHooks()), req)
    assert {c["key"] for c in client.calls} >= {"grader.parse", "grader.final_answer"}
    assert all(c["extend_trace_retention"] is False for c in client.calls)
    assert str(client.calls[0]["run_id"]) == req.run_id


# --- personal data and approvals ---
EMAIL_SQL = "SELECT email FROM customers_marketable WHERE state = 'CA' ORDER BY 1"


def test_personal_data_pauses_for_approval_then_resumes(services_for) -> None:
    script = query_then_answer(EMAIL_SQL, "Exported the California customers who may be contacted.")
    services = services_for({"analyst": script})
    req = request("Export California customers for marketing", export=True)
    hooks = ListHooks()
    paused = run(VerificationLoop(services, hooks), req)
    assert paused.status is RunStatus.AWAITING_APPROVAL
    assert (
        paused.approval and paused.approval.sql == EMAIL_SQL and paused.approval.row_estimate == 5
    )
    assert not hooks.kinds("tool_call_finished")  # nothing ran before approval
    resumed_hooks = ListHooks(RunStatus.RUNNING)
    resumed = asyncio.run(VerificationLoop(services, resumed_hooks).resume(req, approve=True))
    assert resumed.status is RunStatus.ANSWERED and resumed.personal_data
    assert resumed.envelope and resumed.envelope.row_count == 5


def test_a_query_a_person_already_approved_in_this_run_is_not_asked_again(services_for) -> None:
    """Live, a reviewer concern sent the analyst back and it ran the same approved export query
    again: the run asked for the same approval three more times."""
    script = query_then_answer(EMAIL_SQL, "Exported the California customers who may be contacted.")
    services = services_for({"analyst": script})
    req = request("Export California customers for marketing", export=True)
    req.approved_sql = (EMAIL_SQL,)
    outcome = run(VerificationLoop(services, ListHooks()), req)
    assert outcome.status is RunStatus.ANSWERED and outcome.personal_data
    other = request("Export California customers for marketing", export=True)
    other.approved_sql = ("SELECT email FROM customers_marketable WHERE state = 'TX'",)
    assert run(VerificationLoop(services, ListHooks()), other).status is (
        RunStatus.AWAITING_APPROVAL
    ), "a different query still needs its own approval"


def test_an_export_from_the_base_customers_table_is_blocked(services_for) -> None:
    feedback: list[str] = []

    def script(messages: Sequence[BaseMessage]) -> AIMessage:
        tools = tool_messages(messages)
        if not tools:
            return call(
                "run_query", {"sql": "SELECT email FROM customers WHERE state = 'CA'"}, "base"
            )
        feedback.append(str(tools[-1].content))
        return envelope(EMAIL_SQL, "Exported.", status="refused")

    run(VerificationLoop(services_for({"analyst": script}), ListHooks()), request(export=True))
    assert "customers_marketable" in feedback[0]


# --- the schema scout and the reviewer ---
def test_the_schema_scout_is_a_stateless_tool(services_for) -> None:
    briefs: list[str] = []

    def analyst(messages: Sequence[BaseMessage]) -> AIMessage:
        tools = tool_messages(messages)
        if not tools:
            return call("scout_schema", {"question": "orders by state"}, "scout")
        if len(tools) == 1:
            briefs.append(str(tools[0].content))
            return call("run_query", {"sql": COUNT_SQL}, "q")
        return envelope(COUNT_SQL, "There are 2000 orders.")

    def scout(messages: Sequence[BaseMessage]) -> AIMessage:
        if len(messages) == 2:  # the system prompt and the question only: no memory
            return call("describe_table", {"name": "orders"}, "d")
        return call(
            "SchemaBrief",
            {"tables": [{"table": "orders", "columns": ["status"], "why": "orders"}], "joins": []},
            "brief",
        )

    services = services_for({"analyst": analyst, "schema_scout": scout}, scout=True)
    outcome = run(VerificationLoop(services, ListHooks()), request())
    assert outcome.status is RunStatus.ANSWERED
    assert json.loads(briefs[0])["tables"][0]["table"] == "orders"


def reviewer_script(outcomes: list[str]):
    def script(messages: Sequence[BaseMessage]) -> AIMessage:
        assert "Final SQL" in str(messages[-1].content) and "Result preview" in str(
            messages[-1].content
        )
        outcome = outcomes.pop(0)
        return call("ReviewVerdict", {"outcome": outcome, "reasons": [f"{outcome} reason"]}, "v")

    return script


def test_the_reviewer_approves_after_every_grader_passed(services_for) -> None:
    script = query_then_answer(COUNT_SQL, "There are 2000 orders.")
    services = services_for(
        {"analyst": script, "reviewer": reviewer_script(["approve"])}, reviewer=True
    )
    hooks = ListHooks()
    outcome = run(VerificationLoop(services, hooks), request())
    assert outcome.status is RunStatus.ANSWERED and outcome.verdict
    assert hooks.kinds("reviewer_verdict")[0]["outcome"] == "approve"


def test_a_reviewer_concern_is_fed_back_once_then_holds_for_approval(services_for) -> None:
    script = query_then_answer(COUNT_SQL, "There are 2000 orders.")
    reviewer = reviewer_script(["concern", "concern"])
    services = services_for({"analyst": script, "reviewer": reviewer}, reviewer=True)
    hooks = ListHooks()
    outcome = run(VerificationLoop(services, hooks), request())
    assert outcome.status is RunStatus.AWAITING_APPROVAL
    assert outcome.approval and outcome.approval.kind == "held_answer"
    assert hooks.statuses[-1] == RunStatus.VERIFYING and outcome.attempts == 2


def test_a_reviewer_that_gives_no_verdict_holds_the_answer_for_approval(services_for) -> None:
    """Live, run b95481b8 posted an answer the reviewer gave no verdict on, as if it had approved.
    The owner's decision of 27 October 2026: no verdict fails closed, so the answer waits for a
    person."""

    def no_verdict(messages: Sequence[BaseMessage]) -> AIMessage:
        return AIMessage("I cannot tell.", usage_metadata=usage(300, 20))

    script = query_then_answer(COUNT_SQL, "There are 2000 orders.")
    services = services_for({"analyst": script, "reviewer": no_verdict}, reviewer=True)
    hooks = ListHooks()
    outcome = run(VerificationLoop(services, hooks), request())
    assert outcome.status is RunStatus.AWAITING_APPROVAL and outcome.verdict is None
    assert outcome.approval and outcome.approval.kind == "held_answer"
    assert outcome.approval.reason == "the reviewer gave no verdict"
    assert hooks.kinds("reviewer_verdict")[0]["outcome"] == "no verdict"


def test_a_run_without_the_reviewer_is_answered_without_a_verdict(services_for) -> None:
    script = query_then_answer(COUNT_SQL, "There are 2000 orders.")
    services = services_for({"analyst": script}, reviewer=False)
    outcome = run(VerificationLoop(services, ListHooks()), request())
    assert outcome.status is RunStatus.ANSWERED and outcome.verdict is None


def test_a_resumed_run_keeps_its_attempt_and_the_reviewers_one_concern(services_for) -> None:
    """Live, every reviewer concern after an approval sent the analyst back to rewrite the export,
    and each rewrite was held again, to about 110,000 tokens: a resume started the concern count
    and the attempt over. A resumed run now holds the answer at the second concern."""
    script = query_then_answer(EMAIL_SQL, "Exported the California customers who may be contacted.")
    reviewer = reviewer_script(["concern"])  # a second review would find the script empty
    services = services_for({"analyst": script, "reviewer": reviewer}, reviewer=True)
    req = request("Export California customers for marketing", export=True)
    assert run(VerificationLoop(services, ListHooks()), req).status is RunStatus.AWAITING_APPROVAL
    req.attempt, req.concern_fed_back = 2, True  # what the worker reads from the run's events
    loop = VerificationLoop(services, ListHooks(RunStatus.RUNNING))
    resumed = asyncio.run(loop.resume(req, approve=True))
    assert resumed.status is RunStatus.AWAITING_APPROVAL and resumed.attempts == 2
    assert resumed.approval and resumed.approval.kind == "held_answer"


def test_a_kill_switch_engaged_before_the_review_ends_the_run_blocked_not_escalated(
    services_for,
) -> None:
    """Before, a stop seen at the review ended the run escalated, so the board showed escalated
    for a run the kill switch stopped and the run counted toward the escalation demotion."""
    from datapilot.loop1_agent.guard import StopReason

    script = query_then_answer(COUNT_SQL, "There are 2000 orders.")
    services = services_for({"analyst": script, "reviewer": reviewer_script([])}, reviewer=True)
    hooks = ListHooks()

    def engaged_once_verifying() -> StopReason | None:
        return StopReason.KILL_SWITCH if RunStatus.VERIFYING in hooks.statuses else None

    loop = VerificationLoop(services, hooks, external_stop=engaged_once_verifying)
    outcome = run(loop, request())
    assert outcome.status is RunStatus.BLOCKED_KILLSWITCH  # the empty reviewer was never called
    assert outcome.envelope is not None and outcome.verdict is None


def test_the_reviewer_never_sees_a_failed_grader(services_for) -> None:
    script = query_then_answer(COUNT_SQL, "There are 2000 orders.")
    services = services_for({"analyst": script, "reviewer": reviewer_script([])}, reviewer=True)
    outcome = run(VerificationLoop(services, ListHooks()), request(inject_failing_grader=True))
    assert outcome.status is RunStatus.ESCALATED  # the empty reviewer script was never called


# --- the per-call output-token cap ---
CUT_OFF = {"status": "incomplete", "incomplete_details": {"reason": "max_output_tokens"}}


def cut_off_reply(messages: Sequence[BaseMessage]) -> AIMessage:
    """Live, one analyst call produced about 130,000 output tokens; the cap now cuts it off."""
    return AIMessage("", response_metadata=CUT_OFF, usage_metadata=usage(900, 16000))


def test_an_analyst_reply_cut_off_at_its_cap_ends_the_run_escalated(services_for) -> None:
    services = services_for({"analyst": cut_off_reply})
    outcome = run(VerificationLoop(services, ListHooks()), request())
    assert outcome.status is RunStatus.ESCALATED and outcome.attempts == 1
    assert any("output-token cap after 16000 tokens" in r for r in outcome.reasons)
    assert outcome.tokens_out == 16000, "the cut-off call's tokens are counted"


def test_a_reviewer_reply_cut_off_at_its_cap_ends_the_run_escalated(services_for) -> None:
    script = query_then_answer(COUNT_SQL, "There are 2000 orders.")
    services = services_for({"analyst": script, "reviewer": cut_off_reply}, reviewer=True)
    outcome = run(VerificationLoop(services, ListHooks()), request())
    assert outcome.status is RunStatus.ESCALATED
    assert any("output-token cap" in r for r in outcome.reasons)


def test_a_reply_cut_off_as_the_responses_api_sends_it_names_its_real_output_tokens(
    services_for,
) -> None:
    """A real ChatOpenAI over a stand-in client returns an incomplete Responses API reply of 14
    output tokens as the first call; the reason names 14, as the ledger does."""
    from dataclasses import replace

    from cut_off_responses import OUTPUT_TOKENS, LedgerView, cut_off_model, incomplete_response

    ledger = LedgerView()
    model = cut_off_model(incomplete_response(), [ledger])
    services = replace(services_for({}), models=lambda component: model)
    outcome = run(VerificationLoop(services, ListHooks()), request())
    assert outcome.status is RunStatus.ESCALATED and ledger.output_tokens == [OUTPUT_TOKENS]
    assert outcome.reasons == [
        f"a model response was cut off at its output-token cap after {OUTPUT_TOKENS} tokens"
    ]
    assert outcome.tokens_out == OUTPUT_TOKENS


def test_the_live_probe_cut_off_after_list_tables_never_reads_after_0_tokens(
    services_for,
) -> None:
    """The live probe's two calls (runs d9f0ab0e and 730953ea, two ledger rows each): list_tables
    completed within the cap (715 input, 14 output tokens), then the next call was cut off and
    reported 0 input and 0 output tokens. The reason never says 0 tokens; it names the 14 output
    tokens the run's calls reported, which is the ledger's total for the run."""
    from dataclasses import replace

    from cut_off_responses import (
        OUTPUT_TOKENS,
        LedgerView,
        cut_off_model,
        incomplete_response,
        list_tables_response,
        stand_in,
    )

    ledger = LedgerView()
    replies = [list_tables_response(), incomplete_response(input_tokens=0, output_tokens=0)]
    model = cut_off_model(replies, [ledger])
    hooks = ListHooks()
    services = replace(services_for({}), models=lambda component: model)
    outcome = run(VerificationLoop(services, hooks), request())
    assert ledger.output_tokens == [OUTPUT_TOKENS, 0] and stand_in(model).calls == 2
    assert [p["tool"] for p in hooks.kinds("tool_call_finished")] == ["list_tables"]
    assert outcome.status is RunStatus.ESCALATED and outcome.attempts == 1
    assert outcome.reasons == [
        "a model response was cut off at its output-token cap; it reported no output-token "
        f"count, and the run's model calls so far reported {OUTPUT_TOKENS} output tokens"
    ]
    assert outcome.tokens_out == OUTPUT_TOKENS
