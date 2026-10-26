"""Preflight: services, the key check, the drift canary, then the live session (zero tokens)."""

from __future__ import annotations

import shutil
import subprocess
import uuid
from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace

import pytest
from loop4_doubles import ScriptedEvaluator, answered, item
from pydantic import SecretStr
from typer.testing import CliRunner

from datapilot.cli import app
from datapilot.contracts import QueryResult, Split
from datapilot.contracts.live import LiveSession, SessionPurpose
from datapilot.loop2_verification.executor import ExecutionError
from datapilot.loop3_events import budget
from datapilot.loop4_hill_climbing import preflight as checks
from datapilot.settings import PLATFORM, Settings

SETTINGS = Settings(openai_api_key=SecretStr("not-a-real-key"), openai_model="class-model")


def _session(purpose, started_by, timezone) -> LiveSession:
    return LiveSession(
        session_id=uuid.uuid4(),
        purpose=purpose,
        started_at=datetime(2026, 10, 23, 9, 0, tzinfo=UTC),
        started_by=started_by,
        timezone=timezone,
    )


def _canary(trap_passes: bool = False, easy_fails: bool = False):
    def run() -> list[checks.CanaryRun]:
        return [
            checks.CanaryRun("product-count", "easy", not easy_fails, "", None),
            checks.CanaryRun("net-revenue-fiscal-2025", "trap", trap_passes, "", None),
        ]

    return run


def _preflight(purpose: SessionPurpose = SessionPurpose.DEVELOPMENT, **overrides):
    started: list[SessionPurpose] = []

    def start(purpose, started_by, timezone):
        started.append(purpose)
        return _session(purpose, started_by, timezone)

    parts = {
        "canary": _canary(),
        "start_session": start,
        "services": lambda: [checks.Check("postgres", True, "4 of 4 migrations")],
        "budget": lambda: (checks.Check("token budget", True, "0 of 2,000,000 tokens used"), None),
        "key": lambda: checks.Check("openai key", True, "class-model"),
        "install": lambda: ["v1"],
    } | overrides
    report = checks.preflight(purpose, SETTINGS, **parts)
    return report, started


def test_a_clean_preflight_starts_the_session_with_its_purpose() -> None:
    report, started = _preflight()
    assert report.stopped is None and started == [SessionPurpose.DEVELOPMENT]
    assert report.session is not None and report.model_id == "class-model"


def test_a_missing_key_stops_with_the_operations_sentence() -> None:
    found = checks.key_check(Settings(openai_api_key=SecretStr(""), openai_model="m"))
    assert not found.ok and found.detail == checks.KEY_NOT_ACCEPTED


def test_a_rejected_key_stops_with_the_same_sentence() -> None:
    def rejected(key: str, model: str) -> str:
        raise PermissionError("401")

    found = checks.key_check(SETTINGS, rejected)
    assert not found.ok and found.detail == checks.KEY_NOT_ACCEPTED
    report, started = _preflight(key=lambda: found)
    assert report.stopped == checks.KEY_NOT_ACCEPTED and started == []


def test_a_key_whose_project_cannot_use_the_class_model_is_not_accepted() -> None:
    def not_available(key: str, model: str) -> str:
        raise LookupError(model)

    found = checks.key_check(SETTINGS, not_available)
    assert not found.ok and found.detail.startswith(checks.KEY_NOT_ACCEPTED)
    assert "class-model is not available" in found.detail


def test_an_accepted_key_reports_the_model_id_the_api_returns() -> None:
    found = checks.key_check(SETTINGS, lambda key, model: f"{model}-2026-10-01")
    assert found.ok and found.detail == "class-model-2026-10-01"


def test_a_trap_that_passes_stops_preflight_and_asks_for_calibration() -> None:
    report, started = _preflight(canary=_canary(trap_passes=True))
    assert report.stopped == checks.TRAP_PASSED and started == []
    assert "calibration must run again" in report.stopped.lower()


def test_an_easy_question_that_fails_stops_preflight() -> None:
    report, started = _preflight(canary=_canary(easy_fails=True))
    assert report.stopped == checks.EASY_FAILED and started == []


def test_a_service_that_is_down_stops_before_any_model_call() -> None:
    asked: list[str] = []

    def key() -> checks.Check:
        asked.append("key")
        return checks.Check("openai key", True, "m")

    report, started = _preflight(
        services=lambda: [checks.Check("api", False, "not reachable")], key=key
    )
    assert report.stopped and asked == [] and started == []


