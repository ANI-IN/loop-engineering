"""The check's own stack, zero tokens and no database: a run the stack blocked stops the check
instead of failing a line, the recovery names the check's stack and never the class stack, the
check runs in a live session of the purpose it is given, and its daily token count is reset only on
its own Compose project. The api here is a test double, in a unit test only; the checks always run
live against the real api."""

from __future__ import annotations

import io
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from datapilot.assignments import WITHHELD_LINE, assignment, cost, live, solutions, stack
from datapilot.assignments.report import Report, Stop
from datapilot.contracts import RunStatus
from datapilot.contracts.live import LiveSession, SessionPurpose
from datapilot.names import SECTIONS_BY_SLUG

NOW = datetime(2026, 10, 29, 18, 0, tzinfo=UTC)  # a Thursday, 14:00 Eastern time


def _detail(status: RunStatus):
    return SimpleNamespace(run_id=uuid.uuid4(), status=status, events=[], answer=None)


# --- a run the stack blocked ---------------------------------------------------------------------
def test_a_run_ended_at_the_daily_budget_stops_the_check() -> None:
    api = SimpleNamespace(engaged_by_check=False, engaged_at_cap=False)
    with pytest.raises(Stop) as stopped:
        live.stop_on_blocked(_detail(RunStatus.BLOCKED_BUDGET), api)
    message = str(stopped.value)
    assert "blocked_budget" in message and "budgets.tokens_per_day" in message
    assert "not a fault in your solution" in message and "midnight Eastern time" in message


def test_a_kill_switch_engaged_from_outside_stops_the_check() -> None:
    api = SimpleNamespace(engaged_by_check=False, engaged_at_cap=False)
    with pytest.raises(Stop) as stopped:
        live.stop_on_blocked(_detail(RunStatus.BLOCKED_KILLSWITCH), api)
    assert "python -m datapilot.assignments reset" in str(stopped.value)
    assert "make reset" not in str(stopped.value)


@pytest.mark.parametrize("ours", ["engaged_by_check", "engaged_at_cap"])
def test_the_checks_own_kill_switch_is_judged_as_the_check_expects(ours: str) -> None:
    api = SimpleNamespace(engaged_by_check=False, engaged_at_cap=False)
    setattr(api, ours, True)
    live.stop_on_blocked(_detail(RunStatus.BLOCKED_KILLSWITCH), api)  # no stop


@pytest.mark.parametrize("status", [RunStatus.POSTED, RunStatus.REJECTED, RunStatus.ESCALATED])
def test_an_ordinary_end_is_judged(status: RunStatus) -> None:
    live.stop_on_blocked(_detail(status), SimpleNamespace())


class _Blocked:
    """The api as settle sees it: the run ended at the daily budget."""

    def wait(self, run_id: str, *, seconds: float = 600):
        return _detail(RunStatus.BLOCKED_BUDGET)


def test_settle_stops_on_a_run_blocked_at_the_daily_budget() -> None:
    with pytest.raises(Stop, match="blocked_budget"):
        live.settle(_Blocked(), "run", live.reject_all)  # type: ignore[arg-type]


def test_engage_and_release_record_whose_kill_switch_it_is() -> None:
    api = live.Api.__new__(live.Api)
    api._setup(None)
    calls: list[str] = []
    api.kill_switch = calls.append  # type: ignore[method-assign]
    api.engage()
    assert api.engaged_by_check
    api.release()
    assert not api.engaged_by_check and calls == ["arm", "engage", "release"]


def test_a_stop_inside_a_deterministic_requirement_stops_the_check() -> None:
    report = Report("Assignment 3: Event loop", out=io.StringIO())

    def blocked() -> str | None:
        raise Stop("the stack blocked the job")

    with pytest.raises(Stop):
        report.check(5, "A normal day posts nothing", blocked)
    assert report.results == []


