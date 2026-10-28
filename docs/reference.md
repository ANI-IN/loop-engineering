# Reference

> **Terms on this page**
>
> - **Live session**: Everything that runs between one `make preflight` and the next.
> - **Drift canary**: Three easy questions that must pass and two trap questions that must still fail.
> - **Knowledge version**: A numbered set of business rules given to the agent in its prompt.
> - **Planted bug**: A defect switched on by a flag so a demo shows its failure every time.
> - **Domain pack**: The folder that holds one warehouse's settings, rules, benchmark, and knowledge.
> - **Development split**: The benchmark questions the analyzer team may learn from.
> - **Holdout split**: The benchmark questions the analyzer team never sees; the gate decides on them.

This page lists everything you look up but do not read in order: every make target, every setting
and variable, the stacks and their ports, the caps and limits, and the folders. The services, the
application programming interface (API) routes, and the ops tables are on the
[architecture page](architecture.md). Each table names the file its values come
from. Every course term is in the [glossary](glossary.md).

## Make targets

Every target is a thin wrapper over `uv run ...` or `docker compose ...` (`Makefile`), so the same
commands work without make. On Windows, run make inside Ubuntu on WSL2. `make help` lists every
target with its one-line description. The "Model calls" column says whether the target calls
OpenAI with your key. A target's variables, such as `NAME=` and `PLANTED=`, count only on the make
command line: a variable your shell exports is ignored, including the `NAME` that WSL sets to the
computer's name in every shell.

### Run DataPilot

| Target | What it does | Model calls |
|---|---|---|
| `make setup` | Installs the pinned packages; creates `.env` from `.env.example` if missing | None |
| `make up` | Builds the image, starts the six services, and waits until they are healthy | None |
| `make restart` | Recreates the services from the built image, so a `.env` change applies | None |
| `make down` | Stops every service; the database volume is kept | None |
| `make ps` | Shows the services and their health | None |
| `make logs` | Follows the logs of every service; `NAME=<service>` for one | None |
| `make migrate` | Applies the ops schema migrations | None |
| `make seed` | Generates and loads `warehouse` and `warehouse_alt`, deterministic | None |
| `make check-data` | Row counts and content hash of both warehouses against `expected.yaml` | None |
| `make check-pack PACK=<name>` | Checks a pack's files, queries, and preflight data check | None |
| `make preflight PURPOSE=<purpose>` | Checks the setup and canary, then starts a live session | Five canary questions |
| `make demos` | Lists every demo with its tier and name | None |
| `make demo NAME=<slug>` | Triggers one live demo through the API, as the console button does | Yes, for demos that run the agent |
| `make demo NAME=<slug> PLANTED=1` | The demo's planted half: its planted bugs on for its own runs only | Yes, as above |
| `make reset NAME=<section slug>` | Clears a section's live run state and releases the kill switch | None |
| `make reset-discarding-baseline NAME=hill-climbing-loop` | The full reset: it also discards the session's baseline experiment | None |
| `make open-code NAME=<section slug>` | Prints the files and line ranges a section shows in class | None |
| `make autonomy LEVEL=<level> BY="<your name>"` | Sets the autonomy level through the API; the finale needs `unattended` | None |
| `make hill-climbing-runner` | The runner on the host, for development only; `make up` runs it, and a second one refuses | Yes, for each request |
| `make live-smoke` | Five real calls across the system, each with tokens, cost, and trace link | Yes |
| `make spend` | The model spend recorded on this machine, by activity | None |

