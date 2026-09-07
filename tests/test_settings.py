"""Configuration, and the one case 583 green tests never covered.

Every passing case in this file used to set every key, so nothing ever exercised the
journey a first-time cloner actually takes: fill in the model credentials and run.
That path raised `MissingCredential: LANGSMITH_API_KEY is not set`, while README §10
promised LangSmith was optional. A suite that only tests the fully-configured case
cannot see a required setting that should not be.

`test_the_two_model_keys_are_required_and_langsmith_is_not` is that case, and CI runs
the same assertion. The set of required credentials changed with the model policy —
there are two vendors now — but the property being defended did not: LangSmith is
advisory, and a checkout that can call models must start without it.
"""

import pytest

from loopeng.settings import MissingCredential, load_settings


def test_missing_key_names_the_env_var_and_the_fix(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)  # no .env here

    with pytest.raises(MissingCredential) as exc:
        load_settings()

    message = str(exc.value)
    assert "OPENAI_API_KEY" in message
    assert ".env" in message
    # The message must not send a cloner hunting for a credential they do not need —
    # which is now both of the optional ones, not just LangSmith.
    assert "LANGSMITH_API_KEY" not in message
    assert "ANTHROPIC_API_KEY" not in message


def test_the_agent_key_alone_is_enough_to_start(tmp_path, monkeypatch):
    """THE regression test for the journey a cloner actually takes.

    This asserted that BOTH model keys were required, matching a
    `REQUIRED_CREDENTIALS` tuple that listed both — and contradicting README §10 and
    SECURITY.md, which say the Anthropic key is optional because the judge gates
    nothing. The contradiction was visible in this file's own prose: the test below
    described the judge key as one that "gates nothing" while asserting nothing could
    start without it.

    It contradicted them in the direction that turns away a valid checkout. A cloner
    with a working OpenAI key and no Anthropic account could not run the free offline
    paths, let alone measure anything.

    `chdir` into an empty directory so the repo's own `.env` cannot supply a key and
    make this pass for the wrong reason.
    """
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-test")
    monkeypatch.chdir(tmp_path)

    settings = load_settings()

    assert settings.openai_api_key.get_secret_value() == "sk-openai-test"
    assert settings.anthropic_api_key is None
    assert settings.langsmith_api_key is None


