"""Prompt caching: the instrument existed, the number was known, the switch was off.

`pricing.py` prices cache writes and reads. `usage.py` accounts for both classes on every
call. `api_probes.probe_prompt_tokens` measures which prefixes clear which model's
minimum. And `cache_control` appeared nowhere in `src/` — grepped, zero occurrences
outside the bookkeeping — so every call re-sent the full schema-plus-rules prefix at full
input price.

The measured answer, from the committed `results/gate0.json`, is that exactly ONE
combination can cache: frontier at L3, 1037 prefix tokens against a 1024 minimum. Haiku's
minimum is four times Sonnet's and its prefix is shorter, so no Haiku prefix here can
cache at all. Both halves of that are asserted below, because "we switched caching on"
would be a misleading claim if the gate were wrong in the permissive direction.
"""

from types import SimpleNamespace

import pytest

from loopeng import caching
from loopeng.agent.loop import _build_messages, run_question
from loopeng.warehouse.connect import ensure_warehouse


@pytest.fixture(scope="module")
def warehouse(tmp_path_factory):
    return ensure_warehouse(tmp_path_factory.mktemp("wh") / "w.duckdb", seed=20260729)


class RecordingClient:
    """Captures the request body so the cache marker can be asserted on it."""

    def __init__(self):
        self.requests = []
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.requests.append(kwargs)
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text="SELECT COUNT(*) FROM products")],
            usage=SimpleNamespace(input_tokens=10, output_tokens=5),
        )


MEASURED = {
    "worker": {"model_id": "claude-haiku-4-5", "cache_minimum": 4096,
               "L0": {"tokens": 286}, "L3": {"tokens": 648}},
    "frontier": {"model_id": "claude-sonnet-5", "cache_minimum": 1024,
                 "L0": {"tokens": 548}, "L3": {"tokens": 1037}},
}


# ---- the gate reads the measurement, and refuses without one -----------------


def test_the_committed_probe_is_what_the_gate_reads():
    """Not an estimate. Token counts are a measurement, and a second worse instrument
    beside a good one would be wrong in the permissive direction."""
    measured = caching.probe()
    assert measured, f"{caching.PROBE_PATH} holds no token counts"
    assert set(measured) == {"worker", "frontier"}


def test_exactly_one_combination_clears_its_minimum():
    """Measured, not assumed. If this changes, the cache note on the COST chart is
    describing something that is no longer true."""
    cacheable = {
        (role, level)
        for role in ("worker", "frontier")
        for level in ("L0", "L3")
        if caching.prefix_is_cacheable(role, level)
    }
    assert cacheable == {("frontier", "L3")}


def test_no_haiku_prefix_can_cache():
    """Haiku's minimum is four times Sonnet's and its prefix is shorter. That asymmetry
    is silent — no error, just a different cost per cell, on the cheaper model."""
    assert not caching.prefix_is_cacheable("worker", "L0")
    assert not caching.prefix_is_cacheable("worker", "L3")


def test_with_no_measurement_the_gate_refuses_rather_than_guessing(monkeypatch):
    """A cache_control marker on a prefix too short to cache is not an error, but it
    changes the request for nothing and makes the reported hit rate a fiction."""
    monkeypatch.setattr(caching, "probe", lambda path=None: {})
    assert not caching.prefix_is_cacheable("frontier", "L3")
    assert "switched off rather than guessed at" in caching.findings({})[0]


def test_an_unreadable_probe_is_not_a_crash(tmp_path):
    broken = tmp_path / "gate0.json"
    broken.write_text("{not json", encoding="utf-8")
    assert caching.probe(broken) == {}
    assert caching.probe(tmp_path / "absent.json") == {}


# ---- the request body -------------------------------------------------------


def test_the_request_carries_cache_control_where_the_prefix_clears_the_minimum():
    content = _build_messages("q", "L3", [], role="frontier")[0]["content"]

    assert isinstance(content, list), "the prefix was not split into a cacheable block"
    assert content[0]["cache_control"] == caching.CACHE_CONTROL
    assert "cache_control" not in content[1], "the question must sit past the boundary"


