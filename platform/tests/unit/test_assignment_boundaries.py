"""The assignments' boundary, zero tokens and no database: every extension point in class code is
inert, no required change exists in a class code path, every solution applies onto the starter,
and nothing in an assignment path reaches a test double, a replay, or a captured run."""

from __future__ import annotations

import ast
import importlib.util
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from datapilot.assignments import VARIANTS, WITHHELD_REASON, assignment, solutions_withheld
from datapilot.config import pack_config
from datapilot.contracts import AnswerEnvelope, AnswerStatus, ProposedRule
from datapilot.loop1_agent import extension as agent_loop
from datapilot.loop1_agent.catalog import CatalogSnapshot
from datapilot.loop1_agent.tools import Warehouse
from datapilot.loop2_verification import extension as verification_loop
from datapilot.loop3_events import extension as event_loop
from datapilot.loop4_hill_climbing import extension as hill_climbing_loop
from datapilot.loop4_hill_climbing.pack_files import load_benchmark
from datapilot.names import SECTIONS
from datapilot.settings import PLATFORM, REPO

SLUGS = [s.slug for s in SECTIONS]
EXTENSIONS = {
    "agent-loop": "platform/src/datapilot/loop1_agent/extension.py",
    "verification-loop": "platform/src/datapilot/loop2_verification/extension.py",
    "event-loop": "platform/src/datapilot/loop3_events/extension.py",
    "hill-climbing-loop": "platform/src/datapilot/loop4_hill_climbing/extension.py",
}


def test_the_agent_loop_extension_points_are_inert() -> None:
    warehouse = Warehouse(CatalogSnapshot("warehouse"), "postgresql://never-opened")
    assert agent_loop.lookup_tools(warehouse, agent_loop.LookupLog()) == []
    assert agent_loop.WORKING_METHOD == ""
    envelope = AnswerEnvelope(status=AnswerStatus.ANSWERED, final_sql="SELECT 1")
    assert agent_loop.with_matches(envelope, agent_loop.LookupLog()) is envelope
    with pytest.raises(NotImplementedError):
        agent_loop.lookup_values(warehouse, "product", "anything")


def test_the_verification_loop_registers_no_new_grader() -> None:
    assert verification_loop.question_graders() == []
    assert verification_loop.answer_graders() == []
    graders = PLATFORM / "src" / "datapilot" / "loop2_verification" / "graders"
    assert not (graders / "clarify_or_abstain.py").exists()
    assert not (graders / "personal_data_leak.py").exists()


def test_the_event_loop_has_no_scheduled_job_of_its_own() -> None:
    from datetime import date

    assert event_loop.JOB_QUEUES == {}
    assert event_loop.schedule(None) is None  # type: ignore[arg-type]
    for stub in (
        lambda: event_loop.anomaly_event_id(date(2026, 1, 30)),
        lambda: event_loop.measure(date(2026, 1, 30)),
    ):
        with pytest.raises(NotImplementedError):
            stub()


def test_the_hill_climbing_loop_extension_points_are_inert() -> None:
    assert hill_climbing_loop.CRITIC_GUIDANCE == ""
    rule = ProposedRule(id="r", title="t", rule_text="x", applies_when="y", expected_effect="z")
    assert hill_climbing_loop.screen([rule], [], []) == ([rule], [])
    assert all(hill_climbing_loop.enough_holdout_items(n) for n in range(5))
    assert "repeat_customers" not in pack_config()["autonomy"]["metric_families"]
    assert "minimum_holdout_items" not in pack_config()["autonomy"]
    assert [i.id for i in load_benchmark() if i.metric_family == "repeat_customers"] == []


# --- solutions ------------------------------------------------------------------------------------
def _patched_paths(patch: Path) -> list[str]:
    return re.findall(r"^\+\+\+ b/(\S+)", patch.read_text(encoding="utf-8"), re.M)


