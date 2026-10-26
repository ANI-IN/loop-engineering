"""No test reaches any database but its own (session 6, round 2: the class stack's ops tables were
emptied by TRUNCATE on 25 October 2026, 18:46 UTC, and its one session was a test's).

The route: settings built while a test had the database address variables deleted fell back to
localhost:POSTGRES_PORT, the class stack, and stayed in the settings cache after the test, so the
integration fixtures of later tests (clean_ops: TRUNCATE ... CASCADE) ran there. The reproduction
uses a fake class port, 59999, and opens no connection. Zero tokens, no database.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace

import psycopg
import pytest
import stack_for_tests

from datapilot import config, db, tests_database_guard
from datapilot.settings import REPO, Settings, get_settings
from datapilot.tests_database_guard import NotTheTestsDatabase

ADDRESSES = (
    "DATABASE_URL_OWNER",
    "DATABASE_URL_APP",
    "DATABASE_URL_AGENT",
    "DATABASE_URL_AGENT_ALT",
    "DATABASE_URL_SUPERUSER",
    "POSTGRES_PORT",
)
pytestmark = pytest.mark.security  # in make test-security's selection

FAKE_CLASS_PORT = "59999"  # nothing listens here; it stands in for the class stack's 5432


@pytest.fixture
def fake_class_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A .env that moves the class stack to the fake port, read by the settings and the guard."""
    env = tmp_path / ".env"
    env.write_text(f"POSTGRES_PORT={FAKE_CLASS_PORT}\n", encoding="utf-8")
    monkeypatch.setitem(Settings.model_config, "env_file", env)
    monkeypatch.setattr(tests_database_guard, "ENV_FILE", env)
    return env


@pytest.fixture
def refusals() -> Iterator[list[str]]:
    """The guard's refusals during the test, removed so the conftest does not fail it for them."""
    start = len(tests_database_guard.refused)
    seen: list[str] = []
    yield seen
    seen.extend(tests_database_guard.refused[start:])
    del tests_database_guard.refused[start:]


def _tests_url(**changes: str) -> str:
    port = changes.pop("port", tests_database_guard.tests_port())
    host = changes.pop("host", "localhost")
    return f"postgresql://datapilot_owner:datapilot_owner@{host}:{port}/datapilot"


def test_the_old_route_settings_cached_without_the_addresses_reach_the_class_port(
    fake_class_env: Path, monkeypatch: pytest.MonkeyPatch, refusals: list[str]
) -> None:
    get_settings.cache_clear()
    with monkeypatch.context() as during:  # what test_settings_ports' fixture did
        for name in ADDRESSES:
            during.delenv(name, raising=False)
        config.active_pack()  # load_submodule's first call, which filled the empty cache
    # The test is over and the environment is back, but the cached settings are not.
    assert os.environ["DATABASE_URL_OWNER"].endswith(f":{stack_for_tests.port()}/datapilot")
    assert db.url_for(db.Role.OWNER).endswith(f"@localhost:{FAKE_CLASS_PORT}/datapilot")

    # Without the guard, clean_ops' connection goes to the class port.
    opened: list[str] = []

    def unguarded(conninfo: str, **_kwargs: object) -> None:
        opened.append(conninfo)
        raise psycopg.OperationalError("not opened in a test")

    with monkeypatch.context() as old:
        old.setattr(psycopg, "connect", unguarded)
        with pytest.raises(psycopg.OperationalError), db.connect(db.Role.OWNER):
            pass
    assert opened and opened[0].endswith(f"@localhost:{FAKE_CLASS_PORT}/datapilot")

    # With it, the connection is refused before it opens, naming the address.
    refused = pytest.raises(NotTheTestsDatabase, match=f"localhost:{FAKE_CLASS_PORT}/datapilot")
    with refused, db.connect(db.Role.OWNER):
        pass
    assert tests_database_guard.refused[-1] == f"localhost:{FAKE_CLASS_PORT}/datapilot"
    get_settings.cache_clear()


@pytest.mark.parametrize(
    "address",
    [
        _tests_url(port="5432"),
        _tests_url(port=FAKE_CLASS_PORT),
        _tests_url(port="55433"),  # the assignments stack
        _tests_url(host="db.internal", port=tests_database_guard.TESTS_PORT),
        "host=/var/run/postgresql dbname=datapilot",
        "dbname=datapilot user=datapilot_owner",  # no port: libpq's default, 5432
    ],
    ids=["class", "class-moved", "assignments", "remote", "socket", "no-port"],
)
def test_the_guard_refuses_every_address_but_the_tests_own(
    address: str, fake_class_env: Path, refusals: list[str]
) -> None:
    with pytest.raises(NotTheTestsDatabase, match="refused a database connection to"):
        tests_database_guard.check(address)
    tests_database_guard.check(_tests_url())  # the tests' own passes