def test_the_canary_runs_each_question_once_under_the_starting_knowledge() -> None:
    seen: list[str] = []

    def target(question: str, version: str):
        seen.append(version)
        return answered("SELECT 1")

    items = [item("easy-one"), item("trap-one", Split.HOLDOUT)]
    runs = checks.run_canary(
        target,
        ScriptedEvaluator({"easy-one": [True], "trap-one": [False]}),
        items,
        {"easy": ["easy-one"], "traps": ["trap-one"]},
    )
    assert seen == ["v1", "v1"]
    assert [(r.item_id, r.kind, r.as_expected) for r in runs] == [
        ("easy-one", "easy", True),
        ("trap-one", "trap", True),
    ]


def test_the_canary_questions_exist_in_the_benchmark() -> None:
    from datapilot.loop4_hill_climbing.pack_files import load_benchmark

    by_id = {i.id: i for i in load_benchmark()}
    ids = checks.canary_ids()
    assert len(ids["easy"]) == 3 and len(ids["traps"]) == 2
    assert all(not by_id[i].traps for i in ids["easy"])
    assert all(by_id[i].traps for i in ids["traps"])


def test_the_command_takes_a_purpose() -> None:
    result = CliRunner().invoke(app, ["preflight", "--help"])
    assert result.exit_code == 0 and "--purpose" in result.output


class _Answering:
    def get(self, url: str):
        return type("Response", (), {"status_code": 200})()


class _StubData(checks.DataCheck):
    def check(self, executor=None) -> checks.Check:
        return checks.Check("data", True, f"7 {self.rows_are} in {self.qualified}")


class _Counting:
    """An executor double: records the query and answers with one count, or refuses."""

    def __init__(self, count: int | None) -> None:
        self.count, self.queries = count, []

    def run(self, sql: str) -> QueryResult:
        self.queries.append(sql)
        if self.count is None:
            raise ExecutionError("42P01", 'relation "club.payments" does not exist')
        return QueryResult(columns=["n"], rows=[(self.count,)], total_row_count=1, truncated=False)


def test_the_data_check_runs_through_the_executor(select_pack) -> None:
    select_pack("_template")
    data = checks.DataCheck.from_pack()
    executor = _Counting(2785)
    assert data.check(executor).line() == "ok data: 2,785 payments in club.payments"  # type: ignore[arg-type]
    assert executor.queries == ['SELECT count(*) AS n FROM "club"."payments"']
    assert not data.check(_Counting(0)).ok, "an empty table fails"  # type: ignore[arg-type]
    refused = data.check(_Counting(None))  # type: ignore[arg-type]
    # Review round 2: every database message the executor passes on has its quoted part redacted
    # (a cast such as ::regclass quotes a data value there); the check names the table itself.
    assert refused.line() == (
        'x  data: club.payments is not readable as the agent\'s role: relation "<redacted>" '
        "does not exist"
    )


def test_the_service_checks_name_the_pack_and_run_its_data_check(select_pack) -> None:
    select_pack("_template")
    data = _StubData.from_pack()
    found = checks.service_checks(SETTINGS, client=_Answering(), data=data)  # type: ignore[arg-type]
    by_name = {c.name: c for c in found}
    assert found[0] == checks.Check("pack", True, "_template")
    assert by_name["data"].line() == "ok data: 7 payments in club.payments"


def test_the_data_check_and_the_canary_come_from_the_selected_pack(select_pack) -> None:
    query = checks.DataCheck.from_pack().query()
    assert query == 'SELECT count(*) AS n FROM "warehouse"."orders"'
    assert checks.canary_ids()["easy"][0] == "product-count"
    select_pack("_template")
    query = checks.DataCheck.from_pack().query()
    assert query == 'SELECT count(*) AS n FROM "club"."payments"'
    assert checks.canary_ids() == {
        "easy": ["plan-count", "members-north", "members-joined-2024"],
        "traps": ["net-revenue-march-2025", "charges-june-2025"],
    }


