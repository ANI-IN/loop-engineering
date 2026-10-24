# Frequently asked questions

> **Terms on this page**
>
> - **Drift canary**: Three easy questions that must pass and two trap questions that must still fail.
> - **Live session**: Everything that runs between one `make preflight` and the next.
> - **Holdout split**: The benchmark questions the analyzer team never sees; the gate decides on them.
> - **Trap**: A business rule the schema does not reveal, so a plausible query gets it wrong.

Questions learners ask, answered from what is in this repository. Questions from the Thursday
review that did not fit their slot are answered here after the session.

## Money and keys

### Which keys do I need?

Two. Your OpenAI key comes from the operations team, who enable gpt-6-luna on it. Your LangSmith
key comes from your own free Developer account, with no card. Both go into `.env`; the
[setup pages](../setup/README.md) show where.

### What does the course cost me?

Model calls are billed to the project of the key the operations team gives you, and they set its
spending limit; the costs page recommends one, with an alert
([the learner key limit](costs.md#the-learner-key-limit)). Each assignment check also stops at its
own spend cap of 1.00 dollar. LangSmith is free on the Developer plan without a card. The
[costs page](costs.md) lists what each command calls and the caps that bound it.

### Which model does the course use, and why only one?

gpt-6-luna for every agent: the analyst, the schema scout, the reviewer, and the analyzer team
(`.env.example`). One model keeps every result comparable. It has no dated snapshot, so
`make preflight` runs the drift canary before every session to check it still behaves as the
course measured it.

### What happens when a run reaches a cap?

It stops, and the console and the terminal say which cap. The caps are code, not prompt lines:
the row cap, the retry cap, the model and tool call limits, and the token budgets, all in
`platform/packs/datapilot_us/pack.yaml`. The [reference](reference.md#caps-and-limits) lists
each one.

## Setup

### Can I use Windows?

Yes, through WSL2 with Docker Engine inside Ubuntu: [setup on Windows](../setup/windows.md). It is
the setup of the course machine. Native PowerShell and cmd are not supported.

### Does it work on macOS?

The steps follow the official pages, with Docker Desktop or Colima:
[setup on macOS](../setup/macos.md). No command was run on a Mac for the course; the steps from the
clone onwards are the same as on Linux.

### Why do I need Docker?

`make up` runs six services with Docker Compose: Postgres, the api, the worker, the scheduler, the
hill-climbing runner, and the console (`compose.yaml`). The event loop needs real processes and a real database: a job
survives a worker restart only because it lives in Postgres.

## Running the demos

### What do I do if a demo fails?

Reset its section and run it again: `make reset NAME=<section slug>`, then the same console button
or `make demo NAME=<slug>`. Every demo is live, so there is no recording to fall back to. The
[troubleshooting page](troubleshooting.md#running-a-demo) lists the common lines.

### Why does my run look different from the pages?

The model reasons afresh on every run, so the wording, the number of tool calls, the tokens, and
the timings change. Each demo page says what may vary and what never does. The `demo/expected/`
folders hold one real captured run for you to compare with after class.

### Why does the agent still get the spine question wrong after the graders?

Because the graders check that a query is safe and well formed, not that it means what the
business means. The fiscal year rule is not in the schema, so no grader can supply it.
[Section 4: Hill-climbing loop](../section-4-hill-climbing-loop/README.md) learns it from failures,
and the promotion gate decides on holdout questions.

## Results

### Is a passing benchmark proof that the answers are right?

No. It is evidence on the questions in it. The gate compares the active and the candidate
knowledge version item by item on the holdout split, which the analyzer team never sees, with
each holdout item run 3 times and passing on 2 (`evaluation` in `pack.yaml`). A small holdout
can still miss a failure on a question it does not ask.

### Why did a trap question pass under the starting knowledge?

The model sometimes guesses a rule from the data it sees. The drift canary checks two trap
questions before every session for exactly this reason. In calibration no trap passed unaided:
0 of 99 trap runs under the starting knowledge, in the
[calibration report](calibration-report.md).

## Assignments and help

### How is an assignment checked?

You run its live check while you work: `make check-assignment NAME=<slug>`. It brings up the real
stack, prints a cost estimate, runs the done-when scenario with your key, and prints `PASS` or
`FAIL` per requirement, with a trace link for each live step. There is no hidden grader and no
submission.

### Where are the solutions?

Each assignment's `solution/` folder is published at the start of the Thursday review: the
reference solution, two alternatives, and the captured live runs.
[The review session](review-session.md) walks through them.

### Where do I get help?

During class, ask in the chat. A question that does not fit goes to the parking lot and is
answered in the Thursday review, then added here. A key problem goes to the operations team.
