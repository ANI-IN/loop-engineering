# Costs

> **Terms on this page**
>
> - **Drift canary**: Three easy questions that must pass and two trap questions that must still fail.
> - **Trace**: The record of one run's steps, each model call and tool call, stored in LangSmith.
> - **Live session**: Everything that runs between one `make preflight` and the next.

What each command and assignment costs, as two numbers: the most it can cost at the caps, and what
it cost when measured. The caps and prices come from `platform/packs/datapilot_us/pack.yaml`; the
model comes from `.env.example`. Measured costs come from the course's own live runs, recorded in
the [calibration report](calibration-report.md).

## What you pay for

| Account | What bills it | Who pays |
|---|---|---|
| OpenAI, with the key from the operations team | Every model call: the analyst, the schema scout, the reviewer, the analyzer team | Charged to the key's project; the operations team sets its spending limit |
| LangSmith, your own account | Nothing on the free Developer plan without a card | Free; add no card |
| Docker, uv, git, make, Postgres | Nothing | Free |

Every agent uses gpt-6-luna (`OPENAI_MODEL` and `OPENAI_ANALYZER_MODEL` in `.env.example`). Its
prices in `pack.yaml`, in US dollars per 1 million tokens, from the
[OpenAI pricing page](https://developers.openai.com/api/docs/pricing):

| Token kind | Price per 1 million tokens |
|---|---|
| Input | 0.10 dollars |
| Cached input, read from the prompt cache | 0.01 dollars |
| Cache write, 30-minute lifetime (the default) | 0.125 dollars |
| Cache write, 12-hour lifetime | 0.25 dollars |
| Output | 0.50 dollars |

OpenAI caches a long prompt prefix on its own. The tokens it writes to the cache cost more than
plain input, 1.25 times for the default 30-minute lifetime and 2.5 times for the 12-hour one; a
later call that reads them pays the cached-input price
([gpt-6-luna model page](https://developers.openai.com/api/docs/models/gpt-6-luna),
[prompt caching guide](https://developers.openai.com/api/docs/guides/prompt-caching)). DataPilot
never asks for the 12-hour lifetime.

## Commands

The "at most" figure prices every model run of a command at its token cap,
`budgets.tokens_per_run` (60,000 tokens), at the output price: about 3 cents per run. The run
guard checks the cap before each model call, so one call that carries a large result can go far
past it: the planted unbounded rows half reached 186,689 tokens. The "at most" figures still hold,
because they price every token at the output price. Real runs use far less, mostly cheaper input
tokens.

| Command | Model calls | At most, at the caps |
|---|---|---|
| `make setup`, `make up`, `make seed`, `make check-data`, `make reset`, `make ps` | None | 0 dollars |
| `make preflight PURPOSE=<purpose>` | Five canary questions, one agent run each (about 40 model calls) | About 15 cents |
| `make demo NAME=<slug>`, one agent run | One run; retries stay inside its caps | About 3 cents per run |
| `make demo NAME=improve-baseline-experiment` | The whole benchmark: each holdout item 3 times, each dev item once | About 3 cents per run, times the runs |
| `make live-smoke` | Five real calls across the system | It prints its own estimate first |

Measured on gpt-6-luna: one analyst run costs about 0.001 dollars; one 70-run experiment cost
0.0594 to 0.0914 dollars where recorded; `make preflight` cost 0.0053 dollars. What the whole class
sequence costs is measured in the rehearsal.

Every run is also inside the daily cap, `budgets.tokens_per_day` (2,000,000 tokens). The worker
checks it before it claims each job, and a run past it ends as blocked by the budget.

## Assignments

Each live check prints its cost estimate and its spend cap before its first model call ("This
check makes live model calls, about N cents, and stops at 1.00 dollar"), then the actual tokens and
cost at the end, from the usage the OpenAI application programming interface (API) returns.
Model-dependent requirements of Assignment 1: Agent loop and Assignment 2: Verification loop run
each case twice, and a third time only when the two disagree. Assignment 4: Hill-climbing loop runs
the benchmark, so it is the costly one.

**Each check has its own spend cap**, 1.00 dollar (`assignments.check_cap_usd` in `pack.yaml`). The
check counts its own model calls in the spend ledger, so the cap holds on your machine, where the
build budget is off. It starts no new run once its spend, plus the most the runs already under way
can still add, would pass the cap. That headroom is 24 cents: up to 8 runs at once, each at its
whole token budget at the output price. So a check that meets the cap stops after about 76 cents
to 1 dollar, never more. Each check records its calls under an activity of its own (such as
`assignment-agent-loop-1a2b3c4d`), so two checks that run at the same time never count each
other's calls. A check stopped at the cap:

- stops its runs under way with the kill switch, including the benchmark runs that Assignment 4
  makes in its own process, waits for them to end, then releases the kill switch and puts back
  the autonomy level, and Assignment 4 puts back the active knowledge version, as a normal end
  does;
- prints what it spent, that the cap was reached, a PASS or FAIL line for every requirement it
  judged and a NOT RUN line for every one it did not, and how to run it again;
- exits with the "stopped" code, 2.

Typical is what one full check of a solution cost in the build's verification on 23 October 2026,
on gpt-6-luna. This table is the one source of these figures: each assignment page and each check's
"Typical" line quote it. The ranges are what was measured, not bounds: your checks can cost more or
less. The latest checks ran from 21:28 Coordinated Universal Time (UTC) that day, on the check code
as it stood then; a change later that night (23:55 UTC) reworked how each check counts its spend and
judges, with no model call, so these figures predate the checks that ship and each is owed a live
re-run.

| Assignment | What the check runs live | Typical, one full check |
|---|---|---|
| Assignment 1: Agent loop | Questions with informal or misspelled names | Typically about 0.4 cents (0.34 to 0.49, eight checks; the latest 0.49) |
| Assignment 2: Verification loop | The ambiguity suite, the leak cases, an approved export | About 2 cents (1.86 and 135 model calls, the check of 21:28 UTC; note 1) |
| Assignment 3: Event loop | The alert job, a late order, the kill switch, the drill-down | Typically about 0.3 cents (0.23 to 0.40, eight checks; the latest 0.37) |
| Assignment 4, first check of a live session | The baseline and the candidate experiment, the analyzer team, two candidates | About 38 cents, an estimate (note 2) |
| Assignment 4, each later check | The candidate experiment, the analyzer team, two candidates | About 14 to 24 cents (13.58 and 23.95, two checks) |

Note 1: one check of the Assignment 2 check as of 21:28 UTC, whose case 8 was reworded; before that
change, seven checks cost 1.84 to 2.28 cents (149 to 172 model calls each).

Note 2: a first check with two candidates is not yet measured. With one candidate it cost 30.66
cents (one check), and the second candidate's 56 dev runs add about 7 cents, at about 0.12 cents a
run. The Assignment 4 checks before 21:28 UTC all wrote one candidate, as the check did then: each
later check cost 8.70 to 20.56 cents (nine checks).

Without the cap is every run using its whole token budget, 60,000 tokens, at the output price. The
ceiling is what the check prints: the smaller of that and the spend cap.

| Assignment | Without the cap | Spend cap | Ceiling the check prints |
|---|---|---|---|
| Assignment 1: Agent loop | 36 cents | 1.00 dollar | 36 cents |
| Assignment 2: Verification loop | 108 cents | 1.00 dollar | 100 cents |
| Assignment 3: Event loop | 3 cents | 1.00 dollar | 3 cents |
| Assignment 4, first check of a live session | 678 cents, re-runs on top | 1.00 dollar | 100 cents |
| Assignment 4, each later check | 432 cents, re-runs on top | 1.00 dollar | 100 cents |

### The learner key limit

Recommended: a spending limit of 3 dollars on each learner's key, in a dedicated OpenAI project,
with an alert at 1.50 dollars. From the typical costs above, a learner who runs every check five
times while working, with Assignment 4 over two live sessions, spends about 1.45 dollars:
Assignment 1 about 2 cents, Assignment 2 about 10 cents, Assignment 3 about 1.5 cents, and
Assignment 4 about 1.31 dollars (two first checks at about 38 cents and three later ones at about
19 cents). The alert comes just past that, so it marks spending beyond the typical; the limit
leaves more than as much again for class demos and extra checks. A runaway check stops at its own
1.00-dollar cap, so the limit is the backstop across checks, never the first stop.

## LangSmith traces

LangSmith costs nothing on the free Developer plan, but the plan has a hard limit: 5,000 traces a
month while no card is on file. Past it, LangSmith refuses every upload until the month ends; the
limit resets at the start of each calendar month in Coordinated Universal Time (UTC), so the next
reset is 1 November 2026 at 00:00 UTC
([usage and billing](https://docs.langchain.com/langsmith/usage-and-billing)). A trace is one root
run with all its child runs.

**What is traced.** Every demo run and every assignment check run is traced in full. A benchmark
run inside an experiment (the hill-climbing runner's experiments and re-runs, calibration, and the
benchmark inside the check of Assignment 4: Hill-climbing loop) is traced only as a sample:
`tracing.experiment_sample_rate` in `pack.yaml`, 0.2, about 1 run in 5. The experiment runner
decides each run with LangSmith's own sampling rule on the run's id, and a run left out sends no
trace at all. Every run is still scored locally, and the holdout ledger is the record of an
experiment: a row reads "Not traced" when none of its runs was traced.

**Method.** One learner runs every core demo once and every assignment check once. A demo that
shows a planted bug runs once with the bug on and once with it off. Each agent run is counted as
3 traces: its first attempt, the reviewer, which runs as a trace of its own, and one more for a
retry or a resumed approval (each retry starts a new trace). That is more than most runs make: an
answered run with the reviewer makes 2. An analyzer team run is 3 traces (failure analyst, rule
writer, critic). In class the analyzer team writes 2 candidates (`analyzer.candidates`), each from
its own team run and each measured on the 25 dev items once, so its demo adds 50 benchmark runs.
The class benchmark is 70 runs (25 dev items once, 15 holdout items 3 times); with Assignment 4's
six items it is 82. Each experiment the gate judges gets 20 re-runs, and the promoted candidate 15
more for the clearance. The Assignment 4 check also writes 2 candidates, as the class does, and
measures each on its 28 dev items once: 56 more benchmark runs in every check.

| Demo or check | Fully traced | Benchmark runs inside experiments |
|---|---|---|
| Section 1: Agent loop, 3 core demos (4 agent runs) | 12 | None |
| Section 2: Verification loop, 3 core demos (2 runs, 15 retries, 1 run) | 24 | None |
| Section 3: Event loop, 4 core demos (1, 2, 7, and 2 runs) | 36 | None |
| Section 4: Hill-climbing loop, 5 core demos (see below) | 9 | 260 runs and 55 re-runs |
| Assignment 1: Agent loop (12 runs at most) | 36 | None |
| Assignment 2: Verification loop (36 runs at most) | 108 | None |
| Assignment 3: Event loop (1 run) | 3 | None |
| Assignment 4: Hill-climbing loop, first check of a live session (2 step traces) | 2 | 220 runs and 35 re-runs |
| In all | 230 | 570 runs |

Section 4's demos trace 2 analyzer team runs and 1 agent run in full (the naive analyzer makes no
model call), and run 3 experiments and 2 candidate measurements on the benchmark.

| | Benchmark traces | All traces | Share of 5,000 |
|---|---|---|---|
| Sampled at 0.2, one pass of everything | 342 | 572 | About 11 percent |
| Not sampled, one pass of everything | 1,710 | 1,940 | About 39 percent |
| Sampled at 0.2, the working pattern of "The learner key limit" above | 617 on checks, 189 on demos | About 1,630 | About 33 percent |
| Not sampled, the same working pattern | 3,087 on checks, 945 on demos | About 4,860 | About 97 percent |

The working pattern is every check of Assignments 1 to 3 five times, and Assignment 4 over two
live sessions: two first checks of 255 benchmark runs each (220 runs and 35 re-runs) and three
later ones of 173 each (82 runs, 56 dev runs for the two candidates, and 35 re-runs). Sampled, one
learner's whole course fits the free plan three times over; unsampled, the same work uses nearly
all of it, and the build's own experiments used it up on 23 October 2026.

**Why 0.2.** A class experiment of 70 runs still sends about 14 runs to the trace list filtered by
knowledge version, enough to open several in class; a holdout row (6 runs across the baseline and
the candidate) has a trace link about 3 times in 4. At 0.1 the list thins to about 7 runs and half
the rows read "Not traced"; at 0.5 the working pattern takes nearly half the plan.

**A refused upload never slows a run.** Feedback is sent from a background thread, every LangSmith
client waits at most 1 second for a `Retry-After` header instead of the 6 hours LangSmith's own
client allows, and the flush at the end of a command waits at most 15 seconds. The tests in
`platform/tests/unit/test_refused_trace_upload.py` hold it to that against a stand-in server that
refuses every request with the Hypertext Transfer Protocol (HTTP) status 429.

## The caps

| Cap | Setting in `pack.yaml` | What happens when a run reaches it |
|---|---|---|
| 50 rows to the model per query | `limits.row_cap` | The tool returns the first rows, the total count, and a truncation notice |
| 2,000 characters to the model per value | `VALUE_CHARACTER_CAP` in `loop1_agent/tools.py` | The tool and the reviewer's preview cut the value; the notice counts the cuts |
| 3 attempts | `limits.max_retries` | The run ends escalated, with every reason |
| 12 model calls per run | `limits.model_call_limit` | The model call limit ends the run |
| 16 tool calls per run | `limits.tool_call_limit` | Further tool calls are refused, and the agent must answer |
| 60,000 tokens per run | `budgets.tokens_per_run` | Checked before each call, so one large call can go far past it |
| 2,000,000 tokens per day | `budgets.tokens_per_day` | The worker claims no more jobs that day |
| A planner cost of 500,000 | `cost_guard.max_plan_cost` | The cost grader rejects the query before it runs |
| 1.00 dollar per assignment check | `assignments.check_cap_usd` | The check starts no new run and stops cleanly |

The caps hold whatever the model writes: each one is code, not a line in the prompt.

## Check what you spent

- **The terminal.** `make preflight`, `make live-smoke`, and every assignment check print their
  cost. The console shows the tokens and cost of each run.
- **The ledger on your machine.** Every model call is recorded with its tokens and cost in
  `~/.datapilot/spend-ledger.sqlite`. `make spend` prints the total by activity.
- **The OpenAI usage page** of the key's project shows what OpenAI billed. Ask the operations team
  if you cannot see it.

## How the ledger matches OpenAI's usage page

The ledger prices each call from the usage the API returns: `input_tokens`, and within
`input_tokens_details` the tokens read from the cache (`cached_tokens`) and the tokens written to
it (`cache_write_tokens`, split by lifetime in `cache_write_tokens_details`). LangChain passes
these on as `input_token_details.cache_read` and `input_token_details.cache_creation`. Plain input
is what is left: input minus cache reads minus cache writes. A call that fails after it was sent
(a timeout, a cut-off stream, a refusal) is recorded too, with the usage it reports, or else an
estimate counted from the request, marked `estimated` in the ledger.

The build's unattended night of 22 October 2026 is the check. Before cache writes were priced,
the ledger recorded 12,265 calls and 1.6833 dollars; OpenAI's usage page showed 12,269 requests
and 1.78 dollars. The ledger's token totals match the 12,265 model calls in that night's traces
exactly, and the traces add the cache writes the ledger did not store:

| Tokens | Count | Price per 1 million | Dollars |
|---|---|---|---|
| Plain input: 20,904,864 input, less 12,809,184 read, less 3,981,990 written | 4,113,690 | 0.10 | 0.4114 |
| Read from the cache | 12,809,184 | 0.01 | 0.1281 |
| Written to the cache (30-minute lifetime) | 3,981,990 | 0.125 | 0.4977 |
| Output | 1,491,337 | 0.50 | 0.7457 |
| Total, with cache writes priced | | | 1.7829 |

The old formula priced the 3,981,990 written tokens as plain input (8,095,680 plain input tokens,
0.8096 dollars), 0.0995 dollars too little, which gave 1.6833. Priced as OpenAI bills them, the
night comes to 1.7829 dollars, the usage page's 1.78.

The page also counts 4 requests and 2,675 input tokens the ledger never saw. That night's traces
show 32 calls that failed: 28 refused because the project had no credits left, 1 rejected as an
invalid request, and 3 that ended with an event-loop error in a development process. OpenAI counted
at most 4 of them as requests, which suggests the refusals were neither counted nor billed. Even
if all 2,675 tokens were cache writes, they add 0.0003 dollars: 1.7832, still 1.78.

## Sources

- Source 1: OpenAI pricing, <https://developers.openai.com/api/docs/pricing>, OpenAI, n.d.
- Source 2: OpenAI gpt-6-luna model page, <https://developers.openai.com/api/docs/models/gpt-6-luna>, OpenAI, n.d.
- Source 3: OpenAI prompt caching guide, <https://developers.openai.com/api/docs/guides/prompt-caching>, OpenAI, n.d.
- Source 4: LangSmith usage and billing, <https://docs.langchain.com/langsmith/usage-and-billing>, LangChain, n.d.
