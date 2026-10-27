"""Check every published file of the tree: data files, schemas, make commands, structure, release
rules, and secrets. Zero tokens: no model, no database, no service.

    uv run python platform/scripts/check_repo_files.py                 # every check
    uv run python platform/scripts/check_repo_files.py data schemas    # the named checks only
    uv run python platform/scripts/check_repo_files.py --list          # the checks, one a line

The checks, each runnable on its own:

- data: every YAML, TOML, JavaScript Object Notation (JSON) and Excalidraw file parses (YAML
  with the safe loader, every document); a key written twice in one YAML or JSON mapping fails
  too, since the loaders keep only the last.
- schemas: each pack's pack.yaml validates against PackFile below (every key the platform reads,
  with its type); the demo and planted-item registries, each pack's benchmark and knowledge
  versions validate with the platform's own pydantic models; the console's Streamlit settings,
  the guide's guide.json and the console measurements hold their expected top-level keys.
- make-targets: every `make <target>` written in the code of a course page (fenced blocks and
  code spans) names a target of the Makefile (slides/source/build.py, make_targets), a demo or
  section name it passes exists, and `make -n <target> <VARIABLE=value>...` succeeds: a dry run
  that runs nothing.
- structure: every section and the final project hold their required files (the style check's
  SC19 rules), every section in datapilot.names has its folder and its assignment check.py, and
  every demo in platform/demos/registry.yaml has its run.sh entry, its part of the demo page,
  its walkthrough sections (one for each code range it shows) and, for a core demo, its expected
  output.
- release: the release rules on the committed tree (HEAD), as platform/scripts/build_release.py
  reads them: in a public copy, no file the release list leaves out (internal files, private
  folders, withheld solutions); in every tree, no key-like text, host path, LangSmith
  organization link (the release list's `deny_patterns`) or placeholder outside the allow list
  in a file the release ships. The deny words are private: pass each with --deny at release time
  only, never in a committed file.
- secrets: key-like text (the course scanner's patterns, platform/scripts/kit/scan/
  scan_secrets.py) in every file of the tree, published or not; with --history, in every commit
  the checkout holds too. The pinned gitleaks image runs beside it in continuous integration,
  with platform/config/gitleaks.toml.

Output: one `x <file>: <reason>` line for each problem, then one summary line for each check.
Exit code 1 when any check finds a problem, 2 for an unknown check name.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
import tomllib
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    NonNegativeFloat,
    NonNegativeInt,
    PositiveFloat,
    PositiveInt,
    ValidationError,
    field_validator,
)

from datapilot.contracts import AutonomyLevel, BenchmarkItem, KnowledgeVersion
from datapilot.contracts.live import SessionPurpose
from datapilot.contracts.registries import DemoRegistry, PlantedRegistry, Tier, cross_check
from datapilot.names import SECTIONS_BY_SLUG

SCRIPTS = Path(__file__).resolve().parent
CHECKOUT = SCRIPTS.parents[1]
RELEASE_LIST = "platform/config/release.toml"
# Folders that are never the course's files: tools' output, environments and caches. The working
# tree is read through git where it can be (tracked and untracked files, less what .gitignore
# ignores); these are skipped only when git cannot list the checkout.
SKIPPED_DIRS = {
    ".git",
    ".venv",
    ".dev",
    ".claude",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".import_linter_cache",
    "node_modules",
    "build",
    "dist",
    "test-results",
    "playwright-report",
}


def _load(name: str, path: Path) -> ModuleType:
    """A module from a file of this checkout, such as the style checker."""
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def check_style() -> ModuleType:
    return _load("check_style", SCRIPTS / "check_style.py")


def build_release() -> ModuleType:
    return _load("build_release", SCRIPTS / "build_release.py")


def scan_secrets() -> ModuleType:
    return _load("scan_secrets", SCRIPTS / "kit" / "scan" / "scan_secrets.py")


def slide_builder() -> ModuleType:
    return _load("slides_build", CHECKOUT / "slides" / "source" / "build.py")


# -- the files of the tree ------------------------------------------------------------------------


def tree_files(root: Path) -> list[str]:
    """Every file of the working tree as a path relative to `root`: what git tracks or would
    track (untracked files that .gitignore does not ignore count, so a new file is read before
    its commit). Where git cannot read the checkout (an agent worktree under WSL, whose .git file
    names a Windows path), every file outside SKIPPED_DIRS."""
    if shutil.which("git") and (root / ".git").exists():
        done = subprocess.run(
            ["git", "ls-files", "-co", "--exclude-standard", "-z"], cwd=root, capture_output=True
        )
        if done.returncode == 0:
            paths = {p for p in done.stdout.decode("utf-8").split("\0") if p}
            return sorted(p for p in paths if (root / p).is_file())
    found = []
    for folder, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIPPED_DIRS]
        for name in files:
            found.append((Path(folder) / name).relative_to(root).as_posix())
    return sorted(found)


def _read(root: Path, rel: str) -> str | None:
    try:
        return (root / rel).read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


# -- data: every data file parses -----------------------------------------------------------------

YAML_SUFFIXES = (".yaml", ".yml")
JSON_SUFFIXES = (".json", ".excalidraw")
TOML_SUFFIXES = (".toml",)
TOML_NAMES = ("uv.lock",)


class _UniqueKeyLoader(yaml.SafeLoader):
    """The safe loader, refusing a key written twice in one mapping (the plain loader keeps the
    last value without a word)."""


def _construct_mapping(loader: _UniqueKeyLoader, node: yaml.MappingNode, deep: bool = False):
    seen: set[Any] = set()
    for key_node, _ in node.value:
        if key_node.tag == "tag:yaml.org,2002:merge":
            continue  # `<<: *anchor`: a key written here overrides a merged one, as YAML intends
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in seen
        except TypeError:
            continue  # an unhashable key: construct_mapping below reports it
        if duplicate:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found the key {key!r} twice",
                key_node.start_mark,
            )
        seen.add(key)
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping,  # type: ignore[arg-type]
)


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    keys = [key for key, _ in pairs]
    twice = sorted({key for key in keys if keys.count(key) > 1})
    if twice:
        raise ValueError(f"the key {twice[0]!r} appears twice in one object")
    return dict(pairs)


def parse_yaml(text: str) -> list[Any]:
    """Every document of a YAML file, with the safe loader; a duplicate key fails."""
    return list(yaml.load_all(text, Loader=_UniqueKeyLoader))  # noqa: S506 (a safe loader)


def parse_json(text: str) -> Any:
    return json.loads(text, object_pairs_hook=_unique_pairs)


def data_kind(rel: str) -> str | None:
    name = rel.rsplit("/", 1)[-1]
    if name.endswith(YAML_SUFFIXES):
        return "YAML"
    if name.endswith(JSON_SUFFIXES):
        return "JSON"
    if name.endswith(TOML_SUFFIXES) or name in TOML_NAMES:
        return "TOML"
    return None


def parse_problem(kind: str, text: str) -> str | None:
    """Why one data file does not parse, in one line; None when it parses."""
    try:
        if kind == "YAML":
            parse_yaml(text)
        elif kind == "JSON":
            parse_json(text)
        else:
            tomllib.loads(text)
    except (yaml.YAMLError, ValueError, tomllib.TOMLDecodeError) as error:
        return " ".join(str(error).split())
    return None


def data_problems(root: Path) -> tuple[list[str], int]:
    problems, count = [], 0
    for rel in tree_files(root):
        kind = data_kind(rel)
        if kind is None:
            continue
        count += 1
        text = _read(root, rel)
        if text is None:
            problems.append(f"{rel}: not UTF-8 text, so it is not {kind}")
            continue
        why = parse_problem(kind, text)
        if why:
            problems.append(f"{rel}: not valid {kind}: {why}")
    return problems, count


# -- schemas: the pack file, the registries, the benchmark, and the other data files --------------


class _Strict(BaseModel):
    """Every key named, nothing else: a misspelt key fails as a missing one does."""

    model_config = ConfigDict(extra="forbid", strict=True)


class PackDatabases(_Strict):
    agent: str
    agent_alt: str
    owner: str
    app: str
    allowed_schema: str = Field(min_length=1)


class PackModelCall(_Strict):
    """One agent's call settings: the reasoning effort is always explicit, as the Responses
    application programming interface needs."""

    reasoning_effort: str = Field(min_length=1)
    max_output_tokens: PositiveInt


class PackModels(_Strict):
    use_responses_api: bool
    analyst: PackModelCall
    schema_scout: PackModelCall
    reviewer: PackModelCall
    analyzer_team: PackModelCall


class PackAgent(_Strict):
    enabled: bool


class PackAgents(_Strict):
    schema_scout: PackAgent
    reviewer: PackAgent


class PackPrice(_Strict):
    """US dollars per million tokens."""

    input: NonNegativeFloat
    cached_input: NonNegativeFloat
    cache_write_30m: NonNegativeFloat
    cache_write_12h: NonNegativeFloat
    output: NonNegativeFloat


class PackLimits(_Strict):
    row_cap: PositiveInt
    max_retries: NonNegativeInt
    model_call_limit: PositiveInt
    tool_call_limit: PositiveInt
    statement_timeout_ms: PositiveInt
    idle_in_transaction_timeout_ms: PositiveInt
    temp_file_limit_kb: PositiveInt


class PackBudgets(_Strict):
    tokens_per_run: PositiveInt
    tokens_per_day: PositiveInt
    class_pass_tokens: PositiveInt


class PackAssignments(_Strict):
    check_cap_usd: NonNegativeFloat


class PackBudgetLine(_Strict):
    cap_usd: NonNegativeFloat
    names: list[str] = Field(default_factory=list)
    approval_variable: str | None = None


class PackSession(_Strict):
    since_variable: str
    total_usd: NonNegativeFloat
    lines: dict[str, NonNegativeFloat]  # the pack's own line names


class PackBuildBudget(_Strict):
    enabled_variable: str
    total_usd: NonNegativeFloat
    warn_usd: NonNegativeFloat
    stop_usd: NonNegativeFloat
    lines: dict[str, PackBudgetLine]  # the pack's own line names
    session: PackSession


class PackCostGuard(_Strict):
    max_plan_cost: PositiveFloat
    max_plan_rows: PositiveInt


class PackPersonalData(_Strict):
    columns: list[str]
    marketing_view: str


class PackFamilyKeyword(_Strict):
    family: str
    pattern: str

    @field_validator("pattern")
    @classmethod
    def _compiles(cls, value: str) -> str:
        try:
            re.compile(value)
        except re.error as error:
            raise ValueError(f"not a regular expression: {error}") from error
        return value


class PackAutonomy(_Strict):
    family_keywords: list[PackFamilyKeyword]
    default_level: AutonomyLevel = Field(strict=False)  # written as its value, report_only
    metric_families: list[str] = Field(min_length=1)
    demote_after_consecutive_escalations: PositiveInt


class PackEvaluation(_Strict):
    holdout_repeats: PositiveInt
    holdout_pass_threshold: PositiveInt
    dev_regression_reruns: NonNegativeInt
    dev_regression_threshold: NonNegativeInt
    holdout_regression_reruns: NonNegativeInt
    holdout_regression_fail_threshold: NonNegativeInt
    stability_runs: PositiveInt
    stability_keep_passes_at_least: NonNegativeInt
    stability_keep_passes_at_most: NonNegativeInt
    concurrency: PositiveInt
    overfit_question_words: PositiveInt
    overfit_sql_tokens: PositiveInt


class PackTracing(_Strict):
    experiment_sample_rate: float = Field(ge=0, le=1)


class PackAnalyzer(_Strict):
    candidates: PositiveInt


class PackDigest(_Strict):
    question: str = Field(min_length=1)


class PackConsole(_Strict):
    kill_switch_disarm_seconds: PositiveFloat
    strips_per_lane: PositiveInt
    poll_seconds: PositiveFloat


class PackDataCheck(_Strict):
    table: str
    rows_are: str


class PackCanary(_Strict):
    easy: list[str]
    traps: list[str]


class PackPreflight(_Strict):
    data_check: PackDataCheck
    canary: PackCanary


class PackSafeguard(_Strict):
    verification_age_limit_days: PositiveInt


class PackFile(_Strict):
    """platform/packs/<pack>/pack.yaml: every key the platform reads, with its type. The keys are
    the class pack's (use-in-your-repo/check_pack.py, key_paths, requires each one of every pack);
    platform/tests/unit/test_check_repo_files.py keeps this model and the class pack in step."""

    name: str
    display_name: str
    databases: PackDatabases
    models: PackModels
    agents: PackAgents
    prices: dict[str, PackPrice] = Field(min_length=1)  # the pack's own model names
    limits: PackLimits
    budgets: PackBudgets
    assignments: PackAssignments
    build_budget: PackBuildBudget
    cost_guard: PackCostGuard
    personal_data: PackPersonalData
    autonomy: PackAutonomy
    evaluation: PackEvaluation
    tracing: PackTracing
    analyzer: PackAnalyzer
    digest: PackDigest
    channel: str
    console: PackConsole
    preflight: PackPreflight
    safeguard: PackSafeguard


def _validation_lines(error: ValidationError) -> list[str]:
    """One line per field error: the key path and pydantic's reason."""
    return [
        f"{'.'.join(str(part) for part in item['loc']) or 'the file'}: {item['msg']}"
        for item in error.errors()
    ]


