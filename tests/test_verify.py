import inspect
from types import SimpleNamespace

import pytest

from loopeng.agent.loop import TerminationReason
from loopeng.contracts import FORBIDDEN_FIELD_PATTERN
from loopeng.verify.loop import build_context, run_verified
from loopeng.verify.probes import PROBES, run_probes
from loopeng.verify.regex_verifiers import verify_with_regex
from loopeng.verify.verifiers import verify
from loopeng.warehouse.connect import ensure_warehouse


@pytest.fixture(scope="module")
def warehouse(tmp_path_factory):
    return ensure_warehouse(tmp_path_factory.mktemp("wh") / "w.duckdb", seed=20260729)


class ScriptedClient:
    def __init__(self, replies):
        self._replies = list(replies)
        self.calls = 0
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.calls += 1
        text = self._replies[min(self.calls - 1, len(self._replies) - 1)]
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text=text)],
            usage=SimpleNamespace(input_tokens=100, output_tokens=50),
        )


# ---- THE architectural contract, discharged structurally ---------------------


def test_build_context_has_no_gold_parameter():
    """The Gate 0 obligation, in code. The field-name regex constrains the type's
    shape; only scope constrains what can reach it. So the constructing function
    takes no gold argument — there is nothing for a careless author to pass."""
    for name in inspect.signature(build_context).parameters:
        assert not FORBIDDEN_FIELD_PATTERN.search(name), f"build_context exposes {name}"


def test_build_context_cannot_be_handed_a_gold_item():
    """No parameter is typed to accept one, so gold cannot arrive under a different
    name either. Checked on annotations rather than on the source text — the
    docstring legitimately discusses gold, and grepping prose for the word would
    fail on an explanation of why the guarantee holds."""
    for name, param in inspect.signature(build_context).parameters.items():
        assert "GoldItem" not in str(param.annotation), f"build_context accepts gold as {name}"
    assert "GoldItem" not in inspect.getsource(build_context)


def test_the_verified_loop_never_loads_gold():
    """Stronger than the signature check: the whole call stack that builds a context
    must not reach the gold set."""
    source = inspect.getsource(run_verified)
    assert "build_gold" not in source
    assert "gold_rows" not in source


def test_a_verify_context_still_exposes_no_answer_field():
    from dataclasses import fields

    from loopeng.contracts import VerifyContext

    for field in fields(VerifyContext):
        assert not FORBIDDEN_FIELD_PATTERN.search(field.name)


# ---- the AST verifier catches what it claims to ------------------------------


@pytest.mark.parametrize("probe", PROBES, ids=lambda p: p.rule)
def test_the_ast_verifier_rejects_a_query_that_breaks_the_rule(probe):
    from loopeng.verify.probes import _context

    assert not verify(_context(probe.breaks, probe.rule)).ok, probe.note


@pytest.mark.parametrize("probe", PROBES, ids=lambda p: p.rule)
def test_the_ast_verifier_accepts_a_query_that_honours_the_rule(probe):
    """A verifier that rejects everything scores perfectly on the other test."""
    from loopeng.verify.probes import _context

    assert verify(_context(probe.honours, probe.rule)).ok, probe.note


def test_the_v1_probe_surface_covers_every_check_it_claims_to():
    """V1's probes cover its own checks. multi_currency and minor_units share one
    check, so V1 has one probe for the pair; V2's config-driven surface is what
    requires a probe per DECLARED rule."""
    from loopeng.verify.verifiers import RULE_CHECKS

    probed = {p.rule for p in PROBES}
    assert probed <= set(RULE_CHECKS)
    assert set(RULE_CHECKS) - probed == {"minor_units"}


def test_refunds_net_is_probed_even_though_the_sweep_cannot_measure_it():
    """Gate 0 recorded refunds_net as single-cluster, so the sweep can make no claim
    about it. The probe is what covers it, and it is direct evidence rather than an
    inference from sweep outcomes."""
    report = run_probes()
    assert report["by_rule"]["refunds_net"]["sound"]


def test_the_ast_verifier_is_sound_across_the_whole_surface():
    report = run_probes()
    assert report["n_missed_violations"] == 0
    assert report["n_false_rejections"] == 0
    assert report["n_sound"] == report["n_rules"]


