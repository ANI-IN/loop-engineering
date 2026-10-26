"""The real stack a live check runs against: Postgres, the api, workers, the scheduler, the console.

By default the check builds the images from the tree being checked and starts its own Compose
project, datapilot-assignments, on its own host ports (DEFAULTS), with the workers scaled to the
pack's evaluation.concurrency, so it never touches the class stack (project datapilot), which may be
live. COMPOSE_PROJECT_NAME, POSTGRES_PORT, API_PORT, and CONSOLE_PORT override them exactly as they
override Compose's; the project datapilot itself is refused. With
DATAPILOT_ASSIGNMENT_STACK=running the check uses services that are already up at the configured
addresses instead. Either way it then makes sure the warehouses are seeded, a knowledge version is
active, and a live session is open: it starts one only when none is, or, with PURPOSE set (such as
PURPOSE=thursday-review), when the open one is not a session of that purpose started this Eastern
time day.

On its own Compose project the check also sets the stack's daily token count back to zero first
(reset_daily_tokens): the stack is the learner's own, and each check is already held to its own
spend cap, so one day's earlier checks never end a later check's runs at the daily token budget.
With DATAPILOT_ASSIGNMENT_STACK=running the stack may be the class stack, and its count is never
touched.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID

import httpx
import psycopg
import yaml

from datapilot import db, planted
from datapilot.assignments.report import Stop
from datapilot.config import active_pack, pack_config
from datapilot.contracts.live import LiveSession, SessionPurpose
from datapilot.loop3_events import sessions
from datapilot.loop3_events.budget import eastern_day
from datapilot.loop4_hill_climbing.pack_files import load_submodule, pack_root
from datapilot.observability.background import bounded_client, use_for_tracing
from datapilot.settings import get_settings

# The class image's tag in compose.yaml: every service built from it gets the check's own tag.
CLASS_IMAGE = "datapilot:local"
CLASS_PROJECT = "datapilot"
# The check's own project and host ports, used whenever the environment names none.
DEFAULTS = {
    "COMPOSE_PROJECT_NAME": "datapilot-assignments",
    "POSTGRES_PORT": "55433",
    "API_PORT": "8100",
    "CONSOLE_PORT": "8502",
}
STARTED_BY = "make check-assignment"
# The host ports compose.yaml gives the class stack when nothing overrides them.
_PORT_DEFAULT = re.compile(r"\$\{(\w+_PORT):-(\d+)\}")
RESET_COMMAND = "uv run python -m datapilot.assignments reset {slug}"


def class_ports(tree: Path | None = None) -> dict[str, str]:
    """POSTGRES_PORT, API_PORT, and CONSOLE_PORT as compose.yaml defaults them: the class
    stack's ports."""
    from datapilot.settings import REPO

    text = ((tree or REPO) / "compose.yaml").read_text(encoding="utf-8")
    return dict(_PORT_DEFAULT.findall(text))


def refuse_class_ports(tree: Path | None = None) -> None:
    """The check's own stack never uses a port of the class stack: a check, or the reset of its
    stack, given one would reach the class stack's Postgres or bind beside its services."""
    for name, port in class_ports(tree).items():
        if os.environ.get(name, "").strip() == port:
            raise Stop(
                f"{name}={port} is the class stack's port (compose.yaml): the live check and the "
                f"reset of its stack never use it. Leave {name} unset to use "
                f"{DEFAULTS[name]}, or give the port of the check's own Compose project."
            )


def reset_command(slug: str) -> str:
    """The reset of this check's own stack, as a command to copy: with the project and the
    Postgres port in front whenever they are not the defaults, so it resets this stack and no
    other (such as the review's datapilot-review beside datapilot-assignments)."""
    project = os.environ.get("COMPOSE_PROJECT_NAME") or DEFAULTS["COMPOSE_PROJECT_NAME"]
    port = os.environ.get("POSTGRES_PORT") or DEFAULTS["POSTGRES_PORT"]
    command = RESET_COMMAND.format(slug=slug)
    if (project, port) == (DEFAULTS["COMPOSE_PROJECT_NAME"], DEFAULTS["POSTGRES_PORT"]):
        return command
    return f"COMPOSE_PROJECT_NAME={project} POSTGRES_PORT={port} {command}"


