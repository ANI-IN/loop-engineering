# Architecture

> **Terms on this page**
>
> - **Agent loop**: The model calls tools, reads the results, and repeats until it answers.
> - **Verification loop**: Graders check each query and answer, and send failures back to the agent.
> - **Event loop**: Events become jobs that workers run, with approvals, budgets, and a kill switch.
> - **Hill-climbing loop**: Experiments find failures, an analyzer team proposes rules, and a gate decides.
> - **Knowledge version**: A numbered set of business rules given to the agent in its prompt.
> - **Development split**: The benchmark questions the analyzer team may learn from.
> - **Holdout split**: The benchmark questions the analyzer team never sees; the gate decides on them.
> - **Live session**: Everything that runs between one `make preflight` and the next.

DataPilot is one analytics agent for Harbor & Pine Outfitters, wrapped in four loops. Each loop
lives in its own package under `platform/src/datapilot/`, and each one adds a decision the inner
loop cannot make on its own. This page is the map: the big picture, the services, one run step by
step, the application programming interface (API) routes, the ops tables and migrations, and the
other stacks the tests and the assignment checks start.

## The big picture

![DataPilot's processes and data: a webhook sender, a person at the console, and the scheduler send work to the application programming interface; the worker runs the analyst, schema scout, and reviewer agents; the hill-climbing loop runner runs the analyzer team; all of them share the ops schema in PostgreSQL](diagrams/system-architecture.svg)

*Notice that the API, the worker, and the runner never call each other: they meet in the ops schema, and the agents read the warehouse through a read-only role.*

![The four loops nested: the agent loop, with the analyst and the schema scout, inside the verification loop, with the seven graders and the reviewer, inside the event loop, with the router, the jobs table, the kill switch, human approval, and the post; beside them the hill-climbing loop, from the benchmark through the analyzer team and the promotion gate to the active knowledge version, which goes back to the analyst](diagrams/four-loops.svg)

*Notice where the agents are and where there are none: the router, the graders, the overfit guard, and the gate are code, and a person approves.*

| Loop | Package | Agents | Deterministic parts |
|---|---|---|---|
| Agent loop | `loop1_agent/` | The analyst; the schema scout behind one tool | Tools, the row cap, the answer envelope |
| Verification loop | `loop2_verification/` | The reviewer, after every grader passes | Seven graders, the executor, the caps |
| Event loop | `loop3_events/` | None: the router is a table | Router, queue, leases, approvals, autonomy, kill switch |
| Hill-climbing loop | `loop4_hill_climbing/` | The failure analyst, the rule writer, the critic | Evaluator, candidate choice, overfit guard, promotion gate |

## Rules that hold everywhere

- **Agents only where judgement is needed.** Routing, grading, caps, approvals, and the gate are
  code. An agent proposes; code and people decide.
- **The database is the boundary.** The agent connects as a read-only role on one schema
  (`platform/ops/sql/roles.sql`). The api service and the worker check at start that a write
  fails in the agent's transaction, and refuse to start otherwise. A refused write ends the run
  escalated at once; it is never fed back as a retry.
- **Every cap is code.** The row cap, the retry cap, the call limits, and the token budgets come
  from `platform/packs/datapilot_us/pack.yaml`, never from a prompt.
- **Business rules arrive only as knowledge.** The system prompt states the role, the method, and
  the output contract. The rules come from the active knowledge version.
- **Every result is live.** Each result carries its run's start time and its LangSmith trace link.
  Benchmark runs inside experiments are traced as a sample, about 1 run in 5, and a run left out
  says "Not traced" (see [Costs](costs.md#langsmith-traces)). No demo path reuses a model output,
  a verdict, or an experiment from an earlier run.
- **The business date is fixed.** "Today" is 31 January 2026 (`DATAPILOT_BUSINESS_DATE`); run
  start times stay real time, stored in Coordinated Universal Time (UTC).

## Services

`compose.yaml` defines six long-running services and one one-shot service. Every service except
Postgres runs the one image built from `platform/ops/docker/Dockerfile`, as user id 1000, and
mounts `~/.datapilot` for the spend ledger. Every published port listens on 127.0.0.1 only. Read a
service's log with `make logs NAME=<service>`; `make ps` shows each one's state.

### postgres

PostgreSQL 18.6 on port 5432 (`POSTGRES_PORT`), with its data in the Compose volume `pgdata`.
`platform/ops/docker/postgres-init/00-bootstrap.sql` runs once, when the volume is created: it makes
the three roles (owner, app, read-only agent), the databases `datapilot` and `warehouse_alt`, and
the schemas `warehouse`, `ops`, and `lg`. `make seed` fills the two warehouses and sets the agent
role's grants and limits (`platform/ops/sql/roles.sql`).

### migrate

`datapilot migrate`, as the owner role. It applies each file in `platform/ops/sql/ops/` that
`ops.schema_migrations` does not list yet, each in its own transaction, records it, and exits. Every
other DataPilot service waits until it has finished (`depends_on` with
`service_completed_successfully`). `make migrate` runs the same command from your machine.

### api

FastAPI under uvicorn on port 8000 (`API_PORT`), as the app role. It records work and never runs
it: events become a job and a run in one transaction, approvals requeue a parked job, controls
change `ops.control`, and hill-climbing requests become rows in `ops.improvement_requests`. Its
`/health` answers only while the ops schema is reachable; Compose uses it for the `(healthy)` state.
Every route is in [the API routes](#the-api-routes).

### worker

`datapilot worker`. Before each claim it reaps expired leases and checks the kill switch and the
daily token budget. It claims one job from the `default` or `scheduled` queue with
`FOR UPDATE SKIP LOCKED` and a 30-second lease, extends the lease every 10 seconds while the run
works, and finishes only while it still holds that lease. It runs the analyst, the schema scout,
and the reviewer; a paused run lives in the LangGraph checkpointer in schema `lg`. When LangSmith
refuses a trace for its monthly limit, the worker records the time on the run
(`ops.runs.trace_refused_at`, `loop3_events/trace_refusals.py`). A restart request from the console
makes it exit, and Compose starts it again.

### scheduler

`datapilot scheduler` (APScheduler, Eastern time). At 8 a.m. it sends the daily digest event with
the key `digest:YYYY-MM-DD`, through the same idempotent insert as `POST /events`, so a second
delivery is absorbed. Assignment 3: Event loop adds its nightly job here through
`loop3_events/extension.py`.

### hill-climbing-runner

`datapilot hill-climbing-runner` (`loop4_hill_climbing/runner.py`). It takes the requests in
`ops.improvement_requests` in the order they were made: experiments, and analyzer runs that write
two candidates. Between requests it promotes an approved candidate whose gate was ready, runs the
clearance re-runs, and writes the gold check of every live run that answered a benchmark question.
It holds a Postgres advisory lock while it serves, so a second runner on the same database
(`make hill-climbing-runner`) refuses to start.

### console

Streamlit on port 8501 (`CONSOLE_PORT`), from `platform/console/app.py`, with four pages: Agent,
Verify, Events, and Improve. It reads the ops tables directly as the app role, and every action
(ask, approve, stop, run an experiment, approve a version) goes through the API.

## One run, step by step

The run statuses and who writes each change are in `platform/src/datapilot/contracts/lifecycle.py`.

![The run lifecycle: twelve states from received to posted, and 23 numbered transitions, each listed with the component that writes it, taken from the contract in lifecycle.py](diagrams/run-lifecycle.svg)

*Notice that every arrow has one named writer, the API, the worker, or the reaper, and that six states end a run, only one of them with a posted answer.*

1. **Received, then queued.** The api service takes an event on `POST /events`, records it in
   `ops.events` with its deterministic key, and writes the job row. A duplicate key adds no second
   job.
2. **Running.** A worker claims the job with `FOR UPDATE SKIP LOCKED` and a lease, in one short
   transaction. Before the claim it checks the kill switch and the daily token budget.
3. **The agent loop.** The analyst lists tables, describes them, may ask the schema scout, and runs
   queries through the checker. Each query passes the graders before it executes.
4. **Verifying.** The final Structured Query Language (SQL) runs through every grader again, then
   the final-answer grader. A failure goes back to the analyst within `limits.max_retries`.
5. **The reviewer.** When every grader passes, the reviewer reads the question, the final SQL, a
   result preview, and the knowledge. One concern is fed back; a second holds the run for human
   approval.
6. **Approval.** A query that reads personal data, or an export, pauses for human approval. The
   pause lives in the Postgres checkpointer, so it survives a worker restart.
7. **Answered, then posted.** The autonomy policy decides whether the answer posts to the channel
   or waits for a person. A run can also end rejected, failed, escalated, or blocked.

## The API routes

The routes are in `platform/src/datapilot/loop3_events/api/`, and every request and response model
is in `platform/src/datapilot/contracts/api.py` (`ENDPOINTS`). There are 19.

| Route | Who calls it | What it does |
|---|---|---|
| `GET /health` | Compose, the demo scripts, `make preflight` | Answers while the ops schema is reachable |
| `POST /events` | Webhook senders, the console, `make demo`, the live checks | One event in, at most once; a repeat returns the first run |
| `GET /runs` | Your own tools | The open session's runs, newest first (`all_sessions`, `limit`) |
| `GET /runs/{run_id}` | `make demo`, the live checks, `make live-smoke` | One run with its run events, approvals, posts, and `trace_refused_at` |
| `GET /sessions/current` | Your own tools | The open live session; 404 when none is open |
| `POST /approvals/{run_id}` | The console, the live checks | Approve or reject a held run |
| `GET /control` | The live checks | The kill switch and the autonomy level |
| `POST /control/kill-switch` | The console, `make demo`, the live checks | Arm, engage, or release |
| `POST /control/autonomy` | The console, `make autonomy`, the live checks | Set the level; 409 while the kill switch is engaged |
| `POST /control/restart-worker` | The console | Demo control; 403 unless `DATAPILOT_ALLOW_DEMO_CONTROLS=1` |
| `GET /console/settings` | Your own tools | The pack's console limits and the business date |
| `POST /experiments/run` | The console, `make demo` | Queue an experiment for the runner |
| `POST /analyzer/run` | The console, `make demo` | Queue the analyzer team for the runner |
| `GET /improvement/requests` | Your own tools | The open session's experiment and analyzer requests |
| `POST /knowledge/{version}/approve` | The console's Improve page | The human approval a draft version needs; the runner promotes it |
| `POST /demo/large-query` | The console, `make demo` | The unbounded rows demo question |
| `POST /demo/malicious-sql` | The console, `make demo` | The defense layers on malicious SQL |
| `POST /demo/cartesian-query` | The console, `make demo` | The cost guard on a cartesian join |
| `POST /demo/failing-grader` | The console, `make demo` | A question with the injected failing grader |

A webhook sends a question this way; the event id is the sender's own key. It starts one agent run,
so it calls the model:

```bash
curl -s -X POST http://localhost:8000/events \
  -H 'Content-Type: application/json' \
  -d '{"event_id": "webhook:orders-2026-01-30", "type": "question.asked", "source": "webhook",
       "payload": {"question": "How many orders were placed on 30 January 2026?"}}'
```

The response names the `run_id` and `job_id`. The same request again returns the same run with
`"duplicate": true`. The event types are `question.asked`, `export.requested`, and
`digest.requested` (`EventType` in `contracts/lifecycle.py`). A header
`DataPilot-Spend-Activity` names the ledger activity of the run's model calls.

## Packages

| Path | What it holds |
|---|---|
| `platform/src/datapilot/contracts/` | Interfaces every loop builds on: answer envelope, lifecycle, API models |
| `platform/src/datapilot/loop1_agent/` | The analyst, its tools, the schema scout, the run guard, the prompts |
| `platform/src/datapilot/loop2_verification/` | The graders, the read-only executor, the reviewer, the verification loop |
| `platform/src/datapilot/loop3_events/` | API, router, worker, reaper, approvals, autonomy, kill switch, scheduler |
| `platform/src/datapilot/loop4_hill_climbing/` | Evaluator, experiments, analyzer team, candidates, gate, runner, preflight |
| `platform/src/datapilot/assignments/` | The live checks, their own stack, and applying a solution to a scratch copy |
| `platform/src/datapilot/finale.py` | When the finale may be sent, read by the console and `make demo` |
| `platform/src/datapilot/observability/` | LangSmith tracing, refused uploads, and the spend ledger |
| `platform/console/` | The Streamlit console: the Agent, Verify, Events, and Improve pages |
| `platform/packs/datapilot_us/` | The domain pack: settings, data generator, benchmark, knowledge versions |

## The four loops

### Agent loop

The analyst is built with `create_agent` and three tools: `list_tables`, `describe_table`, and
`run_query`. The active knowledge version reaches it through a dynamic prompt. The schema scout is a
stateless subagent behind a fourth tool, `scout_schema`, and returns a schema brief; switch it off
with `agents.schema_scout.enabled` in `pack.yaml`.

### Verification loop

Seven deterministic graders, one file each in `loop2_verification/graders/`: parse, statement
policy, schema, cost, personal data, execution, and final answer. Every query runs in a read-only
transaction as the agent role. The reviewer never overrides a grader; switch it off with
`agents.reviewer.enabled`.

### Event loop

The router is a fixed table from event type to handler and queue (`loop3_events/router.py`):
questions, exports, and the digest, plus the defense checks of the malicious SQL and cost guard
demos, and any scheduled job listed in `loop3_events/extension.py`. The reaper requeues a job whose
lease expired. The kill switch stops every worker and forces the report-only level.

### Hill-climbing loop

In workflow order, each step in `loop4_hill_climbing/`:

1. **Baseline experiment.** The evaluator runs each benchmark item's gold SQL and the agent's SQL
   on two differently seeded databases and compares results, never query text. Each holdout item
   runs 3 times and passes on 2; each development question runs once.
2. **Two candidates.** The analyzer team reads only the failed development questions and writes
   `analyzer.candidates` (2) rule sets. Each runs on the development split only; the runner keeps the one
   with fewer regressions, then more passes, on the development questions, then fewer rules (`candidates.py`). The kept
   one is saved as a draft.
3. **Candidate experiment and gate.** The gate records the baseline experiment it compares with
   (`ops.experiments.gate_baseline_id`), then confirms each apparent regression with re-runs. It
   needs more holdout passes, zero confirmed regressions, human approval, and every new rule
   through the overfit guard.
4. **Approval and promotion.** `POST /knowledge/{version}/approve` marks the draft approved. The
   runner decides it against the recorded baseline, only while the active version is unchanged and
   the gate has finished, so an approval given earlier waits for the gate.
5. **Clearance re-runs.** After the promotion, a metric family is cleared for the unattended level
   when every holdout item of the family passes 2 of 3 runs; an item that fell short gets 3 more.
6. **Gold checks of live runs.** The runner compares every live run that answered a benchmark
   question with its gold result, and writes it on the run as a `gold` grader result.

## Ops tables

Every table is in schema `ops` of database `datapilot`. The console reads most of them directly.

| Table | Written by | Read by |
|---|---|---|
| `events`, `event_duplicates` | The API's idempotent insert | The worker, the API, the console |
| `jobs` | The API, the worker, the reaper, the kill switch | The worker |
| `runs` | The API, the worker, the lifecycle, the trace-refusal recorder | The API, the worker, the runner's gold checks, the console |
| `run_events` | The lifecycle: each status change, tool call, grader result, and verdict | The API, the worker, the console |
| `approvals` | Approvals and the kill switch | The worker, the API, the console |
| `posts` | The channel | The API, the console |
| `control` | The API, the autonomy policy, the kill switch, resets | The worker, the finale check, the console |
| `budgets` | The daily token budget; a live check resets its own stack's count | The worker, the console |
| `autonomy_policy` | The autonomy policy: demotions, and the families a promotion clears; resets | The worker, the console |
| `knowledge_versions` | The runner, the approval route, resets | The analyst's prompt, the runner, the console |
| `experiments` | The runner (`store.py`), resets | The runner, the console |
| `promotion_decisions` | The gate, the class-day safeguard, resets | The runner, the finale check, the console |
| `improvement_requests` | The API, the runner, resets | The runner, the API |
| `analyzer_candidates` | The runner (`candidates.py`) | The console's Improve page |
| `live_sessions` | `make preflight`, a live check on its own stack | Every process, to stamp and filter runs |
| `reset_archives`, `reset_archive_rows` | `make reset` before it deletes a row | `make archive`, `make archive-show` |
| `rehearsal_verifications` | `make safeguard-verify` | `make safeguard-status`, `make safeguard-activate` |
| `schema_migrations` | `migrate`, as the owner role only | `migrate`, `make preflight` |

Schema `lg` holds the LangGraph checkpointer's own tables, one thread per run id. The spend
ledger is not in Postgres: it is the SQLite file `~/.datapilot/spend-ledger.sqlite`.

## Migrations

The files in `platform/ops/sql/ops/`, applied in name order. The numbers 003 to 009 and 014 were
never used, so no migration is missing.

| File | What it adds |
|---|---|
| `001_ops_schema.sql` | The first 13 tables, from events to promotion decisions |
| `002_event_loop.sql` | Queues, parked jobs, approval kinds, worker restarts, improvement requests |
| `010_live_sessions.sql` | Live sessions, and a session on every run and experiment |
| `011_live_session_purpose.sql` | Each session's purpose: class, rehearsal, Thursday review, or development |
| `012_job_spend_activity.sql` | The ledger activity a caller names on a job |
| `013_pack_knowledge_versions.sql` | The domain pack on knowledge versions, experiments, and decisions |
| `015_reset_archive_and_rehearsal_verification.sql` | The reset archive and the class-day safeguard's record |
| `016_analyzer_candidates.sql` | One row per candidate of each analyzer request |
| `017_analyzer_candidates_reset.sql` | Lets the hill-climbing reset delete a session's candidates |
| `018_schema_migrations_owner_only.sql` | Only the owner role may record a migration |
| `019_experiment_without_token_columns.sql` | Drops two experiment columns nothing wrote; spend is in the ledger |
| `020_run_trace_refused.sql` | `runs.trace_refused_at`: when LangSmith refused the run's trace |
| `021_experiment_gate_baseline.sql` | `experiments.gate_baseline_id`: the experiment the gate compared with |

## Other stacks

The class stack is the Compose project `datapilot`. Two other kinds of stack run beside it, each
with its own ports, so none touches the class data.

| Stack | Compose project | Ports | What starts it |
|---|---|---|---|
| Class | `datapilot` | 5432, 8000, 8501 | `make up` |
| Tests | `datapilot-tests` (Postgres only) | 55432 | `make test-stack`, and every target that needs it |
| Assignment checks | `datapilot-assignments` | 55433, 8100, 8502 | `make check-assignment` |
| Thursday review, Assignment 4: Hill-climbing loop | `datapilot-review` | 55434, 8101, 8503 | The [review session](review-session.md) |

The tests' stack is one Postgres, migrated and seeded by `platform/scripts/prepare_tests_database.py`.
`make test-stack`, `make test-integration`, `make test-console`, and `make test-security` each run
under `flock /tmp/datapilot-tests-database.lock`, so checkouts on one machine use it one at a time.

A live check builds its stack from the tree it checks, with its own image tag, and refuses the
`datapilot` project and the class ports. `DATAPILOT_ASSIGNMENT_STACK=running` makes it use services
that are already running instead.

## Cost tracking and caps

Every model call goes through one callback that records its tokens and cost, priced from
`pack.yaml`, in the ledger at `~/.datapilot/spend-ledger.sqlite`. Every service mounts that folder,
so the console and `make spend` read the same numbers. The caps are listed on the
[reference page](reference.md#caps-and-limits); what they mean in money is on the
[costs page](costs.md).

## Files on disk

| Path | What it is |
|---|---|
| `.env` | Your keys and settings; git-ignored, never printed |
| `~/.datapilot/spend-ledger.sqlite` | The spend ledger, outside the repository |
| `~/.datapilot/assignment-work/` | Scratch copies made by `make apply-solution` (`DATAPILOT_ASSIGNMENT_WORK`) |
| The Compose volume `pgdata` | Postgres: the warehouses and the ops schema; `make down` keeps it |
| `platform/packs/datapilot_us/knowledge/` | The knowledge versions shipped with the pack |
| `section-*/demo/expected/` | One real captured run per section, for after class |

## Check it on your machine

`make ps` lists the six running services, each as a container named `datapilot-<service>-1`, with
status `Up`; `api` and `postgres` also show `(healthy)`. `migrate` has exited, so only
`docker compose ps --all` lists it. The ports read
`127.0.0.1:5432->5432/tcp`, `127.0.0.1:8000->8000/tcp`, and `127.0.0.1:8501->8501/tcp`
(`compose.yaml`).

> Your output will differ: run times, ids, and the agent's wording change on every run.

The demos the registry holds, from `make demos`, the first four lines:

```text
agent-simple-question                core     The simple question
agent-texas-last-quarter             optional Texas last quarter
agent-confident-wrong-answer         core     The confident wrong answer
agent-unbounded-rows                 core     Unbounded rows
```

The seeded warehouses, from `make check-data`:

```text
check-data: both warehouses match expected.yaml
```
