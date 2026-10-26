"""The DataPilot api: events, runs, approvals, controls, hill-climbing requests, and demo triggers.

Every request and response model, and the endpoint table, is in datapilot.contracts.api.

At startup it probes the agent role: a write inside a read-only transaction must fail with SQLSTATE
25006, or the process refuses to start. It then reports the planted flags its environment switched
on (ops.service_planted), which a live check and the finale read.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import psycopg
from fastapi import FastAPI, HTTPException

from datapilot import db, planted
from datapilot.config import pack_config
from datapilot.contracts.api import Health
from datapilot.loop2_verification.config import VerificationConfig
from datapilot.loop2_verification.executor import Executor
from datapilot.loop3_events.api import control, demo, events, improve, runs


def probe_agent_role() -> None:
    config = VerificationConfig.from_pack(pack_config())
    Executor(
        db.url_for(db.Role.AGENT), config.schema, config.statement_timeout_ms
    ).probe_read_only()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    probe_agent_role()
    with db.connect(db.Role.APP) as conn:
        planted.report_service(conn, "api")
        conn.commit()
    yield


app = FastAPI(title="DataPilot api", lifespan=lifespan)
for module in (events, runs, control, improve, demo):
    app.include_router(module.api)


@app.get("/health", response_model=Health)
def health() -> Health:
    """Live when the process answers; ready when the ops schema is reachable as the app role."""
    try:
        with db.connect(db.Role.APP) as conn:
            conn.execute("SELECT kill_switch FROM ops.control WHERE id = 1")
    except psycopg.Error as error:
        raise HTTPException(status_code=503, detail=f"ops schema not reachable: {error}") from error
    return Health(status="ok")
