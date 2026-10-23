"""The build-wide spend ledger: every model call records its tokens and cost.

The ledger is a SQLite table outside the Compose database, so resets never lose it and every track,
worktree, and container writes the same file (DATAPILOT_SPEND_LEDGER, mounted into the services).
Before each model call, `check_budget` refuses an activity no budget line covers and stops live work
at its line's cap or the stop line (build_budget in pack.yaml); crossing the warning
line logs once per process. Those lines bind only the build (DATAPILOT_BUILD_BUDGET=1 in its .env);
a learner's machine records every call but is limited only by the learner's own OpenAI project.
`make spend` prints the running total by activity.

A call that fails after it was sent (a timeout, a cut-off stream, a refusal) is recorded too, with
the usage the error reports, or else an estimate from the request marked `estimated`, because
OpenAI can bill it. Cache writes are priced as OpenAI bills them, above the plain input rate.
"""

from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage
from langchain_core.outputs import LLMResult

from datapilot.config import pack_config
from datapilot.settings import REPO, get_settings

log = structlog.get_logger("spend")

DEFAULT_LEDGER = Path.home() / ".datapilot" / "spend-ledger.sqlite"
ENV_FILE = REPO / ".env"
_SCHEMA = """
CREATE TABLE IF NOT EXISTS spend_ledger (
    id INTEGER PRIMARY KEY,
    ts TEXT NOT NULL,
    activity TEXT NOT NULL,
    component TEXT NOT NULL,
    model TEXT NOT NULL,
    input_tokens INTEGER NOT NULL,
    cached_input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    cost_usd REAL NOT NULL,
    run_id TEXT
)
"""
# Columns added after the first ledgers were written: _connect adds any that a ledger lacks, so
# existing rows keep their values and read as no cache writes, measured usage, and no error.
_ADDED_COLUMNS = {
    "cache_write_tokens": "INTEGER NOT NULL DEFAULT 0",  # 30-minute cache writes
    "cache_write_12h_tokens": "INTEGER NOT NULL DEFAULT 0",  # 12-hour cache writes
    "estimated": "INTEGER NOT NULL DEFAULT 0",  # 1: usage estimated from the request
    "error": "TEXT",  # the error type of a failed call, else NULL
}
_warned = False


class BudgetStop(RuntimeError):
    """Live work has reached the build budget's stop line."""


@dataclass(frozen=True)
class Usage:
    """One call's tokens as OpenAI bills them. input_tokens is every input token; of those,
    cached_input_tokens were read from the cache and the two cache-write counts were written to it
    (OpenAI's cached_tokens excludes written tokens), and the rest are plain input."""

    input_tokens: int
    cached_input_tokens: int
    output_tokens: int  # includes reasoning tokens, as OpenAI bills them
    cache_write_tokens: int = 0  # written with the default 30-minute lifetime
    cache_write_12h_tokens: int = 0  # written with the 12-hour lifetime


def ledger_path() -> Path:
    return Path(os.environ.get("DATAPILOT_SPEND_LEDGER", DEFAULT_LEDGER))


def _connect(path: Path | None = None) -> sqlite3.Connection:
    path = path or ledger_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(_SCHEMA)
    present = {row[1] for row in conn.execute("PRAGMA table_info(spend_ledger)")}
    for column, kind in _ADDED_COLUMNS.items():
        if column not in present:
            try:
                conn.execute(f"ALTER TABLE spend_ledger ADD COLUMN {column} {kind}")
            except sqlite3.OperationalError as error:  # another process added it first
                if "duplicate column" not in str(error):
                    raise
    return conn


def _rate(price: dict[str, float], kind: str, model: str, tokens: int) -> float:
    if not tokens:
        return 0.0
    if kind not in price:
        raise KeyError(f"no {kind} price for {model}: add it to prices in pack.yaml")
    return tokens * price[kind]


def cost_usd(model: str, usage: Usage) -> float:
    """What OpenAI bills for the call: plain input, cache reads, cache writes at their own rates
    (30-minute and 12-hour), and output, all per million tokens from the pack's price table."""
    prices = pack_config()["prices"]
    if model not in prices:
        raise KeyError(f"no price for {model}: add it to prices in pack.yaml before calling it")
    price = prices[model]
    written = usage.cache_write_tokens + usage.cache_write_12h_tokens
    plain_input = usage.input_tokens - usage.cached_input_tokens - written
    return (
        plain_input * price["input"]
        + usage.cached_input_tokens * price["cached_input"]
        + _rate(price, "cache_write_30m", model, usage.cache_write_tokens)
        + _rate(price, "cache_write_12h", model, usage.cache_write_12h_tokens)
        + usage.output_tokens * price["output"]
    ) / 1_000_000


