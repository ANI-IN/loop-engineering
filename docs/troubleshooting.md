# Troubleshooting

> **Terms on this page**
>
> - **Live session**: Everything that runs between one `make preflight` and the next.
> - **Drift canary**: Three easy questions that must pass and two trap questions that must still fail.
> - **Console**: The Streamlit app that shows every loop live, on four pages.
> - **Planted bug**: A defect switched on by a flag so a demo shows its failure every time.
> - **Trace**: The record of one run's steps, each model call and tool call, stored in LangSmith.

Each part lists the exact line you see, its cause, and the fix, with the file the message comes
from. A line that ends in `...` is the start of a longer message. For a first install, follow the
[setup page for your system](../setup/README.md); its steps have their own "If it fails" tables.
When nothing here matches, bring the exact line to the instructor. Never paste your `.env` or a key
anywhere.

The last resort for anything that happens in a demo is always the same: reset the section and run
it again, `make reset NAME=<section slug>`, then the same trigger.

## Setup

Messages from the tools themselves, from `Makefile`, and from `compose.yaml`.

| You see | Cause | Fix |
|---|---|---|
| `make: command not found` | make is not installed, or you are in PowerShell | Open Ubuntu on Windows; otherwise install make |
| `uv: command not found` | The terminal started before uv was installed | Open a new terminal |
| `permission denied` on `/var/run/docker.sock` | Your user is not in the `docker` group yet | Log out and back in; on WSL2, `wsl.exe --shutdown` first |
| `Cannot connect to the Docker daemon` | Docker is not running | `sudo systemctl start docker`; on a Mac, start Docker Desktop or `colima start` |
| `docker: 'compose' is not a docker command` | The Compose plugin is missing | Install `docker-compose-plugin`, or set up the plugin folder on a Mac |
| `OPENAI_MODEL is not set: copy it from .env.example into .env` | `.env` lost the model line (`platform/src/datapilot/settings.py`) | Copy `OPENAI_MODEL=gpt-6-luna` from `.env.example` |
| `flock: command not found` from `make test-stack` or another test target | macOS ships no `flock`; the test targets queue on it (`Makefile`) | `brew install flock`, then run the target again |

## Starting the services

Messages from `make up`, `make ps`, and `make logs` (`compose.yaml`).

| You see | Cause | Fix |
|---|---|---|
| `Bind for 127.0.0.1:5432 failed: port is already allocated` | Another Postgres uses port 5432 | Stop it, or set `POSTGRES_PORT` in `.env` and `make up` again |
| The same line for 8000 or 8501 | Another program uses the application programming interface (API) or console port | Set `API_PORT` or `CONSOLE_PORT` in `.env`, then `make up`; the host commands follow the ports |
| A service shows `Restarting` in `make ps` | It fails at start | `make logs NAME=<service>` shows the error line |
| `migrate` exited with an error | The ops migrations failed | `make logs NAME=migrate`; then `make down` and `make up` |
| `attempt to write a readonly database` in `make logs NAME=worker` | The containers run as user id 1000 and cannot write `~/.datapilot` | Make the folder writable for user id 1000 (below), then `make up` |

The spend ledger, `~/.datapilot/spend-ledger.sqlite`, is shared by your machine and the containers,
which run as user id 1000. The full error is `sqlite3.OperationalError`, ending in `attempt to write a
readonly database` or `unable to open database file`. If root made the folder, `sudo chown -R $USER
~/.datapilot` fixes it; if `id -u` prints a number other than 1000, `chmod -R a+rwX ~/.datapilot`.

## Loading the warehouse

Messages from `make seed` and `make check-data`
(`platform/src/datapilot/loop4_hill_climbing/data_cli.py`).

| You see | Cause | Fix |
|---|---|---|
| An `x` line naming a table count or a content hash | A warehouse differs from `expected.yaml` | `make seed` again; it rebuilds both warehouses from the same seed |
| `make seed` cannot connect | The services are not up | `make up`, then `make seed` |

## make preflight

Messages from `platform/src/datapilot/loop4_hill_climbing/preflight.py`.

| You see | Cause | Fix |
|---|---|---|
| `name the session: make preflight PURPOSE=class\|rehearsal\|thursday-review\|development` | `PURPOSE` is missing | Add it, such as `make preflight PURPOSE=development` |
| `A service is not ready: run make up, then preflight again.` | A check line above it starts with `x` | Fix that service; the `x` line names it |
| `Your OpenAI key was not accepted. Check it with the operations team.` | The key is missing from `.env` or OpenAI rejected it | Paste the key again; if it still fails, check it with whoever issued it |
| `... The model gpt-6-luna is not available to it.` | The key works, but its project cannot use the class model | Allow gpt-6-luna on the key's project, or ask the operations team |
| `OpenAI could not be reached: ...` | No network to OpenAI | Check your connection, then run preflight again |
| `The drift canary failed: a trap question passed ...` | The model no longer behaves as the course measured it | Tell the instructor; calibration runs again before class |
| `The drift canary failed: an easy question failed ...` | The model or the warehouse changed | `make check-data`; if it passes, tell the instructor |
| `Less than one class pass is left of this Eastern time day's token budget ...` | Too few tokens are left today for a class (`PURPOSE=class` only) | See "The token budget refusal" below |

