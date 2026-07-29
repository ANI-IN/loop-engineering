"""The same rule checks, done with regexes over the query text.

This module exists to be **worse**, and to be worse in a way that looks better.

A regex verifier asks "does this query mention `deleted_at IS NULL`?" rather than
"does this query actually constrain `deleted_at`?" It therefore accepts a query with
the right words in the wrong places: inside a comment, inside a subquery whose result
is never filtered, on the wrong side of a join, or negated. Every one of those is a
query that breaks the rule while passing the check.

The consequence is the thing worth seeing: **the score goes up and the quality goes
down.** Fewer rejections means a higher pass rate, a shorter loop, and a lower bill,
and every one of those looks like an improvement on a dashboard. The only way to tell
them apart is to test the verifier itself against inputs whose correctness is known —
which is what `loopeng.verify.probes` does.

Nothing here is a strawman. These are the checks a competent engineer writes first,
because they are quick, readable, and pass their own unit tests.
"""

import re

from loopeng.contracts import VerifyContext
from loopeng.verify.verifiers import VerifyResult, Violation

_PATTERNS = {
    "soft_delete": re.compile(r"deleted_at\s+is\s+null", re.IGNORECASE),
    "cancelled_orders": re.compile(r"status\s*(<>|!=)\s*'cancelled'|status\s*=\s*'completed'",
                                   re.IGNORECASE),
    "internal_accounts": re.compile(r"not\s+\w*\.?is_internal|is_internal\s*=\s*false",
                                    re.IGNORECASE),
    "multi_currency": re.compile(r"case\s+.*currency", re.IGNORECASE | re.DOTALL),
    "fan_out": re.compile(r"order_items", re.IGNORECASE),
    "refunds_net": re.compile(r"refunds", re.IGNORECASE),
}

_COMPLAINTS = {
    "soft_delete": "Soft-deleted rows are not excluded.",
    "cancelled_orders": "Cancelled orders are not excluded.",
    "internal_accounts": "Internal test accounts are not excluded.",
    "multi_currency": "Currencies are combined without conversion.",
    "fan_out": "Order-level money is aggregated at line grain.",
    "refunds_net": "Net revenue does not subtract refunds.",
}

# fan_out is inverted relative to the others: mentioning order_items is what a
# correct query does, so the regex version has no way to express the actual trap
# (aggregating orders.amount_minor *after* that join). It is included anyway,
# because leaving it out would make the regex verifier look more careful than it is.
_INVERTED = {"fan_out"}


def verify_with_regex(context: VerifyContext) -> VerifyResult:
    if context.execution_error:
        return VerifyResult(violations=())

    sql = context.sql
    violations = []
    for rule, pattern in _PATTERNS.items():
        applicable = rule in context.rules or (
            rule == "multi_currency" and "minor_units" in context.rules
        )
        if not applicable:
            continue
        found = bool(pattern.search(sql))
        if rule in _INVERTED:
            continue  # the text cannot distinguish correct use from the trap
        if not found:
            violations.append(Violation(rule=rule, complaint=_COMPLAINTS[rule]))
    return VerifyResult(violations=tuple(violations))