def test_psycopg_connect_and_its_keyword_parameters_are_checked(
    fake_class_env: Path, refusals: list[str]
) -> None:
    assert tests_database_guard.installed()
    with pytest.raises(NotTheTestsDatabase, match="localhost:5432/datapilot"):
        psycopg.connect(_tests_url(), port=5432)
    with pytest.raises(NotTheTestsDatabase, match=f"localhost:{FAKE_CLASS_PORT}"):
        psycopg.Connection.connect(_tests_url(port=FAKE_CLASS_PORT))

    async def asynchronous() -> None:
        await psycopg.AsyncConnection.connect(_tests_url(port="5432"))

    with pytest.raises(NotTheTestsDatabase, match="localhost:5432"):
        asyncio.run(asynchronous())


def test_pgport_counts_when_the_address_names_no_port(
    fake_class_env: Path, monkeypatch: pytest.MonkeyPatch, refusals: list[str]
) -> None:
    monkeypatch.setenv("PGPORT", "5432")
    with pytest.raises(NotTheTestsDatabase):
        tests_database_guard.check("host=localhost dbname=datapilot")
    monkeypatch.setenv("PGPORT", tests_database_guard.tests_port())
    tests_database_guard.check("host=localhost dbname=datapilot")


def test_the_tests_port_may_not_be_the_class_stacks_port_from_the_settings(
    fake_class_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(stack_for_tests.PORT_VARIABLE, FAKE_CLASS_PORT)  # .env's POSTGRES_PORT
    with pytest.raises(RuntimeError, match=f"live stack's port {FAKE_CLASS_PORT}"):
        stack_for_tests.port()
    with pytest.raises(NotTheTestsDatabase, match="port of the live class stack"):
        tests_database_guard.tests_port()
    monkeypatch.setenv("POSTGRES_PORT", "55432")  # the shell moves the class stack to it
    monkeypatch.delenv(stack_for_tests.PORT_VARIABLE)
    with pytest.raises(RuntimeError, match="live stack's port 55432"):
        stack_for_tests.port()


def _without_addresses() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if k not in ADDRESSES}


@pytest.mark.slow
def test_a_probe_outside_the_tests_folder_is_held_to_the_tests_database(tmp_path: Path) -> None:
    """A test file outside platform/tests loads no conftest, so nothing points its settings at
    the tests' database: the package's own guard refuses the class port all the same."""
    probe = tmp_path / "test_probe.py"
    probe.write_text(
        "import pytest\n"
        "from datapilot import db, tests_database_guard\n"
        "from datapilot.settings import Settings\n\n"
        "Settings.model_config['env_file'] = None  # the shell alone, as with no .env\n\n"
        "def test_probe():\n"
        "    assert db.url_for(db.Role.OWNER).endswith(':59999/datapilot')\n"
        "    with pytest.raises(tests_database_guard.NotTheTestsDatabase, match='59999'):\n"
        "        with db.connect(db.Role.OWNER):\n"
        "            pass\n",
        encoding="utf-8",
    )
    env = {**_without_addresses(), "POSTGRES_PORT": FAKE_CLASS_PORT, "PYTHONUTF8": "1"}
    done = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", str(probe)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stdout[-2000:] + done.stderr[-2000:]
    assert "1 passed" in done.stdout


def test_outside_pytest_the_guard_is_not_installed() -> None:
    env = {k: v for k, v in os.environ.items() if k != "PYTEST_VERSION"}
    code = "import datapilot.db, psycopg; from datapilot import tests_database_guard as g; "
    code += "print(g.installed())"
    done = subprocess.run(
        [sys.executable, "-c", code], env=env, capture_output=True, text=True, check=True
    )
    assert done.stdout.strip() == "False"


def test_the_next_tests_settings_are_the_tests_database() -> None:
    """True in any test; the next test runs it right after the seeder test, as on 25 October."""
    assert db.url_for(db.Role.OWNER).endswith(f":{stack_for_tests.port()}/datapilot")


@pytest.mark.slow
def test_settings_cached_during_a_test_never_reach_the_next_one() -> None:
    """The order of 25 October: the seeder test (its fixture deletes the addresses, and it fills
    the settings cache), then a test that reads the database address."""
    here = Path(__file__).relative_to(REPO).as_posix()
    nodes = [
        "platform/tests/unit/test_settings_ports.py::"
        "test_the_seeder_reads_the_superuser_address_from_env",
        f"{here}::test_the_next_tests_settings_are_the_tests_database",
    ]
    done = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *nodes],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stdout[-2000:]
    assert "2 passed" in done.stdout


