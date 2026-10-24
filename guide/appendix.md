# Appendix: Cheat sheet, troubleshooting, glossary and recovery

## Command cheat sheet

Every command in the guide, in class order. Run them from the repository folder.

| Moment | Terminal | Command | What you should see |
|---|---|---|---|
| Part 0 | Stack | `make up`, then `make ps` | Every service up; `api` and `postgres` healthy |
| Part 0 | Stack | `make check-data` | `check-data: both warehouses match expected.yaml` |
| Part 0 | Demo | `make reset NAME=agent-loop`, and the other three sections | Each reset ends without an error line |
| Part 0 | Demo | `make preflight PURPOSE=class` | A last line that starts `Live session started at` |
| Chapter 1 | Demo | `make demo NAME=agent-simple-question` | A posted count on the Agent page |
| Chapter 1 | Demo | `make demo NAME=agent-confident-wrong-answer` | A mismatch against gold, with trap notes |
| Chapter 1 | Demo | `make demo NAME=agent-unbounded-rows` | Tokens jump with the bug on; a truncation notice with it off |
| Chapter 2 | Demo | `make demo NAME=verify-malicious-sql` | The layer that stopped each statement |
| Chapter 2 | Demo | `make demo NAME=verify-retry-cap` | Escalated after 3 attempts |
| Chapter 2 | Demo | `make demo NAME=verify-graders-pass-still-wrong` | A green checklist beside a failed gold check |
| Chapter 3 | Demo | `make demo NAME=events-webhook-question` | One post at the report-only level, unverified |
| Chapter 3 | Demo | `make demo NAME=events-approval-survives-restart` | Holding for approval across a worker restart |
| Chapter 3 | Demo | `make demo NAME=events-duplicate-events` | One run, 2 duplicates absorbed |
| Chapter 3 | Demo | `make demo NAME=events-kill-switch-in-flight` | The run under Blocked by kill switch |
| Chapter 4 | Demo | `make demo NAME=improve-baseline-experiment` | The holdout ledger under v1 |
| Chapter 4 | Demo | `make demo NAME=improve-naive-analyzer-blocked` | The gate blocks the version |
| Chapter 4 | Demo | `make demo NAME=improve-analyzer-team-approve` | The knowledge diff of the candidate |
| Chapter 4 | Demo | `make demo NAME=improve-candidate-experiment` | Fixed items and regressions against the baseline |
| Chapter 4 | Demo | `make demo NAME=improve-cleared-unattended` | The spine question answered under the new version |
| Any time | Demo | `make reset NAME=<section slug>` | The section back at its starting state |

A planted half needs its flag in `.env` set to `1`, then `make up`; set it back to `0` and run
`make up` again afterwards. The flags are `BUG_UNBOUNDED_ROWS`, `BUG_NAIVE_GUARD`,
`BUG_NO_RETRY_CAP`, `BUG_MEMORY_CHECKPOINTER`, `BUG_NO_IDEMPOTENCY`,
`BUG_KILLSWITCH_AT_CLAIM_ONLY`, and `BUG_NAIVE_ANALYZER`; the kill switch demo also needs
`DEMO_PACING=1`.

## Troubleshooting

| What you see | Cause | Fix |
|---|---|---|
| `No live session is open: run make preflight first.` | No class session yet | `make preflight PURPOSE=class`, once |
| `Your OpenAI key was not accepted. Check it with the operations team.` | The key is missing or rejected | Ask the operations team |
| `The drift canary failed: ...` | The model no longer behaves as measured | Do not teach the measured results; re-run calibration |
| `Cannot connect to the Docker daemon` | Docker is not running | Start Docker, then `make up` |
| The console is blank | The console service is down | `make ps`, then `make up` |
| A run stays in one lane | The worker stalled or a run hung | `make reset NAME=<section slug>`, then the same demo |
| A planted half looks like the fixed system | The services hold the old `.env` | `make up` after each change to `.env` |
| Restart worker does nothing | Demo controls are off | `DATAPILOT_ALLOW_DEMO_CONTROLS=1` in `.env`, then `make up` |
| The kill switch run finishes first | Demo pacing is off | `DEMO_PACING=1` in `.env`, then `make up` |
| "No baseline run in this session yet." | The baseline experiment never started | Start it now, as the page offers |
| The Improve page does not move | The hill-climbing runner service is down | `make ps`, then `make up` |
| The trace list in LangSmith is still empty | Traces arrive later than the ledger | Read the console's holdout ledger; open the traces later |

Every other message, with its cause and fix: [troubleshooting](../docs/troubleshooting.md).

## Glossary

The terms the guide uses, in the wording of the course glossary. Every query is Structured Query
Language (SQL).

- **Agent loop**: The model calls tools, reads the results, and repeats until it answers.
- **Analyzer team**: The failure analyst, the rule writer, and the critic, which turn failed dev
  items into a candidate knowledge version.
- **Autonomy level**: How much DataPilot may do unattended: report-only, assisted, or unattended.
- **Baseline experiment**: The benchmark run under the active knowledge version, started in the open
  live session.
- **Business date**: The day DataPilot treats as today, 31 January 2026 (`DATAPILOT_BUSINESS_DATE`).
- **Console**: The Streamlit app that shows every loop live, on four pages.
- **Drift canary**: Three easy questions that must pass and two trap questions that must still fail.
- **Escalated**: A run that ended without an answer because it hit a cap or a refused write.
- **Event loop**: Events become jobs that workers run, with approvals, budgets, and a kill switch.
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
- **Spine question**: "What was our net revenue in fiscal year 2025?", the question every section
  asks.
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

<!-- capture: the terminal output of a reset followed by the same demo, on the class machine -->

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
