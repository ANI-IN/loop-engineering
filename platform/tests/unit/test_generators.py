"""Generated pages match their registries: `make docs` would change nothing."""

from __future__ import annotations

import importlib.util
import sys

from datapilot.settings import PLATFORM


def _render():
    path = PLATFORM / "tools" / "generators" / "render.py"
    spec = importlib.util.spec_from_file_location("render", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["render"] = module
    spec.loader.exec_module(module)
    return module


def test_generated_pages_are_up_to_date() -> None:
    assert _render().main(["--check"]) == 0


def test_rendering_twice_gives_the_same_text() -> None:
    render = _render()
    for output in render.outputs():
        current = output.path.read_text(encoding="utf-8")
        once = output.render(current)
        assert output.render(once) == once, output.path