def test_the_request_does_not_carry_cache_control_where_it_does_not():
    """And the first turn stays the single string it always was, so the request is
    byte-identical to what the reference measurements were taken with."""
    for role, level in (("worker", "L3"), ("worker", "L0"), ("frontier", "L0")):
        content = _build_messages("q", level, [], role=role)[0]["content"]
        assert isinstance(content, str), f"{role}/{level} was split for no benefit"
        assert "Question: q" in content


def test_the_split_prefix_concatenates_to_the_same_text():
    """Two adjacent text blocks are the same conversation as one block containing both.
    If they were not, this would be changing what the model sees."""
    single = _build_messages("q", "L3", [], role="worker")[0]["content"]
    split = _build_messages("q", "L3", [], role="frontier")[0]["content"]

    assert isinstance(single, str) and isinstance(split, list)
    assert "".join(block["text"] for block in split).endswith("Question: q")


def test_the_retry_feedback_stays_outside_the_cached_prefix(warehouse):
    """It has to. Feedback inside the prefix would break the cache on every retry —
    which is every call a loop makes beyond the first."""
    client = RecordingClient()
    run_question("q", warehouse=warehouse, role="frontier", level="L3",
                 client=client, max_attempts=1)

    first_turn = client.requests[0]["messages"][0]["content"]
    cached = next(b for b in first_turn if "cache_control" in b)
    assert "That query failed with" not in cached["text"]


def test_the_cached_prefix_is_identical_across_attempts():
    """The cache only hits if the prefix is byte-identical, so a retry must not perturb
    it. Two calls with different histories, same prefix block."""
    from loopeng.agent.loop import Attempt
    from loopeng.usage import CallUsage

    history = [Attempt(1, "SELECT 1", None, "boom", CallUsage("claude-sonnet-5", "ok"))]
    first = _build_messages("q", "L3", [], role="frontier")[0]["content"][0]
    later = _build_messages("q", "L3", history, role="frontier")[0]["content"][0]

    assert first == later


# ---- what it saved, reported and never zeroed -------------------------------


def test_a_cell_with_no_caching_reports_none_not_zero():
    """It did not achieve a nil hit rate; it had no cache to hit. A zero reads as a
    measurement."""
    assert caching.hit_rate({"input_tokens": 500}) is None
    assert caching.saving_usd({"input_tokens": 500}, "claude-sonnet-5") is None


def test_the_hit_rate_is_reads_over_everything_served():
    tokens = {"cache_read_input_tokens": 49, "cache_creation_input_tokens": 1}
    assert caching.hit_rate(tokens) == pytest.approx(0.98)


def test_the_saving_is_against_paying_full_input_price():
    """Reads bill at 0.10x and writes at 1.25x, so one write plus many reads is far
    below the same tokens at 1.00x."""
    tokens = {"cache_read_input_tokens": 1_000_000, "cache_creation_input_tokens": 0}
    saved = caching.saving_usd(tokens, "claude-sonnet-5")

    from loopeng.pricing import prices_for

    prices = prices_for("claude-sonnet-5")
    assert saved == pytest.approx(prices.input - prices.cache_read)
    assert saved > 0


def test_the_cost_note_says_which_cells_cached_and_what_it_saved():
    from loopeng.sweep.chart_model import cache_note

    cells = [{
        "key": "frontier_L3_loop_r0", "role": "frontier",
        "tokens": {"cache_read_input_tokens": 49_000,
                   "cache_creation_input_tokens": 1_000},
    }]
    note = cache_note(cells)

    assert "PROMPT CACHING applied to 1 of 1 cell(s)" in note
    assert "saving est. $" in note, "dollars must keep the est. prefix"


def test_the_cost_note_explains_absence_rather_than_reporting_a_zero():
    from loopeng.sweep.chart_model import cache_note

    note = cache_note([{"key": "worker_L3_loop_r0", "role": "worker", "tokens": {}}])

    assert "did not apply" in note
    assert "no Haiku cell in this project can cache" in note


