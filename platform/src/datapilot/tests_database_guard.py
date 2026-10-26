"""Under pytest, every database connection reaches the tests' own Postgres, never another stack.

On 25 October 2026 the class stack's ops tables were emptied by the integration fixtures
(clean_ops: TRUNCATE ... CASCADE). The settings of that test run had fallen back to the Compose
address of the class stack, localhost:POSTGRES_PORT, since they were built while a test had the
address variables deleted and then outlived it. Checking each address where the tests set it was
not enough, so the check sits on psycopg itself: every connection opened in a process that runs
under pytest, or that a test started, is refused unless it goes to localhost on the tests' port.
The address is checked before the connection opens and again, from libpq's own report, once it
has opened, since a service file or PGHOSTADDR can send libpq somewhere the address never named.
Only the tests' port is allowed; every port a class stack may use, in this checkout or in the
checkout that holds it (an agent worktree has no .env), is refused as the tests' port.

datapilot/__init__.py installs it whenever pytest is running, so a probe test file kept outside
the tests' folder, which loads no conftest, is held to it too.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import psycopg

from datapilot.settings import REPO, Settings

TESTS_PORT = "55432"  # the Makefile's TEST_POSTGRES_PORT, Compose project datapilot-tests
TESTS_PORT_VARIABLE = "DATAPILOT_TEST_POSTGRES_PORT"
CLASS_PORT = "5432"  # compose.yaml's default for the class stack's Postgres
LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
# Keywords of psycopg's connect() that are not connection parameters.
NOT_PARAMETERS = frozenset(
    {"autocommit", "prepare_threshold", "context", "row_factory", "cursor_factory"}
)
ENV_FILE = REPO / ".env"

refused: list[str] = []  # every address refused in this process; the conftest fails the test


class NotTheTestsDatabase(psycopg.OperationalError):
    """A connection, under pytest, to an address that is not the tests' own database. Code under
    test sees it as a connection that failed; the conftest fails the test that made it."""


def under_pytest() -> bool:
    """pytest sets PYTEST_VERSION for its run, and every process a test starts inherits it."""
    return "PYTEST_VERSION" in os.environ or "pytest" in sys.modules


def class_port() -> str:
    """The class stack's Postgres port as the settings read it: POSTGRES_PORT from the shell,
    then from .env, else the Compose default."""
    return str(Settings(_env_file=ENV_FILE).postgres_port)


def other_checkouts(repo: Path | None = None) -> list[Path]:
    """The checkouts whose class stack a test run in `repo` could still reach: every enclosing
    folder that is a checkout (an agent worktree sits in the main checkout's .claude/worktrees),
    and the main checkout a git worktree's .git file names, when that path exists here (one
    written by git for Windows does not exist in Linux)."""
    repo = repo or REPO
    found = [
        parent
        for parent in repo.parents
        if (parent / "compose.yaml").is_file() and (parent / "Makefile").is_file()
    ]
    git_file = repo / ".git"
    if git_file.is_file():
        text = git_file.read_text(encoding="utf-8", errors="replace").strip()
        if text.startswith("gitdir:"):
            git_dir = repo / text.removeprefix("gitdir:").strip()  # an absolute path stays one
            common = git_dir / "commondir"
            if common.is_file():
                main = (git_dir / common.read_text(encoding="utf-8").strip()).resolve().parent
                if main.is_dir() and main != repo and main not in found:
                    found.append(main)
    return found


def class_ports(repo: Path | None = None) -> set[str]:
    """Every port a class stack may listen on: the Compose default, this checkout's POSTGRES_PORT
    (the shell, then .env), and the POSTGRES_PORT in every other checkout's .env. An agent
    worktree has no .env of its own, so the main checkout's tells it where the class stack is."""
    from dotenv import dotenv_values

    ports = {CLASS_PORT, class_port()}
    for checkout in other_checkouts(repo):
        env = checkout / ".env"
        if env.is_file():
            moved = str(dotenv_values(env).get("POSTGRES_PORT") or "").strip()
            if moved:
                ports.add(moved)
    return ports


def tests_port() -> str:
    """The tests' port: DATAPILOT_TEST_POSTGRES_PORT when set, else 55432; never a class port.
    Every connection is then refused unless it reaches localhost on exactly this port."""
    found = os.environ.get(TESTS_PORT_VARIABLE, "").strip() or TESTS_PORT
    if found in class_ports():
        raise NotTheTestsDatabase(
            f"{TESTS_PORT_VARIABLE} or the default tests' port is {found}, the port of the live "
            f"class stack (POSTGRES_PORT, {CLASS_PORT} unless a checkout's .env moves it): no "
            "test may use it"
        )
    return found


