---
name: Bug report
about: Something behaves differently from what the runbook says it will
title: ''
labels: bug
assignees: ''
---

## What you ran

The exact command, please — most of this project's entry points take flags that
change what happens.

```bash

```

## What happened

Paste the output. If a test failed, the whole failure block rather than the last
line.

## What you expected

Each stage's runbook (`demos/0N_*/README.md`) has an **Expected SHAPE** section.
If what you saw is covered there under "what to say if it does not appear", that
may be intended behaviour rather than a bug — worth checking first.

## Environment

- OS and architecture:
- `uv run python -V`:
- `git rev-parse --short HEAD`:

## Checks

- [ ] `uv run pytest -q` — result:
- [ ] `uv run ruff check .` — result:
- [ ] `uv run python tools/lint_no_numbers.py` — result:
- [ ] The checkout is **not** on a cloud-synced path (iCloud Drive, Dropbox). The
      `env_guard` failure mode looks like a mysterious import error.
