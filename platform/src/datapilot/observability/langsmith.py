"""LangSmith: the benchmark dataset sync and a base-tier trace for an experiment run.

Experiments are scored locally and never uploaded as LangSmith experiments (no evaluate() with
uploads, no comparison view). A traced run becomes an ordinary trace in the experiments project,
tagged with knowledge version, split, item, and repetition; the runner traces only the sample of
benchmark runs the pack names (observability.sampling) and never calls a tracer for the others.
The class wiring uses traces.FeedbackTracer on the analyst's own trace. Feedback always passes
extend_trace_retention=False. The client is injected, so tests use a stand-in and nothing here
opens a connection on import.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

from datapilot.contracts import BenchmarkItem
from datapilot.loop4_hill_climbing.experiment import RunRecord

DATASET = "datapilot-benchmark"


class Client(Protocol):
    """The subset of langsmith.Client used here."""

    def has_dataset(self, *, dataset_name: str) -> bool: ...
    def create_dataset(self, dataset_name: str, **kwargs: Any) -> Any: ...
    def read_dataset(self, *, dataset_name: str) -> Any: ...
    def list_examples(self, *, dataset_id: Any) -> Any: ...
    def create_examples(self, *, dataset_id: Any, examples: list[dict[str, Any]]) -> Any: ...
    def update_examples(self, *, dataset_id: Any, updates: list[dict[str, Any]]) -> Any: ...
    def create_run(
        self, name: str, inputs: dict[str, Any], run_type: str, **kwargs: Any
    ) -> None: ...
    def create_feedback(self, run_id: Any, key: str, **kwargs: Any) -> Any: ...


def example_for(item: BenchmarkItem) -> dict[str, Any]:
    """One dataset example: the question in, the gold SQL and status out, the item in metadata."""
    return {
        "inputs": {"question": item.question},
        "outputs": {"gold_sql": item.gold_sql, "expected_status": item.expected_status.value},
        "metadata": {
            "item_id": item.id,
            "split": item.split.value,
            "category": item.category.value,
            "metric_family": item.metric_family,
            "traps": list(item.traps),
            "order_matters": item.order_matters,
            "numeric_tolerance": item.numeric_tolerance,
        },
    }


@dataclass(frozen=True)
class SyncReport:
    created: int
    updated: int
    unchanged: int


def sync_benchmark(
    client: Client, items: Sequence[BenchmarkItem], dataset_name: str = DATASET
) -> SyncReport:
    """Make the LangSmith dataset equal to the benchmark YAML, keyed by item id."""
    if client.has_dataset(dataset_name=dataset_name):
        dataset = client.read_dataset(dataset_name=dataset_name)
    else:
        dataset = client.create_dataset(
            dataset_name, description="DataPilot benchmark, synced from the pack's YAML."
        )
    existing = {
        (ex.metadata or {}).get("item_id"): ex for ex in client.list_examples(dataset_id=dataset.id)
    }
    new, updates, unchanged = [], [], 0
    for item in items:
        wanted = example_for(item)
        current = existing.get(item.id)
        if current is None:
            new.append(wanted)
        elif (current.inputs, current.outputs, current.metadata) != (
            wanted["inputs"],
            wanted["outputs"],
            wanted["metadata"],
        ):
            updates.append({"id": current.id, **wanted})
        else:
            unchanged += 1
    if new:
        client.create_examples(dataset_id=dataset.id, examples=new)
    if updates:
        client.update_examples(dataset_id=dataset.id, updates=updates)
    return SyncReport(created=len(new), updated=len(updates), unchanged=unchanged)


@dataclass
class ExperimentTracer:
    """Implements loop4_hill_climbing.experiment.RunTracer with base-tier traces. Returns the run
    id; the console turns it into a link."""

    client: Client
    project: str

    def trace(self, record: RunRecord, *, experiment_id: UUID) -> str | None:
        run_id = uuid.uuid4()
        tags = [
            f"knowledge_version:{record.knowledge_version}",
            f"split:{record.item.split.value}",
            f"item_id:{record.item.id}",
            f"repetition:{record.repetition}",
        ]
        metadata = {
            "experiment_id": str(experiment_id),
            "knowledge_version": record.knowledge_version,
            "split": record.item.split.value,
            "item_id": record.item.id,
            "repetition": record.repetition,
            "passed": record.result.passed,
        }
        self.client.create_run(
            "benchmark-item",
            {"question": record.item.question, "knowledge_version": record.knowledge_version},
            "chain",
            id=run_id,
            project_name=self.project,
            outputs={
                "answer": record.answer.model_dump(mode="json") if record.answer else None,
                "passed": record.result.passed,
                "reason": record.result.reason,
            },
            start_time=record.started_at,
            end_time=record.finished_at,
            tags=tags,
            extra={"metadata": metadata},
        )
        self.client.create_feedback(
            run_id,
            "execution_match",
            score=int(record.result.passed),
            comment=record.result.reason,
            extend_trace_retention=False,
        )
        return str(run_id)