def pack_problems(root: Path, rel: str) -> list[str]:
    try:
        data = parse_yaml((root / rel).read_text(encoding="utf-8"))[0]
    except (yaml.YAMLError, IndexError, OSError) as error:
        return [f"{rel}: does not load: {' '.join(str(error).split())}"]
    folder = rel.split("/")[-2]
    try:
        PackFile.model_validate(data)
    except ValidationError as error:
        return [f"{rel}: {line}" for line in _validation_lines(error)]
    if data["name"] != folder:
        return [f"{rel}: name is {data['name']!r}, not the folder name {folder!r}"]
    return []


def benchmark_problems(root: Path, pack: Path) -> list[str]:
    """Each benchmark file of a pack: a list of BenchmarkItem (as pack_files.load_benchmark reads
    it), the ids unique across the pack's files; each knowledge version a KnowledgeVersion."""
    problems, ids = [], []
    for path in sorted((pack / "benchmark").glob("*.yaml")):
        rel = path.relative_to(root).as_posix()
        try:
            items = parse_yaml(path.read_text(encoding="utf-8"))[0] or []
        except (yaml.YAMLError, IndexError) as error:
            problems.append(f"{rel}: does not load: {' '.join(str(error).split())}")
            continue
        if not isinstance(items, list):
            problems.append(f"{rel}: holds {type(items).__name__}, not a list of items")
            continue
        for number, raw in enumerate(items, start=1):
            try:
                ids.append(BenchmarkItem.model_validate(raw).id)
            except ValidationError as error:
                name = raw.get("id", f"item {number}") if isinstance(raw, dict) else number
                problems += [f"{rel}: {name}: {line}" for line in _validation_lines(error)]
    problems += [
        f"{pack.relative_to(root).as_posix()}/benchmark: the id {item!r} appears twice"
        for item in sorted({i for i in ids if ids.count(i) > 1})
    ]
    for path in sorted((pack / "knowledge").glob("*.yaml")):
        rel = path.relative_to(root).as_posix()
        try:
            KnowledgeVersion.model_validate(parse_yaml(path.read_text(encoding="utf-8"))[0])
        except (yaml.YAMLError, IndexError) as error:
            problems.append(f"{rel}: does not load: {' '.join(str(error).split())}")
        except ValidationError as error:
            problems += [f"{rel}: {line}" for line in _validation_lines(error)]
    return problems


