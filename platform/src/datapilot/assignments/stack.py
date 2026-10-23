"""The real stack a live check runs against: Postgres, the api, workers, the scheduler, the console.

By default the check builds the images from the tree being checked and starts its own Compose
project, datapilot-assignments, on its own host ports (DEFAULTS), with the workers scaled to the
pack's evaluation.concurrency, so it never touches the class stack (project datapilot), which may be
live. COMPOSE_PROJECT_NAME, POSTGRES_PORT, API_PORT, and CONSOLE_PORT override them exactly as they
override Compose's; the project datapilot itself is refused. With
DATAPILOT_ASSIGNMENT_STACK=running the check uses services that are already up at the configured
addresses instead. Either way it then makes sure the warehouses are seeded, a knowledge version is
active, and a live session is open (it starts one only when none is).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID

import httpx
import psycopg
import yaml

from datapilot import db
from datapilot.assignments.report import Stop
from datapilot.config import active_pack, pack_config
from datapilot.contracts.live import SessionPurpose
from datapilot.loop3_events import sessions
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
    service built from the class image, so the check never retags the class stack's image."""
    lines = ["services:"]
    for service in app_services(tree):
        lines.append(f"  {service}:")
        lines.append(f"    image: {project}-app:local")
        lines.append("    environment:")
        lines.append(f'      DATAPILOT_SPEND_ACTIVITY: "{activity}"')
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


def ensure_session() -> UUID:
    with db.connect(db.Role.APP) as conn:
        session = sessions.open_session(conn)
    if session is not None:
        return session.session_id
    zone = time.strftime("%Z") or "UTC"
    return sessions.start_session(SessionPurpose.DEVELOPMENT, STARTED_BY, zone).session_id


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
    ensure_seeded(say)
    version = ensure_knowledge()
    session_id = ensure_session()
    console = f"http://localhost:{os.environ.get('CONSOLE_PORT', DEFAULTS['CONSOLE_PORT'])}"
    say(
        f"Stack: api {settings.datapilot_api_url}, console {console}, active knowledge {version}, "
        f"live session {session_id}"
    )
    return Stack(project, settings.datapilot_api_url, console, session_id)