def _host_port(ports: str) -> str | None:
    """The host port that docker ps shows published for Postgres's 5432, such as
    "127.0.0.1:55433->5432/tcp"; None when none is."""
    found = re.search(r":(\d+)->5432/tcp", ports)
    return found.group(1) if found else None


def published_postgres_port(project: str) -> str | None:
    """The host port the project's running Postgres container publishes, read from Docker;
    None when the project has no running Postgres."""
    if shutil.which("docker") is None:
        raise Stop(
            "Docker is not available, so the reset cannot confirm that the Postgres on this port "
            f"belongs to the check's own Compose project {project}; nothing was reset."
        )
    done = subprocess.run(
        [
            "docker",
            "ps",
            "--filter",
            f"label=com.docker.compose.project={project}",
            "--filter",
            "label=com.docker.compose.service=postgres",
            "--format",
            "{{.Ports}}",
        ],
        capture_output=True,
        text=True,
    )
    if done.returncode != 0:
        raise Stop(f"docker ps failed, so nothing was reset: {done.stderr.strip()[:200]}")
    for line in done.stdout.splitlines():
        if port := _host_port(line):
            return port
    return None


@dataclass(frozen=True)
class Stack:
    project: str
    api_url: str
    console_url: str
    session_id: UUID


def _with_port(url: str, port: str) -> str:
    parts = urlsplit(url)
    host = parts.hostname or "localhost"
    auth = parts.netloc.rsplit("@", 1)[0] + "@" if "@" in parts.netloc else ""
    return urlunsplit(parts._replace(netloc=f"{auth}{host}:{port}"))


def running_stack() -> bool:
    return os.environ.get("DATAPILOT_ASSIGNMENT_STACK", "").strip() == "running"


def configure(activity: str) -> None:
    """Point this process at the stack's ports and record its spend under `activity`. LangSmith
    settings go into the environment so in-process model calls are traced like the services'."""
    if not running_stack():
        for name, value in DEFAULTS.items():
            os.environ.setdefault(name, value)
    settings = get_settings()
    if port := os.environ.get("POSTGRES_PORT"):
        for name in ("owner", "app", "agent", "agent_alt"):
            url = getattr(settings, f"database_url_{name}")
            os.environ[f"DATABASE_URL_{name.upper()}"] = _with_port(url, port)
    if port := os.environ.get("API_PORT"):
        os.environ["DATAPILOT_API_URL"] = f"http://localhost:{port}"
    os.environ["DATAPILOT_SPEND_ACTIVITY"] = activity
    if key := settings.langsmith_api_key.get_secret_value():
        os.environ.setdefault("LANGSMITH_API_KEY", key)
        os.environ.setdefault("LANGSMITH_TRACING", str(settings.langsmith_tracing).lower())
        os.environ.setdefault("LANGSMITH_ENDPOINT", settings.langsmith_endpoint)
        os.environ.setdefault("LANGSMITH_PROJECT", settings.langsmith_project)
        if settings.langsmith_tracing:  # a refused upload never holds up the check or its exit
            use_for_tracing(bounded_client(api_key=key, api_url=settings.langsmith_endpoint))
    get_settings.cache_clear()


def project_name() -> str:
    project = os.environ.get("COMPOSE_PROJECT_NAME") or DEFAULTS["COMPOSE_PROJECT_NAME"]
    if project == CLASS_PROJECT:
        raise Stop(
            f"The live check never runs on the class stack (Compose project {CLASS_PROJECT}). "
            f"Leave COMPOSE_PROJECT_NAME unset to use {DEFAULTS['COMPOSE_PROJECT_NAME']}."
        )
    return project


def app_services(tree: Path) -> list[str]:
    """Every service of compose.yaml built from the class image (read, with its merge keys)."""
    compose = yaml.safe_load((tree / "compose.yaml").read_text(encoding="utf-8"))
    return [name for name, spec in compose["services"].items() if spec.get("image") == CLASS_IMAGE]


