# Section 2: Verification loop. Concepts

Reading time: about 9 minutes.

## The problem

**Illustrative scenario.** Marcus owns the analytics platform at Harbor & Pine Outfitters. One
product name in the catalogue reads like an instruction to delete old orders. The analyst sees it
in a sample row and writes the Structured Query Language (SQL) `SELECT 1; DELETE FROM orders`. The guard checks that the text starts
with "select" and passes it. Only the read-only role refuses the write.

The same week, a check fails on every attempt and the agent retries until the bill climbs. Then
the fiscal year 2025 revenue answer passes every check, turns the checklist green, and is still
wrong.

> **Terms on this page**
>
> - **Verification loop**: Graders check each query and answer, and send failures back to the agent.
> - **Grader**: A check that passes or fails one stage of a run and says why.
> - **Reviewer**: An independent agent that reads the question, SQL, and result after the graders pass.
> - **Gold SQL**: The query an analyst wrote by hand that gives the right answer.
> - **Human approval**: A person approves or rejects a held action before it runs.
>
> All terms: [glossary](../docs/glossary.md).

## The idea in one sentence

Deterministic layers decide whether a query is safe and well formed, caps decide when the loop
stops, and an independent reviewer adds judgement only after every grader has passed.

## How it works

The tempting question is: if every grader passes, is the answer right? No. Graders prove the query
is safe and well formed. They cannot prove it means what the business means. That gap is what the
last demo of this section shows.

