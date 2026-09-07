"""The single connection factory.

Everything that touches the warehouse goes through here. That is what keeps the
DuckDB-versus-hosted-Postgres decision reversible: swapping the backend is a
change to this file and nothing else.

The agent's connection is read-only, enforced by DuckDB rather than by convention,
with tests asserting that INSERT, UPDATE, DELETE, DROP and CREATE all fail.
"""

import threading
from pathlib import Path

import duckdb

from loopeng.warehouse.generate import generate


class QueryTimeout(RuntimeError):
    """A query was interrupted for exceeding its time budget.

    Deliberately not a duckdb.Error. From Phase 2 onward the SQL is written by a
    model, and "this query would never finish" is a different failure class from
    "this query is invalid" — they belong in different buckets of the error
    taxonomy, so they cannot share an exception type.
    """


class StaleWarehouse(RuntimeError):
    """The warehouse on disk cannot hold the gold set the code now describes.

    Raised rather than silently regenerating, and rather than silently proceeding.
    Both alternatives have a failure mode and this one has neither: regenerating
    would destroy a file mid-session that the operator may be depending on, and
    proceeding produces a warehouse whose slices do not exist, so every gold answer
    referencing them is wrong and every arm scores zero.
    """


def ensure_warehouse(path: Path, seed: int) -> Path:
    """Generate the warehouse if it is absent, and refuse a stale one.

    **It used to only check absence, and that cost a measurement.** The docstring
    said checking was deliberate: "silently regenerating someone's warehouse
    mid-session because a seed argument drifted would be a worse failure than using
    the file that is there." That reasoning is still right, and it is about the SEED.

    It does not cover the schema's CONTENT changing. When `CATEGORIES`, `REGIONS` and
    `MONTHS` were widened to build an 84-item gold set, a warehouse generated before
    the widening had none of the new slices — so gold answers referencing `garden` or
    `NORDICS` came back empty and every arm of a 120-call measurement scored exactly
    zero, including the pattern that requires no rules at all.

    Zero everywhere is at least loud. A partial overlap would have been worse: some
    items right, some wrong, and a plausible number on a chart.

    So the check is for the schema's own vocabulary, not for the seed — it asks
    whether this file can represent the categories and regions the code now declares,
    and refuses when it cannot. Refuses rather than regenerates, because the original
    reasoning about not destroying an operator's file still holds.
    """
    path = Path(path)
    if not path.exists():
        generate(path, seed=seed)
        return path

    missing = _missing_slices(path)
    if missing:
        raise StaleWarehouse(
            f"{path} was generated before the schema's vocabulary changed and is "
            f"missing: {missing}.\n"
            f"Every gold answer referencing those slices would come back empty, and "
            f"the arm would score zero without anything saying why.\n"
            f"Fix: delete {path} and let it regenerate from seed {seed}. It is a "
            f"generated file — nothing is lost."
        )
    return path


def _missing_slices(path: Path) -> dict[str, list[str]]:
    """Declared vocabulary the warehouse on disk does not contain.

    Cheap: two DISTINCT queries against small columns. Asks about the CONTENT the
    gold set indexes into rather than about the seed, because that is what makes an
    answer unreachable.
    """
    from loopeng.warehouse.schema import CATEGORIES, REGIONS

    con = duckdb.connect(str(path), read_only=True)
    try:
        present = {
            "categories": {r[0] for r in
                           con.execute("SELECT DISTINCT category FROM products").fetchall()},
            "regions": {r[0] for r in
                        con.execute("SELECT DISTINCT region FROM customers").fetchall()},
        }
    except duckdb.Error:
        # A file that cannot even be queried for this is a different problem, and
        # the caller will meet it immediately with a clearer error than we could give.
        return {}
    finally:
        con.close()

    missing = {}
    for label, declared in (("categories", CATEGORIES), ("regions", REGIONS)):
        absent = sorted(set(declared) - present[label])
        if absent:
            missing[label] = absent
    return missing


def agent_connection(path: Path) -> duckdb.DuckDBPyConnection:
    """Read-only. The agent writes SQL; it never writes data."""
    return duckdb.connect(str(path), read_only=True)


def run_sql(sql: str, path: Path, timeout_s: float = 30.0) -> list[tuple]:
    """Execute one statement against a read-only connection, under a time budget.

    The budget is enforced by interrupting the connection from a timer thread —
    DuckDB has no per-query timeout setting, and a timeout parameter that did not
    actually stop anything would be precisely the declared-versus-enforced defect
    this project exists to demonstrate. It matters in practice: a model that writes
    an unintended cross join produces a query with no natural end, and one such cell
    would otherwise stall an entire sweep.
    """
    con = agent_connection(path)
    timer = threading.Timer(timeout_s, con.interrupt)
    timer.start()
    try:
        return con.execute(sql).fetchall()
    except duckdb.InterruptException as exc:
        raise QueryTimeout(f"query exceeded its {timeout_s}s budget and was interrupted") from exc
    finally:
        timer.cancel()
        con.close()
