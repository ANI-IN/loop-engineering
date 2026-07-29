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


def ensure_warehouse(path: Path, seed: int) -> Path:
    """Generate the warehouse if it is absent. Returns the path either way.

    Deliberately does not check that an existing file was built with this seed:
    the file is gitignored and rebuilt from scratch, and silently regenerating
    someone's warehouse mid-session because a seed argument drifted would be a
    worse failure than using the file that is there.
    """
    path = Path(path)
    if not path.exists():
        generate(path, seed=seed)
    return path


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
