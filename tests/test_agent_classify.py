from types import SimpleNamespace

import pytest

from loopeng.agent.classify import Outcome, VisibleKind, judge, summarise
from loopeng.agent.loop import run_question
from loopeng.agent.trap import TrapState, run_trap
from loopeng.gold.build import build_gold
from loopeng.warehouse.connect import ensure_warehouse


@pytest.fixture(scope="module")
def warehouse(tmp_path_factory):
    return ensure_warehouse(tmp_path_factory.mktemp("wh") / "w.duckdb", seed=20260729)


@pytest.fixture(scope="module")
def items(warehouse):
    return build_gold(warehouse)


class ScriptedClient:
    """Returns SQL chosen per question, so a whole grid can be driven offline."""

    def __init__(self, sql_for):
        self.calls = 0
        self._sql_for = sql_for
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.calls += 1
        question = kwargs["messages"][0]["content"].split("Question: ")[-1]
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text=self._sql_for(question))],
            usage=SimpleNamespace(input_tokens=100, output_tokens=50),
        )


def _item(items, key):
    return next(i for i in items if i.pattern_key == key)


# ---- the visible / silent split ---------------------------------------------


def test_a_correct_answer_is_correct(items, warehouse):
    item = items[0]
    client = ScriptedClient(lambda q: item.gold_sql)
    run = run_question(item.question, warehouse=warehouse, client=client)
    assert judge(run, item).outcome is Outcome.CORRECT


def test_a_wrong_but_clean_answer_is_a_SILENT_error(items, warehouse):
    """Ran, returned a plausible number, wrong. The category the whole workshop is
    about, and the one Level 1 cannot see."""
    item = _item(items, "p04_gross_revenue")
    client = ScriptedClient(lambda q: item.naive_sql)
    run = run_question(item.question, warehouse=warehouse, client=client)
    judgement = judge(run, item)
    assert judgement.outcome is Outcome.SILENT_ERROR
    assert judgement.ran_and_returned


def test_an_execution_error_is_a_VISIBLE_failure(items, warehouse):
    item = items[0]
    client = ScriptedClient(lambda q: "SELECT * FROM no_such_table")
    run = run_question(item.question, warehouse=warehouse, client=client, max_attempts=1)
    judgement = judge(run, item)
    assert judgement.outcome is Outcome.VISIBLE_FAILURE
    assert judgement.visible_kind is VisibleKind.EXECUTION_ERROR
    assert not judgement.ran_and_returned


def test_an_empty_result_is_visible_not_silent(items, warehouse):
    """A query that runs and returns nothing is visibly odd, not silently wrong."""
    item = items[0]
    client = ScriptedClient(lambda q: "SELECT 1 WHERE 1 = 0")
    run = run_question(item.question, warehouse=warehouse, client=client, max_attempts=1)
    judgement = judge(run, item)
    assert judgement.outcome is Outcome.VISIBLE_FAILURE
    assert judgement.visible_kind is VisibleKind.EMPTY_RESULT


def test_silent_error_rate_denominator_excludes_visible_failures(items, warehouse):
    """The rule that keeps the headline number meaningful: folding visible failures
    in would inflate it with failures the room can already see."""
    good, bad, broken = items[0], _item(items, "p04_gross_revenue"), items[1]

    def sql_for(question):
        if question.strip() == good.question:
            return good.gold_sql
        if question.strip() == bad.question:
            return bad.naive_sql
        return "SELECT * FROM no_such_table"

    client = ScriptedClient(sql_for)
    judgements = [
        judge(run_question(i.question, warehouse=warehouse, client=client, max_attempts=1), i)
        for i in (good, bad, broken)
    ]
    summary = summarise(judgements)
    assert summary["n_total"] == 3
    assert summary["n_ran_and_returned"] == 2
    assert summary["n_silent_errors"] == 1
    assert summary["n_visible_failures"] == 1


# ---- the taxonomy -----------------------------------------------------------


def test_a_naive_match_is_attributed_to_its_rule(items, warehouse):
    """"Ignored rule X" rather than a generic wrong answer — the reason the per-rule
    variants were built."""
    item = _item(items, "p02_orders_in_month")
    naive = item.naive_by_rule["soft_delete"]["sql"]
    client = ScriptedClient(lambda q: naive)
    run = run_question(item.question, warehouse=warehouse, client=client)
    judgement = judge(run, item)
    assert judgement.outcome is Outcome.SILENT_ERROR
    assert judgement.attributed_rules == ("soft_delete",)
    assert not judgement.unclassified


