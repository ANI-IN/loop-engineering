# [SQL Injection Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html) <!-- check-style: allow SC33 the source title is quoted as published -->

Reading time: about 15 minutes.
Source: OWASP Cheat Sheet Series, [SQL Injection Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html), n.d.

> **Terms on this page**
>
> - **Verification loop**: Graders check each query and answer, and send failures back to the agent.
> - **Planted bug**: A defect switched on by a flag so a demo shows its failure every time.

## Why it matters

A text-to-Structured Query Language (SQL) agent is the extreme case of the problem this cheat sheet
was written for: not one user value inside a query, but the whole query written from text you do
not control. The usual primary defense, a prepared statement, does not apply when the model writes
the statement. What remains are the two defenses this cheat sheet ranks next: allow-list
validation and least privilege. DataPilot uses both, in that order.

## Three key ideas

1. **Allow-list what you cannot parameterize.** For parts of a query that "can't use bind
   variables, such as table names, column names", the sheet says "input validation or query
   redesign is the most appropriate defense". DataPilot's syntax-tree guard is that allow-list,
   applied to the whole statement: one SELECT, no write node, tables in one schema.

2. **Least privilege limits the damage.** "To minimize the potential damage of a successful SQL
   injection attack, you should minimize the privileges assigned to every database account".
   Start from what the account needs, "rather than trying to figure out what access rights you
   need to take away". DataPilot's agent role has `SELECT` on the warehouse schema and nothing else
   (`platform/ops/sql/roles.sql`).

3. **Never the owner account.** "Make sure that accounts that only need read access are only
   granted read access to the tables they need access to." The sheet also warns against one
   shared owner account for every application. DataPilot keeps three roles: the owner for
   migrations, the application role for ops tables, and the read-only agent role, the only one the
   agent ever gets.

## Apply it to your repository

1. Find the database account your agent connects as. List its grants.
2. If it can write anything, create a read-only role with `USAGE` and `SELECT` on one schema only,
   as `platform/ops/sql/roles.sql` does, and point the agent at it.
3. Try one write as that role. It must fail with a privilege error, whatever your guard says.
4. Run `make demo NAME=verify-malicious-sql`: with the naive guard planted, the guard lets the
   write through and the role still refuses it.

## Sources

- Source 1: SQL Injection Prevention Cheat Sheet, <https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html>, OWASP Cheat Sheet Series, n.d.
