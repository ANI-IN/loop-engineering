"""A trace upload LangSmith refuses never slows, breaks, or fails a run (the owner's decision of 23
October 2026, after the free plan's monthly unique-trace limit answered every upload with HTTP 429).

The stand-in is a real langsmith.Client over a transport that refuses every request with 429, the
answer LangSmith gave that day, or that hangs. The SDK's own waits (it sleeps 30 seconds and more
after a 429 before trying again) are recorded instead of slept, so a test shows on which thread a
wait would have happened: never on a run's thread, only on the background sender's.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace

import pytest
import requests
from loop4_doubles import SESSION, ScriptedEvaluator, answered, item
from pydantic import SecretStr

from datapilot.contracts import GraderResult, Severity, Split
from datapilot.loop4_hill_climbing.experiment import ExperimentRunner
from datapilot.loop4_hill_climbing.measurement import Scheme
from datapilot.observability import background, traces

SCHEME = Scheme(holdout_repeats=3, holdout_pass_threshold=2, dev_regression_reruns=2)
REFUSAL = b'{"detail": "Monthly unique traces usage limit exceeded"}'


@pytest.fixture(autouse=True)
def fresh_refusal_log(monkeypatch: pytest.MonkeyPatch):
    """Each test counts its own refusals (review round 2): the process-wide log otherwise kept
    every refusal these tests provoke, so `make test` ended with "LangSmith refused 10 trace
    uploads in this process for its monthly trace limit" when no upload reached LangSmith, and a
    later test read the flag these tests set."""
    import logging

    logger = logging.getLogger(background.SDK_LOGGER)
    before = list(logger.filters)
    monkeypatch.setattr(background, "_refusals", background.RefusalLog())
    yield
    for added in [f for f in logger.filters if f not in before]:
        logger.removeFilter(added)


class Refusing(requests.Session):
    """Answers every request with 429 and a Retry-After of 30 seconds; with `hang`, first waits
    until released, like an upload that never completes."""

    def __init__(self, hang: threading.Event | None = None) -> None:
        super().__init__()
        self.calls: list[tuple[str, str]] = []
        self.hang = hang

    def request(self, method, url, *args, **kwargs):  # type: ignore[override]
        self.calls.append((method, str(url)))
        if self.hang is not None:
            self.hang.wait(60)
        response = requests.Response()
        response.status_code = 429
        response.reason = "Too Many Requests"
        response._content = REFUSAL
        response.headers["Retry-After"] = "30"
        response.url = str(url)
        response.request = requests.Request(method, str(url)).prepare()
        return response


@dataclass
class Waits:
    """Stands in for the time module inside langsmith.client: sleeps are recorded, not slept."""

    seen: list[tuple[str, float]] = field(default_factory=list)

    def sleep(self, seconds: float) -> None:
        self.seen.append((threading.current_thread().name, seconds))

    def __getattr__(self, name: str):
        return getattr(time, name)

    def outside_the_sender(self) -> list[tuple[str, float]]:
        return [(name, s) for name, s in self.seen if name != background.SENDER_THREAD]


@pytest.fixture
def waits(monkeypatch) -> Waits:
    import langsmith.client

    found = Waits()
    monkeypatch.setattr(langsmith.client, "time", found)
    return found


def refusing_client(session: requests.Session):
    """A client built the way the platform builds every client, over the stand-in transport."""
    return background.bounded_client(
        api_key="test-key", api_url="http://langsmith.test", session=session
    )


def test_a_traced_run_starts_no_process_on_its_own_thread(monkeypatch) -> None:
    """The SDK describes the runtime on the first traced run of a process: `git describe --dirty`
    and `uname -p` as child processes, on the run's thread, which took more than a second on a busy
    machine with the repository on a Windows drive. A client we build does that once, when it is
    built, so no run waits for it."""
    import platform

    from langchain_core import env as langchain_env
    from langchain_core.runnables import RunnableLambda
    from langsmith.env import _runtime_env
    from langsmith.run_helpers import tracing_context

    # as in a new process: nothing described yet, whatever ran earlier in this one
    for cached in (
        _runtime_env.get_runtime_environment,
        _runtime_env.get_langchain_env_var_metadata,
        _runtime_env._get_default_revision_id,
        langchain_env.get_runtime_environment,
    ):
        cached.cache_clear()
    monkeypatch.setattr(platform, "_uname_cache", None)
    client = refusing_client(Refusing())
    started: list[object] = []

    class NoProcess:
        def __init__(self, *args, **kwargs) -> None:
            started.append(args)
            raise OSError("a traced run must not start a process")

    monkeypatch.setattr(subprocess, "Popen", NoProcess)
    with tracing_context(enabled=True, client=client, project_name="datapilot-experiments"):
        assert RunnableLambda(lambda x: x + 1).invoke(1) == 2
    assert started == []


def _target(question: str, version: str):
    return answered("SELECT 1")


def _items():
    return [item("d1"), item("d2"), item("h1", Split.HOLDOUT), item("h2", Split.HOLDOUT)]


def _evaluator():
    return ScriptedEvaluator({"d1": [True], "d2": [False], "h1": [True] * 3, "h2": [False] * 3})


def test_a_refused_feedback_upload_never_holds_up_an_experiment(waits: Waits) -> None:
    session = Refusing()
    client = refusing_client(session)
    tracer = traces.FeedbackTracer(
        client, traces.TraceLinks(client, "datapilot-experiments", "https://smith.example")
    )
    runner = ExperimentRunner(_target, _evaluator(), SCHEME, tracer=tracer, trace_sample_rate=1.0)
    started = time.monotonic()
    result = runner.run(_items(), "v1", session_id=SESSION)
    assert time.monotonic() - started < 5
    assert result.passed("d1") and not result.passed("d2")
    assert result.passed("h1") and not result.passed("h2")
    assert result.tracer_errors == [], "a refused upload is not a tracer failure of the run"
    assert result.trace_links == {}, "no link to a trace LangSmith refused to look up"
    assert tracer.feedback.flush(timeout=5), "the sender drains, refused or not"
    assert any(url.endswith("/feedback") for _, url in session.calls), "it was sent and refused"
    assert waits.outside_the_sender() == [], "no wait on the experiment's own threads"


def test_grader_feedback_during_a_run_goes_through_the_background_sender(waits: Waits) -> None:
    from datapilot.loop2_verification.feedback import langsmith_client, send_grader_feedback

    settings = SimpleNamespace(
        langsmith_tracing=True,
        langsmith_api_key=SecretStr("test-key"),
        langsmith_endpoint="http://langsmith.test",
    )
    sender = langsmith_client(settings)  # type: ignore[arg-type]
    assert isinstance(sender, background.BackgroundFeedback)
    session = Refusing()
    sender = background.BackgroundFeedback(refusing_client(session))
    result = GraderResult(grader="row_count", passed=True, severity=Severity.INFO, reason="ok")
    started = time.monotonic()
    for _ in range(5):
        send_grader_feedback(sender, uuid.uuid4(), result)
    assert time.monotonic() - started < 1
    assert sender.flush(timeout=5)
    # each one sent, refused, and tried again by the SDK, on the sender's thread only
    assert len([u for _, u in session.calls if u.endswith("/feedback")]) >= 5
    assert waits.outside_the_sender() == []


def test_the_sender_never_raises_and_drops_what_it_cannot_hold() -> None:
    release = threading.Event()

    class Stuck:
        def __init__(self) -> None:
            self.sent = 0

        def create_feedback(self, run_id=None, key="", **kwargs):
            release.wait(30)
            self.sent += 1
            raise ConnectionError("LangSmith refused the upload")

    stuck = Stuck()
    sender = background.BackgroundFeedback(stuck, size=2)
    started = time.monotonic()
    for _ in range(10):
        sender.create_feedback(uuid.uuid4(), "execution_match", score=1)
    assert time.monotonic() - started < 1
    assert not sender.flush(timeout=0.2), "a stuck upload is given up on after the bound"
    assert sender.dropped >= 7
    release.set()
    assert sender.flush(timeout=5)
    assert sender.failed == stuck.sent and sender.failed <= 3


def test_a_refused_trace_upload_never_fails_a_run_and_the_flush_is_bounded(
    waits: Waits, monkeypatch
) -> None:
    from langchain_core.runnables import RunnableLambda
    from langsmith import run_trees
    from langsmith.run_helpers import tracing_context

    session = Refusing()
    client = refusing_client(session)
    monkeypatch.setattr(run_trees, "_CLIENT", client)  # the process's client LangChain flushes
    started = time.monotonic()
    with tracing_context(enabled=True, client=client, project_name="datapilot-experiments"):
        assert RunnableLambda(lambda x: x + 1).invoke(1) == 2
    assert time.monotonic() - started < 1, "the run never waits for LangSmith"
    started = time.monotonic()
    assert traces.flush(timeout=5)
    assert time.monotonic() - started < 5, "the flush keeps its bound"
    assert any("/runs" in url for _, url in session.calls), "the upload was tried and refused"
    assert all(name != threading.current_thread().name for name, _ in waits.seen)


def test_the_flush_at_the_end_of_a_command_waits_no_longer_than_its_bound(monkeypatch) -> None:
    from langchain_core.runnables import RunnableLambda
    from langsmith import run_trees
    from langsmith.run_helpers import tracing_context

    release = threading.Event()
    session = Refusing(hang=release)  # every request hangs until released
    client = refusing_client(session)
    monkeypatch.setattr(run_trees, "_CLIENT", client)
    try:
        started = time.monotonic()
        with tracing_context(enabled=True, client=client, project_name="datapilot-experiments"):
            assert RunnableLambda(lambda x: x).invoke(1) == 1
        assert time.monotonic() - started < 1, "the run never waits for the upload"
        deadline = time.monotonic() + 10
        while not session.calls and time.monotonic() < deadline:  # the upload has begun, and hangs
            time.sleep(0.05)
        assert session.calls
        assert client.tracing_queue.unfinished_tasks > 0, "the run's upload is still in flight"
        started = time.monotonic()
        assert traces.flush(timeout=0.5) is False, "it reports that not everything was sent"
        assert time.monotonic() - started < 2
    finally:
        release.set()


def test_a_flush_that_timed_out_never_reports_everything_sent(monkeypatch) -> None:
    """Client.flush returns at its timeout whether or not its queue drained; traces.flush must
    not take that return for success (it once did, by a race against its own deadline)."""
    import queue

    from langsmith import run_trees

    class InFlight:
        def __init__(self) -> None:
            self.tracing_queue: queue.Queue = queue.Queue()
            self.tracing_queue.put("a batch still being sent")

        def flush(self, timeout=None) -> None:
            return None  # gives up at once, as at its timeout

    monkeypatch.setattr(run_trees, "_CLIENT", InFlight())
    assert traces.flush(timeout=2) is False


@pytest.fixture
def refusing_server():
    """A local stand-in for LangSmith on 127.0.0.1: every request gets 429 with a Retry-After of
    30 seconds, the kind of answer that made the SDK's transport sleep for minutes or hours."""
    seen: list[str] = []

    class Refuse(BaseHTTPRequestHandler):
        def _refuse(self) -> None:
            self.rfile.read(int(self.headers.get("Content-Length") or 0))
            seen.append(self.path)
            self.send_response(429)
            self.send_header("Retry-After", "30")
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(REFUSAL)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(REFUSAL)
            self.close_connection = True

        do_GET = do_POST = do_PATCH = _refuse

        def log_message(self, *args) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Refuse)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}", seen
    finally:
        server.shutdown()


