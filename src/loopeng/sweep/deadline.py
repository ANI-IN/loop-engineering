"""Stopping cleanly when the clock runs out, with the reduced n on the chart.

Both background jobs in the session have a hard deadline: the trap launches at minute
10 and must be finished by 55, the sweep launches at 95 and must be finished by 165.
The next stage starts whether or not they are done.

**A partial result with an honest n is a fine outcome. A stage that overruns and eats
the next one is not.** So the runner takes a deadline, reports its projected finish
continuously, and at the deadline stops — it does not keep going, and it does not
render blank.

WHY THIS IS NOT A TIMEOUT
-------------------------

A timeout kills work in flight. That would throw away a model call already paid for and
leave the item it belonged to unrecorded, so the cell would be short by an item nobody
could account for.

This is cooperative:

    checked before submitting  ->  no work is wasted
    in flight allowed to land  ->  no call is paid for and discarded
    every completion written   ->  the n is exactly what was measured

WHY THE DEADLINE NEVER CUTS AN ITEM SHORT — AND WHY THERE IS NO `TerminationReason.DEADLINE`
--------------------------------------------------------------------------------------------

The plan for this module was to add `DEADLINE` to `TerminationReason` alongside
`budget` and `max_attempts`. Writing it made the mistake visible, so it is recorded
here rather than quietly dropped.

`TerminationReason` names why ONE AGENT LOOP stopped on ONE ITEM. The deadline stops
the RUNNER between items. Those are different layers, and an item that never started
has no run, no attempts and no termination reason — it is not in the rows at all. A
`DEADLINE` member could therefore never be reached, which is precisely the decoration
`test_every_termination_reason_is_reachable` exists to catch. Adding it would have put
a branch in the enum that nothing can produce, in the enum whose docstring is about
policy branches nobody counts.

The tempting alternative — check the clock INSIDE the loop, between attempts, so a
long L2 item terminates as `deadline` with whatever it has — is worse, and not
because it is hard. **An item cut off after attempt 1 of 3 did not run under the
condition being measured.** It would be scored: a truncated answer counted as wrong,
or a not-yet-verified answer counted as correct, and either way an item enters the
accuracy figure having been given less than the arm it is reported under. Dropping the
item is honest. Half-running it and scoring it is not.

So the rule is: an item either runs FULLY under its condition or does not run at all.
Every item in a deadline-stopped cell is exactly as comparable as every item in a
complete one, and the only thing that changed is how many there are.

WHY IT REPORTS A PROJECTION RATHER THAN A COUNTDOWN
---------------------------------------------------

A countdown tells an operator how long is left. A projection tells them whether to
intervene, which is the decision they actually have. `projected_finish` extrapolates
from the items that have already landed, so it improves as the run proceeds and it is
honest about having nothing to extrapolate from before the first one.
"""

import time
from collections.abc import Callable
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass, field


@dataclass
class Deadline:
    """A wall-clock budget, checked cooperatively between items.

    `seconds` is None for no deadline, and that is the default everywhere: nothing
    acquires a time limit by accident. `clock` is injectable so the tests can drive it
    without sleeping — a test that proves a deadline by waiting for one is a test that
    makes the suite slower every time it passes.
    """

    seconds: float | None = None
    clock: Callable[[], float] = time.monotonic
    started: float = field(default=None)  # type: ignore[assignment]

    # How many completions before the projection is worth reporting. Set to the
    # concurrency by the caller; 0 means project from the first item.
    #
    # **Measured, not anticipated.** A live run at concurrency 2 printed:
    #
    #     1/16 items · 2s of 18s · projected finish 32s · WILL OVERRUN
    #     2/16 items · 2s of 18s · projected finish 17s · on track
    #     4/16 items · 6s of 18s · projected finish 22s · WILL OVERRUN
    #
    # `elapsed / done` divides the wall clock by the items that have FINISHED while
    # the other `concurrency - 1` are still running — uncounted work inside the
    # elapsed time — so the first reading overstates per-item cost by roughly the
    # concurrency and then collapses when the wave lands. The verdict flip is what
    # triggers a status line, so the least trustworthy phase produced the most output,
    # and an operator watching would have reached for the abort during the one window
    # where the number meant nothing.
    #
    # A rate measured before the pipeline is full is not the pipeline's rate. It is
    # withheld rather than smoothed: an average over a biased sample is still biased,
    # and "estimating" is the honest thing to print for the two seconds it applies.
    warmup: int = 0

    def __post_init__(self) -> None:
        if self.started is None:
            self.started = self.clock()

    @property
    def elapsed(self) -> float:
        return self.clock() - self.started

    @property
    def remaining(self) -> float | None:
        return None if self.seconds is None else self.seconds - self.elapsed

    def expired(self) -> bool:
        """Has the budget run out? False forever when there is no deadline."""
        return self.remaining is not None and self.remaining <= 0

    def projected_finish(self, done: int, total: int) -> float | None:
        """Seconds from the start to the last item, extrapolated from what landed.

        `None` before anything has landed: with no completed items there is no rate to
        extrapolate from, and a projection built on zero observations is a guess
        wearing a number's clothes. Callers print "estimating" rather than a figure
        nothing supports — the same rule `Metric` follows for a rate with no
        denominator.
        """
        if done <= 0 or total <= 0 or done < self.warmup:
            return None
        return self.elapsed / done * total

    def will_overrun(self, done: int, total: int) -> bool:
        projected = self.projected_finish(done, total)
        return (self.seconds is not None and projected is not None
                and projected > self.seconds)

    def status(self, done: int, total: int) -> str:
        """One line for the operator: where it is, and whether to intervene."""
        if self.seconds is None:
            return f"{done}/{total} items · {self.elapsed:.0f}s elapsed · no deadline"
        head = f"{done}/{total} items · {self.elapsed:.0f}s of {self.seconds:.0f}s"
        projected = self.projected_finish(done, total)
        if projected is None:
            return f"{head} · projected finish: estimating"
        verdict = "WILL OVERRUN" if projected > self.seconds else "on track"
        return f"{head} · projected finish {projected:.0f}s · {verdict}"


