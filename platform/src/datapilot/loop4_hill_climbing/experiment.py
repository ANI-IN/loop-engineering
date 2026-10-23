"""The experiment runner: run the benchmark against one knowledge version and score it locally.

The target is any callable that answers a question under a knowledge version (the analyst, in
class). Every repetition is a fresh call, scored here first: the source of truth. While it runs,
`current_run` names its run id, item, repetition, and whether the trace sample takes it (the pack's
tracing.experiment_sample_rate), so the target tags its trace or turns tracing off. Each item's
result goes to the sink as its runs finish, so the console's holdout ledger fills in live.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable, Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from datapilot.contracts import AnswerEnvelope, BenchmarkItem, Evaluator, ItemResult, Split
from datapilot.loop4_hill_climbing.measurement import Scheme

Target = Callable[[str, str], AnswerEnvelope]  # (question, knowledge version) -> answer


@dataclass(frozen=True)
class RunContext:
    """What the target may read about the repetition it is answering."""

    run_id: UUID
    item: BenchmarkItem
    repetition: int
    knowledge_version: str
    traced: bool = True  # False: the trace sample left this benchmark run out


current_run: ContextVar[RunContext | None] = ContextVar("current_run", default=None)


@dataclass(frozen=True)
class RunRecord:
    """One repetition of one item."""

    item: BenchmarkItem
    repetition: int
    knowledge_version: str
    answer: AnswerEnvelope | None
    result: ItemResult
    started_at: datetime
    finished_at: datetime
    run_id: UUID = field(default_factory=uuid.uuid4)


class RunTracer(Protocol):
    def trace(self, record: RunRecord, *, experiment_id: UUID) -> str | None:
        """Record one run; return its trace id or link."""
        ...


@dataclass
class Confirmation:
    """The re-run that confirms or clears one apparent regression, shown as a ledger step."""

    item_id: str
    split: Split
    reruns: list[bool] = field(default_factory=list)
    confirmed: bool | None = None  # None while the re-runs are still going
    steps: list[str] = field(default_factory=list)
    planned: int = 0  # how many re-runs the scheme asks for

    @property
    def state(self) -> str:
        if self.confirmed is None:
            return "confirming"
        return "confirmed" if self.confirmed else "cleared"

    def as_dict(self) -> dict[str, object]:
        return {
            "split": self.split.value,
            "reruns": self.reruns,
            "confirmed": self.confirmed,
            "steps": self.steps,
            # the three fields the console ledger reads
            "state": self.state,
            "runs": self.planned or len(self.reruns),
            "failures": self.reruns.count(False),
        }


@dataclass
class ExperimentResult:
    experiment_id: UUID
    session_id: UUID
    knowledge_version: str
    splits: list[Split]
    results: dict[str, ItemResult]
    splits_by_item: dict[str, Split]
    started_at: datetime
    wall_seconds: float
    trace_links: dict[str, list[str]] = field(default_factory=dict)
    tracer_errors: list[str] = field(default_factory=list)
    untraced_runs: dict[str, int] = field(default_factory=dict)  # item id -> runs left untraced
    confirmations: dict[str, Confirmation] = field(default_factory=dict)
    final_sql: dict[str, str] = field(default_factory=dict)  # item id -> SQL of its deciding run

    def passes(self, split: Split) -> int:
        return sum(
            1
            for item_id, r in self.results.items()
            if self.splits_by_item[item_id] is split and r.passed
        )

    def total(self, split: Split) -> int:
        return sum(1 for s in self.splits_by_item.values() if s is split)

    def passed(self, item_id: str) -> bool:
        return self.results[item_id].passed


class ItemSink(Protocol):
    """Where an experiment's progress goes while it runs (ops.experiments, for the console)."""

    def started(self, experiment: ExperimentResult) -> None: ...

    def item_done(self, experiment: ExperimentResult, item_id: str) -> None: ...


