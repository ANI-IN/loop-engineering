"""The live check of Assignment 1: Agent loop. Run it with: make check-assignment NAME=agent-loop

Deterministic first, against the real warehouse: the lookup itself (requirements 1 to 7). Then the
cost estimate and the OpenAI key, then the done-when scenario live through the api and the workers:
three questions with informal or misspelled names and one with two equally close names, each
passing on 2 of 3 runs: two runs, and a third only when they disagree (requirements 8 to 11).
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

import psycopg
from psycopg.conninfo import conninfo_to_dict

from datapilot import db
from datapilot.assignments.cost import Planned
from datapilot.assignments.gold import rows, same_result
from datapilot.assignments.live import (
    envelope,
    event_id,
    live_run,
    reject_all,
    settle,
    tool_calls,
    two_of_three,
)
from datapilot.assignments.report import LiveRun, repeated
from datapilot.config import pack_config
from datapilot.contracts.api import RunDetail
from datapilot.loop1_agent import extension
from datapilot.loop1_agent.catalog import load_snapshot
from datapilot.loop1_agent.tools import Warehouse
from datapilot.settings import get_settings

SLUG = "agent-loop"
NEEDED = 2  # of 3 runs; two_of_three makes the third only when the first two disagree
TIED = ("Alpine Trek 45L Backpack", "Alpine Trek 45 L Backpack")


@dataclass(frozen=True)
class Question:
    text: str
    kind: extension.Kind
    wording: str  # how the question names the thing
    value: str  # the exact value in the warehouse
    gold: tuple[str, ...]  # gold SQL; any one of them is a correct answer


PRICE = "SELECT round(list_price_cents / 100.0, 2) FROM warehouse.products WHERE name = '{}'"
CENTS = "SELECT list_price_cents FROM warehouse.products WHERE name = '{}'"
QUESTIONS = (
    Question(
        "What is the list price, in dollars, of the Cascde Lyne trail runner?",
        "product",
        "Cascde Lyne trail runner",
        "Cascade Line Trail Runner",
        (PRICE.format("Cascade Line Trail Runner"), CENTS.format("Cascade Line Trail Runner")),
    ),
    Question(
        "What is the list price, in dollars, of the trail runner from our Basin Haven line?",
        "product",
        "basin haven trail runners",
        "Basin Haven Trail Runner",
        (PRICE.format("Basin Haven Trail Runner"), CENTS.format("Basin Haven Trail Runner")),
    ),
    Question(
        "How many products do we list under trail running shoes?",
        "category",
        "trail running shoes",
        "Trail Runners",
        (
            "SELECT count(*) FROM warehouse.products p JOIN warehouse.categories c "
            "ON c.category_id = p.category_id WHERE c.name = 'Trail Runners'",
        ),
    ),
)
TIE_QUESTION = "What is the list price, in dollars, of the Alpine Trek 45 litre backpack?"
TIE_WORDING = "Alpine Trek 45 litre backpack"
# Requirement 6: while the lookup runs, every role but the agent's points at a closed port,
# and so does the port the settings build the Compose addresses from.
OTHER_ROLE_VARIABLES = (
    "DATABASE_URL_OWNER",
    "DATABASE_URL_APP",
    "DATABASE_URL_AGENT_ALT",
    "DATABASE_URL_SUPERUSER",
)
CLOSED = "postgresql://not-the-agent-role@127.0.0.1:1/closed?connect_timeout=2"
CLOSED_PORT = "1"
# The agent role's address for requirement 6, marked so that a lookup that keeps what it read
# for each address reads again.
MARKED = "application_name=datapilot-check-requirement-6"


def _warehouse(marker: str = "") -> Warehouse:
    url = db.url_for(db.Role.AGENT)
    if marker:
        url += ("&" if "?" in url else "?") + marker
    return Warehouse(load_snapshot(url, pack_config()["databases"]["allowed_schema"]), url)


@contextmanager
def only_the_agent_role() -> Iterator[None]:
    """For the block, the owner, application, and other agent roles point at a closed port, in
    the environment and in the settings both, so a lookup that connects as any of them fails,
    however its code names the role. warehouse.url, the agent role, still connects."""
    saved = {name: os.environ.get(name) for name in (*OTHER_ROLE_VARIABLES, "POSTGRES_PORT")}
    os.environ.update({name: CLOSED for name in OTHER_ROLE_VARIABLES})
    os.environ["POSTGRES_PORT"] = CLOSED_PORT
    get_settings.cache_clear()
    try:
        yield
    finally:
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        get_settings.cache_clear()


def _expect_best(kind: extension.Kind, wording: str, value: str):
    def probe() -> str | None:
        found = extension.lookup_values(_warehouse(), kind, wording)
        if found.best != value:
            seen = ", ".join(c.value for c in found.candidates[:3]) or "no candidates"
            return f'"{wording}" should resolve to "{value}"; it gave {seen}' + (
                " and marked them as a tie" if found.ambiguous else ""
            )
        return None

    return probe


def _tie() -> str | None:
    found = extension.lookup_values(_warehouse(), "product", TIE_WORDING)
    top = {c.value for c in found.candidates[:2]}
    if not found.ambiguous or top != set(TIED):
        return (
            f'"{TIE_WORDING}" is equally close to {TIED[0]} and {TIED[1]}: return both as the top '
            "two candidates and set ambiguous"
        )
    return None


def _bounded() -> str | None:
    found = extension.lookup_values(_warehouse(), "product", "backpack")
    names = {r[0] for r in rows("SELECT name FROM warehouse.products")}
    if not 0 < len(found.candidates) <= extension.MAX_CANDIDATES <= 10:
        return f"return 1 to MAX_CANDIDATES candidates (at most 10); got {len(found.candidates)}"
    if invented := [c.value for c in found.candidates if c.value not in names]:
        return f"every candidate must be an exact stored value; not stored: {invented}"
    return None


@contextmanager
def roles_read_as(seen: set[str]) -> Iterator[None]:
    """For the block, the role of every connection that sends the server anything: each query
    and fetch goes through Connection.wait, so a connection opened earlier counts as well."""
    sync_wait, async_wait = psycopg.Connection.wait, psycopg.AsyncConnection.wait

    def noted(conn, *args, **kwargs):
        seen.add(str(conn.info.user))
        return sync_wait(conn, *args, **kwargs)

    async def noted_async(conn, *args, **kwargs):
        seen.add(str(conn.info.user))
        return await async_wait(conn, *args, **kwargs)

    psycopg.Connection.wait, psycopg.AsyncConnection.wait = noted, noted_async
    try:
        yield
    finally:
        psycopg.Connection.wait, psycopg.AsyncConnection.wait = sync_wait, async_wait


def _read_only_role() -> str | None:
    """The role the lookup actually reads as: run with every other role's address closed, it
    must still find the stored values, and every connection it sends anything on, opened now or
    earlier, must be the agent role's."""
    warehouse = _warehouse(MARKED)
    seen: set[str] = set()
    with only_the_agent_role(), roles_read_as(seen):
        try:
            found = extension.lookup_values(warehouse, "product", "backpack")
        except psycopg.Error as error:
            return (
                "the lookup must read through warehouse.url, the agent role: with every other "
                f"role's address closed it could not connect ({type(error).__name__})"
            )
    agent = conninfo_to_dict(warehouse.url).get("user") if seen else None
    if others := sorted(role for role in seen if role != agent):
        return (
            "the lookup must read through warehouse.url, the agent role: it read as "
            f"{', '.join(others)}, on a connection it opened or kept"
        )
    if not found.candidates:
        return (
            "the lookup must read through warehouse.url, the agent role: with every other role's "
            'address closed it found no stored value for "backpack"'
        )
    return None


