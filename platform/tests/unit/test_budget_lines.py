"""The build budget's lines: every activity counts under one line, a used-up line stops its
activity before the next call, the reserve needs the owner's approval, and the whole build stops
at 10 dollars (zero tokens)."""

from __future__ import annotations

from pathlib import Path

import pytest
from budget_doubles import with_test_budget
from typer.testing import CliRunner

from datapilot.cli import app
from datapilot.config import pack_config
from datapilot.observability import spend

MODEL = next(iter(pack_config()["prices"]))


@pytest.fixture
def ledger(tmp_path: Path, monkeypatch) -> Path:
    with_test_budget(monkeypatch)
    path = tmp_path / "ledger.sqlite"
    monkeypatch.setenv("DATAPILOT_SPEND_LEDGER", str(path))
    monkeypatch.delenv("DATAPILOT_USE_RESERVE", raising=False)
    monkeypatch.setenv("DATAPILOT_BUILD_BUDGET", "1")  # the build's own machines
    return path


def _spend(dollars: float, activity: str, path: Path, calls: int = 1) -> None:
    per_token = pack_config()["prices"][MODEL]["output"] / 1_000_000
    for _ in range(calls):
        tokens = round(dollars / calls / per_token)
        spend.record(
            component="analyst",
            model=MODEL,
            usage=spend.Usage(0, 0, tokens),
            activity=activity,
            path=path,
        )


def test_the_allocation_is_the_owners() -> None:
    budget = pack_config()["build_budget"]
    # the owner raised the total to 10.65 on 25 October 2026, stopping live work at 10.60
    assert (budget["total_usd"], budget["warn_usd"], budget["stop_usd"]) == (10.65, 6.0, 10.6)
    caps = {line.name: line.cap_usd for line in spend.budget_lines()}
    assert caps == {
        "development live checks": 3.8,
        "calibration": 4.7,
        "assignment verification": 5.0,
        "rehearsal": 1.6,
        "reserve": 0.0,
    }
    # the owner's allocation of 24 October moved rehearsal and the reserve to the other lines; since
    # 25 October 2026 the stop line is the only limit that blocks: the lines add up to more
    assert sum(caps.values()) > budget["total_usd"] > budget["stop_usd"]


@pytest.mark.parametrize(
    ("activity", "line"),
    [
        ("development live checks", "development live checks"),
        ("development", "development live checks"),
        ("preflight-development", "development live checks"),
        ("calibration", "calibration"),
        ("calibration-traps", "calibration"),
        ("assignment", "assignment verification"),
        ("assignment verification", "assignment verification"),
        ("rehearsal", "rehearsal"),
        ("screenshots", "rehearsal"),
        ("preflight-rehearsal", "rehearsal"),
        ("preflight-class", "rehearsal"),
    ],
)
def test_every_known_activity_counts_under_one_line(activity: str, line: str) -> None:
    assert spend.line_for(activity).name == line


@pytest.mark.parametrize("activity", ["preflight", "calibrationtraps", "reserve", "test", ""])
def test_an_unknown_activity_is_refused(ledger: Path, activity: str) -> None:
    with pytest.raises(spend.UnknownActivity, match="no budget line"):
        spend.check_budget(ledger, activity=activity)


def test_a_line_stops_before_the_call_that_would_exceed_it(ledger: Path) -> None:
    _spend(1.44, "development live checks", ledger, calls=36)  # 4 cents a call
    spend.check_budget(ledger, activity="development")  # 1.44 + 0.04 is not over 1.50
    _spend(0.03, "preflight-development", ledger)
    with pytest.raises(spend.BudgetStop) as stopped:
        spend.check_budget(ledger, activity="development live checks")
    message = str(stopped.value)
    assert "development live checks line" in message and "$0.0300 left" in message
    assert "reserve" in message
    spend.check_budget(ledger, activity="calibration-traps")  # other lines go on


def test_the_reserve_is_used_only_with_the_owners_approval(ledger: Path, monkeypatch) -> None:
    _spend(2.5, "calibration", ledger, calls=10)
    with pytest.raises(spend.BudgetStop, match="calibration line"):
        spend.check_budget(ledger, activity="calibration-agents")
    monkeypatch.setenv("DATAPILOT_USE_RESERVE", "1")
    spend.check_budget(ledger, activity="calibration-agents")
    _spend(1.5, "calibration-agents", ledger, calls=6)
    with pytest.raises(spend.BudgetStop, match="reserve"):
        spend.check_budget(ledger, activity="calibration-agents")


def test_all_live_work_stops_at_ten_dollars(ledger: Path, monkeypatch) -> None:
    monkeypatch.setenv("DATAPILOT_USE_RESERVE", "1")
    for activity in ("calibration", "assignment", "rehearsal"):
        _spend(2.5, activity, ledger)
    _spend(1.0, "development", ledger)
    _spend(1.5, "calibration-extra", ledger)
    with pytest.raises(spend.BudgetStop, match="stop line"):
        spend.check_budget(ledger, activity="rehearsal")


