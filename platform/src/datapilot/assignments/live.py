"""Live steps through the real api, and the evidence each one carries: the run's live stamp and its
LangSmith trace link. Every run here is new: a fresh event id each time, never an earlier result."""

from __future__ import annotations

import contextlib
import threading
import time
import uuid
from collections.abc import Callable, Iterator, Sequence
from typing import Any

import httpx

from datapilot.assignments.cost import Cap, CapReached
from datapilot.assignments.report import LiveRun, Stop
from datapilot.contracts import TERMINAL, AnswerEnvelope, RunEventKind, RunStatus
from datapilot.contracts.api import (
    ApprovalIn,
    AutonomyIn,
    ControlState,
    EventIn,
    EventSubmitted,
    KillSwitchIn,
    RunDetail,
)
from datapilot.observability import spend
from datapilot.settings import get_settings

BY = "make check-assignment"
WAITING = TERMINAL | {RunStatus.AWAITING_APPROVAL}
_LOOKUPS = {"gave_up": False}  # a trace lookup of this process found nothing after every try
# A run in one of these can still make a model call; after a stop at the spend cap, the kill switch
# stays engaged until none of the check's runs is in one.
UNDER_WAY = frozenset(
    {RunStatus.RECEIVED, RunStatus.QUEUED, RunStatus.RUNNING, RunStatus.VERIFYING}
)


def event_id(slug: str, what: str) -> str:
    return f"assignment-check:{slug}:{what}:{uuid.uuid4().hex[:12]}"


class Api:
    def __init__(self, url: str, cap: Cap | None = None, *, slug: str = "") -> None:
        # the worker records the checked runs' calls under this command's activity
        self.http = httpx.Client(base_url=url, timeout=30, headers=spend.activity_headers())
        self._setup(cap, slug)

    def _setup(self, cap: Cap | None, slug: str = "") -> None:
        self.cap = cap  # set by the live gate; None until then
        self.slug = slug  # the assignment, for the reset command a stop prints
        self.started: set[str] = set()  # the runs this check started
        # Runs in this process (Assignment 4's benchmark) stop at the kill switch too: at the cap,
        # it is engaged even when the check started no run in the workers.
        self.in_process = False
        self.engaged_at_cap = False
        self.engaged_by_check = False  # the check's own kill-switch step engaged it
        self.level_before: str | None = None  # the autonomy level when the cap engaged the switch
        self.halt_error = ""
        self._halting = threading.Lock()

    def guard(self) -> None:
        """Before each new run and while waiting for one: at the spend cap, engage the kill switch
        once (when the check has runs of its own, in the workers or in this process) and raise
        CapReached."""
        if self.cap is None:
            return
        try:
            self.cap.check()
        except CapReached:
            self._halt()
            raise

    def _halt(self) -> None:
        with self._halting:
            if self.engaged_at_cap or self.halt_error or not (self.started or self.in_process):
                return
            try:
                control = self.control()
                self.level_before = control.autonomy_level.value
                if control.kill_switch == "released":
                    self.kill_switch("arm")
                if control.kill_switch != "engaged":
                    self.kill_switch("engage")
                self.engaged_at_cap = True
            except Exception as error:  # reported in the stop message; the stop goes on
                self.halt_error = f"{type(error).__name__}: {str(error)[:200]}"

    def wind_down(self, *, seconds: float = 180) -> list[str]:
        """After a stop at the spend cap: wait until none of the check's runs can still make a
        model call, then release the kill switch and put back the autonomy level it had, as a
        normal end leaves them. Returns the runs still under way at the deadline; the switch then
        stays engaged, so they cannot spend."""
        if not self.engaged_at_cap:
            return []
        deadline = time.monotonic() + seconds
        while True:
            going = sorted(r for r in self.started if self.run(r).status in UNDER_WAY)
            if not going:
                break
            if time.monotonic() >= deadline:
                return going
            time.sleep(1.0)
        self.release()
        if self.level_before is not None:
            self.autonomy(self.level_before)
        self.engaged_at_cap = False
        return []

    def _ok(self, response: httpx.Response) -> Any:
        if response.status_code >= 400:
            raise RuntimeError(
                f"{response.request.method} {response.request.url.path}: "
                f"{response.status_code} {response.text[:300]}"
            )
        return response.json()

    def submit(self, type: str, payload: dict[str, Any], event: str) -> EventSubmitted:
        self.guard()  # no new run at the spend cap
        body = EventIn(event_id=event, type=type, source="assignment-check", payload=payload)  # type: ignore[arg-type]
        submitted = EventSubmitted.model_validate(
            self._ok(self.http.post("/events", json=body.model_dump(mode="json")))
        )
        self.started.add(str(submitted.run_id))
        return submitted

    def run(self, run_id: str) -> RunDetail:
        return RunDetail.model_validate(self._ok(self.http.get(f"/runs/{run_id}")))

    def wait(self, run_id: str, *, seconds: float = 600, until=WAITING) -> RunDetail:
        deadline = time.monotonic() + seconds
        while True:
            self.guard()
            detail = self.run(run_id)
            if detail.status in until:
                return detail
            if time.monotonic() > deadline:
                raise TimeoutError(
                    f"run {run_id} still {detail.status.value} after {seconds:.0f} s"
                )
            time.sleep(1.0)

    def decide(self, run_id: str, decision: str, comment: str = "") -> None:
        body = ApprovalIn(decision=decision, decided_by=BY, comment=comment)  # type: ignore[arg-type]
        self._ok(self.http.post(f"/approvals/{run_id}", json=body.model_dump()))

    def control(self) -> ControlState:
        return ControlState.model_validate(self._ok(self.http.get("/control")))

    def kill_switch(self, action: str) -> None:
        body = KillSwitchIn(action=action, by=BY)  # type: ignore[arg-type]
        self._ok(self.http.post("/control/kill-switch", json=body.model_dump()))

    def engage(self) -> None:
        self.kill_switch("arm")
        self.kill_switch("engage")
        self.engaged_by_check = True

    def release(self) -> None:
        self.kill_switch("release")
        self.engaged_by_check = False

    def autonomy(self, level: str) -> None:
        body = AutonomyIn(level=level, by=BY)  # type: ignore[arg-type]
        self._ok(self.http.post("/control/autonomy", json=body.model_dump(mode="json")))


