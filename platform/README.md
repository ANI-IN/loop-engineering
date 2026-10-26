# Module: Loop Engineering - The platform folder

Everything DataPilot runs on: the Python package, the console, the domain packs, the registries,
the migrations, the tests, and the authoring tools. The services, the application programming
interface (API) routes, and the ops tables are on the [architecture page](../docs/architecture.md);
every make target and setting is on the [reference page](../docs/reference.md).

| Folder | What it holds |
|---|---|
| `src/datapilot/` | The package: `contracts/`, one folder per loop, `assignments/` (the live checks), `observability/`, and the `datapilot` command line (`cli.py`) |
| `console/` | The Streamlit console (`app.py`, `datapilot_console/`), its design notes (`DESIGN.md`), and its style tile (`design_app.py`) |
| `packs/` | The domain packs: `datapilot_us` (Harbor & Pine) and `_template`; `DATAPILOT_PACK` picks one |
| `demos/` | `registry.yaml`: every demo, its trigger, and its tier; the demo pages are generated from it |
| `planted/` | `registry.yaml`: the planted bugs and data traps; [planted items](../docs/planted-items.md) is generated from it |
| `ops/` | `docker/` (the image and the Postgres bootstrap), `sql/ops/` (the ops migrations), `sql/` (the warehouse schema and the agent role) |
| `config/` | `course.toml` (the naming rules), `release.toml` (what a public copy holds) |
| `scripts/` | The style, prose, naming, image, and repository checks, the gate (`verify.sh`), the local copy of the continuous integration run (`ci_local.py`), the release build (`build_release.py`), the commit-message hook (`hooks/`), the course kit's tools (`kit/`), and the tests' database setup |
| `tools/` | The diagram definitions and their export, and the page generators behind `make docs` |
| `tests/` | `unit/` (`make test`, no database, no model) and `integration/` (the tests' own Postgres) |

## Run one process outside Compose

Each service runs the same command on your machine, with the `localhost` addresses in `.env`. Stop
the service in Compose first, so two copies never serve at once:

```bash
docker compose stop worker
uv run datapilot worker
```

| Service | Command on your machine |
|---|---|
| `worker` | `uv run datapilot worker` |
| `scheduler` | `uv run datapilot scheduler` |
| `hill-climbing-runner` | `make hill-climbing-runner`; it refuses while another runner serves the database |
| `api` | `uv run uvicorn datapilot.loop3_events.api.app:app --port 8000` |
| `console` | `cd platform/console && uv run streamlit run app.py` |
| `migrate` | `make migrate` |

`docker compose start <service>` puts the service back.

## The other stacks

The tests use their own Postgres, the Compose project `datapilot-tests` on port 55432, started by
`make test-stack`; every run that uses it waits on the lock `/tmp/datapilot-tests-database.lock`.
Each live check of an assignment runs on its own Compose project, `datapilot-assignments` on ports
55433, 8100, and 8502. The [architecture page](../docs/architecture.md#other-stacks) lists every
stack and its ports.
