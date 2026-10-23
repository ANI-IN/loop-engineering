"""The demo and planted-item registries are valid, consistent, and follow the naming rule."""

from __future__ import annotations

import importlib.util
import re
import sys

import pytest
from pydantic import ValidationError

from datapilot.contracts import registries
from datapilot.contracts.registries import Demo, PlantedKind, Tier
from datapilot.names import SECTIONS
from datapilot.settings import PLATFORM, REPO

CORE_DEMOS = {
    "agent-simple-question",
    "agent-confident-wrong-answer",
    "agent-unbounded-rows",
    "verify-malicious-sql",
    "verify-retry-cap",
    "verify-graders-pass-still-wrong",
    "events-webhook-question",
    "events-approval-survives-restart",
    "events-duplicate-events",
    "events-kill-switch-in-flight",
    "improve-baseline-experiment",
    "improve-naive-analyzer-blocked",
    "improve-analyzer-team-approve",
    "improve-candidate-experiment",
    "improve-cleared-unattended",
}


def _short_forms():
    spec = importlib.util.spec_from_file_location(
        "short_forms", PLATFORM / "scripts" / "short_forms.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["short_forms"] = module
    spec.loader.exec_module(module)
    return module


def test_both_registries_load_and_cross_reference() -> None:
    assert registries.cross_check(registries.demos(), registries.planted()) == []


def test_the_core_demos_are_the_fifteen_planned() -> None:
    core = {d.id for d in registries.demos().demos if d.tier is Tier.CORE}
    assert core == CORE_DEMOS


def test_every_section_has_core_demos() -> None:
    for section in SECTIONS:
        assert any(d.tier is Tier.CORE for d in registries.demos().for_section(section.slug))


def test_every_code_bug_flag_is_in_env_example_and_off() -> None:
    env = (REPO / ".env.example").read_text(encoding="utf-8")
    flags_in_env = set(re.findall(r"^(BUG_[A-Z0-9_]+)=0$", env, re.M))
    code_bugs = {i.id for i in registries.planted().items if i.kind is PlantedKind.CODE_BUG}
    assert flags_in_env == code_bugs


def test_registry_prose_has_no_short_forms() -> None:
    short_forms = _short_forms()
    texts = []
    for demo in registries.demos().demos:
        texts += [demo.title, demo.guaranteed_moment, demo.expected_outcome, demo.trigger.console]
    for item in registries.planted().items:
        texts += [item.name, item.symptom, item.fix]
    found = [(text, short_forms.find(text)) for text in texts if short_forms.find(text)]
    assert found == []


def test_a_numbered_demo_id_is_rejected() -> None:
    demo = registries.demos().demos[0].model_dump()
    demo["id"] = "d1-1"
    with pytest.raises(ValidationError):
        Demo.model_validate(demo)


def test_make_trigger_must_name_the_demo() -> None:
    demo = registries.demos().demos[0].model_dump()
    demo["trigger"]["make"] = "make demo NAME=something-else"
    with pytest.raises(ValidationError):
        Demo.model_validate(demo)