@dataclass
class BoundedRun:
    """What a bounded pass managed, and what stopped it if anything did."""

    results: list
    requested: int
    stopped_early: bool
    elapsed: float
    # Ctrl-C, handled as a stop rather than as a crash. See `run_bounded`.
    interrupted: bool = False

    @property
    def n(self) -> int:
        return len(self.results)

    @property
    def n_not_run(self) -> int:
        return self.requested - self.n

    def note(self) -> str:
        """What the cell says about its own n. Never silent about being partial."""
        if self.interrupted:
            return (
                f"INTERRUPTED after {self.elapsed:.0f}s: {self.n} of {self.requested} "
                f"items measured, and all {self.n} are on disk. The "
                f"{self.n_not_run} that never started were not estimated."
            )
        if not self.stopped_early:
            return f"all {self.requested} items measured"
        return (
            f"STOPPED AT THE DEADLINE after {self.elapsed:.0f}s: {self.n} of "
            f"{self.requested} items measured. Every figure here is computed over "
            f"those {self.n}, and the n beside each one says so. Nothing was "
            f"estimated for the {self.n_not_run} that never started."
        )


def run_bounded(items, work: Callable, *, concurrency: int,
                deadline: Deadline | None = None,
                on_result: Callable | None = None) -> BoundedRun:
    """Run `work` over `items`, submitting no new item once the deadline has passed.

    **Items are fed in rather than all queued at once**, which is the whole mechanism.
    `pool.submit` for every item up front hands the executor a queue it will drain
    regardless — cancelling those afterwards is possible but races with the worker
    picking them up, so the deadline would be advisory. Keeping at most `concurrency`
    in flight means the check before each submission is the only gate there is.

    `on_result` fires for every completion, including after the deadline has passed:
    an item already in flight is paid for, so its result is recorded. That is the
    difference between stopping and aborting.

    CTRL-C IS A DEADLINE OF ZERO, PLUS A FLAG.

    The first KeyboardInterrupt is caught here and handled exactly as the clock
    running out: stop submitting, let what is in flight land, record all of it. An
    operator who interrupts a sweep has decided to stop, not to destroy the last
    thirty calls they paid for — and the alternative is worse than losing them,
    because the exception would escape through the executor's context manager, which
    waits for those same calls anyway and then discards their results. The old
    behaviour was therefore "wait for the work, then throw it away".

    A SECOND Ctrl-C propagates. Someone pressing it twice means now, and a drain that
    cannot itself be interrupted is a hang with a good excuse.
    """
    deadline = deadline or Deadline()
    started = deadline.clock()
    pending = iter(items)
    requested = len(items)
    workers = max(1, concurrency)
    results: list = []
    interrupted = False

    with ThreadPoolExecutor(max_workers=workers) as pool:
        in_flight = set()

        def submit_next() -> bool:
            try:
                item = next(pending)
            except StopIteration:
                return False
            in_flight.add(pool.submit(work, item))
            return True

        while len(in_flight) < workers and submit_next():
            pass

        while in_flight:
            try:
                done, in_flight = wait(in_flight, return_when=FIRST_COMPLETED)
                for future in done:
                    result = future.result()
                    results.append(result)
                    if on_result:
                        on_result(result)
            except KeyboardInterrupt:
                if interrupted:
                    raise  # the second one means now
                interrupted = True
                continue
            # THE CHECK. Before refilling, never during a call, never on a result
            # already paid for. Ctrl-C gates the same door.
            if interrupted or deadline.expired():
                continue
            while len(in_flight) < workers and submit_next():
                pass

    return BoundedRun(
        results=results,
        requested=requested,
        # Short of the requested count, AND the clock is why.
        #
        # The count rather than "did the iterator run dry", which was the first
        # version and was wrong in a way only a trace shows: with the last items
        # already in flight, the iterator is never advanced again, so a deadline
        # expiring while they landed reported `stopped_early` on a cell that had in
        # fact measured everything. A partial-run flag that fires on a complete run
        # would put the deadline disclosure on a chart that did not need it, which is
        # the same class of error as omitting it from one that did.
        #
        # `work` cannot swallow items to reach here: a raising future re-raises at
        # `.result()` above rather than going unrecorded.
        stopped_early=len(results) < requested and deadline.expired(),
        elapsed=deadline.clock() - started,
        interrupted=interrupted,
    )
