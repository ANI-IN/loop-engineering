"""The question queue. A DuckDB table, five columns, no ceremony.

Deliberately minimal, and the omissions are the point rather than an apology:

  **no backoff**        — a worker that cannot reach the model spins and you see it
  **no dead-lettering** — a failed row stays `failed` where the evidence is visible
  **no retry**          — nothing quietly tries again behind your back

Those are the things you would have to build before this went near production, and
naming them is more useful than half-implementing them. What it does demonstrate is
the only thing that matters at this level: **nobody is watching.** Levels 1 and 2 run
because a person typed a command and read the output; here a worker claims work and
answers it with no human in the path, which makes the verifiers the only thing between
the queue and whatever consumes the answers.

The queue lives in its own DuckDB file, separate from the warehouse. The warehouse is
opened read-only by everything that touches it, and a queue needs writes — sharing one
file would mean relaxing that, which is exactly the guarantee Phase 0 spent a test on.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import duckdb

DEFAULT_QUEUE_PATH = Path("question_queue.duckdb")

SCHEMA = """
CREATE TABLE IF NOT EXISTS question_queue (
    id         INTEGER PRIMARY KEY,
    question   VARCHAR   NOT NULL,
    status     VARCHAR   NOT NULL,
    result     VARCHAR,
    claimed_at TIMESTAMP
);
"""

QUEUED, CLAIMED, DONE, FAILED = "queued", "claimed", "done", "failed"


@dataclass(frozen=True)
class QueueRow:
    id: int
    question: str
    status: str
    result: str | None
    claimed_at: datetime | None


def connect(path: Path = DEFAULT_QUEUE_PATH) -> duckdb.DuckDBPyConnection:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(path))
    con.execute(SCHEMA)
    return con


def enqueue(con, question: str) -> int:
    next_id = con.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM question_queue").fetchone()[0]
    con.execute(
        "INSERT INTO question_queue VALUES (?, ?, ?, NULL, NULL)",
        [next_id, question, QUEUED],
    )
    return next_id

def claim(con) -> QueueRow | None:
    """Take the oldest queued row, atomically. Returns None when there is nothing.

    The UPDATE ... RETURNING is one statement, so two workers cannot claim the same
    row: whichever commits first moves it out of `queued` and the other's subquery
    finds nothing. That is the whole of the concurrency story, and it is the one part
    of a queue worth getting right even in a demo.
    """
    rows = con.execute(
        """
        UPDATE question_queue SET status = ?, claimed_at = now()
        WHERE id = (SELECT MIN(id) FROM question_queue WHERE status = ?)
        RETURNING id, question, status, result, claimed_at
        """,
        [CLAIMED, QUEUED],
    ).fetchall()
    return QueueRow(*rows[0]) if rows else None


def finish(con, row_id: int, result: str) -> None:
    con.execute(
        "UPDATE question_queue SET status = ?, result = ? WHERE id = ?",
        [DONE, result, row_id],
    )


def fail(con, row_id: int, reason: str) -> None:
    """A failed row stays failed. Nothing sweeps it up, and that is deliberate."""
    con.execute(
        "UPDATE question_queue SET status = ?, result = ? WHERE id = ?",
        [FAILED, reason, row_id],
    )


def all_rows(con) -> list[QueueRow]:
    return [
        QueueRow(*r)
        for r in con.execute(
            "SELECT id, question, status, result, claimed_at FROM question_queue ORDER BY id"
        ).fetchall()
    ]


def counts(con) -> dict[str, int]:
    return dict(
        con.execute("SELECT status, COUNT(*) FROM question_queue GROUP BY status").fetchall()
    )
