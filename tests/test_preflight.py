"""The cheapest live path, checked offline.

The whole point of preflight is that it runs before anything expensive, so its own
tests must not spend either. Every network step here goes through a stub client, and
the offline steps run for real — they are free.
"""

from pathlib import Path
from types import SimpleNamespace

import anthropic
import httpx
import pytest

from loopeng import preflight
from loopeng.registry import REGISTRY


class StubClient:
    """Answers every role. Records which model ids it was asked for."""

    def __init__(self):
        self.models = []
        self.kwargs = []
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, *, model, messages, **kwargs):
        self.models.append(model)
        self.kwargs.append(kwargs)
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text="ok")],
            usage=SimpleNamespace(input_tokens=12, output_tokens=2),
        )


class RefusingClient:
    def __init__(self, status=401, exc=None):
        self.calls = 0
        self._exc = exc or anthropic.AuthenticationError(
            "Error code: 401 - invalid x-api-key",
            response=httpx.Response(
                status, request=httpx.Request("POST", "https://api.anthropic.com/")
            ),
            body=None,
        )
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.calls += 1
        raise self._exc


@pytest.fixture
def keyed(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    return tmp_path


# ---- the key check ----------------------------------------------------------


def test_a_missing_key_fails_by_name(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)

    step = preflight.check_key()

    assert not step.ok
    assert "ANTHROPIC_API_KEY" in step.detail
    assert ".env" in step.fix


def test_the_key_value_is_never_printed(keyed):
    step = preflight.check_key()
    assert step.ok
    assert "sk-test" not in step.render()


def test_a_missing_langsmith_key_does_not_fail_preflight(keyed):
    """The journey this whole part exists for: one key in, preflight proceeds."""
    assert preflight.check_key().ok


# ---- the model checks -------------------------------------------------------


def test_every_registry_role_is_probed(keyed):
    client = StubClient()
    result = preflight.run(client=client)

    assert set(client.models) == {spec.model_id for spec in REGISTRY.values()}
    assert all(step.ok for step in result.steps), [s.render() for s in result.steps]


def test_the_probe_uses_the_kwargs_the_registry_declares(keyed):
    """Not a simplified call. temperature=0 is legal on Haiku and a 400 on Sonnet 5,
    so a probe that dropped the kwargs could pass where the sweep fails."""
    from loopeng.usage import UsageLedger

    client = StubClient()
    preflight.check_model("worker", client=client, ledger=UsageLedger())

    sent = client.kwargs[0]
    assert sent["temperature"] == REGISTRY["worker"].request_kwargs["temperature"]


def test_the_frontier_max_tokens_is_left_alone(keyed):
    """It caps thinking plus output there. Squeezing it would invent a failure the
    sweep would never hit."""
    from loopeng.usage import UsageLedger

    client = StubClient()
    preflight.check_model("frontier", client=client, ledger=UsageLedger())

    assert client.kwargs[0]["max_tokens"] == REGISTRY["frontier"].request_kwargs["max_tokens"]


def test_a_refused_call_reports_the_fix_not_a_traceback(keyed):
    from loopeng.usage import UsageLedger

    client = RefusingClient()
    step = preflight.check_model("worker", client=client, ledger=UsageLedger())

    assert not step.ok
    assert client.calls == 1
    assert "ANTHROPIC_API_KEY" in step.fix


def test_the_probe_cost_is_reported_and_estimated(keyed):
    result = preflight.run(client=StubClient())
    line = result.cost_line()

    assert line.startswith("est. $"), "dollars are a price table, never a measurement"
    assert result.ledger.totals()["n_calls"] == len(REGISTRY)


# ---- the offline steps ------------------------------------------------------


def test_the_offline_steps_run_without_any_key(tmp_path, monkeypatch):
    """A cloner with a typo still finds out the rest of the checkout is sound."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)

    result = preflight.run()

    names = {step.name: step for step in result.steps}
    assert not result.ok
    assert names["warehouse builds"].ok
    assert names["gold set builds"].ok
    assert names["rule surface (offline, free)"].ok


def test_the_gold_step_reports_items_and_clusters(tmp_path):
    built, gold = preflight.check_warehouse_and_gold(
        warehouse_path=tmp_path / "w.duckdb", seed=20260729
    )
    assert built.ok and gold.ok
    assert "items in" in gold.detail
    assert "clusters" in gold.detail


def test_the_rule_surface_reports_both_columns():
    """A verifier that rejects everything scores perfectly on one column alone."""
    step = preflight.check_rule_surface()
    assert step.ok
    assert "rejects" in step.detail and "accepts" in step.detail


# ---- the rendered output ----------------------------------------------------


def test_a_passing_run_prints_the_next_command(keyed):
    rendered = preflight.render(preflight.run(client=StubClient()))
    assert preflight.NEXT_COMMAND in rendered
    assert "--reference=compare" in rendered


def test_a_failing_run_says_nothing_was_spent(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)

    rendered = preflight.render(preflight.run())

    assert "[FAIL]" in rendered
    assert "Nothing has been spent" in rendered
    assert preflight.NEXT_COMMAND not in rendered


def test_the_entry_point_is_thin_and_delegates():
    """Enforced generally by test_demo_structure; asserted here because this module is
    where the logic it must not hold actually lives."""
    source = (Path(__file__).resolve().parent.parent
              / "demos" / "00_preflight" / "check.py").read_text(encoding="utf-8")
    assert "from loopeng.preflight import" in source
    assert len(source.splitlines()) < 100
