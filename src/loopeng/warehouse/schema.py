"""The warehouse's shape and vocabulary, declared once.

Split from the generator deliberately. This module is what the prompt renderer,
the gold patterns, and the verifiers all read; the generator merely fills tables
that are described here. Keeping the description separate from the data means a
rule can be added to the semantic model and rendered into a prompt without
touching the code that produces rows.
"""

from pathlib import Path

import yaml

TABLES = ("customers", "orders", "order_items", "products", "refunds")
CATEGORIES = ("apparel", "electronics", "home", "outdoors", "beauty")
REGIONS = ("NA", "EMEA", "APAC", "LATAM", "ANZ")
CURRENCIES = ("USD", "EUR", "JPY")

# The generator places orders across calendar 2025; these are the months gold
# patterns parameterise over.
MONTHS = ("2025-01-01", "2025-02-01", "2025-03-01", "2025-04-01", "2025-05-01")

_SEMANTIC_MODEL_PATH = Path(__file__).parent / "semantic_model.yaml"

# Ordered so the file can be executed top to bottom against an empty database:
# referenced tables are created before the tables that point at them. No foreign
# key constraints are declared — the traps in this warehouse are join and filter
# mistakes, and a database that refuses to hold an order pointing at a deleted
# customer would remove the soft-delete trap before the model ever sees it.
#
# Money columns are BIGINT because they hold minor units; JPY amounts in whole
# yen and USD amounts in cents share these columns, and the semantic model's
# usd_factor is what reconciles the two scales.
SCHEMA_DDL = """CREATE TABLE products (
    product_id INTEGER PRIMARY KEY,
    category VARCHAR NOT NULL,
    list_price_minor BIGINT NOT NULL
);

CREATE TABLE customers (
    customer_id INTEGER PRIMARY KEY,
    region VARCHAR NOT NULL,
    is_internal BOOLEAN NOT NULL,
    deleted_at TIMESTAMP
);

CREATE TABLE orders (
    order_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    status VARCHAR NOT NULL,
    currency VARCHAR NOT NULL,
    amount_minor BIGINT NOT NULL,
    placed_at TIMESTAMP NOT NULL,
    deleted_at TIMESTAMP
);

CREATE TABLE order_items (
    order_item_id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    qty INTEGER NOT NULL,
    unit_price_minor BIGINT NOT NULL
);

CREATE TABLE refunds (
    refund_id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL,
    amount_minor BIGINT NOT NULL,
    issued_at TIMESTAMP NOT NULL
);
"""


def load_semantic_model() -> dict:
    return yaml.safe_load(_SEMANTIC_MODEL_PATH.read_text(encoding="utf-8"))