def test_verifier_feedback_does_not_depend_on_what_the_query_returned():
    """The property that matters, stated as a property rather than a word-search.

    The feedback goes straight back into the prompt, so anything derived from the
    result would be a channel for the answer to reach the model. Here the same SQL is
    verified twice with completely different execution rows attached; identical
    feedback proves the complaint is a function of the SQL and the rules alone.

    (The field-name regex is deliberately NOT used for this. It is built for
    identifiers, and against prose it fires on innocent English — "the refunds table
    is not referenced" contains "reference" and leaks nothing.)
    """
    from loopeng.contracts import VerifyContext

    def context_with(sql, rule, rows):
        return VerifyContext(
            question="(probe)", sql=sql, schema_ddl="", rules=(rule,),
            attempt=1, execution_rows=rows, execution_error=None,
        )

    for probe in PROBES:
        a = verify(context_with(probe.breaks, probe.rule, ((1,),))).feedback()
        b = verify(context_with(probe.breaks, probe.rule, ((999_999_999,), (42,)))).feedback()
        assert a == b, f"{probe.rule}: feedback changed with the result rows"


def test_verifier_feedback_never_contains_a_result_value():
    """A cheaper companion check: no number from the rows appears in the complaint."""
    from loopeng.contracts import VerifyContext

    marker = 8675309
    for probe in PROBES:
        feedback = verify(
            VerifyContext(
                question="(probe)", sql=probe.breaks, schema_ddl="", rules=(probe.rule,),
                attempt=1, execution_rows=((marker,),), execution_error=None,
            )
        ).feedback()
        assert str(marker) not in feedback, probe.rule


# ---- the regex verifier is worse, and worse in the way that matters ----------


def test_the_regex_verifier_misses_violations_the_ast_verifier_catches():
    """The whole point of the swap: the same rules, checked by text, accept queries
    that break them."""
    ast_report = run_probes(verify)
    regex_report = run_probes(verify_with_regex)
    assert regex_report["n_missed_violations"] > ast_report["n_missed_violations"]


def test_the_regex_verifier_is_fooled_by_a_comment():
    """The archetype. The words are present; the constraint is not."""
    from loopeng.verify.probes import _context

    sql = (
        "SELECT COUNT(*) FROM orders o JOIN customers c ON c.customer_id = o.customer_id "
        "-- deleted_at IS NULL is handled upstream\n"
        "WHERE o.status <> 'cancelled'"
    )
    assert verify_with_regex(_context(sql, "soft_delete")).ok, "regex should be fooled"
    assert not verify(_context(sql, "soft_delete")).ok, "AST should not be"


def test_the_regex_verifier_is_fooled_by_a_subquery_that_never_filters():
    from loopeng.verify.probes import _context

    sql = (
        "SELECT COUNT(*) FROM orders o WHERE o.order_id IN "
        "(SELECT order_id FROM refunds WHERE 1 = 1) "
        "AND EXISTS (SELECT 1 FROM customers c WHERE c.deleted_at IS NULL)"
    )
    assert verify_with_regex(_context(sql, "soft_delete")).ok


# ---- the loop itself ---------------------------------------------------------


def test_a_query_that_runs_but_breaks_a_rule_is_sent_back(warehouse):
    """The thing Level 1 structurally cannot do."""
    bad = "SELECT COUNT(*) FROM orders o JOIN customers c ON c.customer_id = o.customer_id"
    good = (
        "SELECT COUNT(*) FROM orders o JOIN customers c ON c.customer_id = o.customer_id "
        "WHERE o.deleted_at IS NULL AND c.deleted_at IS NULL"
    )
    client = ScriptedClient([bad, good])
    run = run_verified("q", warehouse=warehouse, rules=("soft_delete",), client=client)
    assert run.termination is TerminationReason.SUCCESS
    assert run.rejections == 1
    assert client.calls == 2


def test_the_rejected_attempt_actually_executed(warehouse):
    """It was not a crash. It ran, returned rows, and was still wrong — which is the
    distinction between Level 1 and Level 2."""
    bad = "SELECT COUNT(*) FROM orders o JOIN customers c ON c.customer_id = o.customer_id"
    client = ScriptedClient([bad])
    run = run_verified("q", warehouse=warehouse, rules=("soft_delete",), client=client,
                       max_attempts=1)
    first = run.attempts[0]
    assert first.attempt.executed
    assert first.attempt.rows
    assert not first.verdict.ok


