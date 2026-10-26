"""Planted flags never judge a solution and never outlive a demo (zero tokens, no database).

A flag switched on for one run is on inside it, in the threads it starts, and nowhere after it;
assignment checks, the verification of the solutions, and the finale refuse to start while a flag
is on in .env, in their own environment, or in a running service, naming each flag and how to turn
it off; a flag a service reads at its start is set for that service alone and put back afterwards,
even on an error. The api and Docker here are test doubles, in a unit test only."""

from __future__ import annotations

import contextlib
import io
import json
import shutil
import subprocess
import uuid
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import yaml
from fastapi import HTTPException

from datapilot import finale, planted
from datapilot.assignments import live, solutions, stack
from datapilot.assignments.report import Stop
from datapilot.contracts import RunStatus, registries
from datapilot.loop3_events import commands
from datapilot.loop3_events.api import events
from datapilot.loop4_hill_climbing.runner import CarriedEvaluator
from datapilot.settings import get_settings

# In make test-security's selection (-k security matches the marker).
pytestmark = pytest.mark.security

BUG = "BUG_NO_IDEMPOTENCY"


def _env_file(tmp_path: Path, text: str) -> Path:
    path = tmp_path / ".env"
    path.write_text(text, encoding="utf-8")
    return path


# --- one run's flags ------------------------------------------------------------------------------
def test_a_flag_for_this_run_is_on_inside_it_and_off_after_it() -> None:
    assert not planted.planted(BUG)
    with planted.for_this_run([BUG, "DEMO_PACING"]) as chosen:
        assert chosen == [BUG, "DEMO_PACING"]
        assert planted.planted(BUG) and planted.active() == [BUG, "DEMO_PACING"]
        assert planted.this_run() == [BUG, "DEMO_PACING"]
    assert not planted.planted(BUG) and planted.active() == [] and planted.this_run() == []


def test_a_flag_for_this_run_goes_off_even_when_the_run_fails() -> None:
    with pytest.raises(RuntimeError), planted.for_this_run([BUG]):
        raise RuntimeError("the run failed")
    assert not planted.planted(BUG)


def test_an_unknown_flag_for_a_run_is_refused() -> None:
    with pytest.raises(KeyError, match="BUG_TYPO"), planted.for_this_run(["BUG_TYPO"]):
        pass


def test_a_thread_pool_gets_the_flags_only_through_carried() -> None:
    """A pool does not carry context variables into its threads: the hill-climbing runner wraps
    its target and evaluator with planted.carried, so an experiment's runs see its flags."""
    probe = planted.planted
    with planted.for_this_run(["BUG_SQL_TEXT_EVAL"]), ThreadPoolExecutor(2) as pool:
        bare = pool.submit(probe, "BUG_SQL_TEXT_EVAL").result()
        carried = pool.submit(planted.carried(probe), "BUG_SQL_TEXT_EVAL").result()
        evaluator = CarriedEvaluator(planted.carried(lambda item, answer: probe(item)))
        through = pool.submit(evaluator.evaluate, "BUG_SQL_TEXT_EVAL", None).result()
    assert (bare, carried, through) == (False, True, True)
    with ThreadPoolExecutor(1) as pool:  # after the request: nothing carried, nothing on
        assert not pool.submit(planted.carried(probe), "BUG_SQL_TEXT_EVAL").result()


def test_the_header_names_known_flags_only() -> None:
    assert planted.from_header(f" {BUG} , DEMO_PACING ") == [BUG, "DEMO_PACING"]
    assert planted.from_header(None) == [] and planted.header([]) == {}
    assert planted.header(["DEMO_PACING", BUG]) == {planted.PLANTED_HEADER: f"{BUG},DEMO_PACING"}
    with pytest.raises(KeyError):
        planted.from_header("BUG_TYPO")


DUPLICATES = "events-duplicate-events"  # plants BUG (and the random digest id)


@pytest.fixture
def demo_controls(monkeypatch) -> Iterator[None]:
    monkeypatch.setenv("DATAPILOT_ALLOW_DEMO_CONTROLS", "1")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_the_api_takes_flags_for_one_run_only_with_demo_controls(monkeypatch) -> None:
    monkeypatch.setenv("DATAPILOT_ALLOW_DEMO_CONTROLS", "0")
    get_settings.cache_clear()
    try:
        assert events.requested_flags(None, None) == []
        with pytest.raises(HTTPException) as refused:
            events.requested_flags(BUG, DUPLICATES)
        assert refused.value.status_code == 403
        monkeypatch.setenv("DATAPILOT_ALLOW_DEMO_CONTROLS", "1")
        get_settings.cache_clear()
        assert events.requested_flags(BUG, DUPLICATES) == [BUG]
        with pytest.raises(HTTPException) as unknown:
            events.requested_flags("BUG_TYPO", DUPLICATES)
        assert unknown.value.status_code == 422
    finally:
        get_settings.cache_clear()


