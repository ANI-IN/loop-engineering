"""The hill-climbing wiring, zero tokens: trace links and feedback, the console's confirmation
fields, the gold check payload, the runner's helpers, and knowledge version composition."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from loop4_doubles import TableRunner, answered, experiment, item

from datapilot.contracts import ItemResult, KnowledgeRule, KnowledgeVersion, Split
from datapilot.loop4_hill_climbing import gold, versions
from datapilot.loop4_hill_climbing.evaluator import ExecutionEvaluator
from datapilot.loop4_hill_climbing.experiment import Confirmation, RunRecord
from datapilot.loop4_hill_climbing.runner import (
    HillClimbingRunner,
    RequestFailed,
    confirmed_regressions,
    failed_dev_items,
)
from datapilot.observability.traces import FeedbackTracer, ModelIds, TraceLinks, web_url

TENANT, PROJECT = uuid.uuid4(), uuid.uuid4()


class _Client:
    def __init__(self, known: bool = True) -> None:
        self.known, self.feedback, self.created = known, [], []

    def read_project(self, *, project_name: str):
        if not self.known:
            raise LookupError(project_name)
        return SimpleNamespace(id=PROJECT, tenant_id=TENANT)

    def create_project(self, name: str, **kwargs):
        self.created.append(name)
        return SimpleNamespace(id=PROJECT, tenant_id=TENANT)

    def create_feedback(self, run_id, key, **kwargs):
        self.feedback.append((run_id, key, kwargs))


def test_the_web_host_comes_from_the_api_endpoint() -> None:
    assert web_url("https://api.smith.langchain.com") == "https://smith.langchain.com"
    assert web_url("https://eu.api.smith.langchain.com/") == "https://eu.smith.langchain.com"


def test_a_run_link_names_the_workspace_project_and_run() -> None:
    client = _Client(known=False)
    links = TraceLinks(client, "datapilot-experiments", "https://smith.langchain.com")
    run_id = uuid.uuid4()
    assert links.url(run_id) == (
        f"https://smith.langchain.com/o/{TENANT}/projects/p/{PROJECT}/r/{run_id}?poll=true"
    )
    links.url(uuid.uuid4())
    assert client.created == ["datapilot-experiments"], "the project is looked up once"


def test_experiment_feedback_goes_on_the_analysts_own_trace_with_retention_off() -> None:
    client = _Client()
    tracer = FeedbackTracer(client, TraceLinks(client, "p", "https://smith.langchain.com"))
    now = datetime.now(UTC)
    record = RunRecord(
        item("h1", Split.HOLDOUT),
        2,
        "v1",
        answered("SELECT 1"),
        ItemResult(item_id="h1", passed=False, reason="row 1 differs from gold"),
        now,
        now,
    )
    link = tracer.trace(record, experiment_id=uuid.uuid4())
    # feedback goes out from the background sender, so a refused upload never holds up a run
    assert tracer.feedback.flush(timeout=5)
    (run_id, key, kwargs) = client.feedback[0]
    assert run_id == record.run_id and kwargs["trace_id"] == record.run_id
    assert key == "execution_match" and kwargs["score"] == 0
    assert kwargs["extend_trace_retention"] is False
    assert link and str(record.run_id) in link


def test_the_confirmation_carries_the_fields_the_console_ledger_reads() -> None:
    confirming = Confirmation("h1", Split.HOLDOUT, steps=["Apparent regression"], planned=3)
    shown = confirming.as_dict()
    assert (shown["state"], shown["runs"], shown["failures"]) == ("confirming", 3, 0)
    confirming.reruns, confirming.confirmed = [False, True, False], True
    assert confirming.as_dict()["state"] == "confirmed"
    assert confirming.as_dict()["failures"] == 2
    cleared = Confirmation("h2", Split.HOLDOUT, reruns=[True, True, False], confirmed=False)
    assert cleared.as_dict()["state"] == "cleared" and cleared.as_dict()["runs"] == 3


def test_the_console_reads_a_confirmation_as_its_ledger_step(monkeypatch) -> None:
    from datapilot.settings import PLATFORM

    monkeypatch.syspath_prepend(str(PLATFORM / "console"))
    from datapilot_console.views import confirm_regression

    done = Confirmation("h1", Split.HOLDOUT, reruns=[False, False, True], confirmed=True, planned=3)
    assert confirm_regression(done.as_dict()) == (
        "regression",
        "Regression: confirmed, failed 2 of 3 more runs",
    )


def test_a_dev_confirmation_carries_the_active_re_runs(monkeypatch) -> None:
    from datapilot.settings import PLATFORM

    monkeypatch.syspath_prepend(str(PLATFORM / "console"))
    from datapilot_console.views import confirm_regression

    from datapilot.loop4_hill_climbing.gate import DevConfirmation
    from datapilot.loop4_hill_climbing.store import _confirmation

    going = DevConfirmation("d1", Split.DEV, planned=2, active_planned=2)
    shown = going.as_dict()
    assert (shown["active_runs"], shown["active_passes"]) == (2, 0)
    assert confirm_regression(shown) == (
        "confirming",
        "Apparent regression: confirming with 2 more runs of each version",
    )
    going.reruns, going.active_reruns, going.confirmed = [False, False], [True, False], False
    assert confirm_regression(going.as_dict()) == (
        "same",
        "Not a regression: the candidate failed 2 of 2 more runs, the active version passed 1 of 2",
    )
    readback = _confirmation({"item_id": "d1", "confirmation": going.as_dict()})
    assert isinstance(readback, DevConfirmation)
    assert readback.active_reruns == [True, False] and readback.active_planned == 2
    holdout = _confirmation({"item_id": "h1", "confirmation": done_holdout().as_dict()})
    assert not isinstance(holdout, DevConfirmation) and holdout.reruns == [False, False, True]


def done_holdout() -> Confirmation:
    return Confirmation("h1", Split.HOLDOUT, reruns=[False, False, True], confirmed=True, planned=3)


SPINE = item(
    "net-revenue-fiscal-2025",
    question="What was our net revenue in fiscal year 2025?",
    gold_sql="SELECT 100.00",
    traps=["net_revenue"],
)


def test_the_gold_check_payload_shows_both_values_and_the_trap() -> None:
    wrong = "SELECT sum(total_cents) / 100.0 FROM warehouse.orders"
    runner = TableRunner(
        {
            ("SELECT 100.00", "warehouse"): [(100.00,)],
            ("SELECT 100.00", "warehouse_alt"): [(80.00,)],
            (wrong, "warehouse"): [(123.45,)],
            (wrong, "warehouse_alt"): [(99.00,)],
        }
    )
    payload = gold.gold_payload(SPINE, answered(wrong), ExecutionEvaluator(runner))
    assert payload["grader"] == "gold" and payload["passed"] is False
    assert (payload["agent_value"], payload["gold_value"]) == ("123.45", "100.0")
    assert payload["trap_labels"] == ["total_cents_used"]
    # the gold check shows the result on both databases, not only the first that differs
    assert payload["warehouses"] == {"warehouse": False, "warehouse_alt": False}
    assert payload["reason"].startswith("warehouse: ") and "; warehouse_alt: " in payload["reason"]


def test_a_run_whose_gold_check_fails_is_recorded_and_never_blocks_the_others() -> None:
    recorded: list[tuple[str, dict]] = []

    class _Conn:
        def execute(self, sql, params=None):
            if sql.startswith("INSERT INTO ops.run_events"):
                recorded.append((params[0], params[2].obj))
                return self
            rows = [
                {"run_id": "bad", "question": SPINE.question, "answer": {"envelope": {}}},
                {
                    "run_id": "good",
                    "question": SPINE.question,
                    "answer": {"envelope": {"status": "answered", "final_sql": "SELECT 100.00"}},
                },
            ]
            return SimpleNamespace(fetchall=lambda: rows)

    runner = TableRunner({("SELECT 100.00", w): [(100.0,)] for w in ("warehouse", "warehouse_alt")})
    checked = gold.check_new_runs(_Conn(), [SPINE], ExecutionEvaluator(runner))  # type: ignore[arg-type]
    assert checked == ["bad", "good"]
    assert recorded[0][1]["reason"].startswith("the gold check could not run")
    assert recorded[1][1]["passed"] is True


SPLITS = {"d1": Split.DEV, "d2": Split.DEV, "h1": Split.HOLDOUT}


def test_the_analyzer_reads_only_failed_dev_items_with_their_deciding_sql() -> None:
    base = experiment("v1", {"d1": False, "d2": True, "h1": False}, SPLITS)
    base.final_sql = {"d1": "SELECT 2"}
    items = [item("d1"), item("d2"), item("h1", Split.HOLDOUT)]
    failed = failed_dev_items(items, base)
    assert [f.item.id for f in failed] == ["d1"]
    assert failed[0].answer is not None and failed[0].answer.final_sql == "SELECT 2"


def test_a_promotion_counts_the_regressions_the_gate_confirmed() -> None:
    candidate = experiment("v2", {"d1": False, "d2": True, "h1": False}, SPLITS)
    candidate.confirmations = {
        "d1": Confirmation("d1", Split.DEV, [False, False], True),
        "h1": Confirmation("h1", Split.HOLDOUT, [True, True, False], False),
    }
    found = confirmed_regressions(candidate)
    assert (found.dev, found.holdout, found.not_confirmed) == (["d1"], [], ["h1"])


def test_a_request_without_a_live_session_fails_plainly() -> None:
    runner = HillClimbingRunner([], lambda q, v: answered("SELECT 1"), None, None, 1)  # type: ignore[arg-type]
    with pytest.raises(RequestFailed, match="no live session"):
        runner.run({"kind": "experiment", "params": {}, "session_id": None})


def test_the_over_broad_rule_is_added_to_the_active_version() -> None:
    rule = KnowledgeRule(id="money", title="Money", rule_text="cents", applies_when="money")
    extra = KnowledgeRule(id="discounts", title="Discounts", rule_text="x", applies_when="y")
    active = KnowledgeVersion(version="v2", rules=[rule])
    overbroad = KnowledgeVersion(version="v2-overbroad", rules=[rule, extra])
    combined = versions.with_rules_of(active, overbroad, "v2-plus-over-broad-rule")
    assert [r.id for r in combined.rules] == ["money", "discounts"]


def test_the_shipped_versions_are_the_starting_and_the_over_broad_one() -> None:
    assert versions.shipped() == [versions.STARTING_VERSION, versions.OVERBROAD_VERSION]
    assert "version: v1" in versions.to_yaml(versions.load_knowledge("v1"))


def test_runs_from_many_threads_share_one_event_loop() -> None:
    """The OpenAI async client is bound to the first loop that used it: a run that started and
    closed its own loop broke the next one ("Event loop is closed")."""
    import asyncio
    from concurrent.futures import ThreadPoolExecutor

    from datapilot.loop4_hill_climbing.targets import shared_loop

    async def which() -> int:
        await asyncio.sleep(0)
        return id(asyncio.get_running_loop())

    with ThreadPoolExecutor(4) as pool:
        loops = set(pool.map(lambda _: shared_loop().run(which()), range(8)))
    assert len(loops) == 1


def test_model_ids_are_counted_by_component() -> None:
    ids = ModelIds()
    message = SimpleNamespace(response_metadata={"model_name": "class-model-2026-10-01"})
    result = SimpleNamespace(generations=[[SimpleNamespace(message=message)]])
    ids.for_component("analyst").on_llm_end(result)
    ids.for_component("analyst").on_llm_end(result)
    assert ids.as_rows() == [
        {"component": "analyst", "model_id": "class-model-2026-10-01", "calls": 2}
    ]
