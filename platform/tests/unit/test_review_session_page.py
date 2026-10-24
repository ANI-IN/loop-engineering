"""The Thursday review's run sheet, zero tokens: the Assignment 4 check runs on a project and ports
of its own, which neither the other checks' stack, the class stack, nor the tests' Postgres uses,
and every walkthrough excerpt's line range is the code it names, read from the files themselves."""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest
import stack_for_tests
import yaml

from datapilot.assignments import WITHHELD_REASON, solutions_withheld
from datapilot.assignments.stack import CLASS_PROJECT, DEFAULTS
from datapilot.settings import REPO

PAGE = REPO / "docs" / "review-session.md"
PORTS = ("POSTGRES_PORT", "API_PORT", "CONSOLE_PORT")


def _page() -> str:
    return PAGE.read_text(encoding="utf-8")


def _class_ports() -> dict[str, str]:
    """The class stack's host ports: the defaults compose.yaml publishes."""
    text = (REPO / "compose.yaml").read_text(encoding="utf-8")
    return {name: re.search(rf"\$\{{{name}:-(\d+)\}}", text).group(1) for name in PORTS}


def _review_settings() -> dict[str, str]:
    """The settings the page gives the Assignment 4 check of the review."""
    block = re.search(r"```bash\n(.*?)```", _page(), re.S)
    assert block, "the page shows the Assignment 4 command in a bash block"
    found = dict(re.findall(r"\b(COMPOSE_PROJECT_NAME|[A-Z]+_PORT)=(\S+)", block.group(1)))
    assert set(found) == {"COMPOSE_PROJECT_NAME", *PORTS}, found
    return found


def test_the_review_stack_shares_no_port_with_any_other_stack() -> None:
    review = _review_settings()
    taken = {
        "the other checks' stack": {DEFAULTS[name] for name in PORTS},
        "the class stack": set(_class_ports().values()),
        "the tests' Postgres": {stack_for_tests.DEFAULT_PORT},
    }
    mine = {review[name] for name in PORTS}
    assert len(mine) == 3, "three ports of its own"
    for where, ports in taken.items():
        assert not mine & ports, f"the review stack takes a port of {where}: {mine & ports}"
    assert review["COMPOSE_PROJECT_NAME"] not in {DEFAULTS["COMPOSE_PROJECT_NAME"], CLASS_PROJECT}


def test_the_defaults_never_share_a_port_with_the_class_stack() -> None:
    assert not {DEFAULTS[name] for name in PORTS} & set(_class_ports().values())


def test_the_review_page_states_the_ports_it_uses() -> None:
    review, page = _review_settings(), _page()
    assert all(review[name] in page.replace(review[name], "", 1) for name in PORTS), (
        "the text names each port of the review stack, beside the command"
    )
    reset = re.search(r"COMPOSE_PROJECT_NAME=(\S+) POSTGRES_PORT=(\S+) uv run python -m", page)
    assert reset, "the page gives the reset of the review stack"
    assert reset.groups() == (review["COMPOSE_PROJECT_NAME"], review["POSTGRES_PORT"])


def test_the_page_never_sends_a_check_reset_to_the_class_stack() -> None:
    assert "make reset NAME=<slug>" not in _page()
    assert "python -m datapilot.assignments reset <slug>" in _page()


# --- the walkthrough excerpts ---------------------------------------------------------------------
# Each excerpt's named code: the top-level definitions its line ranges must hold, the first one
# starting the first range. (block, excerpt number) -> [(file name, definition), ...]
NAMED = {
    ("Assignment 1", 1): [("extension.py", "score"), ("extension.py", "lookup_values")],
    ("Assignment 1", 2): [("extension.py", "WORKING_METHOD")],
    ("Assignment 1", 3): [("extension.py", "_unresolved_tie"), ("extension.py", "with_matches")],
    ("Assignment 2", 1): [("clarify_or_abstain.py", "ClarifyOrAbstainGrader")],
    ("Assignment 2", 2): [
        ("clarify_or_abstain.py", "TERMS"),
        ("clarify_or_abstain.py", "defined_terms"),
    ],
    ("Assignment 2", 3): [("personal_data_leak.py", "PersonalDataLeakGrader")],
    ("Assignment 2", 4): [("extension.py", "question_graders"), ("extension.py", "answer_graders")],
    ("Assignment 3", 1): [
        ("extension.py", "anomaly_event_id"),
        ("extension.py", "request_anomaly_check"),
        ("extension.py", "schedule"),
    ],
    ("Assignment 3", 2): [
        ("extension.py", "NET_REVENUE_SQL"),
        ("extension.py", "baseline_days"),
        ("extension.py", "measure"),
        ("extension.py", "is_anomaly"),
    ],
    ("Assignment 3", 3): [("extension.py", "publish")],
    ("Assignment 3", 4): [("extension.py", "JOB_QUEUES")],
    ("Assignment 4", 1): [("repeat_customers.yaml", "repeat-rate-fy2025")],
    ("Assignment 4", 3): [("extension.py", "CRITIC_GUIDANCE")],
    ("Assignment 4", 4): [
        ("extension.py", "enough_holdout_items"),
        ("eligibility.py", "eligible_families"),
    ],
}
PATH = re.compile(r"`([\w./-]+\.(?:py|yaml))`|`([\w./-]+/)`")
RANGE = re.compile(r"\blines? (\d+)(?: to (\d+))?|\band (\d+) to (\d+)")