def _registered() -> str | None:
    log = extension.LookupLog()
    tools = {t.name: t for t in extension.lookup_tools(_warehouse(), log)}
    if extension.LOOKUP_TOOL_NAME not in tools:
        return f"agent-loop-2: return a tool named {extension.LOOKUP_TOOL_NAME} from lookup_tools"
    tools[extension.LOOKUP_TOOL_NAME].invoke({"kind": "product", "wording": "Basin Haven shoe"})
    if not log.lookups:
        return "agent-loop-2: the tool must append each Lookup it makes to log.lookups"
    if extension.LOOKUP_TOOL_NAME not in extension.WORKING_METHOD:
        return (
            f"agent-loop-3: WORKING_METHOD must tell the analyst when to call "
            f"{extension.LOOKUP_TOOL_NAME}"
        )
    return None


def _ask(ctx, text: str) -> RunDetail:
    submitted = ctx.api.submit("question.asked", {"question": text}, event_id(SLUG, "question"))
    return settle(ctx.api, str(submitted.run_id), reject_all)


def _looked_up_first(detail: RunDetail) -> bool:
    calls = tool_calls(detail)
    if extension.LOOKUP_TOOL_NAME not in calls:
        return False
    return "run_query" not in calls or calls.index(extension.LOOKUP_TOOL_NAME) < calls.index(
        "run_query"
    )


