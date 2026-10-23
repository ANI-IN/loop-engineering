# Assignment 3: Event loop. Specification

The full requirements for Assignment 3: Event loop; the [README](README.md) gives the story and the
steps.

## Inputs

- The complete class system for Section 3: Event loop, with its extension points in
  `platform/src/datapilot/loop3_events/extension.py`, listed in
  [starter/README.md](starter/README.md).
- The seeded warehouse. The check adds its own orders for the anomalous day, Friday 30 January
  2026 (order ids from 900000001, all in the evening in Eastern time, so some fall on the next day
  in Coordinated Universal Time (UTC)), and removes them at the end.
- Read-only: the frozen contracts in `platform/src/datapilot/contracts/`, the business rules for
  net revenue and Eastern business days, and `platform/packs/datapilot_us/pack.yaml`.

## Files you must produce

| Path | What it holds |
|---|---|
| `platform/src/datapilot/loop3_events/extension.py` | `JOB_QUEUES`, `schedule`, `anomaly_event_id`, `request_anomaly_check`, `measure`, `is_anomaly`, `alert_text`, `publish`, and `run_job` |
| `platform/packs/datapilot_us/pack.yaml` | Your thresholds, such as `revenue_anomaly.threshold`, never constants in code |

Keep the names, types, and signatures the starter gives: the check and the worker call them. The
alert is a row in `ops.posts` whose body holds `alert_key`, `day`, `net_revenue_cents`,
`baseline_cents`, `text`, `revision` (1, then one more per update), and `drill_down` with an
`event_id` and a `question`.

## Requirements

Deterministic, checked against the real Postgres, the running api and workers, and the
scheduler's code, with no model call; each must pass every run:

1. The router table maps the job `revenue-anomaly` to its handler: no agent chooses it.
2. `schedule` adds a nightly cron job with id `revenue-anomaly` in Eastern time.
3. `anomaly_event_id` is the same for a day, holds the day's date, and differs per occasion.
4. `measure` returns the day's net revenue and the same weekday of each of the four weeks before,
   on Eastern time days, equal to gold.
5. The job for Thursday 29 January 2026, a normal day, posts nothing.
6. The job for Friday 30 January 2026, with the check's added orders, posts exactly one alert,
   labelled unverified at the report-only level, whose text states the day, its net revenue in
   dollars, and the baseline.
7. A second delivery of the same event is absorbed, and no second alert is posted.
8. After one more order on that day, a re-run updates the same alert: the same post, the new net
   revenue, revision 2, and new text.
9. The label follows the autonomy level (verified at the unattended level while revenue is not
   eligible, unattended once it is), the job is blocked at claim while the kill switch is engaged,
   and `publish` itself posts nothing while the switch is engaged.

Model-dependent, run once live on the real model and checked against gold:

10. The alert's drill-down question, submitted twice with its event id, runs once, and the answer
    it posts to the channel names the top-level category whose sales changed most against the
    four-week same-weekday average. The check's added orders are all in one category, so the gold
    answer is unmistakable. When the run holds for approval (the reviewer holds an answer, or a
    tool call needs one), the check approves it, as an instructor would, and its output says
    "approved by the check"; it then waits for the run to post and judges the posted answer, never
    the held one. A run that ends without posting fails this requirement.

The job exists in no class code path: the course build's boundary test keeps the router table and
the schedule hook empty on the class branch, so the unchanged starter fails this check.

## Live check

`make check-assignment NAME=event-loop` brings up the real stack, sets the report-only level and
releases the kill switch, clears the job's earlier events and alerts, adds its orders, and checks
requirements 1 to 9. It then prints "This check makes live model calls, about N cents, and stops at 1.00 dollar" with its
estimate, checks your OpenAI key, and runs requirement 10, approving any hold as an instructor
would, printing its trace link and live stamp, and at the end the actual tokens and cost. On the way out it removes its orders and puts back your
autonomy level. If the check reaches its spend cap of 1.00 dollar (`assignments.check_cap_usd` in pack.yaml), it stops cleanly: it starts no new run, every requirement it did not reach reads NOT RUN, and it exits 2. A missing or rejected key stops the check with "Live checks need your OpenAI key
from the operations team"; it never falls back to anything offline. When no alert was posted, the
live step does not run. The command exits 0 when every line reads PASS, 1 on any FAIL, and 2 when
it stopped.

Agent runs: 1. An approval resumes the same run; it starts no new one.

## Evidence to hand in

Nothing is submitted, and there is no hidden grader. Bring these to the Thursday review:

- the output of your live check, with the drill-down's trace link;
- one design choice you made, such as what your alert does about the 2 January dip, and why.

## Limits

- Every model call records its spend in the build-wide ledger under the activity "assignment";
  `make spend` shows the total.
- Each run stays within `budgets.tokens_per_run` and the day within `budgets.tokens_per_day` in
  `platform/packs/datapilot_us/pack.yaml`.
- The row cap `limits.row_cap` and the retry cap `limits.max_retries` in the same file still apply.
