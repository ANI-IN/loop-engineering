
import pytest

from loopeng.agent.classify import Outcome, VisibleKind, judge, summarise
from loopeng.agent.loop import run_question
from loopeng.agent.trap import TrapState, run_trap
from loopeng.gold.build import build_gold
from loopeng.warehouse.connect import ensure_warehouse
from tests.fakes import FakeClient


@pytest.fixture(scope="module")
def warehouse(tmp_path_factory):
    return ensure_warehouse(tmp_path_factory.mktemp("wh") / "w.duckdb", seed=20260729)


@pytest.fixture(scope="module")
def items(warehouse):
    return build_gold(warehouse)


def ScriptedClient(replies):
    """The agent's client, in whichever vendor shape the registry says it needs.

    The vendor-shaped double lives in `tests/fakes.py`. This file used to carry its
    own Anthropic-shaped stub; eight modules did, all subtly different, which was
    survivable with one vendor and is not with two — a per-module stub is a
    per-module chance to fake the wrong SDK surface and prove nothing.
    """
    return FakeClient("agent", replies)


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
    """When two rules produce the same wrong answer, naming one would be a coin flip
    presented as a finding.

    The item is FOUND rather than named. It used to be pinned by id, and the id moved
    when the parameter space was widened — a test asserting a property of a specific
    row rather than of the taxonomy, which then failed for a reason that had nothing
    to do with the behaviour under test.
    """
    item = next(
        (i for i in items
         if any(len(group) > 1 for group in i.ambiguous_rule_groups)),
        None,
    )
    assert item is not None, "no item has colliding rule variants to attribute"

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
    state = run_trap(subset, warehouse, arms=(("agent", "L3"),), client=client)

    calls_after_run = client.calls
    assert calls_after_run == len(subset)

    state.reveal()
    assert state.revealed
    assert client.calls == calls_after_run, "reveal made a model call"


def test_judgements_exist_before_reveal(items, warehouse):
    """Scoring happens on arrival. The button reveals; it does not compute."""
    client = ScriptedClient(lambda q: "SELECT COUNT(*) FROM products")
    state = run_trap(items[:2], warehouse, arms=(("agent", "L3"),), client=client)
    assert not state.revealed
    assert all(cell.judgement is not None for cell in state.cells.values())


def test_silent_error_rate_is_none_before_anything_lands():
    """A rate with no observations is not a rate. Rendering it as 0% would be a
    claim, and "not yet measured" is the truth."""
    assert TrapState().silent_error_rate("agent") is None


def test_silent_error_rate_carries_its_n(items, warehouse):
    item = _item(items, "p04_gross_revenue")
    client = ScriptedClient(lambda q: item.naive_sql)
    state = run_trap([item], warehouse, arms=(("agent", "L3"),), client=client)
    metric = state.silent_error_rate("agent@L3")
    assert metric.n == 1
    assert metric.value == 1.0
    # The property, not the spelling. A boundary observation renders as "1 of 1 — at
    # least ...", because "100.0% ±X" reads as a point estimate with noise when what
    # was observed is every trial going one way.
    assert str(metric.n) in metric.render()
    assert "at least" in metric.render()


def test_trap_runs_every_item_against_every_arm(items, warehouse):
    """The arms are the same model at two spec levels, so the SPEC is the variable."""
    client = ScriptedClient(lambda q: "SELECT COUNT(*) FROM products")
    subset = items[:4]
    state = run_trap(subset, warehouse, client=client)
    assert len(state.cells) == len(subset) * 2
    assert client.calls == len(subset) * 2
    assert {cell.arm for cell in state.cells.values()} == {"agent@L3", "agent@L0"}


