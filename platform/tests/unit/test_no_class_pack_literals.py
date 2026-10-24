"""No platform module names Harbor & Pine as a literal: its tables, its distinctive columns, its
traps, its internal email domain, or the warehouse schema's orders table. Those belong in
platform/packs/datapilot_us/ (and the warehouse schema files the pack seeds), so another pack works
through the pack setting alone.

The names are read from Harbor & Pine's own files, so a new table or trap is checked as soon as it
exists. A string literal counts; docstrings and comments are prose, not code, and do not. Each
allowed exception below gives its reason, and an exception that no longer matches anything fails,
so the list only shrinks.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Iterator
from pathlib import Path

import yaml

from datapilot.settings import PLATFORM, REPO

CLASS_PACK = PLATFORM / "packs" / "datapilot_us"
SCHEMA_SQL = PLATFORM / "ops" / "sql" / "warehouse_schema.sql"
# The code that must work for any pack: the platform, the console, the scripts, the pack tooling.
SCANNED = (
    "platform/src/datapilot",
    "platform/console",
    "platform/scripts",
    "use-in-your-repo",
    "final-project",
)
NOT_SCANNED = (
    "platform/src/datapilot/contracts/",  # frozen: built against, never changed by a track
)
# Column names every warehouse has; naming one says nothing about Harbor & Pine.
GENERIC_COLUMNS = {
    "name",
    "email",
    "phone",
    "city",
    "state",
    "zip",
    "status",
    "channel",
    "quantity",
    "first_name",
    "last_name",
    "created_at",
}

# path -> why it may name Harbor & Pine for now. Each is reported to the lead as remaining work.
ALLOWED = {
    # The class demos and checks: their questions and statements are the course's fixed moments,
    # quoted verbatim in platform/demos/registry.yaml, the demo pages, and the slides.
    "platform/src/datapilot/loop2_verification/defense.py": "verification loop demo statements",
    "platform/src/datapilot/loop3_events/worker.py": "reports the defense demo's orders count",
    # Moved from demos.py so the console's buttons read the same questions (and the export
    # request) as make demo.
    "platform/src/datapilot/demo_questions.py": "class demo questions",
    "platform/src/datapilot/loop3_events/api/demo.py": "class demo questions",
    "platform/src/datapilot/loop4_hill_climbing/live_smoke.py": "the class stack's live smoke test",
    "platform/src/datapilot/loop4_hill_climbing/calibration.py": "class calibration questions",
    "platform/src/datapilot/loop4_hill_climbing/data_cli.py": "class calibration item ids",
    # Non-gating trap labels: filtered by each item's own traps, so another pack gets none. Moving
    # the detectors into the pack needs a pack interface change (requested, not made here).
    "platform/src/datapilot/loop4_hill_climbing/trap_detectors.py": "class trap labels",
    # The course's own vocabulary for its business rules and traps, named in prose.
    "platform/src/datapilot/names.py": "course trap names",
    # The assignments extend the class problem; another track is changing them tonight.
    "platform/src/datapilot/assignments/stack.py": "assignment stack checks the class warehouse",
    # The console client marks class traps in SQL; another track is changing it tonight.
    "platform/console/datapilot_console/sql_marks.py": "console trap marks",
    "platform/console/datapilot_console/views.py": "console table list",
    # Design specimens: static pictures of the class console, never run against a pack.
    "platform/console/design/prototypes.py": "design specimen",
    "platform/console/design/specimen.py": "design specimen",
    "platform/console/design/style_tile.py": "design specimen",
}


def class_names() -> set[str]:
    text = SCHEMA_SQL.read_text(encoding="utf-8")
    tables = set(re.findall(r"CREATE TABLE warehouse\.(\w+)", text))
    columns = set(re.findall(r"^\s{4}(\w+)\s+\w", text, re.M)) - GENERIC_COLUMNS
    traps = {
        trap
        for path in (CLASS_PACK / "benchmark").glob("*.yaml")
        for item in yaml.safe_load(path.read_text(encoding="utf-8"))
        for trap in item.get("traps") or []
    }
    pack = yaml.safe_load((CLASS_PACK / "pack.yaml").read_text(encoding="utf-8"))
    view = pack["personal_data"]["marketing_view"].split(".")[-1]
    return tables | columns | traps | {view, "harborpine"}


def pattern() -> re.Pattern[str]:
    names = sorted(class_names(), key=len, reverse=True)
    return re.compile(r"\b(warehouse\.orders|" + "|".join(map(re.escape, names)) + r")\b", re.I)


def literals(tree: ast.AST) -> Iterator[ast.Constant]:
    """Every string constant except a docstring."""
    docstrings = {
        id(node.body[0].value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef)
        and node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
    }
    for node in ast.walk(tree):
        is_text = isinstance(node, ast.Constant) and isinstance(node.value, str)
        if is_text and id(node) not in docstrings:
            yield node


def hits() -> dict[str, list[str]]:
    regex, found = pattern(), {}
    for folder in SCANNED:
        for path in sorted((REPO / folder).rglob("*.py")):
            rel = path.relative_to(REPO).as_posix()
            if "__pycache__" in path.parts or rel.startswith(NOT_SCANNED):
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            lines = [
                f"{rel}:{node.lineno}: {match.group(0)}"
                for node in literals(tree)
                if (match := regex.search(node.value))
            ]
            if lines:
                found[rel] = lines
    return found


def test_the_names_come_from_harbor_and_pine_files() -> None:
    names = class_names()
    assert {"orders", "order_items", "customers", "order_ts", "total_cents"} <= names
    assert {"cancelled_orders", "eastern_time", "fiscal_year", "internal_accounts"} <= names
    assert "customers_marketable" in names and "status" not in names


def test_the_scan_sees_a_class_literal_and_ignores_prose() -> None:
    source = '"""Counts orders."""\nX = "SELECT count(*) FROM warehouse.orders"  # orders\n'
    assert [n.value for n in literals(ast.parse(source))] == [
        "SELECT count(*) FROM warehouse.orders"
    ]
    assert pattern().search("WHERE o.order_ts >= now()")
    assert not pattern().search("SELECT count(*) FROM club.payments")


def test_no_module_outside_the_class_pack_names_harbor_and_pine() -> None:
    found = hits()
    unexpected = [line for rel, lines in found.items() if rel not in ALLOWED for line in lines]
    assert unexpected == [], "move these names into the pack's files:\n" + "\n".join(unexpected)


def test_every_allowed_exception_still_applies() -> None:
    found = hits()
    stale = [rel for rel in ALLOWED if rel not in found]
    assert stale == [], f"remove these from ALLOWED, they no longer name Harbor & Pine: {stale}"
    assert all(Path(REPO / rel).is_file() for rel in ALLOWED)
