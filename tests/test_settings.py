"""Configuration, and the one case 583 green tests never covered.

Every passing case in this file used to set BOTH keys, so nothing ever exercised the
journey a first-time cloner actually takes: drop `ANTHROPIC_API_KEY` into `.env` and
run. That path raised `MissingCredential: LANGSMITH_API_KEY is not set`, while README
§10 promised LangSmith was optional. A suite that only tests the fully-configured case
cannot see a required setting that should not be.

`test_only_the_anthropic_key_is_required` is that case, and CI runs the same assertion.
"""

import pytest

from loopeng.settings import MissingCredential, load_settings


def test_missing_key_names_the_env_var_and_the_fix(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)  # no .env here

    with pytest.raises(MissingCredential) as exc:
        load_settings()

    message = str(exc.value)
    assert "ANTHROPIC_API_KEY" in message
    assert ".env" in message
    # The message must not send a cloner hunting for a credential they do not need.
    assert "LANGSMITH_API_KEY" not in message


def test_only_the_anthropic_key_is_required(tmp_path, monkeypatch):
    """THE regression test for the journey. One key in, settings load.

    `chdir` into an empty directory so the repo's own `.env` cannot supply the
    LangSmith key and make this pass for the wrong reason.
    """
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.chdir(tmp_path)

    settings = load_settings()

    assert settings.anthropic_api_key.get_secret_value() == "sk-test"
    assert settings.langsmith_api_key is None


def test_the_langsmith_key_is_still_read_when_present(tmp_path, monkeypatch):
    """Optional is not ignored. A key that is set must still reach the client."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("LANGSMITH_API_KEY", "ls-test")
    monkeypatch.chdir(tmp_path)

    settings = load_settings()

    assert settings.langsmith_api_key is not None
    assert settings.langsmith_api_key.get_secret_value() == "ls-test"


def test_settings_are_frozen(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("LANGSMITH_API_KEY", "ls-test")
    settings = load_settings()
    # Deliberately broad: the assertion is that mutation is rejected at all, not
    # that pydantic raises one particular class. Narrowing it would couple this
    # test to a library internal that is free to change.
    with pytest.raises(Exception):  # noqa: B017
        settings.warehouse_seed = 1


def test_secrets_do_not_render(monkeypatch):
    """A key must never reach a log line or a projector."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-secret-value")
    monkeypatch.setenv("LANGSMITH_API_KEY", "ls-test")
    settings = load_settings()
    assert "sk-secret-value" not in repr(settings)
    assert "sk-secret-value" not in str(settings)
    assert settings.anthropic_api_key.get_secret_value() == "sk-secret-value"
