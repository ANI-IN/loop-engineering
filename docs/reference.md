# Reference

> **Terms on this page**
>
> - **Live session**: Everything that runs between one `make preflight` and the next.
> - **Drift canary**: Three easy questions that must pass and two trap questions that must still fail.
> - **Knowledge version**: A numbered set of business rules given to the agent in its prompt.
> - **Planted bug**: A defect switched on by a flag so a demo shows its failure every time.
> - **Domain pack**: The folder that holds one warehouse's settings, rules, benchmark, and knowledge.

This page lists everything you look up but do not read in order: every make target, every setting
and variable, the caps and limits, and the folders. Each table names the file its values come
from. Every course term is in the [glossary](glossary.md).

## Make targets

Every target is a thin wrapper over `uv run ...` or `docker compose ...` (`Makefile`), so the same
commands work without make. On Windows, run make inside Ubuntu on WSL2. `make help` lists every
target with its one-line description. The "Model calls" column says whether the target calls
OpenAI with your key.

### Run DataPilot

| Target | What it does | Model calls |
|---|---|---|
| `make setup` | Installs the pinned packages; creates `.env` from `.env.example` if missing | None |
| `make up` | Builds the image, starts the five services, and waits until they are healthy | None |
| `make down` | Stops every service; the database volume is kept | None |
| `make ps` | Shows the services and their health | None |
| `make logs` | Follows the logs of every service; `NAME=<service>` for one | None |
| `make migrate` | Applies the ops schema migrations | None |
| `make seed` | Generates and loads `warehouse` and `warehouse_alt`, deterministic | None |
| `make check-data` | Row counts and content hash of both warehouses against `expected.yaml` | None |
| `make check-pack PACK=<name>` | Checks a pack's files, queries, and preflight data check | None |
| `make preflight PURPOSE=<purpose>` | Checks the setup and canary, then starts a live session | Five canary questions |
| `make demos` | Lists every demo with its tier and name | None |
| `make demo NAME=<slug>` | Triggers one live demo through the api, as the console button does | Yes, for demos that run the agent |
| `make reset NAME=<section slug>` | Clears a section's live run state and releases the kill switch | None |
| `make reset-discarding-baseline NAME=hill-climbing-loop` | The full reset: it also discards the session's baseline experiment | None |
| `make open-code NAME=<section slug>` | Prints the files and line ranges a section shows in class | None |
| `make hill-climbing-runner` | Serves the Improve page: experiments, the analyzer team, promotions | Yes, for each request |
| `make live-smoke` | Five real calls across the system, each with tokens, cost, and trace link | Yes |
| `make spend` | The model spend recorded on this machine, by activity | None |

`PURPOSE` is one of `class`, `rehearsal`, `thursday-review`, or `development`. The section slugs
are `agent-loop`, `verification-loop`, `event-loop`, and `hill-climbing-loop`. The demo slugs are
in each section's demo page and in `platform/demos/registry.yaml`.

Two more commands of the `datapilot` command line, with no model calls:

- `make archive` and `make archive-show NAME=<experiment id>` read the
  reset archive: before `make reset NAME=hill-climbing-loop` deletes or retires experiments,
  promotion decisions, requests, eligibility, or knowledge versions, it copies each row into
  `ops.reset_archive_rows`, stamped with the reset time and the live session.
- `make safeguard-verify NAME=<version> RUN=<run id> BY="<name>"` (in rehearsal),
  `make safeguard-activate BY="<name>"` (in class), and
  `make safeguard-status`: the class-day safeguard in the instructor guide.

### Assignments

| Target | What it does | Model calls |
|---|---|---|
| `make check-assignment NAME=<slug>` | The live check of one assignment: a cost estimate first, the actual cost last | Yes, with your key |
| `make apply-solution NAME=<slug> VARIANT=<variant>` | A scratch copy of the starter with one solution applied | None |

`VARIANT` is `reference`, `alternative-one`, or `alternative-two`. `make check-assignment
NAME=<slug> TREE=<copy>` checks the copy that `make apply-solution` printed.
<!-- provisional: lands with the assignments merge -->

### Checks and documentation

