"""Dataset sync from the benchmark YAML and base-tier run traces, against a stand-in client."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from loop4_doubles import answered, item

from datapilot.contracts import ItemResult, Split
from datapilot.loop4_hill_climbing.experiment import RunRecord
from datapilot.loop4_hill_climbing.pack_files import load_benchmark
from datapilot.observability.langsmith import ExperimentTracer, example_for, sync_benchmark


class ClientDouble:
    def __init__(self, examples: list | None = None) -> None:
        self.examples = examples
        self.calls: list[tuple[str, tuple, dict]] = []

    def _log(self, name: str, *args, **kwargs):
        self.calls.append((name, args, kwargs))

    def has_dataset(self, *, dataset_name):
        return self.examples is not None

    def create_dataset(self, dataset_name, **kwargs):
        self._log("create_dataset", dataset_name)
        return SimpleNamespace(id="ds-1")

    def read_dataset(self, *, dataset_name):
        return SimpleNamespace(id="ds-1")

    def list_examples(self, *, dataset_id):
        return self.examples or []

    def create_examples(self, *, dataset_id, examples):
        self._log("create_examples", examples=examples)

    def update_examples(self, *, dataset_id, updates):
        self._log("update_examples", updates=updates)

    def create_run(self, name, inputs, run_type, **kwargs):
        self._log("create_run", name, inputs, run_type, **kwargs)

    def create_feedback(self, run_id, key, **kwargs):
        self._log("create_feedback", run_id, key, **kwargs)


def test_a_new_dataset_gets_every_item_as_inputs_and_outputs() -> None:
    client = ClientDouble()
    items = load_benchmark()  # its size is test_benchmark.py's to pin, which Assignment 4 updates
    report = sync_benchmark(client, items)
    assert report.created == len(items) and report.updated == 0
    examples = client.calls[-1][2]["examples"]
    assert len(examples) == len(items)
    assert set(examples[0]) == {"inputs", "outputs", "metadata"}
    assert "reference_outputs" not in examples[0]


def test_sync_updates_only_changed_items() -> None:
    items = [item("q1"), item("q2")]
    stale = SimpleNamespace(id="ex-2", **{**example_for(items[1]), "outputs": {"gold_sql": "old"}})
    same = SimpleNamespace(id="ex-1", **example_for(items[0]))
    client = ClientDouble([same, stale])
    report = sync_benchmark(client, items)
    assert (report.created, report.updated, report.unchanged) == (0, 1, 1)
    assert client.calls[-1][2]["updates"][0]["id"] == "ex-2"


def test_each_run_is_a_tagged_base_tier_trace_with_feedback_retention_off() -> None:
    client = ClientDouble()
    now = datetime.now(UTC)
    record = RunRecord(
        item("h1", Split.HOLDOUT),
        2,
        "v1",
        answered("SELECT 1"),
        ItemResult(item_id="h1", passed=False, reason="row 1 differs"),
        now,
        now,
    )
    run_id = ExperimentTracer(client, "datapilot-experiments").trace(record, experiment_id=uuid4())
    (_, run_args, run_kwargs), (_, feedback_args, feedback_kwargs) = client.calls
    assert run_kwargs["project_name"] == "datapilot-experiments"
    assert run_kwargs["tags"] == [
        "knowledge_version:v1",
        "split:holdout",
        "item_id:h1",
        "repetition:2",
    ]
    assert run_kwargs["extra"]["metadata"]["repetition"] == 2
    assert "reference_example_id" not in run_kwargs
    assert feedback_kwargs["extend_trace_retention"] is False
    assert str(feedback_args[0]) == run_id
