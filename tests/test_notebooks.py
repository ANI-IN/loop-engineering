"""`notebooks/` — thin by rule, and committed with no outputs.

Two invariants, and the second is specific to what this repository is about.

**They import from `loopeng` and contain no loop logic.** A notebook cell is the easiest
place in the world to paste something that works. A second implementation of the retry
policy, the budget check or the verifier feedback living in a cell would be the exact
defect this whole project is about — declared in one place, enforced in another — and
nothing would fail. `demos/` is held to the same rule by a line budget; notebooks get a
structural one, because a notebook has no natural size.

**They are committed with every output cleared.** A notebook carrying stored outputs
shows a reader numbers computed on somebody else's machine on some other day, in a
document that looks live. That is the stored-measurement-passing-as-fresh defect with a
`In [12]:` prompt in front of it, and it is the one this repository spent five
mechanisms and then a deletion getting rid of everywhere else. It must not come back
through a file format.
"""

import ast
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
NOTEBOOK_DIR = REPO_ROOT / "notebooks"
NOTEBOOKS = sorted(NOTEBOOK_DIR.glob("*.ipynb"))

# Statements that build control flow rather than call into it. `for` is allowed —
# printing a list of rows is not loop logic — but a function, a class or a `while` in a
# notebook cell is somebody starting to implement something that belongs in `src/`.
BANNED_NODES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.While)

# Going straight to a vendor SDK skips the provider seam, which is where the two
# vendors' opposite cached-token conventions are reconciled and where a usage response
# that reports more cached tokens than prompt tokens raises instead of being believed.
BANNED_IMPORTS = ("openai", "anthropic", "langsmith")


def _code_cells(path: Path) -> list[str]:
    body = json.loads(path.read_text(encoding="utf-8"))
    return ["".join(cell["source"]) for cell in body["cells"]
            if cell["cell_type"] == "code"]


def _parsed(source: str) -> ast.Module:
    """Parse a cell, tolerating the one IPython line-magic the notebooks use."""
    lines = [line for line in source.splitlines() if not line.startswith("%")]
    return ast.parse("\n".join(lines))


def test_there_are_notebooks_to_check():
    """A checker that silently matches nothing is indistinguishable from one that
    passes — the defect this repository has produced twice in a lint rule."""
    assert NOTEBOOKS, "notebooks/ is empty; this whole module would be vacuous"


@pytest.mark.parametrize("path", NOTEBOOKS, ids=lambda p: p.name)
def test_every_code_cell_parses(path):
    for index, source in enumerate(_code_cells(path)):
        try:
            _parsed(source)
        except SyntaxError as exc:  # pragma: no cover - the message is the point
            pytest.fail(f"{path.name} cell {index} does not parse: {exc}")


@pytest.mark.parametrize("path", NOTEBOOKS, ids=lambda p: p.name)
def test_no_notebook_defines_loop_logic(path):
    for index, source in enumerate(_code_cells(path)):
        for node in ast.walk(_parsed(source)):
            assert not isinstance(node, BANNED_NODES), (
                f"{path.name} cell {index} defines a {type(node).__name__}. Notebooks "
                f"import from loopeng and call in; anything with control flow of its "
                f"own belongs in src/loopeng/ where it can be tested."
            )


@pytest.mark.parametrize("path", NOTEBOOKS, ids=lambda p: p.name)
def test_no_notebook_reaches_past_the_provider_seam(path):
    for index, source in enumerate(_code_cells(path)):
        for node in ast.walk(_parsed(source)):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            for name in names:
                assert name.split(".")[0] not in BANNED_IMPORTS, (
                    f"{path.name} cell {index} imports {name} directly. Model calls go "
                    f"through loopeng.providers, which is where the two vendors' "
                    f"opposite cached-token conventions are reconciled."
                )


@pytest.mark.parametrize("path", NOTEBOOKS, ids=lambda p: p.name)
def test_every_notebook_actually_uses_the_library(path):
    """The other half of "thin": a notebook that imports nothing from `loopeng` is not
    thin, it is a separate implementation that happens to be short."""
    sources = "\n".join(_code_cells(path))
    assert "loopeng" in sources, f"{path.name} imports nothing from loopeng"


@pytest.mark.parametrize("path", NOTEBOOKS, ids=lambda p: p.name)
def test_no_notebook_is_committed_with_outputs(path):
    """Stored outputs are numbers computed elsewhere, on some other day, in a document
    that looks live — the defect this repository deleted a whole render path to be rid
    of, arriving through a file format."""
    body = json.loads(path.read_text(encoding="utf-8"))
    for index, cell in enumerate(body["cells"]):
        if cell["cell_type"] != "code":
            continue
        assert cell.get("outputs") == [], (
            f"{path.name} cell {index} carries stored output. Clear it before "
            f"committing: a reader opening this sees figures computed on another "
            f"machine on another day, with nothing on screen saying so."
        )
        assert cell.get("execution_count") is None, (
            f"{path.name} cell {index} carries an execution count, so it was committed "
            f"after being run"
        )


@pytest.mark.parametrize("path", NOTEBOOKS, ids=lambda p: p.name)
def test_every_notebook_says_whether_it_spends(path):
    """A reader must know before running a cell, not after the bill.

    Checked as a property of the first markdown cell rather than of the filename alone,
    because the filename is what someone sees in a directory listing and the heading is
    what they see once it is open. Both have to agree.
    """
    body = json.loads(path.read_text(encoding="utf-8"))
    heading = "".join(body["cells"][0]["source"]).lower()
    assert body["cells"][0]["cell_type"] == "markdown", "every notebook opens with prose"

    if "_free" in path.stem:
        assert "free" in heading and "no api" in heading.replace("no api key", "no api")
    elif "_live" in path.stem:
        assert "spends money" in heading
    else:
        pytest.fail(
            f"{path.name} must end in _free or _live so a reader can tell from the "
            f"directory listing whether opening it costs anything"
        )
