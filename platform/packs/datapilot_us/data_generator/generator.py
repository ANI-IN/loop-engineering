"""The deterministic Harbor & Pine data generator: fixed seed in, identical CSV files out.

Orders are drawn per Eastern local day (weekly pattern, seasons, Black Friday and Cyber Monday
spikes, the holiday uplift, the January dip), at evening-peaked local times, then stored in UTC.
Internal accounts (email domain harborpine.com) place large test orders that add 2 to 3 percent
to revenue, weighted so a few of them land among the top spenders. Only the standard library is
used, so the same seed gives the same bytes on every machine with the same Python.
"""

from __future__ import annotations

import csv
import hashlib
import random
from bisect import bisect
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, timedelta
from itertools import accumulate
from pathlib import Path
from zoneinfo import ZoneInfo

from . import reference as ref

LOCAL = ZoneInfo("America/New_York")
FIRST_DAY = date(2023, 2, 1)
LAST_DAY = date(2026, 1, 31)
TABLES = ("categories", "products", "customers", "orders", "order_items")

# Share of orders by Eastern local hour: evening peak, so evening orders cross the UTC date.
HOUR_WEIGHTS = (
    0.6, 0.3, 0.2, 0.15, 0.15, 0.3, 0.7, 1.4, 2.2, 2.8, 3.1, 3.4,
    3.8, 3.6, 3.3, 3.3, 3.5, 3.9, 4.4, 4.6, 2.3, 1.4, 0.9, 0.6,
)  # fmt: skip
WEEKDAY_WEIGHTS = (1.0, 0.95, 0.95, 1.0, 1.05, 1.12, 1.2)  # Monday first
MONTH_WEIGHTS = (0.68, 0.85, 0.95, 1.0, 1.1, 1.15, 1.15, 1.05, 0.95, 1.0, 1.0, 1.0)
ITEM_COUNTS = (1, 2, 3, 4, 5, 6, 7)
ITEM_COUNT_WEIGHTS = (0.35, 0.25, 0.17, 0.10, 0.07, 0.04, 0.02)


@dataclass(frozen=True)
class Profile:
    """Everything that differs between warehouse and warehouse_alt."""

    seed: int
    customers: int
    orders: int  # orders by real customers; internal test orders come on top
    cancel_rate: float = 0.06
    internal_share: float = 0.005  # of customers
    internal_revenue_share: float = 0.025  # internal net revenue over everyone else's
    heavy_internal_accounts: int = 3  # internal accounts that rank among the top spenders
    heavy_internal_weight: float = 10.0  # their order weight; every other internal account has 1
    yearly_growth: float = 0.12
    discount_rate: float = 0.25
    price_jitter: float = 0.0  # catalog prices move by up to this share
    tax_scale: float = 1.0


PROFILES = {
    "warehouse": Profile(seed=20250201, customers=50_000, orders=398_000),
    "warehouse_alt": Profile(
        seed=7331,
        customers=30_000,
        orders=240_000,
        cancel_rate=0.075,
        internal_revenue_share=0.028,
        yearly_growth=0.05,
        discount_rate=0.3,
        price_jitter=0.08,
        tax_scale=1.1,
    ),
}


def thanksgiving(year: int) -> date:
    first = date(year, 11, 1)
    return first + timedelta(days=(3 - first.weekday()) % 7 + 21)


def day_weight(day: date, profile: Profile) -> float:
    years = (day - FIRST_DAY).days / 365.25
    weight = (1 + profile.yearly_growth) ** years
    weight *= WEEKDAY_WEIGHTS[day.weekday()] * MONTH_WEIGHTS[day.month - 1]
    turkey = thanksgiving(day.year)
    if day == turkey + timedelta(days=1):  # Black Friday
        weight *= 5.0
    elif day == turkey + timedelta(days=4):  # Cyber Monday
        weight *= 4.0
    elif turkey <= day <= date(day.year, 12, 31):
        weight *= 1.6
    return weight


