# Stage 02 — The Verification Loop (Level 2)

> Folder numbers are **loop levels and session stage order**, not phase numbers.
> New to the vocabulary? Read [`demos/README.md`](../README.md) first.

---

## Purpose

**Show a loop that can reject a query which ran perfectly well — and then show how easy
it is to weaken the thing doing the rejecting without anyone noticing.**

Four entry points, in the order a room should meet them:

| entry point | what it demonstrates |
|---|---|
| `run.py` | One question through the verifiers. A query that executes, returns rows, and is sent back anyway with a named rule. |
| `regex_swap.py` | The same questions with the parse-tree checks swapped for regexes. The score goes **up** while the instrument catches **less**. |
| `failure_paths.py` | The three ways a run ends without succeeding. A branch nobody has watched fire is a branch nobody has tested. |
| `abstain.py` | The loop declining to answer, and the coverage/precision trade that decision creates. |

The single most important beat is `regex_swap.py --level L0`: **a fully satisfied verifier
sitting next to almost nothing correct.** That is the honest ceiling of a structural
check, and it is the failure people recognise from their own systems.

---

## Prerequisites specific to this stage

| | |
|---|---|
| **API key** | **Required** by `run.py`, `regex_swap.py` and `failure_paths.py`. Not required by `abstain.py`, which reads cell files off disk and makes no call. |
| **Earlier stages** | None for the first three. **`abstain.py` is the exception**: it needs a measured cell on disk, which is stage 04's output. It says so rather than failing obscurely — see the captured message below. |
| **Cost** | More per question than Level 1: each verification round is another call, and a rejected attempt regenerates. `regex_swap.py` runs the same questions twice, once per verifier, so roughly double a single pass. `failure_paths.py` makes real calls on purpose. |

**Which commands here are free.** `--help` on any of the four entry points — captured
verbatim in
[`docs/assets/02-verification-loop-help.txt`](../../docs/assets/02-verification-loop-help.txt)
— and this one, which is free *and* does real work, because abstention is recomputed from
telemetry that was already measured:

```bash
uv run python demos/02_verification_loop/abstain.py --headless
```

The rule-surface probes are also free and offline, and they are the honest way to check
the verifier itself. [`demos/00_preflight/check.py`](../00_preflight/README.md) runs them
as its fifth line.

---

## What this level ADDS

Verifiers. Level 1 could only see a query that crashed. Level 2 checks a query that
**ran** against the business rules it was supposed to honour, and sends it back with the
specific complaint.

A verifier here is a function that receives the question, the SQL, the schema, the rules
this item requires, and what happened when the query ran — and returns the rules it
believes were broken.

**It never receives the gold answer, and that is structural rather than conventional.**
`VerifyContext` has no field for it, and `build_context()` takes no gold parameter, so
there is nothing in scope at the construction site for a careless author to pass
through. A verifier that could see the answer would score perfectly and measure nothing.

### The control flow

```mermaid
flowchart TD
    Q["Question + the rules this item requires"] --> GEN["Model writes SQL"]
    GEN --> RUN["Execute, read-only, under a timeout"]
    RUN -->|"failed to execute"| DBERR["Feedback: the database's own error<br/><i>this is all Level 1 had</i>"]
    RUN -->|"ran, returned rows"| CTX["build_context()<br/>question · SQL · schema · rules · rows · error"]

    CTX --> GOV["V2 governance verifier"]
    GOV --> COV{"Does every rule declared in<br/>semantic_model.yaml have a check?"}
    COV -->|no| BUILD(["<b>UnenforcedRule</b><br/>raised at import — the build fails"])
    COV -->|yes| AST["Parse-tree checks over the sqlglot AST<br/><i>is the column actually constrained?</i><br/><i>not: does the text mention it?</i>"]

    AST --> VERDICT{"All applicable rules satisfied?"}
    VERDICT -->|yes| ACC(["<b>success</b> — accepted"])
    VERDICT -->|no| FB["Feedback: <b>the rule name and its complaint</b>"]
    FB --> LOOP{"Same SQL, or same feedback,<br/>as before?"}
    LOOP -->|yes| NP(["<b>no_progress</b>"])
    LOOP -->|no| CAPS{"Attempts and budget left?"}
    CAPS -->|no| CAPT(["<b>max_attempts</b> / <b>budget</b>"])
    CAPS -->|yes| GEN
    DBERR --> GEN

    GOLD["the gold answer"]
    GOLD -.->|"NOT a parameter of build_context.<br/>Not in scope. Not omitted by habit."| CTX

    classDef term fill:#e0f2fe,stroke:#0369a1,color:#0b1220,font-weight:bold;
    classDef forbidden fill:#fee2e2,stroke:#b91c1c,color:#0b1220,stroke-dasharray:5 4;
    classDef build fill:#fef3c7,stroke:#b45309,color:#0b1220,font-weight:bold;
    class ACC,NP,CAPT term;
    class GOLD forbidden;
    class BUILD build;
```

