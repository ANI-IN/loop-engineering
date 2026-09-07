"""Generate the `starter` branch from `main`, so it cannot drift.

A workshop starter branch is normally hand-maintained: someone copies the repository,
deletes the interesting parts, and it is correct for about a week. Then `main` moves and
the starter describes a system that no longer exists — a checkout that teaches the wrong
shape, which is the defect this entire repository is about, applied to the thing an
attendee clones first.

**So the starter is not maintained. It is regenerated.** This script takes the current
`main`, replaces the body of each function listed in `HOLLOWED` with a
`NotImplementedError` that keeps the docstring, and leaves everything else untouched:
the tests, the warehouse, the gold set, the charts, the guards. The exercise is to make
the suite green, and the tests are the specification — which is the honest version of
"here is what to build", because it cannot disagree with what the finished thing does.

WHAT IS DELIBERATELY LEFT INTACT

Everything that MEASURES. An attendee who cannot run the offline suite, build the
warehouse, or render a chart has no way to tell whether their loop works, and telling
whether it works is the whole subject. Hollowing the instruments as well would make the
exercise "write code that looks right", which is what the loops exist to argue against.

    uv run python scripts/make_starter.py --check    # what would change, no writes
    uv run python scripts/make_starter.py            # write the files
"""

import argparse
import ast
import subprocess
import sys
from pathlib import Path

# (module, qualified function name). The two loop bodies, and nothing else.
#
# Kept small on purpose. Every entry here is a place the starter can disagree with main
# about what the signature is, so the smallest set that still makes the exercise real is
# the right one — and the exercise is the loops, not the plumbing around them.
HOLLOWED = (
    ("src/loopeng/agent/loop.py", "run_question"),
    ("src/loopeng/verify/loop.py", "run_verified"),
)

BODY = '''    raise NotImplementedError(
        "This is the starter branch. Implement {name} until the suite is green.\\n"
        "The tests are the specification: `uv run pytest -q` names every property it "
        "must have, and every one of them exists on `main`.\\n"
        "Nothing that MEASURES has been removed — the warehouse, the gold set, the "
        "verifiers, the charts and every guard are intact, because telling whether "
        "your loop works is the subject rather than a convenience."
    )
'''


def hollow(source: str, function: str) -> str:
    """Replace one function's body, keeping its signature and docstring.

    The docstring stays because it is the argument for the code, not a description of
    it — `run_question`'s explains why the budget is checked BEFORE the call rather than
    after, which is the part worth reading before writing the loop.
    """
    tree = ast.parse(source)
    target = next(
        (node for node in tree.body
         if isinstance(node, ast.FunctionDef) and node.name == function),
        None,
    )
    if target is None:
        raise LookupError(f"{function} is not a module-level function any more")

    lines = source.splitlines(keepends=True)
    first = target.body[0]
    keep_docstring = (isinstance(first, ast.Expr)
                      and isinstance(first.value, ast.Constant)
                      and isinstance(first.value.value, str))
    body_starts_at = (first.end_lineno if keep_docstring else first.lineno - 1)
    return "".join(
        lines[: body_starts_at]
        + [BODY.replace("{name}", function)]
        + lines[target.end_lineno:]
    )


STARTER_README = """# The starter branch

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
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true",
                        help="Report what would change and write nothing.")
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args(argv)

    for relative, function in HOLLOWED:
        path = args.root / relative
        source = path.read_text(encoding="utf-8")
        try:
            hollowed = hollow(source, function)
        except LookupError as exc:
            print(f"REFUSING: {exc}")
            print("  The starter is generated from main, so a rename here means the "
                  "generator is out of date rather than the branch.")
            return 2
        before, after = len(source.splitlines()), len(hollowed.splitlines())
        print(f"{relative} :: {function}  {before} -> {after} lines")
        if not args.check:
            path.write_text(hollowed, encoding="utf-8")

    if args.check:
        print("\n--check: nothing written")
        return 0

    (args.root / "STARTER.md").write_text(STARTER_README, encoding="utf-8")
    print("wrote STARTER.md")

    # The exercise is "make the suite green", so it has to be RED first, and red in the
    # places the exercise is about rather than because the checkout is broken.
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--no-header", "-x",
         "tests/test_agent_loop.py"],
        cwd=args.root, capture_output=True, text=True,
    )
    if result.returncode == 0:
        print("\nREFUSING: the suite passes with the loops removed, which means the "
              "tests do not exercise them. That is a finding about the tests.")
        return 3
    print("\nstarter generated. tests/test_agent_loop.py fails, as it must.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