# --- the recovery names the check's own stack ---------------------------------------------------
def test_the_engaged_kill_switch_at_the_gate_names_the_checks_own_reset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from datapilot.assignments import runner

    monkeypatch.setattr(runner, "require_openai_key", lambda: None)
    api = SimpleNamespace(control=lambda: SimpleNamespace(kill_switch="engaged"))
    context = runner.Context(
        assignment=assignment("agent-loop"),
        tree=Path("."),
        report=Report("Assignment 1: Agent loop", out=io.StringIO()),
        stack=stack.Stack(
            "datapilot-assignments", "http://localhost:8100", "http://localhost:8502", uuid.uuid4()
        ),
        api=api,  # type: ignore[arg-type]
        activity="assignment",
    )
    with pytest.raises(Stop) as stopped:
        context.live_gate([], none_because="a test")
    message = str(stopped.value)
    assert "uv run python -m datapilot.assignments reset agent-loop" in message
    assert "http://localhost:8502" in message
    assert "make reset" not in message


def test_the_reset_of_the_checks_stack_never_runs_on_services_already_running(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATAPILOT_ASSIGNMENT_STACK", "running")
    with pytest.raises(Stop, match="not the check's own stack"):
        stack.reset_check_stack("agent-loop", "assignment")


def test_the_reset_of_the_checks_stack_refuses_the_class_project(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DATAPILOT_ASSIGNMENT_STACK", raising=False)
    monkeypatch.setattr(stack, "configure", lambda activity: None)
    monkeypatch.setenv("COMPOSE_PROJECT_NAME", stack.CLASS_PROJECT)
    with pytest.raises(Stop, match="never runs on the class stack"):
        stack.reset_check_stack("agent-loop", "assignment")


def _reset_without_a_stack(monkeypatch: pytest.MonkeyPatch, published: str | None) -> list[str]:
    """The reset with its configuration, Docker, and database left out: returns the sections it
    reset, so a refused reset returns none."""
    from datapilot.loop3_events import commands

    done: list[str] = []
    monkeypatch.delenv("DATAPILOT_ASSIGNMENT_STACK", raising=False)
    monkeypatch.delenv("COMPOSE_PROJECT_NAME", raising=False)
    monkeypatch.setattr(stack, "configure", lambda activity: None)
    monkeypatch.setattr(stack, "published_postgres_port", lambda project: published)
    monkeypatch.setattr(
        commands, "reset", lambda slug: done.append(slug) or SimpleNamespace(lines=lambda: [])
    )
    monkeypatch.setattr(stack, "reset_daily_tokens", lambda project: 0)
    return done


def test_the_class_stacks_ports_are_its_compose_defaults() -> None:
    assert stack.class_ports() == {
        "POSTGRES_PORT": "5432",
        "API_PORT": "8000",
        "CONSOLE_PORT": "8501",
    }


@pytest.mark.parametrize(
    ("name", "port"), [("POSTGRES_PORT", "5432"), ("API_PORT", "8000"), ("CONSOLE_PORT", "8501")]
)
def test_the_reset_refuses_a_port_of_the_class_stack(
    monkeypatch: pytest.MonkeyPatch, name: str, port: str
) -> None:
    done = _reset_without_a_stack(monkeypatch, published=port)
    for other, value in stack.DEFAULTS.items():
        if other != "COMPOSE_PROJECT_NAME":
            monkeypatch.setenv(other, value)
    monkeypatch.setenv(name, port)
    with pytest.raises(Stop, match="class stack's port"):
        stack.reset_check_stack("agent-loop", "assignment")
    assert done == [], "nothing was reset"


@pytest.mark.parametrize("published", ["55433", None])
def test_the_reset_refuses_a_port_its_own_project_does_not_publish(
    monkeypatch: pytest.MonkeyPatch, published: str | None
) -> None:
    done = _reset_without_a_stack(monkeypatch, published=published)
    monkeypatch.setenv("POSTGRES_PORT", "55434")  # a typo, or another project's port
    with pytest.raises(Stop, match="belongs to another stack"):
        stack.reset_check_stack("agent-loop", "assignment")
    assert done == []


def test_the_reset_runs_on_the_port_its_own_project_publishes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    done = _reset_without_a_stack(monkeypatch, published="55434")
    monkeypatch.setenv("COMPOSE_PROJECT_NAME", "datapilot-review")
    monkeypatch.setenv("POSTGRES_PORT", "55434")
    lines = stack.reset_check_stack("hill-climbing-loop", "assignment")
    assert done == ["hill-climbing-loop"]
    assert "Compose project datapilot-review (Postgres on port 55434)" in lines[0]


def test_the_published_port_is_read_from_dockers_port_list() -> None:
    assert stack._host_port("127.0.0.1:55434->5432/tcp") == "55434"
    assert stack._host_port("0.0.0.0:5432->5432/tcp, :::5432->5432/tcp") == "5432"
    assert stack._host_port("8000/tcp") is None


def test_the_printed_reset_names_the_checks_project_and_port(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("COMPOSE_PROJECT_NAME", raising=False)
    monkeypatch.delenv("POSTGRES_PORT", raising=False)
    plain = "uv run python -m datapilot.assignments reset hill-climbing-loop"
    assert stack.reset_command("hill-climbing-loop") == plain
    monkeypatch.setenv("COMPOSE_PROJECT_NAME", "datapilot-review")
    monkeypatch.setenv("POSTGRES_PORT", "55434")
    assert stack.reset_command("hill-climbing-loop") == (
        f"COMPOSE_PROJECT_NAME=datapilot-review POSTGRES_PORT=55434 {plain}"
    )


def test_a_kill_switch_stop_names_the_assignment_and_the_stack(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPOSE_PROJECT_NAME", "datapilot-review")
    monkeypatch.setenv("POSTGRES_PORT", "55434")
    api = SimpleNamespace(engaged_by_check=False, engaged_at_cap=False, slug="event-loop")
    with pytest.raises(Stop) as stopped:
        live.stop_on_blocked(_detail(RunStatus.BLOCKED_KILLSWITCH), api)
    message = str(stopped.value)
    assert "COMPOSE_PROJECT_NAME=datapilot-review POSTGRES_PORT=55434 uv run python" in message
    assert "reset event-loop" in message and "<slug>" not in message


@pytest.mark.parametrize("running", [True, False])
def test_the_daily_token_count_is_reset_only_on_the_checks_own_project(
    monkeypatch: pytest.MonkeyPatch, running: bool
) -> None:
    if running:
        monkeypatch.setenv("DATAPILOT_ASSIGNMENT_STACK", "running")
        project = stack.DEFAULTS["COMPOSE_PROJECT_NAME"]
    else:
        monkeypatch.delenv("DATAPILOT_ASSIGNMENT_STACK", raising=False)
        project = stack.CLASS_PROJECT
    with pytest.raises(Stop, match="its own Compose project only"):
        stack.reset_daily_tokens(project)


# --- the live session the check runs in ----------------------------------------------------------
def _session(purpose: SessionPurpose, started: datetime) -> LiveSession:
    return LiveSession(
        session_id=uuid.uuid4(),
        purpose=purpose,
        started_at=started,
        started_by="make preflight",
        timezone="UTC",
    )


def test_without_a_purpose_the_open_session_is_kept() -> None:
    old = _session(SessionPurpose.DEVELOPMENT, NOW - timedelta(days=6))
    assert stack.keeps_open_session(old, None, NOW)
    assert not stack.keeps_open_session(None, None, NOW)


def test_the_review_never_runs_in_an_older_session() -> None:
    review = SessionPurpose.THURSDAY_REVIEW
    assert stack.keeps_open_session(_session(review, NOW - timedelta(hours=2)), review, NOW)
    rehearsal = _session(review, NOW - timedelta(days=2))
    assert not stack.keeps_open_session(rehearsal, review, NOW)
    development = _session(SessionPurpose.DEVELOPMENT, NOW - timedelta(hours=1))
    assert not stack.keeps_open_session(development, review, NOW)


def test_the_purpose_comes_from_purpose(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PURPOSE", raising=False)
    assert stack.session_purpose() is None
    monkeypatch.setenv("PURPOSE", "thursday-review")
    assert stack.session_purpose() is SessionPurpose.THURSDAY_REVIEW
    monkeypatch.setenv("PURPOSE", "review")
    with pytest.raises(Stop, match="not a session purpose"):
        stack.session_purpose()


# --- the typical cost beside the estimate --------------------------------------------------------
def test_the_estimate_prints_the_typical_cost_beside_it() -> None:
    planned = [cost.Planned("analyst runs", 12, "gpt-6-luna")]
    lines = cost.estimate_lines(planned, typical="about 0.4 cents")
    assert lines[0].startswith("This check makes live model calls, about ")
    assert any(line.strip().startswith("Typical:") and "about 0.4 cents" in line for line in lines)
    assert not any("Typical:" in line for line in cost.estimate_lines(planned))


def test_an_estimated_typical_cost_is_never_printed_as_spent() -> None:
    planned = [cost.Planned("analyst runs", 12, "gpt-6-luna")]
    lines = cost.estimate_lines(planned, typical="about 38 cents", typical_estimated=True)
    typical = [line for line in lines if line.strip().startswith("Typical:")]
    assert len(typical) == 1
    assert "is estimated at about 38 cents" in typical[0] and "has spent" not in typical[0]
    measured = cost.estimate_lines(planned, typical="about 0.4 cents")
    assert any("has spent about 0.4 cents" in line for line in measured)


@pytest.mark.parametrize("slug", sorted(SECTIONS_BY_SLUG))
def test_every_check_states_its_typical_cost(slug: str) -> None:
    source = assignment(slug).check_file.read_text(encoding="utf-8")
    assert "typical=" in source, f"{slug}: live_gate(..., typical=...) prints the measured cost"


# --- apply-solution -------------------------------------------------------------------------------
def _public_copy(root: Path) -> Path:
    root.mkdir(parents=True)
    (root / ".gitignore").write_text(f".env\n{WITHHELD_LINE}\n", encoding="utf-8")
    for section in SECTIONS_BY_SLUG.values():
        (root / section.folder / "assignment").mkdir(parents=True)
        (root / section.folder / "assignment" / "check.py").write_text("", encoding="utf-8")
    return root


def test_apply_in_a_public_copy_stops_with_the_thursday_message(tmp_path: Path) -> None:
    source = _public_copy(tmp_path / "public")
    dest = tmp_path / "work" / "agent-loop-reference"
    with pytest.raises(Stop) as stopped:
        solutions.apply("agent-loop", "reference", source=source, dest=dest)
    assert "withheld until the Thursday review" in str(stopped.value)
    assert not dest.exists(), "nothing is copied, and nothing reports a solution applied"


def test_verify_in_a_public_copy_stops_before_any_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(solutions, "solutions_withheld", lambda tree=None: True)
    monkeypatch.setattr(solutions, "_run_captured", lambda *a: pytest.fail("a check ran"))
    with pytest.raises(Stop, match="withheld until the Thursday review"):
        solutions.verify()


def test_a_variant_with_nothing_to_apply_stops(tmp_path: Path) -> None:
    source = tmp_path / "private"
    folder = source / SECTIONS_BY_SLUG["agent-loop"].folder / "assignment" / "solution"
    (folder / "reference").mkdir(parents=True)
    with pytest.raises(Stop, match="nothing to apply"):
        solutions.apply("agent-loop", "reference", source=source, dest=tmp_path / "dest")


def test_apply_never_replaces_an_existing_copy_unasked(tmp_path: Path) -> None:
    source = _public_copy(tmp_path / "source")
    dest = tmp_path / "work" / "agent-loop-starter"
    dest.mkdir(parents=True)
    (dest / "my-notes.txt").write_text("my own change", encoding="utf-8")
    with pytest.raises(Stop, match="FORCE=1"):
        solutions.apply("agent-loop", "starter", source=source, dest=dest)
    assert (dest / "my-notes.txt").read_text(encoding="utf-8") == "my own change"
    solutions.apply("agent-loop", "starter", source=source, dest=dest, force=True)
    assert not (dest / "my-notes.txt").exists()
    assert (dest / ".gitignore").is_file()


def test_the_apply_command_reads_force_from_make(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from datapilot.assignments.__main__ import main

    seen: dict[str, bool] = {}

    def fake_apply(slug: str, variant: str, *, force: bool = False) -> Path:
        seen["force"] = force
        return tmp_path

    monkeypatch.setattr(solutions, "apply", fake_apply)
    monkeypatch.setenv("FORCE", "1")
    assert main(["apply", "agent-loop", "starter"]) == 0
    assert seen["force"] is True
    monkeypatch.delenv("FORCE")
    assert main(["apply", "agent-loop", "starter"]) == 0
    assert seen["force"] is False


def test_a_stop_in_a_command_exits_stopped_with_its_message(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from datapilot.assignments.__main__ import main

    def refused(*args, **kwargs):
        raise Stop("The solutions are withheld until the Thursday review")

    monkeypatch.setattr(solutions, "apply", refused)
    assert main(["apply", "agent-loop", "reference"]) == 2
    assert "withheld until the Thursday review" in capsys.readouterr().out