def test_no_progress_fires_when_the_model_repeats_itself(warehouse):
    """Reachable for the first time here: at Level 1's cap of one attempt this branch
    could not fire at all, so Phase 1 was no evidence it works."""
    bad = "SELECT COUNT(*) FROM orders o JOIN customers c ON c.customer_id = o.customer_id"
    client = ScriptedClient([bad])
    run = run_verified("q", warehouse=warehouse, rules=("soft_delete",), client=client,
                       max_attempts=5)
    assert run.termination is TerminationReason.NO_PROGRESS


def test_budget_fires_before_the_attempt_cap(warehouse):
    bad = "SELECT COUNT(*) FROM orders o"
    client = ScriptedClient([bad, bad + " WHERE 1=1", bad + " WHERE 2=2"])
    run = run_verified("q", warehouse=warehouse, rules=("soft_delete",), client=client,
                       max_attempts=5, budget_usd=1e-9)
    assert run.termination is TerminationReason.BUDGET


def test_a_clean_query_passes_first_time(warehouse):
    good = (
        "SELECT COUNT(*) FROM orders o JOIN customers c ON c.customer_id = o.customer_id "
        "WHERE o.deleted_at IS NULL AND c.deleted_at IS NULL"
    )
    client = ScriptedClient([good])
    run = run_verified("q", warehouse=warehouse, rules=("soft_delete",), client=client)
    assert run.termination is TerminationReason.SUCCESS
    assert run.rejections == 0
    assert client.calls == 1


def test_every_call_is_still_metered(warehouse):
    bad = "SELECT COUNT(*) FROM orders o"
    client = ScriptedClient([bad])
    run = run_verified("q", warehouse=warehouse, rules=("soft_delete",), client=client,
                       max_attempts=3)
    assert len(run.ledger) == len(run.attempts)
    assert run.ledger.totals()["output_tokens"] == 50 * len(run.attempts)


# ---- the swap narration must fit whatever actually happened -----------------


def test_the_reading_does_not_claim_an_effect_that_did_not_appear():
    """A demo whose narration only fits the flattering result will narrate a result
    it did not get. Here the weaker verifier moved nothing, and the text says so."""
    from loopeng.verify.swap import SwapArm, _reading

    ast = SwapArm("ast", accepted=8, correct=5, ran=10, rejections=6)
    regex = SwapArm("regex", accepted=8, correct=5, ran=10, rejections=6)
    reading = _reading({"ast": ast, "regex": regex})
    assert "did not appear" in reading


def test_the_reading_distinguishes_quality_falling_from_quality_flat():
    from loopeng.verify.swap import SwapArm, _reading

    ast = SwapArm("ast", accepted=8, correct=5, ran=10, rejections=6)
    flat = SwapArm("regex", accepted=10, correct=5, ran=10, rejections=0)
    worse = SwapArm("regex", accepted=10, correct=1, ran=10, rejections=0)

    assert "identical" in _reading({"ast": ast, "regex": flat})
    assert "correctness fell" in _reading({"ast": ast, "regex": worse})


def test_the_reading_always_declares_the_correctness_comparison_underpowered():
    """At these n the interval is wide enough that 'quality held' and 'quality
    halved' are indistinguishable, and the arms can only differ on items the AST
    verifier actually rejected. Both facts must reach the room."""
    from loopeng.verify.swap import SwapArm, _reading

    ast = SwapArm("ast", accepted=8, correct=1, ran=10, rejections=6)
    regex = SwapArm("regex", accepted=10, correct=1, ran=10, rejections=0)
    reading = _reading({"ast": ast, "regex": regex})
    assert "UNDERPOWERED" in reading
    assert "AT MOST 6 of 10" in reading
    assert "bound is structural" in reading


def test_the_reading_refuses_to_argue_without_probe_evidence(monkeypatch):
    """If the probe surface does not show the regex verifier catching less, the
    scores are not evidence of anything."""
    import loopeng.verify.swap as swap_module
    from loopeng.verify.swap import SwapArm, _reading

    monkeypatch.setattr(swap_module, "run_probes",
                        lambda fn=None: {"n_missed_violations": 0, "n_sound": 6, "n_rules": 6})
    ast = SwapArm("ast", accepted=8, correct=5, ran=10, rejections=6)
    regex = SwapArm("regex", accepted=10, correct=1, ran=10, rejections=0)
    assert "does not show" in _reading({"ast": ast, "regex": regex})
