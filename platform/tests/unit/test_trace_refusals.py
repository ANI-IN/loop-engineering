"""The worker's record of a trace LangSmith refused for its monthly limit, on stand-ins (zero
tokens, no database): the logging filter hands the refused run ids on without blocking, and one
daemon thread writes them."""

from __future__ import annotations

import logging
import threading
import time
import uuid

import pytest

from datapilot.loop3_events import trace_refusals
from datapilot.observability import background

LIMIT = 'HTTPError(429, \'{"detail":"Monthly unique traces usage limit exceeded"}\')'


def _line(text: str) -> logging.LogRecord:
    return logging.LogRecord(background.SDK_LOGGER, logging.WARNING, "", 0, text, None, None)


def _refused(root: uuid.UUID, child: uuid.UUID) -> logging.LogRecord:
    """The SDK's line for one refused upload of a run and its child."""
    return _line(
        f"Failed to multipart ingest runs: {LIMIT}trace={root},id={root}; trace={root},id={child}"
    )


@pytest.fixture
def refusals(monkeypatch: pytest.MonkeyPatch) -> background.RefusalLog:
    """A fresh refusal log in place of the process's own, so no listener outlives a test."""
    log = background.RefusalLog()
    monkeypatch.setattr(background, "_refusals", log)
    return log


def test_a_listener_gets_the_ids_of_each_upload_refused_for_the_monthly_limit(refusals) -> None:
    seen: list[frozenset[str]] = []
    background.on_refused_runs(seen.append)
    background.on_refused_runs(seen.append)  # once per listener
    root, child = uuid.uuid4(), uuid.uuid4()
    refusals.filter(_refused(root, child))
    refusals.filter(_line(f"Failed to multipart ingest runs: HTTPError(429)trace={uuid.uuid4()}"))
    refusals.filter(_line("Failed to send compressed multipart ingest: connection reset"))
    assert seen == [frozenset({str(root), str(child)})]


def test_a_listener_that_raises_never_breaks_the_sdks_logging(refusals) -> None:
    def broken(named: frozenset[str]) -> None:
        raise RuntimeError("listener broken")

    background.on_refused_runs(broken)
    assert refusals.filter(_refused(uuid.uuid4(), uuid.uuid4()))
    assert refusals.refused == 1


def test_the_recorder_writes_each_refusal_from_its_own_thread(refusals) -> None:
    written: list[tuple[list[str], str]] = []
    recorder = trace_refusals.record_refusals(
        lambda ids: written.append((ids, threading.current_thread().name))
    )
    root, child = uuid.uuid4(), uuid.uuid4()
    refusals.filter(_refused(root, child))
    assert recorder.flush(timeout=5)
    assert written == [(sorted([str(root), str(child)]), trace_refusals.RECORDER_THREAD)]


def test_the_filter_never_waits_for_the_database() -> None:
    """The SDK logs on its background tracing thread; a slow write must not hold it up."""
    release = threading.Event()
    recorder = trace_refusals.RefusalRecorder(lambda ids: release.wait(), size=2)
    started = time.monotonic()
    for _ in range(5):  # one being written, two queued, two dropped
        recorder(frozenset({str(uuid.uuid4())}))
    assert time.monotonic() - started < 1
    deadline = time.monotonic() + 5
    while recorder.dropped < 2 and time.monotonic() < deadline:
        recorder(frozenset({str(uuid.uuid4())}))
    assert recorder.dropped >= 2
    release.set()
    assert recorder.flush(timeout=5)


def test_a_failed_write_is_counted_and_the_recorder_goes_on() -> None:
    calls: list[list[str]] = []

    def write(ids: list[str]) -> None:
        calls.append(ids)
        if len(calls) == 1:
            raise ConnectionError("database down")

    recorder = trace_refusals.RefusalRecorder(write)
    first, second = str(uuid.uuid4()), str(uuid.uuid4())
    recorder(frozenset({first}))
    recorder(frozenset({second}))
    assert recorder.flush(timeout=5)
    assert calls == [[first], [second]] and recorder.failed == 1


def test_only_well_formed_run_ids_are_written() -> None:
    run_id = uuid.uuid4()
    named = {str(run_id).upper(), "------------------------------------", "not-a-run"}
    assert trace_refusals.run_ids(named) == [str(run_id)]
    written: list[list[str]] = []
    recorder = trace_refusals.RefusalRecorder(written.append)
    recorder(frozenset({"------------------------------------"}))
    assert recorder.flush(timeout=5) and written == []