def test_the_default_arms_hold_the_model_constant(items, warehouse):
    """Haiku-vs-Sonnet would teach "buy the bigger model", the opposite of the
    thesis. Same model at two spec levels makes the spec the variable."""
    from loopeng.agent.trap import ARMS

    assert {role for role, _ in ARMS} == {"agent"}
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
    run_trap(items[:4], warehouse, arms=(("agent", "L3"),), client=client,
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
        question="q", level="L3", role="agent", model_id="m",
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


# ---- signalled missing information ------------------------------------------
#
# Measured 2026-09-07 on the eight currency-bearing items at L0, where the conversion
# factors are withheld and no correct answer is computable from the prompt. The two
# models did opposite things, 8/8 each: gpt-5.6-luna invented a rate and returned a
# clean wrong number; gpt-6-astra named the input it was missing. The classifier scored
# the confabulation as a silent error and the signal as a crash — our own instrument
# ranking the honest behaviour below the dishonest one, on the exact axis this project
# is about.


def test_naming_a_missing_input_is_not_an_execution_failure(items, warehouse):
    """The SQL below is gpt-6-astra's, shortened. It cannot run, and that is the
    model saying so rather than the model failing."""
    from loopeng.agent.classify import Outcome

    item = _item(items, "p04_gross_revenue")
    sql = (
        "SELECT SUM(CASE o.currency WHEN 'EUR' THEN o.amount_minor / 100.0 "
        "* $eur_to_usd WHEN 'JPY' THEN o.amount_minor * $jpy_to_usd END) "
        "FROM orders o"
    )
    run = run_question(item.question, warehouse=warehouse, max_attempts=1,
                       client=ScriptedClient(lambda q: sql))
    verdict = judge(run, item)

    assert verdict.outcome is Outcome.SIGNALLED_MISSING_INFO
    assert verdict.abstained
    assert not verdict.ran_and_returned, "nothing was answered"


def test_inventing_a_rate_is_still_a_silent_error(items, warehouse):
    """The other half of the pair, and the half that must NOT move. A plausible
    number computed from a guessed constant is the failure this project is about."""
    from loopeng.agent.classify import Outcome

    item = _item(items, "p04_gross_revenue")
    sql = (
        "SELECT SUM(CASE o.currency WHEN 'EUR' THEN o.amount_minor * 0.0108 "
        "WHEN 'JPY' THEN o.amount_minor * 0.0067 ELSE 0 END) FROM orders o"
    )
    run = run_question(item.question, warehouse=warehouse, max_attempts=1,
                       client=ScriptedClient(lambda q: sql))
    assert judge(run, item).outcome is Outcome.SILENT_ERROR


def test_a_placeholder_inside_a_string_literal_is_not_an_abstention(items, warehouse):
    """The reason this reads the parse tree rather than the text. A regex for a
    dollar-name matches inside a quoted string, and would score a plain broken query
    as a principled refusal."""
    from loopeng.agent.classify import Outcome

    item = _item(items, "p01_product_count")
    run = run_question(item.question, warehouse=warehouse, max_attempts=1,
                       client=ScriptedClient(
                           lambda q: "SELECT '$eur_to_usd' FROM no_such_table"))
    verdict = judge(run, item)

    assert verdict.outcome is Outcome.VISIBLE_FAILURE
    assert not verdict.abstained


def test_an_ordinary_broken_query_is_still_an_execution_error(items, warehouse):
    from loopeng.agent.classify import Outcome, VisibleKind

    item = _item(items, "p01_product_count")
    run = run_question(item.question, warehouse=warehouse, max_attempts=1,
                       client=ScriptedClient(lambda q: "SELECT * FROM no_such_table"))
    verdict = judge(run, item)

    assert verdict.outcome is Outcome.VISIBLE_FAILURE
    assert verdict.visible_kind is VisibleKind.EXECUTION_ERROR


def test_abstentions_are_counted_apart_from_correct_and_failed(items, warehouse):
    """Three bands, not two. Folding an abstention into either one would restate the
    ranking the category exists to correct."""
    from loopeng.agent.classify import summarise

    item = _item(items, "p04_gross_revenue")
    signalled = judge(
        run_question(item.question, warehouse=warehouse, max_attempts=1,
                     client=ScriptedClient(
                         lambda q: "SELECT SUM(o.amount_minor * $rate) FROM orders o")),
        item,
    )
    report = summarise([signalled])

    assert report["n_signalled_missing_information"] == 1
    assert report["n_ran_and_returned"] == 0
    assert report["n_visible_failures"] == 0
    assert report["n_silent_errors"] == 0


# ---- a right answer is not always an earned one -----------------------------
#
# Measured 2026-09-07: gpt-5.6-luna's invented conversion rates spanned 0.0064 to
# 0.0068 across the eight L0 currency items, bracketing the warehouse's declared JPY
# factor. Some landed. A guess that lands is indistinguishable from knowledge to any
# accuracy metric, which is the same ranking inversion this module already had once —
# one level deeper.


def test_matching_gold_without_the_withheld_value_is_not_scored_as_correct(
    items, warehouse
):
    """The factor exists only in the rules. At L0 the rules are withheld and there is
    no rates table, so a correct USD total requires a number the model was never
    shown."""
    from loopeng.agent.classify import Outcome

    item = _item(items, "p04_gross_revenue")
    run = run_question(item.question, warehouse=warehouse, level="L0", max_attempts=1,
                       client=ScriptedClient(lambda q: item.gold_sql))
    verdict = judge(run, item)

    assert verdict.outcome is Outcome.UNEARNED_CORRECT
    assert verdict.unearned
    assert verdict.ran_and_returned, "it ran and it returned; that is the problem"


def test_the_same_answer_at_l3_is_earned(items, warehouse):
    """The other half. With the rules supplied the factor was given, so matching gold
    is knowledge and must score as such — otherwise the trap has no treatment arm."""
    from loopeng.agent.classify import Outcome

    item = _item(items, "p04_gross_revenue")
    run = run_question(item.question, warehouse=warehouse, level="L3", max_attempts=1,
                       client=ScriptedClient(lambda q: item.gold_sql))
    assert judge(run, item).outcome is Outcome.CORRECT


def test_a_rule_free_item_is_earned_even_at_l0(items, warehouse):
    """Deliberately narrow. `p01_product_count` needs no rules at all, so a correct
    answer at L0 is an answer, not a guess."""
    from loopeng.agent.classify import Outcome

    item = _item(items, "p01_product_count")
    run = run_question(item.question, warehouse=warehouse, level="L0", max_attempts=1,
                       client=ScriptedClient(lambda q: item.gold_sql))
    assert judge(run, item).outcome is Outcome.CORRECT


def test_an_inferable_rule_still_earns_its_answer(items, warehouse):
    """A model that writes `deleted_at IS NULL` at L0 plausibly reasoned it from a
    column called `deleted_at`. Inference from the schema earns the answer; only an
    arbitrary constant conjured from nothing does not."""
    from loopeng.agent.classify import Outcome

    item = _item(items, "p02_orders_in_month")
    assert "soft_delete" in item.rules
    run = run_question(item.question, warehouse=warehouse, level="L0", max_attempts=1,
                       client=ScriptedClient(lambda q: item.gold_sql))
    assert judge(run, item).outcome is Outcome.CORRECT


def test_an_unearned_correct_is_not_swept_into_the_silent_error_band(items, warehouse):
    """`silent = ran - correct` counted it as a wrong answer the moment the outcome
    existed. The number was right; calling it a silent error is false in the other
    direction."""
    from loopeng.agent.classify import summarise

    item = _item(items, "p04_gross_revenue")
    verdict = judge(
        run_question(item.question, warehouse=warehouse, level="L0", max_attempts=1,
                     client=ScriptedClient(lambda q: item.gold_sql)),
        item,
    )
    report = summarise([verdict])

    assert report["n_unearned_correct"] == 1
    assert report["n_correct"] == 0
    assert report["n_silent_errors"] == 0
    assert report["n_ran_and_returned"] == 1


# ---- the bands are enumerated, and a new outcome must not join one silently ---
#
# `silent = len(ran) - correct` is a band derived by subtracting the bands somebody
# remembered from the total. It is right exactly while the enumeration in the
# author's head matches the enum, and it fails SILENTLY when a category is added:
# the new outcome lands in whichever band was being derived. That happened twice, in
# two modules, and both times the derived band was `silent_errors` — so a right
# answer was counted as a wrong one on the headline metric with every test green.


def test_every_outcome_has_a_band():
    """THE guard. Adding an `Outcome` member without giving it a band fails here,
    which turns a default somebody inherits into a decision somebody makes."""
    from loopeng.agent.classify import OUTCOME_BANDS, Outcome

    assert set(OUTCOME_BANDS) == set(Outcome), (
        "these outcomes have no band: "
        f"{sorted(str(o) for o in set(Outcome) - set(OUTCOME_BANDS))}"
    )


def test_every_band_is_reachable():
    """The other direction. A band no outcome maps to is a column that renders empty
    forever and reads as a measured zero."""
    from loopeng.agent.classify import BANDS, OUTCOME_BANDS

    assert set(OUTCOME_BANDS.values()) == set(BANDS)


def test_an_unknown_outcome_raises_rather_than_defaulting():
    """A default band is exactly how a new category silently joins an existing one."""
    from loopeng.agent.classify import UnbandedOutcome, band_of

    with pytest.raises(UnbandedOutcome):
        band_of("something_nobody_declared")


def test_the_bands_partition_every_judgement():
    """Counts must sum to the total. If they do not, something was double-counted or
    dropped, and both are invisible in a stacked bar."""
    from loopeng.agent.classify import Outcome, band_counts

    outcomes = list(Outcome) * 3
    counts = band_counts(outcomes)
    assert sum(counts.values()) == len(outcomes)


def test_no_module_derives_an_outcome_band_by_subtraction():
    """The shape, banned where it bites.

    Grep-based and deliberately narrow: it looks for a subtraction assigned to a
    band-shaped name, in the modules that summarise outcomes. A general ban on
    subtraction would be unenforceable and would be switched off within a week.
    """
    import pathlib
    import re

    root = pathlib.Path(__file__).resolve().parent.parent / "src" / "loopeng"
    banned = re.compile(
        r"^\s*(silent|correct|unearned|visible|abstained|wrong)\w*\s*=\s*[^=\n]*\s-\s",
        re.MULTILINE,
    )
    offenders = []
    for path in root.rglob("*.py"):
        for match in banned.finditer(path.read_text(encoding="utf-8")):
            line = match.group(0).strip()
            offenders.append(f"{path.relative_to(root)}: {line}")
    assert not offenders, (
        "an outcome band derived by subtraction — count it by enumeration instead, "
        f"through classify.band_counts: {offenders}"
    )


def test_the_grep_would_catch_the_bug_it_was_written_for():
    """A checker that silently matches nothing makes the test above vacuous and
    green, which is the failure mode this whole repository is about."""
    import re

    banned = re.compile(
        r"^\s*(silent|correct|unearned|visible|abstained|wrong)\w*\s*=\s*[^=\n]*\s-\s",
        re.MULTILINE,
    )
    assert banned.search("    silent = len(ran) - correct\n")
    assert banned.search("    silent = len(ran) - correct - unearned\n")
    assert not banned.search("    silent = bands[BAND_SILENT]\n")


def test_the_cell_report_carries_every_band(items, warehouse):
    """So a renderer never has to work one out for itself."""
    from loopeng.agent.classify import BANDS
    from loopeng.sweep.runner import Cell, summarise_cell

    row = {
        "item_id": "a", "pattern_key": "p", "outcome": "silent_error",
        "ran_and_returned": True, "correct": False, "unearned_correct": False,
        "termination": "success", "n_attempts": 1, "rejections": 0,
        "cost_usd": 0.01, "tokens": {"n_calls": 1},
    }
    report = summarise_cell(Cell("agent", "L0", "loop"), [row], complete=True,
                            seconds=1.0)

    assert set(report["bands"]) == set(BANDS)
    assert report["bands"]["wrong_and_silent"] == 1
    assert sum(report["bands"].values()) == 1


# ---- _could_not_have_known stays narrow -------------------------------------


def test_the_unearned_check_never_fires_for_an_inferable_rule(items):
    """A broader version starts excusing genuine failures.

    `deleted_at`, `status` and `is_internal` are column names in the DDL. A model
    that filters on them at L0 has reasoned from the schema, and that earns the
    answer. Only a value that appears NOWHERE — the conversion factors — does not.
    """
    from loopeng.agent.classify import _could_not_have_known
    from loopeng.gold.patterns import RULES_REQUIRING_UNDISCLOSED_VALUES

    inferable = {"soft_delete", "cancelled_orders", "internal_accounts",
                 "refunds_net", "fan_out"}
    assert not inferable & RULES_REQUIRING_UNDISCLOSED_VALUES

    for item in items:
        if not set(item.rules) & RULES_REQUIRING_UNDISCLOSED_VALUES:
            assert not _could_not_have_known(item, "L0"), (
                f"{item.pattern_key} requires only inferable rules; a correct answer "
                f"at L0 is an answer, not a guess"
            )


def test_the_unearned_check_never_fires_when_the_rules_were_supplied(items):
    """At L3 the factor was given, so matching gold is knowledge. If this fired the
    trap would have no treatment arm."""
    from loopeng.agent.classify import _could_not_have_known

    for item in items:
        assert not _could_not_have_known(item, "L3")


# ---- the taxonomy, pinned the way TerminationReason is -----------------------


def test_every_visible_kind_is_reachable():
    """A category nothing can produce is decoration, and this enum had no pin.

    `TerminationReason` has carried one since the `declined` gap: a new reason has to
    arrive with the test that fires it, rather than joining the enum and never being
    observed. `VisibleKind` — the taxonomy the whole triage path sorts by — had no
    equivalent, and `no_attempts` was in it with no test producing it.

    Each is reached by the test named:

      execution_error   test_a_query_that_fails_to_execute_is_a_visible_failure
      timeout           test_a_timeout_is_its_own_kind
      empty_result      test_an_empty_result_is_visible_not_silent
      no_attempts       test_a_run_with_no_attempts_is_a_visible_failure
      shape_mismatch    test_extra_columns_are_a_shape_mismatch
      null_result       test_all_null_rows_are_their_own_kind
      model_call_failed test_a_failed_model_call_is_not_an_execution_error
    """
    assert {kind.value for kind in VisibleKind} == {
        "execution_error", "timeout", "empty_result", "no_attempts",
        "shape_mismatch", "null_result", "model_call_failed",
    }


def test_a_run_with_no_attempts_is_a_visible_failure(warehouse):
    """The one kind the suite never produced. A run that made no attempt at all is a
    failure you can see without knowing the answer — there is nothing to look at."""
    from loopeng.agent.loop import AgentRun, TerminationReason
    from loopeng.gold.build import build_gold
    from loopeng.usage import UsageLedger

    item = build_gold(warehouse)[0]
    run = AgentRun(
        question=item.question, level="L3", role="agent", model_id="m",
        attempts=(), termination=TerminationReason.MAX_ATTEMPTS,
        item_id=item.item_id, ledger=UsageLedger(),
    )
    verdict = judge(run, item)
    assert verdict.outcome is Outcome.VISIBLE_FAILURE
    assert verdict.visible_kind is VisibleKind.NO_ATTEMPTS


def test_the_sweep_records_which_kind_of_visible_failure(tmp_path, warehouse):
    """`judge` has always computed this and `run_cell` has always dropped it, so the
    most expensive measurement path in the project wrote cells that could be counted
    by outcome and not classified by cause — while `triage/failures.py` exists to sort
    failures by cause and both cheaper paths kept the field."""
    import inspect

    from loopeng.sweep import runner

    source = inspect.getsource(runner.run_cell)
    assert '"visible_kind"' in source, (
        "run_cell no longer records the failure kind; the sweep is the path that "
        "cannot be triaged without it"
    )


def test_visible_kind_counts_enumerate_every_kind_including_the_zeros():
    """A dict built only from the kinds present reads as "these are the failures there
    are", and a reader cannot tell a kind that fired zero times from one the runner
    never records — which was true of all seven, because the sweep did not store it."""
    from loopeng.sweep.runner import visible_kind_counts

    counts = visible_kind_counts([{"outcome": "correct"}])
    assert set(counts) == {kind.value for kind in VisibleKind} | {"unclassified"}
    assert all(value == 0 for value in counts.values())


def test_a_visible_failure_with_no_recorded_kind_is_counted_not_dropped():
    """Silently omitting it would shrink the total below the band count and make the
    two disagree — a cell whose own numbers contradict each other."""
    from loopeng.sweep.runner import visible_kind_counts

    counts = visible_kind_counts([
        {"outcome": "visible_failure", "visible_kind": "shape_mismatch"},
        {"outcome": "visible_failure"},          # a row written before the field existed
        {"outcome": "visible_failure", "visible_kind": "not_a_kind"},
    ])
    assert counts["shape_mismatch"] == 1
    assert counts["unclassified"] == 2
    assert sum(counts.values()) == 3, "every visible failure is accounted for"