def failure_text(detail: RunDetail) -> str:
    answer = detail.answer or {}
    reasons = " ".join(str(r) for r in answer.get("reasons") or [])
    errors = " ".join(str(e.payload.get("error", "")) for e in detail.events)
    return f"{reasons} {errors}".strip()


def stop_on_rejected_key(detail: RunDetail) -> None:
    from datapilot.assignments.keys import MISSING_KEY, NO_CREDITS, out_of_credits, rejected

    if detail.status is not RunStatus.FAILED:
        return
    text = failure_text(detail)
    if rejected(text):
        raise Stop(MISSING_KEY)
    if out_of_credits(text):
        raise Stop(NO_CREDITS)


def daily_budget_stop(detail: RunDetail) -> str:
    from datapilot.config import pack_config

    per_day = int(pack_config()["budgets"]["tokens_per_day"])
    return (
        f"Stopped: run {detail.run_id} ended blocked_budget, because this stack's daily token "
        f"budget (budgets.tokens_per_day in pack.yaml, {per_day:,} tokens per Eastern time "
        "calendar day) is spent. This is not a fault in your solution, and that run was not "
        "judged. The count starts again at midnight Eastern time; a check on its own Compose "
        "project also sets it back to zero when it starts, so run the check again. With "
        "DATAPILOT_ASSIGNMENT_STACK=running, the services' own stack keeps its count until "
        "midnight."
    )


def release_hint(slug: str) -> str:
    from datapilot.assignments.stack import reset_command

    return (
        f"Release it on the check's console, or with {reset_command(slug or '<slug>')}, then run "
        "the check again."
    )


def kill_switch_stop(detail: RunDetail, slug: str = "") -> str:
    return (
        f"Stopped: run {detail.run_id} ended blocked_killswitch, because the kill switch of this "
        "check's stack was engaged from outside the check, such as on its console. This is not a "
        f"fault in your solution, and that run was not judged. {release_hint(slug)}"
    )


def in_process_kill_switch_stop(slug: str) -> str:
    """The stop of a check whose runs are in this process (Assignment 4's benchmark)."""
    return (
        "Stopped: the kill switch of this check's stack was engaged from outside the check, such "
        "as on its console, so the benchmark's runs stopped at their next model call and nothing "
        "measured after it counts. This is not a fault in your solution, and nothing more was "
        f"judged. {release_hint(slug)}"
    )


def stop_on_blocked(detail: RunDetail, api: Any) -> None:
    """A run the stack blocked says nothing about the solution: the daily token budget, or a kill
    switch the check did not engage itself, stops the check (exit 2) instead of failing a line. A
    block from the check's own kill-switch step, or from its stop at the spend cap, is judged as
    the check expects."""
    if detail.status is RunStatus.BLOCKED_BUDGET:
        raise Stop(daily_budget_stop(detail))
    ours = getattr(api, "engaged_by_check", False) or getattr(api, "engaged_at_cap", False)
    if detail.status is RunStatus.BLOCKED_KILLSWITCH and not ours:
        raise Stop(kill_switch_stop(detail, getattr(api, "slug", "")))