def _checkout(folder: Path, env: str | None = None) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "compose.yaml").write_text("name: datapilot\n", encoding="utf-8")
    (folder / "Makefile").write_text("", encoding="utf-8")
    if env is not None:
        (folder / ".env").write_text(env, encoding="utf-8")
    return folder


def test_a_worktree_without_a_env_file_knows_the_class_port_of_the_checkout_holding_it(
    tmp_path: Path, fake_class_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The security review of 26 October, round 3: an agent worktree has no .env, so the guard
    took the class port to be 5432 there while the main checkout had moved it to 55432."""
    main = _checkout(tmp_path / "main", f"POSTGRES_PORT={tests_database_guard.TESTS_PORT}\n")
    worktree = _checkout(main / ".claude" / "worktrees" / "agent-0123abcd")
    assert tests_database_guard.other_checkouts(worktree) == [main]
    assert tests_database_guard.TESTS_PORT in tests_database_guard.class_ports(worktree)

    monkeypatch.setattr(tests_database_guard, "REPO", worktree)
    monkeypatch.delenv(stack_for_tests.PORT_VARIABLE, raising=False)
    with pytest.raises(NotTheTestsDatabase, match="port of the live class stack"):
        tests_database_guard.tests_port()
    with pytest.raises(RuntimeError, match="live stack's port 55432"):
        stack_for_tests.port()
    monkeypatch.setenv(stack_for_tests.PORT_VARIABLE, "55440")  # the tests' settings move it
    assert tests_database_guard.tests_port() == "55440"


def test_a_git_worktree_elsewhere_finds_its_main_checkout_through_its_git_file(
    tmp_path: Path, fake_class_env: Path
) -> None:
    main = _checkout(tmp_path / "main", "POSTGRES_PORT=55450\n")
    (main / ".git" / "worktrees" / "elsewhere").mkdir(parents=True)
    (main / ".git" / "worktrees" / "elsewhere" / "commondir").write_text("../..\n", "utf-8")
    worktree = _checkout(tmp_path / "elsewhere")
    gitdir = (main / ".git" / "worktrees" / "elsewhere").as_posix()
    (worktree / ".git").write_text(f"gitdir: {gitdir}\n", encoding="utf-8")
    assert tests_database_guard.other_checkouts(worktree) == [main.resolve()]
    assert "55450" in tests_database_guard.class_ports(worktree)
    # A path git for Windows wrote, which Linux cannot open, adds nothing and breaks nothing.
    (worktree / ".git").write_text("gitdir: C:/no/such/.git/worktrees/x\n", encoding="utf-8")
    assert tests_database_guard.other_checkouts(worktree) == []
    assert tests_database_guard.class_ports(worktree) == {
        tests_database_guard.CLASS_PORT,
        FAKE_CLASS_PORT,
    }


def _info(host: str, port: int, hostaddr: str = "", dbname: str = "datapilot") -> SimpleNamespace:
    return SimpleNamespace(host=host, port=port, hostaddr=hostaddr, dbname=dbname)


@pytest.mark.parametrize(
    "info",
    [
        _info("127.0.0.1", 59999, "127.0.0.1"),  # a service file's port
        _info("localhost", 55432, "127.0.0.9"),  # PGHOSTADDR
        _info("/var/run/postgresql", 5432),  # a socket, when nothing names a host
        _info("db.internal", 55432, "10.0.0.5"),
    ],
    ids=["service-file", "PGHOSTADDR", "socket", "remote"],
)
def test_what_libpq_actually_connected_to_is_refused_unless_it_is_the_tests_own(
    info: SimpleNamespace, fake_class_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(stack_for_tests.PORT_VARIABLE, raising=False)
    assert tests_database_guard.connected_elsewhere(info) is not None
    for own in (_info("localhost", 55432, "127.0.0.1"), _info("::1", 55432, "::1")):
        assert tests_database_guard.connected_elsewhere(own) is None


class _OpenedConnection:
    def __init__(self, info: SimpleNamespace) -> None:
        self.info = info
        self.closed = False

    def close(self) -> None:
        self.closed = True


class _OpenedAsyncConnection(_OpenedConnection):
    async def close(self) -> None:  # type: ignore[override]
        self.closed = True


def test_a_connection_libpq_opened_elsewhere_is_closed_and_refused(
    fake_class_env: Path, monkeypatch: pytest.MonkeyPatch, refusals: list[str]
) -> None:
    """The address passes the check before connecting (PGSERVICE or a service file sends libpq
    elsewhere); the connection libpq opened is closed and refused before it is returned."""
    monkeypatch.delenv(stack_for_tests.PORT_VARIABLE, raising=False)
    opened: list[_OpenedConnection] = []

    def libpq(where: SimpleNamespace) -> object:
        def connect(_cls: type, _conninfo: str = "", **_kwargs: object) -> _OpenedConnection:
            opened.append(_OpenedConnection(where))
            return opened[-1]

        return connect

    monkeypatch.setitem(tests_database_guard.originals, "sync", libpq(_info("127.0.0.1", 59999)))
    with pytest.raises(NotTheTestsDatabase, match="libpq opened to 127.0.0.1:59999/datapilot"):
        psycopg.connect(_tests_url())
    assert opened[-1].closed
    assert tests_database_guard.refused[-1] == "127.0.0.1:59999/datapilot"

    own = _info("localhost", 55432, "127.0.0.1")
    monkeypatch.setitem(tests_database_guard.originals, "sync", libpq(own))
    assert psycopg.connect(_tests_url()) is opened[-1]
    assert not opened[-1].closed

    async def libpq_async(_cls: type, _conninfo: str = "", **_kwargs: object) -> object:
        opened.append(_OpenedAsyncConnection(_info("/var/run/postgresql", 5432)))
        return opened[-1]

    monkeypatch.setitem(tests_database_guard.originals, "async", libpq_async)
    with pytest.raises(NotTheTestsDatabase, match="/var/run/postgresql:5432"):
        asyncio.run(psycopg.AsyncConnection.connect(_tests_url()))
    assert opened[-1].closed


CONFTEST_FOLDER = REPO / "platform" / "tests"


def _with_the_conftest(tmp_path: Path, body: str) -> subprocess.CompletedProcess[str]:
    """Run one test file outside the repository with the tests' conftest loaded as a plugin:
    these tests check the conftest's own layers, not the package's guard."""
    probe = tmp_path / "test_conftest_layer.py"
    probe.write_text(body, encoding="utf-8")
    paths = [str(CONFTEST_FOLDER), os.environ.get("PYTHONPATH", "")]
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(p for p in paths if p), "PYTHONUTF8": "1"}
    command = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-p", "conftest"]
    return subprocess.run(
        [*command, str(probe)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.slow
def test_a_refusal_the_code_under_test_swallows_still_fails_its_test(tmp_path: Path) -> None:
    """The conftest's first layer: the guard's refusal is an OperationalError, which a worker or
    a retry loop may catch; the conftest fails the test all the same."""
    body = (
        "import psycopg\n"
        "import datapilot\n\n"
        "def test_a_worker_that_swallows_a_failed_connection():\n"
        "    try:\n"
        "        psycopg.connect('postgresql://u:u@localhost:59999/datapilot')\n"
        "    except psycopg.OperationalError:\n"
        "        pass\n"
    )
    done = _with_the_conftest(tmp_path, body)
    assert done.returncode == 1, done.stdout[-2000:] + done.stderr[-2000:]
    # The conftest fails it in the fixture's teardown, which pytest reports as an error.
    assert "1 passed, 1 error" in done.stdout or "1 failed" in done.stdout, done.stdout[-2000:]
    assert "localhost:59999/datapilot, not the tests' database" in done.stdout


@pytest.mark.slow
def test_settings_a_test_cached_are_cleared_by_the_conftest_before_the_next_test(
    tmp_path: Path,
) -> None:
    """The conftest's second layer: a test fills the settings cache with another address, and
    the next test, with no fixture of its own, reads the tests' database again."""
    body = (
        "from datapilot import db\n"
        "from datapilot.settings import get_settings\n\n"
        "def test_one_fills_the_cache_with_another_address(monkeypatch):\n"
        "    monkeypatch.setenv('DATABASE_URL_OWNER', 'postgresql://u:u@localhost:59999/x')\n"
        "    get_settings.cache_clear()\n"
        "    assert db.url_for(db.Role.OWNER).endswith(':59999/x')\n\n"
        "def test_two_reads_the_address_with_no_fixture():\n"
        f"    assert db.url_for(db.Role.OWNER).endswith(':{stack_for_tests.port()}/datapilot')\n"
    )
    done = _with_the_conftest(tmp_path, body)
    assert done.returncode == 0, done.stdout[-2000:] + done.stderr[-2000:]
    assert "2 passed" in done.stdout
