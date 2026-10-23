# [The Art of Loop Engineering](https://www.langchain.com/blog/the-art-of-loop-engineering)

Reading time: about 10 minutes.
Source: Sydney Runkle (LangChain), [The Art of Loop Engineering](https://www.langchain.com/blog/the-art-of-loop-engineering), 2026-06-16.

> **Terms on this page**
>
> - **Hill-climbing loop**: Experiments find failures, an analyzer team proposes rules, and a gate decides.
> - **Human approval**: A person approves or rejects a held action before it runs.

## Why it matters

This post names the four loops Module: Loop Engineering builds: the agent, verification,
event-driven, and hill-climbing loops. Read it after the class as a map of what you built, and
note where DataPilot makes a different choice: its hill-climbing loop learns knowledge versions
for a large language model (LLM) and gates them on a holdout split, instead of rewriting the
harness from production traces.

## Three key ideas

1. **Loops stack.** "The core agent algorithm is simple: give the LLM context and let it call
   tools in a loop until it's done." The post then wraps that loop in a verification loop, then
   an event-driven loop, then a hill-climbing loop. Each outer loop adds a decision the inner one
   cannot make.

2. **The fourth loop improves the others.** "The first three loops automate work. The fourth (and
   arguably most important) automates improvement!" Its key move is that "the return arrow doesn't
   just loop back to the top — it reaches inside and updates the agent loop directly." In
   DataPilot that arrow is a promoted knowledge version.

3. **People stay in every loop.** "Automation doesn't mean removing humans from the loop." The post
   lists a touch point per loop, including that "harness improvements can flow through human review
   before deployment". DataPilot's promotion gate makes that review mandatory: no knowledge version
   becomes active without human approval.

## Apply it to your repository

1. Draw your agent system as the four loops. Mark which ones exist today.
2. For the loop you are missing, write the one decision it would make that nothing makes now.
3. For each loop, name the person who approves, and the step where they do it.
4. Compare your drawing with the four loops diagram on the [architecture page](../../docs/architecture.md).

## Sources

- Source 1: The Art of Loop Engineering, <https://www.langchain.com/blog/the-art-of-loop-engineering>, Sydney Runkle (LangChain), 2026-06-16
