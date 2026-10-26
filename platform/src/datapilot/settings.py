"""Settings from the environment and .env. Every model, URL, and switch comes from here."""

from __future__ import annotations

from datetime import date
from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO = Path(__file__).resolve().parents[3]
PLATFORM = REPO / "platform"
DEFAULT_PACK = "datapilot_us"  # the Harbor & Pine pack the class uses
# The Compose roles (platform/ops/docker/postgres-init): field -> (role and password, database).
COMPOSE_ROLES = {
    "database_url_owner": ("datapilot_owner", "datapilot"),
    "database_url_app": ("datapilot_app", "datapilot"),
    "database_url_agent": ("datapilot_agent_ro", "datapilot"),
    "database_url_agent_alt": ("datapilot_agent_ro", "warehouse_alt"),
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO / ".env", extra="ignore")

    openai_api_key: SecretStr = SecretStr("")
    # Models come only from the environment (.env.example holds the class values).
    openai_model: str = ""
    openai_analyzer_model: str = ""

    langsmith_api_key: SecretStr = SecretStr("")
    langsmith_tracing: bool = True
    langsmith_endpoint: str = "https://api.smith.langchain.com"
    langsmith_project: str = "datapilot-live"
    langsmith_experiments_project: str = "datapilot-experiments"

    # The host ports Compose publishes (compose.yaml reads the same three names from .env). A host
    # address not set on its own below follows them, so moving a port in .env moves every command.
    postgres_port: int = Field(default=5432, gt=0, lt=65536)
    api_port: int = Field(default=8000, gt=0, lt=65536)
    console_port: int = Field(default=8501, gt=0, lt=65536)

    database_url_owner: str = ""
    database_url_app: str = ""
    database_url_agent: str = ""
    database_url_agent_alt: str = ""
    # The superuser make seed uses for the agent role's limits; unset, the Compose superuser on
    # the owner address's server (the seeder's own fallback).
    database_url_superuser: str = ""

    # The domain pack every process reads: a folder name under platform/packs/, never a path.
    datapilot_pack: str = Field(default=DEFAULT_PACK, pattern=r"^[A-Za-z0-9_][A-Za-z0-9_-]*$")

    datapilot_api_url: str = ""
    datapilot_allow_demo_controls: bool = False
    demo_pacing: bool = False
    demo_pacing_seconds: float = Field(default=2.0, ge=0)
    datapilot_spend_activity: str = "development"
    # The day DataPilot treats as "today" for every business question, job, and fresh order. The
    # warehouse ends on 31 January 2026; class runs later. Run start times stay real time.
    datapilot_business_date: date = date(2026, 1, 31)
    # Empty: the console shows times in each viewer's own time zone, formatted in the browser.
    datapilot_display_timezone: str = ""

    @model_validator(mode="after")
    def _host_addresses_follow_the_ports(self) -> Settings:
        """Each database address and the api address left empty is the Compose one on its port."""
        for field_name, (role, database) in COMPOSE_ROLES.items():
            if not getattr(self, field_name):
                url = f"postgresql://{role}:{role}@localhost:{self.postgres_port}/{database}"
                setattr(self, field_name, url)
        if not self.datapilot_api_url:
            self.datapilot_api_url = f"http://localhost:{self.api_port}"
        return self

    @property
    def agent_model(self) -> str:
        """The model of the analyst, the schema scout, and the reviewer."""
        return _required(self.openai_model, "OPENAI_MODEL")

    @property
    def analyzer_model(self) -> str:
        """The model of the analyzer team; OPENAI_MODEL when not set separately."""
        return self.openai_analyzer_model or self.agent_model


class MissingSetting(RuntimeError):
    pass


def _required(value: str, name: str) -> str:
    if not value:
        raise MissingSetting(f"{name} is not set: copy it from .env.example into .env")
    return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