def test_every_client_waits_at_most_a_second_for_a_retry_after(refusing_server, monkeypatch):
    from langchain_core.runnables import RunnableLambda
    from langsmith import run_trees
    from langsmith.run_helpers import tracing_context

    url, seen = refusing_server
    client = background.bounded_client(api_key="test-key", api_url=url)
    assert client.session.adapters["http://"].max_retries.retry_after_max == 1
    monkeypatch.setattr(run_trees, "_CLIENT", client)
    with tracing_context(enabled=True, client=client, project_name="datapilot-experiments"):
        assert RunnableLambda(lambda x: x * 2).invoke(2) == 4
    started = time.monotonic()
    assert traces.flush(timeout=30), "the refused batch is given up after its retries"
    # the information request and the upload, four tries each a second apart, not 30 seconds each
    assert time.monotonic() - started < 15
    assert len([p for p in seen if p.startswith("/runs")]) >= 4


EXITING = """
import sys, time
from langchain_core.runnables import RunnableLambda
from langsmith.run_helpers import tracing_context
from datapilot.observability.background import bounded_client, use_for_tracing
client = bounded_client(api_key="test-key", api_url=sys.argv[1])
use_for_tracing(client)
with tracing_context(enabled=True, client=client, project_name="datapilot-experiments"):
    RunnableLambda(lambda x: x).invoke(1)
print("run done", flush=True)
"""


