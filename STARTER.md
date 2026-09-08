# The starter branch

Two functions have been removed. Everything that measures whether you have put them back
correctly is intact.

**`src/loopeng/agent/loop.py :: run_question` — Level 1.**
Ask the model, run the SQL, retry when it fails to EXECUTE. Terminate for a named
reason, and never raise on a model or SQL failure.

**`src/loopeng/verify/loop.py :: run_verified` — Level 2.**
The same generator with the verifiers around it, rejecting a query that RAN and broke
a declared rule.

## The exercise

```bash
uv sync
uv run pytest -q
```

76 tests fail. Make them pass.

**The tests are the specification**, and that is the honest version of "here is what to
build" — a written spec can disagree with the finished thing, and these cannot. Every
property they name exists on `main`, so if you want to know whether a behaviour is
required or incidental, the answer is in a test rather than in someone's memory.

Read the docstrings that were left behind before you start. They are the ARGUMENT for
the code rather than a description of it: `run_question`'s explains why the budget is
checked before the call and not after, which is the sort of thing you only get wrong
once.

## ruff will report 17 unused imports, and that is a hint

They are in the two hollowed modules, and every one of them is something the
implementation needs — `complete`, `render_prompt`, `run_sql`, `QueryTimeout`,
`triage_call_failure`, `extract_sql`, `declares_unbound_parameter`, `CallUsage`,
`spec_for`. Treat the list as a shopping list. It goes away when you use them.

## What was left alone, and why

Everything that MEASURES: the warehouse, the gold set, the verifiers, the classifier,
the charts, the sweep, and every guard in `tests/`. You cannot tell whether a loop works
without them, and telling whether it works is the entire subject — hollowing the
instruments too would make the exercise "write code that looks right", which is the
thing the loops exist to argue against.

## This branch is GENERATED, not maintained

It is produced from `main` by `scripts/make_starter.py`. A hand-maintained starter is
correct for about a week and then describes a system that no longer exists, which is the
defect this repository is about, arriving in the thing you clone first.

So do not fix a bug here. Fix it on `main` and regenerate.