| Target | What it does | Model calls |
|---|---|---|
| `make test` | The zero-token suites: no model calls, no database | None |
| `make test-integration` | Zero-token tests against Postgres | None |
| `make test-security` | The security suite, zero tokens | None |
| `make test-stack`, `make test-stack-down` | Starts or stops the tests' own Postgres, apart from the live stack | None |
| `make lint` | Ruff, import contracts, the style, prose, and naming checks | None |
| `make format` | Rewrites files with `ruff check --fix` and `ruff format` | None |
| `make import-lint` | The import contracts in `pyproject.toml` | None |
| `make lint-prose` | Banned words and emoji in the course pages | None |
| `make check-style` | The course style check; `CHECK_STYLE_OPTS=--strict` makes warnings fail | None |
| `make check-style-strict` | The style check where warnings fail too | None |
| `make check-names` | The naming rule on course pages, the slide outline, and commit messages | None |
| `make check-short-forms` | The naming rule on this branch's commit messages | None |
| `make guards` | Git configuration allow-list, the only author, no tracked `.env` | None |
| `make registries` | Validates the demo and planted-item registries | None |
| `make docs` | Regenerates every generated page from its registry | None |
| `make docs-check` | Fails if a generated page is out of date | None |
| `make outline` | Rebuilds `slides/outline.md` from `slides/source/` and checks every slide rule | None |
| `make style-tile` | The console style tile on port 8531, with specimen data | None |
| `make check` | Everything the continuous integration runs without a database | None |
| `make verify` | Every check, each result printed; fails if any one fails | None |
| `make calibrate STEP=<step>` | One live calibration step, for the instructor before a cohort | Yes |
| `make verify-assignments` | Each starter once and each solution twice, with captures | Yes |

`make verify-assignments` is the course build's own verification of the solutions.
<!-- provisional: lands with the assignments merge -->

## Settings and variables

Settings come from `.env` at the repository root, which `make setup` copies from `.env.example`.
`platform/src/datapilot/settings.py` reads them. The defaults below are the values in
`.env.example`.

| Variable | Default in `.env.example` | What it sets |
|---|---|---|
| `OPENAI_API_KEY` | empty | Your key from the operations team |
| `LANGSMITH_API_KEY` | empty | Your key from your own LangSmith account |
| `OPENAI_MODEL` | `gpt-6-luna` | The analyst, the schema scout, and the reviewer |
| `OPENAI_ANALYZER_MODEL` | `gpt-6-luna` | The analyzer team; empty means `OPENAI_MODEL` |
| `LANGSMITH_TRACING` | `true` | Sends a trace of every run |
| `LANGSMITH_ENDPOINT` | `https://api.smith.langchain.com` | EU accounts use `https://eu.api.smith.langchain.com` |
| `LANGSMITH_PROJECT` | `datapilot-live` | The project live runs trace to |
| `LANGSMITH_EXPERIMENTS_PROJECT` | `datapilot-experiments` | The project benchmark runs trace to |
| `DATAPILOT_PACK` | `datapilot_us` | The domain pack every process reads, a folder under `platform/packs/` |
| `DATABASE_URL_OWNER` | the Compose owner role | Migrations, seeding, ops tables; never the agent |
| `DATABASE_URL_AGENT` | the Compose read-only role on `datapilot` | The agent's read-only role on the warehouse schema |
| `DATABASE_URL_AGENT_ALT` | the same role on `warehouse_alt` | The second database the evaluator compares on |
| `DATABASE_URL_APP` | the Compose application role | The api, the worker, the scheduler, and the console |
| `SERVICES_DATABASE_URL_AGENT`, `SERVICES_DATABASE_URL_AGENT_ALT` | unset: the Compose Postgres | The agent's two databases as the services in Docker reach them |
| `POSTGRES_PORT`, `API_PORT`, `CONSOLE_PORT` | `5432`, `8000`, `8501` | Host ports for Compose |
| `DATAPILOT_SPEND_ACTIVITY` | `development` | The ledger activity model calls are recorded under (see below) |
| `DATAPILOT_BUILD_BUDGET` | `0` | Build only: `1` enforces the course build's budget lines (see below) |
| `DATAPILOT_SESSION_SINCE` | empty | Build only: a session's start time; its limits apply (see below) |
| `DATAPILOT_BUSINESS_DATE` | `2026-01-31` | The day DataPilot treats as today |
| `DATAPILOT_DISPLAY_TIMEZONE` | empty | Empty shows each viewer's own time zone |
| `DATAPILOT_API_URL` | `http://localhost:8000` | Where the command line and the console reach the api |
| `DATAPILOT_ALLOW_DEMO_CONTROLS` | `1` | Lets the worker-restart control work, for demos |
| `DEMO_PACING`, `DEMO_PACING_SECONDS` | `0`, `2.0` | Pauses between lifecycle stages; never changes results |
| `BUG_*` | `0` each | The planted bugs, all off; [planted items](planted-items.md) lists each one |

A run started by `make demo` or a live check carries the spend activity of the command that
started it. With `DATAPILOT_BUILD_BUDGET` off, your own OpenAI project limit is the only limit
besides each assignment check's own spend cap (`assignments.check_cap_usd`, 1.00 dollar), which
holds with the switch on or off.

