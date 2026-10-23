"""Preflight: the checks before any class, rehearsal, review, or development session, then the start
of its live session (`make preflight PURPOSE=...`, the only code path that starts one).

1. Services: the selected pack (DATAPILOT_PACK), Postgres with the ops migrations, the pack's data
   as the agent's role sees it (preflight.data_check in pack.yaml), the api, and the console.
2. The OpenAI key: one model lookup, no tokens; a missing or rejected key stops here.
3. The starting knowledge is installed (v1 active when no version is).
4. The drift canary (preflight.canary in pack.yaml): three easy questions must pass and two trap
   questions must still fail under the starting knowledge. The class model has no dated snapshot,
   so a trap that passes means it moved and calibration must run again.
5. A new live session with the given purpose starts, ending the previous one.
"""

from __future__ import annotations

import getpass
import os
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx
from psycopg import sql

from datapilot import db
from datapilot.config import UnknownPack, active_pack, pack_config
from datapilot.contracts import BenchmarkItem, Split
from datapilot.contracts.live import LiveSession, SessionPurpose
from datapilot.loop2_verification.config import VerificationConfig
from datapilot.loop2_verification.executor import ExecutionError, Executor
from datapilot.loop4_hill_climbing import versions
from datapilot.loop4_hill_climbing.experiment import ExperimentRunner, RunTracer, Target
from datapilot.loop4_hill_climbing.measurement import Scheme
from datapilot.loop4_hill_climbing.sql_runner import executors
from datapilot.settings import Settings

NOT_A_SESSION = uuid.UUID(int=0)  # canary runs belong to no live session

KEY_NOT_ACCEPTED = "Your OpenAI key was not accepted. Check it with the operations team."
TRAP_PASSED = (
    "The drift canary failed: a trap question passed under the starting knowledge, so the model "
    "no longer behaves as calibrated. Calibration must run again before class."
)
EASY_FAILED = (
    "The drift canary failed: an easy question failed under the starting knowledge. Check the "
    "model and the warehouse, then run preflight again."
)
APPLIED = "SELECT count(*) AS n FROM ops.schema_migrations"


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str

    def line(self) -> str:
        return f"{'ok' if self.ok else 'x '} {self.name}: {self.detail}"


@dataclass
class CanaryRun:
    item_id: str
    kind: str  # "easy" or "trap"
    passed: bool
    reason: str
    trace_url: str | None

    @property
    def as_expected(self) -> bool:
        return self.passed if self.kind == "easy" else not self.passed


@dataclass
class Preflight:
    checks: list[Check] = field(default_factory=list)
    canary: list[CanaryRun] = field(default_factory=list)
    session: LiveSession | None = None
    model_id: str | None = None
    stopped: str | None = None  # the sentence that stopped preflight


class PackHasNoPreflight(KeyError):
    pass


def preflight_section(cfg: dict[str, Any]) -> dict[str, Any]:
    section = cfg.get("preflight")
    if not section:
        raise PackHasNoPreflight(f"pack {cfg['name']} has no preflight section in its pack.yaml")
    return dict(section)


def canary_ids(cfg: dict[str, Any] | None = None) -> dict[str, list[str]]:
    """preflight.canary of the selected pack: its own easy and trap item ids."""
    cfg = cfg or pack_config()
    canary = preflight_section(cfg).get("canary") or {}
    if not canary.get("easy") or not canary.get("traps"):
        raise PackHasNoPreflight(f"pack {cfg['name']}: preflight.canary needs easy and traps ids")
    return {"easy": list(canary["easy"]), "traps": list(canary["traps"])}


@dataclass(frozen=True)
class DataCheck:
    """preflight.data_check: a table in the allowed schema whose rows the agent's role must see."""

    schema: str
    table: str
    rows_are: str  # what one row is, for the check line ("orders")

    @classmethod
    def from_pack(cls, cfg: dict[str, Any] | None = None) -> DataCheck:
        cfg = cfg or pack_config()
        found = preflight_section(cfg).get("data_check") or {}
        schema, _, table = str(found.get("table", "")).partition(".")
        if not table or schema != cfg["databases"]["allowed_schema"]:
            raise PackHasNoPreflight(
                f"pack {cfg['name']}: preflight.data_check.table must be schema.table "
                "inside databases.allowed_schema"
            )
        return cls(schema, table, str(found.get("rows_are") or "rows"))

    @property
    def qualified(self) -> str:
        return f"{self.schema}.{self.table}"

    def query(self) -> str:
        """The count, with the table's name quoted as identifiers, never pasted in."""
        quoted = sql.SQL("SELECT count(*) AS n FROM {}").format(
            sql.Identifier(self.schema, self.table)
        )
        return quoted.as_string()

    def check(self, executor: Executor | None = None) -> Check:
        """Through the executor, as the agent's role on the agent's database: the rows the analyst
        will read."""
        run = executor or executors(VerificationConfig.from_pack())["warehouse"]
        try:
            rows = int(run.run(self.query()).rows[0][0])
        except Exception as error:
            reason = error.message if isinstance(error, ExecutionError) else type(error).__name__
            detail = f"{self.qualified} is not readable as the agent's role: {reason}"
            return Check("data", False, detail)
        return Check("data", rows > 0, f"{rows:,} {self.rows_are} in {self.qualified}")