def trace_link(trace_id: str, *, project: str | None = None, tries: int = 10) -> str:
    """The LangSmith link of a trace, once LangSmith has ingested it."""
    settings = get_settings()
    project = project or settings.langsmith_project
    key = settings.langsmith_api_key.get_secret_value()
    if not key:
        return f"not available: LANGSMITH_API_KEY is not set (trace id {trace_id})"
    from langsmith.utils import LangSmithError

    from datapilot.observability.background import bounded_client

    client = bounded_client(api_key=key, api_url=settings.langsmith_endpoint)
    # Once one trace never showed up (LangSmith refusing uploads, such as at the free plan's
    # monthly limit), later lookups in this check try once, so the check is not slowed run by run.
    for attempt in range(1 if _LOOKUPS["gave_up"] else tries):
        try:
            run = client.read_run(trace_id)
            return client.get_run_url(run=run, project_name=project)
        except LangSmithError:
            if attempt + 1 < tries:
                time.sleep(2)
        except Exception as error:  # a link is evidence, never a reason to fail a check
            return f"not available: {type(error).__name__} (trace id {trace_id})"
    _LOOKUPS["gave_up"] = True
    return f"not found in LangSmith project {project} yet (trace id {trace_id})"


def live_run(detail: RunDetail, passed: bool, what: str) -> LiveRun:
    stamp = detail.live_stamp
    made_calls = detail.tokens_in + detail.tokens_out > 0
    trace = trace_link(str(detail.run_id)) if made_calls else "none: the run made no model call"
    return LiveRun(
        passed=passed,
        detail=f"{what} (status {detail.status.value}, {detail.tokens_in + detail.tokens_out:,} "
        "tokens)",
        run_id=str(detail.run_id),
        started_at_utc=stamp.started_at_utc if stamp else None,
        session_id=str(detail.session_id) if detail.session_id else None,
        trace=trace,
    )


@contextlib.contextmanager
def traced_step(name: str, metadata: dict[str, Any]) -> Iterator[str]:
    """An in-process live step as one LangSmith trace; yields its trace id. Model calls inside it
    become its child runs."""
    from langsmith import trace

    settings = get_settings()
    with trace(
        name, run_type="chain", project_name=settings.langsmith_project, metadata=metadata
    ) as root:
        yield str(root.id)


Decide = Callable[[RunDetail], str]  # a held run -> "approve" or "reject"


def _open_approval(detail: RunDetail) -> bool:
    return any(a.decision is None for a in detail.approvals)


def settle(api: Api, run_id: str, decide: Decide, *, seconds: float = 900) -> RunDetail:
    """Wait for a run to end, acting as the human approver whenever it waits for one."""
    deadline = time.monotonic() + seconds
    while True:
        detail = api.wait(run_id, seconds=max(deadline - time.monotonic(), 1))
        if detail.status is not RunStatus.AWAITING_APPROVAL:
            stop_on_rejected_key(detail)
            stop_on_blocked(detail, api)
            return detail
        if _open_approval(detail):
            api.decide(run_id, decide(detail))
        while time.monotonic() < deadline:  # until the worker picks the decision up
            detail = api.run(run_id)
            if detail.status is not RunStatus.AWAITING_APPROVAL or _open_approval(detail):
                break
            time.sleep(1.0)
        if time.monotonic() >= deadline:
            raise TimeoutError(f"run {run_id} still waits for approval after {seconds:.0f} s")


def reject_all(detail: RunDetail) -> str:
    return "reject"


def tool_calls(detail: RunDetail) -> list[str]:
    return [
        str(e.payload.get("tool"))
        for e in detail.events
        if e.kind is RunEventKind.TOOL_CALL_STARTED
    ]


def envelope(detail: RunDetail) -> AnswerEnvelope | None:
    data = (detail.answer or {}).get("envelope")
    return AnswerEnvelope.model_validate(data) if data else None


def two_of_three[K](
    cases: Sequence[K],
    run: Callable[[K], RunDetail],
    judge: Callable[[K, RunDetail], LiveRun],
) -> list[list[LiveRun]]:
    """The fair pass rule, 2 of 3, at the fewest runs: two runs of every case at once, and a third
    run only for a case whose first two disagree (two passes or two failures already decide)."""
    from datapilot.assignments.gold import in_parallel

    first = in_parallel([lambda c=c: run(c) for c in cases for _ in range(2)])
    groups = [[judge(c, d) for d in first[2 * i : 2 * i + 2]] for i, c in enumerate(cases)]
    split = [i for i, group in enumerate(groups) if sum(r.passed for r in group) == 1]
    third = in_parallel([lambda i=i: run(cases[i]) for i in split])
    for i, detail in zip(split, third, strict=True):
        groups[i].append(judge(cases[i], detail))
    return groups
