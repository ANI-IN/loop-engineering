"""Executes every pattern against the warehouse and freezes the answers.

Two properties gate an item, and one does not.

*Non-degenerate.* An item whose gold answer is all nulls or all zeros cannot
distinguish a correct query from several wrong ones.

*Discriminating.* Gold must differ from the composite naive — the answer you get
ignoring every rule at once. An item where those coincide scores the same at L0 and
L3 and flattens the very gap the workshop is built to show. This one is load-bearing
and carries the two-regeneration hard stop: it raises rather than looping, because
an item that will not discriminate after two reparameterisations is the generator
emitting thin data for that slice, and quietly trying a third hides exactly the
defect worth knowing about.

*Ambiguity is not a gate.* When two rules produce the same wrong answer, the item is
kept and the pair recorded. An item whose variants collide still measures
silent-error rate perfectly well, and that is the headline metric; dropping it would
spend n on the primary measurement to protect the taxonomy, which is secondary.

Everything runs through `run_sql`, the read-only factory. Gold that could only be
produced with write access would be gold the agent cannot reach.
"""

import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from loopeng.gold.compare import is_order_sensitive, rows_equal
from loopeng.gold.patterns import PATTERNS, Pattern
from loopeng.warehouse.connect import run_sql

MAX_REGENERATIONS = 2


class DegenerateGoldItem(RuntimeError):
    """The gold answer is all nulls or zeros and cannot separate right from wrong."""


class IndistinguishableGoldItem(RuntimeError):
    """Gold equals its composite naive: the item cannot tell L0 from L3.

    Raised rather than worked around. Reaching this after the regeneration budget
    means the warehouse has too few rows on one side of a rule for that slice, and
    the same thinness will flatten the sweep silently, where nobody is watching.
    """


@dataclass(frozen=True)
class GoldItem:
    item_id: str
    pattern_key: str
    question: str
    gold_sql: str
    gold_rows: list[list]
    naive_sql: str | None
    naive_rows: list[list] | None
    # rule -> {"sql": ..., "rows": ...}, one entry per rule ignored alone.
    naive_by_rule: dict[str, dict] = field(default_factory=dict)
    # Rules whose variants are indistinguishable from each other, or from gold.
    # The reveal names every rule in a group rather than picking one.
    ambiguous_rule_groups: tuple[tuple[str, ...], ...] = ()
    rules: tuple[str, ...] = ()
    order_sensitive: bool = False


def json_default(value):
    """Serialise DuckDB's types without turning numbers into strings.

    A blanket `default=str` looks harmless and is not: DuckDB returns DECIMAL from
    exactly the aggregates the revenue patterns use, and str(Decimal('76744.66')) is
    '76744.66'. On reload that gold answer is a string, rows_equal correctly refuses
    to equate a number with its string form, and every revenue item then fails
    against a *correct* model answer. gold.jsonl is what reaches LangSmith and what
    grading compares against, so the damage would have been invisible until the
    sweep reported half the set as wrong.
    """
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    return str(value)


def _rows(sql: str, warehouse: Path) -> list[list]:
    return [list(row) for row in run_sql(sql, warehouse)]


def _is_degenerate(rows: list[list]) -> bool:
    flat = [value for row in rows for value in row]
    return not flat or all(value in (None, 0, 0.0) for value in flat)


def _ambiguous_groups(
    naive_by_rule: dict[str, dict], gold_rows: list[list], order_sensitive: bool
) -> tuple[tuple[str, ...], ...]:
    """Group rules whose naive answers cannot be told apart.

    A variant equal to *gold* is grouped too: that rule is inert for this item, so a
    matching output means the model got it right, not that it dropped the rule.
    Either way the taxonomy cannot attribute uniquely, and saying so beats guessing.
    """
    rules = sorted(naive_by_rule)
    groups: list[set[str]] = []

    inert = {
        rule
        for rule in rules
        if rows_equal(naive_by_rule[rule]["rows"], gold_rows, order_sensitive=order_sensitive)
    }

    for index, rule in enumerate(rules):
        for other in rules[index + 1:]:
            if rows_equal(
                naive_by_rule[rule]["rows"],
                naive_by_rule[other]["rows"],
                order_sensitive=order_sensitive,
            ):
                for group in groups:
                    if rule in group or other in group:
                        group.update({rule, other})
                        break
                else:
                    groups.append({rule, other})

    for rule in inert:
        if not any(rule in group for group in groups):
            groups.append({rule})

    return tuple(tuple(sorted(group)) for group in sorted(groups, key=sorted))