def _override(tree: Path, project: str, activity: str) -> Path:
    """A Compose override for the check: the spend activity, and its own image tag for every
    service built from the class image, so the check never retags the class stack's image.

    Every planted bug and demo aid is switched off in it. The copy's .env is a link to the
    checkout's, which a class demonstration switches flags in (sed on .env, then make up): a
    stack started while one was on judged a solution with the bug in it, such as the missing
    idempotency starting a second run for a duplicate drill-down ask. Compose gives a service's
    environment precedence over its env_file, so the flags in .env never reach the check's stack.
    """
    lines = ["services:"]
    for service in app_services(tree):
        lines.append(f"  {service}:")
        lines.append(f"    image: {project}-app:local")
        lines.append("    environment:")
        lines.append(f'      DATAPILOT_SPEND_ACTIVITY: "{activity}"')
        # nor can a request switch one on: the api takes no planted header without demo controls
        lines.append('      DATAPILOT_ALLOW_DEMO_CONTROLS: "0"')
        lines.extend(f'      {flag}: "0"' for flag in planted.flags())
    folder = Path(tempfile.mkdtemp(prefix="datapilot-check-"))
    path = folder / "compose.check.yaml"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def compose_up(tree: Path, activity: str, say) -> str:
    if shutil.which("docker") is None:
        raise Stop(
            "Docker is not available. The live check brings up the real stack with Docker "
            "Compose (setup/ lists the free options); with the services already running, set "
            "DATAPILOT_ASSIGNMENT_STACK=running."
        )
    project = project_name()
    refuse_class_ports(tree)
    override = _override(tree, project, activity)
    files = ["-f", str(tree / "compose.yaml"), "-f", str(override)]
    workers = str(int(pack_config()["evaluation"]["concurrency"]))
    say(f"Stack: building and starting the Compose project {project} from {tree}")
    for args in (
        ["build"],
        ["up", "--detach", "--wait", "--scale", f"worker={workers}"],
    ):
        done = subprocess.run(
            ["docker", "compose", "-p", project, "--project-directory", str(tree), *files, *args],
            cwd=tree,
            capture_output=True,
            text=True,
        )
        if done.returncode != 0:
            tail = "\n".join((done.stdout + done.stderr).strip().splitlines()[-15:])
            raise Stop(f"docker compose {args[0]} failed:\n{tail}")
    return project


def wait_for_api(url: str, seconds: float = 90) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            if httpx.get(f"{url}/health", timeout=5).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(1)
    raise Stop(f"The api at {url} did not answer /health within {seconds:.0f} seconds.")


def ensure_seeded(say) -> None:
    with db.connect(db.Role.OWNER) as conn:
        row = conn.execute("SELECT to_regclass('warehouse.orders') AS t").fetchone()
        seeded = (
            row["t"] is not None
            and conn.execute("SELECT EXISTS (SELECT 1 FROM warehouse.orders) AS e").fetchone()["e"]
        )
    if seeded:
        return
    seeding = load_submodule("data_generator", "seed")
    for warehouse in seeding.DATABASES:
        say(f"Stack: seeding {warehouse} (about a minute; this happens once per database)")
        seeding.seed(warehouse)


def ensure_knowledge() -> str:
    """The active knowledge version; the pack's starting version (v1) when none is active."""
    with db.connect(db.Role.APP) as conn:
        pack = active_pack()
        row = conn.execute(
            "SELECT version FROM ops.knowledge_versions WHERE pack = %s AND status = 'active'",
            (pack,),
        ).fetchone()
        if row:
            return str(row["version"])
        text = (pack_root() / "knowledge" / "v1.yaml").read_text(encoding="utf-8")
        conn.execute(
            "INSERT INTO ops.knowledge_versions "
            "(pack, version, yaml, status, created_by, activated_at) "
            "VALUES (%s, 'v1', %s, 'active', 'pack', now()) ON CONFLICT (pack, version) "
            "DO UPDATE SET status = 'active', activated_at = now()",
            (pack, text),
        )
        conn.commit()
    return "v1"


def session_purpose() -> SessionPurpose | None:
    """The purpose PURPOSE names (make passes PURPOSE=... on its command line to the check), or
    None when it is unset."""
    value = os.environ.get("PURPOSE", "").strip()
    if not value:
        return None
    try:
        return SessionPurpose(value)
    except ValueError:
        names = ", ".join(p.value for p in SessionPurpose)
        raise Stop(f"PURPOSE={value} is not a session purpose; use one of {names}.") from None