def test_the_ambiguous_item_reports_both_rules_and_picks_neither(items, warehouse):
    """p03_customers_in_region__02's variants collide. Naming one would be a coin
    flip presented as a finding."""
    item = next(i for i in items if i.item_id == "p03_customers_in_region__02")
    assert item.ambiguous_rule_groups, "this item is expected to be the ambiguous one"

    naive = item.naive_by_rule["soft_delete"]["sql"]
    client = ScriptedClient(lambda q: naive)
    run = run_question(item.question, warehouse=warehouse, client=client)
    judgement = judge(run, item)
    assert set(judgement.attributed_rules) == {"soft_delete", "internal_accounts"}
    assert judgement.ambiguous


def test_a_wrong_answer_matching_no_variant_is_unclassified(items, warehouse):
    """Reported as its own count. If most errors land here the taxonomy is weak and
    we say so rather than implying coverage we do not have."""
    item = _item(items, "p02_orders_in_month")
    client = ScriptedClient(lambda q: "SELECT 987654")
    run = run_question(item.question, warehouse=warehouse, client=client)
    judgement = judge(run, item)
    assert judgement.outcome is Outcome.SILENT_ERROR
    assert judgement.attributed_rules == ()
    assert judgement.unclassified


def test_summary_counts_unclassified_and_ambiguous_separately(items, warehouse):
    item = _item(items, "p02_orders_in_month")
    client = ScriptedClient(lambda q: "SELECT 987654")
    run = run_question(item.question, warehouse=warehouse, client=client)
    summary = summarise([judge(run, item)])
    assert summary["n_unclassified"] == 1
    assert summary["attribution"] == {}


# ---- reveal is a state flip -------------------------------------------------


def test_reveal_triggers_zero_model_calls(items, warehouse):
    """Re-running to score would burn the wall-clock again and lose the room. The
    judgement is computed as each cell lands; reveal only decides whether it shows."""
    subset = items[:3]
    client = ScriptedClient(lambda q: "SELECT COUNT(*) FROM products")
    state = run_trap(subset, warehouse, arms=(("worker", "L3"),), client=client)

    calls_after_run = client.calls
    assert calls_after_run == len(subset)

    state.reveal()
    assert state.revealed
    assert client.calls == calls_after_run, "reveal made a model call"


def test_judgements_exist_before_reveal(items, warehouse):
    """Scoring happens on arrival. The button reveals; it does not compute."""
    client = ScriptedClient(lambda q: "SELECT COUNT(*) FROM products")
    state = run_trap(items[:2], warehouse, arms=(("worker", "L3"),), client=client)
    assert not state.revealed
    assert all(cell.judgement is not None for cell in state.cells.values())


def test_silent_error_rate_is_none_before_anything_lands():
    """A rate with no observations is not a rate. Rendering it as 0% would be a
    claim, and "not yet measured" is the truth."""
    assert TrapState().silent_error_rate("worker") is None


def test_silent_error_rate_carries_its_n(items, warehouse):
    item = _item(items, "p04_gross_revenue")
    client = ScriptedClient(lambda q: item.naive_sql)
    state = run_trap([item], warehouse, arms=(("worker", "L3"),), client=client)
    metric = state.silent_error_rate("worker@L3")
    assert metric.n == 1
    assert metric.value == 1.0
    assert "n=1" in metric.render()


def test_trap_runs_every_item_against_every_arm(items, warehouse):
    """The arms are the same model at two spec levels, so the SPEC is the variable."""
    client = ScriptedClient(lambda q: "SELECT COUNT(*) FROM products")
    subset = items[:4]
    state = run_trap(subset, warehouse, client=client)
    assert len(state.cells) == len(subset) * 2
    assert client.calls == len(subset) * 2
    assert {cell.arm for cell in state.cells.values()} == {"worker@L3", "worker@L0"}


def test_the_default_arms_hold_the_model_constant(items, warehouse):
    """Haiku-vs-Sonnet would teach "buy the bigger model", the opposite of the
    thesis. Same model at two spec levels makes the spec the variable."""
    from loopeng.agent.trap import ARMS

    assert {role for role, _ in ARMS} == {"worker"}
    assert {level for _, level in ARMS} == {"L0", "L3"}


