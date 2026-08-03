# Stage 01 — The Agent Loop (Level 1)

> Folder numbers are **loop levels and session stage order**, not phase numbers.
> New to the vocabulary? Read [`demos/README.md`](../README.md) first — it defines
> *silent error*, *gold item*, *L0/L3*, *termination reason* and everything else used
> below.

---

## Purpose

**Show a loop that retries, and then show the class of failure it cannot see.**

A model writes SQL, the query runs, and if it fails the database's error goes back to the
model. That is the loop most teams already have. This stage runs it (`run.py`), and then
runs every gold question twice — once with the business rules written into the prompt and
once with them withheld — and reveals how each answer was actually scored (`trap.py`).

The teaching point is not the retry. It is that **a successful run at this level tells you
nothing about whether the answer is right**, and the reveal is what makes a room feel that
before it is named.

---

## Prerequisites specific to this stage

| | |
|---|---|
| **API key** | **Required** for both entry points. `run.py` and `trap.py` both call a model on every attempt. |
| **Earlier stages** | None. The warehouse is generated on first use and the gold set is rebuilt from its patterns. |
| **Cost** | `run.py`: one call per attempt, on the cheap worker model, capped at `--max-attempts` (default 3). `trap.py`: the whole gold set twice — the largest call count in this stage, though not the largest bill. It refuses to start if its own projection exceeds `--cap-usd` (default 2.0). |

**Which commands here are free.** Exactly two, and they make no network call of any kind:
`run.py --help` and `trap.py --help`. Both are captured verbatim in
[`captures/01-agent-loop-help.txt`](captures/01-agent-loop-help.txt), and both
are what `tests/test_demo_structure.py` runs to prove this stage cold-starts.

Everything else on this page spends. Run
[`demos/00_preflight/check.py`](../00_preflight/README.md) first if you have not proved
your key today — it is the cheapest way to find out that `trap.py` will fail after the
first call rather than before it.

---

## What this level ADDS

A model writes SQL, the query runs against a read-only warehouse, and when it fails the
database's own error goes back to the model, which tries again. That is the whole of
Level 1: **retry on failure**.

**Be precise about which failure, because it is the teaching point.**

> **Level 1 catches SYNTACTIC failure. It cannot catch SEMANTIC failure.**
>
> It retries when the SQL did not parse, did not run, or timed out. The feedback it
> receives is the database error and nothing else — not a hint, not a rule reminder,
> just the database's own complaint.
>
> It cannot catch SQL that parses, runs, returns a clean number, and is **wrong**.
> Nothing at this level compares the answer to anything, because there is nothing to
> compare against that the agent is allowed to see.

The distance between those two is the entire reason Level 2 exists, and this stage is
where a room should *feel* it before it is named.

### The control flow

```mermaid
flowchart TD
    Q["Question"] --> P["Render the prompt<br/>L0 = schema only · L3 = schema + declared rules"]
    P --> BUD{"Budget already spent?"}
    BUD -->|yes| TB(["<b>budget</b>"])
    BUD -->|no| GEN["Model writes SQL"]
    GEN -->|"call raised"| REC["Record the call anyway —<br/>a failed call still billed"]
    REC --> BUD
    GEN --> RUN["Execute against the<br/>READ-ONLY warehouse, under a timeout"]
    RUN --> EXEC{"Did it execute?"}
    EXEC -->|yes| TS(["<b>success</b>"])
    EXEC -->|no| PROG{"Same SQL as before,<br/>or same error as before?"}
    PROG -->|yes| TN(["<b>no_progress</b>"])
    PROG -->|no| CAP{"Attempts remaining?"}
    CAP -->|no| TM(["<b>max_attempts</b>"])
    CAP -->|yes| FB["Feed back the database's own error.<br/>Nothing else. No hint, no rule."]
    FB --> BUD

    BLIND["Is the answer RIGHT?"]
    TS -.->|"never asked at this level"| BLIND

    classDef term fill:#e0f2fe,stroke:#0369a1,color:#0b1220,font-weight:bold;
    classDef blind fill:#fef3c7,stroke:#b45309,color:#0b1220;
    class TS,TB,TN,TM term;
    class BLIND blind;
```

