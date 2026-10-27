"""The checks of every published file (platform/scripts/check_repo_files.py): data files (YAML,
TOML, JavaScript Object Notation (JSON)), schemas, make commands, structure, release rules and
secrets. Each passes on this tree, and each fails with the file and the reason on one deliberate
fault (zero tokens; temporary trees and throwaway repositories only)."""

from __future__ import annotations

import copy
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

CHECKOUT = Path(__file__).resolve().parents[3]
SCRIPTS = CHECKOUT / "platform" / "scripts"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


checks = _load("check_repo_files", SCRIPTS / "check_repo_files.py")
check_pack = _load("check_pack", CHECKOUT / "use-in-your-repo" / "check_pack.py")


def _write(root: Path, files: dict[str, str]) -> Path:
    for rel, text in files.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    return root


def _class_pack() -> dict:
    return yaml.safe_load((CHECKOUT / "platform/packs/datapilot_us/pack.yaml").read_text("utf-8"))


# -- this tree passes -----------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["data", "schemas", "structure"])
def test_this_tree_passes(name: str) -> None:
    problems, count = {
        "data": checks.data_problems,
        "schemas": checks.schema_problems,
        "structure": checks.structure_problems,
    }[name](CHECKOUT)
    assert problems == [] and count > 0


def test_this_tree_holds_no_key_like_text() -> None:
    problems, count = checks.secret_problems(CHECKOUT, history=False)
    assert problems == [] and count > 100


@pytest.mark.skipif(shutil.which("make") is None, reason="needs GNU make")
def test_every_make_command_on_a_page_names_a_target_and_passes_a_dry_run() -> None:
    problems, count = checks.make_target_problems(CHECKOUT)
    assert problems == [], "\n".join(problems)
    assert count > 100


def test_the_command_line_lists_the_checks_and_refuses_an_unknown_one(capsys) -> None:
    assert checks.main(["--list"]) == 0
    listed = [line.split(":")[0] for line in capsys.readouterr().out.splitlines()]
    assert listed == ["data", "schemas", "make-targets", "structure", "release", "secrets"]
    assert checks.main(["no-such-check"]) == 2
    assert "unknown check no-such-check" in capsys.readouterr().out


# -- data -----------------------------------------------------------------------------------------


def test_a_key_written_twice_fails_and_a_merge_key_does_not() -> None:
    assert checks.parse_yaml("base: &base {a: 1}\nservice:\n  <<: *base\n  a: 2\n") == [
        {"base": {"a": 1}, "service": {"a": 2}}
    ]
    assert "twice" in checks.parse_problem("YAML", "a: 1\nb: 2\na: 3\n")
    assert "twice" in checks.parse_problem("JSON", '{"a": 1, "a": 2}')


def test_every_document_of_a_yaml_file_is_read() -> None:
    assert checks.parse_yaml("a: 1\n---\nb: 2\n") == [{"a": 1}, {"b": 2}]
    assert checks.parse_problem("YAML", "a: 1\n---\nb: [unclosed\n")


def test_an_invalid_data_file_is_named_with_its_kind(tmp_path: Path) -> None:
    _write(
        tmp_path,
        {
            "good.yaml": "a: 1\n",
            "bad.yaml": "a: [1, 2\n",
            "bad.toml": "a = \n",
            "bad.json": "{",
            "drawing.excalidraw": "{]",
            "notes.md": "a: [\n",
        },
    )
    problems, count = checks.data_problems(tmp_path)
    assert count == 5
    assert [p.split(":")[0] for p in problems] == [
        "bad.json",
        "bad.toml",
        "bad.yaml",
        "drawing.excalidraw",
    ]
    assert "not valid TOML" in problems[1] and "not valid YAML" in problems[2]


# -- schemas --------------------------------------------------------------------------------------


