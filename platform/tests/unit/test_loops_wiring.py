"""Wiring of the three loops that needs no database: the model factory, run metadata, the router,
the autonomy policy, the kill switch middleware, pacing, and the demo triggers."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from datapilot.config import pack_config
from datapilot.contracts import AutonomyLevel, EventType, registries
from datapilot.loop1_agent.analyst import AgentLimits, RunMetadata
from datapilot.loop1_agent.guard import RunGuard, StopReason
from datapilot.loop1_agent.models import openai_factory
from datapilot.loop2_verification.config import VerificationConfig
from datapilot.loop3_events import demos, pacing, router
from datapilot.loop3_events.autonomy import OpsAutonomyPolicy, posting_decision
from datapilot.loop3_events.killswitch import KillSwitchMiddleware
from datapilot.settings import Settings, get_settings


def test_the_live_model_uses_the_responses_api_and_pack_reasoning_without_temperature() -> None:
    settings = Settings(_env_file=None, openai_model="model-from-env", openai_api_key="sk-test")
    build = openai_factory(settings=settings, run_id="r1")
    model = build("reviewer")
    assert model.model_name == "model-from-env" and model.use_responses_api is True
    assert model.reasoning == {"effort": pack_config()["models"]["reviewer"]["reasoning_effort"]}
    assert model.temperature is None
    callback = model.callbacks[0]
    assert (callback.component, callback.model, callback.run_id) == (
        "reviewer",
        "model-from-env",
        "r1",
    )


def test_limits_come_from_the_pack() -> None:
    cfg = pack_config()
    limits = AgentLimits.from_pack(cfg)
    assert limits.model_call_limit == cfg["limits"]["model_call_limit"]
    assert limits.tokens_per_run == cfg["budgets"]["tokens_per_run"]
    config = VerificationConfig.from_pack(cfg)
    assert config.schema == cfg["databases"]["allowed_schema"]
    assert ("customers", "email") in config.personal_columns
    assert config.marketing_view == "customers_marketable"


def test_run_metadata_carries_every_langsmith_key() -> None:
    metadata = RunMetadata(
        run_id="r1",
        event_id="e1",
        demo_name="agent-simple-question",
        pack="datapilot_us",
        knowledge_version="v1",
        autonomy_level="report_only",
        planted_active=["BUG_UNBOUNDED_ROWS"],
        model="m",
    )
    config = metadata.config(thread_id="r1", trace_id="t1", attempt=2)
    keys = {"event_id", "demo_name", "pack", "knowledge_version", "autonomy_level"}
    assert keys | {"planted_active", "model", "datapilot_run_id", "attempt"} <= set(
        config["metadata"]
    )
    assert config["run_id"] == "t1" and config["configurable"] == {"thread_id": "r1"}
    assert "planted:BUG_UNBOUNDED_ROWS" in config["tags"]


def test_the_router_is_a_fixed_table() -> None:
    assert router.route("question.asked", {}).handler == "question"
    assert router.route("export.requested", {}).export is True
    assert router.route("digest.requested", {}).queue == "scheduled"
    assert router.route("question.asked", {"check": "malicious-sql"}).handler == "defense_check"
    assert set(router.ROUTES) == set(EventType)
    with pytest.raises(ValueError):
        router.route("something.else", {})


def test_metric_families_are_assigned_deterministically() -> None:
    families = pack_config()["autonomy"]["metric_families"]
    assert router.metric_family("What was net revenue in fiscal year 2025?", {}, families) == (
        "revenue"
    )
    assert router.metric_family("Average order value last month?", {}, families) == "aov"
    assert router.metric_family("How many orders?", {}, families) == "orders"
    assert router.metric_family("anything", {"metric_family": "products"}, families) == "products"


def policy(level: AutonomyLevel, eligible: set[str] | None = None) -> OpsAutonomyPolicy:
    return OpsAutonomyPolicy(level, "v2", frozenset(eligible or set()))


def test_the_autonomy_levels() -> None:
    assert policy(AutonomyLevel.REPORT_ONLY).level_for("revenue") is AutonomyLevel.REPORT_ONLY
    unattended = policy(AutonomyLevel.UNATTENDED, {"revenue"})
    assert unattended.level_for("revenue") is AutonomyLevel.UNATTENDED
    assert unattended.level_for("orders") is AutonomyLevel.ASSISTED
    assisted = policy(AutonomyLevel.ASSISTED)
    assert posting_decision(
        assisted, "orders", personal_data=True, export=False, approved=False
    ) == ("approve_first")
    assert posting_decision(
        assisted, "orders", personal_data=False, export=True, approved=False
    ) == ("approve_first")
    assert posting_decision(assisted, "orders", personal_data=True, export=True, approved=True) == (
        "post"
    )
    assert posting_decision(
        policy(AutonomyLevel.REPORT_ONLY), None, personal_data=True, export=True, approved=False
    ) == ("post")  # posted labelled unverified, with export rows withheld by the worker


def tool_request() -> Any:
    return SimpleNamespace(tool_call={"id": "c1", "name": "run_query", "args": {}})


@pytest.mark.parametrize("flag", ["0", "1"])
def test_the_kill_switch_middleware(monkeypatch: pytest.MonkeyPatch, flag: str) -> None:
    monkeypatch.setenv("BUG_KILLSWITCH_AT_CLAIM_ONLY", flag)
    guard = RunGuard(tokens_per_run=1000)
    middleware = KillSwitchMiddleware(guard, is_engaged=lambda: True)
    jumped = middleware.before_model({"messages": []}, None)
    tool = middleware.wrap_tool_call(tool_request(), lambda request: "ran")
    if flag == "1":  # planted: nothing stops the run in flight
        assert jumped is None and tool == "ran" and guard.stop_reason is None
    else:
        assert jumped == {"jump_to": "end"} and guard.stop_reason is StopReason.KILL_SWITCH
        assert "kill switch" in tool.content


def test_the_run_guard_stops_at_the_token_budget() -> None:
    guard = RunGuard(tokens_per_run=100, tokens_in=90, tokens_out=10)
    assert guard.check() is StopReason.TOKEN_LIMIT


def test_pacing_is_off_unless_the_demo_aid_is_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DEMO_PACING", raising=False)
    assert pacing.seconds() == 0
    monkeypatch.setenv("DEMO_PACING", "1")
    monkeypatch.setenv("DEMO_PACING_SECONDS", "0.5")
    get_settings.cache_clear()
    try:
        assert pacing.seconds() == 0.5
    finally:
        get_settings.cache_clear()


class RecordingClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def post(self, url: str, **kwargs: Any) -> Any:
        self.calls.append((url, kwargs.get("json") or {}))
        body = {"run_id": f"run-{len(self.calls)}", "request_id": f"req-{len(self.calls)}"}
        return SimpleNamespace(raise_for_status=lambda: None, json=lambda: body)

    def get(self, url: str, **kwargs: Any) -> Any:
        return SimpleNamespace(raise_for_status=lambda: None, json=lambda: {"status": "running"})


@pytest.mark.parametrize("demo", registries.demos().demos, ids=lambda d: d.id)
def test_every_registry_demo_has_a_trigger(demo) -> None:
    client = RecordingClient()
    done = demos.trigger(client, demo, wait_running_seconds=0)
    assert done.run_ids or done.request_ids
    event_ids = {c[1].get("event_id") for c in client.calls if c[0] == "/events"}
    assert all(e is None or e.startswith(("demo:", "digest:")) for e in event_ids)


def test_the_same_event_three_times_uses_one_event_id() -> None:
    demo = next(
        d
        for d in registries.demos().demos
        if d.trigger.api == "POST /events (same event_id three times)"
    )
    client = RecordingClient()
    demos.trigger(client, demo)
    questions = [c[1]["event_id"] for c in client.calls if c[1].get("type") == "question.asked"]
    digests = [c[1]["event_id"] for c in client.calls if c[1].get("type") == "digest.requested"]
    assert len(questions) == 3 and len(set(questions)) == 1
    assert len(digests) == 2 and len(set(digests)) == 1


LOOPS_SECTIONS = {"agent-loop", "verification-loop", "event-loop"}


def test_each_planted_location_of_the_loops_holds_its_flag() -> None:
    from datapilot.settings import REPO

    checked = 0
    for item in registries.planted().items:
        if item.section not in LOOPS_SECTIONS or not item.location.startswith("platform/src"):
            continue
        path = REPO / item.location
        assert path.is_file(), item.id
        if item.id.startswith(("BUG_", "DEMO_")):
            assert f'planted("{item.id}")' in path.read_text(encoding="utf-8"), item.id
            checked += 1
    assert checked == 11  # ten code bugs of the three loops and demo pacing
