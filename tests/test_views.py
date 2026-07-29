"""The five views. Rendering only — no view makes a model call in these tests."""

from types import SimpleNamespace

import pytest

from loopeng.agent.classify import Outcome
from loopeng.agent.trap import TrapState, run_trap
from loopeng.gold.build import build_gold
from loopeng.views import agent, chrome, dial, trap, verify
from loopeng.warehouse.connect import ensure_warehouse


@pytest.fixture(scope="module")
def warehouse(tmp_path_factory):
    return ensure_warehouse(tmp_path_factory.mktemp("wh") / "w.duckdb", seed=20260729)


@pytest.fixture(scope="module")
def items(warehouse):
    return build_gold(warehouse)


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


# ---- TRAP: reveal is a state flip, tested against the VIEW ------------------


def test_reveal_makes_zero_model_calls_through_the_view(items, warehouse):
    """The test previously covered trap.py only. Re-running to score would burn the
    whole wall-clock again and lose the room, so the view path needs it too."""
    subset = items[:3]
    client = ScriptedClient("SELECT COUNT(*) FROM products")
    state = run_trap(subset, warehouse, arms=(("worker", "L3"),), client=client)
    after_run = client.calls

    ids = [i.item_id for i in subset]
    trap.grid(state, ids)
    state.reveal()
    trap.grid(state, ids)
    trap.scoreboard(state)

    assert client.calls == after_run, "the view's reveal path made a model call"


def test_visible_failures_look_identical_to_successes_before_reveal(items, warehouse):
    """A cell reading 'query failed' before the reveal hands the room a free answer
    key for that row."""
    subset = items[:2]
    client = ScriptedClient("SELECT * FROM no_such_table")
    state = run_trap(subset, warehouse, arms=(("worker", "L3"),), client=client)
    ids = [i.item_id for i in subset]

    before = trap.grid(state, ids)
    outcomes = {c.judgement.outcome for c in state.cells.values()}
    assert Outcome.VISIBLE_FAILURE in outcomes, "this fixture should produce failures"
    assert "failure" not in before.lower()
    assert "wrong" not in before.lower()
    assert before.count(trap.LANDED) == len(subset)

    state.reveal()
    assert "visible failure" in trap.grid(state, ids)


def test_the_scoreboard_is_withheld_not_absent(items, warehouse):
    client = ScriptedClient("SELECT COUNT(*) FROM products")
    state = run_trap(items[:2], warehouse, arms=(("worker", "L3"),), client=client)
    assert "withheld, not deferred" in trap.scoreboard(state)


def test_an_unlanded_cell_renders_as_pending():
    state = TrapState()
    assert trap.PENDING in trap.grid(state, ["p01_product_count__00"])


# ---- AGENT: the enqueue box works with no worker running --------------------


def test_enqueue_works_when_no_worker_is_running(tmp_path):
    """A row submitted with no worker sits in `queued`. The queue did not lose the
    question; nothing has picked it up yet, and that is worth showing."""
    from loopeng.queue import store

    queue = tmp_path / "q.duckdb"
    con = store.connect(queue)
    store.enqueue(con, "What was net revenue in March 2025?")
    con.close()

    table = agent._queue_table(queue)
    assert "queued" in table
    assert "net revenue" in table


def test_an_empty_queue_says_so_rather_than_rendering_nothing(tmp_path):
    assert "empty" in agent._queue_table(tmp_path / "q.duckdb")


# ---- DIAL: live and reference are visibly different -------------------------


def test_a_reference_row_is_badged_and_dated():
    cells = [{
        "key": "frontier_L3_one_shot_r0", "label": "Sonnet · L3 · one-shot",
        "role": "frontier", "level": "L3", "mode": "one_shot", "replicate": 0,
        "complete": True, "rate_value": 0.0, "rate_n": 43,
        "silent_error_rate": "0.0% (n=43, measured 2026-07-29)",
        "cost_usd": {"value": 0.36}, "reference": True, "measured_on": "2026-07-29",
    }]
    rendered = dial._rows(cells)
    assert "REFERENCE" in rendered
    assert "2026-07-29" in rendered
    assert "LIVE" not in rendered


