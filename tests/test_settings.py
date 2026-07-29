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