def test_the_cell_report_carries_both_cache_token_classes():
    """The accounting existed in usage.py all the way to the cell report and was dropped
    at the last step, which made a cell's own file unable to say whether caching fired."""
    from loopeng.sweep.runner import TOKEN_FIELDS, Cell, summarise_cell

    assert "cache_read_input_tokens" in TOKEN_FIELDS
    assert "cache_creation_input_tokens" in TOKEN_FIELDS

    row = {
        "item_id": "a", "pattern_key": "p", "outcome": "correct",
        "ran_and_returned": True, "correct": True, "termination": "success",
        "n_attempts": 1, "rejections": 0, "cost_usd": 0.01,
        "tokens": {"n_calls": 1, "input_tokens": 10, "output_tokens": 5,
                   "total_tokens": 15, "cache_creation_input_tokens": 100,
                   "cache_read_input_tokens": 900},
    }
    report = summarise_cell(Cell("frontier", "L3", "loop"), [row],
                            complete=True, seconds=1.0)

    assert report["tokens"]["cache_read_input_tokens"] == 900
    assert report["tokens"]["cache_creation_input_tokens"] == 100


def test_a_row_recorded_before_the_cache_fields_existed_still_summarises():
    """Additive schema. A missing class summed as zero is correct — no cache tokens is
    what "caching did not apply" looks like."""
    from loopeng.sweep.runner import Cell, summarise_cell

    row = {
        "item_id": "a", "pattern_key": "p", "outcome": "correct",
        "ran_and_returned": True, "correct": True, "termination": "success",
        "n_attempts": 1, "rejections": 0, "cost_usd": 0.01,
        "tokens": {"n_calls": 1, "input_tokens": 10, "output_tokens": 5,
                   "total_tokens": 15},
    }
    report = summarise_cell(Cell("worker", "L0", "loop"), [row],
                            complete=True, seconds=1.0)

    assert report["tokens"]["cache_read_input_tokens"] == 0


def test_cache_control_is_set_in_exactly_one_place():
    """It was set nowhere. One place, so the gate cannot be bypassed."""
    from pathlib import Path

    src = Path(__file__).resolve().parent.parent / "src" / "loopeng"
    setting = [
        str(path.relative_to(src.parent.parent))
        for path in src.rglob("*.py")
        if '"cache_control"' in path.read_text(encoding="utf-8")
    ]
    assert setting == ["src/loopeng/caching.py"], f"cache_control is set in {setting}"


# ---- E3: backoff, and a concurrency flag that exists ------------------------
#
# README §18 tells the operator to "lower the per-model concurrency before the sweep
# rather than after it starts failing", and there was no flag to do it with — advice that
# can only be followed by patching source is advice most people will not follow. There was
# no backoff either, so a 429 was retried straight back into the same limit.


def test_a_retryable_failure_waits_before_going_round(warehouse):
    """Retrying a 429 immediately arrives back at the same limit and makes it last
    longer than it had to."""
    import anthropic
    import httpx

    from loopeng.agent.loop import run_question

    slept = []

    class Limited:
        def __init__(self):
            self.calls = 0
            self.messages = SimpleNamespace(create=self._create)

        def _create(self, **kwargs):
            self.calls += 1
            raise anthropic.RateLimitError(
                "Error code: 429",
                response=httpx.Response(
                    429, request=httpx.Request("POST", "https://api.anthropic.com/")
                ),
                body=None,
            )

    client = Limited()
    run_question("q", warehouse=warehouse, client=client, max_attempts=3,
                 sleeper=slept.append)

    assert client.calls == 3
    assert len(slept) == 2, "a sleep between each retry, and none after the last"
    assert slept[1] > slept[0], "the fallback backoff must widen"


def test_no_sleep_after_the_final_attempt(warehouse):
    """Waiting after the last call delays the report and changes nothing."""
    from loopeng.agent.loop import run_question

    slept = []

    class Limited:
        def __init__(self):
            self.messages = SimpleNamespace(create=self._create)

        def _create(self, **kwargs):
            raise RuntimeError("overloaded_error")

    run_question("q", warehouse=warehouse, client=Limited(), max_attempts=1,
                 sleeper=slept.append)
    assert slept == []


