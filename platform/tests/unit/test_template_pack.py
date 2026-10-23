"""The template pack, platform/packs/_template, loads through the platform's own loaders and passes
use-in-your-repo/check_pack.py, the check `make check-pack` runs (zero tokens, no database)."""

from __future__ import annotations

import importlib.util
from types import ModuleType

import pytest

from datapilot.config import pack_config
from datapilot.contracts import Split
from datapilot.loop2_verification.config import VerificationConfig
from datapilot.loop4_hill_climbing.pack_files import load_benchmark, load_knowledge
from datapilot.loop4_hill_climbing.preflight import DataCheck, PackHasNoPreflight, canary_ids
from datapilot.settings import REPO

TEMPLATE = "_template"


def check_pack() -> ModuleType:
    path = REPO / "use-in-your-repo" / "check_pack.py"
    spec = importlib.util.spec_from_file_location("check_pack", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_template_loads_and_validates() -> None:
    config = pack_config(TEMPLATE)
    assert config["name"] == TEMPLATE
    items = load_benchmark(TEMPLATE)
    assert {i.split for i in items} == {Split.DEV, Split.HOLDOUT}
    assert len({i.id for i in items}) == len(items)
    assert load_knowledge("v1", TEMPLATE).rules, "the starting knowledge holds the money rule"
    verification = VerificationConfig.from_pack(config)
    assert verification.schema == "club" and verification.marketing_view == "members_marketable"
    by_id = {i.id: i for i in items}
    canary = canary_ids(config)
    assert all(not by_id[i].traps for i in canary["easy"])
    assert all(by_id[i].traps for i in canary["traps"])
    assert DataCheck.from_pack(config).qualified == "club.payments"


def test_check_pack_passes_on_the_template(capsys: pytest.CaptureFixture[str]) -> None:
    assert check_pack().main([TEMPLATE]) == 0
    out = capsys.readouterr().out
    assert out.splitlines()[-1] == "check_pack: _template: 0 problems"
    assert "x " not in {line[:2] for line in out.splitlines()}
    assert "ok preflight.data_check reads club.payments" in out


def test_check_pack_needs_the_preflight_section() -> None:
    config = {**pack_config(TEMPLATE), "preflight": {}}
    with pytest.raises(PackHasNoPreflight, match="no preflight section"):
        canary_ids(config)
    outside = {**pack_config(TEMPLATE), "preflight": {"data_check": {"table": "warehouse.orders"}}}
    with pytest.raises(PackHasNoPreflight, match="allowed_schema"):
        DataCheck.from_pack(outside)


def test_check_pack_reports_a_missing_pack(capsys: pytest.CaptureFixture[str]) -> None:
    assert check_pack().main(["no_such_pack"]) == 1
    assert capsys.readouterr().out.startswith("x no pack.yaml in ")
