"""The live probe of the per-call output-token cap (make calibrate STEP=output-token-cap), on
stand-ins (zero tokens): only the probe's own analyst gets the low cap, the pack and every other
agent keep theirs, and the probe fails unless the run ends escalated at the cap."""

from __future__ import annotations

import copy
import uuid
from types import SimpleNamespace
from typing import Any

from langchain_core.messages import HumanMessage
from loop4_doubles import answered
from test_live_smoke import _services, _stats
from typer.testing import CliRunner

from datapilot.cli import app
from datapilot.config import pack_config
from datapilot.loop4_hill_climbing import data_cli
from datapilot.loop4_hill_climbing import live_smoke as smoke
from datapilot.loop4_hill_climbing.targets import AnalystTarget
from datapilot.settings import Settings

CUT_OFF_REASON = "a model response was cut off at its output-token cap after 16 tokens"


def _payload(target: AnalystTarget, component: str) -> dict[str, Any]:
    model = target._models(str(uuid.uuid4()))(component)
    return model._get_request_payload([HumanMessage("hello")])  # type: ignore[attr-defined]


def _target() -> AnalystTarget:
    settings = Settings(_env_file=None, openai_model="model-from-env", openai_api_key="sk-test")
    return AnalystTarget(base=SimpleNamespace(), settings=settings)  # type: ignore[arg-type]


def test_the_low_cap_reaches_only_the_probe_analyst() -> None:
    before = copy.deepcopy(pack_config())
    capped = _target().with_output_cap("analyst", smoke.OUTPUT_CAP_PROBE_TOKENS)
    assert _payload(capped, "analyst")["max_output_tokens"] == smoke.OUTPUT_CAP_PROBE_TOKENS
    for other in ("schema_scout", "reviewer"):
        assert (
            _payload(capped, other)["max_output_tokens"]
            == before["models"][other]["max_output_tokens"]
        )
    # the pack itself, and so every other run of this process, keeps its caps
    assert pack_config() == before
    assert (
        _payload(_target(), "analyst")["max_output_tokens"]
        == (before["models"]["analyst"]["max_output_tokens"])
    )


def test_the_probe_cap_is_far_below_normal_use_but_one_the_api_accepts() -> None:
    assert 16 <= smoke.OUTPUT_CAP_PROBE_TOKENS <= 64  # the Responses API's minimum is 16


class _CappedTarget:
    """A stand-in for the analyst under a low cap: it records the cap and ends as told."""

    def __init__(self, status: str, reasons: list[str]) -> None:
        self.status, self.reasons = status, reasons
        self.stats: list[Any] = []
        self.caps: list[tuple[str, int]] = []
        self.base = SimpleNamespace(limits=SimpleNamespace(scout_enabled=True))

    def with_agents(self, *, scout: bool, reviewer: bool) -> _CappedTarget:
        assert not scout and not reviewer  # one analyst call, nothing else
        return self

    def with_output_cap(self, component: str, tokens: int) -> _CappedTarget:
        self.caps.append((component, tokens))
        return self

    def __call__(self, question: str, version: str) -> Any:
        self.stats.append(_stats(question, status=self.status, reasons=self.reasons))

        return answered("SELECT 1")


def test_a_run_ended_escalated_at_the_cap_passes_and_says_so() -> None:
    target = _CappedTarget("escalated", [CUT_OFF_REASON])
    check = smoke.output_cap_probe(_services(target=target))
    assert check.ok, check.hard_failure
    assert target.caps == [("analyst", smoke.OUTPUT_CAP_PROBE_TOKENS)]
    assert "escalated" in check.result and "cut off at its output-token cap" in check.result
    assert check.run_id and check.trace_url


def test_a_run_the_cap_did_not_stop_is_a_hard_failure() -> None:
    check = smoke.output_cap_probe(_services(target=_CappedTarget("answered", [])))
    assert check.hard_failure == "the output-token cap did not end the run escalated at the cap"


def test_an_escalation_for_another_reason_is_a_hard_failure() -> None:
    target = _CappedTarget("escalated", ["token budget of 60000 reached"])
    check = smoke.output_cap_probe(_services(target=target))
    assert check.hard_failure == "the output-token cap did not end the run escalated at the cap"


def test_the_probe_is_a_calibrate_step_on_the_development_line() -> None:
    result = CliRunner().invoke(app, ["calibrate", "output-token-cap", "--help"])
    assert result.exit_code == 0, result.output
    assert '"development live checks"' in (data_cli.output_token_cap.__doc__ or "")
