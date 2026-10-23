"""The SQL guidance check: a rule's SQL guidance must run over the real schema.

A rule's sql_guidance reaches the analyst's prompt word for word, so guidance that does not run
leaves the analyst to guess: a placeholder ("<documented non-internal-customer predicate>"), a
column that does not exist ("customer_is_internal = false"), or prose where SQL should be. The
check is deterministic, like the overfit guard. It parses the guidance with sqlglot as a condition,
an expression, a clause, or a whole query, then looks up every table and column in the catalog
snapshot of the allowed schema. Empty guidance passes: a rule may need no SQL.

In the analyzer team, a rule whose guidance fails goes back to the critic with its problems, to
narrow; a rule that still fails after the critic is dropped, its problems recorded as the reason.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

import sqlglot
from sqlglot import exp

from datapilot.contracts import ProposedRule
from datapilot.loop1_agent.catalog import CatalogSnapshot

DIALECT = "postgres"
# Words in angle brackets or braces, or an ellipsis, stand for SQL nobody wrote. "<>" and "a < b"
# do not match: a placeholder starts with a letter right after its bracket.
_PLACEHOLDER = re.compile(r"<[A-Za-z_][^<>]*>|\{[^{}]*\}|\.\.\.|…")
# A fragment that starts with one of these is a clause of a query, not a condition.
_CLAUSES = {"where", "join", "left", "right", "inner", "full", "cross", "group", "order", "having"}
_ANCHOR = "guidance_fragment"  # the stand-in table a clause or a condition is parsed against


@dataclass(frozen=True)
class GuidanceResult:
    rule_id: str
    passed: bool
    problems: list[str]


class GuidanceCheck:
    def __init__(self, snapshot: CatalogSnapshot) -> None:
        self.snapshot = snapshot
        self._columns = {
            name: {c.name.lower() for c in table.columns} for name, table in snapshot.tables.items()
        }
        self._every_column = {c for columns in self._columns.values() for c in columns}

    @classmethod
    def from_database(cls) -> GuidanceCheck:
        """The catalog of the pack's allowed schema, as the agent's executor sees it (catalog
        system SQL only, the same snapshot the schema grader uses)."""
        from datapilot.loop1_agent.catalog import load_snapshot
        from datapilot.loop4_hill_climbing.sql_runner import WAREHOUSES, executors

        executor = executors()[WAREHOUSES[0]]
        return cls(load_snapshot(executor.url, executor.schema))

    def schema(self) -> dict[str, list[str]]:
        """Each table of the allowed schema with its columns, for the rule writer and the critic."""
        return {name: table.column_names for name, table in sorted(self.snapshot.tables.items())}

    def check(self, rule: ProposedRule) -> GuidanceResult:
        problems = self.problems(rule.sql_guidance)
        return GuidanceResult(rule_id=rule.id, passed=not problems, problems=problems)

    def check_all(self, rules: Sequence[ProposedRule]) -> dict[str, list[str]]:
        """The problems of each rule whose guidance fails, by rule id."""
        return {r.id: found for r in rules if (found := self.problems(r.sql_guidance))}

    def problems(self, guidance: str) -> list[str]:
        text = guidance.strip().rstrip(";").strip()
        if not text:
            return []
        placeholders = _PLACEHOLDER.findall(text)
        if placeholders:
            return [f"SQL guidance has a placeholder, not SQL: {', '.join(placeholders)}"]
        tree = _parse(text)
        if tree is None:
            return [f"SQL guidance does not parse as SQL: {text}"]
        return self._unknown_names(tree)

    def _unknown_names(self, tree: exp.Expression) -> list[str]:
        problems: list[str] = []
        ctes = {cte.alias_or_name.lower() for cte in tree.find_all(exp.CTE)}
        derived = {s.alias.lower() for s in tree.find_all(exp.Subquery) if s.alias}
        aliases: dict[str, str] = {}  # table alias or name -> table
        for table in tree.find_all(exp.Table):
            name = table.name.lower()
            if name == _ANCHOR or name in ctes:
                continue
            if table.db and table.db.lower() != self.snapshot.schema.lower():
                problems.append(f"SQL guidance names a schema other than {self.snapshot.schema}")
            elif name not in self._columns:
                problems.append(f"SQL guidance names a table that does not exist: {table.name}")
            else:
                aliases[name] = name
                aliases[table.alias_or_name.lower()] = name
        outputs = {a.alias.lower() for a in tree.find_all(exp.Alias) if a.alias}
        for column in tree.find_all(exp.Column):
            name, qualifier = column.name.lower(), column.table.lower()
            if not name:
                continue  # a star
            if qualifier in aliases:
                known = name in self._columns[aliases[qualifier]]
            elif qualifier in ctes or qualifier in derived:
                known = True
            else:
                known = name in self._every_column or (not qualifier and name in outputs)
            if not known:
                problems.append(
                    f"SQL guidance names a column that does not exist: {column.sql(DIALECT)}"
                )
        return list(dict.fromkeys(problems))


def _parse(text: str) -> exp.Expression | None:
    """The guidance as one statement: a whole query as written, a clause after a stand-in FROM, a
    condition or expression in a WHERE, or a list of expressions after SELECT."""
    first = text.split(None, 1)[0].lower()
    if first in ("select", "with"):
        forms = [text]
    elif first == "from":
        forms = [f"SELECT 1 {text}"]
    elif first in _CLAUSES:
        forms = [f"SELECT 1 FROM {_ANCHOR} {text}"]
    else:
        forms = [f"SELECT 1 FROM {_ANCHOR} WHERE {text}", f"SELECT {text} FROM {_ANCHOR}"]
    for form in forms:
        try:
            tree = sqlglot.parse_one(form, read=DIALECT)
        except sqlglot.errors.SqlglotError:
            continue
        if tree is None or (form.startswith(f"SELECT {text}") and _implicit_alias(tree, text)):
            continue
        return tree
    return None


def _implicit_alias(tree: exp.Expression, text: str) -> bool:
    """Prose such as "status code" parses as a column with an alias; real guidance writes AS."""
    if not isinstance(tree, exp.Select):
        return False
    for projection in tree.expressions:
        if isinstance(projection, exp.Alias) and projection.alias:
            spelled = re.compile(rf"\bas\s+\"?{re.escape(projection.alias)}\b", re.IGNORECASE)
            if not spelled.search(text):
                return True
    return False
