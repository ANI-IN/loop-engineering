"""The cheapest live path, checked offline.

The whole point of preflight is that it runs before anything expensive, so its own
tests must not spend either. Every network step here goes through a stub client, and
the offline steps run for real — they are free.
"""

from pathlib import Path

import pytest

from loopeng import preflight
from loopeng.registry import REGISTRY
from tests.fakes import FakeClient, refusal


class StubRoster:
    """One client per role, in that role's own vendor shape.

    The three roles no longer share a vendor, so a single stub cannot serve them all
    — which is exactly the mistake this roster exists to make impossible. It hands
    `preflight.run` a `client_for` callable and remembers every client it built, so a
    test can still ask what was sent and to which model.
    """

    def __init__(self):
        self.clients = {}

    def __call__(self, role):
        client = FakeClient(role, ["ok"], tokens={"input_tokens": 12,
                                                  "output_tokens": 2})
        self.clients[role] = client
        return client

    @property
    def models(self):
        return [client.spec.model_id for client in self.clients.values()]

    def kwargs_for(self, role):
        """The request kwargs this role was actually called with, minus the body."""
        request = dict(self.clients[role].requests[0])
        for key in ("model", "messages", "system"):
            request.pop(key, None)
        return request


@pytest.fixture
def keyed(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-test")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    return tmp_path


# ---- the key check ----------------------------------------------------------


def test_a_missing_key_fails_by_name(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)

    step = preflight.check_key()

    assert not step.ok
    # Derived: every REQUIRED credential is named, and only those. The judge key was
    # asserted here and is optional now — a preflight that fails without it turns away
    # a checkout that can run every scored path in the session.
    from loopeng.settings import REQUIRED_CREDENTIALS

    for field in REQUIRED_CREDENTIALS:
        assert field.upper() in step.detail
    assert "ANTHROPIC_API_KEY" not in step.detail
    assert ".env" in step.fix


def test_the_key_value_is_never_printed(keyed):
    step = preflight.check_key()
    assert step.ok
    assert "sk-test" not in step.render()


def test_a_missing_langsmith_key_does_not_fail_preflight(keyed):
    """The journey this whole part exists for: the model keys in, preflight
    proceeds. LangSmith is advisory and must never be a gate."""
    assert preflight.check_key().ok


# ---- the model checks -------------------------------------------------------


def test_every_registry_role_is_probed(keyed):
    roster = StubRoster()
    result = preflight.run(client_for=roster)

    assert set(roster.models) == {spec.model_id for spec in REGISTRY.values()}
    assert all(step.ok for step in result.steps), [s.render() for s in result.steps]


def test_each_role_is_probed_through_its_own_vendors_surface(keyed):
    """One client cannot serve three roles across two vendors. A probe that used the
    wrong SDK surface would fail for a reason the sweep would never hit — or worse,
    pass while exercising nothing."""
    roster = StubRoster()
    preflight.run(client_for=roster)

    assert set(roster.clients) == set(REGISTRY)
    for role, client in roster.clients.items():
        assert client.spec.provider == REGISTRY[role].provider


def test_the_probe_uses_the_kwargs_the_registry_declares(keyed):
    """Not a simplified call. `temperature=0` is legal on the judge and a 400 on both
    scoring roles, so a probe that dropped the kwargs could pass on an account where
    the sweep fails."""
    roster = StubRoster()
    preflight.run(client_for=roster)

    for role, spec in REGISTRY.items():
        assert roster.kwargs_for(role) == dict(spec.request_kwargs), role


def test_no_role_has_its_output_budget_trimmed_for_the_probe(keyed):
    """On the reference role the cap covers reasoning plus the query together, so
    squeezing it would invent a failure the sweep would never hit. It is simpler and
    more honest to trim nothing: "reply with one word" produces few tokens either
    way, so the saving was never real."""
    roster = StubRoster()
    preflight.run(client_for=roster)

    for role, spec in REGISTRY.items():
        sent = roster.kwargs_for(role)
        for cap in ("max_tokens", "max_completion_tokens"):
            if cap in spec.request_kwargs:
                assert sent[cap] == spec.request_kwargs[cap], role


def test_a_refused_call_reports_the_fix_not_a_traceback(keyed):
    from loopeng.usage import UsageLedger

    client = FakeClient("agent", raises=lambda: refusal("credential"))
    step = preflight.check_model("agent", client=client, ledger=UsageLedger())

    assert not step.ok
    assert client.calls == 1
    assert "OPENAI_API_KEY" in step.fix


def test_the_probe_cost_is_reported_and_estimated(keyed):
    result = preflight.run(client_for=StubRoster())
    line = result.cost_line()

    assert line.startswith("est. $"), "dollars are a price table, never a measurement"
    assert result.ledger.totals()["n_calls"] == len(REGISTRY)


# ---- the offline steps ------------------------------------------------------


def test_the_offline_steps_run_without_any_key(tmp_path, monkeypatch):
    """A cloner with a typo still finds out the rest of the checkout is sound."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)

    result = preflight.run()

    names = {step.name: step for step in result.steps}
    assert not result.ok
    assert names["warehouse matches the declared schema"].ok
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
    rendered = preflight.render(preflight.run(client_for=StubRoster()))
    assert preflight.NEXT_COMMAND in rendered
    assert "charts.py" in rendered


def test_a_failing_run_says_nothing_was_spent(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
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


def test_a_stale_warehouse_fails_the_preflight_by_name(tmp_path, monkeypatch, keyed):
    """The gap that "every figure is computed live" does not close.

    Live computation protects against a stale NUMBER. It does nothing against a stale
    SUBSTRATE: a warehouse built before the schema's vocabulary widened produces
    perfectly fresh figures, carrying live timestamps, computed from the wrong world.

    Measured — a 120-call run scored zero on every arm, including the pattern that
    cannot fail, because the local warehouse predated the widening. It was caught only
    because zero everywhere is loud. A partial overlap would have produced a plausible
    number on a chart.

    So the preflight is where an operator meets it: thirty minutes before, with the
    fix named, rather than at minute forty of a stage.
    """
    import duckdb

    from loopeng.warehouse.connect import ensure_warehouse
    from loopeng.warehouse.schema import CATEGORIES

    path = tmp_path / "stale.duckdb"
    ensure_warehouse(path, seed=20260729)
    con = duckdb.connect(str(path))
    con.execute("DELETE FROM products WHERE category = ?", [CATEGORIES[-1]])
    con.close()

    built, gold = preflight.check_warehouse_and_gold(warehouse_path=path, seed=20260729)

    assert not built.ok
    assert CATEGORIES[-1] in built.detail
    assert "rm " in built.fix, "the fix must be a command, not advice"
    assert not gold.ok, "the gold step must not run against a stale warehouse"


# ---- the journey a cloner following the documented setup actually takes ------


def test_the_judge_is_not_probed_when_its_optional_key_is_absent(monkeypatch, tmp_path):
    """Found by cloning the repository and running the documented minimal setup.

    `run()` looped over every role in the registry and built a client for each,
    including the JUDGE — whose key README §10 and SECURITY.md both call optional
    because the judge never gates a result. So a checkout with only `OPENAI_API_KEY`
    crashed in the one command written to tell it what is wrong.

    That is the required-credential defect from two commits earlier, still live one
    layer down: making the key optional in `settings` did not make it optional in the
    tool that checks your setup.
    """
    from loopeng.preflight import _skip_optional_role
    from loopeng.registry import SCORING_ROLES
    from loopeng.settings import load_settings

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.chdir(tmp_path)
    settings = load_settings()

    step = _skip_optional_role("judge", settings)
    assert step is not None, "the judge must not be called without its key"
    assert step.skipped is True
    assert step.ok is True, "an optional role must not fail the preflight"
    assert "gates nothing" in step.detail

    for role in SCORING_ROLES:
        assert _skip_optional_role(role, settings) is None, (
            f"{role} is a scoring role; it must always be probed"
        )


def test_a_skip_is_reported_as_a_skip_and_never_as_a_pass():
    """"We did not call it" and "we called it and it worked" are different facts, and
    reporting the first as the second tells someone their triage path is fine when it
    has never been exercised."""
    from loopeng.preflight import Step

    skipped = Step("judge model reachable", True, "not called", skipped=True)
    assert "[SKIP]" in skipped.render()
    assert "[PASS]" not in skipped.render()


def test_a_missing_credential_becomes_a_step_rather_than_a_traceback(monkeypatch,
                                                                     tmp_path):
    """The client was built OUTSIDE the try, so a missing credential escaped as an
    unhandled MissingCredential and the preflight printed twelve lines of traceback
    instead of the sentence naming the variable and the fix."""
    from loopeng.preflight import check_model
    from loopeng.usage import UsageLedger

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)

    step = check_model("agent", ledger=UsageLedger())
    assert step.ok is False
    assert "OPENAI_API_KEY" in (step.fix or "") + step.detail


def test_the_preflight_entry_point_goes_through_the_shared_guard():
    """It was the one demo calling `main()` directly, in the command whose entire job
    is to fail readably before you spend anything."""
    from pathlib import Path

    entry = (Path(__file__).resolve().parent.parent
             / "demos" / "00_preflight" / "check.py").read_text(encoding="utf-8")
    assert "from loopeng.entrypoint import run" in entry
    assert "SystemExit(main())" not in entry
