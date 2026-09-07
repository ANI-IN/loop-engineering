"""Configuration, loaded once and frozen.

Fail-fast is deliberate: a workshop that starts and then dies on a missing key
forty minutes in is worse than one that refuses to start. Every failure names
the exact environment variable and the exact fix.
"""

from pathlib import Path

from pydantic import SecretStr, ValidationError, field_validator
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

    # Optional on the MODEL, required by DEFAULT at the door. See `load_settings`.
    #
    # Declaring it required here made `load_settings()` the only way to read any
    # setting, so a path that makes no model call still could not start: the
    # exhibit view advertised itself as the zero-spend way to read the app and
    # demanded a key, and `enqueue.py` required a credential it never uses. The
    # Space worked around it by injecting a fake key — the same shape of
    # workaround this repo already identified and deleted for LangSmith.
    #
    # Nothing about fail-fast is given up: `load_settings()` with no argument
    # still raises `MissingCredential` before anything else happens.
    #
    # BOTH vendors are required, for different reasons. OPENAI_API_KEY runs the
    # agent and the reference arm, so without it there is no measurement at all.
    # ANTHROPIC_API_KEY runs the judge, which triages and sorts failures — it
    # gates nothing, but a session that cannot explain its own failures is a
    # session missing the part that makes the failures useful.
    openai_api_key: SecretStr | None = None
    anthropic_api_key: SecretStr | None = None

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

    @field_validator(
        "openai_api_key", "anthropic_api_key", "langsmith_api_key", mode="before"
    )
    @classmethod
    def _blank_is_absent(cls, value):
        """An empty variable means "not configured", not "configured as empty".

        `.env.example` ships `LANGSMITH_API_KEY=` with no value and the onboarding
        says, correctly, to leave it that way. pydantic read that as `SecretStr('')`
        — which is not None — so `langsmith_ds.credential()` returned `''`, the
        `if api_key is None` guard did not fire, and the code went on to construct
        `Client(api_key='')`.

        The result: following the documented setup exactly produced an auth failure
        at the first network call, instead of the "degrades to a no-op with one
        warning naming the variable" that §15, SECURITY.md and this module's own
        docstring all promise. A supported configuration that the config layer
        could not represent.

        Applies to both keys. For ANTHROPIC_API_KEY it means a blank line is
        treated as missing, so `load_settings()` raises the message naming the
        variable and the fix rather than sending an empty key to the API.
        """
        if isinstance(value, str) and not value.strip():
            return None
        return value

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
    "openai_api_key": (
        "OPENAI_API_KEY",
        "Add OPENAI_API_KEY=<your key> to .env (see .env.example). It runs the "
        "agent and the reference arm, so nothing measurable happens without it.",
    ),
    "anthropic_api_key": (
        "ANTHROPIC_API_KEY",
        "Add ANTHROPIC_API_KEY=<your key> to .env (see .env.example). It runs the "
        "judge, which triages failures and never gates a result.",
    ),
}

# Which settings field holds each vendor's credential. The one place the mapping
# lives; `loopeng.providers` reads roles off the registry and comes here for the key.
_KEY_FIELDS = {"openai": "openai_api_key", "anthropic": "anthropic_api_key"}

# Every credential `load_settings()` insists on by default.
#
# ONE, and the second one leaving this tuple is a correction rather than a relaxation.
#
# It read `("openai_api_key", "anthropic_api_key")`, justified as "both, because both
# are required — a run that can score but not triage is half a session". That was true
# of a build where both roles were Anthropic models. Under the current model policy the
# Anthropic key buys the JUDGE, and the judge is never a blocking check anywhere in this
# repository: every scored figure — the trap, the conditions, the sweep, every chart —
# is produced without it.
#
# So the tuple contradicted README §10 and SECURITY.md, which both say the Anthropic key
# is optional, and it contradicted them in the direction that turns away a valid
# checkout: a cloner with a working `OPENAI_API_KEY` and no Anthropic account could not
# start ANYTHING, including the free offline paths. That is the same defect this module's
# own history records — a required `LANGSMITH_API_KEY` shipping green while the README
# promised it was optional — recurring one variable over.
#
# The check does not disappear, it moves. `require_key` raises the same sentence at the
# moment a judge client is constructed, so triage still fails loudly and immediately,
# and it fails for the person who asked for triage rather than for everyone.
REQUIRED_CREDENTIALS = ("openai_api_key",)


def _not_set(field: str) -> str:
    """The one place the missing-credential sentence is written.

    Shared by `load_settings` and `require_api_key` so a path that defers the
    check fails with exactly the text a path that checks up front fails with.
    """
    env_var, fix = _FIXES.get(field, (field.upper(), f"Set {field.upper()} in .env."))
    return f"{env_var} is not set. {fix}"


def load_settings(*, require_credential: bool = True) -> Settings:
    """Configuration, frozen. Raises `MissingCredential` when the key is absent.

    `require_credential=False` is for paths that provably make no model call —
    the exhibit view and the queue's enqueue side. It is keyword-only and
    defaults to True so that every existing caller, and every caller written
    without reading this docstring, keeps the fail-fast behaviour: a workshop
    that starts and then dies on a missing key forty minutes in is worse than
    one that refuses to start.

    Opting out buys the right to *read configuration*, not the right to spend.
    `settings.anthropic_api_key` is then `None`, and every site that builds a
    client goes through `require_api_key`, which raises the same error with the
    same text. The check moves; it does not disappear.
    """
    try:
        settings = Settings()
    except ValidationError as exc:
        # "not set" and "set to something unparseable" are different problems and
        # used to produce the same sentence. Copying `.env.example` to `.env` with
        # an optional line left blank reported `WAREHOUSE_SEED is not set` for a
        # variable that was very much set — to an empty string — which sends the
        # reader looking for a missing line that is right in front of them.
        lines = []
        for error in exc.errors():
            field = str(error["loc"][0]) if error["loc"] else "<unknown>"
            given = error.get("input")
            if error.get("type") == "missing" or given in (None, ""):
                lines.append(_not_set(field))
            else:
                lines.append(
                    f"{field.upper()} is set to {given!r}, which is not valid: "
                    f"{error.get('msg', 'invalid value')}."
                )
        raise MissingCredential("\n".join(lines)) from exc

    if require_credential:
        # Every missing credential is reported, not just the first. An operator
        # thirty minutes from a session should learn about both keys in one run
        # rather than fixing one, re-running, and discovering the other.
        missing = [
            field
            for field in REQUIRED_CREDENTIALS
            if getattr(settings, field) is None
        ]
        if missing:
            raise MissingCredential("\n".join(_not_set(field) for field in missing))
    return settings


def require_key(settings: Settings, provider: str) -> SecretStr:
    """One vendor's credential, or the same failure `load_settings()` would raise.

    Every place that constructs a client calls this. A caller that opted out of
    the up-front check still cannot make a request without one, and when it fails
    it fails with the message that names the variable and the fix.
    """
    try:
        field = _KEY_FIELDS[provider]
    except KeyError:
        raise ValueError(
            f"unknown provider {provider!r}; this build has credentials for "
            f"{sorted(_KEY_FIELDS)}"
        ) from None
    key = getattr(settings, field)
    if key is None:
        raise MissingCredential(_not_set(field))
    return key