def registry_problems(root: Path) -> list[str]:
    """The two registries with their pydantic models (registries.demos and registries.planted read
    them so), then their cross-check."""
    loaded: dict[str, BaseModel] = {}
    problems = []
    for rel, model, key in (
        ("platform/demos/registry.yaml", DemoRegistry, "demos"),
        ("platform/planted/registry.yaml", PlantedRegistry, "items"),
    ):
        try:
            data = parse_yaml((root / rel).read_text(encoding="utf-8"))[0]
            loaded[key] = model.model_validate({key: data})
        except (yaml.YAMLError, IndexError, OSError) as error:
            problems.append(f"{rel}: does not load: {' '.join(str(error).split())}")
        except ValidationError as error:
            problems += [f"{rel}: {line}" for line in _validation_lines(error)]
    if len(loaded) == 2:
        demos, planted = loaded["demos"], loaded["items"]
        assert isinstance(demos, DemoRegistry) and isinstance(planted, PlantedRegistry)
        problems += [f"platform/demos/registry.yaml: {p}" for p in cross_check(demos, planted)]
    return problems


# The top-level keys each of these files must hold, from the code that reads it.
STREAMLIT_SETTINGS = "platform/console/.streamlit/config.toml"
STREAMLIT_KEYS = ("server", "client", "browser", "theme")  # the console's theme lives in [theme]
GUIDE = "guide/guide.json"
GUIDE_KEYS = ("title", "output", "parts")  # guide/source/build_pdf.py, load_config
MEASUREMENTS = "platform/console/screenshots/measurements.json"
# platform/tests/integration/test_console_screens.py writes one entry per measured screen.
MEASUREMENT_KEYS = (
    "1280x720",
    "1280x600",
    "1280x720, kill switch engaged",
    "15 seconds of updates",
)


