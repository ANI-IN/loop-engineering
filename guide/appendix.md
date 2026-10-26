# Appendix: Cheat sheet, troubleshooting, glossary and recovery

## Command cheat sheet

Every command in the guide, in class order. Run them from the repository folder.

| Moment | Terminal | Command | What you should see |
|---|---|---|---|
| Part 0 | Stack | `make up`, then `make ps` | Every service up; `api` and `postgres` healthy |
| Part 0 | Stack | `make check-data` | `check-data: both warehouses match expected.yaml` |
| Part 0 | Demo | `make reset NAME=agent-loop`, and the other three sections | Each reset ends without an error line |
| Part 0 | Demo | `make preflight PURPOSE=class` (on your own copy, `PURPOSE=development`) | A last line that starts `Live session started at` |
| Chapter 1 | Demo | `make demo NAME=agent-simple-question` | A posted count on the Agent page |
| Chapter 1 | Demo | `make demo NAME=agent-confident-wrong-answer` | A mismatch against gold, with trap notes |
| Chapter 1 | Demo | `make demo NAME=agent-unbounded-rows PLANTED=1`, then without `PLANTED=1` | Tokens jump with the bug on; a truncation notice with it off |
| Chapter 2 | Demo | `make demo NAME=verify-malicious-sql`, then with `PLANTED=1` | The layer that stopped each statement |
| Chapter 2 | Demo | `make demo NAME=verify-retry-cap` | Escalated after 3 attempts |
| Chapter 2 | Demo | `make demo NAME=verify-graders-pass-still-wrong` | A green checklist beside a failed gold check |
| Chapter 3 | Demo | `make demo NAME=events-webhook-question` | One post at the report-only level, unverified |
| Chapter 3 | Demo | `make demo NAME=events-approval-survives-restart` | Holding for approval across a worker restart |
| Chapter 3 | Demo | `make demo NAME=events-duplicate-events PLANTED=1`, `make reset NAME=event-loop`, then without `PLANTED=1` | Bug on: three question runs, two digests. Off: one of each, duplicates absorbed |
| Chapter 3 | Demo | `make demo NAME=events-kill-switch-in-flight PLANTED=1`, `make reset NAME=event-loop`, then without `PLANTED=1` | The run posted with the bug on; the run under Blocked by kill switch without |
| Chapter 4 | Demo | `make demo NAME=improve-baseline-experiment` | The holdout ledger under version 1 of the knowledge (the starting version) |
| Chapter 4 | Demo | `make demo NAME=improve-naive-analyzer-blocked PLANTED=1` | The gate blocks the version |
| Chapter 4 | Demo | `make demo NAME=improve-analyzer-team-approve` | The knowledge diff of the candidate |
| Chapter 4 | Demo | `make demo NAME=improve-candidate-experiment` | Fixed items and regressions against the baseline |
| Chapter 4 | Demo | `make demo NAME=improve-cleared-unattended` | The fiscal year 2025 revenue question answered under the new version |
| Any time | Demo | `make reset NAME=<section slug>` | The section back at its starting state |

A planted half is `make demo NAME=<demo> PLANTED=1`: the demo's planted bugs are on for its own
runs and requests only. `.env` keeps every planted flag (`BUG_UNBOUNDED_ROWS`, `BUG_NAIVE_GUARD`,
`BUG_NO_RETRY_CAP`, `BUG_MEMORY_CHECKPOINTER`, `BUG_NO_IDEMPOTENCY`, `BUG_RANDOM_DIGEST_ID`,
`BUG_KILLSWITCH_AT_CLAIM_ONLY`, `BUG_NAIVE_ANALYZER`) and `DEMO_PACING` at `0` all day, so no
`make up` falls between the halves; the finale and every live check refuse to start while one is
on. The kill switch demo switches demo pacing on for its own run. The approval demo's planted half
restarts the worker twice and holds the terminal until its run ends; Ctrl+C ends the wait sooner.

## Troubleshooting