@dataclass
class ExperimentRunner:
    target: Target
    evaluator: Evaluator
    scheme: Scheme = field(default_factory=Scheme.from_pack)
    concurrency: int = 8
    tracer: RunTracer | None = None
    sink: ItemSink | None = None
    trace_sample_rate: float = field(default_factory=lambda: _packs_sample_rate())

    def run_once(self, item: BenchmarkItem, knowledge_version: str, repetition: int) -> RunRecord:
        run_id = uuid.uuid4()
        token = current_run.set(self._context(run_id, item, repetition, knowledge_version))
        started = datetime.now(UTC)
        answer: AnswerEnvelope | None = None
        try:
            answer = self.target(item.question, knowledge_version)
            result = self.evaluator.evaluate(item, answer)
        except Exception as error:  # one failed run is a failed item, never a failed experiment
            reason = f"run failed: {type(error).__name__}: {str(error)[:200]}"
            result = ItemResult(item_id=item.id, passed=False, reason=reason)
        finally:
            current_run.reset(token)
        finished = datetime.now(UTC)
        return RunRecord(
            item, repetition, knowledge_version, answer, result, started, finished, run_id
        )

    def run(
        self,
        items: Sequence[BenchmarkItem],
        knowledge_version: str,
        *,
        session_id: UUID,
        splits: Iterable[Split] = (Split.DEV, Split.HOLDOUT),
    ) -> ExperimentResult:
        chosen = list(splits)
        selected = [i for i in items if i.split in chosen]
        clock = time.monotonic()
        experiment = ExperimentResult(
            experiment_id=uuid.uuid4(),
            session_id=session_id,
            knowledge_version=knowledge_version,
            splits=chosen,
            results={},
            splits_by_item={item.id: item.split for item in selected},
            started_at=datetime.now(UTC),
            wall_seconds=0.0,
        )
        if self.sink:
            self.sink.started(experiment)
        # Items run concurrently; one item's repetitions run one after another, so its run passes
        # are in repetition order however long each run takes.
        with ThreadPoolExecutor(max_workers=self.concurrency) as pool:
            futures = [pool.submit(self._run_item, item, knowledge_version) for item in selected]
            for future in as_completed(futures):
                mine = future.result()
                self._finish_item(experiment, mine[0].item, mine)
        experiment.results = {item.id: experiment.results[item.id] for item in selected}
        experiment.wall_seconds = time.monotonic() - clock
        return experiment

    def _run_item(self, item: BenchmarkItem, knowledge_version: str) -> list[RunRecord]:
        repeats = self.scheme.repeats(item.split)
        return [self.run_once(item, knowledge_version, n) for n in range(1, repeats + 1)]

    def rerun(self, item: BenchmarkItem, knowledge_version: str, times: int) -> list[bool]:
        return [self.run_once(item, knowledge_version, n).result.passed for n in range(times)]

    def _finish_item(
        self, experiment: ExperimentResult, item: BenchmarkItem, mine: list[RunRecord]
    ) -> None:
        for record in mine:
            self._trace(experiment, record)
        mine.sort(key=lambda r: r.repetition)
        experiment.results[item.id] = self._aggregate(item, mine)
        deciding = next((r for r in mine if not r.result.passed), mine[0])
        if deciding.answer is not None and deciding.answer.final_sql:
            experiment.final_sql[item.id] = deciding.answer.final_sql
        if self.sink:
            self.sink.item_done(experiment, item.id)

    def _aggregate(self, item: BenchmarkItem, mine: list[RunRecord]) -> ItemResult:
        run_passes = [r.result.passed for r in mine]
        passed = self.scheme.passes(item.split, run_passes)
        failed = [r.result for r in mine if not r.result.passed]
        reason = failed[0].reason if failed and not passed else mine[0].result.reason
        if len(mine) > 1:
            reason = f"passed {sum(run_passes)} of {len(mine)} runs; {reason}"
        labels = sorted({label for r in mine for label in r.result.trap_labels})
        return ItemResult(
            item_id=item.id, passed=passed, reason=reason, trap_labels=labels, run_passes=run_passes
        )

    # --- the per-run tracing hook ----------------------------------------------------------------
    def traced(self, run_id: UUID) -> bool:
        """Whether the trace sample takes this run: LangSmith's own sampling rule on the run id, at
        trace_sample_rate (observability.sampling). A run left out is not traced at all, and keeps
        its local result like every other."""
        from datapilot.observability.sampling import sampled_in

        return sampled_in(run_id, self.trace_sample_rate)

    def _context(
        self, run_id: UUID, item: BenchmarkItem, repetition: int, knowledge_version: str
    ) -> RunContext:
        return RunContext(run_id, item, repetition, knowledge_version, self.traced(run_id))

    def _trace(self, experiment: ExperimentResult, record: RunRecord) -> None:
        """A tracer, when given, links each traced run to its trace; a tracer failure never changes
        a result. A run the sample left out is counted, so the ledger can say it was not traced."""
        if not self.traced(record.run_id):
            untraced = experiment.untraced_runs
            untraced[record.item.id] = untraced.get(record.item.id, 0) + 1
            return
        if self.tracer is None:
            return
        try:
            link = self.tracer.trace(record, experiment_id=experiment.experiment_id)
        except Exception as error:  # tracing is the linked record, not the result
            experiment.tracer_errors.append(f"{record.item.id}: {type(error).__name__}")
            return
        if link:
            experiment.trace_links.setdefault(record.item.id, []).append(link)


def _packs_sample_rate() -> float:
    from datapilot.observability.sampling import experiment_sample_rate

    return experiment_sample_rate()