def test_a_process_whose_uploads_are_refused_exits_in_seconds(refusing_server, tmp_path) -> None:
    url, seen = refusing_server
    script = tmp_path / "exiting.py"
    script.write_text(EXITING, encoding="utf-8")
    clean = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("LANGSMITH_", "LANGCHAIN_", "OPENAI_"))
    }
    started = time.monotonic()
    done = subprocess.run(
        [sys.executable, str(script), url], env=clean, capture_output=True, text=True, timeout=120
    )
    assert done.returncode == 0 and "run done" in done.stdout, done.stderr[-2000:]
    # the SDK's own transport would sleep 3 times 30 seconds on the way out
    assert time.monotonic() - started < 45
    assert any(p.startswith("/runs") for p in seen), "it tried, was refused, and let go"


REFUSING_TWICE = """
import sys
from langchain_core.runnables import RunnableLambda
from langsmith.run_helpers import tracing_context
from datapilot.observability.background import bounded_client, use_for_tracing
client = bounded_client(api_key="test-key", api_url=sys.argv[1])
use_for_tracing(client)
for n in range(2):  # two uploads, each refused
    with tracing_context(enabled=True, client=client, project_name="datapilot-experiments"):
        RunnableLambda(lambda x: x).invoke(n)
    client.flush()
print("runs done", flush=True)
"""


