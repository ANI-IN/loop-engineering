"""The router: a fixed table from event type to handler, queue, and policy.

Deliberately not an agent. Which code handles an event must be predictable and auditable, so it is
a lookup, never a model's choice.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from datapilot.config import pack_config
from datapilot.contracts import EventType
from datapilot.loop3_events import extension


@dataclass(frozen=True)
class Route:
    handler: str  # "question", "export", "digest", "defense_check", or "job:<name>"
    queue: str
    export: bool = False


ROUTES: dict[EventType, Route] = {
    EventType.QUESTION_ASKED: Route(handler="question", queue="default"),
    EventType.EXPORT_REQUESTED: Route(handler="export", queue="default", export=True),
    EventType.DIGEST_REQUESTED: Route(handler="digest", queue="scheduled"),
}
# A question event whose payload names a deterministic defense check (a demo of the verification
# loop's layers) runs that check instead of the analyst.
DEFENSE_CHECK = Route(handler="defense_check", queue="default")


def route(event_type: str, payload: dict[str, Any]) -> Route:
    kind = EventType(event_type)
    if kind is EventType.QUESTION_ASKED and payload.get("check"):
        return DEFENSE_CHECK
    if kind is EventType.DIGEST_REQUESTED and payload.get("job"):
        return job_route(str(payload["job"]))
    return ROUTES[kind]


def job_route(job: str) -> Route:
    """A scheduled job event runs the job's handler on the queue its table entry names."""
    queue = extension.JOB_QUEUES.get(job)
    if queue is None:
        raise KeyError(f"no route for the scheduled job {job!r}: add it to the router's table")
    return Route(handler=f"job:{job}", queue=queue)


def digest_question(day: str) -> str:
    """The selected pack's digest question (digest.question in pack.yaml) for one day."""
    return str(pack_config()["digest"]["question"]).format(day=day)


def family_keywords() -> list[tuple[str, str]]:
    """(pattern, family) from the selected pack's autonomy.family_keywords, first match wins."""
    table = pack_config()["autonomy"].get("family_keywords") or []
    return [(str(row["pattern"]), str(row["family"])) for row in table]


def question_for(event_type: str, payload: dict[str, Any]) -> str:
    if EventType(event_type) is EventType.DIGEST_REQUESTED and payload.get("job"):
        return str(payload.get("question") or f"{payload['job']} for {payload.get('day', '')}")
    if EventType(event_type) is EventType.DIGEST_REQUESTED:
        return digest_question(str(payload.get("day", "")))
    return str(payload.get("question", ""))


def metric_family(question: str, payload: dict[str, Any], families: list[str]) -> str | None:
    named = payload.get("metric_family")
    if named in families:
        return str(named)
    for pattern, family in family_keywords():
        if family in families and re.search(pattern, question, re.IGNORECASE):
            return family
    return None