def _guide_fields() -> set[str]:
    builder = _load("build_pdf", CHECKOUT / "guide" / "source" / "build_pdf.py")
    return set(builder.Config.__dataclass_fields__) | {"root"}


def keyed_file_problems(root: Path) -> list[str]:
    problems = []
    for rel, keys, parse in (
        (STREAMLIT_SETTINGS, STREAMLIT_KEYS, tomllib.loads),
        (GUIDE, GUIDE_KEYS, parse_json),
        (MEASUREMENTS, MEASUREMENT_KEYS, parse_json),
    ):
        path = root / rel
        if not path.is_file():
            problems.append(f"{rel}: missing")
            continue
        try:
            data = parse(path.read_text(encoding="utf-8"))
        except (ValueError, tomllib.TOMLDecodeError) as error:
            problems.append(f"{rel}: does not parse: {' '.join(str(error).split())}")
            continue
        if not isinstance(data, dict):
            problems.append(f"{rel}: holds {type(data).__name__}, not a table of keys")
            continue
        problems += [f"{rel}: no top-level key {key!r}" for key in keys if key not in data]
        if rel == GUIDE:
            unknown = sorted(set(data) - _guide_fields())
            problems += [f"{rel}: {key!r} is not a setting the guide reads" for key in unknown]
            parts = data.get("parts", [])
            if not isinstance(parts, list) or not all(
                isinstance(p, list) and len(p) == 2 and all(isinstance(s, str) for s in p)
                for p in parts
            ):
                problems.append(f"{rel}: parts must be a list of [file, name] pairs")
    return problems


