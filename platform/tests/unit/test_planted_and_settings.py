"""Planted flags are read only through the registry; models come only from the environment."""

from __future__ import annotations

import pytest

from datapilot import planted
from datapilot.settings import MissingSetting, Settings


def test_a_planted_flag_is_off_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BUG_NAIVE_GUARD", raising=False)
    assert planted.planted("BUG_NAIVE_GUARD") is False


def test_a_planted_flag_turns_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BUG_NAIVE_GUARD", "1")
    assert planted.planted("BUG_NAIVE_GUARD") is True
    assert "BUG_NAIVE_GUARD" in planted.active()


def test_an_unknown_flag_is_an_error() -> None:
    with pytest.raises(KeyError):
        planted.planted("BUG_TYPO")


def test_the_model_must_come_from_the_environment() -> None:
    with pytest.raises(MissingSetting):
        _ = Settings(_env_file=None, openai_model="").agent_model


def test_the_analyzer_team_defaults_to_the_agent_model() -> None:
    settings = Settings(_env_file=None, openai_model="agent-model")
    assert settings.agent_model == "agent-model"
    assert settings.analyzer_model == "agent-model"
    separate = Settings(_env_file=None, openai_model="agent-model", openai_analyzer_model="other")
    assert separate.analyzer_model == "other"


def test_no_model_id_is_hard_coded_in_the_platform(repo_scan) -> None:
    assert repo_scan(r"gpt-[0-9]", "platform/src", "platform/console") == []