def test_the_langsmith_key_is_still_read_when_present(tmp_path, monkeypatch):
    """Optional is not ignored. A key that is set must still reach the client."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-test")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("LANGSMITH_API_KEY", "ls-test")
    monkeypatch.chdir(tmp_path)

    settings = load_settings()

    assert settings.langsmith_api_key is not None
    assert settings.langsmith_api_key.get_secret_value() == "ls-test"


def test_settings_are_frozen(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-test")
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
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-test")
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

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)  # no .env to read

    with pytest.raises(MissingCredential) as exc:
        load_settings()
    assert "OPENAI_API_KEY is not set" in str(exc.value)
    assert ".env.example" in str(exc.value)


def test_every_required_credential_is_reported_not_just_the_first(monkeypatch, tmp_path):
    """An operator half an hour from a session should learn about every missing key in
    one run, rather than fixing one, re-running, and discovering the next.

    Derived from `REQUIRED_CREDENTIALS` rather than listing the variables, so it keeps
    holding whichever credentials that tuple names — including today, when it names
    one.
    """
    from loopeng.settings import REQUIRED_CREDENTIALS, MissingCredential, load_settings

    for field in REQUIRED_CREDENTIALS:
        monkeypatch.delenv(field.upper(), raising=False)
    monkeypatch.chdir(tmp_path)

    with pytest.raises(MissingCredential) as exc:
        load_settings()
    message = str(exc.value)
    for field in REQUIRED_CREDENTIALS:
        assert f"{field.upper()} is not set" in message


def test_each_missing_credential_says_what_it_is_for(monkeypatch, tmp_path):
    """"Set this key" is not a reason. The agent key stops every measurement; the judge
    key stops triage and gates nothing — different consequences, so the fix text says
    which."""
    from loopeng.settings import MissingCredential, load_settings

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)

    with pytest.raises(MissingCredential) as exc:
        load_settings()
    assert "agent and the reference arm" in str(exc.value)


def test_the_judge_key_is_demanded_where_it_is_USED_not_at_startup(monkeypatch, tmp_path):
    """The check moves; it does not disappear.

    Making the judge key optional up front would be a relaxation if that were the end
    of it. It is not: `require_key` raises the same sentence at the moment a judge
    client is constructed, so triage still fails loudly and immediately — and it fails
    for the person who asked for triage rather than for everyone who cloned the repo.
    """
    from loopeng.settings import MissingCredential, load_settings, require_key

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-test")
    monkeypatch.chdir(tmp_path)

    settings = load_settings()  # starts fine

    with pytest.raises(MissingCredential) as exc:
        require_key(settings, "anthropic")
    assert "triages failures and never gates" in str(exc.value)


def test_opting_out_loads_settings_without_a_key(monkeypatch, tmp_path):
    from loopeng.settings import load_settings

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)

    settings = load_settings(require_credential=False)
    assert settings.openai_api_key is None
    assert settings.anthropic_api_key is None
    assert settings.warehouse_seed  # ordinary configuration is readable


def test_opting_out_does_not_buy_the_right_to_spend(monkeypatch, tmp_path):
    """A path that skipped the door still cannot make a request, and the failure
    text is identical to the one the door would have produced."""
    from loopeng.settings import MissingCredential, load_settings, require_key

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-judge-present")
    monkeypatch.chdir(tmp_path)

    settings = load_settings(require_credential=False)
    with pytest.raises(MissingCredential) as deferred:
        require_key(settings, "openai")

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


def test_every_client_construction_goes_through_require_key():
    """The credential check is enforced at the sites that spend, not by convention.

    Reading a `*_api_key` field directly is how a future client site would quietly
    accept `None` and fail with an SDK error naming nothing. There are two vendors
    now, so there are two ways to make that mistake.
    """
    import pathlib

    root = pathlib.Path(__file__).resolve().parent.parent / "src" / "loopeng"
    offenders = []
    for path in root.rglob("*.py"):
        if path.name in ("settings.py", "langsmith_ds.py"):
            continue
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "openai_api_key" in line or "anthropic_api_key" in line:
                offenders.append(f"{path.relative_to(root)}:{n}")
    assert not offenders, (
        f"read a credential directly instead of via require_key(): {offenders}"
    )


def test_exactly_one_module_builds_a_vendor_client():
    """Two vendors is two SDKs, and a second construction site is a second place to
    forget the credential check, the version check, or the usage convention."""
    import pathlib

    root = pathlib.Path(__file__).resolve().parent.parent / "src" / "loopeng"
    builders = sorted(
        str(path.relative_to(root))
        for path in root.rglob("*.py")
        if "openai.OpenAI(" in path.read_text(encoding="utf-8")
        or "anthropic.Anthropic(" in path.read_text(encoding="utf-8")
    )
    assert builders == ["providers.py"], f"clients are constructed in {builders}"


# ---- the setup path the documentation actually tells people to take ----------


def test_copying_the_example_env_file_produces_a_loadable_config(tmp_path, monkeypatch):
    """`cp .env.example .env` must work. It is step 5 of the onboarding.

    This broke the moment the optional variables were documented: writing
    `WAREHOUSE_SEED=` with no value is not "unset", it is the empty string, and
    an int field cannot parse it. Every optional entry is therefore commented out
    with its default shown, and this test is why that stays true.
    """
    import pathlib
    import shutil

    from loopeng.settings import load_settings

    example = pathlib.Path(__file__).resolve().parent.parent / ".env.example"
    shutil.copy(example, tmp_path / ".env")
    with (tmp_path / ".env").open("a", encoding="utf-8") as handle:
        handle.write("OPENAI_API_KEY=sk-openai-not-a-real-key\n")
        handle.write("ANTHROPIC_API_KEY=sk-test-not-a-real-key\n")

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)

    settings = load_settings()
    assert settings.warehouse_seed == 20260729
    assert settings.langsmith_api_key is None


def test_every_uncommented_line_in_the_example_env_is_loadable(tmp_path, monkeypatch):
    """A stricter form of the above: no uncommented entry may carry a value the
    Settings model rejects, and no typed field may be left blank."""
    import pathlib

    example = pathlib.Path(__file__).resolve().parent.parent / ".env.example"
    blank_typed = []
    for n, line in enumerate(example.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        # Only credentials and free-text settings may be blank; anything the model
        # parses into a non-string type may not.
        if value == "" and name.strip() in {"WAREHOUSE_SEED", "RESULTS_DIR",
                                            "WAREHOUSE_PATH"}:
            blank_typed.append(f"{name.strip()} (line {n})")
    assert not blank_typed, (
        f"blank value for a typed field in .env.example: {blank_typed}. "
        f"Comment it out and show the default instead."
    )


def test_an_invalid_value_says_it_is_invalid_rather_than_missing(tmp_path, monkeypatch):
    """"Not set" and "set to nonsense" are different problems, and used to produce
    the same sentence — sending the reader to look for a line already in front
    of them."""
    from loopeng.settings import MissingCredential, load_settings

    (tmp_path / ".env").write_text(
        "ANTHROPIC_API_KEY=sk-test-not-a-real-key\nWAREHOUSE_SEED=banana\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)

    with pytest.raises(MissingCredential) as exc:
        load_settings()
    assert "is set to 'banana'" in str(exc.value)
    assert "is not set" not in str(exc.value)
