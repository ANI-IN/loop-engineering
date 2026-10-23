# [Writing effective tools for AI agents](https://www.anthropic.com/engineering/writing-tools-for-agents)

Reading time: about 20 minutes.
Source: Ken Aizawa (Anthropic), [Writing effective tools for AI agents](https://www.anthropic.com/engineering/writing-tools-for-agents), n.d.

> **Terms on this page**
>
> - **Agent loop**: The model calls tools, reads the results, and repeats until it answers.
> - **Row cap**: The most rows a query returns to the model (`limits.row_cap`).

## Why it matters

Section 1: Agent loop argues that tools decide what the agent can know. This post from Anthropic's
engineering team is a practical guide to designing those tools: what to return, how much, and what
to say when a result is cut. It also explains why a tool for an agent is a different kind of
software from an application programming interface (API) for a developer.

## Three key ideas

1. **A tool is a contract with a non-deterministic caller.** "Tools are a new kind of software
   which reflects a contract between deterministic systems and non-deterministic agents." An agent
   may call the tool, skip it, or misuse it, so the tool must be designed for the agent, not wrapped
   around an existing endpoint.

2. **Return high-signal context, not everything.** Tools "should take care to return only high
   signal information back to agents". The post's example is an address book: a tool that returns
   all contacts makes the agent read every one, "wasting its limited context space on irrelevant
   information". DataPilot's `describe_table` returns types, samples, and distinct values for one
   table, not the whole catalog.

3. **Truncate, and say so.** The post recommends "some combination of pagination, range selection,
   filtering, and/or truncation with sensible default parameter values". If you truncate, "be sure
   to steer agents with helpful instructions". This is exactly DataPilot's `run_query`: at most the
   row cap, the total row count, and a notice that tells the agent to aggregate or add a limit.

## Apply it to your repository

1. Take your agent's largest tool result from a recent trace. Count how much of it the agent used
   in its answer.
2. Add a cap to that tool with a sensible default, and return the total count with a one-line
   notice that says what to do next.
3. Replace opaque identifiers in tool output with names the agent can reason about, as the post
   suggests.
4. Measure tokens per run before and after, as the unbounded rows demo does.

## Sources

- Source 1: Writing effective tools for AI agents, <https://www.anthropic.com/engineering/writing-tools-for-agents>, Ken Aizawa (Anthropic), n.d.
