"""LangSmith uploads that never hold up a run: feedback from a background thread, and clients whose
waits after a refusal are short.

The free plan answers every upload with HTTP 429 once its monthly unique-trace limit is used up
(LangSmith's documented limits (usage and billing pages)). Two waits in the SDK follow from that:

- Feedback with extended retention off is one blocking request, and the SDK waits before it tries
  again: about 30 seconds, doubling, after a 429, and up to about 8 minutes while a trace it cannot
  find yet might still arrive. On a run's own thread that wait would stop the run. Here
  `BackgroundFeedback.create_feedback` only queues the call and returns at once; one daemon thread
  sends the queue, logs a failure by its type, and goes on. A full queue drops new feedback and
  counts it, and the process never waits for the thread when it exits.
- Under every request, the HTTP adapter tries a 429 three more times and sleeps for the server's
  Retry-After header, up to 6 hours each time. The background tracing thread is not a daemon, so a
  process exit waits for those sleeps. `bounded_client` builds every client this platform uses
  with the SDK's own retry settings except that Retry-After counts for at most
  RETRY_AFTER_MAX_SECONDS, and `use_for_tracing` makes it the client LangChain's tracer uses.

`flush` on a sender, and `traces.flush` for the whole process, wait no longer than their bound.

Once the monthly limit is used up, the SDK logs one warning per refused upload, hundreds in one
command. `bounded_client` also installs `RefusalLog` on the SDK's logger: the first refusal is one
short line, the rest are counted, and the count is one line when the process exits. The runs a
refusal for the monthly limit names (the SDK's line ends with "trace=<id>,id=<id>" for each run of
the refused upload) are kept, so the live smoke check can tell a trace LangSmith refused from one
that is missing for another reason. A process can also hand each such refusal on as it happens
(`on_refused_runs`): the worker records it on the run's row in ops, where another process (the live
smoke check) reads it.
"""

from __future__ import annotations

import atexit
import contextlib
import logging
import queue
import re
import threading
import time
import weakref
from collections.abc import Callable
from typing import Any

import structlog

log = structlog.get_logger("feedback")

SENDER_THREAD = "langsmith-feedback"
QUEUE_SIZE = 1000
RETRY_AFTER_MAX_SECONDS = 1  # the SDK's own cap is 6 hours
SDK_LOGGER = "langsmith.client"  # the SDK's client and its background tracing thread
MONTHLY_LIMIT_REFUSAL = "trace refused by LangSmith (monthly limit)"
# How the SDK names each run of an upload it could not send: "trace=<trace id>,id=<run id>".
REFUSED_RUN = re.compile(r"\b(?:trace|id)=([0-9a-fA-F-]{36})\b")


class RefusalLog(logging.Filter):
    """One line for the first upload LangSmith refused (HTTP 429), a count for the rest."""

    def __init__(self) -> None:
        super().__init__()
        self.refused = 0
        self.monthly_limit = False
        self.refused_runs: set[str] = set()  # trace and run ids of uploads refused for the limit
        # each gets the ids of one refused upload, on the SDK's thread, so it must not block
        self.listeners: list[Callable[[frozenset[str]], None]] = []
        self._lock = threading.Lock()

    @staticmethod
    def is_refusal(text: str) -> bool:
        lowered = text.lower()
        return "429" in text or "rate limit" in lowered or "usage limit" in lowered

    def filter(self, record: logging.LogRecord) -> bool:
        text = record.getMessage()
        if not self.is_refusal(text):
            return True
        limit = "usage limit" in text.lower()
        named = frozenset(i.lower() for i in REFUSED_RUN.findall(text)) if limit else frozenset()
        with self._lock:
            self.refused += 1
            first = self.refused == 1
            self.monthly_limit = self.monthly_limit or limit
            self.refused_runs.update(named)
            listeners = list(self.listeners)
        if named:
            for listener in listeners:
                with contextlib.suppress(Exception):  # a record of a refusal never breaks logging
                    listener(named)
        if not first:
            return False
        reason = "its monthly trace limit" if self.monthly_limit else "HTTP 429"
        record.msg = "LangSmith refused a trace upload (%s); later refusals are counted, not shown"
        record.args = (reason,)
        return True

    def refused_run(self, run_id: object) -> bool:
        """True when a refusal for the monthly limit named this run, or the trace it belongs to."""
        with self._lock:
            return str(run_id).lower() in self.refused_runs

    def summary(self) -> str | None:
        if self.refused < 2:
            return None
        limit = " for its monthly trace limit" if self.monthly_limit else ""
        return f"LangSmith refused {self.refused} trace uploads in this process{limit}"


_refusals = RefusalLog()


def collapse_refusals() -> RefusalLog:
    """Install the refusal filter on the SDK's logger, once per process."""
    logger = logging.getLogger(SDK_LOGGER)
    if _refusals not in logger.filters:
        logger.addFilter(_refusals)
        atexit.register(_log_summary)
    return _refusals