| What you see | Cause | Fix |
|---|---|---|
| `No live session is open: run make preflight PURPOSE=class\|rehearsal\|thursday-review\|development first` | No live session yet | `make preflight PURPOSE=class`, once (on your own copy, `PURPOSE=development`) |
| `Your OpenAI key was not accepted. Check it with the operations team.` | The key is missing or rejected | Ask the operations team |
| `The drift canary failed: ...` | The model no longer behaves as measured | Do not teach the measured results; re-run calibration |
| `Cannot connect to the Docker daemon` | Docker is not running | Start Docker, then `make up` |
| The console is blank | The console service is down | `make ps`, then `make up` |
| A run stays in one lane | The worker stalled or a run hung | `make reset NAME=<section slug>`, then the same demo |
| A planted half looks like the fixed system | It was sent without `PLANTED=1` | `make demo NAME=<demo> PLANTED=1` |
| Restart worker does nothing | Demo controls are off | `DATAPILOT_ALLOW_DEMO_CONTROLS=1` in `.env`, then `make up` |
| The kill switch run finishes first | It was sent from the console, which sends no pacing | `make demo NAME=events-kill-switch-in-flight` |
| "No baseline run in this session yet." | The baseline experiment never started | Start it now, as the page offers |
| The Improve page does not move | The hill-climbing runner service is down | `make ps`, then `make up` |
| The trace list in LangSmith is still empty | Traces arrive later than the ledger | Read the console's holdout ledger; open the traces later |

Every other message, with its cause and fix: [troubleshooting](../docs/troubleshooting.md).

## Glossary

The terms the guide uses, in the wording of the course glossary. Every query is Structured Query
Language (SQL).

- **Agent loop**: The model calls tools, reads the results, and repeats until it answers.
- **Analyzer team**: The failure analyst, the rule writer, and the critic, which turn failed development
  questions into a candidate knowledge version.
- **Autonomy level**: How much DataPilot may do unattended: report-only, assisted, or unattended.
- **Baseline experiment**: The benchmark run under the active knowledge version, started in the open
  live session.
- **Business date**: The day DataPilot treats as today, 31 January 2026 (`DATAPILOT_BUSINESS_DATE`).
- **Console**: The Streamlit app that shows every loop live, on four pages.
- **Development split**: The benchmark questions the analyzer team may learn from.
- **Drift canary**: Three easy questions that must pass and two trap questions that must still fail.
- **Escalated**: A run that ended without an answer because it hit a cap or a refused write.
- **Event loop**: Events become jobs that workers run, with approvals, budgets, and a kill switch.
- **Fiscal year 2025 revenue question**: "What was our net revenue in fiscal year 2025?", the
  question every section asks.
- **Gold SQL**: The query an analyst wrote by hand that gives the right answer.
- **Hill-climbing loop**: Experiments find failures, an analyzer team proposes rules, and a gate
  decides.
- **Holdout split**: The benchmark questions the analyzer team never sees; the gate decides on them.
- **Human approval**: A person approves or rejects a held action before it runs.
- **Idempotency**: Running the same event twice has the effect of running it once.
- **Kill switch**: The guarded control that stops every worker and forces the report-only level.
- **Knowledge version**: A numbered set of business rules given to the agent in its prompt.
- **Live session**: Everything that runs between one `make preflight` and the next.
- **Live stamp**: A result's run start time in your local time and its LangSmith trace link.
- **Overfit guard**: The code check that rejects a rule copying a benchmark question or a gold
  query.
- **Planted bug**: A defect switched on by a flag so a demo shows its failure every time.
- **Promotion gate**: The check that a new knowledge version must pass before it becomes active.
- **Regression**: An item that passed under the active version and fails under the candidate, confirmed by re-runs.
- **Reviewer**: An independent agent that reads the question, SQL, and result after the graders
  pass.
- **Trap**: A business rule the schema does not reveal, so a plausible query gets it wrong.
- **Verification loop**: Graders check each query and answer, and send failures back to the agent.

All terms: [glossary](../docs/glossary.md).

## Recovery: reset and re-run

When a live demo stalls or shows the wrong moment in class, say so out loud, reset its section,
and run the same demo again. Every demo is live: there is no replay and no recording.

### Step 1: Reset the section and run the demo again

**Where:** The demo terminal, in the repository folder.

**Type:** the section slug and the demo on screen; for example, for Section 1: Agent loop:

```bash
make ps
make reset NAME=agent-loop
make demo NAME=agent-confident-wrong-answer
```

The section slugs are `agent-loop`, `verification-loop`, `event-loop`, and `hill-climbing-loop`.

**You should see:** every service up, the reset's confirmation, and a new run with a new live stamp
on the console.

The reset prints what it cleared, as in Part 0's image of the four resets, and `make demo` then
prints one line with the queued run's id.

**Look at:** the live stamp of the new run: a start time from just now.

**What it means:** the new run starts from the same state as the first. The hill-climbing reset
keeps the session's baseline experiment.

> [!CHECKPOINT]
> The new run shows a new start time and its own trace link.

> [!IFDIFFERENT]
> A service is down in `make ps` → `make up`, then the reset again.
> The same demo stalls twice → move on to the code walkthrough and return to the demo at the end of the section.

> [!INSTRUCTOR]
> Say: "This is a live system; it just did what live systems do. Same input, new run." Point at the
> new live stamp when the result appears.
