"""The only module that reads planted-item flags. Every flag must be in the planted registry.

A flag is on for a process when its environment sets it (a service reads .env when it starts), or
for one run only, inside `for_this_run`: a demo sends its flags with its own events and requests
(the HTTP header PLANTED_HEADER), and the api, the worker, and the hill-climbing runner switch them
on for that run's work alone, so the flags never outlive the demo and never reach another run. The
api takes only the named demo's own flags (allowed_for), and never one read as a service starts
(AT_SERVICE_START): for those, make demo restarts the service with the flag and a tag
(TAG_VARIABLE), and the restarted worker claims only the jobs of the demo's runs, which carry it.

Each service also reports the flags its own environment switched on when it started
(ops.service_planted), so a live check and the finale can refuse while any is on.
"""

from __future__ import annotations

import os
import re
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from datapilot.contracts import registries
from datapilot.contracts.registries import PlantedKind
from datapilot.settings import REPO

if TYPE_CHECKING:
    import psycopg

_ON = {"1", "true", "yes", "on"}
# The flags a demo switched on for the run being worked on in this context (empty: none).
_THIS_RUN: ContextVar[frozenset[str]] = ContextVar("planted_this_run", default=frozenset())
# The request header that carries a demo's flags, comma-separated, to the api.
PLANTED_HEADER = "DataPilot-Planted"
# The payload key (events) and the params key (hill-climbing requests) the api stores them under.
REQUESTED_KEY = "planted"
# The .env file the services read when they start (a copy of the tree links the checkout's).
ENV_FILE = REPO / ".env"

REPORT_SQL = (
    "INSERT INTO ops.service_planted (service, planted_active) VALUES (%s, %s) "
    "ON CONFLICT (service) DO UPDATE SET planted_active = EXCLUDED.planted_active, "
    "started_at = now()"
)
SERVICES_SQL = (
    "SELECT service, planted_active FROM ops.service_planted "
    "WHERE cardinality(planted_active) > 0 ORDER BY service"
)


def planted(flag: str) -> bool:
    """True when a planted code bug or demo aid is switched on. An unknown flag is a bug here,
    not a silent False, so a typo cannot hide a planted branch."""
    if flag not in set(flags()):
        raise KeyError(f"{flag} is not in platform/planted/registry.yaml")
    return flag in _THIS_RUN.get() or _is_on(os.environ.get(flag, "0"))


def flags() -> list[str]:
    """Every flag: the planted registry's, then the demo pacing aid."""
    return [*registries.planted().flags, "DEMO_PACING"]


def active() -> list[str]:
    """The flags that are on now, for run metadata and the console chips."""
    return [flag for flag in flags() if planted(flag)]


def checked(names: Iterable[str]) -> list[str]:
    """The names, each a known flag (KeyError otherwise), in the registry's order."""
    wanted = {name.strip() for name in names if name.strip()}
    unknown = sorted(wanted - set(flags()))
    if unknown:
        raise KeyError(f"{', '.join(unknown)} not in platform/planted/registry.yaml")
    return [flag for flag in flags() if flag in wanted]


@contextmanager
def for_this_run(names: Iterable[str]) -> Iterator[list[str]]:
    """Switch flags on for the work done in this context only: one demo's run or request. They
    end with the block, even on an error, so the next run starts with none of them."""
    chosen = checked(names)
    token = _THIS_RUN.set(_THIS_RUN.get() | frozenset(chosen))
    try:
        yield chosen
    finally:
        _THIS_RUN.reset(token)


def this_run() -> list[str]:
    """The flags switched on for this run alone (by for_this_run), in the registry's order."""
    return [flag for flag in flags() if flag in _THIS_RUN.get()]


def carried[**P, R](fn: Callable[P, R]) -> Callable[P, R]:
    """fn, run with the flags switched on for this run now, from any thread: a thread pool does not
    carry them into its threads by itself."""
    names = this_run()
    if not names:
        return fn

    def run(*args: P.args, **kwargs: P.kwargs) -> R:
        with for_this_run(names):
            return fn(*args, **kwargs)

    return run


def from_header(value: str | None) -> list[str]:
    """The flags a PLANTED_HEADER value names (KeyError for an unknown one)."""
    return checked((value or "").split(","))


