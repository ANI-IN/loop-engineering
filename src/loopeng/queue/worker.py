"""The polling worker: claim a row, run the Level 2 loop, write the answer back.

It runs the LEVEL 2 loop, not Level 1, and that is the teaching point of this stage.
With nobody watching, the verifiers are the only thing standing between the queue and
whatever consumes the answers — everything the previous stage said about a verifier
being a measuring instrument stops being an argument about measurement and becomes an
argument about what ships.
"""

import time
from pathlib import Path

import structlog

from loopeng.gold.build import build_gold
from loopeng.queue import store
from loopeng.verify.governance import verify_governed
from loopeng.verify.loop import run_verified

log = structlog.get_logger(__name__)

POLL_SECONDS = 2.0


def _rules_for(question: str, warehouse: Path) -> tuple[str, ...]:
    """Look the question up in the gold set to find which rules apply.

    A question that is not in the gold set gets no rules, which means the verifiers
    check nothing. That is honest rather than convenient: this demo answers the
    workshop's questions, and inventing a rule set for an unknown question would be
    the verifier claiming a coverage it does not have.
    """
    for item in build_gold(warehouse):
        if item.question.strip() == question.strip():
            return item.rules
    return ()


def process_one(con, warehouse: Path, *, role: str = "worker", level: str = "L3",
                client=None) -> store.QueueRow | None:
    """Claim and answer one row. Returns the row, or None if the queue was empty."""
    row = store.claim(con)
    if row is None:
        return None

    log.info("claimed", id=row.id, question=row.question[:60])
    try:
        run = run_verified(
            row.question, warehouse=warehouse, rules=_rules_for(row.question, warehouse),
            role=role, level=level, max_attempts=3, client=client, verifier=verify_governed,
        )
    except Exception as exc:  # noqa: BLE001 - a dead row must not kill the worker
        store.fail(con, row.id, f"{type(exc).__name__}: {exc}")
        log.error("failed", id=row.id, error=str(exc))
        return row

    if run.error or run.rows is None:
        # No retry, no dead-letter queue. It stays failed, where you can see it.
        store.fail(con, row.id, run.error or "no result")
        log.warning("failed", id=row.id, reason=run.error)
    else:
        store.finish(con, row.id, f"{run.rows} (terminated: {run.termination})")
        log.info("done", id=row.id, termination=str(run.termination))
    return row


def serve(con, warehouse: Path, *, poll_seconds: float = POLL_SECONDS,
          max_idle_polls: int | None = None, client=None) -> int:
    """Poll until interrupted. `max_idle_polls` bounds it for tests.

    Ctrl-C leaves an in-flight row `claimed` forever. That is a visible consequence of
    having no retry logic, and it is worth showing rather than hiding.
    """
    processed = idle = 0
    while True:
        if process_one(con, warehouse, client=client) is not None:
            processed += 1
            idle = 0
            continue
        idle += 1
        if max_idle_polls is not None and idle >= max_idle_polls:
            return processed
        time.sleep(poll_seconds)