def _model_paths(model, prefix: str = ""):
    for name, field in model.model_fields.items():
        if field.is_required():
            yield prefix + name
            if isinstance(field.annotation, type) and issubclass(
                field.annotation, checks.BaseModel
            ):
                yield from _model_paths(field.annotation, f"{prefix}{name}.")


def test_the_pack_schema_names_every_key_the_class_pack_holds() -> None:
    """The schema and use-in-your-repo/check_pack.py require the same keys: a key added to the
    class pack (and so to every pack) is added to PackFile too."""
    assert set(_model_paths(checks.PackFile)) == set(check_pack.key_paths(_class_pack()))


@pytest.mark.parametrize("pack", ["datapilot_us", "_template"])
def test_both_packs_hold_the_schema(pack: str) -> None:
    assert checks.pack_problems(CHECKOUT, f"platform/packs/{pack}/pack.yaml") == []


def _pack_tree(tmp_path: Path, data: dict) -> str:
    rel = "platform/packs/datapilot_us/pack.yaml"
    _write(tmp_path, {rel: yaml.safe_dump(data)})
    return rel


def test_a_pack_missing_a_key_names_the_key(tmp_path: Path) -> None:
    data = _class_pack()
    del data["limits"]["row_cap"]
    rel = _pack_tree(tmp_path, data)
    assert checks.pack_problems(tmp_path, rel) == [f"{rel}: limits.row_cap: Field required"]


def test_a_pack_value_of_the_wrong_type_or_an_unknown_key_fails(tmp_path: Path) -> None:
    data = copy.deepcopy(_class_pack())
    data["limits"]["row_cap"] = "fifty"
    data["models"]["analyst"]["temperature"] = 0.2  # never passed: not a pack setting
    data["autonomy"]["default_level"] = "fully_automatic"
    data["autonomy"]["family_keywords"][0]["pattern"] = "average (order"
    rel = _pack_tree(tmp_path, data)
    problems = "\n".join(checks.pack_problems(tmp_path, rel))
    assert "limits.row_cap: Input should be a valid integer" in problems
    assert "models.analyst.temperature: Extra inputs are not permitted" in problems
    assert "autonomy.default_level" in problems
    assert "not a regular expression" in problems


def test_a_pack_named_for_another_folder_fails(tmp_path: Path) -> None:
    data = _class_pack()
    data["name"] = "another_pack"
    rel = _pack_tree(tmp_path, data)
    assert "not the folder name 'datapilot_us'" in checks.pack_problems(tmp_path, rel)[0]


def test_a_registry_or_benchmark_that_breaks_its_model_is_named(tmp_path: Path) -> None:
    for rel in ("platform/demos/registry.yaml", "platform/planted/registry.yaml"):
        (tmp_path / rel).parent.mkdir(parents=True)
        shutil.copy(CHECKOUT / rel, tmp_path / rel)
    demos = yaml.safe_load((tmp_path / "platform/demos/registry.yaml").read_text("utf-8"))
    demos[0]["trigger"]["make"] = "make demo NAME=another-demo"
    demos[1]["planted"] = ["BUG_NOT_PLANTED"]
    _write(tmp_path, {"platform/demos/registry.yaml": yaml.safe_dump(demos)})
    problems = checks.registry_problems(tmp_path)
    assert len(problems) == 1 and "trigger.make must be 'make demo NAME=" in problems[0]
    demos[0]["trigger"]["make"] = f"make demo NAME={demos[0]['id']}"
    _write(tmp_path, {"platform/demos/registry.yaml": yaml.safe_dump(demos)})
    assert checks.registry_problems(tmp_path) == [
        "platform/demos/registry.yaml: agent-texas-last-quarter: unknown planted item "
        "BUG_NOT_PLANTED"
    ]
    pack = tmp_path / "platform/packs/datapilot_us"
    _write(pack, {"benchmark/dev.yaml": "- {id: one-question}\n", "knowledge/v1.yaml": "[]\n"})
    problems = checks.benchmark_problems(tmp_path, pack)
    assert problems[0].startswith("platform/packs/datapilot_us/benchmark/dev.yaml: one-question:")
    assert any(p.startswith("platform/packs/datapilot_us/knowledge/v1.yaml") for p in problems)


