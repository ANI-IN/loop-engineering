# 00 · Preflight

```bash
uv run python demos/00_preflight/check.py
```

Numbered 00 because it runs before the loops. It is **not a loop level** — see
[the numbering note](../README.md).

---

## Purpose

**Answer "will this work on my key?" for a fraction of a cent, before anything expensive
runs.** It makes the two smallest possible model calls, then runs three offline checks,
and prints one pass/fail line each. It measures nothing about the workshop's subject; its
whole job is to tell you whether the rest of the repository can run at all, and if not,
which file to open.

It exists because of an absence rather than a bug: before it, the smallest live path was
`--profile delivery`, and a cloner with a typo in their key found out by starting the
thing that spends.

---

## Prerequisites specific to this stage

You need a working checkout (`uv sync`) and, for the two network checks, an
`ANTHROPIC_API_KEY` in `.env`. Nothing else — no earlier stage, no seeded database, no
LangSmith key.

| command | needs a key? | spends? |
|---|---|---|
| `uv run python demos/00_preflight/check.py --help` | no | **free** |
| `uv run python demos/00_preflight/check.py` | yes, for steps 1–2 | two calls, a handful of output tokens |
| `uv run python demos/00_preflight/check.py --quiet` | as above | as above |

**Without a key it still runs and is still free.** Steps 3 to 5 make no network calls, so
they execute anyway and the command exits 1 having spent nothing. That is a supported way
to use it, not a degraded one.

---

## WHAT IT ADDS

The cheapest possible answer to "will this work on my key?". Five checks, in order,
pass/fail per line:

1. `ANTHROPIC_API_KEY` is set — named, never printed.
2. Each role in the registry is called once, **with the request kwargs the registry
   declares**. That is the point: `temperature=0` is legal on Haiku and a 400 on
   Sonnet 5, so a simplified probe call could pass on an account where the sweep fails.
3. The warehouse builds from its seed.
4. The gold set builds, reporting items and clusters.
5. The rule surface runs offline and reports both columns — what the verifier rejects
   and what it accepts. A verifier that rejects everything scores perfectly on one
   column alone.

Steps 3 to 5 make no network calls, so they still run when the key is bad. A cloner
with a typo learns that the rest of their checkout is sound.

## WHAT IT COSTS

Two calls, a handful of output tokens. The line printed at the end carries the `est.`
prefix like every other dollar figure here — tokens are measured, dollars are a
hand-entered price table.

Before this existed the smallest live path was `--profile delivery`: 4 cells, 50 items,
roughly 200 calls, projected est. $0.43. There was no way to spend a fraction of a cent
to find out whether the key was valid first.

## COLD START

Fully cold. It generates the warehouse if it is absent and needs no earlier stage to
have run. `--help` works with no key at all.

---

## Exact run commands

```bash
# the whole preflight
uv run python demos/00_preflight/check.py

# exit code only, no output — for CI and scripts
uv run python demos/00_preflight/check.py --quiet
```

Adding `--help` to either form prints the flags and exits. It needs no key, makes no
network call, and is what `tests/test_demo_structure.py` runs to prove this entry point
cold-starts from an empty directory.

### Configuration options

Read from `check.py`'s argparse. There is exactly one flag.

| flag | default | what it does |
|---|---|---|
| `--quiet` | off | Suppresses the report. The exit code is the whole output: `0` if every check passed, `1` otherwise. |

Exit codes: **0** all checks passed · **1** at least one check failed.

---

## THE SHAPE TO LOOK FOR

Every line `[PASS]`, then the next command printed for you.

### Expected output — captured

**Captured on 2026-08-03, verbatim, running with no `ANTHROPIC_API_KEY` set.** This is
the keyless path, and it is real output rather than a description of one:

```text
$ uv run python demos/00_preflight/check.py
PREFLIGHT — the cheapest possible check that this checkout can spend

[FAIL] ANTHROPIC_API_KEY is set — ANTHROPIC_API_KEY is not set. Add ANTHROPIC_API_KEY=<your key> to .env (see .env.example).
       fix: cp .env.example .env, then add ANTHROPIC_API_KEY=<your key>. LANGSMITH_API_KEY is optional and can stay empty.
[FAIL] models reachable — not attempted — there is no key to call with
       fix: Set ANTHROPIC_API_KEY first; the offline checks below still ran.
[PASS] warehouse builds — warehouse.duckdb verified from seed 20260729
[PASS] gold set builds — 50 items in 10 clusters (5 per cluster — not independent trials)
[PASS] rule surface (offline, free) — rejects 6/6 rule-breaking queries, accepts 6/6 rule-honouring ones

cost of this preflight: est. $0.000000 over 0 call(s) (0 in, 0 out)

Fix the FAIL line(s) above and run this again. Nothing has been spent on a sweep yet.
```

