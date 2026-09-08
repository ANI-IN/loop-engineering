"""The documentation, checked rather than trusted.

Three failure modes this guards against, all of which have already happened here:

  - a relative link that stopped resolving after a file moved
  - a command in a README that no longer parses
  - a diagram copied into two places and then edited in one of them
"""

import ast
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
README = REPO_ROOT / "README.md"

def _is_ours(path: Path) -> bool:
    """Skip anything under a dot-directory.

    `.pytest_cache/README.md` was being collected, which made the number of tests
    depend on whether a previous run had left a cache behind — a suite whose size
    changes with its own side effects is not reproducible, and this module exists
    to check reproducibility claims.
    """
    return not any(part.startswith(".") for part in path.relative_to(REPO_ROOT).parts)


MARKDOWN = sorted(path for path in REPO_ROOT.rglob("*.md") if _is_ours(path))

# The per-level diagrams live in two places on purpose: a GitHub visitor reading
# the architecture section should not have to click four times, and a presenter
# opening a stage runbook should not have to scroll back to the root README. The
# duplication is safe only because this module refuses to let them diverge.
SHARED_DIAGRAMS = {
    "demos/01_agent_loop/README.md": "Level 1",
    "demos/02_verification_loop/README.md": "Level 2",
    "demos/03_event_driven_loop/README.md": "Level 3",
    "demos/04_hill_climbing_loop/README.md": "Level 4",
}


def mermaid_blocks(path: Path) -> list[str]:
    return re.findall(r"^```mermaid\n(.*?)^```$", path.read_text(encoding="utf-8"),
                      re.DOTALL | re.MULTILINE)


# ---- links ------------------------------------------------------------------


def _prose_only(body: str) -> str:
    """Everything outside a fenced block or an inline code span.

    A link is a claim about a file. Code is a quotation, and a quotation of code
    that happens to contain brackets-then-parentheses is not a claim about
    anything — `{"agent": lambda: build_agent_app(...)}` is Python, not a link to
    a file called `name`.

    This is not hypothetical tidying. The audit's own report was the first
    document in this repository to quote a Python dict dispatch, and it turned
    the suite red: a report `links to name, which does not exist`. The test
    was reading source code as documentation.

    Fences are replaced by blank lines rather than deleted so that anything
    reported by line number still lines up with the file.
    """
    without_fences = re.sub(
        r"^(```|~~~).*?^\1",
        lambda m: "\n" * m.group(0).count("\n"),
        body,
        flags=re.DOTALL | re.MULTILINE,
    )
    return re.sub(r"`[^`\n]*`", "", without_fences)


def _links_in(body: str) -> list[str]:
    """Relative link and image targets in one document's prose.

    Split out from `_relative_links` so the extraction can be tested against a
    string. Reading a file to test a regex made the regex untestable, which is
    why the fenced-code defect survived until a document happened to trip it.
    """
    prose = _prose_only(body)
    targets = re.findall(r"(?<!\!)\[[^\]]*\]\(([^)]+)\)", prose)
    targets += re.findall(r"!\[[^\]]*\]\(([^)]+)\)", prose)
    return [
        target for target in targets
        if not target.startswith(("http://", "https://", "mailto:", "#"))
    ]


def _relative_links(path: Path) -> list[str]:
    return _links_in(path.read_text(encoding="utf-8"))


def test_a_link_in_prose_is_still_found_when_code_is_skipped():
    """The fence fix must not be a way of turning the link check off.

    Half of this test is the bug that prompted it — a Python dict dispatch, which
    read as a link to a file called `name` — and half is an ordinary link in
    prose, which must still be found. A fix that made both disappear would leave
    every document unchecked and every test still green.
    """
    body = (
        "See [the runbook](demos/README.md).\n"
        "\n"
        "```python\n"
        'app = {"agent": lambda: build_agent_app(warehouse)}[args.view]()\n'
        "```\n"
        "\n"
        "Inline `{\"trap\": lambda: build_trap_app(items)}[key]` too.\n"
    )
    assert _links_in(body) == ["demos/README.md"]


def test_an_image_in_prose_is_still_found():
    assert _links_in("![dial](assets/dial.png)\n") == ["assets/dial.png"]


def test_a_fenced_block_does_not_swallow_the_document_after_it():
    """An unbalanced count would blank the rest of the file and check nothing."""
    body = "```\ncode\n```\n\nThen [a link](README.md).\n"
    assert _links_in(body) == ["README.md"]