def test_the_refusal_log_of_a_process_is_one_line_and_a_count(refusing_server, tmp_path) -> None:
    """Live, the SDK logged one warning per refused upload, hundreds per command (review round 1,
    F015). The first refusal is one short line, the rest are counted, and the count is one line
    at exit."""
    url, _seen = refusing_server
    script = tmp_path / "refusing_twice.py"
    script.write_text(REFUSING_TWICE, encoding="utf-8")
    clean = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("LANGSMITH_", "LANGCHAIN_", "OPENAI_"))
    }
    done = subprocess.run(
        [sys.executable, str(script), url], env=clean, capture_output=True, text=True, timeout=120
    )
    assert done.returncode == 0 and "runs done" in done.stdout, done.stderr[-2000:]
    lines = [line for line in done.stderr.splitlines() if line.strip()]
    raw = [line for line in lines if any(s in line for s in ("Failed to", "429", "Rate limit"))]
    assert raw == [], lines
    first = [line for line in lines if line.startswith("LangSmith refused a trace upload")]
    assert first == [
        "LangSmith refused a trace upload (its monthly trace limit); later refusals are counted, "
        "not shown"
    ]
    assert lines[-1].startswith("LangSmith refused ") and lines[-1].endswith(
        "trace uploads in this process for its monthly trace limit"
    )


