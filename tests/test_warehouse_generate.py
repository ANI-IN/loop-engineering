import duckdb

from loopeng.warehouse.generate import content_checksum, generate
from loopeng.warehouse.schema import TABLES


def test_same_seed_produces_identical_contents(tmp_path):
    """The contract is content-identity, not byte-identity: DuckDB may write
    version or timestamp metadata into the file header, and this project does not
    claim byte-identity without a test that enforces it."""
    a, b = tmp_path / "a.duckdb", tmp_path / "b.duckdb"
    generate(a, seed=20260729)
    generate(b, seed=20260729)
    assert content_checksum(a) == content_checksum(b)


def test_different_seed_produces_different_contents(tmp_path):
    a, b = tmp_path / "a.duckdb", tmp_path / "b.duckdb"
    generate(a, seed=1)
    generate(b, seed=2)
    assert content_checksum(a) != content_checksum(b)


def test_byte_identity_is_reported_not_assumed(tmp_path):
    """Informational. If this passes, the stronger claim holds and can be stated.
    If it fails, the contract stays content-identity and nothing is broken."""
    a, b = tmp_path / "a.duckdb", tmp_path / "b.duckdb"
    generate(a, seed=7)
    generate(b, seed=7)
    byte_identical = a.read_bytes() == b.read_bytes()
    print(f"byte_identical={byte_identical}")


def test_every_table_is_populated(tmp_path):
    counts = generate(tmp_path / "w.duckdb", seed=20260729)
    assert set(counts) == set(TABLES)
    assert all(count > 0 for count in counts.values())


def test_regenerating_over_an_existing_file_replaces_it(tmp_path):
    """ensure_warehouse in Task 8 calls this on a path that may already hold a
    warehouse from a previous seed. Appending instead of replacing would double
    every row and quietly change every gold answer."""
    path = tmp_path / "w.duckdb"
    first = generate(path, seed=1)
    second = generate(path, seed=1)
    assert first == second
    assert content_checksum(path)


def test_every_rule_has_rows_that_exercise_it(tmp_path):
    """A rule the data never triggers cannot discriminate L0 from L3, so the
    generator must produce rows on both sides of each rule."""
    path = tmp_path / "w.duckdb"
    generate(path, seed=20260729)
    con = duckdb.connect(str(path), read_only=True)

    def count(sql: str) -> int:
        return con.execute(sql).fetchone()[0]

    assert count("SELECT COUNT(*) FROM customers WHERE deleted_at IS NOT NULL") > 0
    assert count("SELECT COUNT(*) FROM customers WHERE deleted_at IS NULL") > 0
    assert count("SELECT COUNT(*) FROM orders WHERE deleted_at IS NOT NULL") > 0
    assert count("SELECT COUNT(*) FROM orders WHERE status = 'cancelled'") > 0
    assert count("SELECT COUNT(*) FROM orders WHERE status <> 'cancelled'") > 0
    assert count("SELECT COUNT(*) FROM customers WHERE is_internal") > 0
    assert count("SELECT COUNT(*) FROM customers WHERE NOT is_internal") > 0
    assert count("SELECT COUNT(DISTINCT currency) FROM orders") == 3
    assert count("SELECT COUNT(*) FROM refunds") > 0

    # Fan-out is only a trap if some orders have several lines.
    assert count(
        "SELECT COUNT(*) FROM (SELECT order_id FROM order_items "
        "GROUP BY order_id HAVING COUNT(*) > 1)"
    ) > 0

    con.close()


def test_order_total_equals_the_sum_of_its_lines(tmp_path):
    """The fan-out trap has to be arithmetically real, not merely structural. If
    orders.amount_minor were independent of order_items, joining and summing would
    produce a wrong number for a reason that has nothing to do with fan-out, and
    the gold item would be testing the generator rather than the rule."""
    path = tmp_path / "w.duckdb"
    generate(path, seed=20260729)
    con = duckdb.connect(str(path), read_only=True)

    mismatches = con.execute(
        """
        SELECT COUNT(*) FROM (
            SELECT o.order_id
            FROM orders o
            JOIN order_items i ON i.order_id = o.order_id
            GROUP BY o.order_id, o.amount_minor
            HAVING SUM(i.qty * i.unit_price_minor) <> o.amount_minor
        )
        """
    ).fetchone()[0]
    con.close()
    assert mismatches == 0


def test_every_order_has_at_least_one_line(tmp_path):
    path = tmp_path / "w.duckdb"
    generate(path, seed=20260729)
    con = duckdb.connect(str(path), read_only=True)
    orphans = con.execute(
        "SELECT COUNT(*) FROM orders o WHERE NOT EXISTS "
        "(SELECT 1 FROM order_items i WHERE i.order_id = o.order_id)"
    ).fetchone()[0]
    con.close()
    assert orphans == 0


def test_refunds_point_only_at_real_orders(tmp_path):
    """No foreign keys are declared — the soft-delete trap needs orders that point
    at deleted customers — so referential sanity where it *is* required gets a test
    instead."""
    path = tmp_path / "w.duckdb"
    generate(path, seed=20260729)
    con = duckdb.connect(str(path), read_only=True)
    dangling = con.execute(
        "SELECT COUNT(*) FROM refunds r WHERE NOT EXISTS "
        "(SELECT 1 FROM orders o WHERE o.order_id = r.order_id)"
    ).fetchone()[0]
    con.close()
    assert dangling == 0
