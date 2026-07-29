import sqlglot

from loopeng.warehouse.schema import (
    CATEGORIES,
    CURRENCIES,
    MONTHS,
    REGIONS,
    SCHEMA_DDL,
    TABLES,
    load_semantic_model,
)


def test_ddl_parses_as_duckdb():
    statements = [s for s in SCHEMA_DDL.split(";") if s.strip()]
    assert len(statements) == len(TABLES)
    for statement in statements:
        sqlglot.parse_one(statement, read="duckdb")


def test_ddl_declares_every_table_in_the_semantic_model():
    declared = {table["name"] for table in load_semantic_model()["tables"]}
    assert declared == set(TABLES)
    for table in TABLES:
        assert f"CREATE TABLE {table}" in SCHEMA_DDL


def test_every_column_in_the_semantic_model_exists_in_the_ddl():
    """The YAML is what gets rendered into the model's prompt at L3. If it
    describes a column the warehouse does not have, the prompt teaches the model
    to write SQL that cannot run."""
    for table in load_semantic_model()["tables"]:
        for column in table["columns"]:
            assert column in SCHEMA_DDL, f"{table['name']}.{column} missing from DDL"


def test_every_rule_carries_a_statement_and_valid_targets():
    model = load_semantic_model()
    table_names = {table["name"] for table in model["tables"]}
    assert model["rules"]
    for name, rule in model["rules"].items():
        assert rule["statement"].strip(), f"rule {name} has no statement to render"
        assert rule["applies_to"], f"rule {name} applies to nothing"
        assert set(rule["applies_to"]) <= table_names, f"rule {name} names an unknown table"


def test_every_metric_references_only_declared_rules():
    model = load_semantic_model()
    known = set(model["rules"])
    for metric in model["metrics"]:
        assert set(metric["rules"]) <= known, f"metric {metric['name']} names an unknown rule"


def test_usd_factor_covers_exactly_the_currencies_in_use():
    """A currency in the data with no factor would make conversion impossible;
    a factor for a currency that never appears is dead config."""
    assert set(load_semantic_model()["usd_factor"]) == set(CURRENCIES)


def test_jpy_factor_reflects_zero_decimal_places():
    """USD and EUR are stored in cents, JPY in whole yen. The factor folds the
    decimal scale together with the FX rate, so JPY's is ~100x larger than a
    naive rate would suggest. Getting this wrong is the minor-units trap.

    The naive rate is the trap: treating yen as a two-decimal currency divides
    JPY's factor by 100, landing it at ~0.000067. USD's factor is exactly the
    two-decimal scale (0.01), so a tenth of it sits between the correct value
    and the cent-scaled mistake and separates them.
    """
    factors = load_semantic_model()["usd_factor"]
    assert factors["JPY"] > factors["USD"] / 10


def test_seven_rules_are_declared():
    """The count is asserted so that deleting a rule is a test failure rather than
    a silent reduction in what the workshop can demonstrate."""
    assert len(load_semantic_model()["rules"]) == 7


def test_vocabularies_are_non_empty_and_distinct():
    for vocabulary in (TABLES, CATEGORIES, REGIONS, CURRENCIES, MONTHS):
        assert vocabulary
        assert len(set(vocabulary)) == len(vocabulary)


def test_five_parameterisations_are_available_per_vocabulary():
    """Gold patterns take five parameterisations each; a vocabulary shorter than
    that would silently produce duplicate gold items."""
    assert len(CATEGORIES) >= 5
    assert len(REGIONS) >= 5
    assert len(MONTHS) >= 5
