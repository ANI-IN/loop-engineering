"""The five views. Rendering only — no view makes a model call in these tests."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from loopeng.agent.classify import Outcome
from loopeng.agent.trap import TrapState, run_trap
from loopeng.gold.build import build_gold
from loopeng.views import agent, chrome, dial, render, verify
from loopeng.warehouse.connect import ensure_warehouse

REPO_ROOT = Path(__file__).resolve().parent.parent


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
    render.grid(state, ids)
    state.reveal()
    render.grid(state, ids)
    render.scoreboard(state)

    assert client.calls == after_run, "the view's reveal path made a model call"


def test_visible_failures_look_identical_to_successes_before_reveal(items, warehouse):
    """A cell reading 'query failed' before the reveal hands the room a free answer
    key for that row."""
    subset = items[:2]
    client = ScriptedClient("SELECT * FROM no_such_table")
    state = run_trap(subset, warehouse, arms=(("worker", "L3"),), client=client)
    ids = [i.item_id for i in subset]

    before = render.grid(state, ids)
    outcomes = {c.judgement.outcome for c in state.cells.values()}
    assert Outcome.VISIBLE_FAILURE in outcomes, "this fixture should produce failures"
    assert "failure" not in before.lower()
    assert "wrong" not in before.lower()
    assert before.count(render.LANDED) == len(subset)

    state.reveal()
    assert "visible failure" in render.grid(state, ids)


def test_the_scoreboard_is_withheld_not_absent(items, warehouse):
    client = ScriptedClient("SELECT COUNT(*) FROM products")
    state = run_trap(items[:2], warehouse, arms=(("worker", "L3"),), client=client)
    assert "withheld, not deferred" in render.scoreboard(state)


def test_an_unlanded_cell_renders_as_pending():
    state = TrapState()
    assert render.PENDING in render.grid(state, ["p01_product_count__00"])


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


def test_a_row_with_no_cells_says_awaiting_measurement_not_a_conclusion():
    """This test replaced one that PINNED the typed conclusions.

    The old version asserted the L3 row said "cannot tell apart" and "not equal" — text
    that was hardcoded in the view with a typed p-value beside it. Asserting it kept the
    defect in place: the test and the code agreed, and both were wrong. The row must still
    render, because a missing "cannot tell apart" row invites the room to fill the gap
    themselves; it must render an absence, not a stored finding.
    """
    rendered = dial._comparison([])

    assert dial.AWAITING in rendered
    for level in ("L0", "L3"):
        assert f"| {level} |" in rendered, "the row must render even with no cells"
    assert "p=" not in rendered, "no typed p-value may survive here"
    assert "McNemar exact p" not in rendered


def test_the_reading_is_derived_from_the_cells_on_screen():
    """And the derived answer is not what was typed: this comparison is cross-model, so
    diff refuses a p-value — the typed readings were asserting exactly the significance
    claim pre_registration forbids in words."""
    def cell(key, role, level, mode, correct):
        return {"key": key, "label": key, "role": role, "level": level, "mode": mode,
                "replicate": 0, "complete": True, "rate_value": 0.1, "rate_n": 10,
                "silent_error_rate": "10.0% (n=10)", "cost_usd": {"value": 0.1},
                "items": [{"item_id": f"i{n}", "correct": correct,
                           "ran_and_returned": True} for n in range(10)]}

    rendered = dial._comparison([
        cell("worker_L0_loop_r0", "worker", "L0", "loop", True),
        cell("frontier_L0_one_shot_r0", "frontier", "L0", "one_shot", False),
    ])

    assert "No p-value" in rendered
    assert "cannot be pinned" in rendered
    assert "p=0.039" not in rendered


def test_no_stored_conclusion_is_typed_into_the_dial_view():
    """The regression, aimed at the source rather than at the render."""
    from pathlib import Path

    source = (Path(__file__).resolve().parent.parent
              / "src" / "loopeng" / "views" / "dial.py").read_text(encoding="utf-8")
    body = source.split('"""', 2)[-1]  # past the module docstring, which tells the story
    for typed in ("p=0.039", "p=0.250", "McNemar exact p="):
        assert typed not in body, f"{typed!r} is typed into views/dial.py again"


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


