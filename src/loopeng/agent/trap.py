"""The trap: every gold question, both models, one shot each.

**Scoring is separated from execution, and that separation is the demo.** Each cell is
judged the moment its result lands, and the judgement is held in `TrapState` unrevealed
until someone asks for it. Pressing reveal flips a flag; it does not re-run anything.
Re-running to score would burn the whole wall-clock again and lose the room, so a test
asserts reveal triggers zero model calls.

**The axis is the SPEC, not the model.** The default arms are the same model at two
prompt levels — Haiku at L3 and Haiku at L0 — so the only thing that differs between
columns is whether the business rules were written down.

Running Haiku against Sonnet instead would teach "buy the bigger model", which is the
opposite of this workshop's thesis and would have to be argued against later. Same
model, two spec levels, makes the spec the variable.

The L3 column is not decoration: it is the baseline that makes L0 legible. L0 on its
own is a wall of red that teaches nothing, because a reader has no way to tell how much
of it is the missing spec and how much is the task simply being hard.

Concurrency is capped well below the measured ceilings in `results/gate0.json` (10,000
requests/minute per model). The cap exists to be polite and predictable, not because
the limit is near.
"""

import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

import structlog

from loopeng.agent.classify import Judgement, Outcome, judge, summarise
from loopeng.agent.loop import AgentRun, run_question
from loopeng.gold.build import GoldItem
from loopeng.metric import Metric
from loopeng.usage import UsageLedger, merge

log = structlog.get_logger(__name__)

# Far below the measured 10,000 requests/minute per model. Pools are per-model, so
# each model gets its own slots rather than sharing one budget.
CONCURRENCY_PER_MODEL = 8

# (role, level). The spec level is the variable; the model is held constant.
ARMS: tuple[tuple[str, str], ...] = (("worker", "L3"), ("worker", "L0"))

ARM_LABELS = {
    ("worker", "L3"): "Haiku · rules given (L3)",
    ("worker", "L0"): "Haiku · rules withheld (L0)",
    ("frontier", "L3"): "Sonnet · rules given (L3)",
    ("frontier", "L0"): "Sonnet · rules withheld (L0)",
}


def arm_key(role: str, level: str) -> str:
    return f"{role}@{level}"


def arm_label(role: str, level: str) -> str:
    return ARM_LABELS.get((role, level), arm_key(role, level))


@dataclass
class Cell:
    """One question against one model. Judged on arrival, revealed later."""

    item_id: str
    role: str
    model_id: str
    question: str
    level: str = "L3"
    run: AgentRun | None = None
    judgement: Judgement | None = None
    seconds: float = 0.0

    @property
    def done(self) -> bool:
        return self.run is not None

    @property
    def arm(self) -> str:
        return arm_key(self.role, self.level)


@dataclass
class TrapState:
    """Everything the trap knows. `revealed` is the only thing the button changes."""

    cells: dict[tuple[str, str], Cell] = field(default_factory=dict)
    revealed: bool = False
    started_at: float = 0.0
    finished_at: float = 0.0

    arms: tuple[tuple[str, str], ...] = ARMS

    def put(self, cell: Cell) -> None:
        self.cells[(cell.item_id, cell.arm)] = cell

    @property
    def wall_clock_seconds(self) -> float:
        end = self.finished_at or time.perf_counter()
        return end - self.started_at if self.started_at else 0.0

    def ledger(self) -> UsageLedger:
        return merge(cell.run.ledger for cell in self.cells.values() if cell.run)

    def judgements(self, arm: str | None = None) -> list[Judgement]:
        return [
            cell.judgement
            for cell in self.cells.values()
            if cell.judgement and (arm is None or cell.arm == arm)
        ]

    def correct_by_item(self, arm: str) -> dict[str, bool]:
        """{item_id: was_correct} for the paired comparison. Only cells that ran."""
        from loopeng.agent.classify import Outcome

        return {
            cell.item_id: cell.judgement.outcome is Outcome.CORRECT
            for cell in self.cells.values()
            if cell.arm == arm and cell.judgement and cell.judgement.ran_and_returned
        }

    def paired_comparison(self, arm_a: str, arm_b: str):
        """McNemar over the items both arms answered. See loopeng.paired."""
        from loopeng.paired import compare

        return compare(
            self.correct_by_item(arm_a),
            self.correct_by_item(arm_b),
            label_a=arm_a,
            label_b=arm_b,
        )

    def reveal(self) -> None:
        """A state flip. Deliberately does nothing else."""
        self.revealed = True

    def silent_error_rate(self, arm: str) -> Metric | None:
        """Over answers that RAN AND RETURNED. Never over all attempts.

        Returns None rather than a zero when nothing has landed yet — a rate with no
        observations is not a rate, and rendering it as 0% would be a claim.
        """
        judgements = [j for j in self.judgements(arm) if j.ran_and_returned]
        if not judgements:
            return None
        silent = sum(1 for j in judgements if j.outcome is Outcome.SILENT_ERROR)
        return Metric.from_counts(successes=silent, n=len(judgements))

    def summary(self, arm: str) -> dict:
        return summarise(self.judgements(arm))


