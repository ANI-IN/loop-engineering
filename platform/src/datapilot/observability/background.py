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
"""

from __future__ import annotations

import queue
import threading
import time
import weakref
from typing import Any

import structlog

log = structlog.get_logger("feedback")

SENDER_THREAD = "langsmith-feedback"
QUEUE_SIZE = 1000
RETRY_AFTER_MAX_SECONDS = 1  # the SDK's own cap is 6 hours

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
