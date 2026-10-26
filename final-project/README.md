# Module: Loop Engineering - Final project

An open-ended capstone: the four loops on a domain no section used, with a benchmark you write, and
a report of what the loops changed. There is no grader; [CHECKLIST.md](CHECKLIST.md) lists what to
show.

## The problem

**Illustrative scenario.** A team ships an analytics agent on its own warehouse. In the first week
it answers a revenue question with a confident number that counts refunds as sales. The fix goes
into the prompt, and a question about the previous quarter quietly breaks. Nobody can say whether
the agent is better than it was, because nobody wrote down what "right" means for their data.

> **Terms on this page**
>
> - **Domain pack**: The folder that holds one warehouse's settings, rules, benchmark, and knowledge.
> - **Trap**: A business rule the schema does not reveal, so a plausible query gets it wrong.
> - **Holdout split**: The benchmark questions the analyzer team never sees; the gate decides on them.
> - **Promotion gate**: The check that a new knowledge version must pass before it becomes active.

## What you'll see

You build five things, each one a piece of the course applied to your own data:

1. **Your own dataset**: a Postgres schema with data you can share, real or generated, loaded into
   two differently seeded databases.
2. **At least three original traps**: business rules your schema does not reveal, none of them a
   copy of the Harbor & Pine traps or the template's.
3. **Your own benchmark with splits**: development and holdout questions, each with gold Structured Query
   Language (SQL), and a naive query for every trap question that gives a different answer.
4. **One extension**: one capability the class code does not have, in any of the four loops.
5. **A before-and-after report**: the baseline experiment under your starting knowledge, the
   candidate after the analyzer team and the gate, and what your extension changed.

The run time and cost depend on your benchmark: `run.sh` prints the number of model runs before it
starts. Your own pack's holdout ledger appears on the Improve page, laid out as the class pack's in
[Section 4: Hill-climbing loop](../section-4-hill-climbing-loop/demo/expected/README.md), with your
own items and versions.

## Run it

### Get ready

Finish the [setup](../setup/README.md) and the four sections. Then work through part 1 of
[apply the loops to your own data](../use-in-your-repo/apply-to-your-repo.md): it runs the
template pack end to end, so every file of a pack is familiar before you write your own.

### Build the pack

Copy the template and write it in this order: the business rules, the data, the benchmark, the
pack settings. Part 2 of the guide has each step.

```bash
cp -r platform/packs/_template platform/packs/my_pack
```

Your traps must change answers. A trap whose naive query returns the gold result on both
databases teaches the loops nothing, and the pack check fails it.

### Check, then run it live

```bash
final-project/run.sh my_pack
```

This runs the pack check with the database and makes no model call. Fix every `x` line. Then set
`DATAPILOT_PACK=my_pack` in `.env`, run `make up` so every service, the hill-climbing runner
among them, reads it, and run the live part:

```bash
final-project/run.sh my_pack --live
```

It starts a live session through `make preflight` with your pack's own canary, then the baseline
experiment. Continue on the Improve page: run the analyzer, read the knowledge diff, run the
experiment on the candidate, and approve or reject it at the gate.

### Time and cost

Every model run stops at `budgets.tokens_per_run` in your `pack.yaml`; at the caps a run costs
about 3 cents at the gpt-6-luna prices in `pack.yaml`. The baseline experiment makes three runs
per holdout item and one per development question, and the candidate experiment the same again, plus the
confirming runs of any apparent regression. The [costs page](../docs/costs.md) explains the caps.

## What to watch

| Step | Screen | What appears |
|---|---|---|
| Pack check | Terminal | One `ok` line per check, and each naive query differing from gold |
| Preflight | Terminal | Your canary: three easy questions pass, two trap questions fail |
| Baseline experiment | Improve page | The holdout ledger, with your trap items failing |
| Analyzer team | Improve page | Diagnoses, proposed rules, the critic's decisions, the knowledge diff |
| Candidate experiment | Improve page | Flips against the baseline, the regression column, the gate verdict |

## What the result means

- **Trap items fail under the starting knowledge.** Your traps are real: the schema does not
  reveal them. If one passes, the model inferred the rule from the data; strengthen it.
- **The candidate flips holdout items with zero regressions.** The learned rules generalize to
  questions the analyzer team never saw, on your data, for this run.
- **The gate blocks the candidate.** Read the reasons: a confirmed regression or no gain is a
  result, and the report says so.
- **One run is one run.** The model reasons afresh each time, so report counts from your runs,
  such as "3 of 4 holdout items", and never a percentage. A small holdout is weak evidence.

## If it fails

| Symptom | Cause | Fix |
|---|---|---|
| `x ...: the naive query differs from gold` | The trap does not change the answer on your data | Add rows that expose it, on both databases |
| `x DATAPILOT_PACK selects "..."` | The platform still reads another pack | Set `DATAPILOT_PACK=my_pack` in `.env`, then run it again |
| `The drift canary failed: a trap question passed ...` | The model solves a canary trap unaided | Pick a harder trap item for the canary, or strengthen the trap |
| The Improve page never updates | The `hill-climbing-runner` service is down | `make ps`; `make logs NAME=hill-climbing-runner`; `make up` |
| A run stalls or shows the wrong state | State left from an earlier run | `make reset NAME=hill-climbing-loop`, then run it again |

## Use it on your own repository

The final project is the rehearsal for your own warehouse. Part 3 of
[apply the loops to your own data](../use-in-your-repo/apply-to-your-repo.md) points DataPilot at
your own Postgres with a read-only role, and the [walkthrough](walkthrough.md) shows the code that
checks a pack and loads its benchmark.
