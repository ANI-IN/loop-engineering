## What this changes, and why

Briefly. The reasoning matters more than the diff — most of the explanation in
this repository lives in commit messages and module docstrings.

## Checks

Everything CI runs:

- [ ] `uv run ruff check .`
- [ ] `uv run python tools/lint_no_numbers.py`
- [ ] `uv run pytest -q`
- [ ] `uv run python tools/sync_hf.py --dry-run`

## If this touches any of these, say so

- [ ] **A business rule** — declared in `semantic_model.yaml`, with a check in
      `RULE_CHECKS` and **both** probes (violating, and correct-but-unusual).
- [ ] **Anything that renders to a room** — no typed numbers. Genuine layout
      geometry carries a `# layout` marker on the line.
- [ ] **`results/reference/`** — images re-rendered and `assets/manifest.json`
      committed alongside.
- [ ] **A Mermaid diagram** — the copies in the README and the stage runbook must
      stay byte-identical; a test asserts it.
- [ ] **`deploy/hf/` or the exhibit** — `tests/test_exhibit.py` must still pass.
      It spies on the model client constructor and is the security boundary for a
      public page.
- [ ] **A new dependency** — is it needed at runtime, or is it tooling? Tooling
      goes in the dev group so it never reaches the venue machine or the Space.

## Anything you were unsure about

Genuinely useful. Say what you considered and rejected.