**The six termination conditions are recorded by name on every run**: `success`,
`max_attempts`, `budget`, `no_progress`, `credential`, `bad_request`. Their distribution
across a full run is
reported, because a policy branch nobody counts is a branch nobody knows fires. At this
stage's default of one attempt per question, `budget` and `no_progress` are structurally
unable to fire — Stage 02 raises the cap and is where they first become reachable.

The amber box is the point of the stage. Nothing in that diagram asks it.

### The trap

`trap.py` runs every gold question twice: **the same model with the rules written down
(L3) and with them withheld (L0)**. Same model, same questions; the only variable is the
spec.

Running two *different* models instead would teach "buy the bigger one", which is the
opposite of this workshop's argument and would have to be argued against later. And L0
on its own is a wall of red that teaches nothing, because nobody can tell how much of it
is the missing spec and how much is the task simply being hard — **the L3 column is what
makes the L0 column legible.** Both columns are labelled on screen.

The questions are phrased the way a business user asks them, so the rules are never
smuggled into the question at either level. A test bans the rule vocabulary from
question text.

**Scoring is separated from execution, and that separation is the demo.** Each cell is
judged the moment its result lands and the judgement is held unrevealed. Pressing
*reveal* flips a flag; it re-runs nothing. A test asserts reveal makes zero model calls.

---

## What this level COSTS

One model call per attempt per question, on the cheaper worker model.

`trap.py` runs the whole gold set twice — once per spec level — so it is the largest
call count in this stage, though not the largest bill.

Every call is metered, including failed, timed-out and budget-exhausted ones, because
those generate tokens and bill. **Token counts are measured; the dollar figure is
estimated** — measured tokens times a hand-entered price table — and renders with the
`est.` prefix, which never comes off. Only a billing export would make cost a
measurement, and this project does not read one.

`trap.py` projects its cost before the first call and refuses to start if the projection
breaches `--cap-usd`. Stop it at any time; partial results are already written to
`results/`.

---

## Run it COLD

No prior step is required. Every command works from a clean checkout with the venv
installed; the warehouse is generated on first use and nothing needs seeding by hand.

### 1. One question, live

```bash
uv run python demos/01_agent_loop/run.py \
  --question "What was gross revenue in March 2025 from our euro and yen orders, in US dollars?"
```

**What appears:** the termination reason and model id, then one block per attempt — the
SQL the model wrote, and either the rows it returned or the database error it hit. Then
a cost line: estimated dollars, call count, and tokens split by class.

**What to observe:** most questions land on the first attempt. When one does not, the
error line is the *only* thing fed back. Notice how little the loop is told.

**The question to sit with:** *the last attempt returned a number. What in this output
tells you whether that number is right?*

### 2. The same thing in a browser

```bash
uv run python -u demos/01_agent_loop/run.py
```

Omit `--question` and it serves the AGENT view instead of running headless. Use `-u`:
without it Python block-buffers stdout when you redirect to a file and the URL never
appears even though the server is fine.

### 3. The trap

```bash
# in a browser, which is how it is delivered
uv run python -u demos/01_agent_loop/trap.py

# or in the terminal
uv run python demos/01_agent_loop/trap.py --headless

# fewer items while developing
uv run python demos/01_agent_loop/trap.py --headless --limit 6
```

**What appears:** a grid, one row per gold item, one column per arm. Cells fill in as
results land. **Every landed cell renders identically** — a cell reading "failed" before
the reveal would hand the room a free answer key for that row.

**What to observe while it fills:** the columns look the same. That is deliberate and
worth saying out loud.

**Then press reveal.** The withheld-rules column is visibly worse, and the scoring
splits three ways: correct, **silently wrong**, and visible failure.

**The question to sit with:** *of the cells that are wrong, how many could you have
spotted without the answer key?*

### Configuration options

