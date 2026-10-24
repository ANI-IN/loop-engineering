# Demo walkthrough for Section 2: Verification loop

The code behind the demos of this section: the order of the graders, the syntax-tree guard, and
the retry cap, for every Structured Query Language (SQL) query the analyst sends.

> **Terms on this page**
>
> - **Verification loop**: Graders check each query and answer, and send failures back to the agent.
> - **Grader**: A check that passes or fails one stage of a run and says why.
> - **Reviewer**: An independent agent that reads the question, SQL, and result after the graders pass.
> - **Planted bug**: A defect switched on by a flag so a demo shows its failure every time.
>
> All terms: [glossary](../../docs/glossary.md).

## What this code does

Every query goes through the checker before it touches the warehouse. The static graders run first
(parse, statement policy, schema), then the cost grader and the personal data grader. Only if none
blocks does the read-only role run the original text, and the execution grader reads the result.
A grader's failure goes back to the analyst as feedback, until the retry cap ends the run
escalated. A write the database refuses is never feedback: the run ends escalated at once.

```mermaid
sequenceDiagram
    participant Analyst
    participant Checker
    participant Graders as Graders (parse, policy, schema, cost, personal data)
    participant Role as Read-only role
    participant Loop as Verification loop
    Analyst->>Checker: run_query(sql)
    Checker->>Graders: grade in order
    alt a grader blocks
        Graders-->>Analyst: the reason, as feedback
    else every grader passes
        Checker->>Role: run the original text
        alt the role refuses a write
            Role-->>Loop: refused write: the run ends escalated, no retry
        else rows
            Role-->>Checker: rows
            Checker-->>Analyst: result
        end
    end
    Analyst->>Loop: answer envelope
    Loop->>Loop: final answer grader
    alt fails and attempts are left
        Loop->>Analyst: "Verification failed": fix it
    else fails at the retry cap
        Loop-->>Loop: escalated, with the reasons
    end
```

## The code, explained

### platform/src/datapilot/loop2_verification/checker.py, lines 85-101

```python
# platform/src/datapilot/loop2_verification/checker.py (lines 85-101)
    def check(self, sql: str, *, question: str = "", export: bool = False) -> Checked:
        """Grade, then execute only if no grader blocked. A refused write is marked on the result,
        so the loop can end the run instead of sending the error back."""
        context = self._context(sql, question, export)
        checked = Checked()
        self._refused = None
        if not self._grade([*self.static, self.cost, self.personal], context, checked):
            checked.refused = self._refused
            return checked
        try:
            checked.result = self.executor.run(sql)
        except ExecutionError as error:
            context.extra["execution_error"] = error
            checked.refused = error if error.refused_write else None
        context.result = checked.result
        self._grade([self.execution], context, checked)
        return checked
```

The order is the design. Cheap checks on the text run first, and execution comes last. The cost
grader is not a security layer: it asks for an `EXPLAIN` plan only for what the syntax tree calls
one read-only SELECT, and reports "not applicable" for anything else. `_grade` stops at the first
blocking result, so the analyst gets one clear reason. The executor runs `sql` as written.

When the database refuses a write (SQLSTATE 25006 or 42501), `checked.refused` marks it. The loop
then stops the run guard, and the run ends escalated with no retry: a refused write is an attack or
a bug, not a mistake for the analyst to fix.

### platform/src/datapilot/loop2_verification/graders/statement_policy.py, lines 84-95

```python
# platform/src/datapilot/loop2_verification/graders/statement_policy.py (lines 84-95)
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
```

This is malicious SQL, layer 2. The root check stops a statement that is not a read. The walk over
every node stops a `DELETE` hidden in a common table expression under a `SELECT` root, which a
prefix check passes. With the naive guard (`BUG_NAIVE_GUARD`) on, a `startswith` check replaces
both the parse and the statement policy graders, and only the read-only transaction and the role's
grants are left to refuse the write.

### platform/src/datapilot/loop2_verification/loop.py, lines 364-369

```python
# platform/src/datapilot/loop2_verification/loop.py (lines 364-369)
            reasons = [f"{failure.grader}: {failure.reason}"]
            if not attempt_allowed(attempt + 1, self._cap):
                reasons.append(f"retry cap reached after {attempt} attempts")
                return self._outcome(
                    RunStatus.ESCALATED, envelope=envelope, reasons=reasons, attempts=attempt
                )
```

This is the retry cap. Before another attempt, `attempt_allowed` compares it with
`limits.max_retries` in `platform/packs/datapilot_us/pack.yaml`; at the cap the run ends escalated
with every reason. Below these lines, the run guard is checked before the feedback goes back, so a
kill switch or a spent budget wins over a retry. With the missing retry cap (`BUG_NO_RETRY_CAP`)
on, `attempt_allowed` always says yes.

## If you copy this into your repository

- Keep the order: text checks, then the cost plan, then execution, then the result check. Moving
  execution earlier lets a bad query cost money before anything stops it.
- Keep the guard on the syntax tree, with an allowlist of root types and a walk over every node. A
  prefix or keyword check misses statements hidden inside a read.
- Keep a database role that cannot write, as the layer after the guard, and run the original text.
- End the run on a refused write instead of retrying it; send only grader failures back as feedback.
- Keep the retry cap and the token budget as two separate stops; either one ends the run.
- Change the forbidden nodes, the denied functions, and the allowed schema to your database.
- Check it with the statements from the malicious SQL demo, and with a grader that always fails:
  the run must end escalated at the cap.
