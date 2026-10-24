"""The analyst as an experiment target: (question, knowledge version) -> answer envelope.

Each call is one fresh, live run of the verification loop (the analyst, the graders, and the
reviewer when enabled) under the named knowledge version, with the live models and the spend
ledger. Nothing is kept between calls except the catalog snapshot and the connection settings.
When the experiment runner names the repetition (experiment.current_run), the run's trace carries
its knowledge version, split, item, and repetition, and its run id is the experiment's run id, so
the ledger links each row to its own trace. A run the experiment's trace sample leaves out
(RunContext.traced) runs with tracing off, all of its traces together.

`analyst` is the factory `datapilot calibrate stability --target` and the hill-climbing runner use.
"""

from __future__ import annotations

import asyncio
import contextlib
import copy
import threading
import time
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver

from datapilot import db
from datapilot.config import pack_config
from datapilot.contracts import AnswerEnvelope, AnswerStatus, KnowledgeVersion, RunEventKind
from datapilot.loop1_agent.analyst import AgentLimits
from datapilot.loop1_agent.catalog import load_snapshot
from datapilot.loop1_agent.guard import StopReason
from datapilot.loop1_agent.models import ModelFactory, openai_factory
from datapilot.loop2_verification.config import VerificationConfig
from datapilot.loop2_verification.executor import Executor
from datapilot.loop2_verification.loop import LoopServices, RunRequest, VerificationLoop
from datapilot.loop4_hill_climbing import versions
from datapilot.loop4_hill_climbing.experiment import current_run
from datapilot.observability.traces import ModelIds, development_project, development_tags
from datapilot.settings import Settings, get_settings


@dataclass
class RunStats:
    """What one run cost and did, for the calibration report."""

    run_id: str
    question: str
    knowledge_version: str
    item_id: str | None
    repetition: int | None
    status: str
    attempts: int
    tokens_in: int
    tokens_out: int
    seconds: float
    reviewer: str | None
    reviewer_reasons: list[str]
    tool_calls: list[str]
    final_sql: str | None
    reasons: list[str] = field(default_factory=list)  # why the run ended as it did
    graders_passed: bool | None = None  # the newest attempt passed every grader


@dataclass
class MemoryHooks:
    """Run hooks for a benchmark run: it is not an event-loop run, so nothing goes to ops.runs."""

    statuses: list[str] = field(default_factory=list)
    events: list[tuple[str, dict[str, Any]]] = field(default_factory=list)

    def status(self, new: Any, **payload: Any) -> None:
        self.statuses.append(str(new))

    def event(self, kind: RunEventKind, payload: dict[str, Any]) -> None:
        self.events.append((kind.value, payload))


class SharedLoop:
    """One event loop on its own thread for every run of this process. The OpenAI client keeps an
    async HTTP connection pool per process, bound to the loop that first used it, so runs from the
    experiment runner's threads must not each start and close their own loop."""

    def __init__(self) -> None:
        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self.loop.run_forever, name="runs", daemon=True).start()

    def run(self, coroutine: Any) -> Any:
        return asyncio.run_coroutine_threadsafe(coroutine, self.loop).result()


_shared: list[SharedLoop] = []
_shared_lock = threading.Lock()


def shared_loop() -> SharedLoop:
    with _shared_lock:
        if not _shared:
            _shared.append(SharedLoop())
        return _shared[0]


def _graders_passed(hooks: MemoryHooks) -> bool | None:
    """Whether the newest attempt's grader results all passed (None when no grader ran)."""
    results = [p for kind, p in hooks.events if kind == RunEventKind.GRADER_RESULT.value]
    if not results:
        return None
    newest = max(int(p.get("attempt") or 1) for p in results)
    return all(p.get("passed") for p in results if int(p.get("attempt") or 1) == newest)


def live_services(model: str, *, cfg: dict[str, Any] | None = None) -> LoopServices:
    cfg = cfg or pack_config()
    config = VerificationConfig.from_pack(cfg)
    executor = Executor(db.url_for(db.Role.AGENT), config.schema, config.statement_timeout_ms)
    return LoopServices(
        models=_models_come_per_run,
        executor=executor,
        snapshot=load_snapshot(executor.url, config.schema),
        config=config,
        limits=AgentLimits.from_pack(cfg),
        knowledge=_knowledge_comes_per_run,
        checkpointer=None,
        model_name=model,
    )


def _models_come_per_run(component: str) -> Any:
    raise RuntimeError("the target builds the models of each run")


def _knowledge_comes_per_run() -> KnowledgeVersion:
    raise RuntimeError("the target names the knowledge version of each run")


def knowledge_from_ops(name: str) -> KnowledgeVersion:
    with db.connect(db.Role.APP) as conn:
        return versions.get(conn, name)


