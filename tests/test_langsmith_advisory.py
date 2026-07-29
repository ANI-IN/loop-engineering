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