def test_both_arms_are_labelled_for_the_screen(items, warehouse):
    """L0 alone is a wall of red that teaches nothing; the L3 column is what makes it
    legible, so both columns have to say which they are."""
    from loopeng.agent.trap import ARMS, arm_label

    for role, level in ARMS:
        label = arm_label(role, level)
        assert "rules" in label.lower()
        assert level in label


def test_cells_stream_back_as_they_land(items, warehouse):
    """The grid filling is part of the demo, so the runner must emit per cell rather
    than batching and dumping at the end."""
    seen = []
    client = ScriptedClient(lambda q: "SELECT COUNT(*) FROM products")
    run_trap(items[:4], warehouse, arms=(("worker", "L3"),), client=client,
             on_cell=seen.append)
    assert len(seen) == 4


# ---- visible kinds added after the first trap run ---------------------------


def test_a_column_count_mismatch_is_VISIBLE_not_silent(items, warehouse):
    """Measured on the first Phase 1 trap: 11 of 35 apparent silent errors were a
    model returning the right numbers plus an extra label column — (product_id,
    category, units) where gold returns (product_id, units).

    It is visible by the project's own definition: a silent error is one you cannot
    detect without knowing the answer, and a column count is knowable without it. You
    asked for one number and got three. Scoring these as silent errors measured how
    precisely the question pinned down an output schema, not whether the model
    understood the business rules, and it inflated the headline by a third.
    """
    item = _item(items, "p01_product_count")
    client = ScriptedClient(lambda q: "SELECT COUNT(*), 'extra' FROM products")
    run = run_question(item.question, warehouse=warehouse, client=client, max_attempts=1)
    judgement = judge(run, item)
    assert judgement.outcome is Outcome.VISIBLE_FAILURE
    assert judgement.visible_kind is VisibleKind.SHAPE_MISMATCH
    assert not judgement.ran_and_returned


def test_an_all_null_answer_is_VISIBLE_not_silent(items, warehouse):
    """A row of NULLs is not a plausible answer; it is a visible non-answer."""
    item = _item(items, "p01_product_count")
    client = ScriptedClient(lambda q: "SELECT NULL")
    run = run_question(item.question, warehouse=warehouse, client=client, max_attempts=1)
    judgement = judge(run, item)
    assert judgement.outcome is Outcome.VISIBLE_FAILURE
    assert judgement.visible_kind is VisibleKind.NULL_RESULT


def test_the_right_shape_with_a_wrong_number_is_still_SILENT(items, warehouse):
    """The reclassification must not become a way to launder real errors: same shape,
    wrong value, still silent."""
    item = _item(items, "p01_product_count")
    client = ScriptedClient(lambda q: "SELECT 999999")
    run = run_question(item.question, warehouse=warehouse, client=client, max_attempts=1)
    assert judge(run, item).outcome is Outcome.SILENT_ERROR


def test_display_rounding_is_not_scored_as_an_error(items, warehouse):
    """A correct query that does not round where the gold SQL does."""
    item = _item(items, "p07_aov_by_region")
    unrounded = item.gold_sql.replace("ROUND(", "(").replace("), 2)", "))")
    client = ScriptedClient(lambda q: unrounded)
    run = run_question(item.question, warehouse=warehouse, client=client, max_attempts=1)
    assert judge(run, item).outcome is Outcome.CORRECT


def test_a_tie_break_difference_is_not_an_error():
    """The real case from the Phase 1 trap: p06_top_products__04 returned the same
    five products with the same five counts, ordering the two tied at 120 the other
    way round. The question does not say how to break a tie; the gold SQL picks
    product_id only because SQL needs a total order."""
    from loopeng.agent.classify import _tie_break_only

    gold = [[137, 121], [127, 120], [188, 120], [163, 119], [92, 117]]
    model = [[137, 121], [188, 120], [127, 120], [163, 119], [92, 117]]
    assert _tie_break_only(model, gold, order_sensitive=True)


def test_a_genuinely_different_ranking_is_still_an_error():
    """The allowance must not excuse a wrong ranking. Here the measure column itself
    is out of order, which is a different claim about which sold most."""
    from loopeng.agent.classify import _tie_break_only

    gold = [[137, 121], [127, 120], [188, 120], [163, 119], [92, 117]]
    reordered = [[92, 117], [163, 119], [127, 120], [188, 120], [137, 121]]
    assert not _tie_break_only(reordered, gold, order_sensitive=True)


