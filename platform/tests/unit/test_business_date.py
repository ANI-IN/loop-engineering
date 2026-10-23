"""Business logic resolves "today" from the business date, never from the system clock.

Allowed: datetime.now(UTC) or datetime.now(tz=UTC) for real-time timestamps (when a run started).
Forbidden in the package and the console: date.today(), datetime.today(), datetime.now() without a
time zone, .date() taken from now(...), time.localtime(), and SQL that asks the database for today
(CURRENT_DATE, now()::date, current_timestamp::date, 'today'). The one exception is
datapilot/business_date.py, which defines the business date.
"""

from __future__ import annotations

import ast
import re
from datetime import date

from datapilot import business_date
from datapilot.settings import PLATFORM, REPO, Settings

FOLDERS = (PLATFORM / "src" / "datapilot", PLATFORM / "console")
SQL_TODAY = re.compile(
    r"\bCURRENT_DATE\b|now\(\)\s*::\s*date|current_timestamp\s*::\s*date|'today'", re.I
)


def _call_name(node: ast.Call) -> str:
    func = node.func
    parts = []
    while isinstance(func, ast.Attribute):
        parts.append(func.attr)
        func = func.value
    if isinstance(func, ast.Name):
        parts.append(func.id)
    return ".".join(reversed(parts))


def _clock_reads(tree: ast.AST) -> list[str]:
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        if name.endswith(("date.today", "datetime.today")) or name == "time.localtime":
            found.append(name)
        elif name.endswith("datetime.now") and not (node.args or node.keywords):
            found.append("datetime.now() without a time zone")
        elif isinstance(node.func, ast.Attribute) and node.func.attr == "date":
            inner = node.func.value
            if isinstance(inner, ast.Call) and _call_name(inner).endswith("now"):
                found.append("now(...).date()")
    return found


def test_business_logic_never_reads_the_system_clock() -> None:
    reads = []
    for folder in FOLDERS:
        for path in folder.rglob("*.py"):
            rel = path.relative_to(REPO).as_posix()
            text = path.read_text(encoding="utf-8")
            reads += [f"{rel}: {r}" for r in _clock_reads(ast.parse(text, filename=rel))]
            reads += [f"{rel}: SQL '{m.group(0)}'" for m in SQL_TODAY.finditer(text)]
        for path in folder.rglob("*.sql"):
            text = path.read_text(encoding="utf-8")
            rel = path.relative_to(REPO).as_posix()
            reads += [f"{rel}: SQL '{m.group(0)}'" for m in SQL_TODAY.finditer(text)]
    assert reads == []


def test_the_detector_catches_clock_reads() -> None:
    samples = [
        "from datetime import date\nx = date.today()",
        "from datetime import datetime\nx = datetime.now()",
        "from datetime import datetime, UTC\nx = datetime.now(UTC).date()",
    ]
    for sample in samples:
        assert _clock_reads(ast.parse(sample)), sample
    assert (
        _clock_reads(ast.parse("from datetime import datetime, UTC\nx = datetime.now(UTC)")) == []
    )


def test_the_default_business_date_is_the_last_warehouse_day() -> None:
    assert Settings(_env_file=None).datapilot_business_date == date(2026, 1, 31)


def test_labels() -> None:
    assert business_date.status_label() == "Business date: 31 January 2026"
    assert "Saturday, 31 January 2026" in business_date.prompt_line()
    assert business_date.yesterday() == date(2026, 1, 30)