def keeps_open_session(
    open_session: LiveSession | None, purpose: SessionPurpose | None, now: datetime | None = None
) -> bool:
    """Whether the check runs in the open session: always when no purpose is asked for; with a
    purpose, only when the open session has it and started this Eastern time day, so a review never
    runs in an old session of rehearsal days earlier."""
    if open_session is None:
        return False
    if purpose is None:
        return True
    return open_session.purpose == purpose and eastern_day(open_session.started_at) == eastern_day(
        now
    )


def ensure_session() -> UUID:
    purpose = session_purpose()
    with db.connect(db.Role.APP) as conn:
        session = sessions.open_session(conn)
    if keeps_open_session(session, purpose):
        assert session is not None
        return session.session_id
    if session is not None and running_stack():
        raise Stop(
            f"PURPOSE={purpose} asks for a new live session, but with "
            "DATAPILOT_ASSIGNMENT_STACK=running the stack may be the class stack, whose open "
            "session the check never ends: start the session there with make preflight."
        )
    zone = time.strftime("%Z") or "UTC"
    return sessions.start_session(
        purpose or SessionPurpose.DEVELOPMENT, STARTED_BY, zone
    ).session_id


def reset_daily_tokens(project: str) -> int:
    """Set this Eastern time day's token count of the check's own stack back to zero; returns the
    tokens it held. Refused for the class project and for services already running."""
    if project == CLASS_PROJECT or running_stack():
        raise Stop("The check resets the daily token count of its own Compose project only.")
    with db.connect(db.Role.APP) as conn:
        row = conn.execute(
            "SELECT tokens_used FROM ops.budgets WHERE day = %s", (eastern_day(),)
        ).fetchone()
        conn.execute("UPDATE ops.budgets SET tokens_used = 0 WHERE day = %s", (eastern_day(),))
        conn.commit()
    return int(row["tokens_used"]) if row else 0


def reset_check_stack(slug: str, activity: str) -> list[str]:
    """`python -m datapilot.assignments reset <slug>`: the recovery for the check's own stack. It
    clears the section's run state and releases the kill switch as `make reset` does for the class
    stack, and sets the daily token count back to zero, on the check's Compose project and ports
    (the same COMPOSE_PROJECT_NAME and POSTGRES_PORT the check reads), never on the class stack: it
    refuses the class stack's ports, and any port the project's own Postgres does not publish."""
    if running_stack():
        raise Stop(
            "With DATAPILOT_ASSIGNMENT_STACK=running the services are not the check's own stack: "
            "reset them where they run."
        )
    configure(activity)
    project = project_name()
    refuse_class_ports()
    port = os.environ.get("POSTGRES_PORT", DEFAULTS["POSTGRES_PORT"])
    published = published_postgres_port(project)
    if published != port:
        where = f"publishes Postgres on port {published}" if published else "runs no Postgres"
        raise Stop(
            f"Not reset: the Compose project {project} {where}, not on port {port}, so that port "
            "belongs to another stack. Give the project and the port the check used, as the "
            "check prints them, such as COMPOSE_PROJECT_NAME=datapilot-review POSTGRES_PORT=55434."
        )
    from datapilot.loop3_events.commands import reset

    try:
        done = reset(slug)
        held = reset_daily_tokens(project)
    except psycopg.OperationalError as error:
        raise Stop(
            f"The check's stack ({project}, Postgres on port {port}) is not reachable: "
            f"{str(error).strip()[:200]}. Its services are up while a check runs and after one."
        ) from None
    return [
        f"Reset the check's own stack, Compose project {project} (Postgres on port {port}), "
        "never the class stack:",
        *done.lines(),
        f"daily token count set back to 0 (it held {held:,} today)",
    ]


CHECK = "The live check"


def refuse_planted(what: str = CHECK, env_file: Path | None = None) -> None:
    """Before anything starts: Stop while .env or this process's environment switches a planted
    flag on. The check's own stack switches every flag off, but a check that silently differs from
    what .env says hides the planted half a class demonstration left on; and the runs a check makes
    in this process (Assignment 4's benchmark) read this environment."""
    on = planted.switched_on(env_file=env_file or planted.ENV_FILE, environ=os.environ)
    if reason := planted.refusal(on, what):
        raise Stop(reason)