def test_the_refusal_filter_names_the_monthly_limit_and_lets_other_lines_through() -> None:
    import logging

    log = background.RefusalLog()
    record = lambda text: logging.LogRecord("langsmith.client", 30, "", 0, text, None, None)  # noqa: E731
    assert log.filter(record("Failed to get info: a connection was reset"))
    assert log.summary() is None and not log.monthly_limit
    limit = 'HTTPError(429, \'{"detail":"Monthly unique traces usage limit exceeded"}\')'
    shown = [log.filter(record(f"Failed to multipart ingest runs: {limit}")) for _ in range(300)]
    assert shown == [True] + [False] * 299
    assert log.monthly_limit and log.summary() == (
        "LangSmith refused 300 trace uploads in this process for its monthly trace limit"
    )


def test_the_refusal_log_keeps_the_runs_it_refused_and_only_those() -> None:
    """Review round 2: one refusal for the monthly limit marked every missing trace of the
    command as refused, whatever the reason it was missing."""
    import logging

    log = background.RefusalLog()
    record = lambda text: logging.LogRecord("langsmith.client", 30, "", 0, text, None, None)  # noqa: E731
    root, child, other = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    limit = 'HTTPError(429, \'{"detail":"Monthly unique traces usage limit exceeded"}\')'
    ids = f"trace={root},id={root}; trace={root},id={child}"
    log.filter(record(f"Failed to multipart ingest runs: {limit}{ids}"))
    log.filter(record(f"Failed to multipart ingest runs: HTTPError(429)trace={other},id={other}"))
    assert log.refused_run(root) and log.refused_run(str(child).upper())
    assert not log.refused_run(other), "a 429 that did not name the monthly limit is no refusal"
    assert not log.refused_run(uuid.uuid4())


def test_a_trace_the_sdk_could_not_upload_is_known_by_its_run_id(refusing_server, monkeypatch):
    """The SDK's own refusal line, from a real upload to the refusing stand-in, names the run."""
    from langchain_core.runnables import RunnableLambda
    from langsmith import run_trees
    from langsmith.run_helpers import tracing_context

    url, _seen = refusing_server
    client = background.bounded_client(api_key="test-key", api_url=url)
    monkeypatch.setattr(run_trees, "_CLIENT", client)
    run_id = uuid.uuid4()
    with tracing_context(enabled=True, client=client, project_name="datapilot-experiments"):
        RunnableLambda(lambda x: x).invoke(1, config={"run_id": run_id})
    assert traces.flush(timeout=30)
    assert background.trace_refused(run_id) and not background.trace_refused(uuid.uuid4())


def test_a_check_gives_up_on_trace_links_quickly_once_traces_are_refused(monkeypatch) -> None:
    from datapilot.assignments import live
    from datapilot.observability import background as module

    class NotFound:
        reads = 0

        def read_run(self, trace_id):
            from langsmith.utils import LangSmithNotFoundError

            NotFound.reads += 1
            raise LangSmithNotFoundError("run not found")

    settings = SimpleNamespace(
        langsmith_project="datapilot-live",
        langsmith_api_key=SecretStr("test-key"),
        langsmith_endpoint="http://langsmith.test",
    )
    monkeypatch.setattr(live, "get_settings", lambda: settings)
    monkeypatch.setattr(module, "bounded_client", lambda **kwargs: NotFound())
    monkeypatch.setattr(live.time, "sleep", lambda seconds: None)
    monkeypatch.setitem(live._LOOKUPS, "gave_up", False)
    first = live.trace_link("one", tries=10)
    assert "not found" in first and NotFound.reads == 10
    second = live.trace_link("two", tries=10)
    assert "not found" in second and NotFound.reads == 11, "later lookups try once"


def test_a_failed_link_lookup_is_not_tried_again_on_every_run() -> None:
    class Down:
        def __init__(self) -> None:
            self.calls = 0

        def read_project(self, **kwargs):
            self.calls += 1
            raise ConnectionError("LangSmith is not answering")

        def create_project(self, *args, **kwargs):
            self.calls += 1
            raise ConnectionError("LangSmith is not answering")

    down = Down()
    links = traces.TraceLinks(down, "datapilot-live", "https://smith.example")
    assert [links.url(uuid.uuid4()) for _ in range(20)] == [None] * 20
    assert links.project_url() is None
    assert down.calls == 2, "one lookup, then no link until the retry interval has passed"
