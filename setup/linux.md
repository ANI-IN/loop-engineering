# Module: Loop Engineering - Setup on Linux

> **Terms on this page**
>
> - **Console**: The Streamlit app that shows every loop live, on four pages.
> - **Live session**: Everything that runs between one `make preflight` and the next.
> - **Drift canary**: Three easy questions that must pass and two trap questions that must still fail.
> - **Trace**: The record of one run's steps, each model call and tool call, stored in LangSmith.

This page takes a Linux machine with `apt` (Ubuntu or Debian) to a first live run, watched on the
console. The course machine runs these commands in Ubuntu on WSL2, with Docker Engine and the
Compose plugin; on a native Ubuntu install the commands are the same. On another distribution,
use Docker's page for it ([Install Docker Engine](https://docs.docker.com/engine/install/)) and
your package manager for git and make; every step from the clone onwards is the same.

## Before you start

- Ubuntu or Debian with `sudo` rights.
- Free disk for the Postgres image, the DataPilot image, and the two seeded warehouses.
- Your OpenAI key from the operations team. LangSmith needs no card.

Every command below runs in a terminal. On Ubuntu, open one with Ctrl+Alt+T.

> Your output will differ: run times, ids, and the agent's wording change on every run.

## Steps

### Step 1: Get your OpenAI key from the operations team

**Why.** Every agent in DataPilot (the analyst, the schema scout, the reviewer, and the analyzer
team) calls gpt-6-luna (`OPENAI_MODEL` in `.env.example`). The operations team issues your key and
enables gpt-6-luna on it.

**Do this.** Ask the operations team for your key before class day. Keep it private until step 7.
Treat it like a password.

**You should see.** One key, sent to you privately.

**Check it worked.** The real test is `make preflight` in step 10. It asks OpenAI whether the key
works and whether it can use gpt-6-luna. It uses no tokens for that check.

**If it fails.** If the key ever lands in a chat, an issue, or a screenshot, tell the operations
team at once so they replace it.

### Step 2: Create the LangSmith account and a key (no card)