`PURPOSE` is one of `class`, `rehearsal`, `thursday-review`, or `development`. With
`PURPOSE=class`, preflight refuses while less than the tokens of one class run-through
(`budgets.class_pass_tokens` in `pack.yaml`) are left of the day's token budget;
`ACCEPT_TOKENS_LEFT=<count>`, the exact count left in the command the refusal prints (digits,
without commas), starts the class session anyway, knowingly
([instructor guide](instructor-guide.md#if-something-breaks)). With 0 tokens left the refusal
offers no such command and preflight takes none. No course command resets or raises the day's
count, and none is planned: the knowing start keeps the cap and the count as they are, so every
run still stops at the cap. The section slugs
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
| `make apply-solution NAME=<slug> VARIANT=<variant>` | Scratch copy of the starter with one solution; `FORCE=1` replaces a copy | None |

`VARIANT` is `reference`, `alternative-one`, or `alternative-two`. `make check-assignment
NAME=<slug> TREE=<copy>` checks the copy that `make apply-solution` printed. Until the Thursday
review, a public copy has no `solution/` folders, so `make apply-solution` and
`make verify-assignments` stop and say the solutions are withheld.

`make check-assignment` also reads `PURPOSE=<purpose>`: with it, the check starts a live session
of that purpose on its own stack unless one of the same purpose opened there today.

### Checks and documentation

| Target | What it does | Model calls |
|---|---|---|
| `make test` | The zero-token suites: no model calls, no database | None |
| `make test-integration` | Zero-token tests against Postgres | None |
| `make test-security` | The security suite, zero tokens | None |
| `make test-console` | The console in a real browser on the tests' own Postgres; rewrites `platform/console/screenshots/` | None |
| `make test-stack`, `make test-stack-down` | Starts or stops the tests' own Postgres, apart from the live stack | None |
| `make lint` | Ruff, import contracts, the style, prose, and naming checks | None |
| `make format` | Rewrites files with `ruff check --fix` and `ruff format` | None |
| `make import-lint` | The import contracts in `pyproject.toml` | None |
| `make lint-prose` | Banned words and emoji in the course pages | None |
| `make check-style` | The course style check; `CHECK_STYLE_OPTS=--strict` makes warnings fail | None |
| `make check-style-strict` | The style check where warnings fail too | None |
| `make check-images` | Published images: size, blank areas, clipped edges, alt text (note 2) | None |
| `make check-images ARGS=--rehearsal` | The same, where the exceptions that expire at the rehearsal fail | None |
| `make check-names` | The naming rule on the course pages and the slide outline (note 1) | None |
| `make check-short-forms` | The naming rule on this branch's commit messages (note 1) | None |
| `make guards` | No `core.worktree` and no tracked `.env`; more checks in the build (note 1) | None |
| `make registries` | Validates the demo and planted-item registries | None |
| `make docs` | Regenerates every generated page from its registry | None |
| `make docs-check` | Fails if a generated page is out of date | None |
| `make outline` | Writes `slides/outline.md` from the final class deck, which it only reads | None |
| `make style-tile` | The console style tile on port 8531, with specimen data | None |
| `make check` | Everything the continuous integration runs without a database | None |
| `make ci-local REPO=<release clone>` | The continuous integration workflow's own steps in a clean clone, no secrets | None |
| `make diagrams ARGS=--check` | Reports stale diagram renders; `ARGS=--build` rewrites them from `definitions.py` | None |
| `make verify` | Every check, each result printed; fails if any one fails | None |
| `make calibrate STEP=<step>` | One live calibration step, for the instructor before a cohort | Yes |
| `make verify-assignments` | Each starter once and each solution twice, with captures | Yes |

`make verify-assignments` is the course build's own verification of the solutions.

Note 1: the commit-message and author checks run in the course's build only: `make check-names`
reads commit messages there, `make check-short-forms` runs there, and `make guards` also checks
that every commit has the one author and no co-author lines and that the git configuration holds
only allowed keys. Your own copy skips them.

Note 2: the image check is part of `make verify`. Its reviewed exceptions are the list `EXCEPTIONS` in
`platform/scripts/check_images.py`. Each names one image, the kind of problem it excuses, the
reason, and when it expires: `never` (the Agent page's empty state, whose blank area is the state
shown) or `rehearsal` (an image the rehearsal retakes). The check prints each excused problem on an
`excused` line and counts them. It fails on an exception whose image is missing or no longer has
that problem, so a retaken image's exception is removed with the retake.

## Settings and variables

Settings come from `.env` at the repository root, which `make setup` copies from `.env.example`.
`platform/src/datapilot/settings.py` reads them. The defaults below are the values in
`.env.example`.

| Variable | Default in `.env.example` | What it sets |
|---|---|---|
| `OPENAI_API_KEY` | empty | Your key, from the operations team or your own OpenAI project |
| `LANGSMITH_API_KEY` | empty | Your key from your own LangSmith account |
| `OPENAI_MODEL` | `gpt-6-luna` | The analyst, the schema scout, and the reviewer |
| `OPENAI_ANALYZER_MODEL` | `gpt-6-luna` | The analyzer team; empty means `OPENAI_MODEL` |
| `LANGSMITH_TRACING` | `true` | Sends traces: every demo run, a sample of experiment runs |
| `LANGSMITH_ENDPOINT` | `https://api.smith.langchain.com` | EU accounts use `https://eu.api.smith.langchain.com` |
| `LANGSMITH_PROJECT` | `datapilot-live` | The project live runs trace to |
| `LANGSMITH_EXPERIMENTS_PROJECT` | `datapilot-experiments` | The project benchmark runs trace to |
| `DATAPILOT_PACK` | `datapilot_us` | The domain pack every process reads, a folder under `platform/packs/` |
| `DATABASE_URL_OWNER` | unset: the Compose owner role on `localhost` and `POSTGRES_PORT` | Migrations, seeding, ops tables; never the agent |
| `DATABASE_URL_AGENT` | unset: the Compose read-only role on `datapilot`, on `POSTGRES_PORT` | The agent's read-only role on the warehouse schema |
| `DATABASE_URL_AGENT_ALT` | unset: the same role on `warehouse_alt`, on `POSTGRES_PORT` | The second database the evaluator compares on |
| `DATABASE_URL_APP` | unset: the Compose application role on `POSTGRES_PORT` | The api service, the worker, the scheduler, and the console |
| `SERVICES_DATABASE_URL_AGENT`, `SERVICES_DATABASE_URL_AGENT_ALT` | unset: the Compose Postgres | The agent's two databases as the services in Docker reach them |
| `POSTGRES_PORT`, `API_PORT`, `CONSOLE_PORT` | `5432`, `8000`, `8501` | Host ports for Compose; the host commands follow them (below) |
| `DATAPILOT_SPEND_ACTIVITY` | `development` | The ledger activity model calls are recorded under (see below) |
| `DATAPILOT_BUILD_BUDGET` | `0` | Build only: `1` enforces the course build's budget lines (see below) |
| `DATAPILOT_SESSION_SINCE` | empty | Build only: a session's start time; its limits apply (see below) |
| `DATAPILOT_BUSINESS_DATE` | `2026-01-31` | The day DataPilot treats as today |
| `DATAPILOT_DISPLAY_TIMEZONE` | empty | Empty shows each viewer's own time zone |
| `DATAPILOT_API_URL` | unset: `http://localhost:` and `API_PORT` | Where the command line and the console reach the API |
| `DATAPILOT_ALLOW_DEMO_CONTROLS` | `1` | For demos: the worker restart, a demo's planted flags, a planted button (below) |
| `DEMO_PACING`, `DEMO_PACING_SECONDS` | `0`, `2.0` | Pauses between lifecycle stages; never changes results |
| `BUG_*` | `0` each | The planted bugs, all off; [planted items](planted-items.md) lists each one |

The host commands follow the ports: while the `DATABASE_URL_*` addresses and `DATAPILOT_API_URL`
are unset, as `.env.example` leaves them, each is the Compose one on `localhost` at
`POSTGRES_PORT` or `API_PORT`, so moving a port in `.env` moves every command; run `make up` after
it. `DATAPILOT_ALLOW_DEMO_CONTROLS` allows the console's worker-restart control, a demo's planted
flags for its own runs, and the console's Improve > Run the naive analyzer (planted) button.

These are read from your shell's environment, not from `.env.example`:

| Variable | Default | What it sets |
|---|---|---|
| `COMPOSE_PROJECT_NAME` | `datapilot-assignments` for a live check | The Compose project of a check's own stack; `datapilot` is refused |
| `POSTGRES_PORT`, `API_PORT`, `CONSOLE_PORT` | `55433`, `8100`, `8502` for a live check | A check's own ports; the class ports are refused |
| `DATAPILOT_ASSIGNMENT_STACK` | unset | `running`: a live check uses the services already running |
| `DATAPILOT_ASSIGNMENT_WORK` | `~/.datapilot/assignment-work` | Where `make apply-solution` writes its copies |
| `DATAPILOT_SPEND_LEDGER` | `~/.datapilot/spend-ledger.sqlite` | The ledger file; the services use the mounted folder |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | Where a live check asks whether your key works |
| `FORCE` | unset | `1`: `make apply-solution` replaces an existing copy |

A run started by `make demo` or a live check carries the spend activity of the command that
started it. With `DATAPILOT_BUILD_BUDGET` off, your own OpenAI project limit is the only limit
besides each assignment check's own spend cap (`assignments.check_cap_usd`, 1.00 dollar), which
holds with the switch on or off.

While `DATAPILOT_SESSION_SINCE` names a session's start, the session limits in `pack.yaml`
(`build_budget.session`) are checked before every model call, in addition to the lines, counting
only the spend since that time; you set them for each session, in `pack.yaml`.
A line not listed there gets nothing in the session. The variable is read from the environment first, then from `.env`, and `make spend` shows
the session as "this session since" its start.

The Compose services reach the owner and application roles on the `postgres` container
(`compose.yaml`), and the agent's databases at the `SERVICES_` addresses, the `postgres` container
when they are unset; the `DATABASE_URL_` values above are for commands you run on your machine.
After a change to `DATAPILOT_PACK`, run `make up`, then `make preflight`: each pack keeps its own
knowledge versions, and preflight reads its data check and canary from the selected pack.

### Stacks and ports

Each stack is its own Compose project with its own ports, so the tests and the checks never touch
the class data. The [architecture page](architecture.md#other-stacks) lists every stack, its
ports, and what starts it.

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
| `dev_regression_reruns`, `dev_regression_threshold` | 2, 2 | A newly failing development question runs twice more per version; see below |
| `holdout_regression_reruns`, `holdout_regression_fail_threshold` | 3, 2 | An apparent holdout regression counts only if 2 of 3 more runs fail |
| `concurrency` | 8 | Benchmark runs at once |

An apparent regression on the development questions counts only when the candidate fails 2 of its 2 re-runs and the active
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
| `slides/` | The outline of the class deck, which is handed out separately |
| `platform/src/datapilot/` | The package: one folder per loop, plus `contracts/` and `observability/` |
| `platform/packs/datapilot_us/` | The Harbor & Pine domain pack: settings, data generator, benchmark, knowledge |
| `platform/packs/_template/` | A domain pack to copy for your own warehouse |
| `platform/console/` | The Streamlit console: the Agent, Verify, Events, and Improve pages |
| `platform/demos/` | The demo registry every demo page and trigger comes from |
| `platform/planted/` | The planted-item registry |
| `platform/ops/` | Ops migrations, warehouse Structured Query Language (SQL) files, Docker files |
| `platform/tests/` | The unit and integration tests |
| `platform/scripts/` | The style, prose, naming, and repository checks |
| `platform/tools/` | The diagram definitions and their export, and the page generators |