def test_a_pack_without_its_checks_stops_preflight_at_the_pack_line(monkeypatch) -> None:
    bare = {"name": "my_pack", "databases": {"allowed_schema": "club"}}
    monkeypatch.setattr(checks, "pack_config", lambda: bare)
    found = checks.service_checks(SETTINGS, client=_Answering())  # type: ignore[arg-type]
    assert found[0] == checks.Check(
        "pack", False, "pack my_pack has no preflight section in its pack.yaml"
    )
    assert "data" not in {c.name for c in found}
    report, started = _preflight(services=lambda: found)
    assert report.stopped and started == []


def test_a_pack_without_a_canary_never_borrows_another_packs_questions() -> None:
    config = {"name": "my_pack", "preflight": {"data_check": {"table": "club.payments"}}}
    with pytest.raises(checks.PackHasNoPreflight, match="my_pack: preflight.canary"):
        checks.canary_ids(config)


# --- the daily token budget (session 6 review, class day: preflight never checked it) ----------
CLASS_PASS = 521_000  # a pass, both finales, a quarter more
DAY = budget.DayBudget(date(2026, 10, 25), 1_700_000, 2_000_000)


def test_preflight_prints_the_eastern_days_tokens_used_cap_and_left() -> None:
    found, refusal = checks.budget_check(
        SessionPurpose.DEVELOPMENT, DAY, CLASS_PASS, timedelta(hours=3)
    )
    assert refusal is None and found.line() == (
        "ok token budget: 1,700,000 of 2,000,000 tokens used on the Eastern time day 2026-10-25, "
        "300,000 left"
    )


def test_a_class_preflight_refuses_with_less_than_one_class_pass_left() -> None:
    found, refusal = checks.budget_check(SessionPurpose.CLASS, DAY, CLASS_PASS, timedelta(hours=3))
    assert not found.ok and "a class pass needs about 521,000" in found.detail
    assert refusal == checks.BUDGET_SHORT.format(until="3 hours 0 minutes", left=300_000)
    assert "midnight Eastern time" in refusal and "course owner's decision" in refusal
    roomy = budget.DayBudget(DAY.day, 1_000_000, 2_000_000)
    assert checks.budget_check(SessionPurpose.CLASS, roomy, CLASS_PASS, timedelta())[1] is None


def test_the_budget_refusal_stops_preflight_before_the_key_and_the_canary() -> None:
    asked: list[str] = []

    def key() -> checks.Check:
        asked.append("key")
        return checks.Check("openai key", True, "m")

    short = checks.budget_check(SessionPurpose.CLASS, DAY, CLASS_PASS, timedelta(hours=1))
    report, started = _preflight(budget=lambda: short, key=key)
    assert report.stopped == short[1] and asked == [] and started == []
    assert report.checks[-1].name == "token budget"


# --- the knowing start of a short class day (session 6 review, round 3, class day) ------------


def test_the_refusal_names_the_session_left_open_and_the_knowing_start_with_todays_count() -> None:
    _, refusal = checks.budget_check(SessionPurpose.CLASS, DAY, CLASS_PASS, timedelta(hours=3))
    assert refusal is not None
    assert "No class session started, so the open session, if any, stays open." in refusal
    assert refusal.endswith(
        "300,000 tokens left, knowingly: make preflight PURPOSE=class ACCEPT_TOKENS_LEFT=300000"
    )


def test_the_exact_count_left_starts_the_class_session_and_says_so() -> None:
    accepted = checks.budget_check(
        SessionPurpose.CLASS, DAY, CLASS_PASS, timedelta(hours=3), accepted_left=300_000
    )
    found, refusal = accepted
    assert refusal is None and found.ok
    assert found.line().endswith(
        "300,000 left; a class pass needs about 521,000; "
        "started knowingly with ACCEPT_TOKENS_LEFT=300000"
    )
    report, started = _preflight(SessionPurpose.CLASS, budget=lambda: accepted)
    assert report.stopped is None and started == [SessionPurpose.CLASS]


@pytest.mark.parametrize("named", [299_999, 300_001, 0, 521_000])
def test_any_other_count_is_refused_as_before(named: int) -> None:
    # a value left from an earlier day, or a guess, never starts a short class day
    found, refusal = checks.budget_check(
        SessionPurpose.CLASS, DAY, CLASS_PASS, timedelta(hours=3), accepted_left=named
    )
    assert not found.ok
    assert refusal == checks.BUDGET_SHORT.format(until="3 hours 0 minutes", left=300_000)


