"""Every action the console takes is one HTTP call to the DataPilot api, made here.

The console reads live state from the ops schema and never imports a loop package; anything that
changes state goes through these calls. Every request is built from a datapilot.contracts.api model
and every reply is validated against the response model its endpoint declares in
contracts.api.ENDPOINTS, the one table the api and the contract test also use. Each call sends a
fresh event id, so a demo always starts a new run.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Literal, TypeVar, cast

import httpx

from datapilot import demo_questions, finale, planted
from datapilot.contracts import api as contract
from datapilot.contracts.lifecycle import EventType
from datapilot.observability import spend
from datapilot.settings import get_settings

API_DOWN = "The api did not answer. Start it with make up."
TIMEOUT_SECONDS = 2.0

# The demo inputs the console sends. They are questions, never answers. Each demo's question comes
# from datapilot.demo_questions, the table `make demo NAME=` reads too; so does the export request.
SPINE_QUESTION = demo_questions.SPINE_QUESTION
OVERBROAD_RULE = "knowledge-v2-overbroad"
# Improve > Run the naive analyzer (planted): the naive analyzer demo's planted half, the console's
# copy of `make demo NAME=improve-naive-analyzer-blocked PLANTED=1`.
NAIVE_ANALYZER_DEMO = "improve-naive-analyzer-blocked"

# Events > Send webhook question starts two registry demos: the event loop's webhook question, and
# the finale's spine question once the finale is the demo being shown.
WEBHOOK_DEMO = "events-webhook-question"
FINALE_DEMO = finale.FINALE_DEMO
UNATTENDED = "unattended"


def webhook_demo(family_levels: dict[str, str], state: finale.FinaleState | None = None) -> str:
    """The demo the webhook button starts: the finale once a version is approved for promotion or
    was promoted in this live session (by the gate or the class-day safeguard), whether a family
    cleared under it or none did, and once any family is cleared for the unattended level; the
    event loop's webhook question before that."""
    if state is not None and state.finale_due:
        return FINALE_DEMO
    return FINALE_DEMO if UNATTENDED in family_levels.values() else WEBHOOK_DEMO


def webhook_hold(demo: str, state: finale.FinaleState) -> str | None:
    """Why the webhook button sends nothing now, or None. While an approved version's promotion is
    pending it never sends: pressed then, it would ask the event loop's question, or the finale
    under the previous version. The finale also waits for the kill switch to be released and the
    unattended level to be set, as `make demo NAME=improve-cleared-unattended` does."""
    if demo == FINALE_DEMO:
        return finale.refusal(state)
    return finale.waiting_for_promotion(state)


Reply = TypeVar("Reply", bound=contract.Response)


class ApiError(RuntimeError):
    """The api did not answer, or refused the request; the message says what to do next."""