@pytest.mark.skipif(solutions_withheld(), reason=WITHHELD_REASON)
@pytest.mark.parametrize("variant", VARIANTS)
@pytest.mark.parametrize("slug", SLUGS)
def test_each_solution_applies_onto_the_starter(slug: str, variant: str, tmp_path: Path) -> None:
    solution = assignment(slug).solution(variant)
    assert (solution / "README.md").is_file(), "each solution names its trade-off in README.md"
    files = solution / "files"
    overlays = [p.relative_to(files).as_posix() for p in files.rglob("*") if p.is_file()]
    assert EXTENSIONS[slug] in overlays
    for rel in overlays:  # a solution replaces extension points or adds files, never class code
        assert rel == EXTENSIONS[slug] or not (REPO / rel).exists(), rel
        if rel.endswith(".py"):
            ast.parse((files / rel).read_text(encoding="utf-8"), filename=rel)
    patch = solution / "changes.patch"
    if patch.is_file():
        for rel in _patched_paths(patch):
            (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO / rel, tmp_path / rel)
        done = subprocess.run(
            ["git", "apply", "--check", str(patch)], cwd=tmp_path, capture_output=True, text=True
        )
        assert done.returncode == 0, done.stderr


def _module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# (slug, variant) -> why its code still names Harbor & Pine. Each is reported to the lead as
# remaining work: with one of these applied, test_no_class_pack_literals fails in the copy. An entry
# that no longer names anything fails, so the list only shrinks.
NAMES_THE_CLASS_PACK_FOR_NOW = {
    ("agent-loop", "reference"): "the lookup tools name the products and categories tables",
    ("agent-loop", "alternative-one"): "the lookup tools name the products and categories tables",
    ("agent-loop", "alternative-two"): "the lookup tools name the products and categories tables",
    ("verification-loop", "reference"): "the ambiguity terms explain themselves with orders",
    ("verification-loop", "alternative-two"): "the clarifying question names orders",
    ("event-loop", "reference"): "the net revenue query reads the orders table",
    ("event-loop", "alternative-one"): "the net revenue query reads the orders table",
    ("event-loop", "alternative-two"): "the net revenue query reads the orders table",
    ("hill-climbing-loop", "alternative-one"): "the screen's reasons name customers and orders",
    ("hill-climbing-loop", "alternative-two"): "the reach table repeats the router's keywords",
}


@pytest.mark.skipif(solutions_withheld(), reason=WITHHELD_REASON)
@pytest.mark.parametrize("variant", VARIANTS)
@pytest.mark.parametrize("slug", SLUGS)
def test_each_solutions_code_names_no_class_pack_literal(slug: str, variant: str) -> None:
    """A solution follows the rule the course teaches and test_no_class_pack_literals enforces: the
    platform code it adds names nothing of Harbor & Pine, so `make test` in a copy with the solution
    applied does not fail that test. The solutions listed above are the exceptions still owed."""
    scan = PLATFORM / "tests" / "unit" / "test_no_class_pack_literals.py"
    literals = _module("pack_literals", scan)
    regex, files = literals.pattern(), assignment(slug).solution(variant) / "files"
    found = []
    for path in sorted(files.rglob("*.py")):
        rel = path.relative_to(files).as_posix()
        if not rel.startswith(literals.SCANNED) or rel in literals.ALLOWED:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        found += [
            f"{rel}:{node.lineno}: {match.group(0)}"
            for node in literals.literals(tree)
            if (match := regex.search(node.value))
        ]
    if (slug, variant) in NAMES_THE_CLASS_PACK_FOR_NOW:
        assert found, f"remove {slug} {variant} from NAMES_THE_CLASS_PACK_FOR_NOW: it names none"
        return
    assert found == [], "move these names into the pack's files:\n" + "\n".join(found)


