"""The SQL guidance check: a rule's guidance must run over the real schema (zero tokens).

The three versions of the 23 October session (v4, v5, v6, saved in promoted_rules/) each stated the
internal-accounts convention with guidance that does not run: v5 a placeholder, v4 and v6 a column
that does not exist. The finale under v5 answered the spine question without the email-domain
filter. Each of those rules must be caught; the predicate the reference SQL uses must pass.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from loop4_doubles import warehouse_snapshot

from datapilot.contracts import KnowledgeVersion, ProposedRule
from datapilot.loop4_hill_climbing.overfit_guard import OverfitGuard
from datapilot.loop4_hill_climbing.pack_files import load_benchmark
from datapilot.loop4_hill_climbing.sql_guidance import GuidanceCheck

CHECK = GuidanceCheck(warehouse_snapshot())
SAVED = Path(__file__).parent / "promoted_rules"
INTERNAL_ACCOUNT_RULES = {
    "v4": "eligible-external-orders",
    "v5": "eligible-business-orders",
    "v6": "sales-order-population-exclusions",
}
EMAIL_DOMAIN = "lower(c.email) NOT LIKE '%@harborpine.com'"


def saved(version: str) -> KnowledgeVersion:
    return KnowledgeVersion.model_validate(
        yaml.safe_load((SAVED / f"{version}-knowledge.yaml").read_text(encoding="utf-8"))
    )


def as_proposed(rule_id: str, guidance: str) -> ProposedRule:
    return ProposedRule(
        id=rule_id,
        title="Exclude internal accounts and status-5 orders",
        rule_text="Business metrics leave out orders of internal accounts and orders in status 5.",
        applies_when="a metric is based on orders",
        sql_guidance=guidance,
        evidence_example_ids=["net-revenue-fiscal-2025"],
        expected_effect="order metrics leave out internal test orders",
    )


def test_the_snapshot_read_from_the_schema_file_has_the_warehouse_tables() -> None:
    schema = CHECK.schema()
    assert {"orders", "customers", "order_items", "products", "categories"} <= set(schema)
    assert "email" in schema["customers"] and "order_ts" in schema["orders"]
    assert "is_internal" not in schema["customers"], "internal accounts have no column of their own"


@pytest.mark.parametrize("version", sorted(INTERNAL_ACCOUNT_RULES))
def test_each_saved_internal_accounts_rule_is_caught(version: str) -> None:
    rule = next(r for r in saved(version).rules if r.id == INTERNAL_ACCOUNT_RULES[version])
    result = CHECK.check(as_proposed(rule.id, rule.sql_guidance))
    assert not result.passed, f"{version}: {rule.sql_guidance!r} must not pass"


def test_the_placeholder_and_the_invented_column_are_named() -> None:
    v5 = CHECK.problems("status <> 5 AND <documented non-internal-customer predicate>")
    assert v5 == [
        "SQL guidance has a placeholder, not SQL: <documented non-internal-customer predicate>"
    ]
    v4 = CHECK.problems("customer_is_internal = false AND status <> 5")
    assert v4 == ["SQL guidance names a column that does not exist: customer_is_internal"]
    v6 = CHECK.problems("customer_is_internal = false AND order_status <> 5")
    assert len(v6) == 2 and "order_status" in v6[1]


@pytest.mark.parametrize(
    "guidance",
    [
        EMAIL_DOMAIN,
        f"o.status <> 5 AND {EMAIL_DOMAIN}",
        "round(sum(o.subtotal_cents - o.discount_cents) / 100.0, 2)",
        "(o.order_ts AT TIME ZONE 'America/New_York')::date",
        "WHERE o.discount_cents = 0",
        "JOIN warehouse.customers c ON c.customer_id = o.customer_id",
        "SELECT c.category_id, p.parent_id FROM warehouse.categories c "
        "JOIN warehouse.categories p ON p.category_id = c.parent_id",
        "",
    ],
)
def test_guidance_that_runs_over_the_schema_passes(guidance: str) -> None:
    assert CHECK.problems(guidance) == []


def test_the_email_domain_rule_passes_the_guidance_check_and_the_overfit_guard() -> None:
    rule = as_proposed("internal-accounts", f"o.status <> 5 AND {EMAIL_DOMAIN}")
    assert CHECK.check(rule).passed
    assert OverfitGuard.from_pack(load_benchmark()).check(rule).passed


@pytest.mark.parametrize(
    "guidance",
    [
        "round(sum(<cents column>) / 100.0, 2)",
        "convert timestamp to America/New_York before date extraction or filtering",
        "join through the assigned category's parent",
        "status code",
        "c.is_internal = false",
        "SELECT count(*) FROM warehouse.returns",
        "SELECT count(*) FROM marketing.orders",
        "o.ordered_at >= DATE '2024-02-01'",
    ],
)
def test_guidance_that_does_not_run_is_caught(guidance: str) -> None:
    assert CHECK.problems(guidance)


def test_every_saved_rule_is_judged_and_the_saved_versions_have_few_that_run() -> None:
    """Most guidance the analyzer team wrote on 23 October was prose; the check names each one."""
    for version in INTERNAL_ACCOUNT_RULES:
        rules = saved(version).rules
        failing = CHECK.check_all([as_proposed(r.id, r.sql_guidance) for r in rules])
        assert INTERNAL_ACCOUNT_RULES[version] in failing
        assert all(problems for problems in failing.values())
