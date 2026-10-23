# Module: Loop Engineering - Assignment 1: Agent loop, starter files

The starter is the complete working class system for Section 1: Agent loop, with nothing removed.
This assignment's code goes in one file, `platform/src/datapilot/loop1_agent/extension.py`. Each
place to fill is marked `# EXTENSION POINT, TODO K (agent-loop-K)`. The class system already calls every
hook there on every run, and each one does nothing yet: `lookup_tools` returns no tool,
`WORKING_METHOD` is empty, `with_matches` returns the envelope unchanged, and `lookup_values` raises
`NotImplementedError` with a one-line hint.

| Extension point | What you fill | Who calls it | Step |
|---|---|---|---|
| `agent-loop-1` | `lookup_values`: the closest stored values, with a tie flag | your tool, and the check | 3 |
| `agent-loop-2` | `lookup_tools`: the tool `find_exact_values` | the verification loop, per run | 4 |
| `agent-loop-3` | `WORKING_METHOD`: one more step for the analyst | the analyst's system prompt | 5 |
| `agent-loop-4` | `with_matches`: record matches in `assumptions` | the verification loop, per answer | 6 |

Work through them in the order of the [assignment steps](../README.md#step-by-step), and run
`make check-assignment NAME=agent-loop` after each one. The deterministic lines need no model call;
the live lines run only once the tool is registered.
