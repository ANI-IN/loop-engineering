"""The live checks' machinery, zero tokens: the cost estimate, the OpenAI key gate, the spend
activity, and the pass rules. The key gate's HTTP is a transport double here, in a unit test only;
the checks themselves always call OpenAI."""

from __future__ import annotations

import copy

import httpx
import pytest
from pydantic import SecretStr

from datapilot.assignments import cost, keys
from datapilot.assignments.report import LiveRun, Report, Stop, per_case, repeated
from datapilot.config import pack_config
from datapilot.observability import spend
from datapilot.settings import Settings

MESSAGE = "Live checks need your OpenAI key from the operations team"


def _pack(tokens: int) -> dict:
    pack = copy.deepcopy(pack_config())
    pack["budgets"]["tokens_per_run"] = tokens
    pack["prices"]["model-under-test"] = {"input": 0.10, "cached_input": 0.01, "output": 0.50}
    return pack


def test_the_estimate_comes_from_the_token_budget_and_the_prices() -> None:
    planned = [cost.Planned("analyst runs", 12, "model-under-test")]
    lines = cost.estimate_lines(planned, _pack(60_000))
    assert lines[0] == "This check makes live model calls, about 7.2 cents"
    assert "36.0 cents" in lines[-1]
    assert cost.estimate_lines(planned, _pack(30_000))[0].endswith("about 3.6 cents")


def test_a_model_without_a_price_cannot_be_estimated() -> None:
    with pytest.raises(KeyError, match="no price"):
        cost.estimate_lines([cost.Planned("runs", 1, "unpriced")], _pack(1000))


def test_the_spend_activity(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATAPILOT_SPEND_ACTIVITY", "development")
    assert cost.activity() == "assignment"
    monkeypatch.setenv("DATAPILOT_SPEND_ACTIVITY", "assignment verification")
    assert cost.activity() == "assignment verification"


@pytest.mark.parametrize("base", ["assignment", "assignment verification"])
def test_each_check_run_records_under_its_own_activity_on_the_assignment_line(
    monkeypatch: pytest.MonkeyPatch, base: str, tmp_path
) -> None:
    """Two checks at the same time (the Thursday review runs Assignment 4 beside the others) never
    share an activity, and each name still counts under the assignment verification line."""
    monkeypatch.setenv("DATAPILOT_SPEND_ACTIVITY", base)
    one, other = cost.check_activity("agent-loop"), cost.check_activity("agent-loop")
    assert one != other
    assert one.startswith(f"{base}-agent-loop-")
    for name in (one, other, cost.check_activity("hill-climbing-loop")):
        assert spend.line_for(name).name == "assignment verification"
    monkeypatch.setenv("DATAPILOT_SPEND_LEDGER", str(tmp_path / "ledger.sqlite"))
    monkeypatch.setenv("DATAPILOT_BUILD_BUDGET", "1")
    spend.check_budget(activity=one)  # covered by a line, so never refused as unknown


def test_the_check_runs_under_its_own_activity(monkeypatch: pytest.MonkeyPatch) -> None:
    from datapilot.assignments import runner

    monkeypatch.setenv("DATAPILOT_SPEND_ACTIVITY", "development")
    seen: list[str] = []

    def bring_up(tree, name, say):
        seen.append(name)
        raise Stop("no stack in a unit test")

    monkeypatch.setattr(runner, "bring_up", bring_up)
    assert runner.run_check("agent-loop", runner.PACKAGE_TREE) == 2
    assert runner.run_check("agent-loop", runner.PACKAGE_TREE) == 2
    assert seen[0].startswith("assignment-agent-loop-") and seen[0] != seen[1]


def _client(status: int) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(status)))


def test_a_missing_key_stops_with_the_exact_message() -> None:
    with pytest.raises(Stop) as stopped:
        keys.require_openai_key(Settings(openai_api_key=SecretStr("")), http=_client(200))
    assert str(stopped.value) == MESSAGE


@pytest.mark.parametrize("status", [401, 403])
def test_a_rejected_key_stops_with_the_exact_message(status: int) -> None:
    with pytest.raises(Stop) as stopped:
        keys.require_openai_key(Settings(openai_api_key=SecretStr("k")), http=_client(status))
    assert str(stopped.value) == MESSAGE


def test_an_accepted_key_passes_the_gate() -> None:
    keys.require_openai_key(Settings(openai_api_key=SecretStr("k")), http=_client(200))


def test_an_account_without_credits_is_recognised() -> None:
    text = "Error code: 429 - {'type': 'insufficient_quota', 'code': 'credit_balance_exhausted'}"
    assert keys.out_of_credits(text)
    assert not keys.out_of_credits("Error code: 429 - rate limit reached, retry in 2s")


def test_a_rejected_key_mid_check_is_recognised() -> None:
    assert keys.rejected("AuthenticationError: Error code: 401 - invalid_api_key")
    assert not keys.rejected("the retry cap was reached")


def test_an_answer_may_carry_more_columns_than_gold() -> None:
    from decimal import Decimal

    from datapilot.assignments.gold import holds_gold

    gold = [(Decimal("177.99"),)]
    assert holds_gold([("Cascade Line Trail Runner", Decimal("177.99"))], gold)
    assert holds_gold([(Decimal("177.99"),)], gold)
    assert not holds_gold([("Cascade Trek Trail Runner", Decimal("93.99"))], gold)
    assert not holds_gold([("a", Decimal("177.99")), ("b", Decimal("1.00"))], gold)  # extra rows


def _runs(*passed: bool) -> list[LiveRun]:
    return [LiveRun(p, "detail") for p in passed]


def test_two_of_three_passes() -> None:
    assert repeated(1, "x", _runs(True, False, True), needed=2, fix="f").passed
    assert not repeated(1, "x", _runs(True, False, False), needed=2, fix="f").passed


def test_every_case_must_pass_on_its_own() -> None:
    groups = [_runs(True, True, True), _runs(False, False, True)]
    result = per_case(1, "x", groups, needed=2, fix="f")
    assert not result.passed and "3 of 3, 1 of 3" in result.rule


def test_a_deterministic_line_reports_an_unfilled_extension_point() -> None:
    report = Report("t")

    def probe() -> str | None:
        raise NotImplementedError("agent-loop-1: write it")

    result = report.check(1, "x", probe)
    assert not result.passed and "agent-loop-1" in result.fix
    assert report.finish() == 1