# The services that report their flags as they start (planted.report_service).
REPORTING = ("api", "worker", "scheduler", "hill-climbing-runner")
StartTimes = Callable[[], "dict[str, datetime] | None"]


def container_starts(project: str) -> dict[str, datetime] | None:
    """When each reporting service's newest container of the Compose project started (UTC), or
    None when Docker cannot say (no Docker, or no container of that project)."""
    if shutil.which("docker") is None:
        return None
    label = f"label=com.docker.compose.project={project}"
    ids = subprocess.run(
        ["docker", "ps", "-q", "--filter", label], capture_output=True, text=True, check=False
    ).stdout.split()
    if not ids:
        return None
    found = subprocess.run(["docker", "inspect", *ids], capture_output=True, text=True, check=False)
    starts: dict[str, datetime] = {}
    for container in json.loads(found.stdout or "[]"):
        service = (container["Config"].get("Labels") or {}).get("com.docker.compose.service")
        stamp = re.sub(r"(\.\d{6})\d+", r"\1", container["State"]["StartedAt"])
        started = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        if service in REPORTING and (service not in starts or started > starts[service]):
            starts[service] = started
    return starts


def refuse_planted_services(
    say,
    starts: StartTimes = lambda: None,
    *,
    wait_seconds: float = 60.0,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    """Once the stack is up: Stop while any of its services reports a planted flag on at its start
    (ops.service_planted), such as the class stack's with DATAPILOT_ASSIGNMENT_STACK=running. Only a
    report written since the service's container started counts: an older row is the one before a
    restart (a demo's restart with a flag reports after the database and the probe), so the check
    waits for each new report, up to `wait_seconds`, and stops if one never comes. The line it
    prints is the check's record that no flag was on."""
    deadline = time.monotonic() + wait_seconds
    while True:
        with db.connect(db.Role.APP) as conn:
            reports = planted.service_reports(conn)
        started = starts()
        stale = sorted(
            service
            for service, at in (started or {}).items()
            if service not in reports or reports[service][1] < at
        )
        if not stale or time.monotonic() >= deadline:
            break
        sleep(1.0)
    if stale:
        raise Stop(
            f"The live check does not start: {', '.join(stale)} has not reported its planted flags "
            f"since it started (after {wait_seconds:.0f} seconds). Wait until the service is "
            "ready (docker compose ps), then run the check again."
        )
    services = {service: flags for service, (flags, _at) in reports.items() if flags}
    if reason := planted.refusal(planted.switched_on(services=services), CHECK):
        raise Stop(reason)
    say("Planted flags: none on, in .env, in this process, or in the stack's services")
    if started is None:
        say(
            "Planted flags: the services' start times could not be read from Docker, so each "
            "service's latest report was taken as it stands"
        )


def bring_up(tree: Path, activity: str, say) -> Stack:
    configure(activity)
    settings = get_settings()
    if running_stack():
        project = "already running"
        say("Stack: using the services already running (DATAPILOT_ASSIGNMENT_STACK=running)")
    else:
        project = compose_up(tree, activity, say)
    wait_for_api(settings.datapilot_api_url)
    try:
        db.wait_until_ready(db.Role.OWNER, timeout_s=30)
    except psycopg.OperationalError as error:
        raise Stop(f"Postgres is not reachable as the owner role: {error}") from None
    compose_project = os.environ.get("COMPOSE_PROJECT_NAME") or CLASS_PROJECT
    if not running_stack():
        compose_project = project
    refuse_planted_services(say, lambda: container_starts(compose_project))
    ensure_seeded(say)
    version = ensure_knowledge()
    session_id = ensure_session()
    if not running_stack():
        held = reset_daily_tokens(project)
        if held:
            say(
                f"Stack: the daily token count of {project} was {held:,} today; set back to 0, "
                "since this check is held to its own spend cap"
            )
    console = f"http://localhost:{os.environ.get('CONSOLE_PORT', DEFAULTS['CONSOLE_PORT'])}"
    say(
        f"Stack: api {settings.datapilot_api_url}, console {console}, active knowledge {version}, "
        f"live session {session_id}"
    )
    return Stack(project, settings.datapilot_api_url, console, session_id)
