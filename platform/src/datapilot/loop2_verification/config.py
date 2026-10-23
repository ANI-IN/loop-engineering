"""The verification loop's settings, read from pack.yaml (limits, cost guard, personal data)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from datapilot.config import active_pack, pack_config


@dataclass(frozen=True)
class VerificationConfig:
    schema: str  # the only schema the agent may read
    row_cap: int
    max_retries: int
    statement_timeout_ms: int
    max_plan_cost: float
    max_plan_rows: float
    personal_columns: frozenset[tuple[str, str]]  # (table, column) inside `schema`
    marketing_view: str  # a table name inside `schema`
    pack: str = field(default_factory=active_pack)

    @classmethod
    def from_pack(
        cls, cfg: dict[str, Any] | None = None, *, schema: str | None = None
    ) -> VerificationConfig:
        """`schema` replaces the pack's allowed schema (the tests use a fixture schema)."""
        cfg = cfg or pack_config()
        pack_schema = cfg["databases"]["allowed_schema"]
        columns = set()
        for qualified in cfg["personal_data"]["columns"]:
            table_schema, table, column = qualified.split(".")
            if table_schema == pack_schema:
                columns.add((table, column))
        view_schema, view = cfg["personal_data"]["marketing_view"].split(".")
        if view_schema != pack_schema:
            raise ValueError("personal_data.marketing_view must be in the allowed schema")
        limits, guard = cfg["limits"], cfg["cost_guard"]
        return cls(
            schema=schema or pack_schema,
            row_cap=int(limits["row_cap"]),
            max_retries=int(limits["max_retries"]),
            statement_timeout_ms=int(limits["statement_timeout_ms"]),
            max_plan_cost=float(guard["max_plan_cost"]),
            max_plan_rows=float(guard["max_plan_rows"]),
            personal_columns=frozenset(columns),
            marketing_view=view,
            pack=cfg["name"],
        )

    @property
    def personal_tables(self) -> frozenset[str]:
        return frozenset(table for table, _ in self.personal_columns)