**The token budget refusal.** With `PURPOSE=class`, preflight refuses while less than one class
pass, about 520,000 tokens, is left of the stack's daily token budget, often after a rehearsal on
the same Eastern time day. No class session starts, and the session open before it stays open, so
any run started now belongs to that session. The count starts again at midnight Eastern time;
raising or resetting it sooner is not a course command, so ask whoever runs the class stack. To
hold the class that day anyway, run the command the message's last line prints,
`make preflight PURPOSE=class ACCEPT_TOKENS_LEFT=<the count left>`, with the count the
`token budget` line shows: the class session starts knowingly, and the worker blocks every run once
the cap is reached. [The instructor guide](instructor-guide.md#if-something-breaks) lists which
demos to cut first. Rehearse on an earlier Eastern time day than the class.

Preflight never prints your key. A failed preflight starts no session, so the earlier session, if
any, stays open. The key check lists models and spends nothing, so a key whose account has no
credits passes it; the canary runs then fail, as in the next part.

## Running a demo

Messages from `make demo` and the API (`platform/src/datapilot/loop3_events/`).

| You see | Cause | Fix |
|---|---|---|
| `No live session is open: run make preflight PURPOSE=class\|rehearsal\|thursday-review\|development first` | Runs belong to a live session, and none is open | `make preflight PURPOSE=development` |
| `x no demo named '...'; the demos are ...` | The demo slug is misspelled | Use a slug the line lists; `make demos` lists them too |
| `x no section named '...'; the sections are agent-loop, verification-loop, event-loop, hill-climbing-loop` | The section slug given to `make reset` is misspelled | Use one of the four the line lists |
| Runs end failed, and `make logs NAME=worker` shows `429` with `insufficient_quota` or `credit_balance_exhausted` | The OpenAI account behind the key has no credits left | Add credits to the key's project, or ask the operations team; then run again |
| The run stays in one lane, or the wrong moment shows | A run from earlier is still in the way | `make reset NAME=<section slug>`, then the same trigger |
| The answer differs from the demo page | The model reasons afresh on every run | Expected; the demo page says what may vary |
| A run ends blocked by the budget | The daily token cap, `budgets.tokens_per_day`, is used | It resets on the next Eastern time day |
| A run ends escalated with `a model response was cut off at its output-token cap ...` | One reply reached its agent's `max_output_tokens` (`pack.yaml`, `loop1_agent/guard.py`) | Ask again; if it repeats, read the trace for the reply that ran long |
| A blocked query with `reads the database clock` | The agent's Structured Query Language (SQL) read the clock (`now()`, `CURRENT_DATE`) | Nothing: the analyst gets the business date back and retries |
| The kill switch stays on after a demo | The section was not reset | `make reset NAME=event-loop` releases it |
| A planted bug chip shows when it should not | A `BUG_*` line in `.env` is `1`, or the run was a planted half (`PLANTED=1`) | Set it back to `0`, then `make up`; a planted half's flags end with its runs |
| A live check or the finale says it does not start while planted flags are on | A flag it names is on in `.env`, the shell, or a running service | Set it to `0` in `.env`, then `make up` (and `unset` it in the shell) |

A model call that hits a cap on the ledger on your machine stops with a line that names the cap.
Bring that line to the instructor.

### The finale and the hill-climbing reset

| You see | Cause | Fix |
|---|---|---|
| `x improve-cleared-unattended not sent: ...` | A promotion or its re-runs still run, the kill switch is on, or the level is low | Do the step the rest of the line names (`finale.py`) |
| `not reset: the hill-climbing runner is running the ...` | A reset would delete the experiment the runner still writes to | Wait until the Improve page shows it finished, then reset; or `docker compose restart hill-climbing-runner`, then reset |
| `another hill-climbing runner already serves this database: ...` from `make hill-climbing-runner` | `make up` already runs the runner as a service, and one runner serves a database | Use the service; read it with `make logs NAME=hill-climbing-runner` |

## The console

The console runs at http://localhost:8501 (`CONSOLE_PORT`, `compose.yaml`).

| You see | Cause | Fix |
|---|---|---|
| `No live session. Run make preflight to start one.` | No live session is open | `make preflight PURPOSE=development` |
| `No baseline run in this session yet.` on the Improve page | No baseline experiment started in the open session | Start it from the Improve page, or `make demo NAME=improve-baseline-experiment` |
| The Improve page never updates | The `hill-climbing-runner` service is down | `make ps`; `make logs NAME=hill-climbing-runner`; `make up` |
| A planted bug's half shows no change | It was sent without `PLANTED=1` | `make demo NAME=<demo> PLANTED=1`; `.env` keeps every planted flag at 0 |
| The page does not open from Windows | The services are down after a restart | `make up` in Ubuntu, then reload |
| The status line or the off-the-board row is cut off | The browser toolbars take the space | Press F11 for full screen |
| A result has no trace link | LangSmith tracing is off, or the key is missing | Check `LANGSMITH_TRACING` and `LANGSMITH_API_KEY`, then `make up` |
| A trace link opens a trace that never appears | LangSmith refused the upload: the free plan's 5,000 traces a month are used | See the next part |
| A holdout ledger row reads "Not traced" | Experiment runs are traced as a sample, about 1 run in 5 | Nothing: the row is scored all the same; LangSmith lists the traced runs |

## LangSmith's monthly trace limit

Once the month's traces are used, LangSmith answers every upload with Hypertext Transfer Protocol
(HTTP) status 429 until the month ends; the [costs page](costs.md#langsmith-traces) explains the
limit and how a run records the refusal. The SDK's own line says
`Monthly unique traces usage limit exceeded`. DataPilot prints the first refusal of each
process once, and a count when the process ends
(`platform/src/datapilot/observability/background.py`): `LangSmith refused a trace upload (its
monthly trace limit); later refusals are counted, not shown`.

The run itself goes on unslowed, and its result and score are unchanged. To stop the refused
uploads before the month ends, set `LANGSMITH_TRACING=false` in `.env`, then `make up`; results
then carry no trace link.

## Assignments

Messages from `make check-assignment` and `make apply-solution`
(`platform/src/datapilot/assignments/`). A check that stops exits with code 2.

| You see | Cause | Fix |
|---|---|---|
| `Live checks need your OpenAI key from the operations team` | No key in `.env`, or OpenAI rejected it | Add the key; if it is there, check it with whoever issued it |
| `The OpenAI account behind your key has no credits left, ...` | Runs failed with an out-of-credits error | Add credits to the key's project, then run the check again |
| `OpenAI answered ... to the key check; try again later.` | OpenAI returned an error | Wait a minute and run the check again |
| `Stopped: this check reached its spend cap of ...`, then `NOT RUN` lines | The check's own cap, `assignments.check_cap_usd` (1.00 dollar), was reached | Read its runs' traces for a loop that keeps spending; then run it again |
| `Stopped: run ... ended blocked_budget, ...` | That stack's daily token budget is spent | Run the check again: on its own stack it sets the count back to zero |
| `The kill switch of this check's stack is engaged, ...` | A run on the check's stack was stopped | Release it on the check's console, or with the reset command the line prints |
| `Docker is not available. The live check brings up the real stack ...` | The check starts its own Compose stack | Start Docker; or, with the services already up, set `DATAPILOT_ASSIGNMENT_STACK=running` |
| `The live check never runs on the class stack ...` | `COMPOSE_PROJECT_NAME` is `datapilot` | Leave it unset |
| `POSTGRES_PORT=5432 is the class stack's port ...` (or the API or console port) | A class port is set for the check | Leave it unset, or give the check's own port |
| `The check's stack (...) is not reachable: ...` | The reset command ran while that stack is down | Run the check first; its services stay up after it |
| `Not reset: the Compose project ... publishes Postgres on port ...` | The reset named another stack's port | Use the project and port the check printed |
| `The solutions are withheld until the Thursday review: ...` | A public copy has no `solution/` folders until the review | Check your own work with `make check-assignment NAME=<slug>` |
| `... already exists, and apply never replaces a folder unasked: ...` | The scratch copy is there from before | Add `FORCE=1` to the command, or remove the folder |
| `FAIL` on every requirement of an untouched starter | The starter fails by design | Build the extension points the README names |
| `FAIL` on a model-dependent requirement once | Model-dependent requirements pass on 2 of 3 runs | Run the check again; read the trace of the failed run |

## Your own repository

Problems when you point DataPilot at your own Postgres or a new domain pack
([use it in your repository](../use-in-your-repo/README.md)).

| You see | Cause | Fix |
|---|---|---|
| The agent sees no tables | The read-only role has no `SELECT` on the schema, or `allowed_schema` is wrong | Grant `USAGE` and `SELECT`, and set `databases.allowed_schema` |
| `personal_data.marketing_view must be in the allowed schema` | The marketing view names another schema | Point it at a view inside `allowed_schema` |
| A benchmark item fails to load | A field is missing or misspelled | The pack check in the guide names the item and the field |
| A write succeeds | The agent role can write | Revoke every privilege except `SELECT`; never use an owner role |