@pytest.mark.skipif(solutions_withheld(), reason=WITHHELD_REASON)
@pytest.mark.parametrize("variant", VARIANTS)
@pytest.mark.parametrize("slug", SLUGS)
def test_each_solutions_new_pack_settings_reach_the_template(
    slug: str, variant: str, tmp_path: Path
) -> None:
    """Every pack needs every setting the platform reads (use-in-your-repo/check_pack.py), so a
    solution that adds a setting to the class pack adds it to the template pack too, and the
    template still passes check_pack with the solution applied."""
    patch = assignment(slug).solution(variant) / "changes.patch"
    if not patch.is_file():
        return
    class_pack = "platform/packs/datapilot_us/pack.yaml"
    template = "platform/packs/_template/pack.yaml"
    for rel in {*_patched_paths(patch), class_pack, template}:
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / rel, tmp_path / rel)
    done = subprocess.run(
        ["git", "apply", "--whitespace=nowarn", str(patch)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert done.returncode == 0, done.stderr
    check_pack = _module("check_pack", REPO / "use-in-your-repo" / "check_pack.py")

    def settings(rel: str) -> set[str]:
        return set(check_pack.key_paths(yaml.safe_load((tmp_path / rel).read_text("utf-8"))))

    missing = sorted(settings(class_pack) - settings(template))
    assert missing == [], f"add these settings to {template} in changes.patch: {missing}"


@pytest.mark.parametrize("slug", SLUGS)
def test_each_assignment_has_its_check(slug: str) -> None:
    # check.py is the file a learner runs: it ships in every copy, the public one included.
    assert (assignment(slug).folder / "check.py").is_file()


@pytest.mark.skipif(solutions_withheld(), reason=WITHHELD_REASON)
@pytest.mark.parametrize("slug", SLUGS)
def test_each_assignment_has_its_captured_folder(slug: str) -> None:
    assert (assignment(slug).folder / "solution" / "captured" / "README.md").is_file()


# --- live only ------------------------------------------------------------------------------------
def _live_only():
    spec = importlib.util.spec_from_file_location(
        "live_only", PLATFORM / "tests" / "unit" / "test_live_only.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _assignment_code() -> list[Path]:
    paths = list((PLATFORM / "src" / "datapilot" / "assignments").rglob("*.py"))
    for slug in SLUGS:
        folder = assignment(slug).folder
        paths += [p for p in folder.rglob("*") if p.is_file() and "captured" not in p.parts]
    return paths


def test_assignment_paths_never_reach_doubles_replays_or_captures() -> None:
    live_only = _live_only()
    hits = []
    for path in _assignment_code():
        if path.suffix not in (".py", ".yaml", ".patch"):
            continue
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(REPO).as_posix()
        for line in text.splitlines():
            if path.suffix == ".patch" and line.startswith(("--- a/", "+++ b/")):
                continue  # which file a patch edits, not what a check reaches
            for what, pattern in live_only.FORBIDDEN_TEXT.items():
                if re.search(pattern, line, re.I) and not live_only._allowed(line):
                    hits.append(f"{rel}: {what}: {line.strip()}")
        if path.suffix == ".py":
            for name in live_only._imports(ast.parse(text)):
                if any(name == f or name.startswith(f + ".") for f in live_only.FORBIDDEN_IMPORTS):
                    hits.append(f"{rel}: imports {name}")
        writer = rel.endswith("assignments/solutions.py")  # it writes captures, never reads them
        if not writer and re.search(r"captured", text):
            hits.append(f"{rel}: names a captured run")
    assert hits == [], "\n".join(hits)


def test_the_hill_climbing_check_knows_the_class_gate() -> None:
    spec = importlib.util.spec_from_file_location(
        "hill_climbing_check", assignment("hill-climbing-loop").check_file
    )
    assert spec is not None and spec.loader is not None
    check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(check)
    for name, want in check.UNCHANGED.items():
        assert check.fingerprint(check.LOOP4 / name) == want, f"update UNCHANGED for {name}"
    assert check.evaluation_fingerprint() == check.EVALUATION


def test_the_planted_rule_is_a_valid_proposal() -> None:
    folder = assignment("hill-climbing-loop").folder
    rule = ProposedRule.model_validate(yaml.safe_load((folder / "planted-rule.yaml").read_text()))
    assert rule.evidence_example_ids


# --- the skips of a public copy -------------------------------------------------------------------
def _withheld_skip_reasons(path: Path) -> list[tuple[int, str]]:
    """Every skipif(solutions_withheld(), ...) in a test file, with its reason as written."""
    found = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if not (isinstance(node, ast.Call) and ast.unparse(node.func).endswith("skipif")):
            continue
        if not node.args or "solutions_withheld" not in ast.unparse(node.args[0]):
            continue
        reason = next((k.value for k in node.keywords if k.arg == "reason"), None)
        found.append((node.lineno, ast.unparse(reason) if reason is not None else ""))
    return found


def test_every_withheld_solution_skip_gives_the_one_reason_the_release_accepts() -> None:
    """The release build accepts a skip in a public copy only with WITHHELD_REASON
    (build_release.py), so a skip with its own wording would fail the release, which make verify
    never runs."""
    tests = PLATFORM / "tests"
    found = {
        f"{path.relative_to(tests)}:{line}": reason
        for path in sorted(tests.rglob("test_*.py"))
        for line, reason in _withheld_skip_reasons(path)
    }
    assert len(found) >= 5, "the scan finds the withheld-solution skips"
    other = {where: reason for where, reason in found.items() if reason != "WITHHELD_REASON"}
    assert not other, other