def test_a_live_row_is_badged_live():
    cells = [{
        "key": "worker_L3_loop_r0", "label": "Haiku · L3 · loop",
        "role": "worker", "level": "L3", "mode": "loop", "replicate": 0,
        "complete": True, "rate_value": 0.09, "rate_n": 43,
        "silent_error_rate": "9.3% (n=43, computed 20:11 today)",
        "cost_usd": {"value": 0.1}, "reference": False,
    }]
    assert "LIVE" in dial._rows(cells)


def test_the_comparison_carries_the_badge_on_both_sides():
    """At delivery this compares a live line against a frozen one, and that has to be
    visible on the row rather than in a caption read afterwards."""
    def cell(key, role, level, mode, is_ref):
        return {"key": key, "label": key, "role": role, "level": level, "mode": mode,
                "replicate": 0, "complete": True, "rate_value": 0.1, "rate_n": 40,
                "silent_error_rate": "10.0% (n=40)", "cost_usd": {"value": 0.1},
                "reference": is_ref, "measured_on": "2026-07-29"}

    cells = [cell("worker_L0_loop_r0", "worker", "L0", "loop", False),
             cell("frontier_L0_one_shot_r0", "frontier", "L0", "one_shot", True)]
    rendered = dial._comparison(cells)
    assert "LIVE" in rendered and "REFERENCE" in rendered
    assert "Read the badges before reading the numbers" in rendered


def test_the_l3_reading_says_cannot_tell_not_equal():
    """The conclusion changed after the wording fix and the view must not say equal."""
    rendered = dial._comparison([])
    assert "cannot tell apart" in rendered
    assert "not equal" in rendered


# ---- OVERSIGHT caveats are in the view, not a report -----------------------


def test_the_oversight_caveats_are_rendered():
    from loopeng.views.oversight import ABSTENTION_READING, ESCALATION_CAVEAT, THRESHOLD_CAVEAT

    assert "not on principle" in THRESHOLD_CAVEAT
    assert "n=12" in THRESHOLD_CAVEAT
    assert "not how often" in ESCALATION_CAVEAT
    assert "does not substitute for the spec" in ABSTENTION_READING


# ---- chrome ----------------------------------------------------------------


def test_every_stamp_carries_time_and_n():
    assert "computed" in chrome.stamp(42) and "n=42" in chrome.stamp(42)


def test_a_stamp_without_an_n_says_not_yet_measured():
    assert "not yet measured" in chrome.stamp(None)


def test_a_reference_stamp_never_claims_it_was_computed_now():
    rendered = chrome.reference_stamp("2026-07-29", 43)
    assert "measured 2026-07-29" in rendered
    assert "not computed in this session" in rendered
    assert "today" not in rendered


def test_concurrency_is_explicit_and_the_queue_is_bounded():
    """Gradio defaults default_concurrency_limit to 1, which serialises everything and
    reads as a hang with two browsers open."""
    assert chrome.CONCURRENCY_LIMIT > 1
    assert chrome.MAX_QUEUE_SIZE > 0


def test_the_lan_url_is_offered_as_a_fallback():
    url = chrome.lan_url(7860)
    assert url is None or url.startswith("http://")


def test_verify_view_exposes_the_probe_surface():
    table = verify._probe_table()
    assert "sound" in table
    assert "nearby-legitimate" in table


def test_the_projector_css_is_actually_applied_not_merely_defined():
    """It was defined and never passed for a while — the same class of defect as a
    rule declared in config that nothing enforces."""
    import inspect

    source = inspect.getsource(chrome.launch)
    assert "css=PROJECTOR_CSS" in source


def test_the_projector_css_sizes_type_for_a_room():
    css = chrome.PROJECTOR_CSS
    assert "font-size" in css
    for selector in ("h1", "code", "button", ".stamp"):
        assert selector in css


def test_launch_binds_to_all_interfaces_so_the_lan_fallback_resolves():
    import inspect

    source = inspect.getsource(chrome.launch)
    assert '"0.0.0.0"' in source
