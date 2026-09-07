"""LangSmith is advisory. results/*.json is the system of record.

The property under test: a sweep cell must complete correctly, and write a complete
and correct results file, with LangSmith raising on every call. If that does not
hold, a bad network turns into lost measurements — and the measurements are the
entire deliverable.
"""

import json

import pytest

from loopeng.langsmith_ds import advisory, upload_gold
from loopeng.metric import Metric, MetricStore
from loopeng.usage import CallUsage, UsageLedger


class Unreachable(RuntimeError):
    pass


def _exploding_client(*args, **kwargs):
    raise Unreachable("LangSmith is down")


@pytest.fixture
def langsmith_down(monkeypatch):
    monkeypatch.setattr("loopeng.langsmith_ds._client", _exploding_client)


# ---- the core guarantee -----------------------------------------------------


def test_a_cell_completes_and_writes_results_with_langsmith_down(langsmith_down, tmp_path):
    """The whole rule in one test: run a cell, LangSmith raises throughout, and the
    results file is still complete and correct."""
    store = MetricStore()
    ledger = UsageLedger()

    # A cell: some work, its usage, its metric, and a trace side-effect that fails.
    for outcome in ("ok", "ok", "error"):
        ledger.record(CallUsage("claude-haiku-4-5", outcome, input_tokens=100, output_tokens=40))

    trace = upload_gold([])
    assert trace.ok is False, "the stub must actually be failing, or this proves nothing"
    assert "Unreachable" in trace.error

    store.put("cell.pass_rate", Metric.from_counts(successes=2, n=3))
    results = tmp_path / "results.json"
    store.save(results)

    # The measured result is complete and correct despite the failure.
    reloaded = MetricStore.load(results)
    assert reloaded.get("cell.pass_rate").n == 3
    assert reloaded.get("cell.pass_rate").value == pytest.approx(2 / 3)
    assert ledger.totals()["n_calls"] == 3
    assert ledger.totals()["output_tokens"] == 120


def test_upload_failure_is_reported_not_raised(langsmith_down):
    """A raise here would abort the sweep partway and lose every later cell."""
    result = upload_gold([])
    assert result.ok is False
    assert result.value is None
    assert result.error


def test_the_results_file_is_valid_json_when_langsmith_is_down(langsmith_down, tmp_path):
    store = MetricStore()
    store.put("a.b", Metric.from_counts(successes=1, n=4))
    upload_gold([])
    path = tmp_path / "results.json"
    store.save(path)
    assert json.loads(path.read_text())["a.b"]["n"] == 4


# ---- the wrapper itself -----------------------------------------------------


def test_advisory_returns_the_value_on_success():
    result = advisory("noop", lambda: 42)
    assert result.ok is True
    assert result.value == 42
    assert result.error is None


def test_advisory_swallows_any_exception_type():
    """Auth, transport, rate limit, or a schema change in an unpinned version — none
    of them may take down a sweep whose results live in results/*.json."""
    for exception in (Unreachable("down"), ValueError("bad"), KeyError("missing"), OSError()):

        def raise_it(exc=exception):
            raise exc

        result = advisory("noop", raise_it)
        assert result.ok is False
        assert result.error


def test_advisory_records_the_error_text_for_the_report():
    result = advisory("noop", lambda: (_ for _ in ()).throw(Unreachable("no route to host")))
    assert "no route to host" in result.error
    assert "Unreachable" in result.error


# ---- an absent key is a degradation, not a startup error --------------------
#
# §15 says LangSmith is advisory and never the system of record. The setting used to
# be declared required, which made that sentence false and forced the public exhibit
# to inject a fake value. These assert the promise now holds.


@pytest.fixture
def no_langsmith_key(tmp_path, monkeypatch):
    """No key, and no `.env` in reach that could supply one."""
    import loopeng.langsmith_ds as ds

    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(ds, "_warned_absent", False)
    return ds


def test_an_absent_key_degrades_to_a_no_op(no_langsmith_key):
    result = upload_gold([])
    assert result.ok is False
    assert result.value is None
    assert "LANGSMITH_API_KEY" in result.error, "the failure must name the variable"


def test_the_absent_key_warning_names_the_variable_once(no_langsmith_key, monkeypatch):
    """One warning per process. A sweep uploads repeatedly and a per-call warning
    would bury the cell progress it sits beside."""
    warnings = []
    monkeypatch.setattr(
        no_langsmith_key.log, "warning", lambda event, **kw: warnings.append((event, kw))
    )

    upload_gold([])
    upload_gold([])
    upload_gold([])

    configured = [kw for event, kw in warnings if event == "langsmith_not_configured"]
    assert len(configured) == 1, f"warned {len(configured)} times, expected once"
    assert configured[0]["variable"] == "LANGSMITH_API_KEY"
    assert "results/*.json" in configured[0]["unaffected"]


