"""The link check (platform/scripts/check_links.py): every relative link and anchor in every shipped
Markdown file resolves, no link names a file the release leaves out, and every link to the course's
GitHub repository names a shipped page and heading."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPTS = REPO / "platform" / "scripts"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


check_links = _load("check_links")
ADDRESS = check_links.repository_address()

RELEASE = """include = ["README.md", "docs/", "slides/", "platform/"]
exclude = ["slides/private/"]
internal_files = ["DRAFT.md"]
build_only = []
"""


def _tree(root: Path, pages: dict[str, str]) -> Path:
    (root / "platform" / "config").mkdir(parents=True)
    (root / "platform" / "config" / "release.toml").write_text(RELEASE, encoding="utf-8")
    for rel, text in pages.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")
    return root


def _problems(root: Path) -> list[str]:
    return check_links.run(root)[2]


def test_every_shipped_markdown_link_in_this_repository_resolves() -> None:
    checked, skipped, problems = check_links.run(REPO)
    assert problems == []
    assert "SECURITY.md" in checked and "slides/outline.md" in checked
    assert "platform/console/DESIGN.md" in checked
    assert len(checked) + len(skipped) == len(check_links.shipped_markdown(REPO))


def test_the_files_are_the_shipped_markdown_files(tmp_path: Path) -> None:
    root = _tree(
        tmp_path,
        {
            "README.md": "# Title\n",
            "docs/page.md": "# Page\n",
            "docs/DRAFT.md": "# Internal\n",
            "slides/private/notes.md": "# Not shipped\n",
            "research/notes.md": "# Not included\n",
        },
    )
    assert check_links.shipped_markdown(root) == ["README.md", "docs/page.md"]


def test_a_good_link_and_anchor_pass(tmp_path: Path) -> None:
    root = _tree(
        tmp_path,
        {
            "README.md": "# Title\n\nSee [the page](docs/page.md#a-heading) and [here](#title).\n",
            "docs/page.md": "# Page\n\n## A heading\n",
        },
    )
    assert _problems(root) == []


def test_a_broken_relative_link_names_the_file_line_and_target(tmp_path: Path) -> None:
    root = _tree(tmp_path, {"README.md": "# Title\n\nText.\nSee [gone](docs/gone.md).\n"})
    assert _problems(root) == ["README.md:4: link target docs/gone.md does not exist"]


def test_a_broken_anchor_is_found(tmp_path: Path) -> None:
    root = _tree(
        tmp_path,
        {"README.md": "# Title\n\n[x](docs/page.md#nowhere)\n", "docs/page.md": "# Page\n"},
    )
    assert _problems(root) == [
        "README.md:3: link target docs/page.md#nowhere: no heading or id 'nowhere' in page.md"
    ]


def test_a_link_inside_a_code_block_is_not_a_link(tmp_path: Path) -> None:
    root = _tree(tmp_path, {"README.md": "# Title\n\n```text\n[x](gone.md)\n```\n"})
    assert _problems(root) == []


def test_a_link_to_a_file_the_release_leaves_out_fails_here_too(tmp_path: Path) -> None:
    root = _tree(
        tmp_path,
        {
            "README.md": "# Title\n\n[notes](slides/private/notes.md) and [plan](docs/DRAFT.md)\n",
            "slides/private/notes.md": "# Notes\n",
            "docs/DRAFT.md": "# Plan\n",
        },
    )
    assert _problems(root) == [
        "README.md:3: link target docs/DRAFT.md: the release leaves out docs/DRAFT.md",
        "README.md:3: link target slides/private/notes.md: the release leaves out "
        "slides/private/notes.md",
    ]


def test_a_file_the_release_leaves_out_is_never_read(tmp_path: Path) -> None:
    root = _tree(
        tmp_path,
        {"README.md": "# Title\n", "slides/private/notes.md": "# Notes\n\n[x](gone.md)\n"},
    )
    assert _problems(root) == []


@pytest.mark.parametrize(
    ("link", "problem"),
    [
        ("tree/main/docs", None),
        ("blob/main/docs/page.md#a-heading", None),
        ("tree/main/docs#a-folder-heading", None),
        ("tree/main/docs/gone", "docs/gone does not exist"),
        ("blob/main/docs/page.md#nowhere", "no heading or id 'nowhere' in docs/page.md"),
        ("tree/main/docs#nowhere", "no heading or id 'nowhere' in docs/README.md"),
        ("blob/main/slides/private/notes.md", "the release leaves out slides/private/notes.md"),
    ],
)
def test_a_link_to_the_course_repository_names_a_shipped_page_and_heading(
    tmp_path: Path, link: str, problem: str | None
) -> None:
    root = _tree(
        tmp_path,
        {
            "slides/outline.md": f"# Outline\n\nLink: Demo page on GitHub | {ADDRESS}/{link}\n",
            "docs/README.md": "# Docs\n\n## A folder heading\n",
            "docs/page.md": "# Page\n\n## A heading\n",
            "slides/private/notes.md": "# Notes\n",
        },
    )
    expected = (
        []
        if problem is None
        else [f"slides/outline.md:3: repository link {ADDRESS}/{link}: {problem}"]
    )
    assert _problems(root) == expected


def test_main_exits_1_and_prints_each_problem(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _tree(tmp_path, {"README.md": "# Title\n\n[gone](gone.md)\n"})
    assert check_links.main(["--root", str(root)]) == 1
    out = capsys.readouterr().out
    assert "x README.md:3: link target gone.md does not exist" in out
    assert out.strip().endswith("1 files checked, 1 problems, 0 skipped")


def test_main_exits_0_on_a_clean_tree(tmp_path: Path) -> None:
    root = _tree(tmp_path, {"README.md": "# Title\n\n[me](#title)\n"})
    assert check_links.main(["--root", str(root)]) == 0