def _build_item(pattern: Pattern, params: dict, index: int, warehouse: Path) -> GoldItem:
    item_id = f"{pattern.key}__{index:02d}"
    gold_sql = pattern.gold_sql.format(**params)
    gold_rows = _rows(gold_sql, warehouse)
    order_sensitive = is_order_sensitive(gold_sql)

    if _is_degenerate(gold_rows):
        raise DegenerateGoldItem(f"{item_id}: gold answer is all nulls or zeros: {gold_rows!r}")

    naive_sql = naive_rows = None
    if pattern.naive_sql is not None:
        naive_sql = pattern.naive_sql.format(**params)
        naive_rows = _rows(naive_sql, warehouse)
        if rows_equal(gold_rows, naive_rows, order_sensitive=order_sensitive):
            raise IndistinguishableGoldItem(
                f"{item_id}: gold equals its composite naive answer ({gold_rows!r}); "
                "this item scores the same at L0 and L3 and cannot discriminate"
            )

    naive_by_rule: dict[str, dict] = {}
    for rule, template in pattern.naive_sql_by_rule.items():
        sql = template.format(**params)
        naive_by_rule[rule] = {"sql": sql, "rows": _rows(sql, warehouse)}

    return GoldItem(
        item_id=item_id,
        pattern_key=pattern.key,
        question=pattern.question.format(**params),
        gold_sql=gold_sql,
        gold_rows=gold_rows,
        naive_sql=naive_sql,
        naive_rows=naive_rows,
        naive_by_rule=naive_by_rule,
        ambiguous_rule_groups=_ambiguous_groups(naive_by_rule, gold_rows, order_sensitive),
        rules=pattern.rules,
        order_sensitive=order_sensitive,
    )


def build_gold(warehouse: Path) -> list[GoldItem]:
    """Execute every pattern at every parameterisation. Raises rather than looping.

    There is deliberately no retry loop here. The plan's regeneration budget is two
    attempts, and the third attempt is the one that would paper over a real defect,
    so a failure surfaces as an exception naming the item and what went wrong.
    """
    items: list[GoldItem] = []
    for pattern in PATTERNS:
        for index, params in enumerate(pattern.params):
            items.append(_build_item(pattern, params, index, warehouse))
    return items


def clustering_summary(items: list[GoldItem]) -> dict:
    """What the 50 items actually are, statistically.

    They are not 50 independent trials. Ten patterns contribute five items each, and
    a systematic flaw in one pattern — a misread rule, an unlucky scope — fails all
    five together. A Wilson interval computed as if n=50 is therefore too narrow.

    This is recorded rather than corrected: the honest fix is a design with more
    patterns and fewer parameterisations each, which is not what this phase builds.
    Overstating precision is the failure mode the whole project exists to avoid, so
    the caveat travels with the number to the screen.
    """
    per_pattern = Counter(item.pattern_key for item in items)
    sizes = set(per_pattern.values())
    return {
        "n_items": len(items),
        "n_clusters": len(per_pattern),
        "items_per_cluster": sizes.pop() if len(sizes) == 1 else sorted(sizes),
        "items_by_pattern": dict(sorted(per_pattern.items())),
        "caveat": (
            "The 50 items are 10 clusters of 5 parameterisations, not 50 independent "
            "trials. A systematic flaw in one pattern fails all five of its items "
            "together, so an interval computed as if n=50 is narrower than the "
            "evidence supports. Report alongside the templating disclosure."
        ),
    }


def ambiguity_summary(items: list[GoldItem]) -> dict:
    ambiguous = [item for item in items if item.ambiguous_rule_groups]
    pairs = Counter(
        group for item in ambiguous for group in item.ambiguous_rule_groups if len(group) > 1
    )
    return {
        "n_ambiguous_items": len(ambiguous),
        "n_items": len(items),
        "groups": {" | ".join(group): count for group, count in sorted(pairs.items())},
        "by_item": {item.item_id: item.ambiguous_rule_groups for item in ambiguous},
    }


def write_gold(items: list[GoldItem], path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for item in items:
            handle.write(
                json.dumps(
                    {
                        "item_id": item.item_id,
                        "pattern_key": item.pattern_key,
                        "question": item.question,
                        "gold_sql": item.gold_sql,
                        "gold_rows": item.gold_rows,
                        "naive_sql": item.naive_sql,
                        "naive_rows": item.naive_rows,
                        "naive_by_rule": item.naive_by_rule,
                        "ambiguous_rule_groups": [
                            list(group) for group in item.ambiguous_rule_groups
                        ],
                        "rules": list(item.rules),
                        "order_sensitive": item.order_sensitive,
                    },
                    default=json_default,
                )
                + "\n"
            )


def read_gold(path: Path) -> list[GoldItem]:
    items = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        body = json.loads(line)
        items.append(
            GoldItem(
                item_id=body["item_id"],
                pattern_key=body["pattern_key"],
                question=body["question"],
                gold_sql=body["gold_sql"],
                gold_rows=body["gold_rows"],
                naive_sql=body["naive_sql"],
                naive_rows=body["naive_rows"],
                naive_by_rule=body["naive_by_rule"],
                ambiguous_rule_groups=tuple(
                    tuple(group) for group in body["ambiguous_rule_groups"]
                ),
                rules=tuple(body["rules"]),
                order_sensitive=body["order_sensitive"],
            )
        )
    return items