Exit code was `1`. Read the two `[PASS]` lines under the failures: that is the check
earning its keep. A bad key did not hide the fact that the rest of the checkout is sound.

**The passing run is NOT captured here**, because capturing it requires a working key and
spending. What the code does on success, from `src/loopeng/preflight.py`: the two `models
reachable` lines become `[PASS]` and name the model id and the tokens each probe billed,
the cost line carries a non-zero `est.` figure, and the closing paragraph is replaced by
the two commands to run next — the smoke sweep, then `charts.py --reference=compare`.
Do not take the numbers on your own machine from anything written here.

The `--help` output, captured on the same day:

```text
$ uv run python demos/00_preflight/check.py --help
usage: check.py [-h] [--quiet]

Cheapest possible check that this checkout can spend.

options:
  -h, --help  show this help message and exit
  --quiet     Exit code only. For scripts and CI.
```

---

## Troubleshooting

**If the shape does not appear:** every `[FAIL]` line carries its own `fix:`. The ones
that come up:

- ***`ANTHROPIC_API_KEY is not set`*** — the exact text, captured above, is
  `ANTHROPIC_API_KEY is not set. Add ANTHROPIC_API_KEY=<your key> to .env (see
  .env.example).` **This is the same sentence every other entry point prints**, because
  they all render it from one function in `src/loopeng/settings.py`. A blank
  `ANTHROPIC_API_KEY=` line counts as absent, deliberately — see `_blank_is_absent` in
  that module.
- *the call was refused* with `AuthenticationError` — the key is wrong, revoked, or the
  account is unfunded. Nothing was spent on a sweep. The same triage runs inside the
  loops, so a bad key stops after **one** call rather than three.
- *the call was refused* with `BadRequestError` — the model rejected the request itself.
  That points at `src/loopeng/registry.py`, not at `.env`.
- ***`warehouse builds` fails*** — the fix on the line says it: delete `warehouse.duckdb`
  and re-run. It is generated from a seed, so nothing is lost.
- ***`gold set builds` fails*** — a question pattern stopped discriminating against this
  warehouse. That is a build gate refusing to ship an item that cannot tell a good
  configuration from a bad one. `src/loopeng/gold/build.py` says what the gates mean.
- ***`rule surface` fails*** — the verifier is not enforcing what it claims to, and the
  `fix:` line names the failing rules. This one is free to reproduce and is the check
  most worth reading twice.
- ***imports fail after a successful `uv sync`*** — the checkout is probably on an
  iCloud-synced path. `src/loopeng/env_guard.py` raises a named error at import rather
  than letting it surface as a confusing `ModuleNotFoundError` later. Move the checkout
  outside any synced directory.

---

## Limitations — what this stage does not show

- **It is not a loop and demonstrates nothing about loop engineering.** No retry, no
  verifier, no measurement. It is infrastructure for the four stages that follow.
- **A pass does not predict cost.** It proves each role answers one trivial request. It
  says nothing about whether a sweep stays inside its cap — that is the sweep's own
  projected-spend abort, in stage 04.
- **It does not check your rate-limit tier.** The concurrency defaults were chosen
  against ceilings measured on one account. A lower-tier account passes preflight and can
  still hit limits mid-sweep.
- **It does not check LangSmith.** Tracing is advisory and optional by design, so there
  is deliberately no check that would fail without it.
- **The two probe calls are minimal by construction**, so they exercise credentials and
  model access — not the prompts, not the verifiers, and not anything the workshop
  measures.

---

## Where to go next

| | |
|---|---|
| the deep-dive on this stage | [`ONBOARDING.md`](ONBOARDING.md) |
| the vocabulary everything else assumes | [`demos/README.md`](../README.md) |
| the whole project, installation, profiles and cost | [the root README](../../README.md) |
| a cloner's shortest path to a live chart | [root README §11.0](../../README.md#110--run-it-on-your-own-key) |
| **next stage** — the agent loop | [`01_agent_loop/`](../01_agent_loop/README.md) |

There is no previous stage; this is the first thing to run.
