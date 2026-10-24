"""The worker's record of each trace LangSmith refused for its monthly limit, on the run's row.

The SDK logs a refused upload on its background tracing thread, often after the run has finished,
and only the uploading process sees that line. The worker hands each refusal's ids
(observability.background.on_refused_runs) to a `RefusalRecorder`: the logging filter only queues
them, and one daemon thread writes them to ops.runs.trace_refused_at with its own short
connection. A run's id is its trace id (the analyst's config passes it as the root run id), so
the trace ids the SDK names match ops.runs rows; the ids of child runs match none.
"""

from __future__ import annotations

import queue
import threading
import time
import uuid
from collections.abc import Callable, Iterable

import structlog

from datapilot import db
from datapilot.observability.background import on_refused_runs

log = structlog.get_logger("trace_refusals")

RECORDER_THREAD = "trace-refusal-recorder"
QUEUE_SIZE = 1000
# The first refusal is kept: it is when LangSmith first turned the run's trace away.
RECORD_SQL = (
    "UPDATE ops.runs SET trace_refused_at = COALESCE(trace_refused_at, now()), "
    "updated_at = now() WHERE run_id = ANY(%s::uuid[])"
)

Write = Callable[[list[str]], None]


def run_ids(named: Iterable[str]) -> list[str]:
    """The ids that are well-formed UUIDs, sorted; the SDK's line could name anything."""
    found = set()
    for text in named:
        try:
            found.add(str(uuid.UUID(text)))
        except ValueError:
            continue
    return sorted(found)


def write_to_ops(ids: list[str]) -> None:
    with db.connect(db.Role.APP) as conn:
        conn.execute(RECORD_SQL, (ids,))
        conn.commit()


class RefusalRecorder:
    """Queues each refusal's ids without blocking, and writes them from one daemon thread."""

    def __init__(self, write: Write = write_to_ops, size: int = QUEUE_SIZE) -> None:
        self.write = write
        self.queue: queue.Queue[list[str]] = queue.Queue(maxsize=size)
        self.dropped = 0
        self.failed = 0
        self._lock = threading.Lock()
        threading.Thread(target=self._drain, name=RECORDER_THREAD, daemon=True).start()

    def __call__(self, named: frozenset[str]) -> None:
        ids = run_ids(named)
        if not ids:
            return
        try:
            self.queue.put_nowait(ids)
        except queue.Full:
            with self._lock:
                self.dropped += 1

    def flush(self, timeout: float) -> bool:
        """Wait at most `timeout` seconds until every queued refusal was written or failed."""
        deadline = time.monotonic() + timeout
        with self.queue.all_tasks_done:
            while self.queue.unfinished_tasks:
                left = deadline - time.monotonic()
                if left <= 0:
                    return False
                self.queue.all_tasks_done.wait(left)
        return True

    def _drain(self) -> None:
        while True:
            ids = self.queue.get()
            try:
                self.write(ids)
            except Exception as error:  # the record of a refusal never stops the worker
                with self._lock:
                    self.failed += 1
                log.warning("trace refusal not recorded", error=type(error).__name__)
            finally:
                self.queue.task_done()


def record_refusals(write: Write = write_to_ops) -> RefusalRecorder:
    """Record on the run's row every refusal this process's LangSmith uploads get from now on."""
    recorder = RefusalRecorder(write)
    on_refused_runs(recorder)
    return recorder