def test_the_absent_key_never_reaches_a_client(no_langsmith_key, monkeypatch):
    """No key means no `Client(...)` is constructed at all — not one built with None."""
    built = []
    monkeypatch.setattr(no_langsmith_key, "credential", lambda: None)
    monkeypatch.setattr(no_langsmith_key, "warn_not_configured", lambda op: built.append(op))

    with pytest.raises(no_langsmith_key.LangSmithNotConfigured):
        no_langsmith_key._client()

    assert built == ["client"]


# ---- an empty variable is not a configured empty key -------------------------


def test_a_blank_langsmith_key_degrades_instead_of_building_a_client(tmp_path,
                                                                    monkeypatch):
    """`.env.example` ships `LANGSMITH_API_KEY=` and the onboarding says to leave
    it that way. pydantic read that as `SecretStr('')`, which is not None — so
    `credential()` returned `''`, the `if api_key is None` guard did not fire, and
    the code built `Client(api_key='')`.

    Following the documented setup exactly therefore produced an auth failure at
    the first network call, instead of the no-op-with-one-warning that §15,
    SECURITY.md and langsmith_ds's own docstring all promise.
    """
    from loopeng.langsmith_ds import credential
    from loopeng.settings import load_settings

    (tmp_path / ".env").write_text(
        "OPENAI_API_KEY=sk-openai-not-a-real-key\n"
        "ANTHROPIC_API_KEY=sk-test-not-a-real-key\n"
        "LANGSMITH_API_KEY=\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)

    assert load_settings().langsmith_api_key is None
    assert credential() is None


def test_a_whitespace_only_key_is_also_absent(tmp_path, monkeypatch):
    from loopeng.settings import load_settings

    (tmp_path / ".env").write_text(
        "OPENAI_API_KEY=sk-openai-not-a-real-key\n"
        "ANTHROPIC_API_KEY=sk-test-not-a-real-key\n"
        "LANGSMITH_API_KEY=   \n",
        encoding="utf-8",
    )
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    assert load_settings().langsmith_api_key is None


def test_a_blank_required_key_is_missing_rather_than_empty(tmp_path, monkeypatch):
    """The same rule on a required key: a blank line must raise the message naming the
    variable, not send an empty key to the API.

    This used to plant a blank `ANTHROPIC_API_KEY`, which stopped being a required
    credential when the judge turned out to gate nothing — so it would have passed for
    the wrong reason. The required set is read from `REQUIRED_CREDENTIALS`.
    """
    from loopeng.settings import REQUIRED_CREDENTIALS, MissingCredential, load_settings

    field = REQUIRED_CREDENTIALS[0]
    (tmp_path / ".env").write_text(f"{field.upper()}=\n", encoding="utf-8")
    for name in REQUIRED_CREDENTIALS:
        monkeypatch.delenv(name.upper(), raising=False)
    monkeypatch.chdir(tmp_path)

    with pytest.raises(MissingCredential) as exc:
        load_settings()
    assert f"{field.upper()} is not set" in str(exc.value)


def test_a_real_key_still_arrives_intact(tmp_path, monkeypatch):
    """The narrowing must not eat a legitimate value."""
    from loopeng.settings import load_settings

    (tmp_path / ".env").write_text(
        "OPENAI_API_KEY=sk-openai-not-a-real-key\n"
        "ANTHROPIC_API_KEY=sk-test-not-a-real-key\n"
        "LANGSMITH_API_KEY=lsv2-not-real\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    assert load_settings().langsmith_api_key.get_secret_value() == "lsv2-not-real"


# ---- the feedback schema ----------------------------------------------------
#
# Four scores were specified before the FX split was measured. The fifth exists
# because that split is the session's L2 content, and without it the finding lives
# in the charts and not in the traces — which is backwards, since the trace is where
# somebody goes to ask why one item scored the way it did.


def _judgement(**kwargs):
    from loopeng.agent.classify import Judgement, Outcome

    base = {
        "item_id": "p04_gross_revenue__00",
        "model_id": "gpt-5.6-luna",
        "outcome": Outcome.CORRECT,
        "termination": "success",
    }
    return Judgement(**{**base, **kwargs})


def test_every_declared_feedback_key_is_written_for_every_item():
    """A key that is declared and sometimes absent is worse than one that is not
    declared: the UI shows it, so a reader assumes the blank means something."""
    from loopeng.langsmith_ds import FEEDBACK_KEYS, feedback_scores

    for judgement in (
        _judgement(),
        _judgement(outcome=__import__(
            "loopeng.agent.classify", fromlist=["Outcome"]).Outcome.SILENT_ERROR),
        _judgement(outcome=__import__(
            "loopeng.agent.classify",
            fromlist=["Outcome"]).Outcome.SIGNALLED_MISSING_INFO),
    ):
        written = {entry["key"] for entry in feedback_scores(judgement, 0.01)}
        assert written == set(FEEDBACK_KEYS), judgement.outcome


def test_the_abstention_score_fires_only_on_an_abstention():
    from loopeng.agent.classify import Outcome
    from loopeng.langsmith_ds import feedback_scores

    def score(judgement):
        return next(e for e in feedback_scores(judgement, 0.0)
                    if e["key"] == "signalled_missing_info")["score"]

    assert score(_judgement(outcome=Outcome.SIGNALLED_MISSING_INFO)) == 1.0
    assert score(_judgement(outcome=Outcome.SILENT_ERROR)) == 0.0
    assert score(_judgement(outcome=Outcome.CORRECT)) == 0.0


def test_an_abstention_scores_zero_accuracy_rather_than_no_score():
    """An absent score shrinks the accuracy denominator, which turns "declined"
    into "not asked" — and that flatters exactly the arm that declines most."""
    from loopeng.agent.classify import Outcome
    from loopeng.langsmith_ds import feedback_scores

    entry = next(e for e in feedback_scores(
        _judgement(outcome=Outcome.SIGNALLED_MISSING_INFO), 0.0)
        if e["key"] == "execution_accuracy")
    assert entry["score"] == 0.0


def test_the_rule_violation_score_names_the_rule():
    from loopeng.agent.classify import Outcome
    from loopeng.langsmith_ds import feedback_scores

    entry = next(e for e in feedback_scores(
        _judgement(outcome=Outcome.SILENT_ERROR,
                   attributed_rules=("soft_delete", "internal_accounts"),
                   ambiguous=True), 0.0)
        if e["key"] == "rule_violation")
    assert entry["value"] == "soft_delete or internal_accounts"
    assert "ambiguous" in entry["comment"]


def test_dollars_stay_labelled_as_estimated():
    from loopeng.langsmith_ds import feedback_scores

    entry = next(e for e in feedback_scores(_judgement(), 0.0123)
                 if e["key"] == "cost_usd")
    assert entry["score"] == 0.0123
    assert "estimated" in entry["comment"]


# ---- the annotation queue asks the right question ---------------------------


def test_the_queue_pairs_the_confabulation_against_the_refusal():
    """Not A-vs-C, which was the original plan and is a generic question with a
    predictable answer. This asks the one the session is about."""
    from loopeng.langsmith_ds import FX_RUBRIC_INSTRUCTIONS, FX_RUBRIC_ITEMS

    assert "WRONG by the automated metric" in FX_RUBRIC_INSTRUCTIONS
    assert "not being asked which is correct" in FX_RUBRIC_INSTRUCTIONS

    keys = {item["feedback_key"] for item in FX_RUBRIC_ITEMS}
    assert keys == {"prefer_in_production", "would_have_noticed"}
    choices = FX_RUBRIC_ITEMS[0]["value_descriptions"]
    assert set(choices) == {"invented_a_rate", "named_what_was_missing",
                            "no_preference"}


def test_rating_cannot_start_a_model_call():
    """The queue holds runs that already happened. Anything else would be an
    unbounded spend surface with a link on a projector."""
    import inspect

    from loopeng import langsmith_ds

    source = inspect.getsource(langsmith_ds.enqueue_for_rating)
    assert "add_runs_to_annotation_queue" in source
    assert "run_question" not in source and "complete(" not in source


# ---- the LangChain boundary --------------------------------------------------


def test_langchain_is_imported_in_exactly_one_place():
    """§15 records the decision not to use LangChain, and that decision is about the
    LOOPS — its rubric middleware scores with an LLM judge, which this project
    refuses as a blocking check.

    A serialisation format for pushing a prompt to LangSmith is not that. But the
    boundary has to be enforced rather than intended, so: exactly one module may
    import it, and none of the loop packages may.
    """
    import pathlib

    root = pathlib.Path(__file__).resolve().parent.parent / "src" / "loopeng"
    importers = sorted(
        str(path.relative_to(root))
        for path in root.rglob("*.py")
        if "langchain" in path.read_text(encoding="utf-8")
    )
    assert importers == ["langsmith_ds.py"], f"langchain reached {importers}"


def test_no_loop_module_imports_langchain():
    """The same property from the other direction, stated where a reader looks."""
    import pathlib

    root = pathlib.Path(__file__).resolve().parent.parent / "src" / "loopeng"
    for package in ("agent", "verify", "sweep", "queue"):
        for path in (root / package).rglob("*.py"):
            assert "langchain" not in path.read_text(encoding="utf-8"), path


# ---- prompts are versions of one thing, not two code paths ------------------


def test_both_prompt_levels_have_a_versioned_name():
    from loopeng.langsmith_ds import PROMPT_NAMES
    from loopeng.prompts import LEVELS

    assert set(PROMPT_NAMES) == set(LEVELS)
    assert len(set(PROMPT_NAMES.values())) == len(LEVELS), "two levels, two names"


def test_pushing_prompts_without_a_key_degrades_rather_than_raising(no_langsmith_key):
    from loopeng.langsmith_ds import push_prompts

    result = push_prompts()
    assert not result.ok
    assert "LANGSMITH_API_KEY" in result.error