@pytest.mark.usefixtures("demo_controls")
@pytest.mark.parametrize(
    ("flags", "demo", "said"),
    [
        # another demo's bug: the review of 26 October ran the naive guard on any event
        ("BUG_NAIVE_GUARD", DUPLICATES, "BUG_NAIVE_GUARD is not a planted flag of " + DUPLICATES),
        (f"{BUG},BUG_NO_COST_GUARD", DUPLICATES, "BUG_NO_COST_GUARD is not a planted flag"),
        (BUG, None, "planted flags need the demo they belong to"),
        (BUG, "no-such-demo", "no-such-demo is not a demo in platform/demos/registry.yaml"),
        # read as the worker starts: no run could carry it, so it is never recorded on one
        (
            "BUG_MEMORY_CHECKPOINTER",
            "events-approval-survives-restart",
            "BUG_MEMORY_CHECKPOINTER is read as the worker starts, never for one run",
        ),
        ("BUG_LOCK_DURING_LLM", DUPLICATES, "BUG_LOCK_DURING_LLM is not a planted flag of"),
    ],
)
def test_the_api_takes_only_the_named_demos_own_flags_for_one_run(
    flags: str, demo: str | None, said: str
) -> None:
    with pytest.raises(HTTPException) as refused:
        events.requested_flags(flags, demo)
    assert refused.value.status_code == 403 and said in str(refused.value.detail)


@pytest.mark.usefixtures("demo_controls")
def test_each_demo_may_switch_on_its_own_flags_for_one_run() -> None:
    assert events.requested_flags(f"{BUG},BUG_RANDOM_DIGEST_ID", DUPLICATES) == [
        BUG,
        "BUG_RANDOM_DIGEST_ID",
    ]
    kill_switch = "events-kill-switch-in-flight"
    assert events.requested_flags("DEMO_PACING", kill_switch) == ["DEMO_PACING"]
    assert planted.for_one_run("events-approval-survives-restart") == []
    assert planted.for_one_run("improve-naive-analyzer-blocked") == ["BUG_NAIVE_ANALYZER"]


