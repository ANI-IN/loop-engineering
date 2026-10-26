"""Each section's demo/run.sh against the demo registry, zero tokens and no stack: its demo lists,
which demos it passes PLANTED=1 to, and the make commands it would run (`--list`, which runs none).

Review of session 6, round 1: run.sh passed PLANTED=1 to no demo, so Section 4's naive analyzer
demo ran the analyzer team instead, and "PLANTED=1 in front" reached every demo, so the script
stopped at the first demo with no planted bug (make demo refuses PLANTED=1 there). Now the script
passes PLANTED=1 only to a demo with a planted code bug, and a demo whose only half is planted
(the naive analyzer) switches its bug on with or without it."""

from __future__ import annotations

import os
import re
import shutil
import subprocess

import pytest

from datapilot import planted
from datapilot.contracts import registries
from datapilot.contracts.registries import PlantedKind
from datapilot.loop3_events import commands
from datapilot.names import SECTIONS
from datapilot.settings import REPO

ARRAY = re.compile(r"^(?P<name>[A-Z_]+_DEMOS)=\((?P<items>[^)]*)\)$", re.M)
NAIVE = "improve-naive-analyzer-blocked"


def _arrays(section_folder: str) -> dict[str, list[str]]:
    text = (REPO / section_folder / "demo" / "run.sh").read_text(encoding="utf-8")
    return {m["name"]: m["items"].split() for m in ARRAY.finditer(text)}


def _has_code_bug(demo: registries.Demo) -> bool:
    items = {item.id: item for item in registries.planted().items}
    return any(p in items and items[p].kind is PlantedKind.CODE_BUG for p in demo.planted)


@pytest.mark.parametrize("section", SECTIONS, ids=lambda s: s.slug)
def test_the_demo_lists_match_the_registry(section) -> None:
    demos = registries.demos().for_section(section.slug)
    arrays = _arrays(section.folder)
    assert arrays["CORE_DEMOS"] == [d.id for d in demos if d.tier.value == "core"]
    assert arrays["OPTIONAL_DEMOS"] == [d.id for d in demos if d.tier.value == "optional"]
    assert arrays["PLANTED_DEMOS"] == [d.id for d in demos if _has_code_bug(d)]


def test_the_naive_analyzer_demo_runs_its_planted_half_without_planted() -> None:
    """Its fixed half is another demo, the analyzer team: the registry's make trigger, with no
    PLANTED=1, must show the blocked moment, so the bug is on either way."""
    demo = registries.demos().by_id(NAIVE)
    assert demo.trigger.make == f"make demo NAME={NAIVE}"
    assert commands.demo_flags(demo, planted_bugs=False) == ["BUG_NAIVE_ANALYZER"]
    assert commands.demo_flags(demo, planted_bugs=True) == ["BUG_NAIVE_ANALYZER"]
    for name in planted.ONLY_PLANTED_HALF:
        assert _has_code_bug(registries.demos().by_id(name)), name


def test_a_demo_with_a_fixed_half_still_needs_planted_for_its_bugs() -> None:
    guard = registries.demos().by_id("verify-malicious-sql")
    assert commands.demo_flags(guard, planted_bugs=False) == []
    assert commands.demo_flags(guard, planted_bugs=True) == ["BUG_NAIVE_GUARD"]


def _listed(section_folder: str, planted_value: str | None) -> list[str]:
    env = {k: v for k, v in os.environ.items() if k != "PLANTED"}
    if planted_value is not None:
        env["PLANTED"] = planted_value
    script = REPO / section_folder / "demo" / "run.sh"
    done = subprocess.run(
        ["bash", str(script), "--optional", "--list"],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return done.stdout.splitlines()


@pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")
@pytest.mark.parametrize("planted_value", [None, "1"], ids=["as it is", "PLANTED=1 in front"])
@pytest.mark.parametrize("section", SECTIONS, ids=lambda s: s.slug)
def test_each_listed_command_is_one_make_demo_accepts(section, planted_value: str | None) -> None:
    """Every command the script would run, in order: PLANTED=1 only for a demo with a planted code
    bug and only when asked, never a PLANTED=1 that make demo refuses (commands.demo_flags), and
    the naive analyzer with its bug on either way."""
    demos = registries.demos().for_section(section.slug)
    ordered = [d for d in demos if d.tier.value == "core"]
    ordered += [d for d in demos if d.tier.value == "optional"]
    expected = []
    for demo in ordered:
        on = planted_value == "1" and _has_code_bug(demo)
        expected.append(f"make demo NAME={demo.id}" + (" PLANTED=1" if on else ""))
        flags = commands.demo_flags(demo, planted_bugs=on)  # DemoRefused for a refused command
        if demo.id == NAIVE:
            assert flags == ["BUG_NAIVE_ANALYZER"]
    assert _listed(section.folder, planted_value) == expected


@pytest.mark.slow
@pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")
@pytest.mark.parametrize("section", SECTIONS, ids=lambda s: s.slug)
def test_the_script_reads_the_api_and_console_addresses_from_the_settings(section) -> None:
    """Session 6 review, round 2: run.sh checked a fixed localhost:8000, so with API_PORT moved in
    .env it said the api did not answer while make demo went to the moved port."""
    env = {**os.environ, "API_PORT": "8999", "CONSOLE_PORT": "8599", "DATAPILOT_API_URL": ""}
    script = REPO / section.folder / "demo" / "run.sh"
    done = subprocess.run(
        ["bash", str(script), "--addresses"], env=env, capture_output=True, text=True, check=True
    )
    assert done.stdout.splitlines() == ["http://localhost:8999", "http://localhost:8599/"]
