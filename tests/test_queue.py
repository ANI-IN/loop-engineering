"""The Level 3 queue: atomic claim, and the omissions that are deliberate."""

from types import SimpleNamespace

import pytest

from loopeng.queue import store, worker
from loopeng.warehouse.connect import ensure_warehouse


@pytest.fixture
def con(tmp_path):
    return store.connect(tmp_path / "q.duckdb")


@pytest.fixture(scope="module")
def warehouse(tmp_path_factory):
    return ensure_warehouse(tmp_path_factory.mktemp("wh") / "w.duckdb", seed=20260729)


class ScriptedClient:
    def __init__(self, sql):
        self.calls = 0
        self._sql = sql
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.calls += 1
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text=self._sql)],
            usage=SimpleNamespace(input_tokens=10, output_tokens=5),
        )


def test_enqueue_then_claim_round_trips(con):
    row_id = store.enqueue(con, "how many products?")
    row = store.claim(con)
    assert row.id == row_id
    assert row.status == store.CLAIMED
    assert row.claimed_at is not None


def test_claiming_an_empty_queue_returns_none(con):
    assert store.claim(con) is None


def test_a_row_can_only_be_claimed_once(con):
    """Two claims on ONE connection. Not "two workers" — see the test below."""
    store.enqueue(con, "q1")
    first = store.claim(con)
    second = store.claim(con)
    assert first is not None
    assert second is None


def test_claims_are_taken_oldest_first(con):
    a = store.enqueue(con, "first")
    store.enqueue(con, "second")
    assert store.claim(con).id == a


def test_a_failed_row_stays_failed(con):
    """No dead-lettering and no retry: nothing sweeps it up, and the evidence stays
    where you can see it. That is the design, not an oversight."""
    row_id = store.enqueue(con, "q")
    store.claim(con)
    store.fail(con, row_id, "it broke")
    assert store.counts(con) == {store.FAILED: 1}
    assert store.claim(con) is None, "a failed row must not be re-claimed"


def test_a_finished_row_is_not_reclaimed(con):
    row_id = store.enqueue(con, "q")
    store.claim(con)
    store.finish(con, row_id, "[[42]]")
    assert store.claim(con) is None
    assert store.all_rows(con)[0].result == "[[42]]"


def test_an_in_flight_row_stays_claimed(con):
    """Ctrl-C during a run leaves the row claimed forever. Visible consequence of
    having no retry logic, and worth showing rather than hiding."""
    store.enqueue(con, "q")
    store.claim(con)
    assert store.counts(con) == {store.CLAIMED: 1}
    assert store.claim(con) is None


def test_the_worker_runs_the_level_2_loop_not_level_1():
    """The teaching point: with nobody watching, the verifiers are the only thing
    between the queue and whatever consumes the answers."""
    import inspect

    source = inspect.getsource(worker)
    assert "run_verified" in source
    assert "verify_governed" in source


def test_the_worker_has_no_backoff_or_retry():
    """Named omissions. A retry hidden in the worker would make the queue look more
    production-ready than it is."""
    import inspect

    source = inspect.getsource(worker).lower()
    assert "backoff" not in source.replace("no backoff", "")
    assert "max_retries" not in source


def test_the_worker_answers_a_queued_question(con, warehouse):
    store.enqueue(con, "how many products?")
    client = ScriptedClient("SELECT COUNT(*) FROM products")
    row = worker.process_one(con, warehouse, client=client)
    assert row is not None
    assert store.counts(con) == {store.DONE: 1}
    assert client.calls == 1


def test_the_worker_marks_a_broken_question_failed(con, warehouse):
    store.enqueue(con, "how many products?")
    client = ScriptedClient("SELECT * FROM no_such_table")
    worker.process_one(con, warehouse, client=client)
    assert store.counts(con) == {store.FAILED: 1}


def test_serve_drains_and_stops(con, warehouse):
    for _ in range(3):
        store.enqueue(con, "how many products?")
    client = ScriptedClient("SELECT COUNT(*) FROM products")
    processed = worker.serve(con, warehouse, poll_seconds=0.0, max_idle_polls=1,
                             client=client)
    assert processed == 3
    assert store.counts(con) == {store.DONE: 3}


def test_serve_on_an_empty_queue_returns_immediately(con, warehouse):
    assert worker.serve(con, warehouse, poll_seconds=0.0, max_idle_polls=1) == 0


def test_the_queue_lives_in_its_own_file(tmp_path):
    """Sharing the warehouse file would mean relaxing its read-only guarantee, which
    Phase 0 spent a test on."""
    assert "warehouse" not in str(store.DEFAULT_QUEUE_PATH)
    con = store.connect(tmp_path / "q.duckdb")
    assert (tmp_path / "q.duckdb").is_file()
    con.close()


# ---- the constraint the runbook has to be honest about -----------------------


def test_a_second_process_cannot_open_the_same_queue(tmp_path):
    """DuckDB's lock is exclusive per file, so there is no two-worker scenario.

    The Level 3 runbook told the room to run a polling worker in one terminal and
    submit from another. That cannot work: the worker holds its connection for its
    whole life, sleeping between polls, so the second terminal dies at connect.

    `store.claim`'s docstring asserted "two workers cannot claim the same row —
    that is the whole of the concurrency story", which is a guarantee about a
    situation the storage engine forbids, and the test above "covered" it with one
    connection used sequentially. Both now say what they actually mean.

    This test pins the constraint so the two-terminal runbook cannot come back
    without something going red.
    """
    import subprocess
    import sys
    import textwrap

    queue = tmp_path / "q.duckdb"
    holder = store.connect(queue)
    store.enqueue(holder, "held open by this process")

    probe = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(f"""
            from loopeng.queue import store
            try:
                store.connect({str(queue)!r})
                print("CONNECTED")
            except Exception as exc:
                print(type(exc).__name__)
        """)],
        capture_output=True, text=True,
    )
    assert "CONNECTED" not in probe.stdout, (
        "a second process opened the queue — if DuckDB has gained multi-writer "
        "support, the Level 3 runbook and store.claim's docstring can both be "
        "made stronger, and this test should be replaced rather than deleted"
    )
    assert "IOException" in probe.stdout, probe.stdout + probe.stderr


def test_sequential_processes_share_the_queue_fine(tmp_path):
    """Which is why the runbook is enqueue-then-drain: each opens and releases."""
    queue = tmp_path / "q.duckdb"

    first = store.connect(queue)
    store.enqueue(first, "written by the first process")
    first.close()

    second = store.connect(queue)
    assert store.counts(second) == {"queued": 1}
    claimed = store.claim(second)
    assert claimed.question == "written by the first process"
