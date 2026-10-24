# Architecture

> **Terms on this page**
>
> - **Agent loop**: The model calls tools, reads the results, and repeats until it answers.
> - **Verification loop**: Graders check each query and answer, and send failures back to the agent.
> - **Event loop**: Events become jobs that workers run, with approvals, budgets, and a kill switch.
> - **Hill-climbing loop**: Experiments find failures, an analyzer team proposes rules, and a gate decides.
> - **Knowledge version**: A numbered set of business rules given to the agent in its prompt.
> - **Live session**: Everything that runs between one `make preflight` and the next.

DataPilot is one analytics agent for Harbor & Pine Outfitters, wrapped in four loops. Each loop
lives in its own package under `platform/src/datapilot/`, and each one adds a decision the inner
loop cannot make on its own. This page is the map: the big picture, the rules that hold
everywhere, one run step by step, and where each part lives on disk.

## The big picture

![DataPilot's processes and data: a webhook sender, a person at the console, and the scheduler send work to the application programming interface; the worker runs the analyst, schema scout, and reviewer agents; the hill-climbing loop runner runs the analyzer team; all of them share the ops schema in PostgreSQL](diagrams/system-architecture.svg)

*Notice that the application programming interface (API), the worker, and the runner never call each other: they meet in the ops schema, and the agents read the warehouse through a read-only role.*

![The four loops nested: the agent loop inside the verification loop inside the event loop, with the hill-climbing loop beside them feeding a promoted knowledge version back to the analyst; six agents drawn as ellipses, and a dashed ellipse under the router, where there is deliberately no agent](diagrams/four-loops.svg)

*Notice where the agents are and where there are none: the router, the graders, the overfit guard, and the gate are code, and a person approves.*

| Loop | Package | Agents | Deterministic parts |
|---|---|---|---|
| Agent loop | `loop1_agent/` | The analyst; the schema scout behind one tool | Tools, the row cap, the answer envelope |
| Verification loop | `loop2_verification/` | The reviewer, after every grader passes | Seven graders, the executor, the caps |
| Event loop | `loop3_events/` | None: the router is a table | Router, queue, leases, approvals, autonomy, kill switch |
| Hill-climbing loop | `loop4_hill_climbing/` | The failure analyst, the rule writer, the critic | Evaluator, overfit guard, promotion gate |

## Rules that hold everywhere

- **Agents only where judgement is needed.** Routing, grading, caps, approvals, and the gate are
  code. An agent proposes; code and people decide.
- **The database is the boundary.** The agent connects as a read-only role on one schema
  (`platform/ops/sql/roles.sql`). A refused write ends the run escalated at once; it is never fed
  back as a retry.
- **Every cap is code.** The row cap, the retry cap, the call limits, and the token budgets come
  from `platform/packs/datapilot_us/pack.yaml`, never from a prompt.
- **Business rules arrive only as knowledge.** The system prompt states the role, the method, and
  the output contract. The rules come from the active knowledge version.
- **Every result is live.** Each result carries its run's start time and its LangSmith trace link.
  Benchmark runs inside experiments are the one exception: they are traced as a sample, about 1 run
  in 5, and a run left out says "Not traced" (see [Costs](costs.md#langsmith-traces)). No demo path reuses a model output, a verdict, or an experiment from an earlier run.
- **The business date is fixed.** "Today" is 31 January 2026 (`DATAPILOT_BUSINESS_DATE`); run
  start times stay real time, stored in Coordinated Universal Time (UTC).

## One run, step by step

The run statuses and who writes each change are in `platform/src/datapilot/contracts/lifecycle.py`.

![The run lifecycle: twelve states from received to posted, and 23 numbered transitions, each listed with the component that writes it, taken from the contract in lifecycle.py](diagrams/run-lifecycle.svg)

*Notice that every arrow has one named writer, the API, the worker, or the reaper, and that six states end a run, only one of them with a posted answer.*

1. **Received, then queued.** The api takes an event on `POST /events`, records it in `ops.events`
   with its deterministic key, and writes the job row. A duplicate key adds no second job.
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

## Packages

| Path | What it holds |
|---|---|
| `platform/src/datapilot/contracts/` | The interfaces every loop builds against: the answer envelope, the lifecycle |
| `platform/src/datapilot/loop1_agent/` | The analyst, its tools, the schema scout, the run guard, the prompts |
| `platform/src/datapilot/loop2_verification/` | The graders, the read-only executor, the reviewer, the verification loop |
| `platform/src/datapilot/loop3_events/` | The api, router, worker, reaper, approvals, autonomy, kill switch, scheduler |
| `platform/src/datapilot/loop4_hill_climbing/` | The evaluator, the experiments, the analyzer team, the overfit guard, the gate |
| `platform/src/datapilot/observability/` | LangSmith tracing and the spend ledger |
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
questions, exports, and the digest. The scheduler requests the daily digest at 8 a.m. Eastern time.
The reaper requeues a job whose lease expired. The kill switch stops every worker and forces the
report-only level.

### Hill-climbing loop

The evaluator runs each benchmark item's gold SQL and the agent's SQL on two differently seeded
databases and compares results, never query text. The analyzer team reads only failed dev items.
The overfit guard rejects a rule that copies a benchmark question or a gold query. The gate promotes
a candidate only with more holdout passes, zero confirmed regressions, and human approval.

## Events and logs

| Where | What it records |
|---|---|
| `ops.events`, `ops.event_duplicates` | Every event received, and every duplicate absorbed |
| `ops.jobs`, `ops.runs`, `ops.run_events` | The queue, each run's status, and each tool call, grader result, and verdict |
| `ops.approvals`, `ops.posts` | Held actions and their decisions; what was posted to the channel |
| `ops.knowledge_versions`, `ops.experiments`, `ops.promotion_decisions` | The hill-climbing loop's record |
| `ops.live_sessions` | Each live session that `make preflight` started |
| LangSmith project `datapilot-live` | A trace of every live run |
| LangSmith project `datapilot-experiments` | Sampled traces of benchmark runs (1 in 5), by version, split, and item |

The schema is in `platform/ops/sql/ops/`. `make logs` follows the services' own logs.

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
| The Compose volume `pgdata` | Postgres: the warehouses and the ops schema; `make down` keeps it |
| `platform/packs/datapilot_us/knowledge/` | The knowledge versions shipped with the pack |
| `section-*/demo/expected/` | One real captured run per section, for after class |

## Check it on your machine

> Your output will differ: run times, ids, and the agent's wording change on every run.

The services and their health, from `make ps` on the course machine:

```text
NAME                    IMAGE                    COMMAND                  SERVICE     CREATED          STATUS                    PORTS
datapilot-api-1         datapilot:local          "uvicorn datapilot.l…"   api         32 minutes ago   Up 31 minutes (healthy)   0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp
datapilot-console-1     datapilot:local          "streamlit run app.p…"   console     32 minutes ago   Up 31 minutes             0.0.0.0:8501->8501/tcp, [::]:8501->8501/tcp
datapilot-postgres-1    postgres:18.6-bookworm   "docker-entrypoint.s…"   postgres    40 minutes ago   Up 40 minutes (healthy)   0.0.0.0:5432->5432/tcp, [::]:5432->5432/tcp
datapilot-scheduler-1   datapilot:local          "datapilot scheduler"    scheduler   32 minutes ago   Up 31 minutes
datapilot-worker-1      datapilot:local          "datapilot worker"       worker      32 minutes ago   Up 31 minutes
```

This capture was taken before the hill-climbing runner became a service, and before every port was
bound to this machine only. Your `make ps` also lists `datapilot-hill-climbing-runner-1`, running
`datapilot hill-climbing-runner`, with status `Up`, and its ports read `127.0.0.1:8000->8000/tcp`,
`127.0.0.1:8501->8501/tcp`, and `127.0.0.1:5432->5432/tcp`, with no `0.0.0.0` or `[::]` entries.

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
