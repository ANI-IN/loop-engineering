"""The benchmark's shape: 40 items, the agreed composition, trap coverage, and paraphrased
holdout questions. Zero tokens, no database."""

from __future__ import annotations

import importlib.util
import re
import sys
from collections import Counter
from difflib import SequenceMatcher

import pytest

from datapilot.config import pack_config
from datapilot.contracts import AnswerStatus, Category, Split
from datapilot.loop4_hill_climbing.pack_files import load_benchmark
from datapilot.settings import PLATFORM

TRAPS = {"fiscal_year", "net_revenue", "cancelled_orders", "eastern_time", "internal_accounts"}
SPINE = "What was our net revenue in fiscal year 2025?"
# The highest similarity allowed between a holdout question and any dev question.
SIMILARITY_LIMIT = 0.75
COMPOSITION = {
    Category.SIMPLE_AGGREGATES: 6,
    Category.JOINS_AND_HIERARCHY: 6,
    Category.FISCAL_PERIODS: 9,
    Category.EASTERN_BUSINESS_DAYS: 6,
    Category.CUSTOMER_SEGMENTS: 4,
    Category.RANKING: 5,
    Category.RATIOS: 4,
}

ITEMS = load_benchmark()
DEV = [i for i in ITEMS if i.split is Split.DEV]
HOLDOUT = [i for i in ITEMS if i.split is Split.HOLDOUT]


def test_forty_items_split_twenty_five_and_fifteen() -> None:
    assert (len(ITEMS), len(DEV), len(HOLDOUT)) == (40, 25, 15)
    assert len({i.id for i in ITEMS}) == 40


def test_the_composition_by_category() -> None:
    assert Counter(i.category for i in ITEMS) == COMPOSITION


def test_the_class_benchmark_has_no_clarification_items() -> None:
    assert all(i.expected_status is AnswerStatus.ANSWERED for i in ITEMS)
    assert all(i.gold_sql for i in ITEMS)


@pytest.mark.parametrize("trap", sorted(TRAPS))
def test_each_trap_is_in_two_dev_and_one_holdout_item(trap: str) -> None:
    assert sum(trap in i.traps for i in DEV) >= 2
    assert sum(trap in i.traps for i in HOLDOUT) >= 1


def test_only_the_five_traps_are_named() -> None:
    assert {t for i in ITEMS for t in i.traps} <= TRAPS


def test_every_trap_item_has_a_naive_query() -> None:
    assert [i.id for i in ITEMS if i.traps and not i.naive_sql] == []
    assert [i.id for i in ITEMS if i.naive_sql and not i.traps] == []


def test_the_spine_question_is_in_dev() -> None:
    spine = [i for i in ITEMS if i.question == SPINE]
    assert len(spine) == 1 and spine[0].split is Split.DEV


def test_metric_families_come_from_the_pack() -> None:
    families = set(pack_config()["autonomy"]["metric_families"])
    assert {i.metric_family for i in ITEMS} <= families


def test_net_revenue_has_at_least_three_holdout_items() -> None:
    assert sum(i.metric_family == "revenue" for i in HOLDOUT) >= 3


def test_ordered_items_have_a_deterministic_order_by() -> None:
    for item in ITEMS:
        if item.order_matters:
            assert item.gold_sql and "ORDER BY" in item.gold_sql, item.id
            order_by = item.gold_sql.rsplit("ORDER BY", 1)[1]
            assert "," in order_by or "fiscal_quarter" in order_by, f"{item.id}: needs a tie-break"


def _words(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def test_holdout_questions_are_paraphrased_away_from_dev() -> None:
    worst = max(
        (SequenceMatcher(None, _words(h.question), _words(d.question)).ratio(), h.id, d.id)
        for h in HOLDOUT
        for d in DEV
    )
    assert worst[0] < SIMILARITY_LIMIT, worst


def test_questions_use_full_words(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = importlib.util.spec_from_file_location(
        "short_forms", PLATFORM / "scripts" / "short_forms.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, "short_forms", module)
    spec.loader.exec_module(module)
    assert {i.id: module.find(i.question) for i in ITEMS if module.find(i.question)} == {}