While `DATAPILOT_SESSION_SINCE` names a session's start, the session limits in `pack.yaml`
(`build_budget.session`) are checked before every model call, in addition to the lines, counting
only the spend since that time: 0.40 dollars for development live checks, 1.00 for calibration,
1.50 for assignment verification, and 2.50 in total. A line not listed there gets nothing in the
session. The variable is read from the environment first, then from `.env`, and `make spend` shows
the session as "this session since" its start.

The Compose services reach the owner and application roles on the `postgres` container
(`compose.yaml`), and the agent's databases at the `SERVICES_` addresses, the `postgres` container
when they are unset; the `DATABASE_URL_` values above are for commands you run on your machine.
After a change to `DATAPILOT_PACK`, run `make up`, then `make preflight`: each pack keeps its own
knowledge versions, and preflight reads its data check and canary from the selected pack.

## Caps and limits

Every cap is a value in the selected pack's `pack.yaml`; the values below are those of
`platform/packs/datapilot_us/pack.yaml`. A cap is a cap: a run stops at it, and the console and the
terminal say which one. The build budget switch, `DATAPILOT_BUILD_BUDGET`, never changes them.

| Cap | Value | Setting in `pack.yaml` |
|---|---|---|
| Rows returned to the model per query | 50 | `limits.row_cap` |
| Attempts before a run ends escalated | 3 | `limits.max_retries` |
| Model calls per run | 12 | `limits.model_call_limit` |
| Tool calls per run | 16 | `limits.tool_call_limit` |
| Statement timeout | 5,000 milliseconds | `limits.statement_timeout_ms` |
| Idle in a transaction, agent role | 10,000 milliseconds | `limits.idle_in_transaction_timeout_ms` |
| Temporary files per query, agent role | 102,400 kilobytes | `limits.temp_file_limit_kb` |
| Tokens per run | 60,000 | `budgets.tokens_per_run` |
| Tokens per day | 2,000,000 | `budgets.tokens_per_day` |
| Spend of one assignment check | 1.00 dollar | `assignments.check_cap_usd` |
| Planner cost of one query | 500,000 | `cost_guard.max_plan_cost` |
| Planner rows of one query | 5,000,000 | `cost_guard.max_plan_rows` |
| Consecutive escalations before the autonomy level drops | 3 | `autonomy.demote_after_consecutive_escalations` |
| Kill switch disarm time | 5 seconds | `console.kill_switch_disarm_seconds` |

The benchmark measurement uses these values from the `evaluation` block of the same file:

| Setting | Value | What it means |
|---|---|---|
| `holdout_repeats`, `holdout_pass_threshold` | 3, 2 | Each holdout item runs 3 times per version and passes on 2 |
| `dev_regression_reruns`, `dev_regression_threshold` | 2, 2 | A newly failing dev item runs twice more per version; see below |
| `holdout_regression_reruns`, `holdout_regression_fail_threshold` | 3, 2 | An apparent holdout regression counts only if 2 of 3 more runs fail |
| `concurrency` | 8 | Benchmark runs at once |

An apparent dev regression counts only when the candidate fails 2 of its 2 re-runs and the active
version passes 2 of its 2 (`dev_regression_threshold`), so an item unstable under both versions is
never a regression.

## Folders

| Folder | What it holds |
|---|---|
| `setup/` | The setup pages for each system and the before-class checklist |
| `section-1-agent-loop/` to `section-4-hill-climbing-loop/` | Each section: pages, demo, assignment, diagrams, and readings |
| `final-project/` | The open-ended final project and its checklist |
| `use-in-your-repo/` | Pointing DataPilot at your own Postgres, or building a new domain pack |
| `docs/` | Start here, this reference, costs, the glossary, the instructor guide |
| `guide/` | The Live Demo Guide: every live demo step by step |
| `slides/` | The class deck and its outline |
| `platform/src/datapilot/` | The package: one folder per loop, plus `contracts/` and `observability/` |
| `platform/packs/datapilot_us/` | The Harbor & Pine domain pack: settings, data generator, benchmark, knowledge |
| `platform/packs/_template/` | A domain pack to copy for your own warehouse |
| `platform/console/` | The Streamlit console: the Agent, Verify, Events, and Improve pages |
| `platform/demos/` | The demo registry every demo page and trigger comes from |
| `platform/planted/` | The planted-item registry |
| `platform/ops/` | Ops migrations, warehouse Structured Query Language (SQL) files, Docker files |
| `platform/tests/` | The unit and integration tests |
| `platform/scripts/` | The style, prose, naming, and repository checks |