def test_the_keyed_settings_files_hold_their_top_level_keys(tmp_path: Path) -> None:
    for rel in (checks.STREAMLIT_SETTINGS, checks.GUIDE, checks.MEASUREMENTS):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(CHECKOUT / rel, tmp_path / rel)
    assert checks.keyed_file_problems(tmp_path) == []
    _write(tmp_path, {checks.GUIDE: '{"title": "x", "output": "x.pdf", "partz": []}'})
    assert checks.keyed_file_problems(tmp_path) == [
        "guide/guide.json: no top-level key 'parts'",
        "guide/guide.json: 'partz' is not a setting the guide reads",
    ]


# -- make-targets ---------------------------------------------------------------------------------

PAGE = """# A page

Run `make up`, then `make demo NAME=agent-simple-question PLANTED=1`; to make sure, read on.

```bash
make preflight PURPOSE=class  # before the class
make reset NAME=<section slug>
make <target>
```

In prose, make demo NAME=not-read is not a command.
"""


def test_make_commands_are_read_from_code_only() -> None:
    found = [(c.line, c.text) for c in checks.make_commands("page.md", PAGE)]
    assert found == [
        (3, "make up"),
        (3, "make demo NAME=agent-simple-question PLANTED=1"),
        (6, "make preflight PURPOSE=class"),
        (7, "make reset NAME=<section slug>"),
    ]


def test_a_named_demo_section_or_purpose_must_exist() -> None:
    def problems(text: str) -> list[str]:
        (command,) = checks.make_commands("page.md", f"`{text}`")
        return checks.value_problems(command, {"agent-simple-question"})

    assert problems("make demo NAME=agent-simple-question") == []
    assert problems("make demo NAME=<slug>") == []
    assert problems("make verify-assignments NAME='event-loop agent-loop'") == []
    assert problems("make preflight PURPOSE=class|rehearsal|thursday-review|development") == []
    assert problems("make demo NAME=agent-simple-questions") == [
        "no demo 'agent-simple-questions' in platform/demos/registry.yaml"
    ]
    assert problems("make reset NAME=agent-loops") == ["no section 'agent-loops' (datapilot.names)"]
    assert problems("make preflight PURPOSE=classes") == ["no session purpose 'classes'"]


@pytest.mark.skipif(shutil.which("make") is None, reason="needs GNU make")
def test_a_page_naming_a_missing_target_fails(tmp_path: Path) -> None:
    shutil.copy(CHECKOUT / "Makefile", tmp_path / "Makefile")
    shutil.copytree(CHECKOUT / "platform/demos", tmp_path / "platform/demos")
    _write(tmp_path, {"README.md": "Run `make up`, then `make warm-up`.\n"})
    problems, count = checks.make_target_problems(tmp_path)
    assert count == 2
    assert problems == ["README.md:1: `make warm-up`: no target 'warm-up' in the Makefile"]


# -- structure ------------------------------------------------------------------------------------


def test_the_run_lists_of_a_demo_script_are_read() -> None:
    text = (CHECKOUT / "section-1-agent-loop/demo/run.sh").read_text(encoding="utf-8")
    lists = checks.run_lists(text)
    assert "agent-simple-question" in lists["CORE_DEMOS"]
    assert lists["OPTIONAL_DEMOS"] == ["agent-texas-last-quarter"]


def _structure_tree(tmp_path: Path) -> Path:
    for rel in ("platform/demos", "section-1-agent-loop"):
        shutil.copytree(CHECKOUT / rel, tmp_path / rel, ignore=shutil.ignore_patterns("*.png"))
    for png in (CHECKOUT / "section-1-agent-loop/demo/expected").glob("*.png"):
        (tmp_path / "section-1-agent-loop/demo/expected" / png.name).write_bytes(b"png")
    return tmp_path