def total_usd(path: Path | None = None) -> float:
    with _connect(path) as conn:
        return float(
            conn.execute("SELECT COALESCE(SUM(cost_usd), 0) FROM spend_ledger").fetchone()[0]
        )


def by_activity(path: Path | None = None, since: str | None = None) -> list[tuple[str, int, float]]:
    """(activity, calls, dollars), largest first; `since` keeps only calls at or after that UTC
    time (ISO 8601, as the ledger stores it)."""
    with _connect(path) as conn:
        return conn.execute(
            "SELECT activity, COUNT(*), SUM(cost_usd) FROM spend_ledger WHERE ts >= ? "
            "GROUP BY activity ORDER BY SUM(cost_usd) DESC",
            (since or "",),
        ).fetchall()


def token_totals(path: Path | None = None) -> dict[str, tuple[int, int, int]]:
    """Activity -> (input tokens, of which cached, output tokens)."""
    with _connect(path) as conn:
        rows = conn.execute(
            "SELECT activity, SUM(input_tokens), SUM(cached_input_tokens), SUM(output_tokens) "
            "FROM spend_ledger GROUP BY activity"
        ).fetchall()
    return {a: (int(i or 0), int(c or 0), int(o or 0)) for a, i, c, o in rows}


def activity_usd(activity: str, path: Path | None = None) -> float:
    with _connect(path) as conn:
        return float(
            conn.execute(
                "SELECT COALESCE(SUM(cost_usd), 0) FROM spend_ledger WHERE activity = ?",
                (activity,),
            ).fetchone()[0]
        )


@dataclass(frozen=True)
class Line:
    """One line of the build budget (build_budget.lines in pack.yaml)."""

    name: str
    cap_usd: float
    names: frozenset[str]  # other activity names that count here
    approval_variable: str | None = None  # set only on the reserve

    def covers(self, activity: str) -> bool:
        return (
            activity == self.name or activity.startswith(f"{self.name}-") or activity in self.names
        )


class UnknownActivity(BudgetStop):
    """A call under an activity name no budget line covers is refused, never counted nowhere."""


def budget_lines() -> list[Line]:
    return [
        Line(
            name=name,
            cap_usd=float(line["cap_usd"]),
            names=frozenset(line.get("names") or ()),
            approval_variable=line.get("approval_variable"),
        )
        for name, line in pack_config()["build_budget"]["lines"].items()
    ]


def reserve_line() -> Line:
    return next(line for line in budget_lines() if line.approval_variable)


def line_for(activity: str) -> Line:
    for line in budget_lines():
        if not line.approval_variable and activity and line.covers(activity):
            return line
    names = ", ".join(line.name for line in budget_lines() if not line.approval_variable)
    raise UnknownActivity(
        f"the ledger activity {activity!r} has no budget line in pack.yaml, so the call is "
        f"refused; set DATAPILOT_SPEND_ACTIVITY to a line ({names}) or one of its names"
    )


def _known_line(activity: str) -> Line | None:
    try:
        return line_for(activity)
    except UnknownActivity:
        return None


@dataclass(frozen=True)
class SessionLimits:
    """build_budget.session: one unattended session's own caps, on top of the lines."""

    since_variable: str
    total_usd: float
    lines: dict[str, float]


def session_limits() -> SessionLimits | None:
    found = pack_config()["build_budget"].get("session")
    if not found:
        return None
    return SessionLimits(
        since_variable=found["since_variable"],
        total_usd=float(found["total_usd"]),
        lines={name: float(cap) for name, cap in found["lines"].items()},
    )


def budget_setting(name: str) -> str:
    """A budget switch from the environment, else from .env (where the containers get it), so a
    command on the host obeys the same switch as the services. Only this one name is read."""
    if name in os.environ:
        return os.environ[name].strip()
    if not ENV_FILE.exists():
        return ""
    from dotenv import dotenv_values

    return str(dotenv_values(ENV_FILE).get(name) or "").strip()


def session_since() -> str | None:
    """The session's start as a UTC ISO time, when the environment or .env names one; else None."""
    limits = session_limits()
    value = budget_setting(limits.since_variable) if limits else ""
    if not value:
        return None
    return datetime.fromisoformat(value).astimezone(UTC).isoformat()