def test_make_spend_shows_each_line_and_what_is_left(ledger: Path) -> None:
    _spend(0.25, "calibration-traps", ledger)
    result = CliRunner().invoke(app, ["spend"])
    assert result.exit_code == 0, result.output
    assert "calibration" in result.output and "$0.2500 of $2.20, $1.9500 left" in result.output
    assert "reserve" in result.output and "only with the owner's approval" in result.output


SESSION_START = "2026-10-23T22:00:00+00:00"


def _spend_at(dollars: float, activity: str, path: Path, ts: str, calls: int = 1) -> None:
    import sqlite3

    spend.total_usd(path)  # creates the ledger table
    with sqlite3.connect(path) as conn:
        last = conn.execute("SELECT COALESCE(max(id), 0) FROM spend_ledger").fetchone()[0]
    _spend(dollars, activity, path, calls=calls)
    with sqlite3.connect(path) as conn:  # place the new rows before or after the session's start
        conn.execute("UPDATE spend_ledger SET ts = ? WHERE id > ?", (ts, last))


@pytest.fixture
def session(ledger: Path, monkeypatch) -> Path:
    monkeypatch.setenv("DATAPILOT_SESSION_SINCE", SESSION_START)
    return ledger


def test_the_session_limits_are_the_owners() -> None:
    limits = spend.session_limits()
    assert limits is not None and limits.since_variable == "DATAPILOT_SESSION_SINCE"
    assert limits.total_usd == 2.95  # session 6, with the owner's raise of 25 October
    assert limits.lines == {
        "development live checks": 0.9,
        "calibration": 0.43,
        "assignment verification": 1.23,
        "rehearsal": 0.39,
    }


def test_the_session_can_be_named_in_env_file_for_host_commands(ledger: Path, monkeypatch) -> None:
    monkeypatch.delenv("DATAPILOT_SESSION_SINCE", raising=False)
    spend.ENV_FILE.write_text("DATAPILOT_SESSION_SINCE=2026-10-22T20:56:01Z\n", encoding="utf-8")
    assert spend.session_since() == "2026-10-22T20:56:01+00:00"
    monkeypatch.setenv("DATAPILOT_SESSION_SINCE", "")  # the environment wins over .env
    assert spend.session_since() is None


def test_the_reserve_switch_can_come_from_env_file(ledger: Path) -> None:
    assert not spend.reserve_approved()
    spend.ENV_FILE.write_text("DATAPILOT_USE_RESERVE=1\n", encoding="utf-8")
    assert spend.reserve_approved()


def test_no_session_limit_unless_the_session_is_named(ledger: Path) -> None:
    assert spend.session_since() is None
    _spend(2.0, "assignment", ledger, calls=10)
    spend.check_budget(ledger, activity="assignment")  # only the 2.80 line applies


def test_this_session_a_line_stops_at_its_session_cap(session: Path) -> None:
    _spend_at(1.1, "assignment", session, "2026-10-23T23:00:00+00:00", calls=10)
    with pytest.raises(spend.BudgetStop, match="this session") as stopped:
        spend.check_budget(session, activity="assignment")
    assert "assignment verification" in str(stopped.value) and "$0.0000 left" in str(stopped.value)


def test_the_development_line_stops_at_thirty_cents_this_session(session: Path) -> None:
    _spend_at(0.29, "development", session, "2026-10-23T23:00:00+00:00", calls=3)
    with pytest.raises(spend.BudgetStop, match="development live checks line is used up"):
        spend.check_budget(session, activity="development")


def test_spend_before_the_session_does_not_count_this_session(session: Path) -> None:
    _spend_at(1.4, "assignment", session, "2026-10-23T12:00:00+00:00", calls=10)
    spend.check_budget(session, activity="assignment")  # 1.40 earlier, nothing this session yet


def test_a_line_not_listed_for_the_session_gets_nothing(session: Path) -> None:
    with pytest.raises(spend.BudgetStop, match="rehearsal line has no allowance this session"):
        spend.check_budget(session, activity="screenshots")


def test_all_live_work_stops_at_the_session_total(session: Path) -> None:
    _spend_at(0.3, "development", session, "2026-10-23T23:00:00+00:00", calls=10)
    _spend_at(0.95, "calibration", session, "2026-10-23T23:30:00+00:00", calls=10)
    _spend_at(1.05, "assignment", session, "2026-10-24T00:00:00+00:00", calls=13)
    with pytest.raises(spend.BudgetStop, match="session total"):
        spend.check_budget(session, activity="assignment")


def test_make_spend_shows_this_session_against_its_limits(session: Path) -> None:
    _spend_at(0.3, "calibration-traps", session, "2026-10-23T23:00:00+00:00")
    result = CliRunner().invoke(app, ["spend"])
    assert result.exit_code == 0, result.output
    assert f"this session since {SESSION_START}" in result.output
    assert "calibration" in result.output and "$0.3000 of $0.95 this session" in result.output
    assert "$0.3000 of $2.35 this session" in result.output
