"""The pack setting: DATAPILOT_PACK names the folder under platform/packs/ that every component
reads, datapilot_us when it is not set (zero tokens, no database)."""

from __future__ import annotations

import re

import pytest
from pydantic import ValidationError

from datapilot.config import UnknownPack, active_pack, pack_config
from datapilot.loop2_verification.config import VerificationConfig
from datapilot.loop3_events.commands import pre_authored_versions
from datapilot.loop4_hill_climbing import versions
from datapilot.loop4_hill_climbing.pack_files import load_benchmark, load_knowledge, pack_root
from datapilot.loop4_hill_climbing.preflight import DataCheck, canary_ids
from datapilot.settings import DEFAULT_PACK, REPO, Settings


def test_the_class_pack_is_the_default() -> None:
    assert DEFAULT_PACK == "datapilot_us"
    assert Settings(_env_file=None).datapilot_pack == "datapilot_us"
    assert active_pack() == "datapilot_us"


def test_one_setting_moves_every_component_to_the_template(select_pack) -> None:
    select_pack("_template")
    assert active_pack() == "_template"
    assert pack_config()["name"] == "_template"
    assert pack_root().name == "_template"
    assert {i.id for i in load_benchmark()} >= {"plan-count", "net-revenue-march-2025"}
    assert load_knowledge(versions.STARTING_VERSION).version == "v1"
    assert versions.shipped() == ["v1"]
    assert pre_authored_versions() == {"v1"}
    config = VerificationConfig.from_pack()
    assert (config.pack, config.schema) == ("_template", "club")
    unnamed = {name: value for name, value in vars(config).items() if name != "pack"}
    assert VerificationConfig(**unnamed).pack == "_template", "the default is the selected pack"
    assert canary_ids()["traps"] == ["net-revenue-march-2025", "charges-june-2025"]
    assert DataCheck.from_pack().qualified == "club.payments"


def test_switching_back_reads_the_class_pack_again(select_pack) -> None:
    select_pack("_template")
    assert pack_config()["display_name"] == "Lantern Coffee Club"
    select_pack("datapilot_us")
    assert pack_config()["name"] == "datapilot_us"
    assert DataCheck.from_pack().qualified == "warehouse.orders"


def test_an_unknown_pack_names_the_setting(select_pack) -> None:
    select_pack("no_such_pack")
    with pytest.raises(UnknownPack, match="DATAPILOT_PACK"):
        pack_config()


@pytest.mark.parametrize("value", ["../datapilot_us", "packs/datapilot_us", "", "my pack"])
def test_the_setting_is_a_folder_name_never_a_path(value: str) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, datapilot_pack=value)


def test_the_env_example_selects_the_class_pack() -> None:
    text = (REPO / ".env.example").read_text(encoding="utf-8")
    assert re.search(r"^DATAPILOT_PACK=datapilot_us$", text, re.M)


def test_compose_takes_the_agent_addresses_from_the_environment() -> None:
    """The services keep today's Compose addresses unless .env names others."""
    text = (REPO / "compose.yaml").read_text(encoding="utf-8")
    for name in ("DATABASE_URL_AGENT", "DATABASE_URL_AGENT_ALT"):
        line = re.search(rf"^\s+{name}: (.+)$", text, re.M)
        assert line, name
        assert line.group(1).startswith(f"${{SERVICES_{name}:-postgresql://"), line.group(1)
        assert "@postgres:5432/" in line.group(1)


# Code that may name the class pack as a string: the setting's default, and the frozen contracts
# (GraderContext.pack; every caller passes the selected pack).
NAMES_THE_CLASS_PACK = ("platform/src/datapilot/settings.py", "platform/src/datapilot/contracts/")


def test_no_component_hard_codes_the_class_pack(repo_scan) -> None:
    hits = repo_scan(
        r"[\"']datapilot_us[\"']", "platform/src", "platform/console/datapilot_console"
    )
    found = [h for h in hits if not h.startswith(NAMES_THE_CLASS_PACK)]
    assert found == []
