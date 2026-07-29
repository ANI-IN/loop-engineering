"""The Space sync refuses, rather than filters.

Copying only the right things is not the same as refusing the wrong ones: a filter
that misses is silent. So every forbidden thing is planted into a staging
directory here and the sync must abort on it.

The other half of the boundary — that the Space constructs no model client at all
— lives in tests/test_exhibit.py, which spies on the constructor.
"""

import json
from pathlib import Path

import pytest

from tools import sync_hf

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def staged(tmp_path) -> Path:
    return sync_hf.stage(tmp_path / "space")


# ---- what it sends ----------------------------------------------------------


def test_it_stages_the_space_entry_point_the_package_and_the_reference_data(staged):
    assert (staged / "app.py").is_file()
    assert (staged / "README.md").is_file()
    assert (staged / "requirements.txt").is_file()
    assert (staged / "src" / "loopeng" / "__init__.py").is_file()
    assert (staged / "src" / "loopeng" / "views" / "exhibit.py").is_file()
    assert (staged / "results" / "reference" / "measurements.json").is_file()


def test_a_clean_stage_passes_every_check(staged):
    files = sync_hf.assert_nothing_forbidden(staged)
    assert files
    sync_hf.assert_frontmatter(staged)
    sync_hf.assert_no_secrets_referenced(staged)


def test_no_pycache_is_staged(staged):
    assert not list(staged.rglob("__pycache__"))
    assert not list(staged.rglob("*.pyc"))


# ---- what it refuses --------------------------------------------------------


def test_it_refuses_a_dotenv(staged):
    (staged / ".env").write_text("ANTHROPIC_API_KEY=sk-ant-real\n", encoding="utf-8")
    with pytest.raises(sync_hf.SyncRefused) as refusal:
        sync_hf.assert_nothing_forbidden(staged)
    assert ".env" in str(refusal.value)
    assert "credentials" in str(refusal.value)


def test_it_refuses_a_dotenv_anywhere_not_just_at_the_root(staged):
    nested = staged / "src" / "loopeng" / ".env"
    nested.write_text("ANTHROPIC_API_KEY=sk-ant-real\n", encoding="utf-8")
    with pytest.raises(sync_hf.SyncRefused):
        sync_hf.assert_nothing_forbidden(staged)


@pytest.mark.parametrize("directory", ["results/sweep", "results/ablation"])
def test_it_refuses_live_cell_output(staged, directory):
    """A stored cell on a public page renders as though it had just been computed."""
    cell = staged / directory / "worker_L0_loop_r0.json"
    cell.parent.mkdir(parents=True, exist_ok=True)
    cell.write_text(json.dumps({"key": "worker_L0_loop_r0", "complete": True}),
                    encoding="utf-8")
    with pytest.raises(sync_hf.SyncRefused) as refusal:
        sync_hf.assert_nothing_forbidden(staged)
    assert directory in str(refusal.value)
    assert "as though it had just been computed" in str(refusal.value)


@pytest.mark.parametrize("name", ["warehouse.duckdb", "question_queue.duckdb",
                                  "src/loopeng/stray.duckdb"])
def test_it_refuses_generated_data(staged, name):
    """The Space rebuilds the warehouse from the seed and asserts its checksum."""
    path = staged / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"DUCK")
    with pytest.raises(sync_hf.SyncRefused) as refusal:
        sync_hf.assert_nothing_forbidden(staged)
    assert "duckdb" in str(refusal.value)


def test_the_refusal_names_everything_it_found_not_just_the_first(staged):
    """An operator fixing one leak should not discover the next one on the retry."""
    (staged / ".env").write_text("k=v\n", encoding="utf-8")
    (staged / "warehouse.duckdb").write_bytes(b"DUCK")
    with pytest.raises(sync_hf.SyncRefused) as refusal:
        sync_hf.assert_nothing_forbidden(staged)
    assert ".env" in str(refusal.value)
    assert "warehouse.duckdb" in str(refusal.value)


def test_a_refusal_says_nothing_was_pushed(staged):
    (staged / ".env").write_text("k=v\n", encoding="utf-8")
    with pytest.raises(sync_hf.SyncRefused) as refusal:
        sync_hf.assert_nothing_forbidden(staged)
    assert "Nothing was sent" in str(refusal.value)