Two things in that diagram are the stage.

**The feedback path carries a rule name and never the answer.** The model is told
*"[multi_currency] Amounts in different currencies are being combined without
conversion"* — never the number it should have produced, never how far off it was.

**The governance verifier reads its rule set from the config.** V1 was a dictionary of
Python checks, and it had the defect this whole workshop is about: the rule set it
enforced and the rule set the config declared were two separate lists nobody compared.
Add a rule to the YAML and V1 silently did not enforce it — the prompt told the model
about it, the semantic model documented it, and nothing checked it. V2 makes the config
the source of truth and **fails the build** when a declared rule has no check. It caught
a real gap on its first run.

### Checks read the parse tree, not the text

`check_soft_delete` asks *"is `deleted_at` actually constrained anywhere in this query's
logic?"* by walking the sqlglot AST. A check that greps for `deleted_at IS NULL` passes a
query with that string inside a comment, inside a subquery that never joins, or negated.

`regex_swap.py` exists to demonstrate exactly that.

### The beat that matters most: a satisfied verifier and zero correct answers

Run the swap at **L0** and both verifiers report everything accepted while almost nothing
is right.

That is not a bug. It is the honest ceiling of a *structural* verifier. The currency
check confirms the query **converts** — that a `CASE` over `currency` exists — and it
cannot confirm the **rates inside it are right**, because nothing about summing mixed
currencies is structurally detectable without the FX factors. At L0 the model has never
seen those factors, so it writes a well-shaped conversion using invented numbers, and
every check passes.

Say this out loud. A verifier that is fully satisfied while every answer is wrong is a
sharper lesson than the regex swap, and it is the one people recognise from their own
systems.

**The implication is a prediction, not a conclusion:** whatever the loop buys at L0 has
to come from governance and execution feedback rather than from structural checks. Stage
04's ablation is what tests that. Do not present it as established.

### The uncomfortable half: swapping the instrument

`regex_swap.py` replaces the AST rule checks with regexes looking for the same thing in
text. The result: the **acceptance rate goes up**, rejections go **down**, cost goes
**down** — and the verifier demonstrably **catches less**.

Three of those four look like an improvement on a dashboard.

Say **"catches less"**, not "quality goes down". Whether the *answers* got worse is a
separate claim, it is underpowered at this `n`, and it is bounded by construction: the
two arms can only differ on items the strict verifier actually rejected. The demo prints
that bound. The demonstrated fact is that **a weaker instrument reports better numbers**,
which is enough.

The only way to tell an improvement from a weakened instrument is to test the instrument
against inputs whose correctness you already know — the **rule-surface probes**. Two per
rule: one query that breaks it and must be rejected, and one that is *correct but
unusual* and must be accepted. The second is the one people skip, and without it a
verifier that rejects everything scores perfectly.

### Abstention: the loop can decline, and say why

`abstain.py` turns coverage from a synonym for *did not crash* into a **choice**.

The confidence signal is read off the loop's own telemetry — did the query run, how many
times did the verifier send it back, which branch terminated the run — rather than from
an extra call asking the model whether it is sure. That is cheaper, and it is more
honest: a model's stated confidence is one more generation to be wrong about, while a
`no_progress` termination is a fact about what happened.

Because the signal is telemetry, the whole coverage/precision curve can be recomputed
over runs that were already measured. **Calibrating abstention costs nothing.**

A declined question shows its reason in plain English and the operator can open the
attempts behind it. **The gold answer is deliberately not shown in that view** — someone
judging whether a decline was fair should be looking at the query and the reason, not at
the answer key.

Answer submission is deliberately missing. It was scoped as polish, and a half-built
write path that silently drops an operator's answer is worse than an obvious gap.

---

## What this level COSTS

More than Level 1 per question: each verification round is another call, and a rejected
attempt means the generation runs again. That is the trade being shown — **Level 2 buys
correctness with tokens**, and the run's own meter is the honest way to see how much.

`regex_swap.py` runs the same questions twice, once per verifier, so it costs roughly
double a single pass.

`failure_paths.py` makes real model calls on purpose. None of the three scenarios stubs
the model, because what is being demonstrated is the controller's behaviour under a real
generator, and a scripted client would only prove that the scripted client works.

