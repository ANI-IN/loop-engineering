"""Rule-surface probes: test the verifier, not the model.

A verifier is a measuring instrument, and an instrument is checked against inputs
whose answer is already known — not by looking at how good the numbers it produces
are. A verifier that rejects nothing produces a wonderful pass rate.

Each probe is a pair of queries per rule: one that **honours** the rule and must be
accepted, and one that **breaks** it and must be rejected. Both run offline against
literals, so the whole surface is measurable with no model calls and no cost.

**This is also how `refunds_net` gets covered at all.** Gate 0 recorded that the rule
is carried by a single pattern (5 items, 1 cluster), so the sweep can make no claim
about it — a flat ablation line there means "not measured", not "the verifier missed
it". The probes test enforcement directly, which is a different and stronger kind of
evidence than inferring it from sweep outcomes.
"""

from dataclasses import dataclass

from loopeng.contracts import VerifyContext
from loopeng.verify.verifiers import verify

_CLEAN_JOIN = (
    "FROM orders o JOIN customers c ON c.customer_id = o.customer_id "
    "WHERE o.deleted_at IS NULL AND c.deleted_at IS NULL "
    "AND o.status <> 'cancelled' AND NOT c.is_internal"
)
_FX = "CASE o.currency WHEN 'USD' THEN 0.01 WHEN 'EUR' THEN 0.0108 WHEN 'JPY' THEN 0.0067 END"


@dataclass(frozen=True)
class Probe:
    rule: str
    honours: str
    breaks: str
    note: str


PROBES: tuple[Probe, ...] = (
    Probe(
        rule="soft_delete",
        honours=f"SELECT COUNT(*) {_CLEAN_JOIN}",
        breaks=(
            "SELECT COUNT(*) FROM orders o JOIN customers c "
            "ON c.customer_id = o.customer_id "
            "WHERE o.status <> 'cancelled' AND NOT c.is_internal"
        ),
        note="deleted_at unconstrained on either table",
    ),
    Probe(
        rule="cancelled_orders",
        honours=f"SELECT COUNT(*) {_CLEAN_JOIN}",
        breaks=(
            "SELECT COUNT(*) FROM orders o JOIN customers c "
            "ON c.customer_id = o.customer_id "
            "WHERE o.deleted_at IS NULL AND c.deleted_at IS NULL AND NOT c.is_internal"
        ),
        note="status never filtered",
    ),
    Probe(
        rule="internal_accounts",
        honours=f"SELECT COUNT(*) {_CLEAN_JOIN}",
        breaks=(
            "SELECT COUNT(*) FROM orders o JOIN customers c "
            "ON c.customer_id = o.customer_id "
            "WHERE o.deleted_at IS NULL AND c.deleted_at IS NULL "
            "AND o.status <> 'cancelled'"
        ),
        note="is_internal never filtered",
    ),
    Probe(
        rule="multi_currency",
        honours=f"SELECT SUM(o.amount_minor * {_FX}) {_CLEAN_JOIN}",
        breaks=f"SELECT SUM(o.amount_minor) / 100.0 {_CLEAN_JOIN}",
        note="raw minor units divided by 100, no per-currency conversion",
    ),
    Probe(
        rule="fan_out",
        honours=(
            f"SELECT SUM(i.qty * i.unit_price_minor * {_FX}) "
            "FROM order_items i JOIN orders o ON o.order_id = i.order_id "
            "JOIN customers c ON c.customer_id = o.customer_id "
            "WHERE o.deleted_at IS NULL"
        ),
        breaks=(
            f"SELECT SUM(o.amount_minor * {_FX}) "
            "FROM order_items i JOIN orders o ON o.order_id = i.order_id "
            "JOIN customers c ON c.customer_id = o.customer_id "
            "WHERE o.deleted_at IS NULL"
        ),
        note="order-grain money aggregated after joining order_items",
    ),
    Probe(
        rule="refunds_net",
        honours=(
            "SELECT SUM(o.amount_minor - COALESCE(r.refunded, 0)) FROM orders o "
            "LEFT JOIN (SELECT order_id, SUM(amount_minor) AS refunded FROM refunds "
            "GROUP BY order_id) r ON r.order_id = o.order_id"
        ),
        breaks="SELECT SUM(o.amount_minor) FROM orders o",
        note="refunds never subtracted; the sweep cannot measure this rule at all",
    ),
)


def _context(sql: str, rule: str) -> VerifyContext:
    return VerifyContext(
        question="(probe)",
        sql=sql,
        schema_ddl="",
        rules=(rule,),
        attempt=1,
        execution_rows=None,
        execution_error=None,
    )


def run_probes(verifier=verify) -> dict:
    """Score a verifier against every rule's honours/breaks pair.

    Two numbers per rule, and they are not the same thing:
      caught  — the breaking query was rejected (the verifier does its job)
      passed  — the honouring query was accepted (it does not reject everything)

    A verifier that rejects everything scores perfectly on `caught` alone, which is
    why both are reported and why the summary counts them separately.
    """
    results = {}
    for probe in PROBES:
        caught = not verifier(_context(probe.breaks, probe.rule)).ok
        accepted = verifier(_context(probe.honours, probe.rule)).ok
        results[probe.rule] = {
            "caught_the_violation": caught,
            "accepted_the_correct_query": accepted,
            "sound": caught and accepted,
            "note": probe.note,
        }
    n_sound = sum(1 for r in results.values() if r["sound"])
    return {
        "by_rule": results,
        "n_rules": len(PROBES),
        "n_sound": n_sound,
        "n_missed_violations": sum(
            1 for r in results.values() if not r["caught_the_violation"]
        ),
        "n_false_rejections": sum(
            1 for r in results.values() if not r["accepted_the_correct_query"]
        ),
    }