@pytest.mark.parametrize("path", MARKDOWN, ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_every_relative_link_resolves(path):
    for target in _relative_links(path):
        resolved = (path.parent / target.split("#")[0]).resolve()
        assert resolved.exists(), (
            f"{path.relative_to(REPO_ROOT)} links to {target}, which does not exist"
        )


# ---- documented commands must be runnable ------------------------------------
#
# `README.md` told the room to run `charts.py --with-reference` for the whole life
# of the Stage 4 runbook. There is no such flag — the real one is `--reference` —
# so the single most-repeated command of the most expensive stage exited 2 every
# time, while a paid sweep was in flight.
#
# Every other check in this module reads prose. This one reads the commands, which
# is the part of a document a reader actually executes.

# `[^\S\n]` is horizontal whitespace only. `\s+` here matched newlines, so one
# command's flag list ran on into every line below it and the checker blamed
# `enqueue.py` for `worker.py --drain`. A checker that reports the wrong file is
# worse than none: it teaches the reader to distrust it and then be right to.
_COMMAND = re.compile(r"^[^\S\n]*uv run python[^\S\n]+(\S+\.py)([^\n]*)", re.MULTILINE)


def _documented_commands(body: str) -> list[tuple[str, list[str]]]:
    """(script, long flags) for every `uv run python …` in a fenced block.

    Line continuations are joined first, so a command split over several lines is
    read as one. Only `--flags` are collected: values, paths and quoted questions
    vary legitimately between documents and prove nothing.
    """
    joined = re.sub(r"\\\n\s*", " ", body)
    commands = []
    for script, tail in _COMMAND.findall(joined):
        flags = [
            token.split("=")[0]
            for token in tail.split()
            if token.startswith("--")
        ]
        commands.append((script, flags))
    return commands


def _declared_flags(script: Path) -> set[str]:
    """Every option string the script's argparse declares, read from the AST.

    Static rather than `--help`, deliberately: importing thirteen entry points in
    a subprocess apiece is slow, and a script whose parser cannot be built without
    a credential would make this test need one.
    """
    tree = ast.parse(script.read_text(encoding="utf-8"))
    flags = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if getattr(node.func, "attr", None) != "add_argument":
            continue
        for arg in node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                if arg.value.startswith("-"):
                    flags.add(arg.value)
    return flags


@pytest.mark.parametrize("path", MARKDOWN, ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_every_documented_command_names_a_script_that_exists(path):
    for script, _ in _documented_commands(path.read_text(encoding="utf-8")):
        assert (REPO_ROOT / script).is_file(), (
            f"{path.relative_to(REPO_ROOT)} runs {script}, which does not exist"
        )


@pytest.mark.parametrize("path", MARKDOWN, ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_every_documented_flag_is_accepted_by_the_script(path):
    for script, flags in _documented_commands(path.read_text(encoding="utf-8")):
        target = REPO_ROOT / script
        if not target.is_file():
            continue  # the test above owns that failure
        declared = _declared_flags(target)
        if not declared:
            continue  # no argparse: nothing to contradict
        for flag in flags:
            assert flag in declared, (
                f"{path.relative_to(REPO_ROOT)} runs `{script} {flag}`, but "
                f"{script} declares no such option. It accepts: {sorted(declared)}"
            )


def test_the_command_reader_would_have_caught_the_flag_that_shipped():
    """The regression guard, against the exact text that was wrong.

    A parser that silently found no commands would make both tests above vacuous
    and green, which is the failure mode this whole module exists to prevent.
    """
    found = _documented_commands(
        "```bash\nuv run python demos/04_hill_climbing_loop/charts.py --with-reference\n```\n"
    )
    assert found == [("demos/04_hill_climbing_loop/charts.py", ["--with-reference"])]
    declared = _declared_flags(
        REPO_ROOT / "demos" / "04_hill_climbing_loop" / "charts.py"
    )
    assert "--with-reference" not in declared
    # And the flag it was a typo FOR is gone too. There is no stored set to select
    # between any more, so the whole option went with the apparatus — which makes
    # this the regression guard for both the typo and the feature.
    assert "--reference" not in declared
    assert "--dir" in declared, "the reader must still find real flags"


def test_the_command_reader_joins_a_continued_line():
    body = (
        "```bash\n"
        "uv run python demos/03_event_driven_loop/enqueue.py \\\n"
        '  --question "what share of beauty orders ended up with a refund?"\n'
        "```\n"
    )
    assert _documented_commands(body) == [
        ("demos/03_event_driven_loop/enqueue.py", ["--question"])
    ]


def test_no_markdown_points_at_a_file_in_a_deleted_directory():
    """`app/` is gone.

    `docs/` came back — it holds the design notes and the pre-committed endings — so
    it is no longer in this list, and the ordinary link check covers it: a `docs/`
    path that does not resolve fails `test_every_relative_link_resolves` like any
    other. `scripts/` returns with the preflight and is removed from here then.

    Aimed at *paths*, not at the words. What must not survive is a reference to a
    file inside a directory that is not there.
    """
    stale = re.compile(r"`(?:app)/[\w./-]+\.\w+`")
    for path in MARKDOWN:
        found = stale.findall(path.read_text(encoding="utf-8"))
        assert not found, (
            f"{path.relative_to(REPO_ROOT)} points at {found}, in a removed directory"
        )


def test_the_clone_instructions_are_real():
    """`git clone <repo>` was a placeholder in two files, and `cd \"Loop Eng\"` was
    never the directory a clone produces."""
    for path in (README,):
        body = path.read_text(encoding="utf-8")
        if "git clone" not in body:
            continue
        assert "<repo>" not in body, f"{path.name} still has a placeholder clone URL"
        assert 'cd "Loop Eng"' not in body, f"{path.name} cds to the wrong directory"
        assert "github.com/ANI-IN/loop-engineering" in body
        assert "cd loop-engineering" in body


def test_no_document_points_at_the_deleted_checklist():
    """`PRE-DELIVERY-CHECKLIST.md` is gone and nothing may cite it.

    It was a list of things the operator had to remember to do, which is the shape of
    control this repository spends twenty sections arguing against. Every item on it
    that mattered became a check that runs and fails — `scripts/preflight.py` — and
    every item that could not be made to run was not load-bearing.

    A citation that resolves to nothing is the defect this suite already has two other
    tests for, so the removal gets the same treatment rather than being trusted.
    """
    offenders = [
        path.relative_to(REPO_ROOT)
        for path in MARKDOWN
        if "PRE-DELIVERY-CHECKLIST" in path.read_text(encoding="utf-8")
    ]
    assert not offenders, f"these still cite the removed checklist: {offenders}"
    assert not (REPO_ROOT / "PRE-DELIVERY-CHECKLIST.md").exists()


# ---- diagrams ---------------------------------------------------------------


def test_the_readme_carries_the_system_overview_and_every_level():
    """One nesting overview plus one diagram per loop level."""
    assert len(mermaid_blocks(README)) == 1 + len(SHARED_DIAGRAMS)


@pytest.mark.parametrize("stage", sorted(SHARED_DIAGRAMS), ids=lambda s: s.split("/")[1])
def test_each_stage_diagram_is_byte_identical_in_the_readme(stage):
    """A diagram duplicated by hand is a diagram that drifts. This is the
    enforcement that makes the duplication safe."""
    stage_blocks = mermaid_blocks(REPO_ROOT / stage)
    assert len(stage_blocks) == 1, f"{stage} should carry exactly one diagram"
    assert stage_blocks[0] in mermaid_blocks(README), (
        f"the {SHARED_DIAGRAMS[stage]} diagram in {stage} differs from the one in "
        f"README.md. They are duplicated deliberately and must stay identical."
    )


@pytest.mark.parametrize("path", MARKDOWN, ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_no_diagram_carries_a_measured_number(path):
    """No numbers in any diagram. Level names and hex colours are not numbers."""
    for block in mermaid_blocks(path):
        stripped = re.sub(r"#[0-9a-fA-F]{3,8}", "", block)              # colours
        stripped = re.sub(r"stroke-dasharray:[\d\s]+", "", stripped)    # dash patterns
        # Identifiers, not measurements: prompt levels (L0/L3), loop levels
        # (Level 2, LEVEL 4), and verifier versions (V1, V2).
        stripped = re.sub(r"\bL[0-4]\b", "", stripped)
        stripped = re.sub(r"\blevel [0-4]\b", "", stripped, flags=re.IGNORECASE)
        stripped = re.sub(r"\bV[12]\b", "", stripped)
        assert not re.search(r"\d", stripped), (
            f"{path.relative_to(REPO_ROOT)} has a number in a diagram: "
            f"{re.findall(r'.{0,40}[0-9].{0,40}', stripped)[:3]}"
        )


# ---- commands ---------------------------------------------------------------


def _fenced_bash(path: Path) -> list[str]:
    return re.findall(r"^```bash\n(.*?)^```$", path.read_text(encoding="utf-8"),
                      re.DOTALL | re.MULTILINE)


@pytest.mark.parametrize("path", MARKDOWN, ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_documented_python_entry_points_exist(path):
    """Every `demos/...py` or `tools/...py` named in a shell block must be a file.

    This is what catches a runbook naming a script that was renamed or removed —
    the failure mode that makes a runbook lie at minute forty of a live session.
    """
    for block in _fenced_bash(path):
        for script in re.findall(r"(?:demos|tools)/[\w/]+\.py", block):
            assert (REPO_ROOT / script).is_file(), (
                f"{path.relative_to(REPO_ROOT)} documents {script}, which does not exist"
            )


def test_every_documented_view_is_a_real_choice():
    """`--view` names in the docs must match what demos/views.py accepts."""
    from demos_views_choices import VIEWS  # noqa: F401  (see the fixture below)


@pytest.fixture(autouse=True, scope="module")
def _install_views_shim():
    """demos/ is not a package, so the view list is read from the source."""
    source = (REPO_ROOT / "demos" / "views.py").read_text(encoding="utf-8")
    match = re.search(r"^VIEWS = \(([^)]*)\)", source, re.MULTILINE)
    views = tuple(re.findall(r'"([a-z]+)"', match.group(1)))
    module = type(sys)("demos_views_choices")
    module.VIEWS = views
    sys.modules["demos_views_choices"] = module
    yield
    del sys.modules["demos_views_choices"]


def test_documented_views_match_the_entry_point():
    from demos_views_choices import VIEWS

    body = README.read_text(encoding="utf-8")
    documented = re.search(r"--view \{([a-z,]+)\}", body)
    assert documented, "the README does not document the view choices"
    assert set(documented.group(1).split(",")) == set(VIEWS)


def test_every_tool_in_the_repo_is_documented():
    """A tool CI runs that the README never names is a tool nobody can find.

    Derived from what is on disk rather than listed, because the list is what went
    stale: two of the three entries here named `tools/render_readme_charts.py` and
    `tools/sync_hf.py` after both had been deleted, and the test kept asserting the
    README mentioned them.
    """
    body = README.read_text(encoding="utf-8")
    tools = sorted(
        f"tools/{path.name}"
        for path in (REPO_ROOT / "tools").glob("*.py")
        if path.name != "__init__.py"
    )
    missing = [tool for tool in tools if tool not in body]
    assert not missing, f"the README names none of: {missing}"


def test_the_readme_prose_names_no_measurement():
    """Numbers live inside the self-labelling images, not in prose.

    Dates, version numbers, section numbers and table rows are structure rather
    than findings, so the check is aimed at what a finding actually looks like:
    a percentage, a p-value, or a dollar figure.
    """
    body = README.read_text(encoding="utf-8")
    body = re.sub(r"^\s*\|.*\|\s*$", "", body, flags=re.MULTILINE)   # tables
    body = re.sub(r"```.*?```", "", body, flags=re.DOTALL)           # code
    body = re.sub(r"\[[^\]]*\]\([^)]*\)", "", body)                  # links
    offenders = re.findall(r"\d+(?:\.\d+)?\s?%|\bp\s?[=<]\s?0?\.\d+|\$\s?\d", body)
    assert not offenders, f"README prose states a measurement: {offenders}"


def test_the_offline_suite_command_is_what_ci_runs():
    ci = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    for command in ("uv run ruff check .", "uv run pytest -q",
                    "uv run python tools/lint_no_numbers.py"):
        assert command in ci, f"CI does not run {command!r}"
        assert command in README.read_text(encoding="utf-8"), (
            f"the README does not document {command!r}, which CI runs"
        )


def test_git_tracks_no_file_under_a_removed_directory():
    """`app/` is removed and must stay that way.

    `docs/` came back — design notes and the pre-committed endings — and `scripts/`
    returns with the preflight. Both are covered by the ordinary checks instead: a
    markdown link into either that does not resolve fails
    `test_every_relative_link_resolves`, which is the property that actually mattered.
    """
    tracked = subprocess.run(
        ["git", "ls-files"], capture_output=True, text=True, cwd=REPO_ROOT,
    ).stdout.split()
    for path in tracked:
        assert not path.startswith("app/"), (
            f"{path} is still tracked but its directory was removed"
        )


# ---- a citation printed as provenance must resolve ---------------------------
#
# `sweep/orchestrator.py` printed "a 16.2% floor (results/noise_floor_*.json)" to the
# room before the first cell ran, and no such file existed in the repo — the artifact
# was on the author's machine and .gitignore dropped it. A citation that resolves to
# nothing is the same defect class as the lint rule that pointed at a moved path and
# scanned nothing: it looks like evidence and cannot be checked.
#
# Extends the link-checking pattern above rather than starting a new one.

CITING_MODULES = (
    "src/loopeng/sweep/orchestrator.py",
    "src/loopeng/sweep/reference.py",
)

# Paths these modules WRITE rather than cite. A chart directory that does not exist yet
# is not a broken citation; it is an output. Enumerated, so adding one is deliberate.
WRITTEN_NOT_CITED = frozenset({
    "results/sweep",       # live cell output, gitignored by design — a fresh clone has none
    "results/charts",      # where the chart PNGs are written
})


def _repo_paths_in_strings(path: Path) -> set[str]:
    """Every `results/...`-shaped string constant in a module, docstrings included.

    Docstrings count here, unlike in the numeric-literal rule: a path named in a
    docstring is still a citation a reader will try to follow.
    """
    import ast

    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            found.update(re.findall(r"results/[\w./*-]*[\w*]", node.value))
    return found


def test_an_absent_citation_says_so_rather_than_quoting_a_figure(monkeypatch):
    """If the file goes missing the line reports that, instead of a number nothing on
    disk supports."""
    from loopeng.sweep import orchestrator

    monkeypatch.setattr(orchestrator, "NOISE_FLOOR_PATH", Path("results/gone.json"))
    assert "NOT ON DISK" in orchestrator._noise_floor_reading()


# ---- committed probe output carries no credentials or identifiers ------------


def test_no_committed_file_carries_an_api_key_shape():
    """A key in a public repo is unbounded spend by strangers."""
    import subprocess

    tracked = subprocess.run(
        ["git", "ls-files"], capture_output=True, text=True, cwd=REPO_ROOT,
    ).stdout.split()
    key_shaped = re.compile(r"\b(?:sk-ant-|lsv2_)[A-Za-z0-9_-]{12,}")
    for name in tracked:
        path = REPO_ROOT / name
        if not path.is_file() or path.suffix in {".png", ".duckdb", ".lock"}:
            continue
        try:
            body = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        assert not key_shaped.findall(body), f"{name} looks like it carries a credential"


def test_ci_asserts_the_required_key_only_journey():
    """The check whose absence let a required LANGSMITH_API_KEY ship green. It has to
    live in the OFFLINE job — the property is that no network and no real key are needed.

    The required set has moved twice: one key, then two with the model policy, then back
    to one when the judge turned out to gate nothing. The property being defended never
    moved — **a checkout must start with the credentials the documentation says are
    required, and no others.**

    So the step is asserted by that property rather than by its own title. This test
    pinned the phrase "only the two model keys can start", which meant it agreed with
    the step for the whole time the step supplied a key the docs called optional.
    """
    from loopeng.registry import PROVIDER_KEY_VARS, spec_for

    ci = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    required = PROVIDER_KEY_VARS[spec_for("agent").provider]
    assert f"{required}: ci-dummy-not-a-real-key" in ci, (
        "the offline job must prove a checkout starts with the required key alone"
    )
    # Only the required credential is supplied, which is what makes this step a test of
    # the journey a cloner takes. It set both, and so could not have caught
    # REQUIRED_CREDENTIALS demanding a key the docs called optional.
    from loopeng.registry import PROVIDER_KEY_VARS, spec_for

    required = PROVIDER_KEY_VARS[spec_for("agent").provider]
    assert f"{required}: ci-dummy-not-a-real-key" in ci
    judge_key = PROVIDER_KEY_VARS[spec_for("judge").provider]
    assert f"{judge_key}: ci-dummy" not in ci, (
        "supplying the optional key makes this step unable to prove the checkout "
        "starts without it"
    )
    assert "langsmith_api_key is None" in ci
    # And it must not have introduced a secret into a job that had none.
    assert "secrets." not in ci, "the offline job must need no secret"


def test_the_readme_documents_the_cloners_journey():
    """§11 was written for the author delivering a workshop. §11.0 is for someone who
    just cloned."""
    body = README.read_text(encoding="utf-8")
    assert "Run it on your own key" in body
    assert "--profile smoke" in body

    # The PROPERTY, not the sentence. This read `assert "LangSmith is optional" in body`
    # and failed the moment the line was corrected to "Anthropic and LangSmith are
    # optional" — an improvement, blocked by a test pinning a spelling. That is the same
    # shape as the DIAL caption test, which asserted its exact wording and so passed for
    # the whole time the caption was false.
    #
    # What §11.0 owes a cloner is: name the credential that is actually required, and say
    # the others are not. Both sides read the registry, so this keeps holding if a role
    # changes provider.
    from loopeng.registry import PROVIDER_KEY_VARS, spec_for

    required = PROVIDER_KEY_VARS[spec_for("agent").provider]
    journey = body[body.index("Run it on your own key"):]
    assert required in journey, (
        f"§11.0 must name {required}, which is the key the agent role actually needs"
    )
    assert "optional" in journey.lower()


def test_the_readme_states_that_no_chart_appears_without_live_calls():
    """The property is true and enforced and was never said to the reader.

    It has no exceptions now. It used to carry two — cells badged REFERENCE, and the
    frozen exhibit view — and both of those are gone along with the code that could
    render them, so the sentence is unconditional and the test checks that it stayed
    that way.
    """
    body = README.read_text(encoding="utf-8")
    assert "without live model calls" in body

    # The claim has no exceptions now. It used to carry two — cells badged REFERENCE,
    # and the frozen exhibit view — and both are gone along with the code that could
    # render them.
    #
    # What is checked is the PROMISE, not the word. The README still says "REFERENCE"
    # once, in the paragraph explaining which mechanisms were removed and why, and
    # banning the vocabulary outright would delete the provenance for the decision in
    # order to satisfy a test about it.
    # A COMMAND naming the removed flag, not the word in prose. The README still
    # explains which mechanisms were removed and why, and banning the vocabulary
    # outright would delete the provenance for the decision to satisfy a test about
    # it. What must not survive is an instruction a reader could type.
    assert "--reference=" not in body, "a documented flag the entry point rejects"
    assert "--view exhibit" not in body, "a view that no longer exists"


def test_the_readme_quotes_the_real_deselected_count():
    """The README shows expected pytest output. Only part of it is worth pinning.

    The `passed` count moves every time a test is added — including when this test
    was added, which made the first version of it fail against the number it had
    just changed. Pinning it would force a README edit on every commit that adds a
    test, and the README already says the count moves.

    `deselected` is different. It is the five live-marked tests, it is stable, and
    the README makes a CLAIM about it — "5 deselected is correct, not a problem" —
    which would be wrong if the live suite grew and nobody noticed. That is the
    part a reader could be misled by, so that is the part asserted.
    """
    quoted = re.search(r"^(\d+) passed, (\d+) deselected$",
                       README.read_text(encoding="utf-8"), re.MULTILINE)
    assert quoted, "the README no longer shows an expected pytest summary line"

    collected = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "-m", "live"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    ).stdout
    tally = re.search(r"(\d+)/(\d+) tests collected", collected)
    assert tally, f"could not read a collection tally from:\n{collected[-400:]}"

    live = int(tally.group(1))
    assert int(quoted.group(2)) == live, (
        f"README says {quoted.group(2)} deselected; there are {live} live tests"
    )
def test_no_identifier_shaped_uuid_survives_anywhere_in_history():
    """The check that was missing, and whose absence is the point.

    `.gitignore` states the identifiers in `results/_resume_first.log` were
    "REDACTED IN PLACE". They were — at HEAD. The redaction landed as an ordinary
    content edit, not a history rewrite, so three UUIDs stayed live in ten commits
    reachable from `main`, and the only test guarding the policy looked at the
    working tree. A rule enforced against HEAD alone is a rule that cannot see the
    thing it was written to prevent.

    This walks every blob in every reachable commit. It is the whole history, not
    a sample, and it costs about a second.

    If this fails after a rewrite, the rewrite did not take. If it fails on a new
    commit, something published an identifier — find it before pushing anywhere.
    """
    uuid_shaped = re.compile(
        rb"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    )

    blobs = subprocess.run(
        ["git", "rev-list", "--objects", "--all"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    ).stdout.splitlines()
    names = {}
    for entry in blobs:
        sha, _, path = entry.partition(" ")
        names[sha] = path

    kinds = subprocess.run(
        ["git", "cat-file", "--batch-check=%(objectname) %(objecttype)"],
        input="\n".join(names), capture_output=True, text=True, cwd=REPO_ROOT,
    ).stdout.split()

    offenders = []
    for sha, kind in zip(kinds[::2], kinds[1::2], strict=True):
        if kind != "blob":
            continue
        content = subprocess.run(
            ["git", "cat-file", "blob", sha],
            capture_output=True, cwd=REPO_ROOT,
        ).stdout
        if uuid_shaped.search(content):
            offenders.append(f"{names.get(sha, '?')} ({sha[:8]})")

    assert not offenders, (
        f"identifier-shaped UUIDs survive in history: {sorted(set(offenders))[:10]}"
    )



def test_no_rendered_label_names_a_model_from_the_registry_by_hand():
    """A model name on a rendered surface must come from the registry.

    The trap grid rendered "Haiku · rules given (L3)" for an arm running
    gpt-5.6-luna — a model name on the session's headline visual, naming a model this
    build does not contain. No test could see it: the label was a correct string that
    had stopped being true, which is the shape typed counts have gone stale in eight
    times.

    **The first version of this test banned retired model names from all source
    prose, and it was wrong in the way p10's first test was wrong.** It fired on
    `registry.py` explaining that gpt-4o-mini was rejected for its cache discount, on
    `pricing.py` recording that a rate had been mis-typed, and on `patterns.py`
    naming the four models a measurement used. Every one of those is provenance, and
    a check that fires on correct code gets widened until it fires on nothing.

    So the check is narrow and derived: the labels a reader sees carry the model ids
    the registry declares, and nothing asserts anything about prose.
    """
    from loopeng.agent.trap import arm_label
    from loopeng.registry import REGISTRY

    for role, spec in REGISTRY.items():
        if role == "judge":
            continue  # the judge runs no arm, so it labels none
        for level in ("L0", "L3"):
            label = arm_label(role, level)
            assert spec.model_id in label, (
                f"{role}@{level} renders {label!r}, which does not name "
                f"{spec.model_id}"
            )


def test_the_trap_arms_hold_the_model_constant():
    """Model-versus-model would teach "buy the bigger model", which is the opposite
    of the finding. The spec level is the variable."""
    from loopeng.agent.trap import ARMS

    assert len({role for role, _level in ARMS}) == 1
    assert {level for _role, level in ARMS} == {"L0", "L3"}


def test_the_instruments_note_counts_its_own_entries():
    """It opened "Twelve instruments have been caught…" while carrying fourteen
    numbered entries — a typed count going stale, in the document about typed things
    going stale. Both figures in the prose are checked against the headings.

    One entry is a PLAN rather than an instrument (§7, the four charts specified for a
    session that no longer existed), which is why the opening says "N instruments and
    one plan" while the closing counts every entry as a data point.
    """
    import re
    from pathlib import Path

    body = (Path(__file__).resolve().parent.parent
            / "docs" / "every-instrument-has-been-wrong.md").read_text(encoding="utf-8")
    numbers = [int(n) for n in re.findall(r"^## (\d+)\. ", body, flags=re.M)]

    assert numbers == list(range(1, len(numbers) + 1)), "the entries are misnumbered"
    # Two entries are not instruments: §7 is a PLAN, and §19 is the author. The opening
    # line names all three categories, so the arithmetic has to as well.
    assert f"**{len(numbers) - 2} instruments have been caught" in body
    assert "one plan has, and one of them is the author" in body
    assert f"It is {len(numbers)} data points" in body


# ---- a citation that resolves to nothing still reads as provenance ------------
#
# This has now happened three times, from two unrelated deletions:
#
#   `results/gate0.json`     cited by two src docstrings and two onboarding docs as the
#                            measured evidence for a concurrency cap, after the file was
#                            removed. One of those docs went further and said "I read the
#                            file's PRESENCE" — a citation vouching for its own
#                            verification, to nothing.
#   `tests/test_exhibit.py`  cited by SECURITY.md as **the security boundary**, after the
#                            test and the view it guarded were both deleted.
#   `tools/render_readme_charts.py`, `tools/sync_hf.py`, `src/loopeng/sweep/reference.py`
#                            cited across README, CONTRIBUTING and four onboarding
#                            documents, all removed in the same clean-up.
#
# The link checker did not catch any of them: these are inline code spans, not markdown
# links, and nothing looked at them.

# The trees whose contents are TRACKED SOURCE. `results/` and `gold/` are deliberately
# excluded — they hold generated output that a fresh checkout legitimately does not have,
# so requiring those paths to exist would fire on correct documentation.
_SOURCE_TREES = ("src/", "tests/", "tools/", "scripts/", "demos/", "docs/", ".github/")
_SOURCE_SUFFIXES = (".py", ".yml", ".yaml", ".toml", ".md")

# A document may name a file that is gone, and often should — half this repository's
# documentation is about what was removed and why. The convention is that it must SAY SO
# in the same paragraph. That keeps the escape hatch honest: an author who wants to cite
# a deleted file has to tell the reader it is deleted, which is the thing a stale
# citation fails to do.
_ABSENT_MARKERS = ("delet", "removed", "no longer", "used to", "gone", "previously",
                   "closed by")

_CODE_SPAN = re.compile(r"`([^`\n]+)`")


def _cited_paths(paragraph: str) -> list[str]:
    """Repo-relative source paths named in inline code within one paragraph."""
    found = []
    for text in _CODE_SPAN.findall(paragraph):
        token = text.strip().split()[0] if text.strip() else ""
        if (token.startswith(_SOURCE_TREES) and token.endswith(_SOURCE_SUFFIXES)
                and "*" not in token):
            found.append(token)
    return found


def test_the_citation_check_finds_a_path_in_inline_code():
    """Half of this test is the shape that slipped past the link checker."""
    assert _cited_paths("See `tools/lint_no_numbers.py` for the rule.") == \
        ["tools/lint_no_numbers.py"]
    assert _cited_paths("Run `uv run pytest tests/test_docs.py -q` first.") == []
    assert _cited_paths("A glob like `demos/02_verification_loop/*.py` is not a file.") == []
    assert _cited_paths("`results/sweep/` is generated, so it is out of scope.") == []


@pytest.mark.parametrize("path", MARKDOWN, ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_every_cited_source_file_exists_or_is_marked_absent(path):
    body = path.read_text(encoding="utf-8")
    for paragraph in re.split(r"\n\s*\n", body):
        marked = any(marker in paragraph.lower() for marker in _ABSENT_MARKERS)
        for cited in _cited_paths(paragraph):
            if (REPO_ROOT / cited).is_file() or marked:
                continue
            pytest.fail(
                f"{path.relative_to(REPO_ROOT)} cites `{cited}`, which is not in the "
                f"repository, and the paragraph does not say it is gone.\n"
                f"Either fix the path, or say in the same paragraph that the file was "
                f"removed — a citation that resolves to nothing still reads as "
                f"provenance."
            )


def test_the_failure_taxonomy_record_exists_and_covers_every_kind():
    """The note cites this file by name, so it has to resolve — and it has to enumerate
    the whole enum, because a record listing only the kinds that fired is a record a
    reader cannot tell "never happened" from "never recorded" in.

    Every sweep before this file existed determined the kind of every visible failure
    and dropped it before writing the row, so "never recorded" was the true answer for
    all seven.
    """
    import json

    from loopeng.agent.classify import VisibleKind

    path = REPO_ROOT / "results" / "failure_taxonomy_observed.json"
    assert path.is_file(), "docs/the-failure-taxonomy.md cites a file that is not here"

    record = json.loads(path.read_text(encoding="utf-8"))
    for kind in VisibleKind:
        assert kind.value in record["kinds"], f"{kind.value} is missing from the record"

    # Derived both ways, so the two halves cannot drift: what the record calls never
    # observed must be exactly the kinds whose count is zero.
    assert set(record["never_observed"]) == {
        kind for kind, count in record["kinds"].items()
        if count == 0 and kind != "unclassified"
    }
    # What the sample covers is a field, not a caveat in prose someone can quote around.
    assert record["covers"]["role"] and record["covers"]["level"]


def _tracked_paths() -> set[str]:
    return set(subprocess.run(
        ["git", "ls-files"], capture_output=True, text=True, cwd=REPO_ROOT,
    ).stdout.split())


@pytest.mark.parametrize(
    "path", [p for p in MARKDOWN if p.parent.name == "docs"],
    ids=lambda p: str(p.relative_to(REPO_ROOT)),
)
def test_evidence_cited_by_a_design_note_is_TRACKED_not_merely_present(path):
    """Present on the author's machine is not the same as in the repository.

    `docs/the-failure-taxonomy.md` cited `results/failure_taxonomy_observed.json`, the
    record of which failure kinds real runs have produced. The file was written,
    committed with `git add -A`, and silently not added — `.gitignore` excludes
    `results/*.json`. The local suite passed, because the file was sitting there
    untracked; CI failed on the clone.

    That is precisely the noise-floor defect repeating with a different filename: a
    citation that resolves on one machine and nowhere else, printed as provenance. The
    existing link check asks `exists()`, which is true of an untracked file, so it
    could not see it — and what caught it was the clean checkout rather than the
    author's laptop.

    Scoped to `docs/`, deliberately. These notes cite EVIDENCE; a runbook naming
    `results/sweep/dial.png` is describing output the reader is about to generate, and
    requiring that to be committed would be the opposite of this repository's rule.
    """
    tracked = _tracked_paths()
    body = path.read_text(encoding="utf-8")
    cited = set(_relative_links(path)) | set(_CODE_SPAN.findall(body))

    for target in cited:
        token = target.strip().split()[0] if target.strip() else ""
        token = token.split("#")[0]
        if not token.startswith(("../results/", "results/")):
            continue
        relative = token.removeprefix("../")
        if relative.endswith("/") or "*" in relative:
            continue  # a directory or a glob, not a cited artifact
        # Only files directly under `results/`. That is where the evidence records
        # live — the noise floor, the taxonomy observation — while everything nested
        # below it is generated output a reader is about to produce for themselves.
        #
        # Without this line the guard fired on the note EXPLAINING the guard, whose
        # own prose gives `results/sweep/dial.png` as the example of a path that must
        # NOT be required to exist. Self-referential, and the check was wrong rather
        # than the sentence.
        if relative.count("/") != 1:
            continue
        assert relative in tracked, (
            f"{path.relative_to(REPO_ROOT)} cites {token} as evidence, and it is not "
            f"tracked by git. It may exist on your machine; it does not exist on a "
            f"clone, which is where anyone checking the claim will look."
        )


def test_the_ci_caveat_names_actions_the_workflow_actually_uses():
    """A caveat that outlives the thing it warns about is this project's own defect.

    README §16 records that three actions still target the deprecated Node 20 runtime
    and that the workflow passes only because the runner forces a newer one. The pins
    are deliberately not bumped — pinning would hide the date this was known and swap a
    loud future failure for a silent present change.

    So the caveat has to stay true. Every action version it names is checked against
    the workflow: bump one and this fails, which is the prompt to update the caveat
    rather than leave a warning about a version nobody uses any more.
    """
    body = README.read_text(encoding="utf-8")
    ci = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    caveat = body[body.index("deprecated Node 20"):body.index("**A green CI badge")]
    named = set(re.findall(r"`([a-z][\w.-]+/[\w.-]+@v\d+)`", caveat))
    assert named, "the caveat no longer names any action version"

    for action in sorted(named):
        assert action in ci, (
            f"README §16 warns about {action}, which this workflow no longer uses. "
            f"Update the caveat: a warning about a version nobody runs is noise, and "
            f"it hides whether the real one is still affected."
        )


def test_the_ci_caveat_is_honest_about_what_ci_cannot_catch():
    """The property, not the wording: a reader must learn from §16 that CI makes no
    model call, so nothing it runs can catch a broken live path."""
    body = README.read_text(encoding="utf-8")
    caveat = body[body.index("## CI, and what it does not cover"):]
    assert "never calls a model" in caveat
    assert "offline contract" in caveat


def test_every_command_a_fix_message_tells_you_to_run_exists():
    """A path that resolves nowhere, in the sentence a stuck operator reads.

    `providers.py` told anyone whose credential was rejected to run
    `uv run python scripts/preflight.py`. There is no such script — it is
    `demos/00_preflight/check.py` — so the one instruction given to someone who is
    already blocked sent them to a file that does not exist.

    That is the citation-to-nothing defect in its worst location: not a design note a
    reader might skim, but the remedy line of an error, read by definition at the
    moment nothing is working. The markdown guard cannot see it because it lives in a
    Python string.

    Narrow on purpose: only `uv run python <path>.py`, which is this repository's one
    documented way of invoking anything, so a match is unambiguous.
    """
    command = re.compile(r"uv run python ([\w./-]+\.py)")
    missing = []
    for tree in ("src", "tools", "scripts"):
        for path in sorted((REPO_ROOT / tree).rglob("*.py")):
            for script in command.findall(path.read_text(encoding="utf-8")):
                if not (REPO_ROOT / script).is_file():
                    missing.append(f"{path.relative_to(REPO_ROOT)} -> {script}")
    assert not missing, (
        "these tell an operator to run something that is not here:\n  "
        + "\n  ".join(missing)
    )


def test_no_ci_step_pipes_a_command_whose_exit_code_is_the_gate():
    """The rule that failed three times, finally made structural.

    A shell pipeline's exit status is its LAST command's, so `pytest … | tail -3`
    always succeeds. That cost a commit, then a CI step named `Confirm live tests were
    deselected` that could not fail for the life of the file, then a push with a
    failing test made while writing up the fix for the second.

    Three occurrences with complete knowledge of the failure mode. Every other instance
    of that gap in this repository was closed by making the rule structural rather than
    remembered, and the workflow was the last place it was still remembered.

    A pipe is allowed if the step sets `pipefail`, which is the actual fix rather than
    a ban — `set -o pipefail` makes the pipeline's status the first failure in it.
    """
    import yaml

    workflow = yaml.safe_load(
        (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    )
    offenders = []
    for job in workflow["jobs"].values():
        for step in job.get("steps", []):
            command = step.get("run")
            if not command:
                continue
            if "|" in command and "pipefail" not in command:
                offenders.append(step.get("name", command.splitlines()[0]))

    assert not offenders, (
        "these CI steps pipe a command whose exit code is the gate, so the step's "
        "status is the last command's and it cannot fail:\n  " + "\n  ".join(offenders)
        + "\nEither drop the pipe or `set -o pipefail`."
    )


def test_nothing_under_src_imports_the_reference_directory():
    """`reference/` is documentation, not a data source, and that is STRUCTURAL.

    The directory it replaces — `results/reference/` — was *loaded* by the renderer, so
    a stored measurement could reach a chart and be shown as a fresh one. Five
    mechanisms guarded against that (a hatched fill, a badge, a date on every row, a
    four-way mode flag, a test), and the guarding was the tell: the capability is gone
    now instead.

    This is what keeps it gone. A module that imports or opens anything under
    `reference/` has reconnected the path that was deleted.
    """
    offenders = []
    for path in sorted((REPO_ROOT / "src").rglob("*.py")):
        body = path.read_text(encoding="utf-8")
        for line in body.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue  # a comment may name it; only code may not reach it
            if "reference/" in stripped and "results/reference" not in stripped:
                offenders.append(f"{path.relative_to(REPO_ROOT)}: {stripped[:80]}")
    assert not offenders, (
        "these reach into reference/, which no module may:\n  " + "\n  ".join(offenders)
    )


def test_the_reference_run_carries_its_own_provenance():
    """Every figure in there is one day, one account, one gold set. Somebody will read
    it as what they should expect, so each of those travels with the numbers rather
    than sitting in a caption."""
    import json

    provenance = json.loads(
        (REPO_ROOT / "reference" / "provenance.json").read_text(encoding="utf-8")
    )
    for field in ("measured_on", "models", "profile", "n_held_out", "account_tier"):
        assert provenance.get(field), f"reference/provenance.json is missing {field}"

    from loopeng.registry import REGISTRY, spec_for

    assert set(provenance["models"]) == set(REGISTRY), "every role is named"
    for role, model in provenance["models"].items():
        assert model == spec_for(role).model_id, (
            f"reference/ records {role}={model}; the registry says "
            f"{spec_for(role).model_id}. Regenerate it, or the numbers describe a "
            f"model policy this build no longer has."
        )


def test_the_docs_index_does_not_restate_a_count_that_can_go_stale():
    """A typed count has gone stale nine times in this build, including inside the note
    about typed things going stale — and then again in the INDEX that summarises it,
    which is a restatement of a restatement.

    Both places are derived from the entry headings now, so there is one number and one
    place it comes from.
    """
    import re

    note = (REPO_ROOT / "docs" / "every-instrument-has-been-wrong.md").read_text(
        encoding="utf-8")
    index = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")
    entries = len(re.findall(r"^## (\d+)\. ", note, flags=re.M))

    # Two entries are not instruments: one is a PLAN, one is the author.
    assert f"{entries - 2} instruments" in index, (
        f"docs/README.md restates a count the note no longer supports; the note has "
        f"{entries} numbered entries"
    )