def schema_problems(root: Path) -> tuple[list[str], int]:
    packs = sorted((root / "platform" / "packs").glob("*/pack.yaml"))
    problems = []
    if not packs:
        problems.append("platform/packs: no pack.yaml in any pack folder")
    for path in packs:
        problems += pack_problems(root, path.relative_to(root).as_posix())
        problems += benchmark_problems(root, path.parent)
    problems += registry_problems(root)
    problems += keyed_file_problems(root)
    return problems, len(packs) * 3 + 2 + 3


# -- make-targets: every make command a page names resolves ---------------------------------------

_FENCE = re.compile(r"^\s{0,3}(```+|~~~+)")
_CODE_SPAN = re.compile(r"(`+)(.+?)\1")
# `make` where a shell command starts: the start of the code, or after a separator.
_MAKE = re.compile(r"(?:^|(?<=[\s;&|(]))make\s+(?P<rest>[^\n`]*)")
_VARIABLE = re.compile(r"^[A-Z][A-Z0-9_]*=")
_PLACEHOLDER = re.compile(r"<[^<>\n]*>")
_TARGET = re.compile(r"^[a-z][a-z0-9_-]*$")
# The command-line variables whose value names something the course defines.
_DEMO_TARGETS = {"demo"}
_SECTION_TARGETS = {
    "reset",
    "check-assignment",
    "apply-solution",
    "open-code",
    "verify-assignments",
}


@dataclass(frozen=True)
class MakeCommand:
    page: str
    line: int
    target: str
    variables: tuple[str, ...] = field(default=())

    @property
    def text(self) -> str:
        return " ".join(("make", self.target, *self.variables))


def fenced_lines(text: str) -> set[int]:
    """The line numbers of fenced code, the fence lines themselves included."""
    inside, fence = set(), None
    for number, line in enumerate(text.split("\n"), start=1):
        opened = _FENCE.match(line)
        if fence:
            inside.add(number)
            if opened and opened.group(1)[0] == fence[0] and len(opened.group(1)) >= len(fence):
                fence = None
        elif opened:
            inside.add(number)
            fence = opened.group(1)
    return inside


def code_lines(text: str) -> list[tuple[int, str]]:
    """(line number, code) for every line of fenced code and every code span of a Markdown page."""
    fenced, found = fenced_lines(text), []
    for number, line in enumerate(text.split("\n"), start=1):
        if number in fenced:
            if not _FENCE.match(line):
                found.append((number, line))
            continue
        found += [(number, span.group(2)) for span in _CODE_SPAN.finditer(line)]
    return found


def make_commands(page: str, text: str) -> list[MakeCommand]:
    """Every `make <target> [VARIABLE=value...]` in the code of one page. A target written as a
    placeholder (`make <target>`) or an option (`make -n`) is not a command."""
    found = []
    for number, code in code_lines(text):
        for match in _MAKE.finditer(code):
            # A placeholder stays one word: NAME=<section slug>.
            rest = _PLACEHOLDER.sub(
                lambda m: m.group(0).replace(" ", "\0"), match.group("rest").split(" #", 1)[0]
            )
            try:
                words = shlex.split(rest)
            except ValueError:
                words = rest.split()
            words = [word.replace("\0", " ") for word in words]
            if not words or not _TARGET.match(words[0]):
                continue
            variables = []
            for word in words[1:]:
                if not _VARIABLE.match(word):
                    break
                variables.append(word)
            found.append(MakeCommand(page, number, words[0], tuple(variables)))
    return found