Read from the argparse declarations in `run.py` and `trap.py`. The full `--help` output is
captured verbatim in
[`captures/01-agent-loop-help.txt`](captures/01-agent-loop-help.txt).

**`run.py`**

| flag | default | what it does |
|---|---|---|
| `--question` | *(unset)* | Run headless in the terminal. **Omitting it serves the AGENT view instead** — the flag chooses the mode, not just the text. |
| `--role` | `worker` | `worker` or `frontier`. The cheap model or the expensive one. |
| `--level` | `L3` | `L0` (schema only) or `L3` (schema plus every declared rule). |
| `--max-attempts` | `3` | The retry cap. This is the loop's whole termination policy at Level 1. |
| `--share` | off | Expose the Gradio app on a public tunnel. |

**`trap.py`**

| flag | default | what it does |
|---|---|---|
| `--headless` | off | Terminal instead of browser. The browser is how it is delivered. |
| `--limit` | *(all items)* | Run only the first N gold items. For development, not for delivery. |
| `--cap-usd` | `2.0` | Projected-cost ceiling. It projects **before** the first call and refuses to start if the projection breaches this. |
| `--share` | off | Public tunnel. |

### Expected output — what is captured, and what is not

**Not captured: a successful run.** Both entry points on this page make live model calls,
so nothing here quotes their success output. What `run.py` prints on a successful run is
described above under *What appears* — the termination reason and model id, one block per
attempt, then a cost line — and that description comes from
`src/loopeng/views/render.py`, which builds it. **Read your own output rather than
matching it against anything on this page.**

**Captured: the keyless failure**, on 2026-08-03, from a clean directory with no
`ANTHROPIC_API_KEY` set. Both entry points behave identically, and this is exactly what
you see if your key is missing:

```text
$ uv run python demos/01_agent_loop/run.py --question "What was gross revenue in March 2025 from our euro and yen orders, in US dollars?"

ANTHROPIC_API_KEY is not set. Add ANTHROPIC_API_KEY=<your key> to .env (see .env.example).

```

Exit code `1`, and the message goes to stderr. **Nothing was called and nothing was
billed** — the credential is validated before the loop is built, which is the whole point
of failing at the door.

**Captured: `--help`**, on the same day, for both entry points —
[`captures/01-agent-loop-help.txt`](captures/01-agent-loop-help.txt). That
file is what `tests/test_demo_structure.py` proves cold-starts from an empty directory.

---

## Expected SHAPE — and what to say if it does not appear

**`run.py`** — a timeline of attempts, with cost ticking upward. Some questions show a
crash, an error line, and a retry that succeeds.

**`trap.py`** — two columns that look alike while running, then a reveal in which the
withheld-rules column is worse. The shape to watch for is **high apparent success next
to low actual correctness**, in both columns.

The comparison is **paired**: both columns answered the same questions, so the reveal
reports McNemar's exact test over the discordant pairs — the items where one arm was
right and the other wrong. Items both arms got right, or both got wrong, carry no
information about which is better. The wording is directional on purpose — *"worse; we
cannot put a number on how much"* — because the items come in clusters and any specific
gap would be more precise than the design supports.

### If the shape does not appear

*If the two columns come out close*, say so plainly and move to Level 2. The point does
not depend on the size of the gap; it depends on there being a category of failure the
loop cannot see. A small gap on the day is a fact about the model, not a broken demo.
**Do not re-run hoping for a better number** — that is the exact behaviour this session
argues against.

*If a question errors on every attempt*, that is a **visible** failure, which is the
benign kind. Say that out loud; it is the contrast that makes the silent kind land.

*If the reveal seems slow*, it is not re-running anything — every judgement was computed
as its cell landed. If it genuinely hangs, the browser lost the `gr.State`; re-run the
trap rather than reloading the page.

*If the grid never fills*, check the API key resolves (`uv run python -c "from
loopeng.settings import load_settings; load_settings()"`). A missing key raises an error
naming the exact variable and the exact fix.

---

## Troubleshooting — the real failure text

