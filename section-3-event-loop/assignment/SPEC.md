# Assignment 3: Event loop. Specification

The full requirements for Assignment 3: Event loop; the [README](README.md) gives the story and the
steps.

## Inputs

- The complete class system for Section 3: Event loop, with its extension points in
  `platform/src/datapilot/loop3_events/extension.py`, listed in
  [starter/README.md](starter/README.md).
- The seeded warehouse. The check adds its own orders for the anomalous day, Friday 30 January
  2026 (order ids from 900000001, all between 20:00 and 23:58 Eastern standard time, so every one
  falls on the next day in Coordinated Universal Time (UTC), 01:00 to 04:58), and removes them at
  the end.
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

Deterministic, checked against the real Postgres, the running api service and workers, and the
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
    it posts to the channel names the top-level category whose sales rose most above the
    four-week same-weekday average. The check judges the category the answer says rose most:
    the one in its own row with the greatest `rise_cents` when the answer returns that column, else
    the one its text says rose most; the text must name that category too. A text that says
    several categories rose most names none, and the requirement fails; so does an answer whose
    text says a category other than its top row's rose most. The check's added
    orders are all in one category, so the gold answer is unmistakable. The question must be one the class system can answer as it stands:
    the check runs it under knowledge version 1, which holds only the money rule, so the question
    names the measure that knowledge does not define, sales as quantity times unit price on the
    order lines (net revenue is an order-level rule, and no rule splits an order's discount over
    its lines), with each category rolled up to its top-level parent, and asks for the rise in
    dollars of the top category alone, in one row with the rise in cents in a column not named
    for revenue (such as `rise_cents`). A change in percent passes 100 percent on the anomalous day, and a
    change in revenue is negative for most categories; the final-answer grader blocks both (it
    blocks any column named for revenue that holds a negative value), so such a run retries
    until its token budget, `budgets.tokens_per_run`, ends it escalated. On 25 October 2026 the
    solutions' earlier question, which asked which category's net revenue "changed the most",
    ended escalated at that budget in 2 of the reference's 4 checks (and 0 of the alternatives'
    4). On the question and the judging that ship, from 22:47 Coordinated Universal Time the
    same day, the starter failed, and the solutions passed 5 of their 6 checks (see "How often a
    correct solution passes", below). When the run holds for approval (the reviewer holds an answer, or a
    tool call needs one), the check approves it, as an instructor would, and its output says
    "approved by the check"; it then waits for the run to post and judges the posted answer, never
    the held one. A run that ends without posting fails this requirement. The drill-down's event id
    is yours to choose; the check clears any earlier run under it first, so the first ask always
    starts a new run, and a first ask absorbed into an earlier run fails this requirement.

**How often a correct solution passes.** Requirement 10 depends on the answer the model gives in
that check. In the course's verification on 25 October 2026 from 22:47 Coordinated Universal Time,
correct solutions passed 5 of 6 checks: the reference 2 of 2,
alternative one 1 of 2, and alternative two 2 of 2. In the one failure the agent's posted answer
said Hiking rose most and the gold category was Water Sports; the same files passed the next check
([evidence](../../docs/evidence/general.md#captures)). A later change to how requirement 10 reads
the answer's text cannot alter the five of these verdicts judged on the answer's row. So a correct solution can read FAIL on
requirement 10 when the agent answers wrongly, and the check is right to fail it: run the check
again. The FAIL line names the category the answer said rose most and the gold one. A starter, and
a solution whose job posts no alert, still fail it every time.

The job exists in no class code path: the boundary test
(`platform/tests/unit/test_assignment_boundaries.py`) keeps the router table and
the schedule hook empty in the class system, so the unchanged starter fails this check.

## Live check

`make check-assignment NAME=event-loop` brings up the real stack, sets the report-only level and
releases the kill switch, clears the job's earlier events and alerts and the runs of their
drill-down questions, adds its orders, and checks
requirements 1 to 9. It then prints "This check makes live model calls, about N cents, and stops at 1.00 dollar" with its
estimate, checks your OpenAI key, and runs requirement 10, approving any hold as an instructor
would, printing its trace link and live stamp, and at the end the actual tokens and cost. On the way out it removes its orders and puts back your
autonomy level. If the check reaches its spend cap of 1.00 dollar (`assignments.check_cap_usd` in pack.yaml), it stops cleanly: it starts no new run, every requirement it did not reach reads NOT RUN, and it exits 2. A missing or rejected key stops the check with "Live checks need your OpenAI key
from the operations team"; it never falls back to anything offline. A run the stack itself
blocked, at its daily token budget or by a kill switch the check did not engage, stops the check
(exit 2) with that reason instead of failing a line. On its own Compose project the check switches
every planted bug off, whatever `.env` says; on services already running, a drill-down run made with
a planted bug switched on (the run records it) stops the check the same way. When no alert was posted, the live step does
not run. The command exits 0 when every line reads PASS, 1 on any FAIL, and 2 when
it stopped.

Agent runs: 1. An approval resumes the same run; it starts no new one.

## Evidence to hand in

Nothing is submitted, and there is no hidden grader. Bring these to the Thursday review:

- the output of your live check, with the drill-down's trace link;
- one design choice you made, such as what your alert does about the 2 January dip, and why.

## Limits

- Every model call records its spend in your own spend ledger,
  `~/.datapilot/spend-ledger.sqlite`, under an activity of its own for this check run, such as
  `assignment-event-loop-1a2b3c4d` (`platform/src/datapilot/assignments/cost.py`); `make spend` lists it.
- Each run stays within `budgets.tokens_per_run` and the day within `budgets.tokens_per_day` in
  `platform/packs/datapilot_us/pack.yaml`.
- The row cap `limits.row_cap` and the retry cap `limits.max_retries` in the same file still apply.
