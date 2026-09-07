"""Structural questions about a query, answered from the parse tree.

Small and deliberately placed low. Both `agent.loop` and `agent.classify` need to ask
whether a query names an input it was never given, and they cannot share the answer
through either of the obvious routes: `classify` imports `loop`, so `loop` cannot
import back; and the predicate must never live in `gold/`, because **the loop is not
allowed to import anything from the gold package** — that isolation is the Phase 0
contract, and a pure helper is still an import.

So it lives here, above nothing and below everything, importing only sqlglot.

**Parse tree, never regex, never the database's error text.** A regex for a
dollar-name matches inside a string literal, so `SELECT '$eur_to_usd'` — an ordinary
broken query — would read as a principled refusal. Matching DuckDB's wording would
tie the question to one engine's phrasing when the question is about what the model
wrote. This is the verifiers' own lesson, applied where two other modules need it.
"""

import sqlglot
from sqlglot import expressions as exp


def declares_unbound_parameter(sql: str) -> bool:
    r"""Does this query name a value it was never given, rather than inventing one?

    A query carrying an unbound placeholder — `$eur_to_usd`, `:rate` — cannot execute,
    and that is the point: the model has written down exactly which input it lacks
    instead of guessing at it.

    Unparseable SQL is `False`. A query that does not parse is an ordinary execution
    failure and has not declined anything.
    """
    if not sql:
        return False
    try:
        tree = sqlglot.parse_one(sql, read="duckdb")
    except Exception:  # noqa: BLE001 - unparseable SQL is an ordinary failure
        return False
    if tree is None:
        return False
    return bool(next(tree.find_all(exp.Placeholder, exp.Parameter), None))
