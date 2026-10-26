"""The Makefile reads its targets' variables from the command line only (session 6 review, round 3).

WSL sets NAME to the computer's name in every shell, and `NAME ?=` kept it: `make logs` followed a
service named DESKTOP-..., and a bare `make verify-assignments` passed it to --only. Each test runs
`make -n` (it prints the commands and runs none) with the variable exported in the environment,
where it must be ignored, and on the command line, where it must still count. Zero tokens; no
command a target names is run.
"""

from __future__ import annotations

import os
import shutil
import subprocess

import pytest

from datapilot.settings import REPO

MAKEFILE = REPO / "Makefile"
EXPORTED = "DESKTOP-3POGG4B"  # the reviewer's computer name, as WSL exports it
GIVEN = "a-readable-slug"
# The variables a target reads (the Makefile's COMMAND_LINE_ONLY), never inherited from make's own
# run of this suite.
VARIABLES = (
    *("NAME", "PURPOSE", "STEP", "ARGS", "VARIANT", "TREE", "PACK"),
    *("PLANTED", "ONCE", "LEVEL", "BY", "RUN", "REPO", "FORCE"),
)

pytestmark = [
    pytest.mark.security,
    pytest.mark.skipif(shutil.which("make") is None, reason="needs GNU make"),
]


def _environment(**exported: str) -> dict[str, str]:
    """This process's environment without make's own (this suite may run under make) and
    without any of the targets' variables, then the ones a test exports."""
    inherited = {"MAKEFLAGS", "MFLAGS", "MAKELEVEL", "MAKEOVERRIDES", *VARIABLES}
    return {**{k: v for k, v in os.environ.items() if k not in inherited}, **exported}


def _make(*arguments: str, dry: bool = True, **exported: str) -> str:
    options = ["-n"] if dry else []
    done = subprocess.run(
        ["make", *options, "--no-print-directory", "-f", str(MAKEFILE), *arguments],
        cwd=REPO,
        env=_environment(**exported),
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stdout + done.stderr
    return done.stdout


NAME_TARGETS = [
    "logs",
    "demo",
    "reset",
    "reset-discarding-baseline",
    "archive-show",
    "safeguard-verify",
    "safeguard-activate",
    "open-code",
    "check-assignment",
    "apply-solution",
    "verify-assignments",
]


@pytest.mark.parametrize("target", NAME_TARGETS)
def test_an_exported_name_is_ignored_and_one_on_the_command_line_counts(target: str) -> None:
    assert EXPORTED not in _make(target, NAME=EXPORTED)
    assert GIVEN in _make(target, f"NAME={GIVEN}", NAME=EXPORTED)


def test_make_logs_and_a_full_verification_with_the_computers_name_exported() -> None:
    """The review's two failures: no service named after the computer, no --only."""
    assert _make("logs", NAME=EXPORTED).strip().endswith("logs --follow")
    assert _make("logs", "NAME=api", NAME=EXPORTED).strip().endswith("logs --follow api")
    full = _make("verify-assignments", NAME=EXPORTED)
    assert "--only" not in full
    assert "--only agent-loop" in _make("verify-assignments", "NAME=agent-loop", NAME=EXPORTED)


@pytest.mark.parametrize(
    ("target", "variable", "value", "shows"),
    [
        ("preflight", "PURPOSE", "class", "--purpose class"),
        ("calibrate", "STEP", "traps", "calibrate traps"),
        ("calibrate", "ARGS", "--runs 3", "--runs 3"),
        ("verify-assignments", "VARIANT", "reference", "--variant reference"),
        ("verify-assignments", "ONCE", "1", "--once"),
        ("check-assignment", "TREE", "/tmp/copy", "--tree /tmp/copy"),
        ("check-pack", "PACK", "datapilot_us", "check_pack.py datapilot_us"),
        ("autonomy", "LEVEL", "unattended", '"unattended"'),
        ("autonomy", "BY", "Ada", '--by "Ada"'),
        ("safeguard-verify", "RUN", "run-17", '--run "run-17"'),
        ("ci-local", "REPO", "/tmp/release", '--repo "/tmp/release"'),
        ("demo", "PLANTED", "1", "--planted"),
    ],
)
def test_every_variable_a_target_reads_counts_only_on_the_command_line(
    target: str, variable: str, value: str, shows: str
) -> None:
    assert shows not in _make(target, **{variable: value})
    assert shows in _make(target, f"{variable}={value}")


def test_an_exported_variable_never_reaches_a_recipes_environment() -> None:
    """The check and apply commands read PURPOSE and FORCE from their environment, which make
    fills with what it exports: an exported FORCE=1 must never replace a scratch copy."""
    probe = "--eval=probe-environment: ; @printenv FORCE PURPOSE NAME || true"
    assert _make(probe, "probe-environment", dry=False, FORCE="1", PURPOSE="class").strip() == ""
    given = _make(probe, "probe-environment", "FORCE=1", "PURPOSE=class", dry=False)
    assert given.split() == ["1", "class"]


def test_a_planted_variable_in_makeflags_counts_as_the_command_line() -> None:
    """MAKEFLAGS is make's own command line: a parent make passes its command-line variables to a
    sub-make there, and make cannot tell that from a shell that sets MAKEFLAGS itself. So a
    PLANTED=1 in MAKEFLAGS is a PLANTED=1 given on the command line, deliberately, as the review of
    26 October, round 3, recorded; PLANTED exported alone never is."""
    assert "--planted" in _make("demo", "NAME=agent-unbounded-rows", MAKEFLAGS="PLANTED=1")
    assert "--planted" not in _make("demo", "NAME=agent-unbounded-rows", PLANTED="1")
    assert "--planted" not in _make("demo", "NAME=agent-unbounded-rows", "PLANTED=yes")


# The tests' own stack is named in the Makefile, never taken from the environment (session 7
# review): an exported TEST_STACK=datapilot made `make test-stack-down` stop the class stack.
@pytest.mark.parametrize(
    ("variable", "exported", "kept"),
    [
        ("TEST_STACK", "datapilot", "-p datapilot-tests "),
        ("TEST_POSTGRES_PORT", "5432", "POSTGRES_PORT=55432 "),
    ],
)
def test_the_tests_stack_ignores_the_environment(variable: str, exported: str, kept: str) -> None:
    printed = _make("test-stack-down", **{variable: exported})
    assert kept in printed


def test_the_tests_stack_still_takes_the_command_line() -> None:
    printed = _make("test-stack-down", "TEST_STACK=another-tests")
    assert "-p another-tests " in printed