def test_the_servers_retry_after_wins_over_our_guess():
    """It knows when the pool refills and we do not."""
    import httpx

    from loopeng.agent.loop import retry_after_seconds

    response = httpx.Response(
        429, headers={"retry-after": "7"},
        request=httpx.Request("POST", "https://api.anthropic.com/"),
    )
    exc = SimpleNamespace(response=response)
    assert retry_after_seconds(exc, attempt=1) == pytest.approx(7.0)


def test_a_missing_or_junk_retry_after_falls_back_to_doubling():
    import httpx

    from loopeng.agent.loop import BACKOFF_BASE_SECONDS, retry_after_seconds

    plain = SimpleNamespace(response=httpx.Response(
        429, request=httpx.Request("POST", "https://api.anthropic.com/")))
    assert retry_after_seconds(plain, 1) == pytest.approx(BACKOFF_BASE_SECONDS)
    assert retry_after_seconds(plain, 3) == pytest.approx(BACKOFF_BASE_SECONDS * 4)

    junk = SimpleNamespace(response=httpx.Response(
        429, headers={"retry-after": "soon"},
        request=httpx.Request("POST", "https://api.anthropic.com/")))
    assert retry_after_seconds(junk, 1) == pytest.approx(BACKOFF_BASE_SECONDS)

    assert retry_after_seconds(SimpleNamespace(), 1) == pytest.approx(BACKOFF_BASE_SECONDS)


def test_the_backoff_is_capped():
    """An unbounded doubling turns a transient limit into a hung sweep."""
    from loopeng.agent.loop import BACKOFF_CEILING_SECONDS, retry_after_seconds

    assert retry_after_seconds(SimpleNamespace(), 40) == BACKOFF_CEILING_SECONDS


def test_the_level_2_loop_backs_off_too(warehouse):
    """It is the loop the sweep cells run."""
    import anthropic
    import httpx

    from loopeng.verify.loop import run_verified

    slept = []

    class Limited:
        def __init__(self):
            self.messages = SimpleNamespace(create=self._create)

        def _create(self, **kwargs):
            raise anthropic.RateLimitError(
                "Error code: 429",
                response=httpx.Response(
                    429, request=httpx.Request("POST", "https://api.anthropic.com/")),
                body=None,
            )

    run_verified("q", warehouse=warehouse, client=Limited(), max_attempts=3,
                 sleeper=slept.append)
    assert len(slept) == 2


def test_the_concurrency_flag_exists_and_defaults_to_the_measured_value():
    """The README's advice was unfollowable without editing source."""
    from pathlib import Path

    from loopeng.sweep.runner import CONCURRENCY_PER_MODEL

    entry = (Path(__file__).resolve().parent.parent
             / "demos" / "04_hill_climbing_loop" / "sweep.py").read_text(encoding="utf-8")
    assert '"--concurrency"' in entry
    assert "CONCURRENCY_PER_MODEL" in entry, "the default must be the measured value"
    assert CONCURRENCY_PER_MODEL > 0


def test_the_concurrency_reaches_the_thread_pool(warehouse, tmp_path):
    """A flag that is accepted and then ignored is worse than no flag."""
    from loopeng.sweep.runner import Cell, run_cell

    seen = {}
    import loopeng.sweep.runner as runner_module

    real = runner_module.ThreadPoolExecutor

    def spy(*args, **kwargs):
        seen["max_workers"] = kwargs.get("max_workers")
        return real(*args, **kwargs)

    runner_module.ThreadPoolExecutor = spy
    try:
        run_cell(Cell("worker", "L0", "loop"), [], warehouse,
                 directory=tmp_path, concurrency=3)
    finally:
        runner_module.ThreadPoolExecutor = real

    assert seen["max_workers"] == 3


def test_the_run_report_records_the_concurrency_used():
    """So a cell that behaved differently under a different pool size can be told apart
    from one that did not."""
    import inspect

    from loopeng.sweep.orchestrator import run_sweep

    assert "concurrency" in inspect.signature(run_sweep).parameters
