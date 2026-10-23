"""Trace links and tracing setup for processes outside Compose (preflight, calibration, the
hill-climbing runner).

- `export_tracing_env` copies the LangSmith settings from .env into the process environment,
  where LangChain's tracer reads them; values are never printed. It and `live_links` make a
  bounded client (observability.background) the process's tracing client.
- `TraceLinks` turns a run id into its LangSmith link. The project id and the workspace id are
  looked up once per process (a connection detail, not a result); after a failed lookup there is
  no link, and no new try, for LINK_RETRY_SECONDS, so a LangSmith that is down never slows each
  run.
- `FeedbackTracer` implements the experiment runner's RunTracer on the analyst's own trace: it adds
  the local pass or fail as feedback, always with extend_trace_retention=False, from the background
  sender (observability.background), and returns the link the console shows. The runner calls it
  only for the runs its sample traces (observability.sampling).
- `flush` sends what the process traced at the end of a command, waiting at most FLUSH_SECONDS.
- `ModelIds` records the model id the API returns on every call, for the calibration report.
"""

from __future__ import annotations

import os
import threading
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from datapilot.loop4_hill_climbing.experiment import RunRecord
from datapilot.observability.background import (
    BackgroundFeedback,
    background,
    bounded_client,
    senders,
    use_for_tracing,
)
from datapilot.settings import Settings

DEVELOPMENT_PROJECT = "datapilot-development"  # separate from the class and experiment projects
PROJECT_VARIABLE = "DATAPILOT_DEVELOPMENT_PROJECT"
TRACK_VARIABLE = "DATAPILOT_TRACE_TRACK"  # such as calibration
FEATURE_VARIABLE = "DATAPILOT_TRACE_FEATURE"  # such as live-smoke
FLUSH_SECONDS = 15.0  # the longest the end of a command waits for LangSmith
LINK_RETRY_SECONDS = 300.0  # after a failed project lookup: no link, and no new try, this long


def development_project() -> str:
    return os.environ.get(PROJECT_VARIABLE) or DEVELOPMENT_PROJECT


def development_tags(feature: str | None = None, track: str | None = None) -> list[str]:
    """track:<track> and feature:<feature> for a live development run; the environment names them
    (DATAPILOT_TRACE_TRACK, DATAPILOT_TRACE_FEATURE), and the arguments are the defaults (the
    calling track's own tools pass their track)."""
    tags = []
    if chosen_track := os.environ.get(TRACK_VARIABLE) or track:
        tags.append(f"track:{chosen_track}")
    if chosen := os.environ.get(FEATURE_VARIABLE) or feature:
        tags.append(f"feature:{chosen}")
    return tags


def export_tracing_env(settings: Settings, project: str) -> bool:
    """Turn LangSmith tracing on for this process when a key is set; True when it is on."""
    key = settings.langsmith_api_key.get_secret_value()
    enabled = bool(settings.langsmith_tracing and key)
    os.environ["LANGSMITH_TRACING"] = "true" if enabled else "false"
    if enabled:
        os.environ["LANGSMITH_API_KEY"] = key
        os.environ["LANGSMITH_ENDPOINT"] = settings.langsmith_endpoint
        os.environ["LANGSMITH_PROJECT"] = project
        use_for_tracing(bounded_client(api_key=key, api_url=settings.langsmith_endpoint))
    return enabled


def web_url(endpoint: str) -> str:
    """https://api.smith.langchain.com -> https://smith.langchain.com (and the regional hosts)."""
    return endpoint.rstrip("/").removesuffix("/api/v1").replace("api.smith.", "smith.", 1)