@dataclass(frozen=True)
class ApiClient:
    base_url: str
    timeout: float = TIMEOUT_SECONDS
    http: httpx.Client | None = None  # an injected client (tests: the api app's TestClient)
    # The ledger activity of the runs this console starts (None: the worker's own).
    spend_activity: str | None = None

    @classmethod
    def from_settings(cls, session_purpose: str | None = None) -> ApiClient:
        """The api of this machine; with the open live session's purpose, the worker records the
        console's runs under that session's line (spend.starter_activity)."""
        activity = spend.starter_activity(session_purpose, "console") if session_purpose else None
        return cls(get_settings().datapilot_api_url.rstrip("/"), spend_activity=activity)

    def send(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None,
        extra_headers: dict[str, str] | None = None,
    ) -> tuple[int, Any]:
        """One raw request: (status code, decoded json). The contract test's seam."""
        headers = {spend.ACTIVITY_HEADER: self.spend_activity} if self.spend_activity else {}
        headers.update(extra_headers or {})
        if self.http is not None:
            response = self.http.request(method, path, json=body, headers=headers)
        else:
            with httpx.Client(base_url=self.base_url, timeout=self.timeout) as client:
                response = client.request(method, path, json=body, headers=headers)
        try:
            data = response.json() if response.content else {}
        except ValueError:
            data = {"detail": response.text}
        return response.status_code, data

    def _call(
        self,
        method: str,
        path: str,
        expect: type[Reply],
        request: contract.Request | None = None,
        headers: dict[str, str] | None = None,
    ) -> Reply:
        entry = contract.endpoint(method, path)
        if entry.response is not expect or (entry.request is None) != (request is None):
            raise TypeError(f"{method} {path} does not match contracts.api.ENDPOINTS")
        body = request.model_dump(mode="json") if request is not None else None
        try:
            status, data = self.send(method, path, body, headers)
        except httpx.HTTPError as error:
            raise ApiError(API_DOWN) from error
        if status >= 400:
            detail = str(data.get("detail", "") if isinstance(data, dict) else data)[:300]
            raise ApiError(f"The api refused the request ({status}): {detail or 'no detail'}")
        return cast(Reply, entry.response.model_validate(data))

    # --- health ----------------------------------------------------------------------------
    def healthy(self) -> bool:
        try:
            self._call("GET", "/health", contract.Health)
        except ApiError:
            return False
        return True

    # --- events ----------------------------------------------------------------------------
    def send_event(
        self, event_type: EventType, payload: dict[str, Any], *, event_id: str | None = None
    ) -> contract.EventSubmitted:
        request = contract.EventIn(
            event_id=event_id or new_event_id(str(payload.get("demo_name", "console"))),
            type=event_type,
            source="console",
            payload=payload,
        )
        return self._call("POST", "/events", contract.EventSubmitted, request)

    def ask(self, question: str, demo_name: str | None) -> contract.EventSubmitted:
        """Ask a question; `demo_name` is None for a typed question no registry demo asks."""
        payload = {"question": question}
        if demo_name is not None:
            payload["demo_name"] = demo_name
        return self.send_event(EventType.QUESTION_ASKED, payload)

    def ask_demo(self, demo_name: str) -> contract.EventSubmitted:
        """Start a registry demo with exactly the question `make demo NAME=` sends."""
        return self.ask(demo_questions.question_for(demo_name), demo_name)

    def request_export(self) -> contract.EventSubmitted:
        """Start the approval demo with exactly the export request `make demo NAME=` sends."""
        payload = {
            "question": demo_questions.EXPORT_QUESTION,
            "demo_name": "events-approval-survives-restart",
        }
        return self.send_event(EventType.EXPORT_REQUESTED, payload)

    def run_digest(self, day: str, session_id: str) -> contract.EventSubmitted:
        # One digest per business day and live session: a second click is absorbed as a duplicate.
        payload = {"day": day, "demo_name": "events-digest-now"}
        event_id = f"digest:{day}:{session_id}"
        return self.send_event(EventType.DIGEST_REQUESTED, payload, event_id=event_id)

    def send_three_times(self, question: str) -> list[contract.EventSubmitted]:
        event_id = new_event_id("events-duplicate-events")
        payload = {"question": question, "demo_name": "events-duplicate-events"}
        return [
            self.send_event(EventType.QUESTION_ASKED, payload, event_id=event_id) for _ in range(3)
        ]

    # --- demo triggers ---------------------------------------------------------------------
    def demo(
        self, name: Literal["large-query", "malicious-sql", "cartesian-query", "failing-grader"]
    ) -> contract.EventSubmitted:
        return self._call("POST", f"/demo/{name}", contract.EventSubmitted)

    # --- human controls --------------------------------------------------------------------
    def decide(
        self, run_id: str, decision: Literal["approve", "reject"]
    ) -> contract.ApprovalDecided:
        request = contract.ApprovalIn(decision=decision, decided_by="console")
        return self._call("POST", f"/approvals/{run_id}", contract.ApprovalDecided, request)

    def kill_switch(self, action: Literal["arm", "engage", "release"]) -> contract.KillSwitchState:
        request = contract.KillSwitchIn(action=action, by="console")
        return self._call("POST", "/control/kill-switch", contract.KillSwitchState, request)

    def stop_all(self) -> contract.KillSwitchState:
        """The status line's second click: the api arms, then engages, the kill switch."""
        self.kill_switch("arm")
        return self.kill_switch("engage")

    def set_autonomy(
        self, level: Literal["report_only", "assisted", "unattended"]
    ) -> contract.AutonomyState:
        """The system's autonomy level, set by a person (the api refuses while the kill switch is
        engaged); the finale needs the unattended level."""
        request = contract.AutonomyIn(level=contract.AutonomyLevel(level), by="console")
        return self._call("POST", "/control/autonomy", contract.AutonomyState, request)

    def restart_worker(self) -> contract.RestartRequested:
        return self._call("POST", "/control/restart-worker", contract.RestartRequested)

    # --- hill-climbing loop ----------------------------------------------------------------
    def run_experiment(
        self, target: Literal["active", "candidate"], *, plus_rule: str | None = None
    ) -> contract.ImprovementRequestOut:
        request = contract.ExperimentIn(
            target=target, plus_rule=plus_rule, split="all", requested_by="console"
        )
        return self._call("POST", "/experiments/run", contract.ImprovementRequestOut, request)

    def run_analyzer(self) -> contract.ImprovementRequestOut:
        request = contract.AnalyzerIn(requested_by="console")
        return self._call("POST", "/analyzer/run", contract.ImprovementRequestOut, request)

    def run_naive_analyzer(self) -> list[contract.ImprovementRequestOut]:
        """The naive analyzer demo's planted half, as `make demo NAME=improve-naive-analyzer-blocked
        PLANTED=1` queues it: the analyzer, then the candidate experiment, each with the demo's
        own flags in the planted header and the demo's name beside them (planted.header), so the
        flags are on for these two requests alone. The api takes them only while demo controls
        are allowed (DATAPILOT_ALLOW_DEMO_CONTROLS)."""
        flags = planted.header(planted.for_one_run(NAIVE_ANALYZER_DEMO), demo=NAIVE_ANALYZER_DEMO)
        analyzer = contract.AnalyzerIn(requested_by="console")
        candidate = contract.ExperimentIn(target="candidate", requested_by="console")
        return [
            self._call("POST", "/analyzer/run", contract.ImprovementRequestOut, analyzer, flags),
            self._call(
                "POST", "/experiments/run", contract.ImprovementRequestOut, candidate, flags
            ),
        ]

    def approve_version(self, version: str) -> contract.KnowledgeApproved:
        request = contract.KnowledgeApprovalIn(approved_by="console")
        path = f"/knowledge/{version}/approve"
        return self._call("POST", path, contract.KnowledgeApproved, request)


def new_event_id(demo_name: str) -> str:
    return f"console:{demo_name}:{uuid.uuid4().hex[:12]}"
