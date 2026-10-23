# Assignment 1: Agent loop. Specification

The full requirements for Assignment 1: Agent loop; the [README](README.md) gives the story and the
steps.

## Inputs

- The complete class system for Section 1: Agent loop, with four marked extension points in
  `platform/src/datapilot/loop1_agent/extension.py`, listed in [starter/README.md](starter/README.md).
- The seeded warehouse, including the two near-identical product names "Alpine Trek 45L Backpack"
  and "Alpine Trek 45 L Backpack".
- Read-only: the frozen contracts in `platform/src/datapilot/contracts/` and
  `platform/packs/datapilot_us/pack.yaml`.

## Files you must produce

| Path | What it holds |
|---|---|
| `platform/src/datapilot/loop1_agent/extension.py` | `lookup_values`, `lookup_tools`, `WORKING_METHOD`, and `with_matches`, at the extension points `agent-loop-1` to `agent-loop-4` |

Keep the names, types, and signatures the starter gives: the check calls them.

## Requirements

Deterministic, checked against the real warehouse with no model call; each must pass every run:

1. `lookup_values` maps the misspelled wording "Cascde Lyne trail runner" to the stored product
   "Cascade Line Trail Runner".
2. It maps the informal wording "basin haven trail runners" to "Basin Haven Trail Runner".
3. It maps the informal category wording "trail running shoes" to the category "Trail Runners".
4. For "Alpine Trek 45 litre backpack" it returns the two near-identical names as its top two
   candidates and marks the lookup ambiguous.
5. It returns between one and `MAX_CANDIDATES` candidates (at most 10), each an exact stored value,
   never a whole column.
6. It reads the warehouse only through `warehouse.url`, the read-only agent role: the module names
   neither the owner role nor the application role.
7. `lookup_tools` returns a tool named `find_exact_values`, with the arguments `kind` and
   `wording`, that appends each lookup to the run's log, and `WORKING_METHOD` names the tool.

Model-dependent, run live through the api and the workers on the real model; each passes on 2 of 3
runs (two runs, and a third only when the first two disagree):

8. "What is the list price, in dollars, of the Cascde Lyne trail runner?" answers with the gold
   result, the lookup is called before the first `run_query`, and the stored name is in
   `assumptions`.
9. The same for "What is the list price, in dollars, of the trail runner from our Basin Haven
   line?".
10. The same for "How many products do we list under trail running shoes?".
11. "What is the list price, in dollars, of the Alpine Trek 45 litre backpack?" ends with status
    `needs_clarification` and a `clarifying_question` that names both stored names exactly.

The capability exists in no class code path: the course build's boundary test keeps every
extension point inert on the class branch, so the unchanged starter fails this check.

## Live check

`make check-assignment NAME=agent-loop` brings up the real stack, checks requirements 1 to 7, prints
"This check makes live model calls, about N cents, and stops at 1.00 dollar" with its estimate, checks your OpenAI key, and
then runs requirements 8 to 11 live. Each live run prints its LangSmith trace link and its live
stamp (run id, start time in Coordinated Universal Time (UTC), live session). At the end it prints
the actual tokens and cost from the spend ledger. If the check reaches its spend cap of 1.00 dollar (`assignments.check_cap_usd` in pack.yaml), it stops cleanly: it starts no new run, every requirement it did not reach reads NOT RUN, and it exits 2. A missing or rejected key stops the check with
"Live checks need your OpenAI key from the operations team"; it never falls back to anything
offline. When requirement 7 fails, the live requirements do not run, so nothing is spent on a
starter that cannot pass them. The command exits 0 when every line reads PASS, 1 on any FAIL, and
2 when it stopped.

Agent runs: 8 always (4 questions, 2 runs each), and at most 4 more.

## Evidence to hand in

Nothing is submitted, and there is no hidden grader. Bring these to the Thursday review:

- the output of your live check, with its trace links;
- one design choice you made, such as how close two names must be to count as a tie, and why.

## Limits

- Every model call records its spend in the build-wide ledger under the activity "assignment";
  `make spend` shows the total.
- Each run stays within `budgets.tokens_per_run` in `platform/packs/datapilot_us/pack.yaml`.
- The row cap `limits.row_cap` and the retry cap `limits.max_retries` in the same file still apply.