def run_trap(
    items: list[GoldItem],
    warehouse: Path,
    *,
    arms: tuple[tuple[str, str], ...] = ARMS,
    max_attempts: int = 1,
    budget_usd: float = 0.10,
    client=None,
    on_cell: Callable[[Cell], None] | None = None,
    state: TrapState | None = None,
) -> TrapState:
    """Run every item against every role, streaming cells back as they land.

    `max_attempts=1` by default: the trap is one-shot on purpose. Level 1's retry is
    demonstrated by run.py on a single question, where the attempt timeline is
    legible; here the point is what a single confident answer looks like.
    """
    state = state or TrapState(arms=arms)
    state.arms = arms
    state.started_at = time.perf_counter()

    by_item = {item.item_id: item for item in items}
    jobs = [(item, role, level) for role, level in arms for item in items]

    def _one(item: GoldItem, role: str, level: str) -> Cell:
        started = time.perf_counter()
        run = run_question(
            item.question,
            warehouse=warehouse,
            role=role,
            level=level,
            max_attempts=max_attempts,
            budget_usd=budget_usd,
            client=client,
            item_id=item.item_id,
        )
        return Cell(
            item_id=item.item_id,
            role=role,
            level=level,
            model_id=run.model_id,
            question=item.question,
            run=run,
            # Judged on arrival. The reveal only decides whether it is shown.
            judgement=judge(run, by_item[item.item_id]),
            seconds=time.perf_counter() - started,
        )

    with ThreadPoolExecutor(max_workers=CONCURRENCY_PER_MODEL * len(arms)) as pool:
        futures = {
            pool.submit(_one, item, role, level): (item.item_id, role, level)
            for item, role, level in jobs
        }
        for future in as_completed(futures):
            item_id, role, level = futures[future]
            try:
                cell = future.result()
            except Exception as exc:  # noqa: BLE001 - a dead cell must not kill the grid
                log.error("trap_cell_failed", item_id=item_id, arm=arm_key(role, level),
                          error=str(exc))
                cell = Cell(item_id=item_id, role=role, level=level, model_id="", question="")
            state.put(cell)
            if on_cell:
                on_cell(cell)

    state.finished_at = time.perf_counter()
    return state


# Measured 2026-07-29 on a calibration run of one item from EACH of the ten patterns,
# both models, at L3 — mean tokens per one-shot call, rounded up.
#
# Sampling across patterns matters more than sample size here. The first calibration
# used items[:3], which are all pattern 1 ("how many products in this range"), and
# reported mean output of 34 tokens: a one-line COUNT(*). Projecting the trap from
# that would have under-estimated it by roughly six times, because the revenue
# patterns write joins and CASE expressions. An unrepresentative sample is a worse
# input to a spend cap than a small one.
_CALIBRATION = {
    "worker": {"input": 700, "output": 210},
    "frontier": {"input": 1100, "output": 260},
}


def estimate_trap_cost(n_items: int, *, arms: tuple[tuple[str, str], ...] = ARMS) -> float:
    """Projected est. USD for a trap of this size. Deliberately pessimistic.

    An estimate of an estimate — measured average token counts times the hand-entered
    price table — so it is rounded up rather than down. Refusing a run that would have
    just fit is a cheap mistake; discovering the cap was breached after the fact is not.
    """
    from loopeng.pricing import prices_for
    from loopeng.registry import spec_for

    total = 0.0
    for role, level in arms:
        shape = _CALIBRATION[role]
        # L0 is the shorter prompt; the difference is small next to output tokens.
        scale = 1.0 if level == "L3" else 0.7
        total += n_items * prices_for(spec_for(role).model_id).cost_usd(
            input_tokens=int(shape["input"] * scale),
            output_tokens=shape["output"],
        )
    return total * 1.25  # headroom for retries and thinking variance


