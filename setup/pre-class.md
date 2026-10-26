# Module: Loop Engineering - Before class

> **Terms on this page**
>
> - **Console**: The Streamlit app that shows every loop live, on four pages.
> - **Live session**: Everything that runs between one `make preflight` and the next.
> - **Drift canary**: Three easy questions that must pass and two trap questions that must still fail.
>
> All terms: [glossary](../docs/glossary.md).

Finish this checklist before class day, then once more on the morning of the class. Each item
names the command to run and what it must print. If an item fails, the
[troubleshooting page](../docs/troubleshooting.md) has the exact line and its fix.

## Before class day

1. **Finish the setup page for your system.** [Setup](README.md) ends with the first live demo on
   your machine.
2. **Your OpenAI key from the operations team.** It goes into `OPENAI_API_KEY` in `.env`. The
   operations team must enable gpt-6-luna on it, the model of every agent (`OPENAI_MODEL` in
   `.env.example`). If `make preflight` says `The model gpt-6-luna is not available to it.`, ask
   them to enable it. Never commit `.env`: `git check-ignore .env` prints `.env`.
3. **LangSmith on your own free account.** Put your key in `LANGSMITH_API_KEY` and keep
   `LANGSMITH_TRACING=true`. Stay on the free Developer plan and add no card. Every run on the
   console links to its trace in your account, in the project `datapilot-live`.
4. **The services.** `make up`, then `make ps`: six services up, with `api` and `postgres`
   healthy.
5. **The warehouse.** `make check-data` prints `check-data: both warehouses match
   expected.yaml`. If it does not, run `make seed` and check again.
6. **Preflight.** `make preflight PURPOSE=development` checks the services, the warehouse, your
   key, and the drift canary, then starts a live session. Its last line starts `Live session
   started at`. If it prints `Your OpenAI key was not accepted. Check it with the operations
   team.`, the key is missing or rejected: contact the operations team. Preflight never prints
   the key itself.

## On class day

1. **Start the services** with `make up`, then confirm with `make ps`.
2. **Run preflight for the class**: `make preflight PURPOSE=class`. Its canary asks five questions,
   each one agent run with your key, and the class session starts when every check passes.
3. **Open the console** at http://localhost:8501 and press F11 for full screen. The run board is
   laid out for a page of 1280 by 720 pixels (`platform/console/DESIGN.md`), and browser toolbars
   take space it needs. Press F11 again to leave full screen.
4. **Keep a terminal open** in the repository folder, beside the browser. Each demo has a make
   target, `make demo NAME=<slug>`, that does what the console button does.
5. **Bring the exact message** of anything that still fails to the start of class.
