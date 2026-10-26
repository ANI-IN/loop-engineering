"""The scheduler process (APScheduler, Eastern time): the 8 a.m. KPI digest.

The digest's event id is deterministic, digest:YYYY-MM-DD, so firing it twice (a restart, a second
scheduler, a manual run) is absorbed by the idempotent POST /events path. An on-demand digest
adds an occasion, so each request is fresh while a repeated delivery of it is still absorbed.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta

import structlog
from apscheduler.schedulers.blocking import BlockingScheduler

from datapilot import db
from datapilot.business_date import today as business_day
from datapilot.contracts import EventType
from datapilot.contracts.api import EventSubmitted
from datapilot.loop3_events import extension
from datapilot.loop3_events.api.events import submit_event
from datapilot.loop3_events.budget import EASTERN
from datapilot.planted import planted, report_service

log = structlog.get_logger("scheduler")


def digest_event_id(day: date, occasion: str | None = None) -> str:
    if planted("BUG_RANDOM_DIGEST_ID"):
        return f"digest:{uuid.uuid4()}"  # planted: a new id every time, so nothing is absorbed
    return f"digest:{day.isoformat()}" + (f":{occasion}" if occasion else "")


def request_digest(day: date | None = None, *, occasion: str | None = None) -> EventSubmitted:
    """The digest requested on business day `day` (the business date by default); it covers the
    day before."""
    day = day or business_day()
    with db.connect(db.Role.APP) as conn:
        submitted = submit_event(
            conn,
            event_id=digest_event_id(day, occasion),
            type=EventType.DIGEST_REQUESTED.value,
            source="scheduler",
            payload={"day": (day - timedelta(days=1)).isoformat()},
        )
        conn.commit()
    log.info("digest requested", event_id=submitted.event_id, duplicate=submitted.duplicate)
    return submitted


def build(scheduler: BlockingScheduler | None = None) -> BlockingScheduler:
    scheduler = scheduler or BlockingScheduler(timezone=EASTERN)
    scheduler.add_job(
        request_digest, "cron", hour=8, minute=0, id="daily-digest", replace_existing=True
    )
    extension.schedule(scheduler)
    return scheduler


def main() -> None:
    db.wait_until_ready(db.Role.APP)
    with db.connect(db.Role.APP) as conn:  # what a live check and the finale read
        report_service(conn, "scheduler")
        conn.commit()
    scheduler = build()
    log.info("scheduler ready", jobs=[job.id for job in scheduler.get_jobs()])
    scheduler.start()