@pytest.mark.parametrize("named", [None, 0, 1])
def test_with_no_token_left_no_knowing_start_is_offered_or_taken(named: int | None) -> None:
    # a class session started with 0 left would block every run it starts (review of 26 October)
    spent = budget.DayBudget(DAY.day, 2_000_000, 2_000_000)
    found, refusal = checks.budget_check(
        SessionPurpose.CLASS, spent, CLASS_PASS, timedelta(hours=3), accepted_left=named
    )
    assert not found.ok and found.detail.startswith("2,000,000 of 2,000,000 tokens used")
    assert refusal == checks.BUDGET_SPENT.format(until="3 hours 0 minutes")
    assert checks.ACCEPT_VARIABLE not in refusal and "No class session started" in refusal
    over = budget.DayBudget(DAY.day, 2_100_000, 2_000_000)  # a run's last call can pass the cap
    assert checks.budget_check(SessionPurpose.CLASS, over, CLASS_PASS, timedelta(), 0)[1] == (
        checks.BUDGET_SPENT.format(until="0 hours 0 minutes")
    )
    rehearsal = checks.budget_check(SessionPurpose.REHEARSAL, spent, CLASS_PASS, timedelta())
    assert rehearsal[1] is None  # only the class session is refused


def test_a_named_count_changes_nothing_on_a_day_with_a_class_pass_left() -> None:
    roomy = budget.DayBudget(DAY.day, 1_000_000, 2_000_000)
    named = checks.budget_check(SessionPurpose.CLASS, roomy, CLASS_PASS, timedelta(), 1_000_000)
    plain = checks.budget_check(SessionPurpose.CLASS, roomy, CLASS_PASS, timedelta())
    assert named == plain and plain[1] is None


def test_the_command_reads_the_count_from_its_option_or_make_variable() -> None:
    import typer

    preflight = typer.main.get_group(app).commands["preflight"]
    option = next(p for p in preflight.params if p.name == "accept_tokens_left")
    assert option.opts == ["--accept-tokens-left"]
    assert option.envvar == checks.ACCEPT_VARIABLE == "ACCEPT_TOKENS_LEFT"


@pytest.mark.skipif(shutil.which("make") is None, reason="GNU make is not installed here")
def test_make_passes_the_command_line_variable_to_the_preflight_command() -> None:
    # make exports a variable set on its command line to the recipe's environment, so
    # `make preflight PURPOSE=class ACCEPT_TOKENS_LEFT=300000` reaches the option's envvar; UV is
    # replaced by a command that prints the variable, and the rest of the recipe becomes a comment
    command = ["make", "-s", "-C", str(PLATFORM.parent), "preflight", "PURPOSE=class"]
    command += ["ACCEPT_TOKENS_LEFT=300000", "UV=printenv ACCEPT_TOKENS_LEFT #"]
    done = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False)
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == "300000"


def test_the_class_pass_threshold_is_a_pack_setting_with_its_measurement() -> None:
    from datapilot.config import pack_config

    assert pack_config()["budgets"]["class_pass_tokens"] == CLASS_PASS
    text = (PLATFORM / "packs" / "datapilot_us" / "pack.yaml").read_text(encoding="utf-8")
    assert "394,313" in text and "25 October 2026" in text
    assert "394,313 + 10,240 + 12,395 = 416,948" in text and "521,185" in text


class _NoRow:
    def execute(self, *_args: object) -> object:
        return SimpleNamespace(fetchone=lambda: None)


def test_a_day_with_no_budget_row_yet_has_used_nothing() -> None:
    noon = datetime(2026, 10, 26, 16, 0, tzinfo=UTC)  # noon Eastern time
    found = budget.today(_NoRow(), noon)  # type: ignore[arg-type]
    assert (found.day, found.used, found.left) == (date(2026, 10, 26), 0, 2_000_000)
    assert budget.until_next_day(noon) == timedelta(hours=12)
    # 1 November 2026: the clock goes back an hour at 2:00, so the day has 25 hours
    assert budget.until_next_day(datetime(2026, 11, 1, 4, 0, tzinfo=UTC)) == timedelta(hours=25)


def test_the_console_check_reads_the_console_port_through_the_settings() -> None:
    moved = Settings(_env_file=None, console_port=8599, api_port=8999)
    assert checks.settings_console_url(moved) == "http://localhost:8599/"