def line_usage(path: Path | None = None, since: str | None = None) -> dict[str, tuple[int, float]]:
    """Line name -> (calls, dollars). Rows under no line are reported as "unassigned"."""
    out: dict[str, tuple[int, float]] = {}
    for activity, calls, cost in by_activity(path, since):
        line = _known_line(activity)
        name = line.name if line else "unassigned"
        before = out.get(name, (0, 0.0))
        out[name] = (before[0] + calls, before[1] + float(cost or 0))
    return out


def reserve_used(path: Path | None = None) -> float:
    """What the lines spent past their caps, which only the reserve can have paid for."""
    usage = line_usage(path)
    return sum(
        max(0.0, usage.get(line.name, (0, 0.0))[1] - line.cap_usd)
        for line in budget_lines()
        if not line.approval_variable
    )


SWITCHED_ON = {"1", "true", "yes", "on"}


def _switched_on(variable: str) -> bool:
    return bool(variable) and (budget_setting(variable) or "0").lower() in SWITCHED_ON


def reserve_approved() -> bool:
    return _switched_on(reserve_line().approval_variable or "")


def build_budget_on() -> bool:
    """The lines, the warning, and the stop line apply only where the build's .env turns them on
    (build_budget.enabled_variable). A learner's machine leaves it off and is limited only by the
    learner's own OpenAI project limit; the ledger records every call either way."""
    return _switched_on(pack_config()["build_budget"].get("enabled_variable") or "")


def _check_session(path: Path | None, line: Line | None, activity: str, next_call: float) -> None:
    """While a session is named, its total and its per-line caps hold too, counting only this
    session. Only the build names a session, so this holds with or without the build budget
    switch."""
    since, limits = session_since(), session_limits()
    if since is None or limits is None:
        return
    if line is None:
        raise BudgetStop(f"the activity {activity!r} has no budget line, so nothing this session")
    this_session = line_usage(path, since)
    total = sum(dollars for _, dollars in this_session.values())
    if total + next_call > limits.total_usd:
        raise BudgetStop(
            f"the session total is used up: ${total:.4f} of ${limits.total_usd:.2f} this session "
            f"(since {since}); all live work stops until the owner says otherwise"
        )
    cap = limits.lines.get(line.name)
    if cap is None:
        raise BudgetStop(f"the {line.name} line has no allowance this session")
    spent = this_session.get(line.name, (0, 0.0))[1]
    if spent + next_call > cap:
        raise BudgetStop(
            f"the {line.name} line is used up this session: ${spent:.4f} of ${cap:.2f} this "
            f"session, ${max(0.0, cap - spent):.4f} left, and the next call costs about "
            f"${next_call:.4f}"
        )


def check_budget(path: Path | None = None, activity: str | None = None) -> float:
    """Before a call, with the build budget on: refuse an activity no line covers; stop when the
    next call (the line's mean call so far) would take its line past its cap, or the build past the
    stop line; the reserve is used only when the owner approved it. Logs once past the warning
    line. With it off, only a named session's limit applies."""
    activity = activity if activity is not None else get_settings().datapilot_spend_activity
    on = build_budget_on()
    line = line_for(activity) if on else _known_line(activity)
    calls, spent_line = line_usage(path).get(line.name, (0, 0.0)) if line else (0, 0.0)
    next_call = spent_line / calls if calls else 0.0
    spent = total_usd(path)
    if on and line is not None:
        _check_lines(path, line, spent, spent_line, next_call)
    _check_session(path, line, activity, next_call)
    return spent


def _check_lines(
    path: Path | None, line: Line, spent: float, spent_line: float, next_call: float
) -> None:
    global _warned
    budget = pack_config()["build_budget"]
    if spent + next_call > budget["stop_usd"] or spent >= budget["stop_usd"]:
        raise BudgetStop(
            f"build spend ${spent:.4f} reached the stop line ${budget['stop_usd']:.2f} "
            f"(budget ${budget['total_usd']:.2f}); all live work stops"
        )
    if spent_line + next_call > line.cap_usd:
        left = max(0.0, line.cap_usd - spent_line)
        reserve = reserve_line()
        reserve_left = reserve.cap_usd - reserve_used(path)
        if not reserve_approved():
            raise BudgetStop(
                f"the {line.name} line is used up: ${spent_line:.4f} of ${line.cap_usd:.2f}, "
                f"${left:.4f} left, and the next call costs about ${next_call:.4f}; the reserve "
                f"(${reserve_left:.4f} left) is used only with the owner's approval"
            )
        if next_call > reserve_left:
            raise BudgetStop(
                f"the {line.name} line and the reserve are used up: the reserve has "
                f"${max(0.0, reserve_left):.4f} left of ${reserve.cap_usd:.2f}"
            )
    if spent >= budget["warn_usd"] and not _warned:
        _warned = True
        log.warning(
            "build spend past the warning line", spent=round(spent, 4), warn=budget["warn_usd"]
        )


