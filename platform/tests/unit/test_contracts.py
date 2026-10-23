"""The frozen contracts: names, the run lifecycle, and the ops schema agree with each other."""

from __future__ import annotations

import re
import tomllib
from collections import deque

from datapilot import names
from datapilot.contracts import TERMINAL, TRANSITIONS, AutonomyLevel, RunEventKind, RunStatus
from datapilot.contracts.lifecycle import EventType
from datapilot.contracts.live import SessionPurpose
from datapilot.settings import PLATFORM, REPO

OPS_SQL = (PLATFORM / "ops" / "sql" / "ops" / "001_ops_schema.sql").read_text(encoding="utf-8")


def _check_list(table: str, column: str) -> set[str]:
    """The values of `column ... CHECK (column IN (...))` in one table of the ops migration."""
    block = re.search(rf"CREATE TABLE ops\.{table} \((.*?)\n\);", OPS_SQL, re.S)
    assert block, f"no table ops.{table}"
    pattern = rf"\b{column}\b[^,]*?CHECK \({column} IN \((.*?)\)\)"
    match = re.search(pattern, block.group(1), re.S)
    assert match, f"no CHECK list for ops.{table}.{column}"
    return set(re.findall(r"'([^']+)'", match.group(1)))


def test_sections_match_the_course_config() -> None:
    config = tomllib.loads((PLATFORM / "config" / "course.toml").read_text(encoding="utf-8"))
    assert [(s["number"], s["name"], s["slug"]) for s in config["sections"]] == [
        (s.number, s.name, s.slug) for s in names.SECTIONS
    ]
    for section in names.SECTIONS:
        assert (REPO / section.folder).is_dir()


def test_module_title_matches_the_course_config() -> None:
    config = tomllib.loads((PLATFORM / "config" / "course.toml").read_text(encoding="utf-8"))
    module = config["module"]
    assert "number" not in module
    assert names.MODULE_TITLE == "Module: {}".format(module["title"]) == "Module: Loop Engineering"


def test_every_transition_starts_from_a_live_status() -> None:
    assert all(source not in TERMINAL for source, _ in TRANSITIONS)


def test_every_status_is_reachable_from_received() -> None:
    seen, queue = {RunStatus.RECEIVED}, deque([RunStatus.RECEIVED])
    while queue:
        current = queue.popleft()
        for source, target in TRANSITIONS:
            if source is current and target not in seen:
                seen.add(target)
                queue.append(target)
    assert seen == set(RunStatus)


def test_every_live_status_can_reach_a_terminal_one() -> None:
    for status in set(RunStatus) - TERMINAL:
        seen, queue = {status}, deque([status])
        while queue:
            current = queue.popleft()
            for source, target in TRANSITIONS:
                if source is current and target not in seen:
                    seen.add(target)
                    queue.append(target)
        assert seen & TERMINAL, status


def test_ops_schema_matches_the_lifecycle_contract() -> None:
    assert _check_list("runs", "status") == {s.value for s in RunStatus}
    assert _check_list("run_events", "kind") == {k.value for k in RunEventKind}
    assert _check_list("events", "type") == {t.value for t in EventType}


def test_ops_schema_matches_the_autonomy_levels() -> None:
    levels = {level.value for level in AutonomyLevel}
    assert _check_list("runs", "autonomy_level_applied") == levels
    assert _check_list("control", "autonomy_level") == levels
    assert _check_list("autonomy_policy", "level") == levels
    assert set(names.AUTONOMY_LEVEL_NAMES) == {level.value for level in AutonomyLevel}


def test_autonomy_labels_are_full_names() -> None:
    assert [level.label for level in AutonomyLevel] == [
        "report-only level",
        "assisted level",
        "unattended level",
    ]


def test_session_purposes_match_the_ops_schema() -> None:
    sql = (PLATFORM / "ops" / "sql" / "ops" / "011_live_session_purpose.sql").read_text("utf-8")
    match = re.search(r"CHECK \(purpose IN \((.*?)\)\)", sql, re.S)
    assert match
    assert set(re.findall(r"'([^']+)'", match.group(1))) == {p.value for p in SessionPurpose}


def test_live_stamps_reach_the_browser_as_utc() -> None:
    from datetime import UTC, datetime, timedelta, timezone
    from uuid import uuid4

    from datapilot.contracts.live import LiveStamp

    started = datetime(2026, 10, 25, 14, 5, 32, tzinfo=timezone(timedelta(hours=5, minutes=30)))
    stamp = LiveStamp(run_id=uuid4(), session_id=uuid4(), started_at=started, trace_url=None)
    assert stamp.to_browser()["started_at_utc"] == "2026-10-25T08:35:32+00:00"
    assert started.astimezone(UTC).hour == 8
