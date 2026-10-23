"""The selected pack's active knowledge version, read from ops.knowledge_versions at the start of
every run."""

from __future__ import annotations

import psycopg
import yaml
from psycopg.rows import dict_row

from datapilot import db
from datapilot.config import active_pack
from datapilot.contracts import KnowledgeVersion

ACTIVE_SQL = (
    "SELECT version, yaml FROM ops.knowledge_versions WHERE pack = %s AND status = 'active'"
)
NO_VERSION = "none"


def parse_version(version: str, text: str) -> KnowledgeVersion:
    data = yaml.safe_load(text) or {}
    return KnowledgeVersion(
        version=str(data.get("version", version)),
        rules=data.get("rules") or [],
        notes=str(data.get("notes") or ""),
    )


def active_knowledge(url: str | None = None) -> KnowledgeVersion:
    """The active version, or an empty one named "none" before any version is activated."""
    with psycopg.connect(url or db.url_for(db.Role.APP), row_factory=dict_row) as conn:
        row = conn.execute(ACTIVE_SQL, (active_pack(),)).fetchone()
    if row is None:
        return KnowledgeVersion(version=NO_VERSION)
    return parse_version(row["version"], row["yaml"])