def header(names: Sequence[str], demo: str = "") -> dict[str, str]:
    """The headers that carry a demo's flags for its own runs: the flags, and the demo they
    belong to (DEMO_HEADER), which the api checks them against."""
    if not names:
        return {}
    return {PLANTED_HEADER: ",".join(checked(names)), **({DEMO_HEADER: demo} if demo else {})}


# Flags read once, as a service starts, so no run can carry them: the service they need restarted.
AT_SERVICE_START = {
    "BUG_MEMORY_CHECKPOINTER": "worker",  # the checkpointer is made when the worker starts
    "BUG_LOCK_DURING_LLM": "worker",  # the claim reads it before the run is known
}
# The demos whose only half is the planted one: the naive analyzer's fixed half is another demo,
# the analyzer team (improve-analyzer-team-approve). `make demo NAME=<demo>` switches their planted
# bugs on with or without PLANTED=1, so the registry's make trigger shows the demo's moment.
ONLY_PLANTED_HALF = frozenset({"improve-naive-analyzer-blocked"})
# The demo the planted flags of a request belong to, for a request that does not name it itself
# (a hill-climbing request; an event names it in its payload's demo_name).
DEMO_HEADER = "DataPilot-Demo"


def for_one_run(demo: str) -> list[str]:
    """The flags a demo may switch on for one of its own runs or requests: its planted code bugs
    and demo aids, except those read only as a service starts (they could not act on the run)."""
    found = registries.demos().by_id(demo)
    return [flag for flag in for_demo(found.planted, bugs=True) if flag not in AT_SERVICE_START]


class NotTheDemos(ValueError):
    """Planted flags a request may not switch on: the message says which, and why."""


def allowed_for(chosen: Sequence[str], demo: str | None) -> list[str]:
    """`chosen`, when every flag is the named demo's own for one run; NotTheDemos otherwise."""
    if not chosen:
        return []
    if not demo:
        raise NotTheDemos(
            f"planted flags need the demo they belong to: name it in the event's demo_name or "
            f"the {DEMO_HEADER} header"
        )
    try:
        found = registries.demos().by_id(demo)
    except KeyError:
        raise NotTheDemos(f"{demo} is not a demo in platform/demos/registry.yaml") from None
    own = for_demo(found.planted, bugs=True)
    if others := [flag for flag in chosen if flag not in own]:
        raise NotTheDemos(
            f"{', '.join(others)} is not a planted flag of {demo} (its own: "
            f"{', '.join(own) or 'none'})"
        )
    if at_start := [flag for flag in chosen if flag in AT_SERVICE_START]:
        raise NotTheDemos(
            f"{', '.join(at_start)} is read as the {AT_SERVICE_START[at_start[0]]} starts, never "
            f"for one run: make demo NAME={demo} PLANTED=1 restarts that service with it"
        )
    return list(chosen)


# A worker restarted for a demo's service-start flag claims only the jobs of that demo's runs: the
# api tags them with TAG_HEADER's value, and the restart sets the same tag in the worker's
# environment (TAG_VARIABLE), until the demo restarts it without.
TAG_HEADER = "DataPilot-Demo-Tag"
TAG_VARIABLE = "DATAPILOT_DEMO_RUN_TAG"


def service_tag() -> str | None:
    """The tag of the one demo this service was restarted for, or None: it serves every run."""
    return os.environ.get(TAG_VARIABLE, "").strip() or None


def merged(*lists: Iterable[str]) -> list[str]:
    """The flags of every list, each once, in the order first seen."""
    return list(dict.fromkeys(flag for names in lists for flag in names))


def for_demo(planted_ids: Sequence[str], *, bugs: bool) -> list[str]:
    """The flags a demo switches on for its own runs: its demo aids (such as demo pacing) always,
    and its planted code bugs only for the planted half (`bugs`)."""
    registry, known = registries.planted(), set(flags())
    out = []
    for item_id in planted_ids:
        kind = registry.by_id(item_id).kind if item_id in known else None
        if kind is PlantedKind.DEMO_AID or (bugs and kind is PlantedKind.CODE_BUG):
            out.append(item_id)
    return checked(out)


# --- where a flag is on --------------------------------------------------------------------------
def _is_on(value: str) -> bool:
    return value.strip().strip("'\"").strip().lower() in _ON


