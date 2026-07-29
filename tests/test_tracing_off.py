"""The zero-network property, enforced rather than assumed."""

import os

from langsmith.utils import tracing_is_enabled

from loopeng.settings import Settings


def test_tracing_is_disabled_for_the_offline_suite():
    """If this fails, ordinary pytest runs are sending traces over the network and
    the default suite is neither offline nor free. The conftest fixture forces the
    environment variables off; this asserts the SDK actually agrees."""
    assert not tracing_is_enabled()


def test_every_known_tracing_variable_is_falsy():
    for var in ("LANGSMITH_TRACING", "LANGCHAIN_TRACING_V2"):
        value = os.environ.get(var, "false")
        assert value.lower() in ("false", "0", "", "no"), f"{var}={value!r} enables tracing"


def test_settings_default_tracing_to_off(tmp_path, monkeypatch):
    # chdir away from the repo so the developer's own .env cannot mask the default.
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("LANGSMITH_API_KEY", "ls-test")
    monkeypatch.delenv("LANGSMITH_TRACING", raising=False)
    assert Settings().langsmith_tracing is False


def test_the_project_name_defaults_to_the_workshop_project(tmp_path, monkeypatch):
    """Left to the SDK's own default, runs land in a project called "default"
    alongside everything else on the account. A real .env may legitimately override
    this, so the test isolates itself from one and checks the code's default."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("LANGSMITH_API_KEY", "ls-test")
    monkeypatch.delenv("LANGSMITH_PROJECT", raising=False)
    assert Settings().langsmith_project == "loop-eng-workshop"


def test_the_project_name_is_never_the_sdk_default(monkeypatch):
    """Whatever .env says, it must not be "default" — that is the shared bucket."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("LANGSMITH_API_KEY", "ls-test")
    assert Settings().langsmith_project not in ("", "default")
