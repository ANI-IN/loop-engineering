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


# ---- require_credential: the check moves, it does not disappear --------------


def test_the_default_still_refuses_a_checkout_with_no_key(monkeypatch, tmp_path):
    """The whole point of making the field optional was to change nothing here."""
    from loopeng.settings import MissingCredential, load_settings

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)  # no .env to read

    with pytest.raises(MissingCredential) as exc:
        load_settings()
    assert "ANTHROPIC_API_KEY is not set" in str(exc.value)
    assert ".env.example" in str(exc.value)


def test_opting_out_loads_settings_without_a_key(monkeypatch, tmp_path):
    from loopeng.settings import load_settings

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)

    settings = load_settings(require_credential=False)
    assert settings.anthropic_api_key is None
    assert settings.warehouse_seed  # ordinary configuration is readable


def test_opting_out_does_not_buy_the_right_to_spend(monkeypatch, tmp_path):
    """A path that skipped the door still cannot make a request, and the failure
    text is identical to the one the door would have produced."""
    from loopeng.settings import MissingCredential, load_settings, require_api_key

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)

    settings = load_settings(require_credential=False)
    with pytest.raises(MissingCredential) as deferred:
        require_api_key(settings)

    with pytest.raises(MissingCredential) as upfront:
        load_settings()
    assert str(deferred.value) == str(upfront.value)


def test_require_credential_is_keyword_only():
    """Positional would let a caller disable the check by accident."""
    import inspect

    from loopeng.settings import load_settings

    param = inspect.signature(load_settings).parameters["require_credential"]
    assert param.kind is inspect.Parameter.KEYWORD_ONLY
    assert param.default is True


def test_every_client_construction_goes_through_require_api_key():
    """The credential check is enforced at the sites that spend, not by convention.

    Reading `settings.anthropic_api_key` directly is how a future client site
    would quietly accept `None` and fail with an SDK error naming nothing.
    """
    import pathlib

    root = pathlib.Path(__file__).resolve().parent.parent / "src" / "loopeng"
    offenders = []
    for path in root.rglob("*.py"):
        if path.name == "settings.py":
            continue
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "anthropic_api_key" in line:
                offenders.append(f"{path.relative_to(root)}:{n}")
    assert not offenders, (
        f"read the credential directly instead of via require_api_key(): {offenders}"
    )
