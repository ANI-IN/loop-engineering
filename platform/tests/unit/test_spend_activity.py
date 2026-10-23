"""The spend activity travels with the work: a model built for a job records its calls under the
job's activity, and falls back to DATAPILOT_SPEND_ACTIVITY only when the job names none (zero
tokens: the callback is driven directly, no model is called)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, LLMResult

from datapilot.config import pack_config
from datapilot.loop1_agent.models import openai_factory
from datapilot.observability import spend
from datapilot.settings import Settings, get_settings

MODEL = next(iter(pack_config()["prices"]))


@pytest.fixture
def ledger(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "ledger.sqlite"
    monkeypatch.setenv("DATAPILOT_SPEND_LEDGER", str(path))
    monkeypatch.setenv("DATAPILOT_SPEND_ACTIVITY", "development")
    monkeypatch.setenv("DATAPILOT_BUILD_BUDGET", "1")
    get_settings.cache_clear()
    yield path
    get_settings.cache_clear()


def one_call(callback: spend.SpendCallback) -> None:
    callback.on_chat_model_start({}, [[]])
    usage = {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15}
    message = AIMessage("ok", usage_metadata=usage)  # type: ignore[arg-type]
    callback.on_llm_end(LLMResult(generations=[[ChatGeneration(message=message)]]))


def activities(path: Path) -> list[tuple[str, str]]:
    with sqlite3.connect(path) as conn:
        return conn.execute("SELECT activity, run_id FROM spend_ledger ORDER BY id").fetchall()


def test_a_jobs_activity_wins_over_the_process_environment(ledger: Path) -> None:
    for run_id, activity in (("r1", "calibration-traps"), ("r2", None), ("r3", "")):
        callback = spend.SpendCallback(
            component="analyst", model=MODEL, run_id=run_id, activity=activity
        )
        one_call(callback)
    assert activities(ledger) == [
        ("calibration-traps", "r1"),
        ("development", "r2"),
        ("development", "r3"),
    ]


def test_the_budget_check_uses_the_jobs_activity(ledger: Path) -> None:
    callback = spend.SpendCallback(component="analyst", model=MODEL, activity="nobody")
    with pytest.raises(spend.UnknownActivity):
        callback.on_chat_model_start({}, [[]])


def test_the_live_factory_hands_the_activity_to_every_model() -> None:
    settings = Settings(_env_file=None, openai_model=MODEL, openai_api_key="sk-test")
    build = openai_factory(run_id="r1", activity="screenshots", settings=settings)
    for component in ("analyst", "schema_scout", "reviewer"):
        assert build(component).callbacks[0].activity == "screenshots"
    assert openai_factory(settings=settings)("analyst").callbacks[0].activity is None


def test_starters_send_their_own_activity(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATAPILOT_SPEND_ACTIVITY", "preflight-class")
    get_settings.cache_clear()
    try:
        assert spend.activity_headers() == {spend.ACTIVITY_HEADER: "preflight-class"}
    finally:
        get_settings.cache_clear()
