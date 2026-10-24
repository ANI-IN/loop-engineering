"""Every demo is live: demo paths never reuse a result from an earlier run.

What is forbidden in demo paths (the datapilot package, the console, the Makefile, Compose, and the
demo scripts section-*/demo/run.sh and final-project/run.sh) is reusing model outputs, answers,
grader verdicts, reviewer verdicts, analyzer proposals, or experiment results from earlier runs,
and reaching test doubles or replays. Three kinds of check:

1. An AST import check: no demo path imports test code or a test double.
2. An AST cache check: no function whose result is one of those result types is cached.
3. Text checks for saved result files, replays, and the expected/ folder path.

Allowed, and documented in ALLOWED below: caching database connections and pools
(st.cache_resource), small schema or catalog snapshots, st.cache_data on small reads that are not
model or evaluation results, the word "expected" in identifiers such as expected_status, and
comments about OpenAI's automatic prompt-prefix billing (cached input tokens)."""

from __future__ import annotations

import ast
import re

import pytest

from datapilot.settings import PLATFORM, REPO

PY_FOLDERS = (PLATFORM / "src" / "datapilot", PLATFORM / "console")
# The demo scripts the instructor runs in class sit next to their expected/ folders: every one is
# read, found by glob so a new section is read too.
DEMO_SCRIPTS = sorted(
    p.relative_to(REPO).as_posix()
    for p in [*REPO.glob("section-*/demo/run.sh"), REPO / "final-project" / "run.sh"]
)
TEXT_PATHS = ["platform/src", "platform/console", "Makefile", "compose.yaml", *DEMO_SCRIPTS]

# The result types a demo must always produce fresh.
RESULT_TYPES = (
    "answer",
    "envelope",
    "grader_result",
    "grader_verdict",
    "verdict",
    "review",
    "proposal",
    "proposed_rule",
    "diagnosis",
    "experiment_result",
    "experiment",
    "item_result",
)
_RESULT = "|".join(RESULT_TYPES)

# 1. Modules no demo path may import: test code and every test double.
FORBIDDEN_IMPORTS = (
    "tests",
    "conftest",
    "pytest",
    "unittest.mock",
    "langchain_core.language_models.fake",
    "langchain_core.language_models.fake_chat_models",
    "langchain_community",
)

# 2. Caching decorators; a cached function whose name names a result type is forbidden.
CACHE_DECORATORS = {"lru_cache", "cache", "cache_data", "cached", "memoize"}

# 3. Text patterns: what each one forbids.
FORBIDDEN_TEXT = {
    "saved result files": rf"({_RESULT})s?[\w-]*\.(json|jsonl|pkl|pickle|parquet|csv|sqlite)\b",
    "replays and recordings": r"\breplay|cassette|\bvcr\b|record(ed)?_(run|response)s?\b",
    "the expected/ folder": r"(^|[\s\"'(/])expected/",
    "test fixtures and doubles": r"platform/tests|(^|[\s\"'(/])fixtures/|GenericFakeChatModel|"
    r"Fake(ListLLM|ListChatModel|MessagesListChatModel)|StubAgent|stub_agent",
}

# Lines that match a forbidden pattern but are allowed, each with its reason.
ALLOWED = {
    r"st\.cache_resource": "database connections and pools",
    r"cached_input|cache_read|prompt[- ]?(prefix|cach)": "OpenAI automatic prompt-prefix billing",
    r"(catalog|schema)[_ ]snapshot": "small schema or catalog snapshots",
}


def _allowed(line: str) -> bool:
    return any(re.search(pattern, line, re.I) for pattern in ALLOWED)


def _imports(tree: ast.AST) -> list[str]:
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.append(node.module)
    return names


def _decorator_name(node: ast.expr) -> str:
    target = node.func if isinstance(node, ast.Call) else node
    if isinstance(target, ast.Attribute):
        return target.attr
    return target.id if isinstance(target, ast.Name) else ""


def _trees():
    for folder in PY_FOLDERS:
        for path in folder.rglob("*.py"):
            yield path, ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def test_demo_paths_never_import_test_doubles() -> None:
    reached = [
        f"{path.relative_to(REPO).as_posix()}: {name}"
        for path, tree in _trees()
        for name in _imports(tree)
        if any(name == f or name.startswith(f + ".") for f in FORBIDDEN_IMPORTS)
    ]
    assert reached == []


def test_no_result_is_cached_across_runs() -> None:
    cached = []
    for path, tree in _trees():
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            decorators = {_decorator_name(d) for d in node.decorator_list}
            if decorators & CACHE_DECORATORS and re.search(_RESULT, node.name, re.I):
                cached.append(f"{path.relative_to(REPO).as_posix()}: {node.name}")
    assert cached == []


@pytest.mark.parametrize("what", sorted(FORBIDDEN_TEXT))
def test_demo_paths_never_reach(what: str, repo_scan) -> None:
    hits = [line for line in repo_scan(FORBIDDEN_TEXT[what], *TEXT_PATHS) if not _allowed(line)]
    assert hits == []


def test_the_text_checks_read_every_demo_script() -> None:
    from datapilot.names import SECTIONS_BY_SLUG

    expected = {f"{s.folder}/demo/run.sh" for s in SECTIONS_BY_SLUG.values()}
    assert expected | {"final-project/run.sh"} <= set(TEXT_PATHS)
    assert all((REPO / path).is_file() for path in DEMO_SCRIPTS)


@pytest.mark.parametrize(
    ("line", "allowed"),
    [
        ("expected_status: answered", False),
        ("@st.cache_resource\ndef pool():", True),
        ("# OpenAI bills cached_input tokens at a lower price", True),
        ("SNAPSHOT = load_catalog_snapshot()", True),
    ],
)
def test_the_allow_list_covers_what_it_documents(line: str, allowed: bool) -> None:
    assert _allowed(line) is allowed
    if not allowed:
        assert not any(re.search(p, line, re.I) for p in FORBIDDEN_TEXT.values())


def test_forbidden_patterns_catch_reused_results() -> None:
    examples = [
        "answers = json.load(open('answers.json'))",
        "load('experiment_results.parquet')",
        "replay_run(run_id)",
        "Path('section-1-agent-loop/demo/expected/terminal.txt')",
    ]
    for example in examples:
        assert any(re.search(p, example, re.I) for p in FORBIDDEN_TEXT.values()), example