@dataclass
class AnalystTarget:
    base: LoopServices
    settings: Settings
    knowledge: Callable[[str], KnowledgeVersion] = knowledge_from_ops
    project: str | None = None  # the LangSmith project of each run's trace
    tags: list[str] = field(default_factory=list)  # more trace tags, such as track:calibration
    model_ids: ModelIds = field(default_factory=ModelIds)
    stats: list[RunStats] = field(default_factory=list)
    pack: dict[str, Any] | None = None  # this target's own copy of pack.yaml (None: the pack's)
    # Checked before every model and tool call of each run (the hill-climbing runner passes the
    # kill switch, so an experiment's run in flight stops at its next call).
    external_stop: Callable[[], StopReason | None] | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock)

    @property
    def model(self) -> str:
        return self.settings.agent_model

    def with_agents(self, *, scout: bool, reviewer: bool) -> AnalystTarget:
        limits = replace(self.base.limits, scout_enabled=scout, reviewer_enabled=reviewer)
        return replace(self, base=replace(self.base, limits=limits), stats=[])

    def with_output_cap(self, component: str, tokens: int) -> AnalystTarget:
        """This target with one agent's max_output_tokens lowered, for the live probe of the cap;
        the pack, and every other target of the process, keep their own."""
        pack = copy.deepcopy(self.pack or pack_config())
        pack["models"][component]["max_output_tokens"] = tokens
        return replace(self, pack=pack, stats=[])

    def _models(self, run_id: str) -> ModelFactory:
        build = openai_factory(run_id=run_id, settings=self.settings, pack=self.pack)

        def models(component: str) -> Any:
            chat = build(component)
            chat.callbacks = [*(chat.callbacks or []), self.model_ids.for_component(component)]
            return chat

        return models

    def __call__(self, question: str, knowledge_version: str) -> AnswerEnvelope:
        context = current_run.get()
        run_id = str(context.run_id if context else uuid.uuid4())
        knowledge = self.knowledge(knowledge_version)
        services = replace(
            self.base,
            models=self._models(run_id),
            knowledge=lambda: knowledge,
            checkpointer=InMemorySaver(),
        )
        hooks = MemoryHooks()
        request = RunRequest(run_id=run_id, question=question)
        started = time.monotonic()
        loop = (
            VerificationLoop(services, hooks, external_stop=self.external_stop)
            if self.external_stop
            else VerificationLoop(services, hooks)
        )

        async def run() -> Any:
            # the tracing context is entered on the event loop's thread, where the run happens
            with self._tracing(knowledge_version, context):
                return await loop.start(request)

        outcome = shared_loop().run(run())
        envelope = outcome.envelope or AnswerEnvelope(
            status=AnswerStatus.ESCALATED, answer_text="; ".join(outcome.reasons)
        )
        reviews = [p for kind, p in hooks.events if kind == RunEventKind.REVIEWER_VERDICT.value]
        stats = RunStats(
            run_id=run_id,
            question=question,
            knowledge_version=knowledge_version,
            item_id=context.item.id if context else None,
            repetition=context.repetition if context else None,
            status=outcome.status.value,
            attempts=outcome.attempts,
            tokens_in=outcome.tokens_in,
            tokens_out=outcome.tokens_out,
            seconds=round(time.monotonic() - started, 2),
            reviewer=reviews[-1]["outcome"] if reviews else None,
            reviewer_reasons=list(reviews[-1].get("reasons") or []) if reviews else [],
            tool_calls=[
                str(p.get("tool"))
                for kind, p in hooks.events
                if kind == RunEventKind.TOOL_CALL_FINISHED.value
            ],
            final_sql=envelope.final_sql,
            reasons=list(outcome.reasons),
            graders_passed=_graders_passed(hooks),
        )
        with self._lock:
            self.stats.append(stats)
        return envelope

    def _tracing(self, knowledge_version: str, context: Any) -> Any:
        from langsmith.run_helpers import tracing_context

        if context is not None and not context.traced:
            # the experiment's trace sample left this run out: none of its traces is sent
            return tracing_context(enabled=False)
        if not self.project:
            return contextlib.nullcontext()

        tags = [*self.tags, f"knowledge_version:{knowledge_version}", f"model:{self.model}"]
        metadata: dict[str, Any] = {"knowledge_version": knowledge_version}
        if context is not None:
            tags += [
                f"split:{context.item.split.value}",
                f"item_id:{context.item.id}",
                f"repetition:{context.repetition}",
            ]
            metadata |= {
                "split": context.item.split.value,
                "item_id": context.item.id,
                "repetition": context.repetition,
            }
        return tracing_context(project_name=self.project, tags=tags, metadata=metadata)


def analyst(*, project: str | None = None, tags: Sequence[str] = ()) -> AnalystTarget:
    """The live analyst target on the class model (OPENAI_MODEL)."""
    settings = get_settings()
    return AnalystTarget(
        base=live_services(settings.agent_model),
        settings=settings,
        project=project or settings.langsmith_experiments_project,
        tags=list(tags),
    )


def development_analyst() -> AnalystTarget:
    """The analyst for a live development run (calibration): traced to datapilot-development with
    the track and feature tags from the environment."""
    return analyst(
        project=development_project(), tags=development_tags("calibration", "calibration")
    )