def _blocks() -> dict[str, str]:
    parts = re.split(r"^## (Assignment \d): .*$", _page(), flags=re.M)
    return dict(zip(parts[1::2], parts[2::2], strict=True))


def _excerpts() -> list[tuple[str, int, list[tuple[Path, int, int]]]]:
    """(block, number, [(file, first line, last line), ...]) for every excerpt with line ranges."""
    found = []
    for block, text in _blocks().items():
        if "Walkthrough excerpts" not in text:
            continue
        _, _, rest = text.partition("Walkthrough excerpts")
        intro, _, listing = rest.partition("\n1. ")
        base = PATH.search(intro)
        base_file = base.group(1) if base and base.group(1) else None
        base_dir = base.group(2) if base and base.group(2) else ""
        current = base_file  # "the same file" is the one the excerpt before named
        for number, item in enumerate(re.split(r"\n\d\. ", "\n1. " + listing)[1:], start=1):
            item = item.split("\n\n")[0]
            ranges = []
            for token in re.finditer(f"{PATH.pattern}|{RANGE.pattern}", item):
                if token.group(2):
                    continue
                if path := token.group(1):
                    whole = path.startswith(("section-", "platform/"))
                    current = path if whole else f"{base_dir}{path}"
                    continue
                numbers = [g for g in token.groups()[2:] if g]
                first, last = int(numbers[0]), int(numbers[-1])
                assert current, f"{block} excerpt {number}: lines without a file"
                ranges.append((REPO / current, first, last))
            if ranges:
                found.append((block, number, ranges))
    return found


def _definitions(path: Path) -> dict[str, tuple[int, int]]:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".yaml":
        lines = text.splitlines()
        starts = [i for i, line in enumerate(lines, start=1) if line.startswith("- id: ")]
        ends = [*(s - 1 for s in starts[1:]), len(lines)]
        out = {}
        for start, end in zip(starts, ends, strict=True):
            while end > start and not lines[end - 1].strip():
                end -= 1
            out[lines[start - 1].removeprefix("- id: ").strip()] = (start, end)
        assert yaml.safe_load(text)
        return out
    out = {}
    for node in ast.parse(text).body:
        if isinstance(node, ast.Assign):
            names = [ast.unparse(t) for t in node.targets]
        elif isinstance(node, ast.AnnAssign):
            names = [ast.unparse(node.target)]
        else:
            names = [getattr(node, "name", "")]
        for name in names:
            out[name] = (node.lineno, node.end_lineno or node.lineno)
    return out


@pytest.mark.skipif(solutions_withheld(), reason=WITHHELD_REASON)
def test_every_excerpt_range_is_the_code_it_names() -> None:
    excerpts = _excerpts()
    assert {(block, number) for block, number, _ in excerpts} == set(NAMED), (
        "every excerpt with line ranges has its named code in NAMED, and no more"
    )
    for block, number, ranges in excerpts:
        where = f"{block} excerpt {number}"
        for index, (file_name, name) in enumerate(NAMED[(block, number)]):
            held = [(p, a, b) for p, a, b in ranges if p.name == file_name]
            assert held, f"{where}: no range in {file_name}"
            for path, _, _ in held:
                assert path.is_file(), f"{where}: {path} does not exist"
            spans = {p: _definitions(p) for p, _, _ in held}
            defined = [(p, a, b) for p, a, b in held if name in spans[p]]
            assert defined, f"{where}: {name} is not defined in {file_name}"
            start, end = spans[defined[0][0]][name]
            inside = [(a, b) for _, a, b in defined]
            assert any(a <= start and end <= b for a, b in inside), (
                f"{where}: {name} is at lines {start} to {end}, outside {inside}"
            )
            if index == 0:
                assert defined[0][1] == start, (
                    f"{where}: the excerpt starts at line {defined[0][1]}, {name} at {start}"
                )