As everywhere: tokens measured, dollars estimated with the `est.` prefix, every call
counted including the ones that failed.

---

## Run it COLD

No prior step required. Does not depend on stage 01 having run.

### 1. One question through the verifiers

```bash
uv run python demos/02_verification_loop/run.py

# or pick the item yourself
uv run python demos/02_verification_loop/run.py --item p05_net_revenue__02

# or watch what happens with the rules withheld
uv run python demos/02_verification_loop/run.py --level L0
```

**What appears:** the question, the rules it requires, then one block per attempt — the
SQL, and either `VERIFIER REJECTED` with the named rule and complaint, or `accepted`
with the rows.

**What to observe:** the **diff between attempts**. A filter appearing. A `CASE` over
currency being added. Point at the change, not at the final answer.

**The question to sit with:** *the rejected query ran cleanly and returned rows. What
told us it was wrong, and could that same thing have told us at Level 1?*

### 2. The swap

```bash
uv run python demos/02_verification_loop/regex_swap.py

# the L0 beat — a fully satisfied verifier and almost nothing right
uv run python demos/02_verification_loop/regex_swap.py --level L0
```

Defaults to items requiring `fan_out`, because that is where the two verifiers genuinely
differ: *"`orders.amount_minor` aggregated **after** joining `order_items`"* is a shape,
not a word, and text cannot express it.

**What appears:** two arms side by side — acceptance rate, actual correctness, rejection
count, cost, and probe surface — then a generated reading.

**What to observe:** the probe surface dropping while the acceptance rate rises.

**The question to sit with:** *which of these four numbers would have appeared on a
dashboard, and which one would have told you the instrument got worse?*

### 3. The termination branches

```bash
uv run python demos/02_verification_loop/failure_paths.py
```

Three runs that end **without** succeeding: the attempt cap, the budget cap, and the
no-progress detector. Not every demo path is a success path, and a branch nobody has
watched fire is a branch nobody has tested. Exits non-zero if any branch fails to reach
the termination it claims.

### 4. Abstention

```bash
# print the curve and the declined list
uv run python demos/02_verification_loop/abstain.py --headless

# serve the intervention view
uv run python -u demos/02_verification_loop/abstain.py
```

Needs a measured cell on disk — run stage 04's sweep first, or pass `--dir` at a
directory that has one. It says so plainly if there is nothing to read.

**What to observe:** move the threshold and watch coverage and precision move in
**opposite** directions.

**The question to sit with:** *a single accuracy number would have hidden this trade
completely. Where on that curve would you actually want to sit?*

### Configuration options

Read from the argparse declarations. The full `--help` output for all four entry points is
captured verbatim in
[`docs/assets/02-verification-loop-help.txt`](../../docs/assets/02-verification-loop-help.txt).

**`run.py`**

| flag | default | what it does |
|---|---|---|
| `--item` | *(a rule-heavy item)* | Gold item id. Omitted, it picks the first `p05_net_revenue` item, which requires several rules at once. |
| `--role` | `worker` | `worker` or `frontier`. |
| `--level` | `L3` | `L0` or `L3`. `L0` is the beat where the verifier is satisfied and the answers are not. |
| `--max-attempts` | `3` | The retry cap. Unlike Level 1, `budget` and `no_progress` are genuinely reachable here. |

**`regex_swap.py`**

| flag | default | what it does |
|---|---|---|
| `--limit` | `10` | Items per arm. Both arms run the same items — the comparison is paired. |
| `--rule` | `fan_out` | Only items requiring this rule. `fan_out` is the default because it is a *shape* rather than a word, so it is where the two verifiers genuinely differ. If no item requires the named rule, it falls back to the whole rule-bearing pool rather than running nothing. |
| `--level` | `L3` | `L0` or `L3`. |
| `--max-attempts` | `3` | The retry cap, applied to both arms. |

**`failure_paths.py`**

| flag | default | what it does |
|---|---|---|
| `--item` | *(a rule-heavy item)* | Gold item id. Omitted, it picks the first `p07_aov_by_region` item. |

It takes no other flags on purpose: the three scenarios are the demo, and making them
configurable would let someone reach a branch by tuning rather than by running the
controller.

**`abstain.py`**

| flag | default | what it does |
|---|---|---|
| `--cell` | `worker_L0_loop_r0` | Which measured cell to read the telemetry from. |
| `--dir` | `results/sweep` | Where cell files live. Point it at any directory that has one. |
| `--threshold` | `1.0` | The abstention threshold used for the declined list in headless mode. |
| `--headless` | off | Print the curve and the declined list instead of serving the intervention view. |
| `--share` | off | Public tunnel for the served view. |

