"""Run a benchmark query on one warehouse through the verification loop's executor.

The evaluator runs both the gold SQL and the agent's final SQL here, on warehouse and on
warehouse_alt. Every query goes through loop2_verification.executor.Executor, like every other
path that runs agent SQL: the read-only agent role, SET TRANSACTION READ ONLY, the statement
timeout, and a rollback. The original SQL text is executed, never a regenerated one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from datapilot import db
from datapilot.contracts import QueryResult
from datapilot.loop2_verification.config import VerificationConfig
from datapilot.loop2_verification.executor import Executor, WarehouseRunner

WAREHOUSES = ("warehouse", "warehouse_alt")
_ROLES = {"warehouse": db.Role.AGENT, "warehouse_alt": db.Role.AGENT_ALT}


class SqlRunner(Protocol):
    def run(self, sql: str, warehouse: str, *, max_rows: int) -> QueryResult: ...


def executors(config: VerificationConfig | None = None) -> dict[str, Executor]:
    config = config or VerificationConfig.from_pack()
    return {
        name: Executor(db.url_for(role), config.schema, config.statement_timeout_ms)
        for name, role in _ROLES.items()
    }


@dataclass(frozen=True)
class ReadOnlyRunner:
    """The production runner: one executor per warehouse database."""

    runner: WarehouseRunner = field(default_factory=lambda: WarehouseRunner(executors()))

    def run(self, sql: str, warehouse: str, *, max_rows: int) -> QueryResult:
        return self.runner.run(sql, warehouse, max_rows=max_rows)