**Why.** Every run sends a trace to LangSmith, and every result on the console links to it. The
free Developer plan is enough: "Personal organizations are limited to 5,000 traces per month until
a credit card is added."
([LangSmith billing](https://docs.langchain.com/langsmith/billing), read 2026-10-23). Without a
card there is nothing to bill. Do not add a card.

**Do this.**

1. Open https://smith.langchain.com and sign up. Stay on the free Developer plan.
2. Open the Settings page and select the application programming interface (API) Keys section
   ([Create an account and API key](https://docs.langchain.com/langsmith/create-account-api-key)).
3. Create a Personal Access Token with an expiry after the course.
4. Copy the key right away: "LangSmith will display the API key only once."

**You should see.** The key once, in a dialog.

**Check it worked.** The key is listed under Settings, API Keys. Step 11 opens a trace with it.

**If it fails.** If the key was not copied, create a new one. If your account is in the EU
region, step 7 changes one more line in `.env`.

### Step 3: Install Docker Engine and the Compose plugin

**Why.** `make up` starts five containers with Docker Compose: Postgres, the api, the worker, the
scheduler, and the console (`compose.yaml`). Docker Engine and its Compose plugin are free.

**Do this.** These are Docker's commands for Ubuntu, "Install using the apt repository"
([Install Docker Engine on Ubuntu](https://docs.docker.com/engine/install/ubuntu/), read
2026-10-23). On Debian, use the same page for Debian, which differs only in the repository
address.

```bash
sudo apt update
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

sudo tee /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Then let your user run Docker without `sudo`
([Linux post-installation steps for Docker Engine](https://docs.docker.com/engine/install/linux-postinstall/)):

```bash
sudo groupadd docker
sudo usermod -aG docker $USER
```

`groupadd` may say the group already exists; that is fine. Log out and back in, so the group
change takes effect.

**You should see.** apt installs the packages with no error line.

**Check it worked.**

```bash
systemctl is-active docker
docker --version
docker compose version
```

The first line prints `active`, and the other two print a version each. Docker's own check is
`docker run hello-world`, which prints a message that the install works.

**If it fails.**

| Problem | Fix |
|---|---|
| `permission denied` on `/var/run/docker.sock` | Log out and back in after the `usermod` line |
| `systemctl is-active docker` prints `inactive` | `sudo systemctl start docker` |
| `docker: 'compose' is not a docker command` | Install `docker-compose-plugin` with the last apt line |
| apt reports conflicts with `docker.io` | Run Docker's "Uninstall old versions" command first |

### Step 4: Install git and make

**Why.** You clone the course repository with git. Every course command is a make target, such as
`make up` or `make demo NAME=agent-simple-question`.

**Do this.**

```bash
sudo apt install -y git make
```

**You should see.** The install ends without an error line.

**Check it worked.** `git --version` and `make --version` each print a version.

**If it fails.** If apt cannot find a package, run `sudo apt update` and try again.

### Step 5: Install uv

**Why.** uv installs the pinned Python and every package (`uv.lock`), and every make target runs
through `uv run`. `.python-version` pins Python 3.12, and uv downloads it on first use. The
DataPilot image uses uv 0.13.1 (`platform/ops/docker/Dockerfile`).

**Do this.** This installs that version
([Installing uv](https://docs.astral.sh/uv/getting-started/installation/)):

```bash
curl -LsSf https://astral.sh/uv/0.13.1/install.sh | sh
```

The installer puts `uv` in `~/.local/bin`. Open a new terminal afterwards, so that folder is on
your `PATH`.

**You should see.** The installer ends with a line that says where it put `uv`.

**Check it worked.** In the new terminal, `uv --version` prints `uv 0.13.1` and your platform.

**If it fails.** `uv: command not found` means the terminal started before the install: open a new
one. If it persists, check that `~/.local/bin/uv` exists.

### Step 6: Clone the repository and run make setup

**Why.** The repository holds DataPilot, the Harbor & Pine domain pack, the four sections, and
every make target.

**Do this.** Clone the course repository:

```bash
git clone https://github.com/ANI-IN/loop-engineering.git ~/datapilot
cd ~/datapilot
make setup
```

`make setup` installs the pinned packages with `uv sync --frozen` and copies `.env.example` to
`.env` if `.env` does not exist yet.

**You should see.** uv's install lines, then `+ created .env: add OPENAI_API_KEY and
LANGSMITH_API_KEY`.

**Check it worked.** `ls .env` lists the file.

**If it fails.**

| Problem | Fix |
|---|---|
| `make: uv: No such file or directory` | Open a new terminal (step 5) |
| uv reports the lock file is out of date | You edited `pyproject.toml`; restore it with `git checkout pyproject.toml` |

### Step 7: Put your keys in the .env file

**Why.** Your keys go into `.env` in the repository folder. It is git-ignored, and DataPilot never
prints, logs, or traces them. The Compose services read the same file.

**Do this.** Open the file with `nano .env`. Paste your two keys after the `=`. The values below
are placeholders.

```ini
OPENAI_API_KEY=your-key-from-the-operations-team
LANGSMITH_API_KEY=your-langsmith-key
```

Leave every other line as it is: `OPENAI_MODEL=gpt-6-luna` and `LANGSMITH_TRACING=true` are the
class values. Save with Ctrl+O and Enter, and leave with Ctrl+X. EU LangSmith accounts also set
`LANGSMITH_ENDPOINT=https://eu.api.smith.langchain.com` (no trailing slash).

**You should see.** The two lines filled, with no quotes and no spaces around the `=`.

**Check it worked.** `git check-ignore .env` prints `.env`, so git never commits it.

**If it fails.** Never commit `.env`, paste it anywhere, or share a screenshot of it. If you did,
delete the LangSmith key on its settings page and ask the operations team to replace the OpenAI
key.

### Step 8: Start the services

**Why.** `make up` builds the DataPilot image, then starts Postgres, applies the ops migrations,
and starts the api, the worker, the scheduler, and the console. It waits until every service with
a health check is healthy.

**Do this.**

```bash
make up
make ps
```

**You should see.** The image build, then the containers starting. `make ps` on the course
machine:

```text
NAME                    IMAGE                    COMMAND                  SERVICE     CREATED          STATUS                    PORTS
datapilot-api-1         datapilot:local          "uvicorn datapilot.l…"   api         32 minutes ago   Up 31 minutes (healthy)   0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp
datapilot-console-1     datapilot:local          "streamlit run app.p…"   console     32 minutes ago   Up 31 minutes             0.0.0.0:8501->8501/tcp, [::]:8501->8501/tcp
datapilot-postgres-1    postgres:18.6-bookworm   "docker-entrypoint.s…"   postgres    40 minutes ago   Up 40 minutes (healthy)   0.0.0.0:5432->5432/tcp, [::]:5432->5432/tcp
datapilot-scheduler-1   datapilot:local          "datapilot scheduler"    scheduler   32 minutes ago   Up 31 minutes
datapilot-worker-1      datapilot:local          "datapilot worker"       worker      32 minutes ago   Up 31 minutes
```

**Check it worked.** Five services show `Up`, and `api` and `postgres` show `(healthy)`.

**If it fails.**

| Problem | Fix |
|---|---|
| `Bind for 0.0.0.0:5432 failed: port is already allocated` | Another Postgres uses the port: set `POSTGRES_PORT` in `.env` |
| `Cannot connect to the Docker daemon` | `sudo systemctl start docker` |
| A service keeps restarting | `make logs NAME=<service>` shows why; the [troubleshooting page](../docs/troubleshooting.md) lists the common lines |

### Step 9: Load the warehouse

**Why.** `make seed` generates the Harbor & Pine data and loads it into two databases: `warehouse`
and the differently seeded `warehouse_alt` that the evaluator compares against. Seeding is
deterministic, so `make check-data` can compare row counts and a content hash with
`platform/packs/datapilot_us/data_generator/expected.yaml`. Neither makes a model call.

**Do this.**

```bash
make seed
make check-data
```

**You should see.** One line per warehouse with its row counts and content hash, then the check.
The last line of `make check-data` on the course machine:

```text
check-data: both warehouses match expected.yaml
```

**Check it worked.** That exact line, with no `x` line before it.

**If it fails.** An `x` line names the table whose count or hash differs. Run `make seed` again; it
rebuilds both warehouses from the same seed.

### Step 10: Run make preflight

**Why.** One command checks everything so far and starts your live session: the services, the
seeded warehouse, your OpenAI key, the starting knowledge, and the drift canary. gpt-6-luna has no
dated snapshot, so the canary checks that the model still behaves as the course measured it. Runs
belong to the open live session, so a demo needs a preflight first.

**Do this.**

```bash
make preflight PURPOSE=development
```

The canary makes five live model calls with your key. `PURPOSE=development` names a session on
your own machine; on class day you run `make preflight PURPOSE=class`.

**You should see.** One line per check starting with `ok`, one `canary` line per question ending
in `as expected` with its trace link, and a last line that starts with `Live session started at`.
Your key is never printed.

**Check it worked.** The last line starts `Live session started at` and names the model id
`gpt-6-luna`.

**If it fails.**

| Line | Fix |
|---|---|
| `A service is not ready: run make up, then preflight again.` | Step 8, then `make preflight PURPOSE=development` again |
| `Your OpenAI key was not accepted. Check it with the operations team.` | Copy the key into `.env` again; if it still fails, ask the operations team |
| `... The model gpt-6-luna is not available to it.` | Ask the operations team to enable gpt-6-luna on your key |
| `The drift canary failed: ...` | Bring the exact line to the instructor; do not change any setting |

### Step 11: Run the first live demo

**Why.** This is the end-to-end check: a real question from the analyst, answered against the
warehouse with your key, shown live on the console and traced in LangSmith. It is the first demo
of Section 1: Agent loop, the simple question.

**Do this.** Open http://localhost:8501 in your browser. Then, in the terminal:

```bash
make demo NAME=agent-simple-question
```

**You should see.** The terminal prints the demo name with the run it started. On the console's
Agent page the run appears with its tool calls, its Structured Query Language (SQL), its answer,
and a live stamp: the start time in your local time and a trace link.
<!-- screenshot: the console Agent page after the simple question, with the live stamp -->

**Check it worked.** The trace link on the console opens the run in LangSmith, in the project
`datapilot-live` (`LANGSMITH_PROJECT` in `.env.example`).

**If it fails.**

| Problem | Fix |
|---|---|
| `No live session is open: run make preflight first.` | Step 10 |
| The console does not open in your browser | Check `make ps`; try http://127.0.0.1:8501 |
| The run stays in one lane | `make reset NAME=agent-loop`, then the same `make demo` again |

## Common errors

| Symptom | Fix |
|---|---|
| `make: command not found` | Step 4 |
| `uv: command not found` | Open a new terminal (step 5) |
| `permission denied` on the Docker socket | Log out and back in after step 3 |
| The console is blank after a restart | Run `make up`, then `make preflight PURPOSE=development` |
| A demo ran but the console shows no trace link | Check `LANGSMITH_API_KEY` and `LANGSMITH_TRACING=true` in `.env`, then `make up` |

Every other message, with its cause and fix: [troubleshooting](../docs/troubleshooting.md).

## You're ready

You are ready when:

- `make ps` shows five services up, with `api` and `postgres` healthy;
- `make check-data` ends with `check-data: both warehouses match expected.yaml`;
- `make preflight PURPOSE=development` ends with `Live session started at`;
- `make demo NAME=agent-simple-question` shows a run with a live stamp on the console.

Next: the [pre-class checklist](pre-class.md), then
[Section 1: Agent loop](../section-1-agent-loop/README.md).

## Sources

- Source 1: Install Docker Engine, <https://docs.docker.com/engine/install/>, Docker, n.d.
- Source 2: LangSmith billing, <https://docs.langchain.com/langsmith/billing>, LangChain, n.d.
- Source 3: Create an account and API key,
  <https://docs.langchain.com/langsmith/create-account-api-key>, LangChain, n.d.
- Source 4: Install Docker Engine on Ubuntu, <https://docs.docker.com/engine/install/ubuntu/>,
  Docker, n.d.
- Source 5: Linux post-installation steps for Docker Engine,
  <https://docs.docker.com/engine/install/linux-postinstall/>, Docker, n.d.
- Source 6: Installing uv, <https://docs.astral.sh/uv/getting-started/installation/>, Astral, n.d.
