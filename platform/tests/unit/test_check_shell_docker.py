"""The shell, Dockerfile, and Compose checks: how they find the files and the commands they run.

The checks that need Docker (hadolint, the image build, Compose) run in continuous integration
itself; here their commands are pinned: a pinned hadolint image, no secret in a build, and Compose
reading .env.example, never a real .env.
"""

from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "platform" / "scripts" / "check_shell_docker.py"


def _load():
    spec = importlib.util.spec_from_file_location("check_shell_docker", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["check_shell_docker"] = module
    spec.loader.exec_module(module)
    return module


check = _load()


@pytest.mark.parametrize(
    ("line", "interpreter"),
    [
        ("#!/usr/bin/env bash", "bash"),
        ("#!/bin/sh", "sh"),
        ("#!/bin/bash -e", "bash"),
        ("#!/usr/bin/env -S bash -euo pipefail", "bash"),
        ("#!/usr/bin/env PYTHONUNBUFFERED=1 python3", "python3"),
        ("#!/usr/bin/env python3", "python3"),
        ("#!", None),
        ("# a comment", None),
        ("", None),
    ],
)
def test_the_shebang_names_its_interpreter(line, interpreter):
    assert check.shebang_interpreter(line) == interpreter


def test_shell_scripts_are_found_by_suffix_and_by_shebang(tmp_path):
    files = {
        "demo/run.sh": "echo no shebang\n",
        "hooks/commit-msg": "#!/usr/bin/env bash\necho hook\n",
        "tools/posix": "#!/bin/sh\necho posix\n",
        "tools/build.bash": "echo bash\n",
        "tools/zsh-only": "#!/usr/bin/env zsh\necho zsh\n",
        "tools/script.py": "#!/usr/bin/env python3\nprint()\n",
        "README.md": "# not a script\n",
    }
    for name, text in files.items():
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(text, encoding="utf-8")
    listed = [*files, "deleted/but-listed.sh"]  # a tracked name missing from the disk is skipped
    assert check.shell_scripts(tmp_path, listed) == [
        "demo/run.sh",
        "hooks/commit-msg",
        "tools/build.bash",
        "tools/posix",
    ]


def test_the_repository_shell_scripts_include_every_run_script_and_the_hook():
    found = check.shell_scripts(ROOT, check.tracked_files(ROOT))
    run_scripts = sorted(p.relative_to(ROOT).as_posix() for p in ROOT.glob("*/**/run.sh"))
    tracked = set(check.tracked_files(ROOT))
    assert [s for s in run_scripts if s in tracked] == [s for s in found if s.endswith("/run.sh")]
    assert {"platform/scripts/hooks/commit-msg", "platform/scripts/verify.sh"} <= set(found)
    assert not any(name.startswith(".venv/") for name in found)


def test_a_folder_that_is_not_a_checkout_is_read_outside_its_dot_folders(tmp_path):
    for name in ("run.sh", "tools/check.sh", ".venv/bin/activate.sh", "a/__pycache__/x.sh"):
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text("echo\n", encoding="utf-8")
    (tmp_path / ".env.example").write_text("A=1\n", encoding="utf-8")
    assert check.tracked_files(tmp_path) == [".env.example", "run.sh", "tools/check.sh"]


def test_dockerfiles_and_compose_files_are_found_by_name():
    files = [
        "platform/ops/docker/Dockerfile",
        "tools/Dockerfile.worker",
        "tools/api.Dockerfile",
        "docs/Dockerfile.md.j2x/notes.md",
        "compose.yaml",
        "other/docker-compose.yml",
        "compose.override.yaml",
    ]
    assert check.dockerfiles(files) == [
        "platform/ops/docker/Dockerfile",
        "tools/Dockerfile.worker",
        "tools/api.Dockerfile",
    ]
    assert check.compose_files(files) == ["compose.yaml", "other/docker-compose.yml"]


def test_profiles_are_every_profile_a_service_names():
    data = {
        "services": {
            "postgres": {"image": "postgres"},
            "console": {"profiles": ["ui", "debug"]},
            "tools": {"profiles": ["debug"]},
        }
    }
    assert check.compose_profiles(data) == ["debug", "ui"]
    assert check.compose_profiles({"services": {"api": {}}}) == []
    assert check.compose_profiles({}) == []


def test_build_contexts_come_from_compose(tmp_path):
    data = {
        "services": {
            "api": {"build": {"context": ".", "dockerfile": "platform/ops/docker/Dockerfile"}},
            "short": {"build": "tools"},
            "postgres": {"image": "postgres:18.6-bookworm"},
        }
    }
    assert check.build_contexts(tmp_path, "compose.yaml", data) == {
        "platform/ops/docker/Dockerfile": ".",
        "tools/Dockerfile": "tools",
    }


def test_the_repository_dockerfile_is_built_from_the_root_as_compose_builds_it():
    data = check.load_compose(ROOT / "compose.yaml")
    assert check.build_contexts(ROOT, "compose.yaml", data) == {
        "platform/ops/docker/Dockerfile": "."
    }
    assert check.env_file_problems(ROOT) == []


def test_a_build_context_must_leave_every_env_file_out(tmp_path):
    assert "is missing" in check.env_file_problems(tmp_path)[0]
    (tmp_path / ".dockerignore").write_text(".git\n.env\n", encoding="utf-8")
    assert len(problems := check.env_file_problems(tmp_path)) == 1
    assert ".env.*" in problems[0]
    (tmp_path / ".dockerignore").write_text(".env\n.env.*\n!.env.example\n", encoding="utf-8")
    assert check.env_file_problems(tmp_path) == []


def test_compose_warnings_are_found_in_its_output():
    output = (
        'WARN[0000] The "API_PORT" variable is not set. Defaulting to a blank string.\n'
        'time="2026-10-27" level=warning msg="version is obsolete"\n'
        "services:\n"
    )
    assert len(check.compose_warnings(output)) == 2
    assert check.compose_warnings("") == []


def test_hadolint_runs_from_one_image_pinned_by_tag_and_digest():
    command = check.hadolint_command()
    image = check.HADOLINT_IMAGE
    assert image in command
    name, _, digest = image.partition("@")
    assert name.startswith("hadolint/hadolint:v") and ":latest" not in name
    assert digest.startswith("sha256:") and len(digest) == len("sha256:") + 64
    assert command[command.index("--failure-threshold") + 1] == "style"
    assert "--network=none" in command and command[-1] == "-"


def test_a_build_carries_no_secret_and_no_build_argument():
    command = check.build_command("platform/ops/docker/Dockerfile", ".")
    assert command[:2] == ["docker", "build"]
    assert not any(part.startswith(("--secret", "--build-arg", "--ssh")) for part in command)
    assert command[-1] == "."
    tag = check.build_tag("platform/ops/docker/Dockerfile")
    assert tag == "datapilot-check:platform-ops-docker"


def test_compose_reads_the_example_variables_and_never_a_real_env_file(tmp_path):
    compose, example = tmp_path / "compose.yaml", tmp_path / ".env.example"
    command = check.compose_command(compose, example, None)
    assert command[command.index("--env-file") + 1] == str(example)
    assert command[-3:] == ["config", "--quiet", "--no-env-resolution"]
    assert "--profile" not in command
    with_profile = check.compose_command(compose, example, "ui")
    assert with_profile[with_profile.index("--profile") + 1] == "ui"
    assert not any(part.endswith(("/.env", "\\.env")) or part == ".env" for part in command)


def test_shellcheck_reads_every_script_at_the_strictest_severity():
    command = check.shellcheck_command("shellcheck", ["a.sh", "b"])
    assert "--severity=style" in command
    assert command[-2:] == ["a.sh", "b"]


def _tracked(git, files: dict[str, str]) -> Path:
    """The files written into the throwaway repository and added, so `git ls-files` lists them."""
    repo = Path(git("rev-parse", "--show-toplevel").stdout.strip())
    for name, text in files.items():
        (repo / name).parent.mkdir(parents=True, exist_ok=True)
        (repo / name).write_bytes(text.encode("utf-8"))
    git("add", "--all")
    return repo


@pytest.mark.skipif(sys.platform == "win32", reason="bash is the Linux runner's")
def test_bash_syntax_fails_on_a_script_that_does_not_parse(throwaway_repo, capsys):
    repo = _tracked(
        throwaway_repo,
        {"good/run.sh": "#!/usr/bin/env bash\necho fine\n", "bad/run.sh": "if true; then\n"},
    )
    assert check.main(["bash-n", "--root", str(repo)]) == 1
    output = capsys.readouterr().out
    assert "x syntax bad/run.sh" in output and "ok    good/run.sh" in output


@pytest.mark.skipif(
    sys.platform == "win32" or shutil.which("shellcheck") is None,
    reason="ShellCheck from the dev group, on the Linux runner",
)
def test_shellcheck_fails_on_a_finding_and_passes_a_clean_script(throwaway_repo, capsys):
    script = '#!/usr/bin/env bash\nset -euo pipefail\necho "$1"\n'
    repo = _tracked(throwaway_repo, {"run.sh": script})
    assert check.main(["shellcheck", "--root", str(repo)]) == 0
    (repo / "run.sh").write_text("#!/usr/bin/env bash\necho $1\n", encoding="utf-8")
    assert check.main(["shellcheck", "--root", str(repo)]) == 1
    assert "SC2086" in capsys.readouterr().out


def test_a_check_with_nothing_to_check_fails(throwaway_repo, capsys):
    repo = _tracked(throwaway_repo, {"README.md": "# nothing\n"})
    for name in ("shellcheck", "bash-n", "hadolint", "build", "compose"):
        assert check.main([name, "--root", str(repo)]) == 1
    assert "x no shell script found" in capsys.readouterr().out