def _log_summary() -> None:
    if line := _refusals.summary():
        logging.getLogger("datapilot.langsmith").warning(line)


def monthly_limit_refused() -> bool:
    """True once LangSmith refused an upload of this process for its monthly trace limit."""
    return _refusals.monthly_limit


def on_refused_runs(listener: Callable[[frozenset[str]], None]) -> None:
    """Hand `listener` the run and trace ids of every upload LangSmith refuses for its monthly
    limit from now on (once per listener). It runs on the SDK's thread: it must only queue."""
    with _refusals._lock:
        if listener not in _refusals.listeners:
            _refusals.listeners.append(listener)


def trace_refused(run_id: object) -> bool:
    """True when LangSmith refused this run's own upload for its monthly trace limit; a trace
    missing for any other reason (a wrong project, a tracing bug) is not refused."""
    return _refusals.refused_run(run_id)


_senders: weakref.WeakSet[BackgroundFeedback] = weakref.WeakSet()


class BackgroundFeedback:
    """A feedback client (create_feedback) that never blocks or raises in the caller."""

    def __init__(self, client: Any, size: int = QUEUE_SIZE) -> None:
        self.client = client
        self.queue: queue.Queue[tuple[Any, str, dict[str, Any]]] = queue.Queue(maxsize=size)
        self.dropped = 0
        self.failed = 0
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        _senders.add(self)

    def create_feedback(self, run_id: Any = None, key: str = "", **kwargs: Any) -> None:
        self._start()
        try:
            self.queue.put_nowait((run_id, key, kwargs))
        except queue.Full:
            with self._lock:
                self.dropped += 1

    def flush(self, timeout: float) -> bool:
        """Wait until every queued feedback was sent or failed, at most `timeout` seconds; True
        when the queue is empty."""
        deadline = time.monotonic() + timeout
        with self.queue.all_tasks_done:
            while self.queue.unfinished_tasks:
                left = deadline - time.monotonic()
                if left <= 0:
                    return False
                self.queue.all_tasks_done.wait(left)
        return True

    def _start(self) -> None:
        with self._lock:
            if self._thread is None:
                self._thread = threading.Thread(target=self._send, name=SENDER_THREAD, daemon=True)
                self._thread.start()

    def _send(self) -> None:
        while True:
            run_id, key, kwargs = self.queue.get()
            try:
                self.client.create_feedback(run_id, key, **kwargs)
            except Exception as error:  # feedback is a record, never a reason to stop
                with self._lock:
                    self.failed += 1
                log.warning("feedback not sent", key=key, error=type(error).__name__)
            finally:
                self.queue.task_done()


def background(client: Any) -> BackgroundFeedback:
    """The client as a background sender (unchanged when it already is one)."""
    return client if isinstance(client, BackgroundFeedback) else BackgroundFeedback(client)


def senders() -> list[BackgroundFeedback]:
    """Every sender of this process, for the bounded flush at the end of a command."""
    return list(_senders)


def bounded_retry() -> Any:
    """The SDK's default transport retry (langsmith.client._default_retry_config), with each wait
    for a Retry-After header cut to RETRY_AFTER_MAX_SECONDS."""
    from langsmith.utils import LangSmithRetry

    return LangSmithRetry(
        total=3,
        status_forcelist=[429, 500, 502, 503, 504, 408, 425],
        backoff_factor=0.5,
        raise_on_redirect=False,
        raise_on_status=False,
        respect_retry_after_header=True,
        retry_after_max=RETRY_AFTER_MAX_SECONDS,
        allowed_methods=None,
    )


def bounded_client(**kwargs: Any) -> Any:
    """A langsmith.Client whose waits after a refused request are short (see the module), with the
    runtime description every trace carries made now, not on a run's thread."""
    from langsmith import Client

    describe_runtime()
    collapse_refusals()
    return Client(retry_config=bounded_retry(), **kwargs)


def describe_runtime() -> None:
    """Fill the SDK's caches of the runtime description that every trace carries. The first traced
    run of a process would otherwise make it on its own thread, starting child processes (`git
    describe --tags --always --dirty` for the revision, `uname -p` for the processor), which took
    more than a second on a busy machine with the repository on a Windows drive. Each value is
    cached for the life of the process, so this costs once, when a client is built."""
    from langchain_core.env import get_runtime_environment as langchain_runtime
    from langsmith import env

    env.get_runtime_environment()
    env.get_langchain_env_var_metadata()
    langchain_runtime()


def use_for_tracing(client: Any) -> None:
    """Make `client` the one LangChain's tracer and langsmith.trace use in this process (the SDK's
    public langsmith.configure), so their uploads have the short waits too."""
    import langsmith

    langsmith.configure(client=client)
