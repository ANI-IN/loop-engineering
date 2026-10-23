# Module: Loop Engineering - Setup

> **Terms on this page**
>
> - **Console**: The Streamlit app that shows every loop live, on four pages.
> - **Live session**: Everything that runs between one `make preflight` and the next.
> - **Drift canary**: Three easy questions that must pass and two trap questions that must still fail.
> - **Trace**: The record of one run's steps, each model call and tool call, stored in LangSmith.

These pages take a machine with nothing installed to a first live run of DataPilot. At the end,
the analyst answers a real question against the Harbor & Pine warehouse, you watch it on the
console, and the run's trace opens in LangSmith. They assume no tool is installed. Your OpenAI
key comes from the operations team; your LangSmith account is your own.

## What you will install

| Item | Why you need it | Version or plan |
|---|---|---|
| OpenAI key from the operations team | The analyst, the schema scout, the reviewer, and the analyzer team | gpt-6-luna enabled on it (`.env.example`) |
| LangSmith account | A trace of every run | Free Developer plan, no card |
| WSL2 and Ubuntu (Windows only) | A Linux shell for every course command | Current Ubuntu from `wsl --install` |
| Docker Engine and the Compose plugin | Postgres, the api, the worker, the scheduler, and the console | Postgres `18.6-bookworm` (`compose.yaml`) |
| git, uv, make | Clone the repository, install Python and the packages, run the targets | uv 0.13.1 (`platform/ops/docker/Dockerfile`), Python 3.12 (`.python-version`) |

uv installs the pinned Python and every pinned package from `uv.lock`, so you never install
Python yourself. Docker builds one image for the four DataPilot services and pulls the Postgres
image the first time you run `make up`.

Model calls cost money on the key from the operations team; the [costs page](../docs/costs.md)
lists what each command calls. `make setup`, `make up`, `make seed`, and `make check-data` make no
model calls.

How long it takes: the first install has not been timed on a clean machine yet.
<!-- provisional: the first-install time is measured during the rehearsal on a clean machine -->
Account sign-up, downloads, and the WSL restart depend on you and your network.

## Pick your system

| Your machine | Page | Tested for the course |
|---|---|---|
| Windows 10 (version 2004 or later) or Windows 11 | [windows.md](windows.md) | Yes: WSL2, Ubuntu, Docker Engine inside Ubuntu |
| Linux with `apt` (Ubuntu, Debian) | [linux.md](linux.md) | In Ubuntu on WSL2; the commands are the same |
| macOS | [macos.md](macos.md) | No: the steps follow the official pages |

Every page has the same steps in the same order: the two keys, the tools, the clone, `.env`, the
services, the warehouse, `make preflight`, and the first live demo. Each step says why, what to
do, what you should see, how to check it worked, and what to do if it fails.

Native Windows shells (PowerShell, cmd) are not supported. On Windows, every command after the
WSL install runs in the Ubuntu terminal.

Before class day, also work through [pre-class.md](pre-class.md): the short checklist of what
must work before the class starts.

## Get help

- [Troubleshooting](../docs/troubleshooting.md): the exact messages and their fixes, grouped by
  command.
- [Frequently asked questions](../docs/faq.md): keys, setup, demos, and assignments.
- [Reference](../docs/reference.md): every make target, setting, and cap.
- A key problem goes to the operations team. Anything else: bring the exact message to the start
  of class. Never share your `.env` or a key.