The section above is what to *say* when the demo's shape is wrong. This one is what to do
when the command itself is wrong.

**`ANTHROPIC_API_KEY is not set. Add ANTHROPIC_API_KEY=<your key> to .env (see
.env.example).`** — verbatim, captured above. Exit code 1, nothing billed. A blank
`ANTHROPIC_API_KEY=` line in `.env` counts as absent on purpose, so "I set it to empty"
and "I did not set it" produce the same sentence rather than an auth failure at the first
call.

**`ABORT: projected est. $N exceeds the $M cap.`** — `trap.py` only. It projected the
whole run before making a call and stopped. Raise `--cap-usd`, or cut the run with
`--limit`. **It has spent nothing at this point**; the projection happens first.

**A `run.py` browser URL never appears.** Almost always stdout buffering rather than a
broken server. Use `python -u`, which is why every browser command on this page has it.

**`AuthenticationError` / a `401` or `403` on the first attempt.** The loop stops after
**one** call rather than retrying — a wrong key is not a transient failure and retrying it
three times just bills three times. The termination reason is recorded as `credential`.

**`BadRequestError` / a `400`.** The model refused the request itself. That is
`src/loopeng/registry.py` and not `.env`; the classic case is a sampling parameter the
frontier model rejects. The termination reason is `bad_request`.

**Imports fail after a successful `uv sync`.** The checkout is on an iCloud-synced path.
`src/loopeng/env_guard.py` raises a named error at import. Move the checkout.

**The wrong Python runs.** A conda base environment on `PATH` shadows the project
interpreter. Run everything through `uv run` and confirm with `uv run python -V`.

---

## Limitations — what this stage does not show

- **It cannot see a wrong answer.** That is the whole design and it is stated at the top,
  but it bears repeating as a limitation: nothing at Level 1 compares the result to
  anything. Stage 02 is the fix.
- **Two of the six termination conditions cannot fire in the trap.** `run_trap` is
  one-shot by default — Level 1's retry is not what it is measuring — and with a single
  attempt `budget` and `no_progress` are structurally unreachable. `run.py` raises the cap
  and makes them possible, but Stage 02's `failure_paths.py` is where you can reliably
  watch every branch fire.
- **The trap's comparison is directional and stays that way.** The items come in
  clusters, so McNemar over the discordant pairs overstates its own confidence. The demo
  says *"worse; we cannot put a number on how much"* rather than quoting a gap, and no
  number here should be read off a page.
- **The questions are templated.** A small set of patterns, parameterised. Nothing here
  is evidence about freely-phrased questions.
- **One provider.** Both roles are Anthropic models, so `--role frontier` is not a
  cross-vendor comparison and no LLM judge blocks anything.
- **The trap writes `results/phase1_trap.json` and nothing reads it back into the
  session.** It is an artifact for you, not an input to a later stage.

---

## Where to go next

| | |
|---|---|
| the deep-dive on this stage | [`ONBOARDING.md`](ONBOARDING.md) |
| the vocabulary this page assumes | [`demos/README.md`](../README.md) |
| the whole project | [the root README](../../README.md) |
| this stage in the root README | [§11 Stage 1](../../README.md#11--running-each-demo) |
| the architecture of this level | [root README §6](../../README.md#6--architecture) |
| **previous** — prove your key first | [`00_preflight/`](../00_preflight/README.md) |
| **next stage** — verifiers that catch what this cannot | [`02_verification_loop/`](../02_verification_loop/README.md) |

---

## Where the code lives

| you are looking for | it is in |
|---|---|
| the loop and its six termination conditions | `src/loopeng/agent/loop.py` |
| visible vs silent classification, the error taxonomy | `src/loopeng/agent/classify.py` |
| the trap runner, arms, cost projection | `src/loopeng/agent/trap.py` |
| the grid and the reveal | `src/loopeng/views/trap.py` |
| the read-only connection and the query timeout | `src/loopeng/warehouse/connect.py` |
| the gold set and its wrong-answer variants | `src/loopeng/gold/` |
