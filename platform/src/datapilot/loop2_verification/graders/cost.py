"""Grader 4, cost: refuse a query before it runs when its plan is too expensive.

It is not a security layer: it estimates only what the syntax-tree classifier calls one read-only
SELECT and reports "not applicable" for anything else, so EXPLAIN never sees a write.
Two checks: a join with no join condition (a cartesian product), found on the syntax tree, and the
planner's own estimate from EXPLAIN (FORMAT JSON) against the pack's thresholds.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sqlglot import exp

from datapilot.contracts import GraderContext, GraderResult, Stage
from datapilot.loop2_verification.config import VerificationConfig
from datapilot.loop2_verification.executor import ExecutionError
from datapilot.loop2_verification.graders._sql import blocked, parse_single, passed
from datapilot.loop2_verification.graders.statement_policy import is_read_only_select
from datapilot.planted import planted

Explain = Callable[[str], dict[str, Any]]


def _joined_in_where(select: exp.Select, alias: str) -> bool:
    """A comma join is fine when WHERE equates one of its columns with another table's column."""
    where = select.args.get("where")
    if where is None:
        return False
    for eq in where.find_all(exp.EQ):
        left, right = eq.left, eq.right
        if isinstance(left, exp.Column) and isinstance(right, exp.Column):
            tables = {left.table.lower(), right.table.lower()}
            if alias in tables and len(tables) == 2:
                return True
    return False


def unconditioned_join(tree: exp.Expression) -> str | None:
    """The alias of the first joined table with no join condition, or None."""
    for join in tree.find_all(exp.Join):
        if join.args.get("on") is not None or join.args.get("using"):
            continue
        target = join.this
        if not isinstance(target, exp.Table) or not isinstance(target.this, exp.Identifier):
            continue  # LATERAL subqueries and set-returning functions
        alias = target.alias_or_name.lower()
        select = join.find_ancestor(exp.Select)
        if (join.kind or "").upper() != "CROSS" and select and _joined_in_where(select, alias):
            continue
        return alias
    return None


class CostGrader:
    name = "cost"
    stage = Stage.PRE_EXECUTION

    def __init__(self, config: VerificationConfig, explain: Explain) -> None:
        self.config = config
        self.explain = explain

    def check(self, context: GraderContext) -> GraderResult:
        if planted("BUG_NO_COST_GUARD"):
            return passed(self.name, "cost guard off")  # planted: every plan is accepted
        sql = context.sql or ""
        # Not a security layer: it estimates read-only SELECTs only, asking the real syntax-tree
        # classifier even when the naive guard is planted; refusing writes stays with the guard
        # and the database's read-only transaction.
        if not is_read_only_select(sql):
            return passed(
                self.name, "not applicable: only a read-only SELECT is estimated (no EXPLAIN)"
            )
        tree = parse_single(sql)
        alias = unconditioned_join(tree) if tree is not None else None
        if alias:
            return blocked(
                self.name,
                f"join without a condition on {alias} (a cartesian product)",
                f"The join to {alias} has no ON or USING condition; add the join keys.",
            )
        try:
            plan = self.explain(sql)
        except ExecutionError as error:
            return blocked(self.name, f"EXPLAIN failed: {error.message}", error.feedback)
        cost, rows = float(plan["Total Cost"]), float(plan["Plan Rows"])
        if cost > self.config.max_plan_cost or rows > self.config.max_plan_rows:
            return blocked(
                self.name,
                f"plan cost {cost:,.0f} and {rows:,.0f} rows over the limits "
                f"({self.config.max_plan_cost:,.0f}, {self.config.max_plan_rows:,.0f})",
                "The plan is too expensive. Filter earlier, aggregate, or join on keys.",
            )
        return passed(self.name, f"plan cost {cost:,.0f}, {rows:,.0f} rows")
