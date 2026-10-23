"""What a check prints: one PASS or FAIL line per requirement, and for each live step its trace
link and live stamp. A FAIL line says what to fix; a NOT RUN line names a requirement a stop at the
check's spend cap left unjudged. Exit codes: 0 every requirement passed, 1 any failed, 2 the check
stopped before it could finish (such as a missing OpenAI key, or its spend cap)."""

from __future__ import annotations

import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import TextIO

PASSED, FAILED, STOPPED = 0, 1, 2


class Stop(RuntimeError):
    """The check cannot go on; the message is printed as is and the check exits 2."""


@dataclass(frozen=True)
class LiveRun:
    """One live step: what it showed, and where to see it."""

    passed: bool
    detail: str
    run_id: str | None = None
    started_at_utc: str | None = None
    session_id: str | None = None
    trace: str = "no trace link"

    def stamp(self) -> str:
        if self.run_id is None:
            return "no live stamp: the step did not start a run"
        return f"run {self.run_id}, started {self.started_at_utc} (UTC), session {self.session_id}"


@dataclass
class Result:
    number: int
    text: str
    passed: bool
    fix: str = ""
    live: list[LiveRun] = field(default_factory=list)
    rule: str = ""  # the pass rule and how the live runs did against it
    ran: bool = True  # False: the check stopped before it could judge this requirement


def repeated(number: int, text: str, runs: Sequence[LiveRun], *, needed: int, fix: str) -> Result:
    """A model-dependent requirement: it passes when at least `needed` of its runs passed."""
    passes = sum(r.passed for r in runs)
    ok = passes >= needed
    rule = f"passed {passes} of {len(runs)} runs; {RULE}"
    return Result(number, text, ok, "" if ok else fix, list(runs), rule)


RULE = "passes on 2 of 3 runs; a third run is made only when the first two disagree"


def per_case(
    number: int, text: str, groups: Sequence[Sequence[LiveRun]], *, needed: int, fix: str
) -> Result:
    """Several model-dependent cases under one requirement: each case must pass on its own."""
    ok = all(sum(r.passed for r in group) >= needed for group in groups)
    counts = ", ".join(f"{sum(r.passed for r in g)} of {len(g)}" for g in groups)
    rule = f"each of the {len(groups)} cases {RULE}; passes per case, in order: {counts}"
    runs = [run for group in groups for run in group]
    return Result(number, text, ok, "" if ok else fix, runs, rule)


@dataclass
class Report:
    title: str
    out: TextIO = sys.stdout
    results: list[Result] = field(default_factory=list)

    def say(self, text: str = "") -> None:
        print(text, file=self.out, flush=True)

    def add(self, result: Result) -> Result:
        self.results.append(result)
        mark = "NOT RUN" if not result.ran else "PASS" if result.passed else "FAIL"
        self.say(f"{mark}  {result.number}. {result.text}")
        if not result.ran:
            self.say(f"      {result.fix}")
            return result
        if result.rule:
            self.say(f"      {result.rule}")
        if not result.passed and result.fix:
            self.say(f"      To fix: {result.fix}")
        for index, run in enumerate(result.live, start=1):
            self.say(f"      live run {index}: {'PASS' if run.passed else 'FAIL'}, {run.detail}")
            self.say(f"        trace: {run.trace}")
            self.say(f"        live stamp: {run.stamp()}")
        return result

    def check(self, number: int, text: str, probe: Callable[[], str | None]) -> Result:
        """A deterministic requirement: `probe` returns None when it holds, else what to fix. An
        unfinished extension point (NotImplementedError) or any error is a FAIL that says so."""
        try:
            problem = probe()
        except NotImplementedError as error:
            problem = f"the extension point is not filled in yet: {error}"
        except Exception as error:  # a broken solution fails its line; the check goes on
            problem = f"{type(error).__name__}: {str(error).strip()[:300]}"
        return self.add(Result(number, text, problem is None, problem or ""))

    def not_run(self, number: int, text: str, why: str) -> Result:
        return self.add(Result(number, text, False, f"not run, because {why}"))

    def not_judged(self, number: int, text: str, why: str) -> Result:
        """A requirement a stop left unjudged: printed NOT RUN, never PASS."""
        return self.add(Result(number, text, False, f"Not run, because {why}.", ran=False))

    def finish_stopped(self, why: str) -> int:
        passed = sum(r.passed for r in self.results)
        failed = sum(r.ran and not r.passed for r in self.results)
        unjudged = sum(not r.ran for r in self.results)
        self.say(
            f"Result: STOPPED {why}, {passed} of {len(self.results)} requirements passed, "
            f"{failed} failed, {unjudged} not run"
        )
        return STOPPED

    def finish(self) -> int:
        passed = sum(r.passed for r in self.results)
        total = len(self.results)
        verdict = "PASS" if passed == total and total else "FAIL"
        self.say(f"Result: {verdict}, {passed} of {total} requirements passed")
        return PASSED if verdict == "PASS" else FAILED