def test_a_different_top_five_is_still_an_error():
    """A different set of products is not a tie-break difference at all."""
    from loopeng.agent.classify import _tie_break_only

    gold = [[137, 121], [127, 120], [188, 120], [163, 119], [92, 117]]
    different = [[137, 121], [127, 120], [188, 120], [163, 119], [999, 117]]
    assert not _tie_break_only(different, gold, order_sensitive=True)


def test_tie_break_allowance_does_not_apply_to_unordered_items():
    """Only order-sensitive items have a tie-break to forgive."""
    from loopeng.agent.classify import _tie_break_only

    gold = [[137, 121], [127, 120]]
    model = [[127, 120], [137, 121]]
    assert not _tie_break_only(model, gold, order_sensitive=False)


def test_a_row_count_mismatch_is_VISIBLE_not_silent(items, warehouse):
    """Found by Phase 4 triage: a query returned 105 rows where gold had 1 — an
    aggregate that never collapsed — and was scored a SILENT error because only the
    column count was compared. Asking for one number and getting a hundred and five is
    as visible as getting three columns. The asymmetry was ours, not the model's."""
    item = _item(items, "p01_product_count")
    client = ScriptedClient(lambda q: "SELECT product_id FROM products LIMIT 20")
    run = run_question(item.question, warehouse=warehouse, client=client, max_attempts=1)
    judgement = judge(run, item)
    assert judgement.outcome is Outcome.VISIBLE_FAILURE
    assert judgement.visible_kind is VisibleKind.SHAPE_MISMATCH


def test_an_order_sensitive_item_may_return_many_rows(items, warehouse):
    """A top-N query legitimately returns many rows; a wrong N is a wrong ranking, not
    a shape mismatch, so the row check must not fire on the correct answer."""
    item = _item(items, "p06_top_products")
    client = ScriptedClient(lambda q: item.gold_sql)
    run = run_question(item.question, warehouse=warehouse, client=client, max_attempts=1)
    assert judge(run, item).outcome is Outcome.CORRECT


# ---- a failed call is not a failed query -------------------------------------


def _run_ending_in(sql, error, outcome):
    from loopeng.agent.loop import AgentRun, Attempt, TerminationReason
    from loopeng.usage import CallUsage

    return AgentRun(
        question="q", level="L3", role="worker", model_id="m",
        attempts=(Attempt(n=1, sql=sql, rows=None, error=error,
                          usage=CallUsage(model_id="m", outcome=outcome)),),
        termination=TerminationReason.MAX_ATTEMPTS,
    )


def test_a_failed_model_call_is_not_reported_as_an_execution_error(items):
    """A sweep run on a bad key used to report that every item hit an execution
    error, sending the operator to the SQL and the warehouse. The database was
    never involved: no query was ever sent."""
    verdict = judge(_run_ending_in("", "AuthenticationError: invalid x-api-key", "auth"),
                    items[0])
    assert verdict.outcome is Outcome.VISIBLE_FAILURE
    assert verdict.visible_kind is VisibleKind.MODEL_CALL_FAILED


def test_a_real_database_error_is_still_an_execution_error(items):
    verdict = judge(_run_ending_in("SELECT nope FROM orders", 'Binder Error: no "nope"',
                                   "ok"), items[0])
    assert verdict.outcome is Outcome.VISIBLE_FAILURE
    assert verdict.visible_kind is VisibleKind.EXECUTION_ERROR


def test_a_query_timeout_is_still_a_timeout(items):
    verdict = judge(_run_ending_in("SELECT 1", "QueryTimeout: 30s", "ok"), items[0])
    assert verdict.visible_kind is VisibleKind.TIMEOUT


def test_splitting_the_bucket_moves_no_rate(items):
    """`ran_and_returned` is False either way, so the silent-error numerator and
    denominator are untouched — this only stops one bucket from lying about cause."""
    failed_call = judge(_run_ending_in("", "RateLimitError: 429", "rate_limit"), items[0])
    db_error = judge(_run_ending_in("SELECT x", "Binder Error", "ok"), items[0])
    assert failed_call.ran_and_returned is False
    assert db_error.ran_and_returned is False
