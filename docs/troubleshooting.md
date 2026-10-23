# Troubleshooting

> **Terms on this page**
>
> - **Live session**: Everything that runs between one `make preflight` and the next.
> - **Drift canary**: Three easy questions that must pass and two trap questions that must still fail.
> - **Console**: The Streamlit app that shows every loop live, on four pages.
> - **Planted bug**: A defect switched on by a flag so a demo shows its failure every time.

Each part lists the exact line you see, its cause, and the fix, with the file the message comes
from. For a first install, follow the [setup page for your system](../setup/README.md); its
steps have their own "If it fails" tables. When nothing here matches, bring the exact line to the
instructor. A key problem goes to the operations team. Never paste your `.env` or a key anywhere.

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

## Starting the services

Messages from `make up`, `make ps`, and `make logs` (`compose.yaml`).

| You see | Cause | Fix |
|---|---|---|
| `Bind for 0.0.0.0:5432 failed: port is already allocated` | Another Postgres uses port 5432 | Stop it, or set `POSTGRES_PORT` in `.env` and `make up` again |
| The same line for 8000 or 8501 | Another program uses the api or console port | Set `API_PORT` or `CONSOLE_PORT` in `.env` |
| A service shows `Restarting` in `make ps` | It fails at start | `make logs NAME=<service>` shows the error line |
| `migrate` exited with an error | The ops migrations failed | `make logs NAME=migrate`; then `make down` and `make up` |

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
| `Your OpenAI key was not accepted. Check it with the operations team.` | The key is missing from `.env` or OpenAI rejected it | Paste the key again; if it still fails, ask the operations team |
| `... The model gpt-6-luna is not available to it.` | The key works, but its project cannot use the class model | Ask the operations team to enable gpt-6-luna on your key |
| `OpenAI could not be reached: ...` | No network to OpenAI | Check your connection, then run preflight again |
| `The drift canary failed: a trap question passed ...` | The model no longer behaves as the course measured it | Tell the instructor; calibration runs again before class |
| `The drift canary failed: an easy question failed ...` | The model or the warehouse changed | `make check-data`; if it passes, tell the instructor |

Preflight never prints your key. A failed preflight starts no session, so the earlier session, if
any, stays open.

## Running a demo

Messages from `make demo` and the api (`platform/src/datapilot/loop3_events/`).

| You see | Cause | Fix |
|---|---|---|
| `No live session is open: run make preflight first.` | Runs belong to a live session, and none is open | `make preflight PURPOSE=development` |
| `no demo named '...'; make demos lists them` | The slug is misspelled | `make demos` lists every slug |
| The run stays in one lane, or the wrong moment shows | A run from earlier is still in the way | `make reset NAME=<section slug>`, then the same trigger |
| The answer differs from the demo page | The model reasons afresh on every run | Expected; the demo page says what may vary |
| A run ends blocked by the budget | The daily token cap, `budgets.tokens_per_day`, is used | It resets on the next Eastern time day |
| The kill switch stays on after a demo | The section was not reset | `make reset NAME=event-loop` releases it |
| A planted bug chip shows when it should not | A `BUG_*` line in `.env` is `1` | Set it back to `0`, then `make up` |

A model call that hits a cap on the ledger on your machine stops with a line that names the cap.
Bring that line to the instructor.

## The console

The console runs at http://localhost:8501 (`CONSOLE_PORT`, `compose.yaml`).

| You see | Cause | Fix |
|---|---|---|
| `No live session. Run make preflight to start one.` | No live session is open | `make preflight PURPOSE=development` |
| `No baseline run in this session yet.` on the Improve page | No baseline experiment started in the open session | Start it from the Improve page, or `make demo NAME=improve-baseline-experiment` |
| The Improve page never updates | The hill-climbing runner is not running | `make hill-climbing-runner` in its own terminal |
| The page does not open from Windows | The services are down after a restart | `make up` in Ubuntu, then reload |
| The status line or the off-the-board row is cut off | The browser toolbars take the space | Press F11 for full screen |
| A result has no trace link | LangSmith tracing is off or the key is wrong | Check `LANGSMITH_TRACING` and `LANGSMITH_API_KEY`, then `make up` |
| A holdout ledger row reads "Not traced" | Experiment runs are traced as a sample, about 1 run in 5 | Nothing: the row is scored all the same; LangSmith lists the traced runs |

## Assignments

Messages from `make check-assignment` (`platform/src/datapilot/assignments/`).
<!-- provisional: lands with the assignments merge -->

| You see | Cause | Fix |
|---|---|---|
| `Live checks need your OpenAI key from the operations team` | No key in `.env`, or OpenAI rejected it | Add the key; if it is there, ask the operations team |
| `FAIL` on every requirement of an untouched starter | The starter fails by design | Build the extension points the README names |
| `FAIL` on a model-dependent requirement once | Model-dependent requirements pass on 2 of 3 runs | Run the check again; read the trace of the failed run |
| `OpenAI answered ... to the key check; try again later.` | OpenAI returned an error | Wait a minute and run the check again |

## Your own repository

Problems when you point DataPilot at your own Postgres or a new domain pack
([use it in your repository](../use-in-your-repo/README.md)).

| You see | Cause | Fix |
|---|---|---|
| The agent sees no tables | The read-only role has no `SELECT` on the schema, or `allowed_schema` is wrong | Grant `USAGE` and `SELECT`, and set `databases.allowed_schema` |
| `personal_data.marketing_view must be in the allowed schema` | The marketing view names another schema | Point it at a view inside `allowed_schema` |
| A benchmark item fails to load | A field is missing or misspelled | The pack check in the guide names the item and the field |
| A write succeeds | The agent role can write | Revoke every privilege except `SELECT`; never use an owner role |
