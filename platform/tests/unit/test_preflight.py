"""Preflight: services, the key check, the drift canary, then the live session (zero tokens)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from loop4_doubles import ScriptedEvaluator, answered, item
from pydantic import SecretStr
from typer.testing import CliRunner

from datapilot.cli import app
from datapilot.contracts import QueryResult, Split
from datapilot.contracts.live import LiveSession, SessionPurpose
from datapilot.loop2_verification.executor import ExecutionError
from datapilot.loop4_hill_climbing import preflight as checks
from datapilot.settings import Settings

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


def _preflight(**overrides):
    started: list[SessionPurpose] = []

    def start(purpose, started_by, timezone):
        started.append(purpose)
        return _session(purpose, started_by, timezone)

    parts = {
        "canary": _canary(),
        "start_session": start,
        "services": lambda: [checks.Check("postgres", True, "4 of 4 migrations")],
        "key": lambda: checks.Check("openai key", True, "class-model"),
        "install": lambda: ["v1"],
    } | overrides
    report = checks.preflight(SessionPurpose.DEVELOPMENT, SETTINGS, **parts)
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
    assert refused.line() == (
        'x  data: club.payments is not readable as the agent\'s role: relation "club.payments" '
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