# A .env line as Compose reads it: any leading whitespace, an optional `export` and whitespace
# (spaces or tabs), the name, whitespace, the equals sign (session 6 review, round 2: an indented
# `export` line and `export` with a tab were on for Compose and off here).
ENV_LINE = re.compile(r"^\s*(?:export\s+)?(?P<key>[A-Za-z_][A-Za-z0-9_]*)\s*=(?P<value>.*)$")


def in_env_file(path: Path) -> list[str]:
    """The flags a .env file switches on (the services read it when they start); later lines win,
    as Compose reads them. A missing file switches none on."""
    if not path.is_file():
        return []
    values: dict[str, str] = {}
    known = set(flags())
    for line in path.read_text(encoding="utf-8").splitlines():
        found = ENV_LINE.match(line)
        if found and found["key"] in known:
            values[found["key"]] = re.split(r"\s#", found["value"], maxsplit=1)[0]
    return [flag for flag in flags() if _is_on(values.get(flag, "0"))]


def in_environment(environ: Mapping[str, str]) -> list[str]:
    return [flag for flag in flags() if _is_on(environ.get(flag, "0"))]


IN_ENV_FILE = ".env"
THIS_SHELL = "this shell's environment"


def switched_on(
    *,
    env_file: Path | None = None,
    environ: Mapping[str, str] | None = None,
    services: Mapping[str, Sequence[str]] | None = None,
) -> dict[str, list[str]]:
    """Every flag that is on, with where: the .env file (what a service started now gets), this
    process's environment, and each running service's own report of its flags."""
    on: dict[str, list[str]] = {}
    for flag in in_env_file(env_file) if env_file is not None else []:
        on.setdefault(flag, []).append(IN_ENV_FILE)
    for flag in in_environment(environ) if environ is not None else []:
        on.setdefault(flag, []).append(THIS_SHELL)
    for service, names in (services or {}).items():
        for flag in names:
            on.setdefault(flag, []).append(f"the {service} service")
    return {flag: on[flag] for flag in flags() if flag in on}


def off_in_env_file(flag: str) -> str:
    """The sed command (GNU sed, as on Linux and in WSL) that turns `flag` off in .env in every
    form in_env_file reads as on: `FLAG=1`, indented, after `export` and spaces or tabs, and with
    spaces or tabs around the equals sign."""
    space = "[[:space:]]"
    pattern = f"^{space}*(export{space}+)?{flag}{space}*="
    return f"sed -i -E 's/{pattern}.*/{flag}=0/' .env"


def refusal(on: Mapping[str, Sequence[str]], what: str) -> str | None:
    """Why `what` does not start while planted flags are on, naming each flag, where it is on, and
    how to turn it off; None when none is."""
    if not on:
        return None
    named = "; ".join(f"{flag} (on in {', '.join(where)})" for flag, where in on.items())
    edits = " ".join(off_in_env_file(flag) for flag in on)
    shell = [flag for flag, where in on.items() if THIS_SHELL in where]
    unset = f" Also unset it in this shell: unset {' '.join(shell)}." if shell else ""
    return (
        f"{what} does not start while planted flags are on: {named}. It runs on the fixed system "
        f"only. Turn each off: set it to 0 in .env ({edits}), then make up.{unset}"
    )


# --- each service's own report --------------------------------------------------------------------
def report_service(conn: psycopg.Connection[Any], service: str) -> list[str]:
    """Record the flags this process's environment switched on as it starts (the per-run flags of
    a demo are never among them); returns them."""
    on = in_environment(os.environ)
    conn.execute(REPORT_SQL, (service, on))
    return on


def service_reports(conn: psycopg.Connection[Any]) -> dict[str, tuple[list[str], datetime]]:
    """Every service's latest report: its flags and when it wrote them (as it started)."""
    rows = conn.execute("SELECT service, planted_active, started_at FROM ops.service_planted")
    return {row["service"]: (list(row["planted_active"]), row["started_at"]) for row in rows}


def services_on(conn: psycopg.Connection[Any]) -> dict[str, list[str]]:
    """Each service that reported flags on at its start, with them."""
    return {row["service"]: list(row["planted_active"]) for row in conn.execute(SERVICES_SQL)}
