import subprocess
import sys

import pytest


def test_package_imports():
    import loopeng  # noqa: F401


def test_live_marker_is_deselected_by_default():
    """The default suite must never hit the network. If this stops holding, a
    workshop delivered on a bad venue network fails at the test step, not the demo."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "tests/"],
        capture_output=True,
        text=True,
    )
    assert "deselected" in result.stdout
    assert result.returncode == 0


@pytest.mark.live
def test_live_canary():
    """Exists only so the default run has something to deselect. Never asserts
    anything about the network."""
    assert True
