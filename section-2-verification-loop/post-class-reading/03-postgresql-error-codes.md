# [PostgreSQL Error Codes](https://www.postgresql.org/docs/current/errcodes-appendix.html)

Reading time: about 10 minutes.
Source: PostgreSQL Global Development Group, [PostgreSQL Error Codes](https://www.postgresql.org/docs/current/errcodes-appendix.html), n.d.

> **Terms on this page**
>
> - **Verification loop**: Graders check each query and answer, and send failures back to the agent.
> - **Escalated**: A run that ended without an answer because it hit a cap or a refused write.

## Why it matters

The verification loop sends every failure back to the analyst as a reason it can act on. For
database errors, that reason comes from the error code, not the message text. This appendix lists
every code Postgres can return and explains how they are grouped. It is the table DataPilot's
executor maps from: some codes become feedback and a retry, and two end the run.

## Three key ideas

1. **Test the code, not the message.** "Applications that need to know which error condition has
   occurred should usually test the error code, rather than looking at the textual error message."
   Codes are "less likely to change across PostgreSQL releases" and are not translated, so a
   mapping keyed on them keeps working.

2. **The class tells you what to do.** "The first two characters of an error code denote a class
   of errors, while the last three characters indicate a specific condition within that class."
   Class `42` is a syntax or access rule violation; class `57` is operator intervention, which
   includes `57014` for a cancelled query, such as a statement timeout.

3. **Two codes mean a write was refused.** `25006` is `read_only_sql_transaction` and `42501` is
   `insufficient_privilege`. In DataPilot, either one ends the run escalated at once: a write
   attempt is an incident, not a mistake to correct. Other codes, such as `42P01` for an unknown
   table, go back to the analyst as feedback within the retry cap.

## Apply it to your repository

1. Collect the database errors your agent hit in the last week of traces, by code.
2. For each code, write one sentence the agent can act on, such as "Look up the real names with
   the schema tools" for an unknown table.
3. Decide which codes must never be retried. Start with `25006` and `42501`.
4. Compare with the mapping in `platform/src/datapilot/loop2_verification/executor.py`.

## Sources

- Source 1: PostgreSQL Error Codes, <https://www.postgresql.org/docs/current/errcodes-appendix.html>, PostgreSQL Global Development Group, n.d.