def _days() -> list[date]:
    return [FIRST_DAY + timedelta(days=i) for i in range((LAST_DAY - FIRST_DAY).days + 1)]


def _utc(day: date, hour: int, rng: random.Random) -> datetime:
    local = datetime(day.year, day.month, day.day, hour, rng.randrange(60), rng.randrange(60))
    return local.replace(tzinfo=LOCAL).astimezone(UTC)


def _ts(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S+00")


class HarborPineGenerator:
    """Implements datapilot.contracts.DataGenerator for one profile."""

    def __init__(self, profile: Profile) -> None:
        self.profile = profile

    def generate(self, out_dir: Path, *, seed: int) -> dict[str, int]:
        profile = replace(self.profile, seed=seed)
        rng = random.Random(profile.seed)
        out_dir.mkdir(parents=True, exist_ok=True)
        categories, leaf_ids = _categories()
        products = _products(rng, leaf_ids, profile)
        customers, internal_ids = _customers(rng, profile)
        orders, items = _orders(rng, profile, products, customers, internal_ids)
        _set_created_at(rng, customers, orders)
        rows = {
            "categories": categories,
            "products": [p[:7] for p in products],
            "customers": customers,
            "orders": orders,
            "order_items": items,
        }
        for table, table_rows in rows.items():
            with (out_dir / f"{table}.csv").open("w", newline="", encoding="utf-8") as handle:
                csv.writer(handle, lineterminator="\n").writerows(table_rows)
        return {table: len(table_rows) for table, table_rows in rows.items()}

    def content_hash(self, out_dir: Path) -> str:
        digest = hashlib.sha256()
        for table in TABLES:
            digest.update(table.encode())
            digest.update((out_dir / f"{table}.csv").read_bytes())
        return digest.hexdigest()


def _categories() -> tuple[list[list[object]], dict[str, int]]:
    rows: list[list[object]] = []
    leaf_ids: dict[str, int] = {}
    for top_id, top in enumerate(ref.CATEGORIES, start=1):
        rows.append([top_id, top, ""])
    next_id = len(ref.CATEGORIES) + 1
    for top_id, subs in enumerate(ref.CATEGORIES.values(), start=1):
        for sub in subs:
            rows.append([next_id, sub, top_id])
            leaf_ids[sub] = next_id
            next_id += 1
    return rows, leaf_ids


def _products(rng: random.Random, leaf_ids: dict[str, int], profile: Profile) -> list[list]:
    """Rows: id, sku, name, category_id, list_price_cents, cost_cents, is_active, weight."""
    specs: list[tuple[str, str, int]] = []
    for subs in ref.CATEGORIES.values():
        for sub, (noun, (low, high)) in subs.items():
            used: set[str] = set()
            while len(used) < 24:
                name = f"{rng.choice(ref.LINES)} {rng.choice(ref.SERIES)} {noun}"
                if name not in used:
                    used.add(name)
                    specs.append((sub, name, rng.randrange(low, high + 1) * 100 - 1))
    specs += list(ref.NEAR_DUPLICATES) + list(ref.INJECTION_NAMES)
    rows = []
    for product_id, (sub, name, price) in enumerate(specs, start=1):
        price = int(price * (1 + rng.uniform(-profile.price_jitter, profile.price_jitter)))
        cost = int(price * rng.uniform(0.42, 0.6))
        active = "f" if rng.random() < 0.1 else "t"
        weight = 1 / (rng.random() * 40 + 1)
        sku = f"HP-{leaf_ids[sub]:02d}-{product_id:05d}"
        rows.append([product_id, sku, name, leaf_ids[sub], price, cost, active, weight])
    return rows


def _email(rng: random.Random, first: str, last: str, domain: str) -> str:
    local = rng.choice(
        [f"{first}.{last}", f"{first[0]}{last}", f"{first}{last}{rng.randrange(10, 99)}"]
    )
    style = rng.random()
    if style < 0.55:
        return f"{local}@{domain}".lower()
    if style < 0.85:
        return f"{local}@{domain}"
    return f"{local}@{domain.upper()}"


def _customers(rng: random.Random, profile: Profile) -> tuple[list[list], list[int]]:
    """Rows: id, first, last, email, phone, city, state, zip, created_at (set later), opt-out."""
    states = list(ref.STATES)
    cum = list(accumulate(ref.STATES[s][0] for s in states))
    internal_count = round(profile.customers * profile.internal_share)
    internal_ids = sorted(rng.sample(range(1, profile.customers + 1), internal_count))
    internal = set(internal_ids)
    rows = []
    for customer_id in range(1, profile.customers + 1):
        first, last = rng.choice(ref.FIRST_NAMES), rng.choice(ref.LAST_NAMES)
        if customer_id in internal:
            state = rng.choice(ref.INTERNAL_STATES)
            email = _email(rng, first, last, ref.INTERNAL_DOMAIN)
            if rng.random() < 0.5:
                email = email.replace("harborpine.com", "HarborPine.com").replace(
                    "HARBORPINE.COM", "HarborPine.com"
                )
        else:
            state = states[bisect(cum, rng.random() * cum[-1])]
            email = _email(rng, first, last, rng.choice(ref.EMAIL_DOMAINS))
            if rng.random() < 0.0005:  # fans of the brand, not staff
                email = f"harborpine.fan{customer_id}@{rng.choice(ref.EMAIL_DOMAINS)}"
        _, _, (zip_low, zip_high), cities = ref.STATES[state]
        zip_code = f"{rng.randint(zip_low, zip_high):03d}{rng.randrange(100):02d}"
        phone = (
            ""
            if rng.random() < 0.15
            else f"({rng.randint(201, 989)}) 555-01{rng.randrange(100):02d}"
        )
        opt_out = "t" if rng.random() < 0.08 else "f"
        rows.append(
            [
                customer_id,
                first,
                last,
                email,
                phone,
                rng.choice(cities),
                state,
                zip_code,
                "",
                opt_out,
            ]
        )
    return rows, internal_ids


def _order(
    rng: random.Random,
    profile: Profile,
    products: list[list],
    product_cum: list[float],
    item_range: tuple[int, int] | None,
    quantity_range: tuple[int, int] | None,
    promo_day: bool,
) -> tuple[list[tuple[int, int, int]], int, int]:
    """Lines (product_id, quantity, unit price), subtotal, discount."""
    if item_range:
        count = rng.randint(*item_range)
    else:
        count = rng.choices(ITEM_COUNTS, ITEM_COUNT_WEIGHTS)[0]
    lines = []
    for _ in range(count):
        product = products[bisect(product_cum, rng.random() * product_cum[-1])]
        if quantity_range:
            quantity = rng.randint(*quantity_range)
        else:
            roll = rng.random()
            quantity = 1 if roll < 0.85 else 2 if roll < 0.96 else 3
        lines.append((product[0], quantity, product[4]))
    subtotal = sum(q * p for _, q, p in lines)
    discount = 0
    if rng.random() < (0.7 if promo_day else profile.discount_rate):
        kind = rng.random()
        if kind < 0.75:
            discount = subtotal * rng.choice((10, 15, 20)) // 100
        else:
            discount = min(1000, subtotal // 2)
    return lines, subtotal, discount


def _orders(
    rng: random.Random,
    profile: Profile,
    products: list[list],
    customers: list[list],
    internal_ids: list[int],
) -> tuple[list[list], list[list]]:
    internal = set(internal_ids)
    regular = [c[0] for c in customers if c[0] not in internal]
    activity = list(accumulate(rng.lognormvariate(0, 1.0) for _ in regular))
    product_cum = list(accumulate(p[7] for p in products))
    state_of = {c[0]: c[6] for c in customers}
    states = list(ref.STATES)
    state_cum = list(accumulate(ref.STATES[s][0] for s in states))
    days = _days()
    weights = [day_weight(d, profile) for d in days]
    scale = profile.orders / sum(weights)
    hours = list(range(24))
    drafts: list[tuple] = []  # (ts, customer, channel, ship_state, lines, subtotal, discount, day)
    regular_net = 0
    for day, weight in zip(days, weights, strict=True):
        turkey = thanksgiving(day.year)
        promo = day in (turkey + timedelta(days=1), turkey + timedelta(days=4))
        app_share = 0.3 + 0.15 * (day - FIRST_DAY).days / (LAST_DAY - FIRST_DAY).days
        for _ in range(round(weight * scale * rng.uniform(0.92, 1.08))):
            customer = regular[bisect(activity, rng.random() * activity[-1])]
            ts = _utc(day, rng.choices(hours, HOUR_WEIGHTS)[0], rng)
            channel = "app" if rng.random() < app_share else "web"
            ship = state_of[customer]
            if rng.random() < 0.05:
                ship = states[bisect(state_cum, rng.random() * state_cum[-1])]
            lines, subtotal, discount = _order(
                rng, profile, products, product_cum, None, None, promo
            )
            regular_net += subtotal - discount
            drafts.append((ts, customer, channel, ship, lines, subtotal, discount, day))
    # Internal test orders: mid-sized, on weekday office hours. A few heavy accounts place enough
    # of them to rank among the top spenders every fiscal year; the rest stay small.
    heavy = profile.heavy_internal_accounts
    internal_cum = list(
        accumulate(
            profile.heavy_internal_weight if rank < heavy else 1.0
            for rank in range(len(internal_ids))
        )
    )
    shuffled = internal_ids[:]
    rng.shuffle(shuffled)
    target = regular_net * profile.internal_revenue_share
    internal_net = 0
    while internal_net < target:
        customer = shuffled[bisect(internal_cum, rng.random() * internal_cum[-1])]
        day = rng.choice(days)
        while day.weekday() >= 5:
            day = rng.choice(days)
        ts = _utc(day, rng.randint(9, 16), rng)
        lines, subtotal, discount = _order(
            rng, profile, products, product_cum, (2, 6), (1, 1), False
        )
        internal_net += subtotal - discount
        drafts.append((ts, customer, "web", state_of[customer], lines, subtotal, discount, day))
    drafts.sort(key=lambda d: (d[0], d[1]))
    orders, items = [], []
    tax_of = {s: ref.STATES[s][1] * profile.tax_scale for s in states}
    item_id = 0
    for order_id, (ts, customer, channel, ship, lines, subtotal, discount, day) in enumerate(
        drafts, start=1
    ):
        net = subtotal - discount
        tax = round(net * tax_of[ship])
        shipping = 0 if net >= 7500 else 795
        if rng.random() < 0.08:
            shipping = 1995
        age = (LAST_DAY - day).days
        if rng.random() < profile.cancel_rate:
            status = 5
        elif age > 9:
            status = 4
        else:
            status = 1 if age < 1 else 2 if age < 3 else 3
        total = net + tax + shipping
        orders.append(
            [order_id, customer, _ts(ts), status, channel, ship, subtotal, discount, tax,
             shipping, total]
        )  # fmt: skip
        for product_id, quantity, price in lines:
            item_id += 1
            items.append([item_id, order_id, product_id, quantity, price])
    return orders, items


def _set_created_at(rng: random.Random, customers: list[list], orders: list[list]) -> None:
    """Sign-up before the first order; customers without orders sign up any time."""
    first_order: dict[int, str] = {}
    for order in orders:  # sorted by time, so the first seen is the first order
        first_order.setdefault(order[1], order[2])
    start = datetime(2021, 1, 1, tzinfo=UTC)
    end = datetime(2026, 1, 31, 23, 0, tzinfo=UTC)
    for row in customers:
        first = first_order.get(row[0])
        if first:
            latest = datetime.strptime(first, "%Y-%m-%d %H:%M:%S+00").replace(tzinfo=UTC)
            latest -= timedelta(minutes=5)
            earliest = max(start, latest - timedelta(days=400))
        else:
            earliest, latest = start, end
        span = int((latest - earliest).total_seconds())
        row[8] = _ts(earliest + timedelta(seconds=rng.randrange(max(span, 1))))
