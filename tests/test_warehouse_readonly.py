import duckdb
import pytest

from loopeng.warehouse.connect import QueryTimeout, agent_connection, ensure_warehouse, run_sql


@pytest.fixture(scope="module")
def warehouse(tmp_path_factory):
    return ensure_warehouse(tmp_path_factory.mktemp("wh") / "w.duckdb", seed=20260729)


def test_insert_fails(warehouse):
    con = agent_connection(warehouse)
    with pytest.raises(duckdb.Error):
        con.execute("INSERT INTO products VALUES (999999, 'x', 1)")
    con.close()


def test_drop_fails(warehouse):
    con = agent_connection(warehouse)
    with pytest.raises(duckdb.Error):
        con.execute("DROP TABLE products")
    con.close()


def test_update_and_delete_fail(warehouse):
    con = agent_connection(warehouse)
    with pytest.raises(duckdb.Error):
        con.execute("UPDATE products SET category = 'x'")
    with pytest.raises(duckdb.Error):
        con.execute("DELETE FROM products")
    con.close()


def test_create_table_fails(warehouse):
    """The agent must not be able to materialise a scratch table and query that
    instead — it would work, and it would write to the file the whole project
    treats as immutable ground truth."""
    con = agent_connection(warehouse)
    with pytest.raises(duckdb.Error):
        con.execute("CREATE TABLE scratch AS SELECT * FROM products")
    con.close()


def test_select_works(warehouse):
    assert run_sql("SELECT COUNT(*) FROM products", warehouse)[0][0] > 0


def test_ensure_is_idempotent(warehouse):
    from loopeng.warehouse.generate import content_checksum

    before = content_checksum(warehouse)
    ensure_warehouse(warehouse, seed=20260729)
    assert content_checksum(warehouse) == before


def test_ensure_generates_when_absent(tmp_path):
    path = tmp_path / "fresh.duckdb"
    assert not path.exists()
    ensure_warehouse(path, seed=20260729)
    assert path.exists()
    assert run_sql("SELECT COUNT(*) FROM orders", path)[0][0] > 0


def test_run_sql_enforces_its_timeout(warehouse):
    """The timeout is not decorative. In Phase 3 the SQL comes from a model, and a
    runaway cross join would hang the sweep with no upper bound on the cell. A
    declared timeout_s that did not actually interrupt anything would be the
    declared-versus-enforced defect this project is about, in our own foundation."""
    runaway = "SELECT COUNT(*) FROM range(100000000) a, range(1000) b, range(1000) c"
    with pytest.raises(QueryTimeout) as exc:
        run_sql(runaway, warehouse, timeout_s=0.5)
    assert "0.5" in str(exc.value)


def test_timeout_is_distinguishable_from_a_sql_error(warehouse):
    """Phase 2 needs to tell "the model wrote a runaway query" apart from "the model
    wrote invalid SQL". They are different failure classes and land in different
    buckets of the taxonomy, so they cannot share an exception type."""
    with pytest.raises(duckdb.Error) as exc:
        run_sql("SELECT * FROM no_such_table", warehouse)
    assert not isinstance(exc.value, QueryTimeout)


def test_a_fast_query_is_unaffected_by_the_timeout(warehouse):
    assert run_sql("SELECT 1", warehouse, timeout_s=0.5) == [(1,)]


def test_the_connection_survives_a_timeout(warehouse):
    """A timed-out query must not poison the warehouse for the next item."""
    with pytest.raises(QueryTimeout):
        run_sql(
            "SELECT COUNT(*) FROM range(100000000) a, range(1000) b, range(1000) c",
            warehouse,
            timeout_s=0.5,
        )
    assert run_sql("SELECT COUNT(*) FROM products", warehouse)[0][0] > 0
