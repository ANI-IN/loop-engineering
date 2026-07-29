"""Configuration, loaded once and frozen.

Fail-fast is deliberate: a workshop that starts and then dies on a missing key
forty minutes in is worse than one that refuses to start. Every failure names
the exact environment variable and the exact fix.
"""

from pathlib import Path

from pydantic import SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from loopeng.env_guard import EnvironmentUnsafe, check_environment

# Checked at import, before anything else in this module runs. The pytest caller
# in tests/ protects the build; this one protects the live session. A suite that
# was green this morning says nothing about the venv's file flags right now, and
# the failure it guards against is intermittent.
_environment_problem = check_environment()
if _environment_problem:
    raise EnvironmentUnsafe(_environment_problem)


class MissingCredential(RuntimeError):
    """Raised when a required credential is absent, naming the variable and the fix."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        frozen=True,
        extra="ignore",
    )

    anthropic_api_key: SecretStr

    # Optional, and it has to be, because §15 promises LangSmith is advisory and never
    # the system of record. Declaring it required made that promise false: a checkout
    # with a valid ANTHROPIC_API_KEY and no LangSmith key could not start at all, and
    # the exhibit had to inject a fake value to get past this line. A rule the config
    # contradicts is the defect this project is about, so the config moved.
    #
    # Absent means tracing degrades to a no-op with one warning naming the variable.
    # See loopeng.langsmith_ds.
    langsmith_api_key: SecretStr | None = None
    langsmith_project: str = "loop-eng-workshop"

    # Tracing is opt-in, and defaults off. The LangSmith SDK enables itself from
    # environment variables, so a developer machine with LANGSMITH_TRACING exported
    # would have ordinary pytest runs attempting network sends — quietly breaking
    # the zero-network property the offline suite is built on. Phase 3 turns this
    # on deliberately for the sweep.
    langsmith_tracing: bool = False

    # Changing the seed changes every gold answer. It is configuration, not a knob.
    warehouse_seed: int = 20260729
    warehouse_path: Path = Path("warehouse.duckdb")
    results_dir: Path = Path("results")


# One entry per credential that can actually be missing. LANGSMITH_API_KEY is
# deliberately absent: it is optional, so it can never raise here, and an entry for it
# would be a fix message for a failure that cannot happen.
_FIXES = {
    "anthropic_api_key": (
        "ANTHROPIC_API_KEY",
        "Add ANTHROPIC_API_KEY=<your key> to .env (see .env.example).",
    ),
}


def load_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as exc:
        lines = []
        for error in exc.errors():
            field = str(error["loc"][0]) if error["loc"] else "<unknown>"
            env_var, fix = _FIXES.get(field, (field.upper(), f"Set {field.upper()} in .env."))
            lines.append(f"{env_var} is not set. {fix}")
        raise MissingCredential("\n".join(lines)) from exc