def _section_one(problems: list[str]) -> list[str]:
    return [p for p in problems if p.startswith("section-1-agent-loop/")]


def test_a_demo_without_its_run_sh_entry_fails(tmp_path: Path) -> None:
    root = _structure_tree(tmp_path)
    assert _section_one(checks.demo_problems(root)) == []
    run = root / "section-1-agent-loop/demo/run.sh"
    run.write_text(
        run.read_text(encoding="utf-8").replace(" agent-unbounded-rows)", ")", 1), "utf-8"
    )
    assert _section_one(checks.demo_problems(root)) == [
        "section-1-agent-loop/demo/run.sh: agent-unbounded-rows is not in CORE_DEMOS"
    ]


def test_a_demo_without_its_page_walkthrough_or_expected_output_fails(tmp_path: Path) -> None:
    root = _structure_tree(tmp_path)
    folder = root / "section-1-agent-loop/demo"
    for name, old, new in (
        ("README.md", "### Unbounded rows", "### Rows without a bound"),
        ("walkthrough.md", "### platform/src/datapilot/loop1_agent/analyst.py, lines 72-86", "x"),
        ("expected/README.md", "## The confident wrong answer", "## The wrong answer"),
    ):
        page = folder / name
        page.write_text(page.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")
    (folder / "expected/agent-simple-question-answer.png").unlink()
    problems = _section_one(checks.demo_problems(root))
    shown = "'### platform/src/datapilot/loop1_agent/analyst.py, lines 72-86'"
    assert problems == [
        f"section-1-agent-loop/demo/walkthrough.md: no section {shown} for the demo "
        "agent-simple-question",
        "section-1-agent-loop/demo/expected/README.md: '## The simple question' links "
        "agent-simple-question-answer.png, which is missing",
        f"section-1-agent-loop/demo/walkthrough.md: no section {shown} for the demo "
        "agent-texas-last-quarter",
        "section-1-agent-loop/demo/expected/README.md: no part '## The confident wrong answer' "
        "for the demo agent-confident-wrong-answer",
        "section-1-agent-loop/demo/README.md: no part '### Unbounded rows' for the demo "
        "agent-unbounded-rows",
    ]


def test_an_assignment_without_its_check_fails(tmp_path: Path) -> None:
    root = _structure_tree(tmp_path)
    (root / "section-1-agent-loop/assignment/check.py").unlink()
    problems = checks.structure_problems(root)[0]
    assert "section-1-agent-loop/assignment/check.py: missing" in problems
    assert "section-3-event-loop: missing (the folder of Section 3: Event loop)" in problems


# -- release --------------------------------------------------------------------------------------

RELEASE_LIST = """
include = ["README.md", ".gitignore", "platform/", "section-*/"]
exclude = ["research/", "section-*/assignment/solution/"]
solutions = "section-*/assignment/solution/"
# Names of its own, so the release never drops this test for naming a file it leaves out.
internal_files = ["WORKING-NOTES.md"]
build_only = ["platform/scripts/build_machine.sh"]
host_path_examples = ['<[a-z]+>']
deny_patterns = ['smith\\.langchain\\.com/o/[0-9a-f]{8}-[0-9a-f]{4}-']
pages = []
"""


# A throwaway repository's commits carry a test identity, as in test_build_release.py.
IDENTITY = ["-c", "user.name=t", "-c", "user.email=t@example.com"]


def _git(repository: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repository), *IDENTITY, *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def _repository(root: Path, files: dict[str, str]) -> Path:
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _write(root, {"platform/config/release.toml": RELEASE_LIST, **files})
    _git(root, "add", "--all", "--force")  # a file the tree's .gitignore names is the fault
    _git(root, "commit", "-q", "-m", "tree")
    return root


PUBLIC = {
    "README.md": "# A course\n\nRun `make up`.\n",
    ".gitignore": ".env\nsection-*/assignment/solution/\n",
    "platform/src/app.py": "VALUE = 1\n",
}


def test_a_public_copy_passes_and_one_holding_a_left_out_file_fails(tmp_path: Path) -> None:
    public = _repository(tmp_path / "public", PUBLIC)
    assert checks.release_problems(public, []) == ([], 4)
    leaked = _repository(
        tmp_path / "leaked",
        {
            **PUBLIC,
            "platform/WORKING-NOTES.md": "internal\n",
            "section-1-agent-loop/assignment/solution/answer.py": "ANSWER = 42\n",
        },
    )
    problems, _ = checks.release_problems(leaked, [])
    assert [p.split(":")[0] for p in problems] == [
        "platform/WORKING-NOTES.md",
        "section-1-agent-loop/assignment/solution/answer.py",
    ]


def test_the_build_may_hold_what_the_release_leaves_out(tmp_path: Path) -> None:
    build = _repository(
        tmp_path / "build",
        {
            **PUBLIC,
            "WORKING-NOTES.md": "internal\n",
            "platform/scripts/build_machine.sh": "echo build\n",
            "section-1-agent-loop/assignment/solution/answer.py": "ANSWER = 42\n",
        },
    )
    assert checks.release_problems(build, [])[0] == []


def test_published_solutions_pass_once_the_gitignore_stops_withholding_them(
    tmp_path: Path,
) -> None:
    files = {**PUBLIC, ".gitignore": ".env\n"}
    files["section-1-agent-loop/assignment/solution/answer.py"] = "ANSWER = 42\n"
    assert checks.release_problems(_repository(tmp_path / "public", files), [])[0] == []


def test_key_like_text_a_placeholder_an_organization_link_or_a_deny_word_fails(
    tmp_path: Path,
) -> None:
    key = "sk-" + "Ab1" * 8  # built here, so this file holds no key-like text
    link = "https://smith.langchain.com/o/" + "0123abcd-0123-4567"
    page = "# A course\n\nRun `make up` on [CLASS DATE] with the Harbor word.\n"
    repository = _repository(
        tmp_path / "public",
        {
            **PUBLIC,
            "README.md": page,
            "platform/src/app.py": f'KEY = "{key}"\nTRACE = "{link}"\n',
        },
    )
    problems, _ = checks.release_problems(repository, ["harbor"])
    assert problems == [
        "README.md: deny word #1",
        "platform/src/app.py: key-like text",
        "platform/src/app.py: deny pattern #1",
        "README.md:3: placeholder text (a square-bracket placeholder)",
    ]
    assert key not in "\n".join(problems)


# -- secrets --------------------------------------------------------------------------------------


def test_a_key_anywhere_in_the_tree_is_found_and_never_printed(tmp_path: Path, capsys) -> None:
    key = "lsv2_" + "pt_" + "0a1b2c3d4e" * 3
    _write(tmp_path, {"notes/scratch.txt": f"LANGSMITH_API_KEY={key}\n", "README.md": "# Hi\n"})
    problems, count = checks.secret_problems(tmp_path, history=False)
    assert count == 2
    assert problems == ["notes/scratch.txt: key-like text (lsv2: lsv2… (38 chars))"]
    assert checks.main(["--root", str(tmp_path), "secrets"]) == 1
    assert key not in capsys.readouterr().out


def test_the_gitleaks_settings_parse_and_name_a_reason_for_every_allow_entry() -> None:
    import tomllib

    settings = tomllib.loads((CHECKOUT / "platform/config/gitleaks.toml").read_text("utf-8"))
    assert settings["extend"] == {"useDefault": True}
    assert all(entry["description"] for entry in settings["allowlists"])
    pinned = (CHECKOUT / "platform/config/gitleaks.toml").read_text("utf-8")
    assert "ghcr.io/gitleaks/gitleaks:v8.30.1@sha256:" in pinned
