# Module: Loop Engineering - Diagrams for Section 1: Agent loop

Each diagram here has an `.excalidraw` source, a `.svg` with the font embedded for pages, and a
`.png` at 2x for slides. The colours, the shapes, the step frames, and how the renders are made are
explained once, in [the shared diagrams page](../../docs/diagrams/README.md#colours-and-shapes).
This section also uses [the warehouse data model](../../docs/diagrams/README.md#the-warehouse-data-model)
and [the four loops as one system](../../docs/diagrams/README.md#the-four-loops-as-one-system).

## The agent loop

![The analyst agent between its prompt, which carries the business date and the active knowledge version, and its tools list_tables, describe_table, run_query, and scout_schema; run_query goes through the checker and returns at most 50 rows; scout_schema starts a schema scout agent inside a dashed tool boundary with only list_tables and describe_table; the run ends in an answer envelope; a stop box lists the limits of every run: 12 model calls, 16 tool calls, 60,000 tokens](./agent-loop.svg)

*Notice the schema scout's boundary: it can read the catalog but has no run_query, and every answer arrives as one structured envelope.*

The snippet for this folder's README or the section's `concepts.md` (both sit one level above
`diagrams/`):

```markdown
![The analyst agent between its prompt, which carries the business date and the active knowledge version, and its tools list_tables, describe_table, run_query, and scout_schema; run_query goes through the checker and returns at most 50 rows; scout_schema starts a schema scout agent inside a dashed tool boundary with only list_tables and describe_table; the run ends in an answer envelope; a stop box lists the limits of every run: 12 model calls, 16 tool calls, 60,000 tokens](diagrams/agent-loop.svg)

*Notice the schema scout's boundary: it can read the catalog but has no run_query, and every answer arrives as one structured envelope.*
```

- **What it teaches**: an agent is a model that calls tools in a loop; here the prompt carries the
  active knowledge version, `run_query` never touches the database itself, the schema scout is a
  stateless helper with a narrower tool set, and the run ends in an answer envelope or a stop.
- **Slide topic**: the agent loop, at the start of Section 1: Agent loop.
- **Files**: `agent-loop`, with step frames `agent-loop-step-1` (the question, the prompt, the
  analyst), `-step-2` (the tools, the checker, and the row cap), `-step-3` (the schema scout's
  tool boundary), `-step-4` (the answer envelope), and `-step-5` (the stops for every run).
- **Source in the code**: `platform/src/datapilot/loop1_agent/analyst.py` (the prompt, the limits,
  the structured output), `tools.py` (the three tools and the row cap), `scout.py` (the schema
  scout and its catalog tools), `platform/src/datapilot/contracts/answer.py` (the envelope), and
  `limits` and `budgets` in `platform/packs/datapilot_us/pack.yaml` (50 rows, 12 model calls, 16
  tool calls, 60,000 tokens per run).