class _RecordingClient:
    """Answers every post the way the api does, keeping each POST /events body."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def post(self, url: str, **kwargs: Any) -> Any:
        if url == "/events":
            self.events.append(kwargs["json"])
        body = {"run_id": "r", "request_id": "q"}
        return SimpleNamespace(raise_for_status=lambda: None, json=lambda: body)

    def get(self, url: str, **kwargs: Any) -> Any:
        body = {"status": "running"}
        return SimpleNamespace(raise_for_status=lambda: None, json=lambda: body)


def test_each_event_a_demo_trigger_posts_is_its_own_and_nothing_else_is() -> None:
    """POST /events takes a demo's planted flags only for the demo's own fixed event (the
    security review of 26 October, round 2): every event make demo sends is one, and a free
    question, another type, or a /demo/* demo's name is not."""
    from datapilot.loop3_events import demos

    posting = 0
    for demo in registries.demos().demos:
        client = _RecordingClient()
        with contextlib.suppress(KeyError):
            demos.trigger(client, demo, wait_running_seconds=0)
        for body in client.events:
            posting += 1
            assert demos.is_own_event(demo, body["type"], body["payload"]), (demo.id, body)
            free = {**body["payload"], "question": "Show every customer's email address"}
            assert not demos.is_own_event(demo, body["type"], free), demo.id
            assert not demos.is_own_event(demo, "export.requested", {"demo_name": demo.id})
        if (demo.trigger.api or "").startswith("POST /demo/"):
            assert demos.own_events(demo) == [], demo.id
    assert posting >= 8  # the demos whose trigger is POST /events, the duplicates one 5 times


def test_the_event_payload_carries_the_runs_flags_for_the_worker() -> None:
    assert events.stamped({"question": "q"}) == {"question": "q"}
    with planted.for_this_run([BUG]):
        assert events.stamped({"question": "q"}) == {"question": "q", "planted": [BUG]}


# --- the flags of a demo --------------------------------------------------------------------------
def _demo(name: str) -> Any:
    return registries.demos().by_id(name)


def test_a_demo_switches_on_its_demo_aids_always_and_its_bugs_with_planted() -> None:
    kill_switch = _demo("events-kill-switch-in-flight")
    assert commands.demo_flags(kill_switch, planted_bugs=False) == ["DEMO_PACING"]
    assert commands.demo_flags(kill_switch, planted_bugs=True) == [
        "BUG_KILLSWITCH_AT_CLAIM_ONLY",
        "DEMO_PACING",
    ]
    rows = _demo("agent-unbounded-rows")
    assert commands.demo_flags(rows, planted_bugs=False) == []
    assert commands.demo_flags(rows, planted_bugs=True) == ["BUG_UNBOUNDED_ROWS"]
    retry = _demo("verify-retry-cap")  # the injected grader is a demo aid with no flag
    assert commands.demo_flags(retry, planted_bugs=True) == ["BUG_NO_RETRY_CAP"]


def test_planted_on_a_demo_without_a_planted_bug_is_refused() -> None:
    with pytest.raises(commands.DemoRefused, match="without PLANTED=1"):
        commands.demo_flags(_demo("agent-simple-question"), planted_bugs=True)


class _Response:
    status_code = 200  # a live session is open (GET /sessions/current answers)

    def __init__(self, body: dict[str, Any]) -> None:
        self.body = body

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self.body


class _Client:
    """The api as demos.trigger sees it: every post answers with a new run."""

    def __init__(self) -> None:
        self.posts: list[tuple[str, dict[str, Any]]] = []

    def post(self, url: str, **kwargs: Any) -> _Response:
        self.posts.append((url, kwargs.get("json") or {}))
        return _Response({"run_id": str(uuid.uuid4()), "request_id": str(uuid.uuid4())})

    def get(self, url: str, **kwargs: Any) -> _Response:
        return _Response({"status": "posted"})


def _digest_ids(client: _Client) -> list[str]:
    return [b["event_id"] for url, b in client.posts if b.get("type") == "digest.requested"]


def test_the_digest_id_of_a_planted_demo_is_random_for_that_trigger_only() -> None:
    """The random digest id is read in the process that makes the id: make demo's own."""
    fixed, bugged = _Client(), _Client()
    commands.demo("events-duplicate-events", client=fixed, say=lambda _line: None)
    commands.demo("events-duplicate-events", planted_bugs=True, client=bugged, say=lambda _: None)
    assert len(set(_digest_ids(fixed))) == 1  # one deterministic id, sent twice
    assert len(set(_digest_ids(bugged))) == 2  # a new id each time: nothing is absorbed
    assert not planted.planted("BUG_RANDOM_DIGEST_ID")  # off again once the trigger returned


# --- a flag a service reads at its start ----------------------------------------------------------
@contextlib.contextmanager
def _ops(rows: list[dict[str, Any]]) -> Iterator[Any]:
    yield SimpleNamespace(execute=lambda *_args: rows)


def test_a_service_start_flag_restarts_that_service_with_it_and_back_even_on_error(
    monkeypatch,
) -> None:
    monkeypatch.setattr(commands.db, "connect", lambda *_a, **_k: _ops([]))
    calls: list[list[str]] = []
    overrides: list[dict[str, Any]] = []

    def compose(args: list[str]) -> None:
        calls.append(args)
        files = [Path(a) for a in args if a.endswith("compose.demo.yaml")]
        overrides.extend(yaml.safe_load(f.read_text(encoding="utf-8")) for f in files)

    flags = {"BUG_MEMORY_CHECKPOINTER": "worker"}
    with (
        pytest.raises(RuntimeError, match="the demo broke"),
        commands.services_with(flags, compose=compose, say=lambda _line: None),
    ):
        raise RuntimeError("the demo broke")
    assert len(calls) == 2  # with the flag, then back without it
    assert len(overrides) == 1
    environment = overrides[0]["services"]["worker"]["environment"]
    tag = environment.pop(planted.TAG_VARIABLE)
    assert environment == {"BUG_MEMORY_CHECKPOINTER": "1"} and tag.startswith("demo-")
    assert calls[0][-1] == "worker" and calls[1][-1] == "worker" and "--no-deps" in calls[1]
    assert not any(a.endswith("compose.demo.yaml") for a in calls[1])  # .env alone afterwards
    assert all("up" in c and ".env" not in " ".join(c) for c in calls)


def test_a_service_start_flag_is_refused_while_a_run_is_under_way(monkeypatch) -> None:
    monkeypatch.setattr(commands.db, "connect", lambda *_a, **_k: _ops([{"run_id": "r1"}]))
    calls: list[list[str]] = []
    with (
        pytest.raises(commands.DemoRefused, match="under way"),
        commands.services_with({"BUG_MEMORY_CHECKPOINTER": "worker"}, compose=calls.append),
    ):
        pass
    assert calls == []  # nothing restarted


def test_the_approval_demo_planted_restarts_the_worker_and_waits_for_its_run(monkeypatch) -> None:
    monkeypatch.setattr(commands.db, "connect", lambda *_a, **_k: _ops([]))
    calls: list[list[str]] = []
    client = _Client()
    done = commands.demo(
        "events-approval-survives-restart",
        planted_bugs=True,
        client=client,
        compose=calls.append,
        say=lambda _line: None,
    )
    assert len(done.run_ids) == 1 and len(calls) == 2
    assert [url for url, _body in client.posts] == ["/events"]


class _HeaderClient(_Client):
    def __init__(self) -> None:
        super().__init__()
        self.headers: list[dict[str, str]] = []

    def post(self, url: str, **kwargs: Any) -> _Response:
        self.headers.append(dict(kwargs.get("headers") or {}))
        return super().post(url, **kwargs)


def test_the_restarted_workers_tag_goes_with_the_demos_own_events_only(monkeypatch) -> None:
    """The security review of 26 October: a worker restarted with a service-start flag took every
    run. Now its tag is in its environment and on the demo's events; it claims those alone."""
    monkeypatch.setattr(commands.db, "connect", lambda *_a, **_k: _ops([]))
    overrides: list[dict[str, Any]] = []

    def compose(args: list[str]) -> None:
        files = [Path(a) for a in args if a.endswith("compose.demo.yaml")]
        overrides.extend(yaml.safe_load(f.read_text(encoding="utf-8")) for f in files)

    client = _HeaderClient()
    commands.demo(
        "events-approval-survives-restart",
        planted_bugs=True,
        client=client,
        compose=compose,
        say=lambda _line: None,
    )
    tag = overrides[0]["services"]["worker"]["environment"][planted.TAG_VARIABLE]
    assert tag.startswith("events-approval-survives-restart-")
    # the flag itself is never in a header: the api refuses a service-start flag for one run
    assert client.headers == [{planted.TAG_HEADER: tag}]
    fixed = _HeaderClient()
    commands.demo("events-approval-survives-restart", client=fixed, say=lambda _line: None)
    assert fixed.headers == [{}]  # the fixed half: no tag, no restart


def test_a_demos_per_run_flags_go_in_its_header_with_the_demo_named() -> None:
    client = _HeaderClient()
    commands.demo(DUPLICATES, planted_bugs=True, client=client, say=lambda _line: None)
    assert client.headers[0] == {
        planted.PLANTED_HEADER: f"{BUG},BUG_RANDOM_DIGEST_ID",
        planted.DEMO_HEADER: DUPLICATES,
    }


def test_the_restart_back_waits_for_another_run_under_way(monkeypatch) -> None:
    """Before restoring, as before starting: a run other than the demo's that a worker works on
    is waited for (up to a bound), then the restart back happens anyway."""
    answers = iter([[], [{"run_id": "other"}], []])  # before the start, then twice before restore
    seen: list[tuple[Any, ...]] = []

    @contextlib.contextmanager
    def connect(*_a: Any, **_k: Any) -> Iterator[Any]:
        rows = next(answers)
        yield SimpleNamespace(execute=lambda *args: (seen.append(args), rows)[1])

    monkeypatch.setattr(commands.db, "connect", connect)
    monkeypatch.setattr(commands.time, "sleep", lambda _s: None)
    calls: list[list[str]] = []
    said: list[str] = []
    with commands.services_with(
        {"BUG_MEMORY_CHECKPOINTER": "worker"}, compose=calls.append, say=said.append
    ) as restart:
        assert restart is not None and len(calls) == 1
        restart.run_ids.append("ours")
    assert len(calls) == 2
    assert seen[1] == (commands.OTHERS_WORKING_SQL, (["ours"],))  # the demo's own run excepted
    assert "Waiting for 1 other run(s) under way before the restart back" in said


def test_the_restart_back_happens_after_a_bounded_wait(monkeypatch) -> None:
    def execute(sql: str, *_params: Any) -> list[dict[str, str]]:
        return [] if sql == commands.UNDER_WAY_SQL else [{"run_id": "stuck"}]

    @contextlib.contextmanager
    def connect(*_a: Any, **_k: Any) -> Iterator[Any]:
        yield SimpleNamespace(execute=execute)

    monkeypatch.setattr(commands.db, "connect", connect)
    calls: list[list[str]] = []
    said: list[str] = []
    with commands.services_with(
        {"BUG_MEMORY_CHECKPOINTER": "worker"},
        compose=calls.append,
        say=said.append,
        restore_wait_seconds=0,
    ):
        pass
    assert len(calls) == 2  # put back although a run was still under way
    assert any("the restart back stops them now" in line for line in said)


def _decision(verdict: str, ready: bool) -> Any:
    from datapilot.loop4_hill_climbing.gate import GateDecision, Regressions

    return GateDecision(
        verdict=verdict,  # type: ignore[arg-type]
        ready_for_approval=ready,
        reasons=["pass: holdout passes 9 of 10 against 7 for v1"],
        sentence="Promoted: v2 passes.",
        candidate_version="v2",
        active_version="v1",
        candidate_holdout_passes=9,
        active_holdout_passes=7,
        holdout_total=10,
        regressions=Regressions(),
        approved_by="a person",
    )


def test_the_gate_never_decides_on_an_experiment_made_with_a_planted_flag() -> None:
    """The security review of 26 October: an experiment made with the planted evaluator could
    decide a promotion. Only the naive analyzer's candidate goes through, to be blocked."""
    from datapilot.loop4_hill_climbing import runner

    with pytest.raises(runner.RequestFailed, match="BUG_SQL_TEXT_EVAL"):
        runner.refuse_planted_gate(["BUG_SQL_TEXT_EVAL"])
    with pytest.raises(runner.RequestFailed, match="DEMO_PACING"):
        runner.refuse_planted_gate(["BUG_NAIVE_ANALYZER", "DEMO_PACING"])
    runner.refuse_planted_gate([])
    runner.refuse_planted_gate(["BUG_NAIVE_ANALYZER"])
    promoted = _decision("promoted", ready=True)
    assert runner.blocked_if_planted(promoted, []) is promoted
    blocked = runner.blocked_if_planted(promoted, ["BUG_NAIVE_ANALYZER"])
    assert blocked.verdict == "blocked" and not blocked.ready_for_approval
    assert blocked.reasons[-1] == "fail: written by the naive analyzer (BUG_NAIVE_ANALYZER)"
    ready = runner.blocked_if_planted(_decision("blocked", ready=True), ["BUG_NAIVE_ANALYZER"])
    assert ready.verdict == "blocked" and not ready.ready_for_approval
    already = _decision("blocked", ready=False)  # the overfit guard's block: its reasons stand
    assert runner.blocked_if_planted(already, ["BUG_NAIVE_ANALYZER"]) is already


def test_an_exported_planted_variable_never_switches_a_half_on(monkeypatch) -> None:
    """The security review of 26 October: make passes PLANTED=yes, and an exported PLANTED, to the
    recipe's environment; only the Makefile's --planted (PLANTED=1) decides."""
    from typer.testing import CliRunner

    from datapilot.cli import app

    asked: list[bool] = []

    def demo(name: str, *, planted_bugs: bool, say: Any) -> Any:
        asked.append(planted_bugs)
        return SimpleNamespace(run_ids=[], request_ids=[])

    monkeypatch.setattr(commands, "demo", demo)
    for value in ("1", "yes", "true", "on"):
        result = CliRunner().invoke(app, ["demo", "agent-unbounded-rows"], env={"PLANTED": value})
        assert result.exit_code == 0, result.output
    assert CliRunner().invoke(app, ["demo", "agent-unbounded-rows", "--planted"]).exit_code == 0
    assert asked == [False, False, False, False, True]


def test_a_failed_restart_back_says_to_run_make_up(monkeypatch) -> None:
    monkeypatch.setattr(commands.db, "connect", lambda *_a, **_k: _ops([]))

    def compose(args: list[str]) -> None:
        if not any(a.endswith("compose.demo.yaml") for a in args):
            raise commands.DemoRefused("docker compose up failed")

    with (
        pytest.raises(commands.DemoRefused, match="make up"),
        commands.services_with({"BUG_MEMORY_CHECKPOINTER": "worker"}, compose=compose),
    ):
        pass


# --- where a flag is on, and the refusals ---------------------------------------------------------
def test_the_env_file_is_read_for_flags_only(tmp_path: Path) -> None:
    path = _env_file(
        tmp_path,
        f"OPENAI_MODEL=x\n{BUG}=0\n# {BUG}=1\nDEMO_PACING='1'\n{BUG}=1  # the demo\n"
        "BUG_NAIVE_GUARD=no\nexport BUG_NO_RETRY_CAP=true\n",
    )
    assert planted.in_env_file(path) == ["BUG_NO_RETRY_CAP", BUG, "DEMO_PACING"]
    assert planted.in_env_file(tmp_path / "missing") == []


def test_the_refusal_names_each_flag_where_it_is_on_and_how_to_turn_it_off(tmp_path) -> None:
    on = planted.switched_on(
        env_file=_env_file(tmp_path, f"{BUG}=1\n"),
        environ={"DEMO_PACING": "1"},
        services={"api": [BUG]},
    )
    assert on == {BUG: [".env", "the api service"], "DEMO_PACING": ["this shell's environment"]}
    said = planted.refusal(on, "The live check")
    assert said is not None and said.startswith("The live check does not start")
    assert f"{BUG} (on in .env, the api service)" in said
    assert planted.off_in_env_file(BUG) in said and "then make up" in said
    assert "unset DEMO_PACING" in said
    assert planted.refusal({}, "The live check") is None


# Every form of an `on` line that Compose reads as on (session 6 review, round 2, tests: the last
# two were on for Compose and off for the guard, and the test skipped a form the guard missed).
ON_LINES = [
    f"{BUG}=1",
    f"export {BUG}=1",
    f"{BUG} = 1",
    f"export  {BUG}=yes",
    f"  {BUG}=1",
    f"  export {BUG}=1",
    f"export\t{BUG}=1",
    f"\t{BUG}\t=\t1",
]


@pytest.mark.parametrize("line", ON_LINES)
def test_every_form_compose_reads_as_on_is_read_as_on(tmp_path: Path, line: str) -> None:
    path = _env_file(tmp_path, f"OPENAI_MODEL=x\n{line}\n")
    assert planted.in_env_file(path) == [BUG], repr(line)


@pytest.mark.skipif(shutil.which("docker") is None, reason="compares with docker compose itself")
def test_the_env_file_is_read_as_docker_compose_reads_it(tmp_path: Path) -> None:
    """docker compose config prints the merged settings and starts nothing; its reading of each
    line is the one the services get."""
    (tmp_path / "compose.yaml").write_text(
        "services:\n  probe:\n    image: busybox\n    env_file: [.env]\n", encoding="utf-8"
    )
    for line in [*ON_LINES, f"# {BUG}=1", f"{BUG}=0", f"{BUG}=1 # on"]:
        path = _env_file(tmp_path, f"{line}\n")
        done = subprocess.run(
            ["docker", "compose", "-p", "datapilot-env-probe", "config", "--format", "json"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )
        if done.returncode != 0:
            pytest.fail(f"docker compose config failed on {line!r}: {done.stderr[-500:]}")
        environment = json.loads(done.stdout)["services"]["probe"].get("environment") or {}
        compose_on = planted._is_on(str(environment.get(BUG) or "0"))
        assert (BUG in planted.in_env_file(path)) is compose_on, repr(line)


@pytest.mark.skipif(
    shutil.which("bash") is None or shutil.which("sed") is None,
    reason="runs the printed sed through bash",
)
@pytest.mark.parametrize("line", ON_LINES)
def test_the_refusals_sed_turns_off_every_form_the_env_file_reads_as_on(
    tmp_path: Path, line: str
) -> None:
    """The security review of 26 October: `export FLAG=1` and spaces were read as on, and the
    printed sed matched neither, so the refusal came back after the step it printed. The printed
    command is GNU sed's (Linux and WSL, where the course runs make)."""
    path = _env_file(tmp_path, f"OPENAI_MODEL=x\n{line}\nBUG_NAIVE_GUARD=1\n")
    assert set(planted.in_env_file(path)) == {BUG, "BUG_NAIVE_GUARD"}, f"{line!r} is on"
    said = planted.refusal(planted.switched_on(env_file=path), "The live check")
    assert said is not None
    command = planted.off_in_env_file(BUG)
    assert command in said
    subprocess.run(["bash", "-c", command], cwd=tmp_path, check=True)
    assert planted.in_env_file(path) == ["BUG_NAIVE_GUARD"]  # BUG off, the other flag untouched
    assert "OPENAI_MODEL=x" in path.read_text(encoding="utf-8")


def test_an_assignment_check_refuses_while_env_or_its_environment_has_a_flag_on(
    tmp_path, monkeypatch
) -> None:
    with pytest.raises(Stop, match=BUG):
        stack.refuse_planted(env_file=_env_file(tmp_path, f"{BUG}=1\n"))
    clean = _env_file(tmp_path, f"{BUG}=0\n")
    stack.refuse_planted(env_file=clean)  # no stop
    monkeypatch.setenv("BUG_NAIVE_GUARD", "1")
    with pytest.raises(Stop, match="BUG_NAIVE_GUARD"):
        stack.refuse_planted(env_file=clean)


STARTED = datetime(2026, 10, 26, 14, 0, tzinfo=UTC)


def _report(service: str, flags: list[str], at: datetime = STARTED) -> dict[str, Any]:
    return {"service": service, "planted_active": flags, "started_at": at}


def test_an_assignment_check_refuses_while_a_stack_service_reports_a_flag(monkeypatch) -> None:
    rows = [_report("worker", ["BUG_UNBOUNDED_ROWS"])]
    monkeypatch.setattr(stack.db, "connect", lambda *_a, **_k: _ops(rows))
    with pytest.raises(Stop, match="BUG_UNBOUNDED_ROWS .on in the worker service"):
        stack.refuse_planted_services(lambda _line: None)
    said: list[str] = []
    monkeypatch.setattr(stack.db, "connect", lambda *_a, **_k: _ops([_report("worker", [])]))
    stack.refuse_planted_services(said.append, lambda: {"worker": STARTED})
    assert said == ["Planted flags: none on, in .env, in this process, or in the stack's services"]


def test_a_report_older_than_its_services_start_is_waited_for_then_refused(monkeypatch) -> None:
    """The security review of 26 October: a worker restarted with a flag reports only after the
    database and the read-only probe, so the check read the row from before the restart."""
    before = _report("worker", [], STARTED - timedelta(minutes=5))  # the row before the restart
    monkeypatch.setattr(stack.db, "connect", lambda *_a, **_k: _ops([before]))
    slept: list[float] = []
    with pytest.raises(Stop, match="worker has not reported its planted flags since it started"):
        stack.refuse_planted_services(
            lambda _line: None, lambda: {"worker": STARTED}, wait_seconds=0, sleep=slept.append
        )
    missing = [_report("api", [])]  # the worker never reported at all
    monkeypatch.setattr(stack.db, "connect", lambda *_a, **_k: _ops(missing))
    with pytest.raises(Stop, match="worker has not reported"):
        stack.refuse_planted_services(
            lambda _line: None, lambda: {"worker": STARTED}, wait_seconds=0
        )
    # once the restarted worker has reported, its new row decides
    answers = iter([[before], [_report("worker", ["BUG_MEMORY_CHECKPOINTER"])]])

    @contextlib.contextmanager
    def connect(*_a: Any, **_k: Any) -> Iterator[Any]:
        rows = next(answers)
        yield SimpleNamespace(execute=lambda *_args: rows)

    monkeypatch.setattr(stack.db, "connect", connect)
    with pytest.raises(Stop, match="BUG_MEMORY_CHECKPOINTER .on in the worker service"):
        stack.refuse_planted_services(
            lambda _line: None, lambda: {"worker": STARTED}, sleep=slept.append
        )
    assert slept == [1.0]


def test_without_docker_the_check_says_the_start_times_were_not_read(monkeypatch) -> None:
    monkeypatch.setattr(stack.db, "connect", lambda *_a, **_k: _ops([]))
    said: list[str] = []
    stack.refuse_planted_services(said.append)
    assert len(said) == 2 and "start times could not be read from Docker" in said[1]


def test_the_check_reads_each_services_newest_container_start(monkeypatch) -> None:
    inspected = [
        {
            "Config": {"Labels": {"com.docker.compose.service": "worker"}},
            "State": {"StartedAt": "2026-10-26T14:00:01.123456789Z"},
        },
        {
            "Config": {"Labels": {"com.docker.compose.service": "worker"}},
            "State": {"StartedAt": "2026-10-26T14:03:00.5Z"},
        },
        {
            "Config": {"Labels": {"com.docker.compose.service": "postgres"}},
            "State": {"StartedAt": "2026-10-26T13:00:00Z"},
        },
    ]

    def run(args: list[str], **_k: Any) -> Any:
        out = "a b c\n" if args[1] == "ps" else json.dumps(inspected)
        return SimpleNamespace(stdout=out)

    monkeypatch.setattr(stack.shutil, "which", lambda _name: "/usr/bin/docker")
    monkeypatch.setattr(stack.subprocess, "run", run)
    assert stack.container_starts("datapilot") == {
        "worker": datetime(2026, 10, 26, 14, 3, 0, 500000, tzinfo=UTC)
    }


def test_bring_up_refuses_a_stack_whose_service_reports_a_flag(monkeypatch) -> None:
    """The tests review of 26 October: with the call in bring_up replaced by pass, every test
    still passed. With DATAPILOT_ASSIGNMENT_STACK=running (the class stack, where the check's
    override does not apply) this call is the only guard."""
    monkeypatch.setenv("DATAPILOT_ASSIGNMENT_STACK", "running")
    monkeypatch.setattr(stack, "configure", lambda _activity: None)
    monkeypatch.setattr(stack, "wait_for_api", lambda _url: None)
    monkeypatch.setattr(stack.db, "wait_until_ready", lambda *_a, **_k: None)
    monkeypatch.setattr(stack, "container_starts", lambda _project: None)
    monkeypatch.setattr(stack.db, "connect", lambda *_a, **_k: _ops([_report("api", [BUG])]))
    monkeypatch.setattr(stack, "ensure_seeded", lambda _say: pytest.fail("nothing is seeded"))
    with pytest.raises(Stop, match=rf"{BUG} \(on in the api service\)"):
        stack.bring_up(Path("."), "assignment-event-loop-1a2b3c4d", lambda _line: None)


def test_the_check_refuses_before_it_starts_any_stack(tmp_path, monkeypatch) -> None:
    from datapilot.assignments import runner
    from datapilot.assignments.report import Report

    written = io.StringIO()
    monkeypatch.setattr(runner, "Report", lambda title: Report(title, out=written))
    monkeypatch.setattr(planted, "ENV_FILE", _env_file(tmp_path, f"{BUG}=1\n"))
    monkeypatch.setattr(runner, "bring_up", lambda *_a: pytest.fail("the stack must not start"))
    assert runner.run_check("event-loop", runner.PACKAGE_TREE) == 2
    out = written.getvalue()
    # the refusal itself, not any error that also exits 2 (the tests review of 26 October)
    assert "does not start while planted flags are on" in out
    assert f"{BUG} (on in .env)" in out and planted.off_in_env_file(BUG) in out


def test_the_verification_of_the_solutions_refuses_while_a_flag_is_on(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(solutions, "solutions_withheld", lambda: False)
    monkeypatch.setattr(planted, "ENV_FILE", _env_file(tmp_path, f"{BUG}=1\n"))
    monkeypatch.setattr(solutions, "apply", lambda *_a, **_k: pytest.fail("nothing is applied"))
    with pytest.raises(Stop, match="The verification of the solutions does not start"):
        solutions.verify()


class _PlantedRun:
    """The api as settle sees it: the run ended, made with a planted bug on."""

    def wait(self, run_id: str, *, seconds: float = 600) -> Any:
        return SimpleNamespace(
            run_id=run_id,
            status=RunStatus.POSTED,
            events=[],
            answer=None,
            planted_active=["BUG_NAMES_ONLY_SCHEMA"],
        )


def test_settle_stops_every_assignments_check_on_a_run_made_with_a_flag_on() -> None:
    with pytest.raises(Stop, match="BUG_NAMES_ONLY_SCHEMA"):
        live.settle(_PlantedRun(), "r1", live.reject_all)  # type: ignore[arg-type]


READY = finale.FinaleState("released", "unattended", None)


def test_the_finale_refuses_first_while_a_service_reports_a_flag() -> None:
    state = finale.FinaleState(
        "engaged", "report_only", None, planted_on=(("DEMO_PACING", "the worker service"),)
    )
    said = finale.refusal(state)
    assert said is not None and said.startswith("The finale does not start")
    assert "DEMO_PACING (on in the worker service)" in said and "make up" in said
    assert finale.refusal(READY) is None


def test_make_demo_refuses_the_finale_while_env_has_a_flag_on(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(commands.db, "connect", lambda *_a, **_k: _ops([]))
    monkeypatch.setattr(commands.finale, "read", lambda _conn, _pack: READY)
    commands.check_finale()  # nothing on: no refusal
    monkeypatch.setattr(planted, "ENV_FILE", _env_file(tmp_path, f"{BUG}=1\n"))
    with pytest.raises(commands.FinaleRefused, match=rf"{BUG} \(on in \.env\)"):
        commands.check_finale()
    with pytest.raises(commands.FinaleRefused):
        commands.demo(finale.FINALE_DEMO, client=_Client())
