"""The build-protecting half of the environment guard.

The same function runs at import in settings.py. This file only supplies the
adversarial cases: a real environment that is currently sound proves nothing
about whether the check would notice if it stopped being sound.
"""

import os
import stat
from pathlib import Path

import pytest

from loopeng.env_guard import check_environment


def test_this_environment_is_sound():
    """If this fails, read the message — it names the problem and the fix."""
    problem = check_environment()
    assert problem is None, problem


def test_detects_an_icloud_interpreter_prefix(tmp_path):
    fake_prefix = tmp_path / "Library" / "Mobile Documents" / "venv"
    fake_prefix.mkdir(parents=True)
    problem = check_environment(prefix=fake_prefix, paths=())
    assert problem is not None
    assert "iCloud" in problem
    assert "Fix:" in problem


def test_detects_an_icloud_data_path(tmp_path):
    """The warehouse is regenerated at session start and results/*.json is
    rewritten cell by cell during the sweep. Syncing either mid-demo is its own
    failure mode, separate from the .pth problem."""
    synced = tmp_path / "com~apple~CloudDocs" / "warehouse.duckdb"
    synced.parent.mkdir(parents=True)
    synced.write_bytes(b"")
    problem = check_environment(prefix=tmp_path, paths=(synced,))
    assert problem is not None
    assert "data path" in problem


@pytest.mark.skipif(
    not hasattr(os, "chflags"),
    reason=(
        "os.chflags and UF_HIDDEN are BSD-only. The failure this guards against is "
        "macOS iCloud setting UF_HIDDEN on .pth files, which cannot occur on Linux, so "
        "the test is skipped there rather than weakened to run everywhere. The guard "
        "itself already handles the absence: getattr(st, 'st_flags', 0) returns 0 on "
        "platforms without it, and the companion test below covers that path."
    ),
)
def test_detects_a_hidden_pth_file(tmp_path):
    """The actual observed failure: CPython skips hidden .pth files silently, so
    the editable install vanishes and `import loopeng` fails with no clue why."""
    site_packages = tmp_path / "lib" / "python3.12" / "site-packages"
    site_packages.mkdir(parents=True)
    pth = site_packages / "loopeng.pth"
    pth.write_text("/somewhere/src\n")
    os.chflags(pth, stat.UF_HIDDEN)

    problem = check_environment(prefix=tmp_path, paths=())
    assert problem is not None
    assert "UF_HIDDEN" in problem
    assert "loopeng.pth" in problem


def test_a_visible_pth_file_is_not_a_problem(tmp_path):
    site_packages = tmp_path / "lib" / "python3.12" / "site-packages"
    site_packages.mkdir(parents=True)
    (site_packages / "loopeng.pth").write_text("/somewhere/src\n")
    assert check_environment(prefix=tmp_path, paths=()) is None


def test_importing_settings_runs_the_same_check():
    """One function, two callers. If these ever diverge, the session-protecting
    half is the one that would fail silently."""
    import inspect

    import loopeng.settings as settings_module

    source = inspect.getsource(settings_module)
    assert "check_environment()" in source
    assert Path(settings_module.__file__).exists()