# ---- one boundary, and it is enforced ---------------------------------------
#
# There were two `build_trap_app` implementations, in `agent/ui.py` and `views/trap.py`,
# and they had ALREADY drifted: different outcome labels, different withheld-scores
# wording, one checking `len(state.arms) == 2` and the other `PAIRED_ARM_COUNT`, one
# rendering a null metric through a helper and the other inline. `render_attempts` was
# also defined twice, as two genuinely different functions sharing a name. And
# `views/agent.py` imported from `agent/ui.py` while `views/oversight.py` imported from
# `triage/ui.py`, so the boundary was crossed in both directions.
#
# The rule now: `views/` owns all Gradio composition; `*/ui.py` modules own none, and
# there are none left.


def _src_files():
    root = REPO_ROOT / "src" / "loopeng"
    return sorted(root.rglob("*.py"))


def _definitions_of(name: str) -> list[str]:
    import ast

    found = []
    for path in _src_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == name:
                found.append(str(path.relative_to(REPO_ROOT)))
    return sorted(found)


@pytest.mark.parametrize(
    "name",
    ["build_trap_app", "build_run_app", "build_agent_app", "build_intervention_app",
     "render_attempt_timeline", "render_cost", "render_metric", "render_declined",
     "grid", "scoreboard"],
)
def test_each_view_helper_is_defined_exactly_once(name):
    assert len(_definitions_of(name)) == 1, (
        f"{name} is defined in {_definitions_of(name)}; two copies is two places for "
        f"the wording of a disclosure to diverge"
    )


def test_render_attempts_is_gone_as_a_name():
    """It named two different functions over two different inputs. That is how
    views/agent.py and views/oversight.py ended up importing "the same" helper from two
    different modules."""
    assert _definitions_of("render_attempts") == []


def test_no_ui_module_survives_outside_views():
    """`*/ui.py` owning gr.Blocks is what made the boundary meaningless."""
    strays = [
        str(path.relative_to(REPO_ROOT)) for path in _src_files()
        if path.name == "ui.py"
    ]
    assert strays == [], f"{strays} still exist; views/ owns Gradio composition"


def test_only_views_import_gradio():
    """The enforcement, aimed at imports rather than at file names, so a differently
    named module cannot reintroduce the same problem."""
    offenders = []
    for path in _src_files():
        if path.parent.name == "views":
            continue
        if "import gradio" in path.read_text(encoding="utf-8"):
            offenders.append(str(path.relative_to(REPO_ROOT)))
    assert offenders == [], f"{offenders} import gradio outside views/"


def test_the_render_module_composes_nothing():
    """It holds pure string renderers. A gr.Blocks here would put the boundary back
    where it was.

    Checked against the AST rather than the text, because the docstring says the words
    "no `gr.Blocks` in this file, ever" and a substring search cannot tell a rule from
    its violation.
    """
    import ast

    path = REPO_ROOT / "src" / "loopeng" / "views" / "render.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
        and node.value.id == "gr"
    ]
    assert calls == [], f"views/render.py touches gr.{calls[0].attr}"
    assert "import gradio" not in path.read_text(encoding="utf-8")


def test_the_surviving_outcome_labels_are_not_emoji():
    """Chosen deliberately. Emoji render at the mercy of whichever font the projector's
    browser resolves, and a missing glyph in the cell that should read "silently wrong"
    is the worst place in this project for a rendering failure."""
    for label in render.OUTCOME_LABELS.values():
        assert label.isascii(), f"{label!r} will not survive a projector's font stack"
    assert "SILENTLY WRONG" in render.OUTCOME_LABELS[Outcome.SILENT_ERROR]


def test_the_withheld_line_states_the_property_not_the_button():
    assert "withheld, not deferred" in render.WITHHELD
