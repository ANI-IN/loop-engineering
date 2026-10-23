"""Benchmark runs inside experiments are traced as a sample (the owner's decision of 23 October
2026): the pack names the rate, each run is decided by LangSmith's own sampling rule on its run id,
and a run left out keeps its local result and says plainly that it was not traced. Demo runs and
assignment check runs outside the benchmark stay fully traced."""

from __future__ import annotations

import sys
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from loop4_doubles import SESSION, ScriptedEvaluator, answered, experiment, item

from datapilot.config import pack_config
from datapilot.contracts import Split
from datapilot.loop4_hill_climbing.experiment import ExperimentRunner, RunContext, current_run
from datapilot.loop4_hill_climbing.measurement import Scheme
from datapilot.observability import sampling
from datapilot.settings import PLATFORM

SCHEME = Scheme(holdout_repeats=3, holdout_pass_threshold=2, dev_regression_reruns=2)
CONSOLE = PLATFORM / "console"
if str(CONSOLE) not in sys.path:
    sys.path.insert(0, str(CONSOLE))


# --- the rate and the rule ----------------------------------------------------------------------


def test_the_pack_names_a_sample_rate_below_one() -> None:
    rate = sampling.experiment_sample_rate()
    assert rate == pack_config()["tracing"]["experiment_sample_rate"]
    assert 0 < rate < 1


def test_a_pack_without_a_tracing_block_traces_every_run() -> None:
    assert sampling.experiment_sample_rate({"name": "a pack of a learner's own"}) == 1.0


def test_a_rate_outside_zero_to_one_is_refused() -> None:
    with pytest.raises(ValueError, match="between 0 and 1"):
        sampling.experiment_sample_rate({"tracing": {"experiment_sample_rate": 1.5}})


def test_the_decision_is_langsmiths_own_sampling_rule() -> None:
    from langsmith import Client

    rate = 0.2
    client = Client(api_key="test-key", api_url="http://127.0.0.1:9", tracing_sampling_rate=rate)
    ids = [uuid.uuid4() for _ in range(2000)]
    ours = [sampling.sampled_in(i, rate) for i in ids]
    assert ours == [client._should_sample(str(i)) for i in ids]
    assert 0.15 < sum(ours) / len(ids) < 0.25
    assert all(sampling.sampled_in(i, 1.0) for i in ids[:50])
    assert not any(sampling.sampled_in(i, 0.0) for i in ids[:50])


def test_the_note_says_how_many_runs_are_traced() -> None:
    assert sampling.sample_note(0.2) == "Experiment runs are traced as a sample: about 1 run in 5."
    assert sampling.sample_note(0.0) == "Experiment runs are not traced."
    assert sampling.sample_note(1.0) == ""


# --- the experiment runner ----------------------------------------------------------------------


class _Tracer:
    def __init__(self) -> None:
        self.records: list = []

    def trace(self, record, *, experiment_id):
        self.records.append(record)
        return f"https://smith.example/r/{record.run_id}"


def _seeing(seen: list[RunContext]):
    def target(question: str, version: str):
        context = current_run.get()
        assert context is not None
        seen.append(context)
        return answered("SELECT 1")

    return target


def _items():
    return [item(f"d{n}") for n in range(30)] + [item(f"h{n}", Split.HOLDOUT) for n in range(10)]


def test_the_runner_traces_only_the_runs_the_sample_takes() -> None:
    seen: list[RunContext] = []
    tracer = _Tracer()
    items = _items()
    runner = ExperimentRunner(
        _seeing(seen),
        ScriptedEvaluator({i.id: [True] * 3 for i in items}),
        SCHEME,
        tracer=tracer,
        trace_sample_rate=0.5,
    )
    result = runner.run(items, "v1", session_id=SESSION)
    assert len(seen) == 60
    traced = {c.run_id for c in seen if c.traced}
    assert traced == {c.run_id for c in seen if sampling.sampled_in(c.run_id, 0.5)}
    assert 0 < len(traced) < 60
    assert {r.run_id for r in tracer.records} == traced, "feedback and links only where traced"
    assert all(result.passed(i.id) for i in items), "every run keeps its local result"
    assert sum(len(v) for v in result.trace_links.values()) == len(traced)
    assert sum(result.untraced_runs.values()) == 60 - len(traced)


def test_at_rate_zero_no_run_is_traced_and_every_result_stands() -> None:
    seen: list[RunContext] = []
    tracer = _Tracer()
    items = [item("d1"), item("h1", Split.HOLDOUT)]
    runner = ExperimentRunner(
        _seeing(seen),
        ScriptedEvaluator({"d1": [True], "h1": [True, False, True]}),
        SCHEME,
        tracer=tracer,
        trace_sample_rate=0.0,
    )
    result = runner.run(items, "v1", session_id=SESSION)
    assert not any(c.traced for c in seen) and tracer.records == []
    assert result.passed("d1") and result.results["h1"].run_passes == [True, False, True]
    assert result.trace_links == {} and result.untraced_runs == {"d1": 1, "h1": 3}


