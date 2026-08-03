# Security Policy

## Reporting a vulnerability

Report privately through GitHub's [Report a
vulnerability](https://github.com/ANI-IN/loop-engineering/security/advisories/new)
form rather than by opening a public issue.

Please include what you did, what happened, and what you expected. Expect an
acknowledgement within a week.

## What this project is, and what that means for its threat model

This is a workshop application. It runs from a laptop in front of a room. It is
not a service, it has no users, it stores no personal data, and it is not
intended for production use. The realistic risks are therefore narrow, and they
are mostly about **spending money** and **leaking credentials** rather than about
compromising a system.

## The two controls that actually matter

### 1. The public exhibit constructs no model client

`deploy/hf/` is a frozen exhibit intended to be published publicly. A public page
holding a working API key means unbounded spend by strangers, so the guarantee
here is structural rather than quantitative: **no `anthropic.Anthropic` is ever
constructed** on that path.

That is enforced by a test which spies on the constructor and asserts none is
built (`tests/test_exhibit.py`). **That test is the security boundary.** If you
change anything under `src/loopeng/views/exhibit.py` or `deploy/hf/`, that test
passing is the thing to check.

The exhibit profile independently has no model roles, no cells, and a zero spend
cap, so any attempt to run a cell refuses immediately.

### 2. The Space sync refuses rather than filters

`tools/sync_hf.py` will not publish:

| | why |
|---|---|
| `.env` | credentials |
| `results/sweep/`, `results/ablation/` | live cell output, which on a public page renders as though it had just been computed |
| any `*.duckdb` | generated data; the Space rebuilds it from the seed and asserts a checksum |

These are **assertions over everything staged**, not a copy list. Copying only the
right things is not the same as refusing the wrong ones: a filter that misses is
silent. See `tests/test_sync_hf.py`, which plants each forbidden item and asserts
the push aborts.

## Credentials

- Real values live in `.env`, which is gitignored. `.env.example` holds names
  only and is committed.
- Settings load once, frozen, with `SecretStr`, so a key cannot be printed by
  accident.
- **No credential has ever been committed to this repository.** Verified with
  `git log --all --full-history -- .env` and a scan of every blob in history for
  key-shaped strings.

If you believe a key has been exposed, **rotate it first**. Rewriting git history
does not reliably remove a secret from a hosting provider's servers.

## Running a hosted instance that *can* call models

> ### There is no spend guard in this build. Do not rely on one.
>
> `src/loopeng/views/live_mode.py` implements a ceiling, and it is tested. **No
> view calls it.** `LiveBudget` is never constructed, `read_config()` is never
> invoked by any entry point, and `LOOPENG_LIVE` / `LOOPENG_LIVE_CEILING_USD` are
> read by nothing at runtime.
>
> So if you host an instance with a working key and a view that spends, **nothing
> in this repository caps what strangers can spend on it.** Setting those two
> variables will not change that; they are inert. The protection you get from this
> project is that the **exhibit makes no model calls at all** — enforced
> structurally, by a test that spies on the `anthropic.Anthropic` constructor and
> fails if one is ever built (`tests/test_exhibit.py`). That test is the real
> boundary, and it is the reason a public Space here cannot spend anyone's money.
>
> **Host the exhibit. Do not host a live view publicly.** If you need one, put it
> behind authentication you control and set a spending limit in the Anthropic
> console, which is enforcement outside this codebase and therefore actually
> enforcement.
>
> This section previously described the three conditions below as though they
> gated something, with the caveat at the bottom. That ordering is how a reader
> ends up trusting a control that does not exist, which is the exact failure this
> project is about — so the caveat is now the heading.

**What `live_mode.py` would do, if it were wired.** Recorded because the design is
sound and the module is worth finishing, not because any of it is in force:

1. `LOOPENG_LIVE=1` set explicitly. A key alone would not enable it — a key can
   arrive for a dozen reasons that are not "please spend it".
2. `ANTHROPIC_API_KEY` set to something real.
3. `LOOPENG_LIVE_CEILING_USD` set. Live with no ceiling is not a configuration it
   accepts; it refuses rather than defaulting to a number nobody chose.

Even wired, the ceiling would turn unbounded into capped, which is not the same as
safe: anyone with the link can burn the cap, repeatedly, and a restart resets it.

## Data

The warehouse is generated from a fixed seed. It contains no real data about
anyone. The queue stores whatever questions people type into it during a session,
in a local DuckDB file that is gitignored.

## Dependencies

Pinned in `uv.lock`. CI installs with `uv sync --locked` on every push, so a
resolution that drifts fails the build rather than arriving silently.
