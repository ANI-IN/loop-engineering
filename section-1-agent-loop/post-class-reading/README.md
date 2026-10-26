# Module: Loop Engineering - Reading list for Section 1: Agent loop

Three readings that go past the class time of the agent loop. Each page sums up one primary source
in plain words and shows how to apply it to your own repository. Each page takes a few minutes; the
reading time in the table is for the full source, at 200 words a minute, rounded up to 5 minutes.

> **Terms on this page**
>
> - **Trap**: A business rule the schema does not reveal, so a plausible query gets it wrong.
> - **Agent loop**: The model calls tools, reads the results, and repeats until it answers.

## Readings

| Reading | Reading time | Why read it |
|---|---|---|
| [01 Business knowledge as evidence](01-bird-external-knowledge.md) | 65 minutes | Why the rules behind a number are not in the schema |
| [02 Enterprise schemas](02-spider-2-enterprise-schemas.md) | 75 minutes | How far real warehouses are from benchmark schemas, and what agents must search |
| [03 Writing tools for agents](03-writing-tools-for-agents.md) | 20 minutes | How to design what a tool returns, and why truncation needs instructions |

## How to use these

- Read them in order: the first explains the traps, the second the schemas, the third the tools.
- After each reading, do the first step of its "Apply it to your repository" list on a database
  you work with. It takes a few minutes and makes the idea concrete.
- Then compare what you found with DataPilot's tools in `platform/src/datapilot/loop1_agent/tools.py`.