def test_at_rate_one_every_run_is_traced() -> None:
    seen: list[RunContext] = []
    tracer = _Tracer()
    items = [item("d1"), item("h1", Split.HOLDOUT)]
    runner = ExperimentRunner(
        _seeing(seen),
        ScriptedEvaluator({"d1": [True], "h1": [True] * 3}),
        SCHEME,
        tracer=tracer,
        trace_sample_rate=1.0,
    )
    result = runner.run(items, "v1", session_id=SESSION)
    assert all(c.traced for c in seen) and len(tracer.records) == 4
    assert result.untraced_runs == {}


def test_the_default_rate_is_the_packs() -> None:
    runner = ExperimentRunner(_seeing([]), ScriptedEvaluator({}), SCHEME)
    assert runner.trace_sample_rate == sampling.experiment_sample_rate()


def test_reruns_are_benchmark_runs_and_are_sampled_too() -> None:
    seen: list[RunContext] = []
    runner = ExperimentRunner(
        _seeing(seen), ScriptedEvaluator({"h1": [True] * 4}), SCHEME, trace_sample_rate=0.0
    )
    assert runner.rerun(item("h1", Split.HOLDOUT), "v2", 4) == [True] * 4
    assert len(seen) == 4 and not any(c.traced for c in seen)


# --- the analyst target -------------------------------------------------------------------------


def _target():
    from datapilot.loop4_hill_climbing.targets import AnalystTarget

    return AnalystTarget(
        base=None,  # type: ignore[arg-type]
        settings=SimpleNamespace(agent_model="gpt-6-luna"),  # type: ignore[arg-type]
        project="datapilot-experiments",
    )


def _context(traced: bool) -> RunContext:
    return RunContext(uuid.uuid4(), item("h1", Split.HOLDOUT), 1, "v1", traced=traced)


def test_a_run_left_out_of_the_sample_is_not_traced_at_all() -> None:
    from langsmith.run_helpers import get_tracing_context

    with _target()._tracing("v1", _context(traced=False)):
        assert get_tracing_context()["enabled"] is False


def test_a_sampled_run_and_a_demo_run_are_traced_to_their_project() -> None:
    from langsmith.run_helpers import get_tracing_context

    with _target()._tracing("v1", _context(traced=True)):
        found = get_tracing_context()
        assert found["enabled"] is not False and found["project_name"] == "datapilot-experiments"
        assert "item_id:h1" in found["tags"] and "repetition:1" in found["tags"]
    with _target()._tracing("v1", None):  # a run outside any experiment
        found = get_tracing_context()
        assert found["enabled"] is not False and found["project_name"] == "datapilot-experiments"


# --- the record and the console -----------------------------------------------------------------


def test_the_experiment_record_says_how_many_runs_were_not_traced() -> None:
    from datapilot.loop4_hill_climbing.store import example_entry

    result = experiment("v1", {"h1": True, "h2": True}, {"h1": Split.HOLDOUT, "h2": Split.HOLDOUT})
    result.untraced_runs = {"h1": 3}
    result.trace_links = {"h2": ["https://smith.example/r/1"]}
    assert example_entry(result, "h1")["runs_not_traced"] == 3
    assert example_entry(result, "h1")["trace_urls"] == []
    assert "runs_not_traced" not in example_entry(result, "h2")


def test_a_ledger_row_whose_runs_were_all_left_out_says_not_traced() -> None:
    from datapilot_console import views

    def holdout(item_id: str, **extra):
        return {"item_id": item_id, "split": "holdout", "run_passes": [True] * 3, **extra}

    baseline = {
        "experiment_id": uuid.uuid4(),
        "knowledge_version": "v1",
        "version_status": "active",
        "per_example": [
            holdout("a", trace_urls=[], runs_not_traced=3),
            holdout("b", trace_urls=["https://smith.example/r/b"], runs_not_traced=2),
        ],
        "langsmith_url": "https://smith.example/list?version=v1",
        "started_at": datetime(2026, 10, 23, tzinfo=UTC),
    }
    ledger = views.ledger_view(
        [("a", "A?"), ("b", "B?"), ("c", "C?")],
        baseline=baseline,
        candidate=None,
        session_id=SESSION,
        display_tz=None,
        repeats=3,
        pass_threshold=2,
        sample_rate=0.2,
    )
    rows = {r["item"]: r for r in ledger["rows"]}
    assert rows["a"]["trace_url"] is None and rows["a"]["not_traced"] is True
    assert rows["b"]["trace_url"] == "https://smith.example/r/b" and not rows["b"]["not_traced"]
    assert rows["c"]["trace_url"] is None and not rows["c"]["not_traced"], "not run yet"
    assert ledger["trace_sample_note"] == sampling.sample_note(0.2)


def test_the_ledger_component_shows_the_not_traced_state_in_words() -> None:
    js = (CONSOLE / "datapilot_console" / "components" / "holdout_ledger.js").read_text("utf-8")
    assert "r.not_traced" in js and "'Not traced'" in js
    assert sampling.NOT_TRACED in js
    assert "data.trace_sample_note" in js
