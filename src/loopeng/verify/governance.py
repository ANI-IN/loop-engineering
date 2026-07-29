"""V2: the governance verifier, driven by `semantic_model.yaml` rather than by hand.

V1 (`loopeng.verify.verifiers`) is a dict of Python checks. It works, and it has the
defect this whole workshop is about: **the rule set it enforces and the rule set the
config declares are two separate lists that nobody compares.** Add a rule to the YAML
and V1 silently does not enforce it. The prompt tells the model about it, the semantic
model documents it, and nothing checks it — declared, not enforced.

V2 closes that by making the config the source of truth and **failing the build**:

  - every rule declared in `semantic_model.yaml` must have an enforcement check
  - every rule must carry **two probes**: one query that violates it and must be
    rejected, and one that is *legitimate but nearby* and must be accepted
  - a rule missing either raises at construction time, not at review time

The nearby-legitimate probe is the half that is easy to skip and does the most work. A
verifier is trivially perfect at catching violations if it rejects everything, so each
rule is also given a correct query written in an unusual-but-valid shape — filtering in
a CTE, using COALESCE, aliasing differently. A check that pattern-matches rather than
understands rejects those, and the probe surface says so.
"""

from dataclasses import dataclass

from loopeng.contracts import VerifyContext
from loopeng.verify.verifiers import RULE_CHECKS, VerifyResult, Violation, _parse
from loopeng.warehouse.schema import load_semantic_model


class UnenforcedRule(RuntimeError):
    """A rule is declared in the semantic model and nothing enforces it.

    This is the exact defect the workshop is about, so it is a build failure here
    rather than a line in a report.
    """


class UnprobedRule(RuntimeError):
    """A rule is enforced but its enforcement is never tested against known inputs."""


@dataclass(frozen=True)
class RuleProbes:
    """Two queries per rule. Both directions, because one direction is free to fake."""

    violation: str
    nearby_legitimate: str
    why_nearby: str


_CLEAN = (
    "FROM orders o JOIN customers c ON c.customer_id = o.customer_id "
    "WHERE o.deleted_at IS NULL AND c.deleted_at IS NULL "
    "AND o.status <> 'cancelled' AND NOT c.is_internal"
)
_FX = "CASE o.currency WHEN 'USD' THEN 0.01 WHEN 'EUR' THEN 0.0108 WHEN 'JPY' THEN 0.0067 END"

PROBES: dict[str, RuleProbes] = {
    "soft_delete": RuleProbes(
        violation=(
            "SELECT COUNT(*) FROM orders o JOIN customers c "
            "ON c.customer_id = o.customer_id WHERE o.status <> 'cancelled'"
        ),
        nearby_legitimate=(
            "WITH live_orders AS (SELECT * FROM orders WHERE deleted_at IS NULL), "
            "live_customers AS (SELECT * FROM customers WHERE deleted_at IS NULL) "
            "SELECT COUNT(*) FROM live_orders o JOIN live_customers c "
            "ON c.customer_id = o.customer_id WHERE o.status <> 'cancelled' "
            "AND NOT c.is_internal"
        ),
        why_nearby="excludes deleted rows in CTEs, so the predicate is not in the outer WHERE",
    ),
    "cancelled_orders": RuleProbes(
        violation=(
            "SELECT COUNT(*) FROM orders o JOIN customers c "
            "ON c.customer_id = o.customer_id "
            "WHERE o.deleted_at IS NULL AND c.deleted_at IS NULL AND NOT c.is_internal"
        ),
        nearby_legitimate=(
            "SELECT COUNT(*) FROM orders o JOIN customers c "
            "ON c.customer_id = o.customer_id "
            "WHERE o.deleted_at IS NULL AND c.deleted_at IS NULL AND NOT c.is_internal "
            "AND o.status IN ('completed', 'pending')"
        ),
        why_nearby="excludes cancelled by whitelisting the other statuses, not by <>",
    ),
    "internal_accounts": RuleProbes(
        violation=(
            "SELECT COUNT(*) FROM orders o JOIN customers c "
            "ON c.customer_id = o.customer_id "
            "WHERE o.deleted_at IS NULL AND c.deleted_at IS NULL "
            "AND o.status <> 'cancelled'"
        ),
        nearby_legitimate=(
            "SELECT COUNT(*) FROM orders o JOIN customers c "
            "ON c.customer_id = o.customer_id "
            "WHERE o.deleted_at IS NULL AND c.deleted_at IS NULL "
            "AND o.status <> 'cancelled' AND c.is_internal = FALSE"
        ),
        why_nearby="uses `is_internal = FALSE` rather than `NOT is_internal`",
    ),
    "multi_currency": RuleProbes(
        violation=f"SELECT SUM(o.amount_minor) / 100.0 {_CLEAN}",
        nearby_legitimate=(
            f"WITH converted AS (SELECT o.amount_minor * {_FX} AS usd {_CLEAN}) "
            "SELECT SUM(usd) FROM converted"
        ),
        why_nearby="converts inside a CTE, so the CASE is not in the outer SELECT",
    ),
    "minor_units": RuleProbes(
        violation=f"SELECT SUM(o.amount_minor) / 100.0 {_CLEAN}",
        nearby_legitimate=f"SELECT SUM(o.amount_minor * {_FX}) {_CLEAN}",
        why_nearby="the declared factor folds the decimal scale in; JPY is not /100",
    ),
    "fan_out": RuleProbes(
        violation=(
            f"SELECT SUM(o.amount_minor * {_FX}) FROM order_items i "
            "JOIN orders o ON o.order_id = i.order_id "
            "JOIN customers c ON c.customer_id = o.customer_id "
            "WHERE o.deleted_at IS NULL"
        ),
        nearby_legitimate=(
            f"SELECT SUM(i.qty * i.unit_price_minor * {_FX}) FROM order_items i "
            "JOIN orders o ON o.order_id = i.order_id "
            "JOIN customers c ON c.customer_id = o.customer_id "
            "WHERE o.deleted_at IS NULL"
        ),
        why_nearby="joins order_items too, but aggregates at line grain, which is correct",
    ),
    "refunds_net": RuleProbes(
        violation="SELECT SUM(o.amount_minor) FROM orders o",
        nearby_legitimate=(
            "SELECT SUM(o.amount_minor) - COALESCE("
            "(SELECT SUM(amount_minor) FROM refunds), 0) FROM orders o"
        ),
        why_nearby="subtracts refunds via a scalar subquery rather than a LEFT JOIN",
    ),
}


