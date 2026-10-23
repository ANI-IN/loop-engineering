"""Grader results as LangSmith feedback (key grader.<name>) on the run's trace.

Extended retention is always off: on the free plan, SDK feedback would otherwise upgrade the trace
to billed retention. The client is injected, so tests and runs without tracing pass None. The live
client sends from a background thread (observability.background): the SDK's own waits after a
refused upload happen there, never in the run.
"""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

import structlog

from datapilot.contracts import GraderResult
from datapilot.observability.background import background, bounded_client
from datapilot.settings import Settings, get_settings

log = structlog.get_logger("feedback")


class FeedbackClient(Protocol):
    def create_feedback(self, run_id: Any = None, key: str = "", **kwargs: Any) -> Any: ...


def langsmith_client(settings: Settings | None = None) -> FeedbackClient | None:
    settings = settings or get_settings()
    if not (settings.langsmith_tracing and settings.langsmith_api_key.get_secret_value()):
        return None
    # sent from a background thread: a slow or refusing LangSmith never holds up the run
    return background(
        bounded_client(
            api_key=settings.langsmith_api_key.get_secret_value(),
            api_url=settings.langsmith_endpoint,
        )
    )


def send_grader_feedback(
    client: FeedbackClient | None, trace_id: UUID, result: GraderResult
) -> None:
    if client is None:
        return
    try:
        client.create_feedback(
            run_id=trace_id,
            key=f"grader.{result.grader}",
            score=1.0 if result.passed else 0.0,
            comment=result.reason,
            extend_trace_retention=False,
        )
    except Exception as error:  # feedback is a record, never a reason to fail a run
        log.warning("grader feedback not sent", grader=result.grader, error=str(error))