def check(conninfo: str = "", **parameters: Any) -> None:
    """Refuse, naming the address, any connection that is not localhost on the tests' port."""
    from psycopg.conninfo import conninfo_to_dict, make_conninfo

    found = conninfo_to_dict(make_conninfo(conninfo, **parameters))
    hosts = str(found.get("hostaddr") or found.get("host") or os.environ.get("PGHOST") or "")
    hosts_list = [host or "localhost" for host in hosts.split(",")]
    ports = str(found.get("port") or os.environ.get("PGPORT") or CLASS_PORT).split(",")
    if len(ports) == 1:  # libpq gives the one port named to every host
        ports = ports * len(hosts_list)
    allowed = tests_port()
    wrong = [
        f"{host}:{port}"
        for host, port in zip(hosts_list, ports, strict=False)
        if host not in LOCAL_HOSTS or port != allowed
    ]
    if wrong or len(ports) != len(hosts_list):
        where = f"{', '.join(wrong) or hosts}/{found.get('dbname', '')}"
        refused.append(where)
        raise NotTheTestsDatabase(
            f"refused a database connection to {where}: under pytest only the tests' own "
            f"database is reached (localhost:{allowed}, Compose project datapilot-tests), never "
            f"the class stack (port {class_port()}) or another stack"
        )


def connected_elsewhere(info: Any) -> str | None:
    """Where an open connection really went, when that is not localhost on the tests' port; None
    when it is the tests' own. libpq may take its address from settings check() never sees: a
    service file (PGSERVICE, service=), PGHOSTADDR, or a socket when no host is named."""
    host = str(info.host or "")
    port = str(info.port or "")
    try:
        address = str(info.hostaddr or "")
    except psycopg.NotSupportedError:  # libpq before 12 cannot say; the host name decides
        address = ""
    local = host in LOCAL_HOSTS and address in {"", "127.0.0.1", "::1"}
    if local and port == tests_port():
        return None
    return f"{host}{f' ({address})' if address and address != host else ''}:{port}/{info.dbname}"


def _refuse_connected(where: str) -> NotTheTestsDatabase:
    refused.append(where)
    return NotTheTestsDatabase(
        f"refused a database connection that libpq opened to {where}: under pytest only the "
        f"tests' own database is reached (localhost:{tests_port()}, Compose project "
        "datapilot-tests); the connection was closed before any statement ran"
    )


# psycopg's own connect functions, kept by install(); a test may stand in for them.
originals: dict[str, Any] = {}


def install() -> None:
    """Wrap psycopg's connect for every connection class, pools and checkpointers included. The
    address is checked before the connection opens (a clear message), and what libpq actually
    connected to is checked after it opens (opening one changes nothing): a connection anywhere
    else is closed and refused."""
    if getattr(psycopg.Connection.connect, "tests_database_guard", False):
        return
    originals["sync"] = psycopg.Connection.connect.__func__
    originals["async"] = psycopg.AsyncConnection.connect.__func__

    def guarded(cls: type, conninfo: str = "", **kwargs: Any) -> Any:
        check(conninfo, **{k: v for k, v in kwargs.items() if k not in NOT_PARAMETERS})
        conn = originals["sync"](cls, conninfo, **kwargs)
        where = connected_elsewhere(conn.info)
        if where is not None:
            conn.close()
            raise _refuse_connected(where)
        return conn

    async def guarded_async(cls: type, conninfo: str = "", **kwargs: Any) -> Any:
        check(conninfo, **{k: v for k, v in kwargs.items() if k not in NOT_PARAMETERS})
        conn = await originals["async"](cls, conninfo, **kwargs)
        where = connected_elsewhere(conn.info)
        if where is not None:
            await conn.close()
            raise _refuse_connected(where)
        return conn

    guarded.tests_database_guard = True  # type: ignore[attr-defined]
    guarded_async.tests_database_guard = True  # type: ignore[attr-defined]
    psycopg.Connection.connect = classmethod(guarded)  # type: ignore[assignment,method-assign]
    psycopg.AsyncConnection.connect = classmethod(guarded_async)  # type: ignore[assignment,method-assign]
    psycopg.connect = psycopg.Connection.connect  # the module's own name for it


def installed() -> bool:
    return bool(getattr(psycopg.Connection.connect, "tests_database_guard", False))
