"""V2: the config is the source of truth, and gaps fail the build."""

import pytest

from loopeng.verify.governance import (
    PROBES,
    UnenforcedRule,
    UnprobedRule,
    assert_full_coverage,
    coverage_report,
    declared_rules,
    run_governance_probes,
    verify_governed,
)
from loopeng.verify.verifiers import RULE_CHECKS


def test_every_declared_rule_is_enforced():
    """The defect this project is about, applied to our own governance layer: a rule
    the semantic model declares and nothing checks. It is a build failure, not a
    report line — and it fired on its first run, catching minor_units."""
    report = coverage_report()
    assert report["unenforced"] == [], report["unenforced"]


def test_every_declared_rule_is_probed():
    assert coverage_report()["unprobed"] == []


def test_no_probe_exists_for_a_rule_the_config_does_not_declare():
    """A probe for a rule nobody declared is dead weight that inflates the surface."""
    assert coverage_report()["probed_but_undeclared"] == []


def test_coverage_is_seven_rules():
    assert len(declared_rules()) == 7
    assert len(PROBES) == 7


def test_an_unenforced_rule_raises_rather_than_degrading_quietly(monkeypatch):
    """The gate must bite. Remove a check and construction fails."""
    import loopeng.verify.governance as governance

    monkeypatch.setattr(
        governance, "RULE_CHECKS", {k: v for k, v in RULE_CHECKS.items() if k != "fan_out"}
    )
    with pytest.raises(UnenforcedRule) as exc:
        governance.assert_full_coverage()
    assert "fan_out" in str(exc.value)


def test_an_unprobed_rule_raises_too(monkeypatch):
    import loopeng.verify.governance as governance

    monkeypatch.setattr(
        governance, "PROBES", {k: v for k, v in PROBES.items() if k != "refunds_net"}
    )
    with pytest.raises(UnprobedRule) as exc:
        governance.assert_full_coverage()
    assert "refunds_net" in str(exc.value)


def test_the_gate_passes_as_shipped():
    assert_full_coverage()


# ---- both probe directions --------------------------------------------------


@pytest.mark.parametrize("rule", sorted(PROBES), ids=str)
def test_the_violation_probe_is_rejected(rule):
    report = run_governance_probes()
    assert report["by_rule"][rule]["caught_the_violation"], PROBES[rule].violation


@pytest.mark.parametrize("rule", sorted(PROBES), ids=str)
def test_the_nearby_legitimate_probe_is_accepted(rule):
    """The half that is easy to skip and does the most work. A verifier that rejects
    everything is perfect at catching violations; only this direction says whether it
    understands the rule or merely pattern-matches it."""
    report = run_governance_probes()
    entry = report["by_rule"][rule]
    assert entry["accepted_the_nearby_legitimate"], (
        f"{rule}: rejected a correct query that {entry['why_nearby']}"
    )


def test_v2_is_sound_across_the_whole_declared_surface():
    report = run_governance_probes()
    assert report["n_sound"] == report["n_rules"] == 7
    assert report["n_missed_violations"] == 0
    assert report["n_false_rejections"] == 0


def test_v2_only_checks_rules_the_item_actually_requires():
    from loopeng.contracts import VerifyContext

    context = VerifyContext(
        question="q", sql="SELECT COUNT(*) FROM products", schema_ddl="",
        rules=(), attempt=1, execution_rows=None, execution_error=None,
    )
    assert verify_governed(context).ok