_INSERT = (
    "INSERT INTO spend_ledger (ts, activity, component, model, input_tokens, "
    "cached_input_tokens, output_tokens, cost_usd, run_id, cache_write_tokens, "
    "cache_write_12h_tokens, estimated, error) "
    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)"
)


def record(
    *,
    component: str,
    model: str,
    usage: Usage,
    activity: str | None = None,
    run_id: str | None = None,
    path: Path | None = None,
    estimated: bool = False,
    error: str | None = None,
) -> float:
    """Record one model call; return its cost. `estimated` marks usage counted from the request
    because the call failed without reporting any; `error` names a failed call's error type."""
    cost = cost_usd(model, usage)
    with _connect(path) as conn:
        conn.execute(
            _INSERT,
            (
                datetime.now(UTC).isoformat(),
                activity or get_settings().datapilot_spend_activity,
                component,
                model,
                usage.input_tokens,
                usage.cached_input_tokens,
                usage.output_tokens,
                cost,
                run_id,
                usage.cache_write_tokens,
                usage.cache_write_12h_tokens,
                int(estimated),
                error,
            ),
        )
    return cost


# The header a starter of live work (make demo, the live smoke check, an assignment check) sends
# with POST /events, so the worker records that job's calls under the starter's activity.
ACTIVITY_HEADER = "DataPilot-Spend-Activity"


def activity_headers() -> dict[str, str]:
    """This process's activity, for the requests that start a job."""
    return {ACTIVITY_HEADER: get_settings().datapilot_spend_activity}


def starter_activity(purpose: str, starter: str) -> str:
    """The activity of work that one starter (the console) begins in a live session: the budget
    line the session's own preflight counts under, followed by the starter, such as
    "rehearsal-console". With no such line, this process's own activity."""
    found = _known_line(f"preflight-{purpose}")
    return f"{found.name}-{starter}" if found else get_settings().datapilot_spend_activity


def usage_from_message(message: AIMessage) -> Usage:
    """LangChain's usage_metadata: cache_read is OpenAI's cached_tokens and cache_creation its
    cache_write_tokens. LangChain does not pass on the split by lifetime, and the platform never
    asks for the 12-hour lifetime, so every write counts at the default 30-minute rate."""
    meta: dict[str, Any] = message.usage_metadata or {}
    details: dict[str, Any] = meta.get("input_token_details") or {}
    return Usage(
        input_tokens=int(meta.get("input_tokens") or 0),
        cached_input_tokens=int(details.get("cache_read") or 0),
        output_tokens=int(meta.get("output_tokens") or 0),
        cache_write_tokens=int(details.get("cache_creation") or 0),
    )


def usage_from_api(usage: dict[str, Any]) -> Usage:
    """The Responses API's own usage object (usage.input_tokens_details.cached_tokens,
    cache_write_tokens, and cache_write_tokens_details.ttl_30m_tokens and ttl_12h_tokens)."""
    details: dict[str, Any] = usage.get("input_tokens_details") or {}
    by_lifetime: dict[str, Any] = details.get("cache_write_tokens_details") or {}
    written = int(details.get("cache_write_tokens") or 0)
    longer = int(by_lifetime.get("ttl_12h_tokens") or 0)
    return Usage(
        input_tokens=int(usage.get("input_tokens") or 0),
        cached_input_tokens=int(details.get("cached_tokens") or 0),
        output_tokens=int(usage.get("output_tokens") or 0),
        cache_write_tokens=written - longer,
        cache_write_12h_tokens=longer,
    )


def usage_from_error(error: BaseException, response: LLMResult | None) -> Usage | None:
    """The usage a failed call reports, when it reports any: a partial response's message, or the
    usage in the error's response body; None when neither has one."""
    for generations in response.generations if response else []:
        for generation in generations:
            message = getattr(generation, "message", None)
            if isinstance(message, AIMessage) and message.usage_metadata:
                found = usage_from_message(message)
                if found.input_tokens or found.output_tokens:
                    return found
    body = getattr(error, "body", None)
    if isinstance(body, dict):
        usage = body.get("usage") or (body.get("response") or {}).get("usage")
        if isinstance(usage, dict) and usage.get("input_tokens"):
            return usage_from_api(usage)
    return None


