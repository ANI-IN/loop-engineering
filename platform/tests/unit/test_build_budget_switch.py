"""The build budget binds only the build: DATAPILOT_BUILD_BUDGET=1 turns its lines and its stop line
on; off (a learner's machine), every call is still recorded and nothing is refused or stopped. A
named session's limit holds either way (zero tokens)."""

from __future__ import annotations

from pathlib import Path

import pytest
from budget_doubles import with_test_budget
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, LLMResult
from typer.testing import CliRunner

from datapilot.cli import app
from datapilot.config import pack_config
from datapilot.observability import spend

MODEL = next(iter(pack_config()["prices"]))
SESSION_START = "2026-10-23T22:00:00+00:00"


@pytest.fixture
def ledger(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    with_test_budget(monkeypatch)  # the mechanism's fixed allocation, not the owner's current one
    path = tmp_path / "ledger.sqlite"
    monkeypatch.setenv("DATAPILOT_SPEND_LEDGER", str(path))
    for name in ("DATAPILOT_BUILD_BUDGET", "DATAPILOT_USE_RESERVE", "DATAPILOT_SESSION_SINCE"):
        monkeypatch.delenv(name, raising=False)
    return path


def _spend(dollars: float, activity: str, path: Path, calls: int = 1) -> None:
    per_token = pack_config()["prices"][MODEL]["output"] / 1_000_000
    for _ in range(calls):
        tokens = round(dollars / calls / per_token)
        usage = spend.Usage(0, 0, tokens)
        spend.record(component="analyst", model=MODEL, usage=usage, activity=activity, path=path)


def test_the_switch_is_off_unless_set_to_one(ledger: Path, monkeypatch) -> None:
    assert pack_config()["build_budget"]["enabled_variable"] == "DATAPILOT_BUILD_BUDGET"
    assert not spend.build_budget_on(), "off by default"
    spend.ENV_FILE.write_text("DATAPILOT_BUILD_BUDGET=1\n", encoding="utf-8")
    assert spend.build_budget_on(), "the build's .env turns it on for host commands too"
    monkeypatch.setenv("DATAPILOT_BUILD_BUDGET", "0")  # the environment wins over .env
    assert not spend.build_budget_on()


def test_off_a_learners_activity_is_never_refused_or_stopped(ledger: Path) -> None:
    _spend(1.60, "development", ledger, calls=40)  # past the development line's 1.50
    _spend(9.00, "my-own-experiments", ledger, calls=10)  # past the 10-dollar stop line
    assert spend.check_budget(ledger, activity="development") == pytest.approx(10.60)
    assert spend.check_budget(ledger, activity="my-own-experiments") == pytest.approx(10.60)


@pytest.mark.parametrize("activity", ["development", "my-own-experiments"])
def test_on_the_same_calls_are_stopped(ledger: Path, monkeypatch, activity: str) -> None:
    monkeypatch.setenv("DATAPILOT_BUILD_BUDGET", "1")
    _spend(1.60, "development", ledger, calls=40)
    with pytest.raises(spend.BudgetStop):
        spend.check_budget(ledger, activity=activity)


def test_off_the_ledger_still_records_every_call(ledger: Path) -> None:
    callback = spend.SpendCallback(component="analyst", model=MODEL, activity="my-own-experiments")
    callback.on_chat_model_start({}, [[]])
    usage = {"input_tokens": 100, "output_tokens": 20, "total_tokens": 120}
    message = AIMessage("ok", usage_metadata=usage)  # type: ignore[arg-type]
    callback.on_llm_end(LLMResult(generations=[[ChatGeneration(message=message)]]))
    assert [(a, n) for a, n, _ in spend.by_activity(ledger)] == [("my-own-experiments", 1)]


def test_a_named_session_still_holds_with_the_switch_off(ledger: Path, monkeypatch) -> None:
    """The build's unattended session keeps its limit even before its .env has the switch."""
    monkeypatch.setenv("DATAPILOT_SESSION_SINCE", SESSION_START)
    with pytest.raises(spend.BudgetStop, match="rehearsal line has no allowance this session"):
        spend.check_budget(ledger, activity="screenshots")
    with pytest.raises(spend.BudgetStop, match="no budget line, so nothing this session"):
        spend.check_budget(ledger, activity="my-own-experiments")
    spend.check_budget(ledger, activity="calibration-traps")  # within the session's allowance


def test_make_spend_says_when_the_lines_are_not_enforced(ledger: Path, monkeypatch) -> None:
    result = CliRunner().invoke(app, ["spend"])
    assert result.exit_code == 0 and "the build budget is off" in result.output
    monkeypatch.setenv("DATAPILOT_BUILD_BUDGET", "1")
    assert "the build budget is off" not in CliRunner().invoke(app, ["spend"]).output
