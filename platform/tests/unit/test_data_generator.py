"""The generator is deterministic and keeps the planted data conditions, on a small profile.
The full-size checks run against the seeded databases (integration)."""

from __future__ import annotations

import csv
import re
from dataclasses import replace
from pathlib import Path

import pytest

from datapilot.loop4_hill_climbing.pack_files import load_package, load_submodule
from datapilot.settings import PLATFORM

generator = load_package("data_generator")
seeding = load_submodule("data_generator", "seed")
SMALL = replace(generator.PROFILES["warehouse"], customers=2_000, orders=6_000)


@pytest.fixture(scope="module")
def small(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict[str, int]]:
    out = tmp_path_factory.mktemp("small")
    return out, generator.HarborPineGenerator(SMALL).generate(out, seed=SMALL.seed)


def _rows(out: Path, table: str) -> list[list[str]]:
    with (out / f"{table}.csv").open(encoding="utf-8", newline="") as handle:
        return list(csv.reader(handle))


def test_the_same_seed_gives_the_same_bytes(small, tmp_path: Path) -> None:
    out, counts = small
    again = generator.HarborPineGenerator(SMALL)
    assert again.generate(tmp_path, seed=SMALL.seed) == counts
    assert again.content_hash(tmp_path) == again.content_hash(out)


def test_another_seed_gives_other_data(small, tmp_path: Path) -> None:
    out, _ = small
    other = generator.HarborPineGenerator(SMALL)
    other.generate(tmp_path, seed=SMALL.seed + 1)
    assert other.content_hash(tmp_path) != other.content_hash(out)


def test_orders_cover_three_fiscal_years_in_utc(small) -> None:
    out, counts = small
    orders = _rows(out, "orders")
    assert len(orders) == counts["orders"] > SMALL.orders
    stamps = sorted(o[2] for o in orders)
    assert stamps[0] >= "2023-02-01 05:00:00+00" and stamps[-1] < "2026-02-01 05:00:00+00"


def test_totals_add_up_and_statuses_are_one_to_five(small) -> None:
    out, _ = small
    for o in _rows(out, "orders"):
        subtotal, discount, tax, shipping, total = map(int, o[6:11])
        assert total == subtotal - discount + tax + shipping
        assert o[3] in {"1", "2", "3", "4", "5"} and o[4] in {"web", "app"}


def test_internal_accounts_use_the_domain_only(small) -> None:
    out, _ = small
    customers = _rows(out, "customers")
    internal = [c for c in customers if c[3].lower().endswith("@harborpine.com")]
    assert len(internal) == round(SMALL.customers * SMALL.internal_share)
    assert len(customers[0]) == 10  # no flag column besides the opt-out
    assert any(c[3] != c[3].lower() for c in internal), "mixed case must be present"


def test_zip_codes_keep_leading_zeros_and_some_phones_are_empty(small) -> None:
    out, _ = small
    customers = _rows(out, "customers")
    assert any(c[7].startswith("0") for c in customers)
    assert all(len(c[7]) == 5 for c in customers)
    assert any(c[4] == "" for c in customers)


def test_the_catalog_keeps_the_planted_names(small) -> None:
    out, _ = small
    names = [p[2] for p in _rows(out, "products")]
    assert "Alpine Trek 45L Backpack" in names and "Alpine Trek 45 L Backpack" in names
    assert sum("ignore all previous instructions" in n or "drop table" in n for n in names) == 2
    assert len(set(names)) == len(names)


def test_role_settings_fill_every_placeholder_in_roles_sql() -> None:
    text = (PLATFORM / "ops" / "sql" / "roles.sql").read_text(encoding="utf-8")
    assert set(re.findall(r"\{(\w+)\}", text)) == set(seeding.role_settings())