def service_checks(
    settings: Settings, client: httpx.Client | None = None, data: DataCheck | None = None
) -> list[Check]:
    try:  # the pack's own checks must exist before any of them runs
        canary_ids()
        data = data or DataCheck.from_pack()
        checks = [Check("pack", True, active_pack())]
    except (PackHasNoPreflight, UnknownPack) as error:
        checks = [Check("pack", False, str(error.args[0]))]
    try:
        with db.connect(db.Role.OWNER) as conn:
            applied = conn.execute(APPLIED).fetchone()["n"]
        expected = len(db.migration_files())
        checks.append(Check("postgres", applied == expected, f"{applied} of {expected} migrations"))
    except Exception as error:
        checks.append(Check("postgres", False, f"not reachable: {type(error).__name__}"))
    if data is not None:
        checks.append(data.check())
    http = client or httpx.Client(timeout=5)
    for name, url in (
        ("api", f"{settings.datapilot_api_url.rstrip('/')}/health"),
        ("console", settings_console_url(settings)),
    ):
        try:
            status = http.get(url).status_code
            checks.append(Check(name, status == 200, f"HTTP {status} from {url}"))
        except httpx.HTTPError as error:
            checks.append(Check(name, False, f"not reachable at {url}: {type(error).__name__}"))
    return checks


def settings_console_url(settings: Settings) -> str:
    """The console sits beside the api on the console port (CONSOLE_PORT, 8501 by default)."""
    host = httpx.URL(settings.datapilot_api_url).host
    return f"http://{host}:{os.environ.get('CONSOLE_PORT', '8501')}/"


def key_check(settings: Settings, lookup: Callable[[str, str], str] | None = None) -> Check:
    """Look the model up with the key (no tokens). The detail is the model id the API returns."""
    key = settings.openai_api_key.get_secret_value()
    if not key:
        return Check("openai key", False, KEY_NOT_ACCEPTED)
    try:
        model_id = (lookup or openai_model_lookup)(key, settings.agent_model)
    except PermissionError:
        return Check("openai key", False, KEY_NOT_ACCEPTED)
    except LookupError:  # the key works, but its project cannot use the class model
        detail = f"{KEY_NOT_ACCEPTED} The model {settings.agent_model} is not available to it."
        return Check("openai key", False, detail)
    except Exception as error:
        return Check("openai key", False, f"OpenAI could not be reached: {type(error).__name__}")
    return Check("openai key", True, model_id)


def openai_model_lookup(key: str, model: str) -> str:
    import openai

    try:
        return openai.OpenAI(api_key=key).models.retrieve(model).id
    except (openai.AuthenticationError, openai.PermissionDeniedError) as error:
        raise PermissionError("key not accepted") from error
    except openai.NotFoundError as error:
        raise LookupError(f"{model} is not available to this key") from error


def run_canary(
    target: Target,
    evaluator: Any,
    items: Sequence[BenchmarkItem],
    ids: dict[str, list[str]],
    tracer: RunTracer | None = None,
) -> list[CanaryRun]:
    """Each canary question once under the starting knowledge, concurrently."""
    by_id = {i.id: i for i in items}
    kinds = {item_id: "easy" for item_id in ids["easy"]} | {t: "trap" for t in ids["traps"]}
    chosen = [by_id[i].model_copy(update={"split": Split.DEV}) for i in kinds]
    # five runs, each shown with its trace link: a check, not a benchmark experiment, so all traced
    runner = ExperimentRunner(target, evaluator, Scheme(), len(chosen), tracer, trace_sample_rate=1)
    result = runner.run(chosen, versions.STARTING_VERSION, session_id=NOT_A_SESSION)
    return [
        CanaryRun(
            item_id,
            kind,
            result.results[item_id].passed,
            result.results[item_id].reason,
            (result.trace_links.get(item_id) or [None])[0],
        )
        for item_id, kind in kinds.items()
    ]


def preflight(
    purpose: SessionPurpose,
    settings: Settings,
    *,
    canary: Callable[[], list[CanaryRun]],
    start_session: Callable[[SessionPurpose, str, str], LiveSession],
    services: Callable[[], list[Check]],
    key: Callable[[], Check],
    install: Callable[[], list[str]],
) -> Preflight:
    report = Preflight()
    report.checks = services()
    if not all(c.ok for c in report.checks):
        report.stopped = "A service is not ready: run make up, then preflight again."
        return report
    found = key()
    report.checks.append(found)
    if not found.ok:
        report.stopped = found.detail
        return report
    report.model_id = found.detail
    added = install()
    report.checks.append(
        Check("knowledge", True, f"installed {', '.join(added)}" if added else "already installed")
    )
    report.canary = canary()
    if any(r.kind == "trap" and r.passed for r in report.canary):
        report.stopped = TRAP_PASSED
        return report
    if any(r.kind == "easy" and not r.passed for r in report.canary):
        report.stopped = EASY_FAILED
        return report
    report.session = start_session(purpose, getpass.getuser(), local_zone())
    return report


def local_zone() -> str:
    return os.environ.get("TZ") or str(datetime.now(UTC).astimezone().tzinfo)