REJECTED_CODES = {
    "insufficient_quota",
    "context_length_exceeded",
    "invalid_request_error",
    "invalid_prompt",
    "rate_limit_exceeded",
}


def rejected_before_processing(error: BaseException) -> bool:
    """True when OpenAI refused the request before processing it (a 4xx status, or an error code
    such as insufficient_quota or context_length_exceeded): such a request is not billed."""
    status = getattr(error, "status_code", None) or getattr(
        getattr(error, "response", None), "status_code", None
    )
    if isinstance(status, int) and 400 <= status < 500:
        return True
    body = getattr(error, "body", None)
    if isinstance(body, dict):
        found = body.get("error") if isinstance(body.get("error"), dict) else body
        if found.get("code") in REJECTED_CODES or found.get("type") in REJECTED_CODES:
            return True
    return False


CHARACTERS_PER_TOKEN = 4  # OpenAI's rule of thumb for English text; used only for an estimate


def estimate_input_tokens(messages: Any, invocation: dict[str, Any] | None = None) -> int:
    """Input tokens counted from the request a failed call sent: its messages, their tool calls,
    and the tool definitions. An estimate, so the ledger marks the row `estimated`."""
    tools = (invocation or {}).get("tools")
    characters = len(json.dumps(tools, default=str)) if tools else 0
    for batch in messages or []:
        for message in batch:
            content = getattr(message, "content", message)
            text = content if isinstance(content, str) else json.dumps(content, default=str)
            calls = getattr(message, "tool_calls", None) or []
            characters += len(text) + (len(json.dumps(calls, default=str)) if calls else 0)
    return -(-characters // CHARACTERS_PER_TOKEN)  # rounded up


class SpendCallback(BaseCallbackHandler):
    """Attach to every chat model (callbacks=[SpendCallback(...)]): checks the budget before each
    call and records each call's usage after it, under `activity` when the work names one (a job
    started with the activity header) and else under DATAPILOT_SPEND_ACTIVITY."""

    raise_error = True  # a BudgetStop must stop the run, not be logged and ignored

    def __init__(
        self,
        *,
        component: str,
        model: str,
        run_id: str | None = None,
        activity: str | None = None,
    ) -> None:
        self.component = component
        self.model = model
        self.run_id = run_id
        self.activity = activity or None
        self._sent: dict[Any, int] = {}  # sent calls not yet ended -> estimated input tokens

    def on_chat_model_start(self, serialized: Any, messages: Any, **kwargs: Any) -> None:
        check_budget(activity=self.activity)
        # Only a call that passed the budget check is sent, so only it can fail after sending.
        call = kwargs.get("run_id")
        self._sent[call] = estimate_input_tokens(messages, kwargs.get("invocation_params"))

    def on_llm_error(self, error: BaseException, **kwargs: Any) -> None:
        """A sent call that failed (a timeout, a cut-off stream, a refusal) can still be billed:
        record it with the usage it reports, or else the estimate from its request; a request the
        API refused outright (rejected_before_processing) is recorded at zero. Recording never
        raises, so the call's own error is the one the run sees."""
        estimate = self._sent.pop(kwargs.get("run_id"), None)
        if estimate is None:
            return
        try:
            usage = usage_from_error(error, kwargs.get("response"))
            rejected = usage is None and rejected_before_processing(error)
            record(
                component=self.component,
                model=self.model,
                # A request OpenAI rejects before processing it is not billed: record that it
                # happened, at no cost. Anything else that failed may have been processed: estimate.
                usage=usage or Usage(0 if rejected else estimate, 0, 0),
                activity=self.activity,
                run_id=self.run_id,
                estimated=usage is None and not rejected,
                error=type(error).__name__,
            )
        except Exception as failure:
            log.warning("a failed model call could not be recorded", error=repr(failure))

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        self._sent.pop(kwargs.get("run_id"), None)
        for generations in response.generations:
            for generation in generations:
                message = getattr(generation, "message", None)
                if isinstance(message, AIMessage):
                    record(
                        component=self.component,
                        model=self.model,
                        usage=usage_from_message(message),
                        activity=self.activity,
                        run_id=self.run_id,
                    )