def declared_rules() -> tuple[str, ...]:
    return tuple(load_semantic_model()["rules"])


def coverage_report() -> dict:
    """Which declared rules are enforced and probed. The build gate reads this."""
    declared = declared_rules()
    return {
        "declared": list(declared),
        "enforced": sorted(set(declared) & set(RULE_CHECKS)),
        "unenforced": sorted(set(declared) - set(RULE_CHECKS)),
        "unprobed": sorted(set(declared) - set(PROBES)),
        "probed_but_undeclared": sorted(set(PROBES) - set(declared)),
    }


def assert_full_coverage() -> None:
    """Raise unless every declared rule is both enforced and probed.

    Called at import of this module and by a test, so a rule added to the YAML with no
    check fails the build rather than becoming a silent gap in the governance layer.
    """
    report = coverage_report()
    if report["unenforced"]:
        raise UnenforcedRule(
            f"declared in semantic_model.yaml but not enforced: {report['unenforced']}. "
            "A rule the config declares and nothing checks is the defect this project "
            "is about; add a check to loopeng.verify.verifiers.RULE_CHECKS."
        )
    if report["unprobed"]:
        raise UnprobedRule(
            f"enforced but never probed: {report['unprobed']}. Every rule needs a "
            "violation probe and a nearby-legitimate probe, or its enforcement is "
            "untested."
        )


def verify_governed(context: VerifyContext) -> VerifyResult:
    """V2. Same checks as V1, but the applicable rule set comes from the config.

    V1 asks each hardcoded check whether it applies. V2 starts from the rules declared
    in the semantic model, intersects with what the item requires, and refuses to run
    at all if the config declares something unenforced.
    """
    assert_full_coverage()

    if context.execution_error:
        return VerifyResult(violations=())
    tree = _parse(context.sql)
    if tree is None:
        return VerifyResult(violations=())

    violations = []
    for rule in declared_rules():
        if rule not in context.rules:
            continue
        complaint = RULE_CHECKS[rule](context, tree)
        if complaint:
            violations.append(Violation(rule=rule, complaint=complaint))
    return VerifyResult(violations=tuple(violations))


def run_governance_probes(verifier=verify_governed) -> dict:
    """Score a verifier on both directions of every declared rule."""
    def context_for(sql: str, rule: str) -> VerifyContext:
        return VerifyContext(
            question="(probe)", sql=sql, schema_ddl="", rules=(rule,),
            attempt=1, execution_rows=None, execution_error=None,
        )

    results = {}
    for rule, probes in PROBES.items():
        caught = not verifier(context_for(probes.violation, rule)).ok
        accepted = verifier(context_for(probes.nearby_legitimate, rule)).ok
        results[rule] = {
            "caught_the_violation": caught,
            "accepted_the_nearby_legitimate": accepted,
            "sound": caught and accepted,
            "why_nearby": probes.why_nearby,
        }
    return {
        "by_rule": results,
        "n_rules": len(PROBES),
        "n_sound": sum(1 for r in results.values() if r["sound"]),
        "n_missed_violations": sum(1 for r in results.values() if not r["caught_the_violation"]),
        "n_false_rejections": sum(
            1 for r in results.values() if not r["accepted_the_nearby_legitimate"]
        ),
    }


# Enforced at import: a declared-but-unenforced rule cannot survive to runtime.
assert_full_coverage()
