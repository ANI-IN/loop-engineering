# Module: Loop Engineering

New here? [Start here](docs/start-here.md).

This module builds four loops around one analytics agent, DataPilot, and measures each one live on
the same benchmark of business questions. It is for experienced engineers who already use
LangChain, LangGraph, LangSmith, the Model Context Protocol, and multi-agent patterns: none of
those is taught here. The class is a 4-hour Sunday session where every demo runs live, followed by
four assignments and a 2-hour Thursday review.

## The problem

A finance manager at Harbor & Pine Outfitters asks the analytics agent for last fiscal year's net
revenue. The agent sums an order column over the calendar year and answers in one confident
sentence. The number goes into a board deck. Nobody can say where it came from.

The team adds checks, and every check on the query passes; the answer is still wrong, because no
check knows what "net revenue" means at Harbor & Pine. A retried webhook then posts the same answer
three times, and an approval vanishes when the worker restarts. Rules written from the failures
raise the score on the team's own test questions and quietly break another question. A stronger
model fixes none of these failures: each one is a missing loop around the model.

> **Terms on this page**
>
> - **Agent loop**: The model calls tools, reads the results, and repeats until it answers.
> - **Verification loop**: Graders check each query and answer, and send failures back to the agent.
> - **Event loop**: Events become jobs that workers run, with approvals, budgets, and a kill switch.
> - **Hill-climbing loop**: Experiments find failures, an analyzer team proposes rules, and a gate decides.
> - **Development split**: The benchmark questions the analyzer team may learn from.
> - **Holdout split**: The benchmark questions the analyzer team never sees; the gate decides on them.
> - **Autonomy level**: How much DataPilot may do unattended: report-only, assisted, or unattended.
>
> All terms: [glossary](docs/glossary.md).

## Why it happens

