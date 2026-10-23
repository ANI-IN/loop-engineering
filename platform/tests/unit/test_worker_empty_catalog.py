"""A worker started before the warehouse was seeded reads the catalog again, instead of keeping an
empty one until it restarts (found by the fresh-install review of 23 October: make up runs before
make seed, and the first demo answered that no warehouse tables were available)."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any

from datapilot.loop1_agent.catalog import CatalogSnapshot
from datapilot.loop3_events import worker as worker_module


@dataclass
class Base:
    snapshot: CatalogSnapshot
    executor: Any = field(default_factory=lambda: SimpleNamespace(url="postgresql://agent"))
    config: Any = field(default_factory=lambda: SimpleNamespace(schema="warehouse"))


def _worker(snapshot: CatalogSnapshot) -> worker_module.Worker:
    worker = worker_module.Worker.__new__(worker_module.Worker)
    worker.base = Base(snapshot=snapshot)  # type: ignore[assignment]
    return worker


def test_an_empty_catalog_is_read_again(monkeypatch) -> None:
    seeded = CatalogSnapshot(schema="warehouse", tables={"orders": object()})  # type: ignore[dict-item]
    calls: list[tuple[str, str]] = []

    def load(url: str, schema: str) -> CatalogSnapshot:
        calls.append((url, schema))
        return seeded

    monkeypatch.setattr(worker_module, "load_snapshot", load)
    worker = _worker(CatalogSnapshot(schema="warehouse"))
    worker._refresh_empty_snapshot()
    assert calls == [("postgresql://agent", "warehouse")]
    assert worker.base.snapshot is seeded


def test_a_catalog_with_tables_is_kept(monkeypatch) -> None:
    def load(url: str, schema: str) -> CatalogSnapshot:
        raise AssertionError("a catalog with tables must not be read again")

    monkeypatch.setattr(worker_module, "load_snapshot", load)
    held = CatalogSnapshot(schema="warehouse", tables={"orders": object()})  # type: ignore[dict-item]
    worker = _worker(held)
    worker._refresh_empty_snapshot()
    assert worker.base.snapshot is held
