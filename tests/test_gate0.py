import json
from pathlib import Path

import pytest

from loopeng.gate0 import REFUNDS_NET_CAVEAT, TEMPLATING_DISCLOSURE, rule_coverage
from loopeng.gold.build import build_gold
from loopeng.probes import CACHE_MINIMUM_TOKENS, cacheability_findings
from loopeng.warehouse.connect import ensure_warehouse

REPORT = Path("results/gate0.json")


@pytest.fixture(scope="module")
def items(tmp_path_factory):
    warehouse = ensure_warehouse(tmp_path_factory.mktemp("wh") / "w.duckdb", seed=20260729)
    return build_gold(warehouse)


# ---- rule coverage and the single-cluster caveat ----------------------------


def test_refunds_net_is_carried_by_a_single_cluster(items):
    """The fact the caveat exists to state. If a later change spreads refunds_net
    across more patterns, this fails and the caveat should be revisited."""
    coverage = rule_coverage(items)
    assert coverage["clusters_per_rule"]["refunds_net"] == 1
    assert coverage["rules_carried_by_a_single_cluster"] == ["refunds_net"]


def test_the_caveat_says_what_a_flat_line_means(items):
    """A single-cluster rule cannot be measured by the sweep, and the report has to
    say so, or a flat ablation line reads as a verifier failure that never happened."""
    caveat = rule_coverage(items)["caveat"]
    assert "refunds_net" in caveat
    assert "one pattern" in caveat.lower()
    assert "not measured here" in caveat.lower()
    assert "rule-surface probes" in caveat.lower()


def test_every_other_rule_spans_several_clusters(items):
    coverage = rule_coverage(items)
    for rule, clusters in coverage["clusters_per_rule"].items():
        if rule == "refunds_net":
            continue
        assert clusters >= 2, f"{rule} is also single-cluster and needs the same caveat"


def test_coverage_lists_every_pattern(items):
    coverage = rule_coverage(items)
    assert len(coverage["by_pattern"]) == 10
    assert coverage["by_pattern"]["p01_product_count"]["rules"] == ["(none - the L0 floor)"]


# ---- cacheability findings --------------------------------------------------


def test_asymmetric_caching_is_flagged_explicitly():
    """A prompt between the two minimums caches on Sonnet and silently does not on
    Haiku. Silent is the problem: no error, just a different cost per cell."""
    probe = {
        "frontier": {"L0": {"cacheable": False}, "L3": {"cacheable": True}},
        "worker": {"L0": {"cacheable": False}, "L3": {"cacheable": False}},
    }
    findings = " ".join(cacheability_findings(probe))
    assert "L3 caches on frontier but NOT on worker" in findings
    assert "silent" in findings.lower()
    assert "cost comparison" in findings.lower()


def test_uniform_cacheability_is_reported_without_a_warning():
    probe = {
        "frontier": {"L0": {"cacheable": True}, "L3": {"cacheable": True}},
        "worker": {"L0": {"cacheable": True}, "L3": {"cacheable": True}},
    }
    findings = " ".join(cacheability_findings(probe))
    assert "NOT" not in findings


def test_cache_minimums_are_per_model():
    """Haiku's minimum is four times Sonnet's; treating them as one number is what
    produces the silent asymmetry."""
    assert CACHE_MINIMUM_TOKENS["claude-haiku-4-5"] == 4096
    assert CACHE_MINIMUM_TOKENS["claude-sonnet-5"] == 1024


# ---- the written report -----------------------------------------------------


@pytest.mark.skipif(not REPORT.exists(), reason="gate0.json is produced by the live run")
def test_the_report_carries_every_required_section():
    report = json.loads(REPORT.read_text())
    for section in ("warehouse", "query_latency", "gold_set", "langsmith", "prompts",
                    "rate_limits", "spend"):
        assert section in report, f"gate0.json is missing {section}"


@pytest.mark.skipif(not REPORT.exists(), reason="gate0.json is produced by the live run")
def test_dollars_are_labelled_estimated_in_the_report():
    """Tokens are measured; dollars are those tokens times a table typed in by hand.
    Nobody upgrades that label."""
    report = json.loads(REPORT.read_text())
    assert report["spend"]["cost_usd"]["source"] == "estimated"
    assert "billing export" in report["spend"]["cost_usd"]["how"]


@pytest.mark.skipif(not REPORT.exists(), reason="gate0.json is produced by the live run")
def test_the_report_states_langsmith_is_advisory():
    report = json.loads(REPORT.read_text())
    assert "ADVISORY ONLY" in report["langsmith"]["role"]
    assert "system of record" in report["langsmith"]["role"]


@pytest.mark.skipif(not REPORT.exists(), reason="gate0.json is produced by the live run")
def test_the_report_carries_the_disclosures():
    report = json.loads(REPORT.read_text())
    assert report["gold_set"]["templating_disclosure"] == TEMPLATING_DISCLOSURE
    assert report["gold_set"]["rule_coverage"]["caveat"] == REFUNDS_NET_CAVEAT


@pytest.mark.skipif(not REPORT.exists(), reason="gate0.json is produced by the live run")
def test_every_reported_value_says_how_it_was_obtained():
    """A number whose provenance is not written down becomes a number someone quotes
    later without the caveat."""
    report = json.loads(REPORT.read_text())
    for key, entry in report["warehouse"].items():
        assert entry.get("how"), f"warehouse.{key} does not say how it was obtained"


@pytest.mark.skipif(not REPORT.exists(), reason="gate0.json is produced by the live run")
def test_byte_identity_is_recorded_as_false_not_omitted():
    report = json.loads(REPORT.read_text())
    entry = report["warehouse"]["byte_identical_across_runs"]
    assert entry["value"] is False
    assert "content-identity" in entry["note"]
