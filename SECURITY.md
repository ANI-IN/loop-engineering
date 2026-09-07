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

## This project publishes nothing, and that is now the whole answer

**Two controls used to be described here and both are gone, because what they
protected is gone.** There is no public exhibit and no deployment sync in this
repository: the exhibit view, the Space sync tool, the `deploy/` tree and their tests
were all removed. Nothing here pushes anything anywhere.

That is worth stating rather than quietly dropping, because this file previously
asserted two specific protections — a test spying on the model-client constructor,
and a publish step that refused forbidden files — and pointed at the tests enforcing
them. Both citations resolved to nothing. A security document naming a boundary that
does not exist is worse than one that names no boundary at all: a reader audits the
claim, finds a plausible sentence, and stops.

**If you add a deployment path, neither of those controls comes with it.** They would
have to be rebuilt, and the reasoning behind them is the part worth keeping:

- A public page holding a working API key means unbounded spend by strangers, so the
  guarantee wanted there is structural — *no client is ever constructed* — rather
  than quantitative.
- A publish step should **assert over everything staged** rather than copy a list of
  allowed files. Copying only the right things is not the same as refusing the wrong
  ones, because a filter that misses is silent.

## What does hold in this build

| control | enforced by |
|---|---|
| No credential has ever been committed | `.env` is gitignored; a test scans **every blob in every reachable commit**, not just HEAD |
| A key cannot be printed by accident | settings load once, frozen, with `SecretStr` |
| The offline suite needs no key and makes no network call | it runs in CI with no secret available, and the live tests are a marker that is deselected by default |
| The agent cannot write to the warehouse | the connection is opened read-only and the database enforces it, rather than a convention doing so |
| Nothing runs from a cloud-synced path that breaks imports | `src/loopeng/env_guard.py`, which refuses at startup |

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
> variables will not change that; they are inert.
>
> There is no longer a safe thing to host instead. This paragraph used to say "host
> the exhibit" — a frozen view that made no model calls at all, enforced by a test
> spying on the client constructor. That view and that test were both removed, so the
> honest advice is shorter: **do not host any view from this repository publicly.**
> If you need one, put it behind authentication you control and set a spending limit
> in the provider's console, which is enforcement outside this codebase and therefore
> actually enforcement.
>
> This section previously described the three conditions below as though they
> gated something, with the caveat at the bottom. That ordering is how a reader
> ends up trusting a control that does not exist, which is the exact failure this
> project is about — so the caveat is now the heading.

**What `live_mode.py` would do, if it were wired.** Recorded because the design is
sound and the module is worth finishing, not because any of it is in force:

1. `LOOPENG_LIVE=1` set explicitly. A key alone would not enable it — a key can
   arrive for a dozen reasons that are not "please spend it".
2. A working model credential. Note that `live_mode` reads `ANTHROPIC_API_KEY`, which under the current model policy is the JUDGE key and gates nothing — another reason the module is not wired.
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