### Expected output — what is captured, and what is not

**Not captured: any successful run of `run.py`, `regex_swap.py` or `failure_paths.py`.**
All three make live model calls, so nothing on this page quotes their output. What they
print is described above under *What appears*, and those descriptions come from the
rendering code — `_render()` in `run.py` for the attempt blocks, and `run_swap()` in
`src/loopeng/verify/swap.py` for the two-arm table and the generated reading. **Read your
own output; do not match it against a page.**

**Captured: the keyless failure**, 2026-08-03, from a clean directory with no
`ANTHROPIC_API_KEY`. All three key-requiring entry points print exactly this and exit 1,
having called nothing:

```text
$ uv run python demos/02_verification_loop/run.py

ANTHROPIC_API_KEY is not set. Add ANTHROPIC_API_KEY=<your key> to .env (see .env.example).

```

**Captured: `abstain.py` with no cell to read**, same day. This is the honest-failure path
the section above promises, and it is what you get on a fresh clone before stage 04 has
run:

```text
$ uv run python demos/02_verification_loop/abstain.py --headless --dir <a directory with no cells>
No cell 'worker_L0_loop_r0' in <a directory with no cells>. Run the sweep first.
```

Exit code `1`. The path in the real output is whatever you passed to `--dir`; it is
elided here only because the capture ran from a scratch directory.

**Captured: `--help` for all four entry points** —
[`docs/assets/02-verification-loop-help.txt`](../../docs/assets/02-verification-loop-help.txt).

---

## Expected SHAPE — and what to say if it does not appear

**`run.py`** — at least one rejection with a named rule, then a revised query that
differs in a visible way.

**`regex_swap.py`** — the regex verifier scores **higher** while catching **less**: a
higher acceptance rate, fewer rejections, lower cost, and a probe surface that drops
from fully sound to at least one missed violation.

**The correctness comparison is underpowered and the demo says so.** At this `n` the
interval is wide enough that "quality held" and "quality halved" cannot be told apart,
and the arms can only differ on items the strict verifier actually rejected — the demo
prints that bound. **Do not read equal correctness as evidence the weaker verifier is
fine. Read the probe surface.**

**`failure_paths.py`** — three runs, each reaching the branch it names.

**`abstain.py`** — a slider, with coverage and precision trading against each other, and
a list of declined questions each explaining itself in a sentence.

### If the shape does not appear

*If the regex verifier does not score higher*, do not treat it as a failed demo. The
narration is generated from what actually happened and refuses to claim a dashboard
effect that did not appear. Say what happened and make the point directly: the risk is
that a verifier is graded by the score it produces rather than by what it catches, and
the fix is to check instruments against known-wrong inputs. **The argument stands whether
or not the numbers cooperate on the day.**

*If a verifier rejects everything*, that is also worth showing: an instrument that never
passes anything is as useless as one that never fails anything, and it is **visibly**
broken rather than silently wrong.

*If nothing is declined* in `abstain.py`, the threshold is too low — raise it until
something is, and say that out loud. An abstention mechanism that never abstains is
decoration.

*If `failure_paths.py` reports a MISMATCH*, read which branch. `max_attempts` reporting
`no_progress` means the over-strict verifier is repeating its complaint — that is the
no-progress detector working, and the scenario needs varied feedback to reach the cap.
That distinction was found by running it, not by reading it.

*If the build raises `UnenforcedRule`*, someone added a rule to `semantic_model.yaml`
without a check in `RULE_CHECKS`. That is the governance gate doing its job. It is also
the single best live demonstration available in this stage, if you have the nerve.

---

## Troubleshooting — the real failure text

The section above is what to *say* when the demo's shape is wrong. This one is what to do
when the command itself is wrong.

**`ANTHROPIC_API_KEY is not set. Add ANTHROPIC_API_KEY=<your key> to .env (see
.env.example).`** — captured above. Exit 1, stderr, nothing billed. `run.py`,
`regex_swap.py` and `failure_paths.py` all print exactly this; `abstain.py` never does,
because it needs no credential.

**`No cell 'worker_L0_loop_r0' in results/sweep. Run the sweep first.`** — `abstain.py`
only, captured above, exit 1. Either run stage 04's sweep, or point `--dir` at a
directory that already has a cell file. It refuses rather than plotting an empty curve,
because a flat line reads as a measurement.

