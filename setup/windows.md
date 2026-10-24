# Module: Loop Engineering - Setup on Windows

> **Terms on this page**
>
> - **Console**: The Streamlit app that shows every loop live, on four pages.
> - **Live session**: Everything that runs between one `make preflight` and the next.
> - **Drift canary**: Three easy questions that must pass and two trap questions that must still fail.
> - **Trace**: The record of one run's steps, each model call and tool call, stored in LangSmith.
> - **WSL2**: Windows Subsystem for Linux, which runs a real Ubuntu next to Windows.

This page takes a Windows PC with nothing installed to a first live run, watched on the console.
Everything runs inside WSL2, with Docker Engine installed inside Ubuntu. This page does not use
Docker Desktop. It is the setup of the course machine: Windows 11, WSL2, Ubuntu, and Docker
Engine with the Compose plugin inside Ubuntu.

Two rules matter more than any other on this page:

- After step 3, every command runs in the Ubuntu terminal, not in PowerShell or cmd. The few
  exceptions say PowerShell.
- The repository lives in the Linux file system, under your Linux home folder, never under
  `/mnt/c/`.

## Before you start

- Windows 11, or Windows 10 version 2004 (build 19041) or later
  ([Install WSL](https://learn.microsoft.com/en-us/windows/wsl/install)).
- Administrator rights on the PC, for step 3 only.
- Free disk for the Postgres image, the DataPilot image, and the two seeded warehouses.
- Your OpenAI key from the operations team. LangSmith needs no card.

> Your output will differ: run times, ids, and the agent's wording change on every run.

## Steps

### Step 1: Get your OpenAI key from the operations team

**Why.** Every agent in DataPilot (the analyst, the schema scout, the reviewer, and the analyzer
team) calls gpt-6-luna (`OPENAI_MODEL` in `.env.example`). The operations team issues your key and
enables gpt-6-luna on it.

**Do this.** Ask the operations team for your key before class day. Keep it private until step 8.
Treat it like a password.

**You should see.** One key, sent to you privately.

**Check it worked.** The real test is `make preflight` in step 11. It asks OpenAI whether the key
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

**Check it worked.** The key is listed under Settings, API Keys. Step 12 opens a trace with it.

**If it fails.** If the key was not copied, create a new one. If your account is in the EU
region, step 8 changes one more line in `.env`.

### Step 3: Install WSL2 and Ubuntu

**Why.** The course commands, the Makefile, and Docker Engine need a Linux shell. WSL2 runs a real
Ubuntu next to Windows. Native Windows shells (PowerShell, cmd) are not supported.

**Do this.** Right-click PowerShell, choose Run as administrator, and run:

```powershell
wsl --install
```

Microsoft: "This command will enable the features necessary to run WSL and install the Ubuntu
distribution of Linux." (Source 1, read 2026-10-23). Restart the PC when asked. Then open Ubuntu
from the Start menu. The first start asks you to create a Linux user name and password. Remember
the password: `sudo` asks for it.

From now on, run every command in the Ubuntu terminal, unless a step says PowerShell. PowerShell
shows `PS C:\...>`; Ubuntu shows `you@PC:~$`.

Docker Engine needs systemd inside Ubuntu. Check it in the Ubuntu terminal:

```bash
cat /etc/wsl.conf
```

**You should see.** An Ubuntu terminal with a prompt like `you@PC:~$`, and `/etc/wsl.conf` with
these two lines (the file may hold more):

```text
[boot]
systemd=true
```

If the lines are missing, add them with `sudo nano /etc/wsl.conf`, run `wsl.exe --shutdown` in
PowerShell, and open Ubuntu again
([Use systemd with WSL](https://learn.microsoft.com/en-us/windows/wsl/systemd)).

**Check it worked.** In PowerShell, `wsl.exe -l -v` lists Ubuntu, and its `VERSION` column says
`2`.

**If it fails.**

| Problem | Fix |
|---|---|
| `wsl --install` prints the WSL help text | WSL is already there: `wsl --install -d Ubuntu` |
| The install hangs at 0.0% | `wsl --install --web-download -d Ubuntu` |
| `0x80370102 ... a required feature is not installed` | Turn on virtualization: [WSL troubleshooting](https://learn.microsoft.com/en-us/windows/wsl/troubleshooting) |
| `VERSION` shows `1` | `wsl --set-version Ubuntu 2` |
| `System has not been booted with systemd` | Add the two lines to `/etc/wsl.conf` as above |

### Step 4: Install Docker Engine inside Ubuntu

**Why.** `make up` starts five containers with Docker Compose: Postgres, the api, the worker, the
scheduler, and the console (`compose.yaml`). The course machine runs Docker Engine inside Ubuntu,
not Docker Desktop. If Docker Desktop is installed with WSL integration on, turn that integration
off for Ubuntu, so only one engine answers the `docker` command.

**Do this.** These are Docker's commands for Ubuntu, "Install using the apt repository"
([Install Docker Engine on Ubuntu](https://docs.docker.com/engine/install/ubuntu/), read
2026-10-23):

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

`groupadd` may say the group already exists; that is fine. The group change takes effect at the
next login: close every Ubuntu window, run `wsl.exe --shutdown` in PowerShell, and open Ubuntu
again.

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
| `permission denied` on `/var/run/docker.sock` | `wsl.exe --shutdown` in PowerShell, reopen Ubuntu |
| `systemctl is-active docker` prints `inactive` | `sudo systemctl start docker` |
| `docker: 'compose' is not a docker command` | Install `docker-compose-plugin` with the last apt line |
| apt reports conflicts with `docker.io` | Run Docker's "Uninstall old versions" command first |

### Step 5: Install git and make

**Why.** You clone the course repository with git. Every course command is a make target, such as
`make up` or `make demo NAME=agent-simple-question`.

**Do this.**

```bash
sudo apt install -y git make
```

**You should see.** The install ends without an error line.

**Check it worked.** `git --version` and `make --version` each print a version.

**If it fails.** If apt cannot find a package, run `sudo apt update` and try again.

### Step 6: Install uv

**Why.** uv installs the pinned Python and every package (`uv.lock`), and every make target runs
through `uv run`. `.python-version` pins Python 3.12, and uv downloads it on first use. The
DataPilot image uses uv 0.13.1 (`platform/ops/docker/Dockerfile`).

**Do this.** This installs that version
([Installing uv](https://docs.astral.sh/uv/getting-started/installation/)):

```bash
curl -LsSf https://astral.sh/uv/0.13.1/install.sh | sh
```

The installer puts `uv` in `~/.local/bin`. Open a new Ubuntu terminal afterwards, so that folder
is on your `PATH`.

**You should see.** The installer ends with a line that says where it put `uv`.

**Check it worked.** In the new terminal, `uv --version` prints `uv 0.13.1` and your platform.

**If it fails.** `uv: command not found` means the terminal started before the install: open a new
one. If it persists, check that `~/.local/bin/uv` exists.

### Step 7: Clone the repository and run make setup

**Why.** The repository holds DataPilot, the Harbor & Pine domain pack, the four sections, and
every make target. Keep it in the Linux file system: "For the fastest performance speed, store
your files in the WSL file system if you are working in a Linux command line"
([Working across file systems](https://learn.microsoft.com/en-us/windows/wsl/filesystems)).

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

**Check it worked.** `pwd` prints a path under `/home/`, and `ls .env` lists the file.

**If it fails.**

| Problem | Fix |
|---|---|
| `pwd` starts with `/mnt/c` | You cloned onto the Windows drive: `cd ~` and clone again |
| `make: uv: No such file or directory` | Open a new Ubuntu terminal (step 6) |
| uv reports the lock file is out of date | You edited `pyproject.toml`; restore it with `git checkout pyproject.toml` |

### Step 8: Put your keys in the .env file

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

### Step 9: Start the services

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

This capture was taken before the hill-climbing runner became a service, and before every port was
bound to this machine only. Your `make ps` also lists `datapilot-hill-climbing-runner-1`, running
`datapilot hill-climbing-runner`, with status `Up`, and its ports read `127.0.0.1:8000->8000/tcp`,
`127.0.0.1:8501->8501/tcp`, and `127.0.0.1:5432->5432/tcp`, with no `0.0.0.0` or `[::]` entries.

**Check it worked.** Six services show `Up` (postgres, api, worker, scheduler,
hill-climbing-runner, and console), and `api` and `postgres` show `(healthy)`.

**If it fails.**

| Problem | Fix |
|---|---|
| `Bind for 0.0.0.0:5432 failed: port is already allocated` | Another Postgres uses the port: set `POSTGRES_PORT` in `.env` |
| `Cannot connect to the Docker daemon` | `sudo systemctl start docker` |
| A service keeps restarting | `make logs NAME=<service>` shows why; the [troubleshooting page](../docs/troubleshooting.md) lists the common lines |

### Step 10: Load the warehouse

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

### Step 11: Run make preflight

**Why.** One command checks everything so far and starts your live session: the services, the
seeded warehouse, your OpenAI key, the starting knowledge, and the drift canary. gpt-6-luna has no
dated snapshot, so the canary checks that the model still behaves as the course measured it. Runs
belong to the open live session, so a demo needs a preflight first.

**Do this.**

```bash
make preflight PURPOSE=development
```

The canary asks five questions with your key, each one agent run (about 40 model calls, under a
cent). `PURPOSE=development` names a session on
your own machine; on class day you run `make preflight PURPOSE=class`.

**You should see.** One line per check starting with `ok`, one `canary` line per question ending
in `as expected` with its trace link, and a last line that starts with `Live session started at`.
Your key is never printed.

**Check it worked.** The last line starts `Live session started at` and names the model id
`gpt-6-luna`.

**If it fails.**

| Line | Fix |
|---|---|
| `A service is not ready: run make up, then preflight again.` | Step 9, then `make preflight PURPOSE=development` again |
| `Your OpenAI key was not accepted. Check it with the operations team.` | Copy the key into `.env` again; if it still fails, ask the operations team |
| `... The model gpt-6-luna is not available to it.` | Ask the operations team to enable gpt-6-luna on your key |
| `The drift canary failed: ...` | Bring the exact line to the instructor; do not change any setting |

### Step 12: Run the first live demo

**Why.** This is the end-to-end check: a real question from the analyst, answered against the
warehouse with your key, shown live on the console and traced in LangSmith. It is the first demo
of Section 1: Agent loop, the simple question.

**Do this.** Open http://localhost:8501 in your Windows browser. In WSL's default networking mode,
a server in Ubuntu is reachable from Windows at `localhost`
([WSL networking](https://learn.microsoft.com/en-us/windows/wsl/networking)). Then, in the
Ubuntu terminal:

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
| `No live session is open: run make preflight first.` | Step 11 |
| The console does not open in the Windows browser | Check `make ps`; try http://127.0.0.1:8501 |
| The run stays in one lane | `make reset NAME=agent-loop`, then the same `make demo` again |

## Common errors

| Symptom | Fix |
|---|---|
| `make: command not found` | You are in PowerShell: open Ubuntu. Otherwise step 5 |
| `uv: command not found` | Open a new Ubuntu terminal (step 6) |
| `permission denied` on the Docker socket | `wsl.exe --shutdown` in PowerShell after step 4 |
| The console is blank after a restart of Windows | Open Ubuntu, run `make up`, then `make preflight PURPOSE=development` |
| A demo ran but the console shows no trace link | Check `LANGSMITH_API_KEY` and `LANGSMITH_TRACING=true` in `.env`, then `make up` |

Every other message, with its cause and fix: [troubleshooting](../docs/troubleshooting.md).

## You're ready

You are ready when:

- `make ps` shows six services up, with `api` and `postgres` healthy;
- `make check-data` ends with `check-data: both warehouses match expected.yaml`;
- `make preflight PURPOSE=development` ends with `Live session started at`;
- `make demo NAME=agent-simple-question` shows a run with a live stamp on the console.

Next: the [pre-class checklist](pre-class.md), then
[Section 1: Agent loop](../section-1-agent-loop/README.md).

## Sources

- Source 1: Install WSL, <https://learn.microsoft.com/en-us/windows/wsl/install>, Microsoft, n.d.
- Source 2: LangSmith billing, <https://docs.langchain.com/langsmith/billing>, LangChain, n.d.
- Source 3: Create an account and API key,
  <https://docs.langchain.com/langsmith/create-account-api-key>, LangChain, n.d.
- Source 4: Use systemd to manage Linux services with WSL,
  <https://learn.microsoft.com/en-us/windows/wsl/systemd>, Microsoft, n.d.
- Source 5: Troubleshooting Windows Subsystem for Linux,
  <https://learn.microsoft.com/en-us/windows/wsl/troubleshooting>, Microsoft, n.d.
- Source 6: Install Docker Engine on Ubuntu, <https://docs.docker.com/engine/install/ubuntu/>,
  Docker, n.d.
- Source 7: Linux post-installation steps for Docker Engine,
  <https://docs.docker.com/engine/install/linux-postinstall/>, Docker, n.d.
- Source 8: Installing uv, <https://docs.astral.sh/uv/getting-started/installation/>, Astral, n.d.
- Source 9: Working across Windows and Linux file systems,
  <https://learn.microsoft.com/en-us/windows/wsl/filesystems>, Microsoft, n.d.
- Source 10: Accessing network applications with WSL,
  <https://learn.microsoft.com/en-us/windows/wsl/networking>, Microsoft, n.d.
