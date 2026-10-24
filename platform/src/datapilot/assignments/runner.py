"""Running one assignment's live check against a tree (the repository, or a copy with a solution
applied): load its check.py, bring up the stack, and report.

Order inside every check: the stack, the deterministic requirements (no model calls), then the
live gate (the cost estimate with the check's spend cap, then the OpenAI key), then the live steps,
then the actual spend. A check that reaches its spend cap stops cleanly: the kill switch stops its
runs under way, the stack is put back as a normal end leaves it, every requirement is printed as
PASS, FAIL, or NOT RUN, and the check exits stopped (2).
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType

import datapilot
from datapilot.assignments import Assignment, assignment
from datapilot.assignments.cost import (
    Cap,
    CapReached,
    Planned,
    check_activity,
    check_cap_usd,
    dollars,
    estimate_lines,
    headroom_usd,
    ledger_mark,
    spent_since,
)
from datapilot.assignments.keys import require_openai_key
from datapilot.assignments.live import Api
from datapilot.assignments.report import STOPPED, Report, Stop
from datapilot.assignments.stack import Stack, bring_up, reset_command
from datapilot.settings import MissingSetting, get_settings

PACKAGE_TREE = Path(datapilot.__file__).resolve().parents[3]


@dataclass
class Context:
    """What a check.py receives."""

    assignment: Assignment
    tree: Path
    report: Report
    stack: Stack
    api: Api
    activity: str
    mark: int | None = None  # the spend ledger's last row before the first model call
    cleanups: list[Callable[[], None]] = field(default_factory=list)
    cap: Cap | None = None  # this check's spend cap, from the live gate on
    live: list[tuple[int, str]] = field(default_factory=list)  # the live requirements, in order

    def live_gate(
        self,
        planned: list[Planned],
        *,
        none_because: str = "",
        live: Sequence[tuple[int, str]] = (),
        typical: str = "",
    ) -> None:
        """Before the first model call: print the estimate and the spend cap, then check the OpenAI
        key. `live` names the live requirements, so a stop at the cap prints each one; `typical` is
        what a check of a working solution spent in the build's verification."""
        say = self.report.say
        say()
        cap_usd = check_cap_usd() if planned else None
        headroom = 0.0
        self.live = list(live)
        if planned:
            try:
                lines = estimate_lines(planned, cap_usd=cap_usd, typical=typical)
                headroom = headroom_usd(planned)
            except KeyError as error:  # a model without a price in pack.yaml
                raise Stop(str(error).strip("'\"")) from None
            for line in lines:
                say(line)
        else:
            say(f"No live step will run this time, because {none_because}.")
        require_openai_key()
        if self.api.control().kill_switch == "engaged":
            reset = reset_command(self.assignment.slug)
            raise Stop(
                "The kill switch of this check's stack is engaged, so every live run would be "
                f"blocked: release it on the check's console ({self.stack.console_url}), or with "
                f"{reset}, which resets the check's own stack and never the class stack, then run "
                "the check again."
            )
        self.mark = ledger_mark()
        if cap_usd is not None:
            self.cap = Cap(cap_usd, self.mark, self.activity, headroom)
            self.api.cap = self.cap
        say("OpenAI key: accepted (checked without using tokens)")
        say()

    def on_exit(self, cleanup: Callable[[], None]) -> None:
        self.cleanups.append(cleanup)

    @property
    def agent_model(self) -> str:
        try:
            return get_settings().agent_model
        except MissingSetting as error:
            raise Stop(str(error)) from None

    @property
    def analyzer_model(self) -> str:
        try:
            return get_settings().analyzer_model
        except MissingSetting as error:
            raise Stop(str(error)) from None


def load_check(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        f"assignment_check_{path.parent.parent.name}", path
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses in the check look their module up here
    spec.loader.exec_module(module)
    return module


AT_CAP = "the check stopped at its spend cap first"


def stop_at_cap(
    reached: CapReached,
    report: Report,
    api: Api,
    live: Sequence[tuple[int, str]],
    *,
    slug: str,
    mark: int,
    activity: str,
) -> int:
    """A clean stop at the spend cap: wind the runs down, say what was spent and what did not run,
    and how to run again. Exit code: stopped (2)."""
    say = report.say
    engaged = api.engaged_at_cap
    try:
        still = api.wind_down()
    except Exception as error:  # say so; the rest of the stop still prints
        still, api.halt_error = [], f"{type(error).__name__}: {str(error)[:200]}"
    spent = spent_since(mark, activity)
    cap = api.cap.usd if api.cap is not None else check_cap_usd()
    say()
    say(
        f"Stopped: this check reached its spend cap of {dollars(cap)} "
        "(assignments.check_cap_usd in pack.yaml)."
    )
    say(
        f"It spent {spent.cost_usd:.4f} dollars ({spent.cost_usd * 100:.2f} cents) in "
        f"{spent.calls} model calls, and started no new run once the runs under way could take "
        "it past the cap."
    )
    if api.halt_error:
        say(
            f"The kill switch could not be engaged or released ({api.halt_error}): open the "
            "console and check it before you run anything else."
        )
    elif still:
        say(
            "The kill switch stays engaged, because these runs had not ended: "
            f"{', '.join(still)}. Release it on the console once they end."
        )
    elif engaged:
        say(
            "The kill switch stopped the runs under way and is released again; the autonomy level "
            "is put back."
        )
    judged = {r.number for r in report.results}
    for number, text in live:
        if number not in judged:
            report.not_judged(number, text, AT_CAP)
    code = report.finish_stopped("at the spend cap")
    say(
        f"To run again: make check-assignment NAME={slug}. Each check has its own cap, counted "
        "from its own first model call. A check of a working solution typically costs far less "
        "(docs/costs.md); one that keeps reaching the cap is spending in a loop, which the traces "
        "of its runs show."
    )
    return code


def run_check(slug: str, tree: Path) -> int:
    target = assignment(slug, tree)
    report = Report(target.title)
    name = check_activity(slug)  # this run's own, so a check beside it never counts here
    report.say(f"{target.title}: live check (make check-assignment NAME={slug})")
    report.say(f"Tree: {tree}")
    context: Context | None = None
    code = STOPPED
    try:
        stack = bring_up(tree, name, report.say)
        context = Context(target, tree, report, stack, Api(stack.api_url, slug=slug), name)
        load_check(target.check_file).run(context)
        code = report.finish()
    except CapReached as reached:
        if context is None or context.mark is None:
            report.say(str(reached))
        else:
            code = stop_at_cap(
                reached,
                report,
                context.api,
                context.live,
                slug=slug,
                mark=context.mark,
                activity=name,
            )
    except Stop as stop:
        report.say(str(stop))
    except Exception as error:  # the check itself broke: say so, never report a PASS
        report.say(f"The check stopped on an error: {type(error).__name__}: {error}")
    finally:
        if context is not None:
            for cleanup in reversed(context.cleanups):
                try:
                    cleanup()
                except Exception as error:  # report it; the other cleanups still run
                    report.say(f"Cleanup step failed: {type(error).__name__}: {error}")
            if context.mark is not None:
                report.say(spent_since(context.mark, name).line(name))
    return code


def check_in_tree(slug: str, tree: Path) -> int:
    """Run the check with the tree's own code: the same interpreter, the tree first on the path."""
    tree = tree.resolve()
    if tree == PACKAGE_TREE:
        return run_check(slug, tree)
    env = {**os.environ, "PYTHONPATH": str(tree / "platform" / "src")}
    done = subprocess.run(
        [sys.executable, "-m", "datapilot.assignments", "check", slug], cwd=tree, env=env
    )
    return done.returncode