1. **The rules live in people's heads, not in the schema.**
   [BIRD](https://arxiv.org/abs/2305.03111) calls them external knowledge and hands models the
   missing rules as evidence. [Spider 2.0](https://arxiv.org/abs/2411.07763) shows large language
   model (LLM) agents do much worse on real enterprise schemas than on benchmark schemas.
2. **A check on the query is not a check on the answer.** A Structured Query Language (SQL)
   result that matches on one database can still be wrong:
   [Semantic Evaluation for Text-to-SQL with Distilled Test Suites](https://arxiv.org/abs/2010.02840)
   measures how often single-database execution match gives false positives.
3. **A queue delivers at least once, and memory does not survive a restart.** A Postgres job queue
   can hand the same work out twice
   ([You don't need a job queue: Postgres already has SKIP LOCKED](https://www.prisma.io/blog/you-dont-need-a-job-queue-postgres-already-has-skip-locked)). A pending
   approval is an interrupted run, and its state must outlive the process
   ([Human-in-the-loop](https://docs.langchain.com/oss/python/langchain/human-in-the-loop)).
4. **Rules written from failures do not reliably transfer.**
   [MAGIC](https://arxiv.org/abs/2406.12692) turns failures into a self-correction guideline; a
   [table agents survey](https://arxiv.org/html/2507.10281) re-ran it and found small gains.

The four loops follow [The art of loop engineering](https://www.langchain.com/blog/the-art-of-loop-engineering).
Every source and finding is on the [evidence page](docs/evidence.md).

## The approach

![DataPilot's processes and data: a webhook sender, a person at the console, and the scheduler send work to the application programming interface; the worker runs the analyst, schema scout, and reviewer agents; the hill-climbing loop runner runs the analyzer team; all of them share the ops schema in PostgreSQL](docs/diagrams/system-architecture.svg)

*Notice that the application programming interface (API), the worker, and the runner never call each other: they meet in the ops schema, and the agents read the warehouse through a read-only role.*

### The services

`make up` starts six services and the one-shot migrate (`compose.yaml`); ports listen on this machine
only. Logs: `make logs NAME=<service>`. The [architecture page](docs/architecture.md#services) walks through each.

| Service | Port | What it does | What it reads and writes |
|---|---|---|---|
| `postgres` | 5432 | PostgreSQL 18.6 | Database `datapilot` (schemas `warehouse`, `ops`, `lg`) and `warehouse_alt` |
| `migrate` | none | Applies the ops migrations, then exits; every other service waits for it | Writes `ops`, records each file in `ops.schema_migrations` |
| `api` | 8000 | Takes events, approvals, controls, and hill-climbing requests (19 routes) | Writes events, jobs, runs, approvals, control, requests |
| `worker` | none | Claims jobs with a lease and runs the analyst, schema scout, and reviewer | Reads the warehouse read-only; writes runs, run events, posts |
| `scheduler` | none | Sends the daily digest event at 8 a.m. Eastern time | Writes the event the way the API does |
| `hill-climbing-runner` | none | Experiments, analyzer team, promotions, gold checks; one per database | Writes experiments, candidates, knowledge versions, decisions |
| `console` | 8501 | The Streamlit console: the Agent, Verify, Events, and Improve pages | Reads `ops` directly; acts only through the API |

### Each loop's workflow

| Loop | Starts on | Steps, in order | What decides |
|---|---|---|---|
| Section 1: Agent loop | A question | Tables, descriptions, the schema scout, queries of at most 50 rows, the answer | The analyst, inside its call, tool, and token caps |
| Section 2: Verification loop | Every query, then the answer | Graders, read-only executor, final-answer grader, reviewer; up to 3 attempts | Code; a persistent reviewer concern goes to a person |
| Section 3: Event loop | A webhook, the schedule, or the console | Idempotent insert, router, job, leased claim, run, approval, post or hold | The router table, the autonomy policy, a person, the kill switch |
| Section 4: Hill-climbing loop | A request on the Improve page | Baseline, two candidates (one kept), gate, approval, promotion, clearance | The promotion gate (code) and a person |

## The class plan

| Section | Folder | What you see in class | Time |
|---|---|---|---|
| Section 1: Agent loop | [section-1-agent-loop/](section-1-agent-loop/README.md) | The simple question, the confident wrong answer, unbounded rows | 0:47-1:22 |
| Section 2: Verification loop | [section-2-verification-loop/](section-2-verification-loop/README.md) | Malicious SQL, the retry cap, every grader passes, still wrong | 1:22-1:55 |
| Section 3: Event loop | [section-3-event-loop/](section-3-event-loop/README.md) | The webhook question, the approval across a restart, duplicates, the kill switch | 2:05-2:48 |
| Section 4: Hill-climbing loop | [section-4-hill-climbing-loop/](section-4-hill-climbing-loop/README.md) | Baseline and candidate experiments, the analyzer team, the gate, the last run | 3:03-3:38 |

Before Section 1: the opening 0:00-0:13, the problem statement 0:13-0:37, and Designing
text-to-SQL 0:37-0:47; two breaks, 1:55-2:05 and 2:53-3:03; the closing 3:38-4:00. The minute-by-minute plan is in the [instructor guide](docs/instructor-guide.md); every live demo, step by step, is in [guide/](guide/README.md).

### What you build

| Assignment | What you build | Live check | Effort |
|---|---|---|---|
| [Assignment 1: Agent loop](section-1-agent-loop/assignment/README.md) | A value-lookup tool for informal or misspelled product names | `make check-assignment NAME=agent-loop` | About 1.5 hours |
| [Assignment 2: Verification loop](section-2-verification-loop/assignment/README.md) | Two graders: clarify-or-abstain, and a personal-data leak check | `make check-assignment NAME=verification-loop` | About 2 hours |
| [Assignment 3: Event loop](section-3-event-loop/assignment/README.md) | A nightly revenue anomaly alert, at most one per day | `make check-assignment NAME=event-loop` | About 2 to 2.5 hours |
| [Assignment 4: Hill-climbing loop](section-4-hill-climbing-loop/assignment/README.md) | A repeat-customer metric family, a critic change, a holdout minimum per family | `make check-assignment NAME=hill-climbing-loop` | About 2 to 2.5 hours |

Each check runs live. The [final project](final-project/README.md) then uses a dataset of your own.

## What we measured

Calibration ran every core demo and the benchmark live on 22 and 23 October 2026, on gpt-6-luna,
with business date 31 January 2026; every demo and assignment check ran live again on 24 and 25
October. The [calibration report](docs/calibration-report.md) holds every count below, and
[what each loop is worth](docs/benefits.md) compares each loop with its protection off and on.

- **Section 1: Agent loop.** 0 of 99 trap item runs passed under version 1 of the knowledge (the starting version).
- **Section 2: Verification loop.** The reviewer raised a concern in 6 of 7 runs on the wrong
  answer to the fiscal year 2025 revenue question (7 runs of that one question).
- **Section 3: Event loop.** In 7 of 7 demo runs each: the same event sent three times gave one run
  and 2 duplicates absorbed, and a pending approval survived a worker restart.
- **Section 4: Hill-climbing loop.** Holdout items passed: 2 of 15 under version 1, against 12 to
  14 of 15 under the 7 versions promoted with two candidates. 14 of 15 candidate experiments had no
  regressions; the fifteenth had one regression on the development questions.

### Worked examples

> Your output will differ: run times, ids, and the agent's wording change on every run.

Section 1, the simple question, as the Agent page showed it on 22 October 2026 (the lines without
ids of `section-1-agent-loop/demo/expected/agent-simple-question-terminal.txt`):

```text
question: How many orders have been placed in total?
status: posted
tool calls: list_tables, describe_table, run_query
final SQL: SELECT COUNT(*) AS total_orders FROM orders;
answer: There have been 405738 orders placed in total.
```

Section 2, malicious SQL with the naive guard planted (`verify-malicious-sql-naive-guard-terminal.txt`):

```text
statement: DELETE FROM orders
  role grants: stopped it: SQLSTATE 42501: permission denied for table orders
  stopped by: role grants
orders before 405738, after 405738: unchanged True
```

### What it costs you

Measured on gpt-6-luna: about 0.001 dollars per analyst run, 0.0594 to 0.0914 dollars per 70-run
experiment, and 0.0053 dollars for `make preflight`. Each assignment check stops at its own spend
cap, 1.00 dollar (`assignments.check_cap_usd` in `pack.yaml`). Set a 3-dollar limit on your OpenAI
project, with an alert at 1.50 dollars: the [costs page](docs/costs.md) shows how running every
check five times typically comes to about 1.16 dollars.

**Known limitations.** Revenue was cleared for the unattended level in 7 of 11 live promotions of a
knowledge version (versions 8, 9, 11, 13, 15, 17, and 19). The two-candidate method has been measured
in seven promotions, so every count is a small sample. gpt-6-luna has no dated snapshot, so `make preflight` runs a drift canary first.

## Quick start

**Prerequisites.** An OpenAI key whose project can use gpt-6-luna: in a cohort, from the operations
team; on your own, from an OpenAI project you create with the budget above. A LangSmith account on
the free Developer plan, with no card. Docker Engine with the Compose plugin, git, make, and uv
0.13.1, which installs Python 3.12. Knowledge of Python, Postgres SQL, Docker Compose, and LangChain
agents. Measured on the build machine: the six class services use about 625 mebibytes (MiB) of
memory; Docker held 4.2 gigabytes (GB) of volumes and 6.6 GB of images, and uv's cache 1.2 GB.

| Your machine | Tested for the course | Setup page |
|---|---|---|
| Windows 10 (version 2004 or later) or 11 | Yes: Ubuntu on WSL2, Docker Engine inside Ubuntu | [setup/windows.md](setup/windows.md) |
| Linux with `apt` | The same commands, run in Ubuntu on WSL2 | [setup/linux.md](setup/linux.md) |
| macOS | No: the steps follow the official pages | [setup/macos.md](setup/macos.md) |

```bash
git clone https://github.com/ANI-IN/loop-engineering.git ~/datapilot
cd ~/datapilot
make setup                            # creates .env: add OPENAI_API_KEY and LANGSMITH_API_KEY
make up                               # builds the image and starts the services; 63 seconds once the image is built
make ps                               # six services Up; api and postgres (healthy)
make seed
make check-data                       # ends: check-data: both warehouses match expected.yaml
make preflight PURPOSE=development    # ends with a line that starts: Live session started at
make demo NAME=agent-simple-question
```

On Windows, run these in the Ubuntu terminal. Open the console at <http://localhost:8501> to watch the
run. `make preflight` asks five canary questions, one agent run each. [setup/](setup/README.md)
explains every step and its failures.

### LangSmith

Demo and check runs trace in full to the project `datapilot-live`; experiment runs go to
`datapilot-experiments` as a sample of about 1 in 5 (`tracing.experiment_sample_rate`), and a row
with none reads "Not traced". EU accounts set `LANGSMITH_ENDPOINT`. The free plan allows 5,000 traces
a month; past that every upload is refused, runs go on, and the trace link never fills
([costs](docs/costs.md#langsmith-traces)).

### Adapt DataPilot to your own data

One setting, `DATAPILOT_PACK` in `.env`, names the domain pack every process reads, a folder under
`platform/packs/`. Copy `platform/packs/_template/`, run `make check-pack PACK=<name>`, set the
setting, then `make up` and `make preflight PURPOSE=development`. [Use it in your
repository](use-in-your-repo/README.md) walks through it, including what stays Harbor & Pine.

### When something fails

The most common lines; every other one, with its cause, is on [troubleshooting](docs/troubleshooting.md).

| You see | Fix |
|---|---|
| `No live session is open: run make preflight PURPOSE=class\|rehearsal\|thursday-review\|development first` | `make preflight PURPOSE=development` |
| `Your OpenAI key was not accepted. Check it with the operations team.` | Paste the key into `.env` again; then check its project |
| `Bind for 127.0.0.1:5432 failed: port is already allocated` | Set `POSTGRES_PORT` in `.env`, then `make up` |
| A trace link that never fills | The LangSmith monthly limit, above |
| `The OpenAI account behind your key has no credits left, ...` | Add credits to the key's project, then run again |

## Where next

Start with [Section 1: Agent loop](section-1-agent-loop/README.md). To build text-to-SQL on your own warehouse, follow [designing text-to-SQL for your own warehouse](docs/text-to-sql-design.md).
Every outside source the slides cite is on the [sources page](docs/sources.md). Look things up in [architecture](docs/architecture.md),
[reference](docs/reference.md), and the [frequently asked questions](docs/faq.md). Never share your `.env` or a key.

### Repository layout

| Folder | What it holds |
|---|---|
| `setup/` | Setup for Windows, Linux, and macOS, and the pre-class checklist |
| `section-1-agent-loop/` to `section-4-hill-climbing-loop/` | Pages, demo, assignment, readings; `solution/` is published at the Thursday review |
| `final-project/`, `use-in-your-repo/` | The capstone, and DataPilot on your own Postgres |
| `docs/`, `guide/` | Architecture, reference, costs, troubleshooting, glossary; the Live Demo Guide |
| `platform/` | Code, console, packs, migrations, tests: [platform/README.md](platform/README.md) |

### Licence

The MIT License in [LICENSE](LICENSE) covers the code, text, and images. The console's fonts, Atkinson
Hyperlegible Next and Mono in `platform/console/static/fonts/`, keep the SIL Open Font License 1.1.

## Sources

- Source 1: Can LLM Already Serve as A Database Interface? A BIg Bench for Large-Scale Database Grounded Text-to-SQLs, <https://arxiv.org/abs/2305.03111>, Jinyang Li et al., 2023-05-04
- Source 2: Spider 2.0: Evaluating Language Models on Real-World Enterprise Text-to-SQL Workflows, <https://arxiv.org/abs/2411.07763>, Fangyu Lei et al., 2024-11-12
- Source 3: Semantic Evaluation for Text-to-SQL with Distilled Test Suites, <https://arxiv.org/abs/2010.02840>, Ruiqi Zhong et al., 2020-10-06
- Source 4: You don't need a job queue: Postgres already has SKIP LOCKED, <https://www.prisma.io/blog/you-dont-need-a-job-queue-postgres-already-has-skip-locked>, Prisma, 2026-07-17
- Source 5: LangChain human-in-the-loop, <https://docs.langchain.com/oss/python/langchain/human-in-the-loop>, LangChain, n.d.
- Source 6: MAGIC: Generating Self-Correction Guideline for In-Context Text-to-SQL, <https://arxiv.org/abs/2406.12692>, Arian Askari et al., 2024-06-18
- Source 7: Toward Real-World Table Agents: Capabilities, Workflows, and Design Principles for LLM-based Table Intelligence, <https://arxiv.org/html/2507.10281>, Jiaming Tian et al., 2025-07-14
- Source 8: The art of loop engineering, <https://www.langchain.com/blog/the-art-of-loop-engineering>, Sydney Runkle (LangChain), 2026-06-16
