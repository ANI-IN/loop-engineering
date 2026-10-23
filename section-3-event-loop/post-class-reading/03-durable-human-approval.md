# [Human-in-the-loop](https://docs.langchain.com/oss/python/langchain/human-in-the-loop)

Reading time: about 25 minutes.
Source: LangChain, [Human-in-the-loop](https://docs.langchain.com/oss/python/langchain/human-in-the-loop), n.d.

> **Terms on this page**
>
> - **Human approval**: A person approves or rejects a held action before it runs.
> - **Personal data**: Customer emails, phone numbers, and names; a query that reads them waits for human approval.

## Why it matters

You know the middleware. Read this page again for the part that decides whether an approval
survives the real world: where the paused run lives. The approval that survives a restart demo
turns on exactly that sentence, and the page also covers the conditional interrupt DataPilot uses
for personal data.

## Three key ideas

1. **A pause is saved state.** When a tool call needs review, "the middleware issues an interrupt
   that halts execution. The graph state is saved using LangGraph's persistence layer, so execution
   can pause safely and resume later." The approval is not a process waiting; it is a checkpoint.

2. **The checkpointer decides durability.** "You must configure a checkpointer to persist the
   graph state across interrupts. In production, use a persistent checkpointer like
   AsyncPostgresSaver or MongoDBSaver. For testing or prototyping, use InMemorySaver." DataPilot
   uses `AsyncPostgresSaver` in schema `lg`; the in-memory checkpointer
   (`BUG_MEMORY_CHECKPOINTER`) is the planted bug that loses the approval on restart.

3. **Interrupt only what needs a decision.** A `when` predicate decides per call: "Calls that
   evaluate to False never pause, so a reviewer only sees the actions that need a decision." The
   predicate "runs again when the agent resumes, so it must return the same result for the same
   call". DataPilot's personal-data check is deterministic for the same reason.

## Apply it to your repository

1. Find every approval step in your agents. Check which checkpointer each one uses.
2. Restart the process while an approval is pending. If the approval is gone, switch to a
   persistent checkpointer.
3. Make each approval rule a deterministic function of the call, so it gives the same answer on
   resume.
4. Show the reviewer the exact action, as DataPilot's dialog shows the exact query and row count.

## Sources

- Source 1: Human-in-the-loop, <https://docs.langchain.com/oss/python/langchain/human-in-the-loop>, LangChain, n.d.
