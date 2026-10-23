"""The domain pack interface: everything DataPilot needs to know about one warehouse."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from datapilot.contracts.evaluation import BenchmarkItem, Evaluator
from datapilot.contracts.grading import Grader
from datapilot.contracts.knowledge import KnowledgeStore


@runtime_checkable
class Tool(Protocol):
    name: str
    description: str

    def invoke(self, **kwargs: Any) -> Any: ...


class DataGenerator(Protocol):
    def generate(self, out_dir: Path, *, seed: int) -> dict[str, int]:
        """Write the seed files; return row counts per table."""
        ...

    def content_hash(self, out_dir: Path) -> str: ...


class EventSource(Protocol):
    """Anything that produces events for the api: a webhook client, the scheduler, the console."""

    name: str

    def events(self) -> Sequence[dict[str, Any]]: ...


@runtime_checkable
class DomainPack(Protocol):
    name: str
    root: Path

    def config(self) -> dict[str, Any]:
        """The parsed pack.yaml."""
        ...

    def tools(self) -> Sequence[Tool]: ...

    def graders(self) -> Sequence[Grader]: ...

    def evaluator(self) -> Evaluator: ...

    def knowledge_store(self) -> KnowledgeStore: ...

    def load_benchmark(self) -> Sequence[BenchmarkItem]: ...

    def data_generator(self) -> DataGenerator: ...