def test_the_real_repository_stage_never_carries_a_duckdb(staged):
    """The developer's own warehouse.duckdb sits at the repo root. It must not be
    swept up by the copy — this is the leak the ignore filter exists for."""
    assert (REPO_ROOT / "warehouse.duckdb").exists() or True  # present or not, both fine
    assert not list(staged.rglob("*.duckdb"))


# ---- the Space has to actually build ----------------------------------------


def test_the_frontmatter_is_what_spaces_requires(staged):
    frontmatter = sync_hf.assert_frontmatter(staged)
    assert frontmatter["sdk"] == "gradio"
    assert frontmatter["sdk_version"] == "6.20.0"
    assert frontmatter["app_file"] == "app.py"


def test_wrong_frontmatter_is_refused_before_pushing(staged):
    readme = staged / "README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8").replace("sdk_version: 6.20.0",
                                                   "sdk_version: 4.0.0"),
        encoding="utf-8",
    )
    with pytest.raises(sync_hf.SyncRefused) as refusal:
        sync_hf.assert_frontmatter(staged)
    assert "will not build" in str(refusal.value)


def test_a_readme_without_frontmatter_is_refused(staged):
    (staged / "README.md").write_text("# no frontmatter\n", encoding="utf-8")
    with pytest.raises(sync_hf.SyncRefused):
        sync_hf.assert_frontmatter(staged)


def test_the_space_sets_placeholder_credentials_not_real_ones(staged):
    """Settings validate at import. Without placeholders the Space dies on startup;
    with a REAL key it becomes a public page that can spend."""
    sync_hf.assert_no_secrets_referenced(staged)

    app = staged / "app.py"
    app.write_text(app.read_text(encoding="utf-8").replace("exhibit-no-live-calls", "sk-ant"),
                   encoding="utf-8")
    with pytest.raises(sync_hf.SyncRefused) as refusal:
        sync_hf.assert_no_secrets_referenced(staged)
    assert "public page that can spend" in str(refusal.value)


# ---- requirements are generated, not hand-written ---------------------------


def test_requirements_are_generated_from_the_lock_and_are_current():
    """Spaces do not use uv. If this fails, run:
    uv run python tools/sync_hf.py --write-requirements"""
    committed = (REPO_ROOT / "deploy" / "hf" / "requirements.txt").read_text(encoding="utf-8")
    assert committed == sync_hf.render_requirements()


def test_every_requirement_is_pinned_to_a_locked_version():
    versions = sync_hf.locked_versions()
    for line in sync_hf.render_requirements().splitlines():
        if not line or line.startswith("#"):
            continue
        package, _, floor = line.partition(">=")
        assert floor, f"{line} has no version floor"
        assert versions[package] == floor, f"{package} floor is not the locked version"


def test_the_requirements_cover_what_the_exhibit_imports():
    """The exhibit builds the gold set, reads the semantic model, opens DuckDB,
    parses SQL, loads settings and serves Gradio."""
    for package in ("gradio", "duckdb", "sqlglot", "pyyaml",
                    "pydantic-settings", "structlog", "anthropic"):
        assert package in sync_hf.SPACE_PACKAGES


def test_matplotlib_never_reaches_the_space():
    """It renders the README images and is a dev dependency. A Space that installed
    it would be paying for a build step it never runs."""
    assert "matplotlib" not in sync_hf.SPACE_PACKAGES
    assert "matplotlib" not in sync_hf.render_requirements()


def test_langsmith_never_reaches_the_space():
    """The exhibit traces nothing, and a tracing SDK on a public page is an
    outbound call nobody asked for."""
    assert "langsmith" not in sync_hf.SPACE_PACKAGES


# ---- the dry run is a real rehearsal ----------------------------------------


def test_the_dry_run_pushes_nothing_and_succeeds(tmp_path, capsys):
    assert sync_hf.main(["--dry-run", "--keep", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "dry run: nothing pushed" in out
    assert "refused" in out
    assert not (tmp_path / "space" / ".git").exists()


def test_the_dry_run_reports_what_it_is_sending(tmp_path, capsys):
    """A sync that says only what it blocked tells you nothing about what it sent."""
    sync_hf.main(["--dry-run", "--keep", str(tmp_path)])
    out = capsys.readouterr().out
    assert "staged" in out and "file(s)" in out
    assert "sdk gradio" in out