def save_state(state: TrapState, path: Path) -> Path:
    """Write the run to results/ — the system of record.

    Everything needed to re-derive every reported number without another model call:
    each cell's SQL, its rows, its judgement, its usage. LangSmith is advisory; this
    file is not.
    """
    import json

    # Reuses the gold builder's encoder rather than default=str. That exact shortcut
    # turned Decimal('76744.66') into the string '76744.66' in Phase 0, and rows_equal
    # correctly refuses to equate a number with its string form — so every revenue row
    # in this file would come back unusable for any later analysis. results/ is the
    # system of record; it does not get a lossy encoder.
    from loopeng.gold.build import json_default

    payload = {
        "arms": [arm_key(role, level) for role, level in state.arms],
        "wall_clock_seconds": round(state.wall_clock_seconds, 2),
        "n_cells": len(state.cells),
        "usage": state.ledger().as_dict(),
        "cells": [
            {
                "item_id": cell.item_id,
                "arm": cell.arm,
                "role": cell.role,
                "level": cell.level,
                "model_id": cell.model_id,
                "question": cell.question,
                "seconds": round(cell.seconds, 3),
                "sql": cell.run.sql if cell.run else None,
                "rows": cell.run.rows if cell.run else None,
                "error": cell.run.error if cell.run else None,
                "termination": str(cell.run.termination) if cell.run else None,
                "n_attempts": len(cell.run.attempts) if cell.run else 0,
                "outcome": str(cell.judgement.outcome) if cell.judgement else None,
                "visible_kind": (
                    str(cell.judgement.visible_kind)
                    if cell.judgement and cell.judgement.visible_kind
                    else None
                ),
                "attributed_rules": (
                    list(cell.judgement.attributed_rules) if cell.judgement else []
                ),
                "ambiguous": cell.judgement.ambiguous if cell.judgement else False,
            }
            for cell in sorted(state.cells.values(), key=lambda c: (c.item_id, c.arm))
        ],
        "summary_by_arm": {
            arm_key(role, level): state.summary(arm_key(role, level))
            for role, level in state.arms
        },
        "paired": (
            state.paired_comparison(
                arm_key(*state.arms[0]), arm_key(*state.arms[1])
            ).as_dict()
            if len(state.arms) == 2
            else None
        ),
    }
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=json_default), encoding="utf-8")
    return path


def print_grid(state: TrapState, *, revealed: bool) -> None:
    """Terminal rendering. Unrevealed cells are identical whatever happened in them.

    A cell that reads "failed" before the reveal hands the room a free answer key for
    that row, which is exactly what the trap withholds.
    """
    if not revealed:
        landed = sum(1 for cell in state.cells.values() if cell.done)
        print(f"\n{landed} cells landed in {state.wall_clock_seconds:.1f}s. Scores withheld.\n")
        return

    print(f"\n{'=' * 70}\nREVEAL\n{'=' * 70}")
    for role, level in state.arms:
        arm = arm_key(role, level)
        summary = state.summary(arm)
        rate = state.silent_error_rate(arm)
        print(f"\n{arm_label(role, level)}:")
        print(f"  silent-error rate : {rate.render() if rate else 'not yet measured'}")
        print(f"  ran and returned  : {summary['n_ran_and_returned']}")
        print(f"  correct           : {summary['n_correct']}")
        print(f"  silently wrong    : {summary['n_silent_errors']}")
        print(
            f"  visible failures  : {summary['n_visible_failures']} "
            f"{summary['visible_failure_kinds']}"
        )
        print(f"  unclassified      : {summary['n_unclassified']}")
        print(f"  termination       : {summary['termination_reasons']}")
        if summary["attribution"]:
            print("  attribution:")
            for rule, count in summary["attribution"].items():
                print(f"    {rule}: {count}")

    if len(state.arms) == 2:
        paired = state.paired_comparison(arm_key(*state.arms[0]), arm_key(*state.arms[1]))
        print(f"\nPAIRED (McNemar exact): {paired.render()}")
        print(f"  table: both_correct={paired.both_correct} "
              f"only_first={paired.only_a_correct} only_second={paired.only_b_correct} "
              f"both_wrong={paired.both_wrong}")

    ledger = state.ledger()
    print(f"\nwall clock : {state.wall_clock_seconds:.1f}s")
    print(f"tokens     : {ledger.totals()}")
    print(f"cost       : est. ${ledger.cost_usd():.4f}")