def _judge(question: Question, detail: RunDetail) -> LiveRun:
    answer = envelope(detail)
    problems = []
    if answer is None or answer.status.value != "answered":
        problems.append(f"status {answer.status.value if answer else 'none'}")
    else:
        same, why = same_result(answer.final_sql, question.gold)
        if not same:
            problems.append(f"wrong answer ({why})")
        noted = " ".join(answer.assumptions).lower()
        if question.value.lower() not in noted:
            problems.append(f'"{question.value}" is not in the assumptions')
    if not _looked_up_first(detail):
        problems.append(f"no {extension.LOOKUP_TOOL_NAME} call before run_query")
    what = "correct, looked up first, match recorded" if not problems else "; ".join(problems)
    return live_run(detail, not problems, what)


def _judge_tie(detail: RunDetail) -> LiveRun:
    """Both stored names, letter for letter and space for space; letter case aside, since the
    question is written for a person (the SPEC says so)."""
    answer = envelope(detail)
    asked = (answer.clarifying_question or "") if answer else ""
    named = all(name.lower() in asked.lower() for name in TIED)
    ok = bool(answer) and answer.status.value == "needs_clarification" and named
    what = (
        "asked which of the two products"
        if ok
        else (f"status {answer.status.value if answer else 'none'}; question: {asked or 'none'}")
    )
    return live_run(detail, ok, what)


def run(ctx) -> None:
    report = ctx.report
    for number, question in enumerate(QUESTIONS[:2], start=1):
        label = "misspelled" if number == 1 else "informal"
        report.check(
            number,
            f"The lookup maps {label} product wording to the exact product name",
            _expect_best(question.kind, question.wording, question.value),
        )
    report.check(
        3,
        "The lookup maps informal category wording to the exact category name",
        _expect_best(QUESTIONS[2].kind, QUESTIONS[2].wording, QUESTIONS[2].value),
    )
    report.check(4, "Two equally close exact values are returned together as a tie", _tie)
    report.check(5, "The lookup returns a short list of stored values, never a column", _bounded)
    report.check(6, "The lookup reads only through the read-only agent role", _read_only_role)
    registered = report.check(
        7, "The lookup tool is registered and the working method names it", _registered
    )

    live_texts = [
        *(f"Live: {q.wording!r} answers correctly, with the lookup first" for q in QUESTIONS),
        "Live: two equally close product names end in needs_clarification naming both",
    ]
    if not registered.passed:
        ctx.live_gate([], none_because="requirement 7 failed, so the analyst has no lookup tool")
        for offset, text in enumerate(live_texts):
            report.not_run(8 + offset, text, "requirement 7 failed first")
        return
    cases = [*QUESTIONS, None]  # None: the tie question
    ctx.live_gate(
        [
            Planned(
                "analyst runs (4 questions, 2 runs each)",
                2 * len(cases),
                ctx.agent_model,
                extra=len(cases),
            )
        ],
        live=list(enumerate(live_texts, start=8)),
        typical="about 0.4 cents",
    )
    groups = two_of_three(
        cases,
        lambda case: _ask(ctx, case.text if case else TIE_QUESTION),
        lambda case, detail: _judge(case, detail) if case else _judge_tie(detail),
    )
    for index, runs in enumerate(groups[:-1]):
        report.add(
            repeated(
                8 + index,
                live_texts[index],
                runs,
                needed=NEEDED,
                fix="call the lookup before filtering on a name, filter on its exact value, and "
                "record the match in assumptions",
            )
        )
    report.add(
        repeated(
            11,
            live_texts[3],
            groups[-1],
            needed=NEEDED,
            fix="when the lookup reports a tie, end with needs_clarification and name both values",
        )
    )
