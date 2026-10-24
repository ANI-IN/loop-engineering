"""Triggering a registry demo through the api, exactly as the console or `make demo NAME=` does.

Each trigger sends fresh events (a new event id every time), so every trigger is a new live run;
the deterministic digest id still absorbs a repeated delivery within one trigger. Every request
body is built from a datapilot.contracts.api model.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Protocol

from datapilot.business_date import today as business_day
from datapilot.business_date import yesterday as business_yesterday
from datapilot.contracts.api import AnalyzerIn, EventIn, ExperimentIn, KillSwitchIn
from datapilot.contracts.registries import Demo
from datapilot.demo_questions import EXPORT_QUESTION, question_for
from datapilot.loop3_events.scheduler import digest_event_id

DEMO_POSTS = {
    "/demo/large-query",
    "/demo/malicious-sql",
    "/demo/cartesian-query",
    "/demo/failing-grader",
}
# The naive analyzer demo queues both of its steps: its blocked verdict comes from the candidate
# experiment, and the runner takes requests in the order they were made.
ANALYZER_THEN_CANDIDATE = "POST /analyzer/run, then POST /experiments/run (the candidate)"


class Client(Protocol):
    def post(self, url: str, **kwargs: Any) -> Any: ...

    def get(self, url: str, **kwargs: Any) -> Any: ...


@dataclass
class Triggered:
    demo: str
    run_ids: list[str] = field(default_factory=list)  # ops.runs ids
    request_ids: list[str] = field(default_factory=list)  # ops.improvement_requests ids


def _ok(response: Any) -> dict[str, Any]:
    response.raise_for_status()
    return response.json()


def _event(
    client: Client, demo: Demo, type: str, payload: dict[str, Any], event_id: str = ""
) -> str:
    body = EventIn(
        event_id=event_id or f"demo:{demo.id}:{uuid.uuid4().hex[:12]}",
        type=type,  # type: ignore[arg-type]
        source="demo",
        payload={"demo_name": demo.id, **payload},
    )
    return str(_ok(client.post("/events", json=body.model_dump(mode="json")))["run_id"])


def _wait_until_running(client: Client, run_id: str, seconds: float) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if _ok(client.get(f"/runs/{run_id}"))["status"] in ("running", "verifying"):
            return
        time.sleep(0.5)


def trigger(client: Client, demo: Demo, *, wait_running_seconds: float = 60.0) -> Triggered:
    api = demo.trigger.api or ""
    done = Triggered(demo.id)
    question = question_for(demo.id)  # the console's buttons read the same table
    if api.startswith("POST /demo/"):
        path = api.split()[1]
        if path not in DEMO_POSTS:
            raise KeyError(f"{demo.id}: no demo endpoint {path}")
        done.run_ids.append(str(_ok(client.post(path, json={}))["run_id"]))
    elif api == "POST /events (question.asked)":
        done.run_ids.append(_event(client, demo, "question.asked", {"question": question}))
    elif api == "POST /events (export.requested)":
        done.run_ids.append(_event(client, demo, "export.requested", {"question": EXPORT_QUESTION}))
    elif api == "POST /events (digest.requested)":
        event_id = digest_event_id(business_day(), uuid.uuid4().hex[:8])
        done.run_ids.append(
            _event(client, demo, "digest.requested", {"day": str(business_yesterday())}, event_id)
        )
    elif api == "POST /events (same event_id three times)":
        event_id = f"demo:{demo.id}:{uuid.uuid4().hex[:12]}"
        runs = [
            _event(client, demo, "question.asked", {"question": question}, event_id)
            for _ in range(3)
        ]
        done.run_ids.append(runs[0])
        digest_id = digest_event_id(business_day(), uuid.uuid4().hex[:8])
        for _ in range(2):
            _event(client, demo, "digest.requested", {"day": str(business_yesterday())}, digest_id)
    elif api == "POST /control/kill-switch":
        run_id = _event(client, demo, "question.asked", {"question": question})
        done.run_ids.append(run_id)
        _wait_until_running(client, run_id, wait_running_seconds)
        for action in ("arm", "engage"):
            body = KillSwitchIn(action=action, by="demo")  # type: ignore[arg-type]
            _ok(client.post("/control/kill-switch", json=body.model_dump(mode="json")))
    elif api.startswith("POST /experiments/run"):
        experiment = ExperimentIn(
            target="candidate" if "candidate" in demo.id else "active",
            plus_rule="over-broad" if "over-broad rule" in api else None,
            requested_by="demo",
        )
        sent = client.post("/experiments/run", json=experiment.model_dump(mode="json"))
        done.request_ids.append(str(_ok(sent)["request_id"]))
    elif api in ("POST /analyzer/run", ANALYZER_THEN_CANDIDATE):
        sent = client.post("/analyzer/run", json=AnalyzerIn(requested_by="demo").model_dump())
        done.request_ids.append(str(_ok(sent)["request_id"]))
        if api == ANALYZER_THEN_CANDIDATE:  # the runner takes it after the analyzer, on its draft
            experiment = ExperimentIn(target="candidate", requested_by="demo")
            sent = client.post("/experiments/run", json=experiment.model_dump(mode="json"))
            done.request_ids.append(str(_ok(sent)["request_id"]))
    else:
        raise KeyError(f"{demo.id}: no trigger for {api!r}")
    return done