**`UnenforcedRule` raised at import, before anything runs.** A rule was added to
`semantic_model.yaml` with no check in `RULE_CHECKS`. This is the governance verifier
failing the build on purpose — the declared-versus-enforced gap, caught at the only moment
it is cheap to catch. Add the check, or remove the rule.

**`failure_paths.py` exits non-zero with a `MISMATCH`.** A scenario reached a different
termination than it claimed. Read *which* branch: `max_attempts` reporting `no_progress`
means the over-strict verifier repeated its complaint and the no-progress detector fired
first. That is the detector working; the scenario needs varied feedback to reach the cap.
This distinction was found by running it, not by reading it.

**`regex_swap.py` runs but the arms are identical.** Check `--rule`. If no gold item
requires the rule you named, the script silently falls back to the whole rule-bearing pool
— which will include items where the two verifiers cannot differ. `fan_out` is the default
for exactly this reason.

**Imports fail after a successful `uv sync`** — iCloud-synced checkout; see
`src/loopeng/env_guard.py`. **The wrong Python runs** — a conda base environment on
`PATH`; run everything through `uv run`.

---

## Limitations — what this stage does not show

- **The structural verifier cannot check values, only shapes.** It confirms a `CASE` over
  `currency` exists; it cannot confirm the rates inside it are right. At `L0` that is why
  everything passes and almost nothing is correct. This is a ceiling, not a bug.
- **The correctness comparison in the swap is underpowered, and bounded.** The two arms
  can only differ on items the strict verifier actually rejected, and the demo prints that
  bound. Do not read equal correctness as evidence the weaker verifier is fine — read the
  probe surface.
- **One rule is exercised by a single pattern**, so the sweep can make no claim about it.
  Its enforcement is covered by the rule-surface probes instead, which test the verifier
  directly rather than inferring it from outcomes.
- **Six rules are probed, not seven.** `minor_units` and `multi_currency` are one SQL
  change and share a single check, so one probe pair covers both. The exemption is named
  in `probes.py` as `UNPROBED_BY_DESIGN` and the report carries `n_declared_rules`
  alongside `n_rules` — a fraction whose denominator had itself drifted is the defect that
  produced that field.
- **Abstention is calibrated, not enforced.** `abstain.py` shows the curve and the
  declined list. Nothing in this stage acts on a threshold automatically.
- **Escalation exists and no entry point runs it.** `src/loopeng/triage/escalate.py`
  implements and tests handing a declined question to the frontier model, but nothing on
  this page invokes it — the OVERSIGHT view reads a stored artifact instead. It is a
  documented gap rather than a hidden one.
- **Answer submission is deliberately missing** from the intervention view. It was scoped
  as polish, and a half-built write path that silently drops an operator's answer is worse
  than an obvious gap.
- **Every committed measurement in this repository predates a verifier fix and has not
  been re-run.** The old AST checks asked only whether a column *appeared* in a `WHERE` or
  `JOIN` — no polarity, no table — so four bypasses were possible and are now pinned as
  tests. Anything stored describes a *weaker* verifier than the one you are running. If
  your numbers differ from the committed ones, that difference is the finding.

---

## Where to go next

| | |
|---|---|
| the deep-dive on this stage | [`ONBOARDING.md`](ONBOARDING.md) |
| the vocabulary this page assumes | [`demos/README.md`](../README.md) |
| the whole project | [the root README](../../README.md) |
| this stage in the root README | [§11 Stage 2](../../README.md#11--running-each-demo) |
| what is and is not claimed | [root README §16 Limitations](../../README.md#16--limitations) |
| **previous stage** — the loop that cannot see this | [`01_agent_loop/`](../01_agent_loop/README.md) |
| **next stage** — these verifiers, with nobody watching | [`03_event_driven_loop/`](../03_event_driven_loop/README.md) |

---

## Where the code lives

| you are looking for | it is in |
|---|---|
| the Level 2 loop, `build_context` and its missing gold parameter | `src/loopeng/verify/loop.py` |
| the AST rule checks | `src/loopeng/verify/verifiers.py` |
| the governance verifier and the build gate | `src/loopeng/verify/governance.py` |
| the deliberately weaker regex checks | `src/loopeng/verify/regex_verifiers.py` |
| the swap comparison and its generated reading | `src/loopeng/verify/swap.py` |
| the rule-surface probes | `src/loopeng/verify/probes.py` |
| the three termination scenarios | `src/loopeng/verify/failure_paths.py` |
| the contract type with no field for the answer | `src/loopeng/contracts.py` |
| abstention scoring and the intervention view | `src/loopeng/triage/abstain.py`, `src/loopeng/views/intervention.py` |
