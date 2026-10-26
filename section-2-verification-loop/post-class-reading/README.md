# Module: Loop Engineering - Reading list for Section 2: Verification loop

Three readings that go past the class time of the verification loop. Each page sums up one primary
source in plain words and shows how to apply it to your own repository. Each page takes a few
minutes; the reading time in the table is for the full source, at 200 words a minute, rounded up
to 5 minutes.

> **Terms on this page**
>
> - **Verification loop**: Graders check each query and answer, and send failures back to the agent.
> - **Grader**: A check that passes or fails one stage of a run and says why.

## Readings

| Reading | Reading time | Why read it |
|---|---|---|
| [01 Why one database is not proof](01-distilled-test-suites.md) | 45 minutes | Why a query that matches on one database can still be wrong |
| [02 Least privilege and allow-lists](02-sql-injection-prevention.md) | 15 minutes | Why the database role is the boundary, and the parser is not |
| [03 Error codes as feedback](03-postgresql-error-codes.md) | 10 minutes | How to turn a database error into a reason the agent can act on |

## How to use these

- Read the first one before Section 4: Hill-climbing loop; its evaluator rests on the same idea.
- Read the second and third together: one says which layer refuses, the other how it says so.
- After each reading, do the first step of its "Apply it to your repository" list on a database
  you work with.
