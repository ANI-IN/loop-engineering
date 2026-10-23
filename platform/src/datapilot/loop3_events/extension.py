"""Extension points of Assignment 3: Event loop, a scheduled job of your own.

The class system calls two hooks here: the router reads JOB_QUEUES, and the scheduler calls
schedule(). Both are empty, so class runs are unchanged. The assignment fills in the rest
(section-3-event-loop/assignment/starter/README.md); the worker calls run_job only for a job the
router table names. The course build's boundary test keeps this file in this state on the class
branch.

A job event is a digest.requested event whose payload names the job: {"job": JOB_NAME, "day":
"YYYY-MM-DD", "question": a one-line title for the console, "metric_family": "revenue"}.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal

import psycopg
from apscheduler.schedulers.base import BaseScheduler

from datapilot.contracts.api import EventSubmitted

JOB_NAME = "revenue-anomaly"

# EXTENSION POINT, TODO 3 (event-loop-3): the router's table for scheduled jobs, job name -> queue.
JOB_QUEUES: dict[str, str] = {}


@dataclass(frozen=True)
class Measurement:
    """One business day's net revenue and the four days it is compared with."""

    day: date
    net_revenue_cents: int
    baseline: dict[date, int] = field(default_factory=dict)  # comparison day -> net revenue


@dataclass(frozen=True)
class JobResult:
    outcome: Literal["alert_posted", "alert_updated", "no_alert", "blocked_killswitch"]
    text: str
    alert_key: str | None = None
    post_id: int | None = None


# EXTENSION POINT, TODO 1 (event-loop-1): the schedule and the event the job runs from.
def schedule(scheduler: BaseScheduler) -> None:
    # The class scheduler runs the morning digest only; add the nightly job here.
    return None


def anomaly_event_id(day: date, occasion: str | None = None) -> str:
    raise NotImplementedError(
        "event-loop-1: a deterministic event id for the day's check, plus the occasion if any"
    )


def request_anomaly_check(
    day: date | None = None, *, occasion: str | None = None
) -> EventSubmitted:
    raise NotImplementedError(
        "event-loop-1: submit the job event for the business day before `day` (the business date "
        "by default), as the scheduler's request_digest does"
    )


# EXTENSION POINT, TODO 2 (event-loop-2): the job: baseline, decision, alert.
def measure(day: date) -> Measurement:
    raise NotImplementedError(
        "event-loop-2: net revenue on `day` and on the same weekday of each of the four weeks "
        "before it, on Eastern time calendar days, read through the read-only agent role"
    )


def is_anomaly(measurement: Measurement) -> bool:
    raise NotImplementedError("event-loop-2: decide whether the day is far from its baseline")


def alert_text(measurement: Measurement) -> str:
    raise NotImplementedError("event-loop-2: the alert: the day, its net revenue, the baseline")


def publish(
    conn: psycopg.Connection[Any], measurement: Measurement, *, run_id: str, event_id: str
) -> JobResult:
    raise NotImplementedError(
        "event-loop-2: post the day's one alert, or update it, as the autonomy level allows; "
        "post nothing while the kill switch is engaged"
    )


def run_job(
    job: str, conn: psycopg.Connection[Any], payload: dict[str, Any], *, run_id: str, event_id: str
) -> JobResult:
    raise NotImplementedError(f"event-loop-2: run the {job} job for payload['day']")
