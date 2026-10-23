# Module: Loop Engineering - Demos for Section 1: Agent loop

## The problem

**Illustrative scenario.** A finance manager at Harbor & Pine Outfitters asks DataPilot for the net
revenue of the last fiscal year. The analyst finds a column that looks like revenue, sums it over the
calendar year, and answers in one confident sentence. Later someone asks for a long list, and the
analyst pulls every row into its context before it answers.

These demos put both failures in front of a live run. The spine question runs under knowledge
version v1, which states only the money rule, so the traps in the seeded data decide the answer.
The unbounded rows demo sends a Structured Query Language (SQL) query that returns far more rows
than the model needs.

> **Terms on this page**
>
> - **Agent loop**: The model calls tools, reads the results, and repeats until it answers.
> - **Trap**: A business rule the schema does not reveal, so a plausible query gets it wrong.
> - **Gold SQL**: The query an analyst wrote by hand that gives the right answer.
> - **Answer envelope**: The structured result of a run: status, SQL, rows, and answer text.
> - **Knowledge version**: A numbered set of business rules given to the agent in its prompt.
> - **Planted bug**: A defect switched on by a flag so a demo shows its failure every time.
>
> All terms: [glossary](../../docs/glossary.md).

## What you'll see

Each demo is one real run of the analyst against the warehouse, with real model calls traced to
LangSmith. The analyst writes SQL, runs it through `run_query`, and
returns an answer envelope that the console shows with its SQL, tokens, cost, and trace link.

Times and cost: not measured yet. Calibration runs each demo three times and lists the runs on the
[evidence page](../../docs/evidence/section-1-agent-loop.md). Until then, `run.sh` states the most
a run can cost at the caps in `platform/packs/datapilot_us/pack.yaml`.

```mermaid
flowchart LR
    T[make demo or console control] --> E[Event and job]
    E --> W[Worker]
    W --> A[Analyst]
    A -->|list_tables, describe_table| S[(Warehouse)]
    A -->|run_query, rows capped| S
    A --> V[Answer envelope]
    V --> C[Console: tool timeline and gold check]
```

## Run it

Finish the [setup pages](../../setup/README.md) first, including the
[pre-class checks](../../setup/pre-class.md). Then start the services and confirm the data in a
terminal at the repository root:

```bash
make up
make check-data
```

Open the console at http://localhost:8501 on the Agent page. Run every core demo of this section
from the same terminal, one at a time, with:

```bash
bash section-1-agent-loop/demo/run.sh
```

Add `--optional` to run Texas last quarter after the core demos, or name one demo to run it alone.
Each `make demo` prints the run ids it started; the run itself shows up in the console.

The unbounded rows demo runs twice: once with the planted bug on and once with it off. Set
`BUG_UNBOUNDED_ROWS=1` in `.env`, run `make up` so the services read it, and run the demo; then set
it back to `0`, run `make up`, and run the demo again.

<!-- generated:demo-table -->
| Demo | Tier | Run it | Target minutes |
|---|---|---|---|
| The simple question | core | `make demo NAME=agent-simple-question` | 3 |
| Texas last quarter | optional | `make demo NAME=agent-texas-last-quarter` | 4 |
| The confident wrong answer | core | `make demo NAME=agent-confident-wrong-answer` | 5 |
| Unbounded rows | core | `make demo NAME=agent-unbounded-rows` | 4 |

Each demo also runs from the console (Agent > Ask; Agent > Ask; Agent > Ask the spine question; Agent > Run large query).
Recovery for every demo in Section 1: Agent loop: `make reset NAME=agent-loop`, then the same
trigger again. The target minutes are the class plan's, from `platform/demos/registry.yaml`, not
measured times.
<!-- /generated:demo-table -->

### Files and links