def _named_values(value: str) -> list[str]:
    """The concrete values a variable names: none for a placeholder (<slug>, {section}, $NAME),
    each alternative of class|rehearsal, each word of "event-loop agent-loop"."""
    if not value or any(mark in value for mark in "<>{}$*"):
        return []
    return value.replace("|", " ").split()


def value_problems(command: MakeCommand, demo_ids: set[str]) -> list[str]:
    """A demo, section or session purpose named on the command line that the course does not have.
    A pack name is the learner's own (make check-pack PACK=my_pack), so it is not read."""
    problems = []
    for variable in command.variables:
        key, value = variable.split("=", 1)
        for named in _named_values(value):
            if key == "NAME" and command.target in _DEMO_TARGETS and named not in demo_ids:
                problems.append(f"no demo {named!r} in platform/demos/registry.yaml")
            elif key == "NAME" and command.target in _SECTION_TARGETS:
                if named not in SECTIONS_BY_SLUG:
                    problems.append(f"no section {named!r} (datapilot.names)")
            elif key == "PURPOSE" and named not in {p.value for p in SessionPurpose}:
                problems.append(f"no session purpose {named!r}")
    return problems


def dry_run(root: Path, command: MakeCommand) -> str | None:
    """`make -n` of one command in `root`: None when it succeeds, else make's last line. Every
    variable a target reads counts only from the command line (the Makefile's COMMAND_LINE_ONLY),
    so the dry run sees exactly what the page passes."""
    done = subprocess.run(
        ["make", "--no-print-directory", "-n", "-C", str(root), command.target, *command.variables],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if done.returncode == 0:
        return None
    lines = (done.stderr.strip() or done.stdout.strip() or f"exit {done.returncode}").splitlines()
    return lines[-1]


def make_target_problems(root: Path) -> tuple[list[str], int]:
    style = check_style()
    targets = set(slide_builder().make_targets(root / "Makefile"))
    if not targets:
        return ["Makefile: no targets found"], 0
    # Without make, every other part still runs and the check still fails: never a silent pass.
    can_run = shutil.which("make") is not None
    demo_ids = _demo_ids(root)
    commands: list[MakeCommand] = []
    for page in style.default_files(root):
        rel = page.relative_to(root).as_posix()
        commands += make_commands(rel, page.read_text(encoding="utf-8"))
    problems, checked = [], {}
    for command in commands:
        where = f"{command.page}:{command.line}: `{command.text}`"
        if command.target not in targets:
            problems.append(f"{where}: no target {command.target!r} in the Makefile")
            continue
        problems += [f"{where}: {why}" for why in value_problems(command, demo_ids)]
        key = (command.target, command.variables)
        if not can_run:
            continue
        if key not in checked:
            checked[key] = dry_run(root, command)
        if checked[key] is not None:
            problems.append(f"{where}: make -n fails: {checked[key]}")
    if not can_run:
        problems.append("the dry run needs GNU make on the PATH (inside WSL on Windows)")
    return problems, len(commands)


def _demo_ids(root: Path) -> set[str]:
    try:
        data = parse_yaml((root / "platform/demos/registry.yaml").read_text(encoding="utf-8"))[0]
        return {d.id for d in DemoRegistry.model_validate({"demos": data}).demos}
    except (OSError, yaml.YAMLError, IndexError, ValidationError):
        return set()  # the schemas check reports the registry itself


# -- structure: sections, assignments, the final project, and every demo --------------------------

ASSIGNMENT_ITEMS = ("README.md", "SPEC.md", "starter/", "check.py")
_RUN_LIST = re.compile(r"^(CORE_DEMOS|OPTIONAL_DEMOS)=\(([^)]*)\)", re.M)
_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_LINK = re.compile(r"\]\(([^)\s#]+)")


def headings(text: str) -> list[tuple[int, int, str]]:
    """(line, level, text) for every heading outside fenced code."""
    fenced, found = fenced_lines(text), []
    for number, line in enumerate(text.split("\n"), start=1):
        match = _HEADING.match(line)
        if match and number not in fenced:
            found.append((number, len(match.group(1)), match.group(2)))
    return found


def section_text(text: str, level: int, title: str) -> str | None:
    """The body under the first heading of `level` named `title`, up to the next heading of that
    level or a higher one; None when the page has no such heading."""
    lines = text.split("\n")
    found = headings(text)
    for index, (number, found_level, found_title) in enumerate(found):
        if found_level == level and found_title == title:
            end = next((n for n, lv, _ in found[index + 1 :] if lv <= level), len(lines) + 1)
            return "\n".join(lines[number : end - 1])
    return None


def run_lists(text: str) -> dict[str, list[str]]:
    """The CORE_DEMOS and OPTIONAL_DEMOS arrays of a section's run.sh."""
    return {name: words.split() for name, words in _RUN_LIST.findall(text)}


def demo_problems(root: Path) -> list[str]:
    try:
        data = parse_yaml((root / "platform/demos/registry.yaml").read_text(encoding="utf-8"))[0]
        registry = DemoRegistry.model_validate({"demos": data})
    except (OSError, yaml.YAMLError, IndexError, ValidationError):
        return []  # the schemas check reports the registry itself
    problems = []
    for demo in registry.demos:
        folder = SECTIONS_BY_SLUG[demo.section].folder + "/demo"
        page = _read(root, f"{folder}/README.md") or ""
        if (3, demo.title) not in {(level, title) for _, level, title in headings(page)}:
            problems.append(
                f"{folder}/README.md: no part '### {demo.title}' for the demo {demo.id}"
            )
        listed = run_lists(_read(root, f"{folder}/run.sh") or "")
        array = "CORE_DEMOS" if demo.tier is Tier.CORE else "OPTIONAL_DEMOS"
        if demo.id not in listed.get(array, []):
            problems.append(f"{folder}/run.sh: {demo.id} is not in {array}")
        walkthrough = _read(root, f"{folder}/walkthrough.md") or ""
        shown = {t for _, lv, t in headings(walkthrough) if lv == 3}
        for code in demo.code:
            if f"{code.path}, lines {code.lines}" not in shown:
                problems.append(
                    f"{folder}/walkthrough.md: no section '### {code.path}, lines {code.lines}' "
                    f"for the demo {demo.id}"
                )
        if demo.tier is Tier.CORE:
            problems += expected_problems(root, f"{folder}/expected", demo.id, demo.title)
    return problems


def expected_problems(root: Path, folder: str, demo_id: str, title: str) -> list[str]:
    """A core demo's expected output: a '## <title>' part in expected/README.md that links at
    least one file of expected/, each linked file present."""
    page = _read(root, f"{folder}/README.md")
    if page is None:
        return [f"{folder}/README.md: missing (the expected output of {demo_id})"]
    body = section_text(page, 2, title)
    if body is None:
        return [f"{folder}/README.md: no part '## {title}' for the demo {demo_id}"]
    linked = [t for t in _LINK.findall(body) if "://" not in t]
    if not linked:
        return [f"{folder}/README.md: '## {title}' links no expected output of {demo_id}"]
    return [
        f"{folder}/README.md: '## {title}' links {target}, which is missing"
        for target in linked
        if not (root / folder / target).is_file()
    ]


def structure_problems(root: Path) -> tuple[list[str], int]:
    style = check_style()
    found = style.section_problems(root) + style.final_project_problems(root)
    problems = [f"{p.path}: {p.message}" for p in found]
    for section in SECTIONS_BY_SLUG.values():
        if not (root / section.folder).is_dir():
            problems.append(f"{section.folder}: missing (the folder of {section.title})")
            continue
        for item in ASSIGNMENT_ITEMS:
            path = root / section.folder / "assignment" / item
            if not (path.is_dir() if item.endswith("/") else path.is_file()):
                problems.append(f"{section.folder}/assignment/{item}: missing")
    problems += demo_problems(root)
    return problems, len(SECTIONS_BY_SLUG) + 1


# -- release: the release rules on the committed tree ---------------------------------------------


def is_build(root: Path) -> bool:
    """The course's private build holds one of the release list's build_only files; a public copy
    never does (the repository guards and the style checker decide the same way)."""
    listed = tomllib.loads((root / RELEASE_LIST).read_text(encoding="utf-8"))
    return any((root / p).is_file() for p in listed.get("build_only", []))


def solutions_published(root: Path) -> bool:
    """A public copy publishes the solutions once the owner's release with --with-solutions has
    run: its .gitignore no longer withholds them."""
    listed = tomllib.loads((root / RELEASE_LIST).read_text(encoding="utf-8"))
    ignore = root / ".gitignore"
    text = ignore.read_text(encoding="utf-8") if ignore.is_file() else ""
    return listed.get("solutions", "") not in text.split()


def release_problems(root: Path, deny: list[str], ref: str = "HEAD") -> tuple[list[str], int]:
    """The release build's own rules (build_release.config, public_texts, make_release.select and
    content_problems, placeholder_problems), read from the commit `ref` as the release reads it."""
    release = build_release()
    kit = release.make_release
    build = is_build(root)
    with_solutions = not build and solutions_published(root)
    settings = release.config(root, ref, deny, "", with_solutions=with_solutions)
    problems = []
    if not build:
        _, left_out = kit.select(kit.tracked(root, ref), settings)
        problems += [
            f"{path}: the release list leaves this file out ({why}), so a public copy never "
            "holds it"
            for path, why in sorted(left_out.items())
        ]
    texts = release.public_texts(root, settings, ref)
    if not build:
        included, _ = kit.select(kit.tracked(root, ref), settings)
        problems += [
            f"{path}: a test the release drops (it names a file the release leaves out)"
            for path in sorted(set(included) - set(texts))
            if kit._is_test(path)
        ]
    problems += kit.content_problems(texts, settings)
    problems += release.placeholder_problems(texts, _listed(root).get("placeholder_allow", []))
    return problems, len(texts)


def _listed(root: Path) -> dict[str, Any]:
    return tomllib.loads((root / RELEASE_LIST).read_text(encoding="utf-8"))


# -- secrets: key-like text in every file, and in history -----------------------------------------


def secret_problems(root: Path, history: bool) -> tuple[list[str], int]:
    """The course scanner's key patterns on every file of the tree; with `history`, on every commit
    too. A key is never printed: the kind and a masked prefix only."""
    scanner = scan_secrets()
    problems, files = [], tree_files(root)
    for rel in files:
        text = _read(root, rel)
        if text is None:
            continue
        problems += [
            f"{rel}: key-like text ({hit.kind}: {hit.masked})" for hit in scanner.find_keys(text)
        ]
    if history:
        found = scanner.scan_repo(root)
        if found["history_keys"]:
            problems += [f"git history: key-like text ({line})" for line in found["masked"]]
    return problems, len(files)


# -- the command line -----------------------------------------------------------------------------

CHECKS: dict[str, str] = {
    "data": "every YAML, TOML, JSON and Excalidraw file parses, no key twice",
    "schemas": "packs, registries, benchmarks, knowledge versions, and keyed settings files",
    "make-targets": "every make command in a page's code names a target and passes make -n",
    "structure": "sections, assignments, the final project, and every demo's files",
    "release": "the release rules on the committed tree (internal files, keys, placeholders)",
    "secrets": "key-like text in every file of the tree (and history with --history)",
}


def run_check(name: str, root: Path, args: argparse.Namespace) -> tuple[list[str], int]:
    runners: dict[str, Callable[[], tuple[list[str], int]]] = {
        "data": lambda: data_problems(root),
        "schemas": lambda: schema_problems(root),
        "make-targets": lambda: make_target_problems(root),
        "structure": lambda: structure_problems(root),
        "release": lambda: release_problems(root, args.deny, args.ref),
        "secrets": lambda: secret_problems(root, args.history),
    }
    return runners[name]()


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("checks", nargs="*", help="the checks to run (default: every check)")
    parser.add_argument("--root", type=Path, default=CHECKOUT, help="the tree to check")
    parser.add_argument("--list", action="store_true", help="list the checks and stop")
    parser.add_argument("--ref", default="HEAD", help="the commit the release check reads")
    parser.add_argument(
        "--deny", action="append", default=[], help="a word no published file may hold (release)"
    )
    parser.add_argument("--history", action="store_true", help="secrets: read every commit too")
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.list:
        for name, what in CHECKS.items():
            print(f"{name}: {what}")
        return 0
    unknown = [name for name in args.checks if name not in CHECKS]
    if unknown:
        print(f"x unknown check {', '.join(unknown)}; the checks: {', '.join(CHECKS)}")
        return 2
    root = args.root.resolve()
    failed = False
    summaries = []
    for name in args.checks or list(CHECKS):
        started = time.monotonic()
        problems, count = run_check(name, root, args)
        seconds = time.monotonic() - started
        for problem in problems:
            print(f"x {problem}")
        failed = failed or bool(problems)
        summaries.append(
            f"{'x' if problems else 'ok'} {name}: {len(problems)} problems "
            f"({count} read, {seconds:.1f} seconds)"
        )
    print("\n".join(summaries))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
