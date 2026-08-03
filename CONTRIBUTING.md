# Contributing

Thanks for looking. This is a workshop application rather than a library, so the
bar for a change is *"does this make the argument clearer or the evidence
stronger"* rather than *"does this add a feature"*.

## Getting set up

```bash
git clone https://github.com/ANI-IN/loop-engineering.git
cd loop-engineering
uv sync
uv run pytest -q
```

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/). Nothing else — no
Docker, no database server, no API key.

**Put the checkout somewhere your cloud storage does not sync.** iCloud Drive
evicts files it thinks are cold, and an evicted `.pth` file breaks the editable
install in a way that looks like a mysterious import error. A guard catches this
at import and names the fix.

## Before you open a pull request

Run everything CI runs:

```bash
uv run ruff check .
uv run python tools/lint_no_numbers.py
uv run pytest -q
uv run python tools/render_readme_charts.py "$(mktemp -d)"
uv run python tools/sync_hf.py --dry-run
```

The offline suite needs no key, makes no network call, and costs nothing. If a
change makes it need any of those, that is the change to reconsider.

**The chart step renders to a scratch directory and does not diff the pixels.**
It used to read `render_readme_charts.py && git diff --exit-code -- assets/`,
which cannot work and was removed from CI for that reason: matplotlib rasterises
text through FreeType, so a Linux runner does not reproduce the bytes a macOS
machine committed, and the step failed for a reason unrelated to the images being
wrong. What this command checks is that rendering still *runs*. Whether the
committed images are *current* is checked by `tests/test_readme_charts.py`, which
compares manifest hashes rather than pixels and is therefore platform-independent.

## The rules this codebase actually enforces

These are not style preferences. Each one is a test that will fail your build,
and each exists because the corresponding mistake was made here at least once.

**No typed numbers in the modules that render to a room.**
`tools/lint_no_numbers.py` bans numeric literals in the eleven modules that build
what an audience reads, because a typed number is indistinguishable from a
measured one once it is on a projector. Every number must come from a `Metric`,
which carries its own `n`.

Genuine layout geometry — a figure coordinate, a string truncation width, a slider
step — is exempt with a trailing `# layout` marker on that line. The rule counts
and prints how many exemptions exist, so the count cannot grow quietly. Do not
use the marker to smuggle a measurement past it.

**A declared lint target must exist.** The rule once pointed at a path that had
been deleted; it scanned nothing, found nothing, and passed. An unresolvable
target is now a build failure.

**No numbers in any README or diagram.** Results do not exist until the session
runs. Anything quoted in advance is a number somebody will read as though it were
measured. Numbers live in the app, stamped with the time they were computed, and
in the generated images, which carry their measurement date inside the image.

**Demos stay thin.** No loop logic in `demos/` — it lives in `src/loopeng/`. A
demo file wires arguments, calls in, and renders. Over a hundred lines fails the
build. The loops are nested rather than parallel, so a second copy in a demo file
is a second place for one to drift.

**Every demo cold-starts.** No stage may depend on another having run. A test
executes each entry point from an empty working directory.

**Every declared business rule has a check and two probes.** Adding a rule to
`src/loopeng/warehouse/semantic_model.yaml` without a corresponding entry in
`RULE_CHECKS` raises `UnenforcedRule` at import and fails the build. That is the
defect this whole project is about, so it is not allowed to happen here. Each rule
also needs a violating probe *and* a correct-but-unusual probe — a verifier that
rejects everything scores perfectly on the first alone.

**The verifier never sees the gold answer.** `VerifyContext` has no field for it
and `build_context()` takes no such argument. Do not add one. Judgement against
gold happens afterwards, on the finished run.

**`assets/` is generated.** Never hand-edit or hand-place an image. It is written
only by `tools/render_readme_charts.py`, from `results/reference/`.

If you change anything under `results/reference/`, re-render and commit both the
images and `assets/manifest.json`. The manifest records the source hashes, so a
test will tell you the images are stale — on any platform, which matters because
re-rendering is byte-identical *within* an environment but not across one.
Do not expect your PNGs to match the committed ones byte-for-byte if you are on a
different OS; that is expected and the test suite accounts for it.

**Diagrams are duplicated deliberately and must stay identical.** Each level's
Mermaid block appears in both the README and its stage runbook. A test asserts
they match byte-for-byte.

## Adding a business rule, end to end

1. Declare it in `semantic_model.yaml` with a `statement` and `applies_to`.
2. Add a check to `RULE_CHECKS` in `src/loopeng/verify/verifiers.py`, reading the
   sqlglot AST rather than the query text.
3. Add both probes in `src/loopeng/verify/governance.py` and
   `src/loopeng/verify/probes.py`.
4. Add or extend a gold pattern that exercises it, with its naive variant.
5. Run the suite. The governance gate will tell you if you missed a step.

## Tests

Write the test that would have caught the bug, and say in its docstring what
actually went wrong. Several tests here read like short incident reports, and
that is on purpose: a test whose name explains the failure mode is worth more
than three that assert the same thing.

Live tests carry `@pytest.mark.live` and are deselected by default. They cost
real money. Do not add one unless the thing being tested genuinely cannot be
observed offline.

## Commits

Plain, lower-case, imperative summaries describing the change and why. Bodies are
welcome and encouraged for anything non-obvious — most of the reasoning in this
repository lives in commit messages and module docstrings rather than in a
separate design document.

## Reporting a security issue

See [SECURITY.md](SECURITY.md). Do not open a public issue for anything involving
credentials or unbounded spend.