- [run.sh](run.sh): the launcher; its header states what it runs, the caps, and the target minutes
- [walkthrough.md](walkthrough.md): the code behind these demos, explained
- [Knowledge version v1](../../platform/packs/datapilot_us/knowledge/v1.yaml): the near-empty rules
- [The analyst's prompt](../../platform/src/datapilot/loop1_agent/prompts.py)
- [The row cap and call limits](../../platform/packs/datapilot_us/pack.yaml): `limits` and `budgets`
- [expected/](expected/): real output from a real run, for comparison after class, never in class
- [Evidence page](../../docs/evidence/section-1-agent-loop.md): the measured runs

## What to watch

| Step | Screen | What appears |
|---|---|---|
| The simple question | Agent page | The tool timeline: each call with its duration |
| The confident wrong answer | Agent page | The answer-versus-gold ledger and the annotated SQL |
| Unbounded rows | Agent page | The token counter, with the bug on and then off |

Each demo's entry below comes from the demo registry: how to start it, what guarantees its moment,
and what may differ from run to run.

<!-- generated:demo-runbook -->
### The simple question

- **Tier**: core
- **Start it**: Agent > Ask in the console, or `make demo NAME=agent-simple-question`
- **What appears**: The analyst lists tables, describes one, runs one query, and returns an answer envelope with the SQL and the result; the tool timeline shows each call with its duration.
- **Expected live outcome**: A correct count with its SQL, tokens, cost, and a LangSmith link.
- **What can vary**: the analyst's wording; number of tool calls; latency; tokens
- **Recovery**: `make reset NAME=agent-loop`, then the same trigger again

### Texas last quarter

- **Tier**: optional, cut first when the section runs late
- **Start it**: Agent > Ask in the console, or `make demo NAME=agent-texas-last-quarter`
- **What appears**: A multi-join question across orders, order items, products, and categories for customers in Texas over the last completed fiscal quarter (August to October 2025, against the business date of 31 January 2026), with the join path visible in the SQL.
- **Expected live outcome**: An answer whose SQL joins four tables; the gold check shows pass or the trap hit.
- **What can vary**: join order; whether the fiscal-quarter trap is hit; latency
- **Recovery**: `make reset NAME=agent-loop`, then the same trigger again

### The confident wrong answer

- **Tier**: core
- **Start it**: Agent > Ask the spine question in the console, or `make demo NAME=agent-confident-wrong-answer`
- **Guaranteed by**: the near-empty knowledge version v1; the tempting total_cents column; the undocumented order status codes; the five traps in the seeded data
- **What appears**: Under knowledge version v1, the spine question "What was our net revenue in fiscal year 2025?" gets a confident, wrong answer; the answer-versus-gold ledger shows the mismatch and the annotated SQL names each trap behind the wrong fragments.
- **Expected live outcome**: A mismatch against gold with at least one trap annotation on the SQL.
- **What can vary**: which traps the SQL hits; the wrong value; wording
- **Recovery**: `make reset NAME=agent-loop`, then the same trigger again

### Unbounded rows

- **Tier**: core
- **Start it**: Agent > Run large query in the console, or `make demo NAME=agent-unbounded-rows`
- **Guaranteed by**: the unbounded rows bug (`BUG_UNBOUNDED_ROWS`)
- **What appears**: With the unbounded rows bug on, a 10,000-row SELECT goes through run_query and a list question follows; the token counter spikes. With it off, the same steps return at most the row cap, the total count, and a truncation notice.
- **Expected live outcome**: Tokens per run jump with the bug on and drop back with it off.
- **What can vary**: exact token counts; the list question's wording
- **Recovery**: `make reset NAME=agent-loop`, then the same trigger again
<!-- /generated:demo-runbook -->

## What the result means

A correct count on the simple question shows the loop itself works: tool choice, SQL, and the
answer envelope. A mismatch on the spine question is the expected result under knowledge version
v1. It shows that better tools do not supply business rules, which is the case for
[Section 2: Verification loop](../../section-2-verification-loop/README.md).

If the spine question comes back correct, the model solved the traps unaided on this run. Report it
as it is; the gold check, not the answer's wording, is the verdict. One run shows what one model
did once; the evidence page counts several.

With the unbounded rows bug on, the token counter jumps because every row reaches the model. With it
off, the model sees at most the row cap (`limits.row_cap` in `pack.yaml`), the total count, and a
truncation notice.

## If it fails

| What you see | Why | What to do |
|---|---|---|
| `run.sh` says the services do not answer | The services are not running | `make up`, then `make ps` until every service is healthy |
| The run stays in Queued | The worker is not running or is restarting | `make ps`; `make logs NAME=worker` for the reason |
| The run ends escalated with a token limit | The run reached `budgets.tokens_per_run` | Reset and run it again; the cap is the designed stop |
| The token counter does not move with the bug on | The services still hold the old `.env` | Run `make up` after each change to `.env` |
| Anything else | A stale run or an engaged kill switch | `make reset NAME=agent-loop`, then the same trigger again |