![Two stages of checks. Stage 1: each query passes the parse, statement policy, schema, cost, and personal data graders, then the read-only executor and the execution grader; a block sends feedback to the analyst, personal data goes to a person, and a write the database refuses ends the run at once. Stage 2: the answer envelope's query runs through graders 1 to 6 again, then the final-answer grader, then the reviewer agent; a failure retries, up to 3 attempts. A red band on top: the stop before every model call and every tool call](diagrams/verification-layers.svg)

*Notice the order: the reviewer only ever sees an answer that every grader passed, and the stop before the model call can end the run at any point.*

### 1) Defense in layers

The syntax-tree guard is an allowlist. It accepts exactly one statement with a SELECT or
set-operation root, no write node anywhere, no denied function, and tables in the warehouse
schema only. The executor runs the original SQL text, never SQL regenerated from the tree. Below
the guard, the agent role is read-only and every transaction runs `SET TRANSACTION READ ONLY`, so a
write fails with SQLSTATE 25006; with read-only switched off, the role's grants refuse it with
SQLSTATE 42501. The cost grader is not a security layer: it estimates read-only SELECT statements
only and reports anything else as not applicable, so a write that gets past the guard reaches the
read-only transaction. A refused write is not feedback: the run ends at once as escalated, and the
analyst never gets another turn to try a different write. A statement timeout,
`limits.statement_timeout_ms` in `platform/packs/datapilot_us/pack.yaml`, ends slow queries.

The tree cannot see SQL hidden in string literals, such as `dblink` or `query_to_xml`. Statements
such as `DO` and `CALL` parse to an opaque command. That is why the role stays mandatory under the
guard. The naive guard (`BUG_NAIVE_GUARD`) shows the gap. Each layer assumes the one above it
fails.

### 2) Graders send reasons back

Graders run at three stages, the `Stage` values in `platform/src/datapilot/contracts/grading.py`:
pre-execution, post-execution, and final answer. Each returns a pass or fail, a reason, a
severity, and feedback for the agent. Block stops the query; route sends it to human approval.
The seven graders, one file each in `platform/src/datapilot/loop2_verification/graders/`, are:
parse (exactly one statement), statement policy, schema, cost, personal data, execution, and final
answer. A failure the agent can read is a failure it
can fix.

### 3) Caps end the loop

A grader failure sends the run back to the analyst, which is the loop. A refused write is the one
exception: it ends the run escalated and never counts as a retry. The retry cap,
`limits.max_retries` in `pack.yaml`, is 3; after it the run ends escalated with every reason
attached. Each run also has `limits.model_call_limit` of 12 model calls and
`limits.tool_call_limit` of 16 tool calls. The missing retry cap (`BUG_NO_RETRY_CAP`) shows a run
that loops while its cost climbs. The missing cost guard (`BUG_NO_COST_GUARD`) shows a cartesian
join running to the timeout, where the `cost_guard` thresholds would reject it at once. Every
loop needs a stop that is not the model's choice.

### 4) The reviewer reads after the graders

The reviewer is an independent agent. It runs only after every deterministic grader has passed.
It sees the question, the final SQL, the result preview, and the active knowledge version, and
nothing else. It returns a `ReviewVerdict`: approve, or concern with reasons. It never overrides a
grader. A concern goes back to the analyst once, within the retry cap. If the concern persists,
the run holds for human approval. You switch it with `agents.reviewer.enabled` in `pack.yaml`.
Judgement goes after the deterministic checks, never instead of them.

### Before and after

Before: a startswith check passes stacked statements, a failing check loops until someone
notices the bill, and a green checklist reads as a correct answer.

After: the guard stops stacked statements before execution, the run escalates after the retry cap
with its reasons, and the green checklist sits beside a gold check that can still fail.

## How DataPilot does it

The guard lives in `platform/src/datapilot/loop2_verification/graders/statement_policy.py`. These
lines check the root, walk every node of the parsed tree against the forbidden nodes and the
denied functions, and keep every table inside the allowed schema:

```python
# platform/src/datapilot/loop2_verification/graders/statement_policy.py (lines 80-107)
    def check(self, context: GraderContext) -> GraderResult:
        tree = parse_single(context.sql or "")
        if tree is None:
            return blocked(self.name, "not one parseable statement", "Send one SELECT statement.")
        root = tree.unnest() if isinstance(tree, exp.Subquery) else tree
        if not isinstance(root, exp.Select | exp.SetOperation):
            kind = type(root).__name__.upper()
            return blocked(self.name, f"{kind} is not allowed", "Only SELECT queries may run.")
        for node in tree.walk():
            if isinstance(node, FORBIDDEN_NODES):
                kind = type(node).__name__.upper()
                return blocked(
                    self.name,
                    f"{kind} inside the query",
                    f"The query contains {kind}; only reads are allowed, including inside CTEs.",
                )
            if isinstance(node, exp.Func) and _denied(function_name(node)):
                fn = function_name(node)
                return blocked(self.name, f"function {fn} is denied", f"Do not call {fn}.")
        for table in base_tables(tree):
            if (table.db and table.db.lower() != self.schema) or table.catalog:
                where = ".".join(p for p in (table.catalog, table.db) if p)
                return blocked(
                    self.name,
                    f"table outside the {self.schema} schema: {where}.{table.name}",
                    f"Read only tables in the {self.schema} schema (list_tables shows them).",
                )
        return passed(self.name, "a read-only SELECT in the allowed schema")
```

Every `blocked` result carries feedback the analyst can act on. The naive guard in the same file is
a single `startswith` check, swapped in by `guard_graders` when `BUG_NAIVE_GUARD` is on. The retry
cap is `attempt_allowed` in `platform/src/datapilot/loop2_verification/limits.py`: an attempt may
start only while its number is at most `limits.max_retries`.
The reviewer's output contract is `ReviewVerdict` in
`platform/src/datapilot/contracts/agents.py`.

## What we measured

| Measure | Reviewer on | Reviewer off |
|---|---|---|
| Tokens per question | Not run | Not run |
| Latency per question | Not run | Not run |
| Reviewer approves the wrong spine answer | Not run | Not applicable |
<!-- provisional: calibration fills this table from real runs with the reviewer on and off -->

The class runs and the calibration runs will be listed on the
[Section 2 evidence page](../docs/evidence/section-2-verification-loop.md).

## When it helps, and when it does not

It helps when:

- Text in the data tries to steer the agent toward a write.
- A query would scan a cartesian join or return far more rows than the question needs.
- A check fails for a reason the agent can act on, such as a table outside the allowed schema.

It does not help when:

- The query is safe and well formed but applies the wrong business rule.
- The reviewer shares the analyst's blind spot, such as not knowing the fiscal year.
- A grader keeps failing for a reason the agent cannot change.

## Key takeaways

- Stack deterministic layers, each built as if the one above it fails, with the read-only role last.
- Send every failure back as a reason, and end the loop with a cap the model does not control.
- A green checklist means safe and well formed, not right; judgement comes after the graders.

## Check your understanding

1. Why does the read-only role stay mandatory when the syntax-tree guard exists?

   <details><summary>Answer</summary>

   The tree cannot see SQL inside string literals, and some statements parse to an opaque command.
   The role refuses every write, whatever the guard missed.

   </details>

2. Why does the executor run the original SQL text, not SQL regenerated from the tree?

   <details><summary>Answer</summary>

   Regenerated SQL can change meaning. Running the text the guard checked means the guard's verdict
   applies to exactly what executes.

   </details>

3. What happens when a grader fails on every attempt?

   <details><summary>Answer</summary>

   Each failure returns its reason to the analyst. After `limits.max_retries` attempts the run ends
   escalated with every reason attached, so cost stops climbing.

   </details>

4. Why may the reviewer never pass a failed grader?

   <details><summary>Answer</summary>

   A grader is deterministic and testable; the reviewer is a model. Letting judgement overrule a
   check would make the safety layers depend on a model's choice.

   </details>

## Further reading

- [Section 2 reading list](post-class-reading/README.md)
- [Semantic Evaluation for Text-to-SQL with Distilled Test Suites](https://arxiv.org/abs/2010.02840),
  on why one matching database is not proof of a correct query.

## Sources

- Source 1: Semantic Evaluation for Text-to-SQL with Distilled Test Suites, <https://arxiv.org/abs/2010.02840>, Ruiqi Zhong et al., 2020-10-06