@dataclass
class TraceLinks:
    client: Any  # langsmith.Client
    project: str
    web: str
    _ids: tuple[UUID, UUID] | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _failed_at: float | None = None

    def _project_ids(self) -> tuple[UUID, UUID]:
        with self._lock:
            if self._ids is None:
                failed = self._failed_at
                if failed is not None and time.monotonic() - failed < LINK_RETRY_SECONDS:
                    raise LookupError("the LangSmith project lookup failed a moment ago")
                try:
                    self._ids = self._look_up()
                except Exception:
                    self._failed_at = time.monotonic()
                    raise
            return self._ids

    def _look_up(self) -> tuple[UUID, UUID]:
        try:
            found = self.client.read_project(project_name=self.project)
        except Exception:  # a new project: create it so links work from the first run
            found = self.client.create_project(self.project, upsert=True)
        return (found.tenant_id, found.id)

    def url(self, run_id: UUID | str) -> str | None:
        try:
            tenant, project = self._project_ids()
        except Exception:  # no link is better than a failed run
            return None
        return f"{self.web}/o/{tenant}/projects/p/{project}/r/{run_id}?poll=true"

    def project_url(self) -> str | None:
        try:
            tenant, project = self._project_ids()
        except Exception:
            return None
        return f"{self.web}/o/{tenant}/projects/p/{project}"


@dataclass
class FeedbackTracer:
    """Implements experiment.RunTracer on the analyst's own trace (its run id is the trace id)."""

    client: Any
    links: TraceLinks
    feedback: BackgroundFeedback = field(init=False)

    def __post_init__(self) -> None:
        self.feedback = background(self.client)

    def trace(self, record: RunRecord, *, experiment_id: UUID) -> str | None:
        self.feedback.create_feedback(
            record.run_id,
            "execution_match",
            score=int(record.result.passed),
            comment=record.result.reason,
            trace_id=record.run_id,
            extend_trace_retention=False,
        )
        return self.links.url(record.run_id)


def live_links(settings: Settings, project: str) -> tuple[Any, TraceLinks] | None:
    """The LangSmith client and the link builder, or None when tracing is off."""
    key = settings.langsmith_api_key.get_secret_value()
    if not (settings.langsmith_tracing and key):
        return None
    client = bounded_client(api_key=key, api_url=settings.langsmith_endpoint)
    use_for_tracing(client)  # the process's traces get the same short waits after a refusal
    return client, TraceLinks(client, project, web_url(settings.langsmith_endpoint))


def flush(timeout: float = FLUSH_SECONDS) -> bool:
    """Send every trace and feedback of this process (end of a command), waiting at most `timeout`
    seconds; True when everything went out in time. A refused or hanging upload never holds up the
    end of a command: the waiting happens on a daemon thread, and what is left is given up."""
    from langsmith import run_trees
    from langsmith.run_helpers import get_tracing_context

    done = threading.Event()
    # the process's client (the one LangChain's tracer uses) and any the caller's context names
    clients = {id(c): c for c in (run_trees._CLIENT, get_tracing_context()["client"]) if c}

    def drain() -> None:
        deadline = time.monotonic() + timeout
        drained = True
        for client in clients.values():
            # Client.flush returns at its timeout whether or not the queue is empty: what is left
            # unfinished (a batch still being sent counts until it is done) decides
            client.flush(timeout=max(deadline - time.monotonic(), 0.0))
            queue = getattr(client, "tracing_queue", None)
            drained = drained and (queue is None or queue.unfinished_tasks == 0)
        sent = [sender.flush(max(deadline - time.monotonic(), 0.0)) for sender in senders()]
        if drained and all(sent):
            done.set()

    threading.Thread(target=drain, name="langsmith-flush", daemon=True).start()
    return done.wait(timeout)


class ModelIds:
    """Counts the model ids the API reports on each response, by component."""

    def __init__(self) -> None:
        self.seen: Counter[tuple[str, str]] = Counter()
        self._lock = threading.Lock()

    def for_component(self, component: str) -> _ComponentIds:
        return _ComponentIds(self, component)

    def add(self, component: str, model: str) -> None:
        with self._lock:
            self.seen[(component, model)] += 1

    def as_rows(self) -> list[dict[str, Any]]:
        return [
            {"component": c, "model_id": m, "calls": n} for (c, m), n in sorted(self.seen.items())
        ]


class _ComponentIds(BaseCallbackHandler):
    def __init__(self, ids: ModelIds, component: str) -> None:
        self.ids, self.component = ids, component

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        for generations in response.generations:
            for generation in generations:
                message = getattr(generation, "message", None)
                meta = getattr(message, "response_metadata", None) or {}
                model = meta.get("model_name") or meta.get("model")
                if model:
                    self.ids.add(self.component, str(model))
