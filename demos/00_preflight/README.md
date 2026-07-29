# 00 · Preflight

```bash
uv run python demos/00_preflight/check.py
```

Numbered 00 because it runs before the loops. It is **not a loop level** — see
[the numbering note](../README.md).

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

## THE SHAPE TO LOOK FOR

Every line `[PASS]`, then the next command printed for you.

**If the shape does not appear:** every `[FAIL]` line carries its own `fix:`. The two
that come up:

- *the call was refused* with `AuthenticationError` — the key is wrong, revoked, or the
  account is unfunded. Nothing was spent on a sweep. The same triage runs inside the
  loops, so a bad key stops after **one** call rather than three.
- *the call was refused* with `BadRequestError` — the model rejected the request itself.
  That points at `src/loopeng/registry.py`, not at `.env`.
