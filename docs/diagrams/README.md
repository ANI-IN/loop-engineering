# Module: Loop Engineering - Diagrams

This folder holds the diagrams that more than one page uses: the whole system, the four loops as
one system, the run lifecycle, and the warehouse data model. Each section has its own `diagrams/`
folder for the diagram of its loop.

## How to read these files

Every diagram has three files with the same name:

| File | What it is for |
|---|---|
| `.excalidraw` | The source. Open it at excalidraw.com to edit it |
| `.svg` | A render with the font embedded, for pages on GitHub |
| `.png` | A render at 2x scale (3840 by 2160), for slides |

Some diagrams are built up on slides one step at a time. They also have step frames, named
`-step-1`, `-step-2`, and so on. Each frame adds one part, and every frame is the same 1920 by 1080
panel, so nothing moves between slides. The file without a step number is the full diagram, the
same as the last step.

Every diagram sits on a light rounded panel (`#F0F3F6`), so it reads on the navy slide background
(`#324158`) and on GitHub in light or dark mode. The panel is 1920 by 1080, placed at 80% of the
slide width, and every label is 20 pixels or more on it.

## Colours and shapes

The colours and shapes mean the same thing in every diagram:

| Colour | Shape | Meaning |
|---|---|---|
| Amber `#FFAB40` | Ellipse | An agent: a model decides what happens next |
| Blue `#3896D2` | Rounded rectangle | Code: the same input gives the same result |
| Grey `#78909C` | Rectangle with square corners | Stored state: a database, a table, a record |
| Green `#43A047` | Diamond | A person decides: human approval |
| Red `#E46962` | Rounded rectangle, thick outline | A stop, a failure, or a trap; the label says which |
| White | Rectangle with square corners | Outside DataPilot: a sender or a service |
| None, dashed | Ellipse | Deliberately no agent here |
| None, solid | Rectangle with its name on top | The boundary of a loop or a process |
| Dark `#212121` | Text and arrows | Every label and every arrow |

In the run lifecycle, a white rounded rectangle is a state the run goes on from, and a thick
outline is a state that ends the run.

Colour is never the only signal. Each kind has its own shape, every red box starts with the word
"Stop", "Blocked", "Failed", "Trap", or "No", and the alt text and caption of each diagram say what
it shows. You do not need to tell the colours apart to read a diagram.

## The diagrams

Each diagram below has its embed snippet for a page in `docs/`; from another folder, change the
path (from the root `README.md`, `docs/diagrams/<name>.svg`; from a section page,
`../docs/diagrams/<name>.svg`).

### The system

![DataPilot's processes and data: a webhook sender, a person at the console, and the scheduler send work to the application programming interface; the worker runs the analyst, schema scout, and reviewer agents; the hill-climbing loop runner runs the analyzer team; all of them share the ops schema in PostgreSQL](./system-architecture.svg)

*Notice that the application programming interface (API), the worker, and the runner never call each other: they meet in the ops schema, and the agents read the warehouse through a read-only role.*

```markdown
![DataPilot's processes and data: a webhook sender, a person at the console, and the scheduler send work to the application programming interface; the worker runs the analyst, schema scout, and reviewer agents; the hill-climbing loop runner runs the analyzer team; all of them share the ops schema in PostgreSQL](diagrams/system-architecture.svg)

*Notice that the API, the worker, and the runner never call each other: they meet in the ops schema, and the agents read the warehouse through a read-only role.*
```

- **What it teaches**: the processes, the agents inside them, and the data they share.
- **Slide topic**: the system, in the opening, and the architecture page.
- **Files**: `system-architecture`.
- **Source in the code**: `compose.yaml` (the services and the one-shot migrate),
  `platform/src/datapilot/db.py`, the 19 routes in `platform/src/datapilot/loop3_events/api/`,
  `loop3_events/scheduler.py`, `loop3_events/worker.py`, `loop3_events/trace_refusals.py`,
  `loop3_events/improvement.py` (one runner per database), `loop4_hill_climbing/runner.py` (two
  candidates, promotions with clearance re-runs, gold checks of live runs), and the tables in
  `platform/ops/sql/ops/`.

### The four loops as one system

![The four loops nested: the agent loop inside the verification loop inside the event loop, with the hill-climbing loop beside them feeding a promoted knowledge version back to the analyst; six agents drawn as ellipses, and a dashed ellipse under the router, where there is deliberately no agent](./four-loops.svg)

*Notice where the agents are and where there are none: the router, the graders, the overfit guard, and the gate are code, and a person approves.*

```markdown
![The four loops nested: the agent loop inside the verification loop inside the event loop, with the hill-climbing loop beside them feeding a promoted knowledge version back to the analyst; six agents drawn as ellipses, and a dashed ellipse under the router, where there is deliberately no agent](diagrams/four-loops.svg)

*Notice where the agents are and where there are none: the router, the graders, the overfit guard, and the gate are code, and a person approves.*
```

- **What it teaches**: how the four loops wrap one another, where each agent sits, and where the
  course chose code instead of an agent.
- **Slide topic**: the module map, in the opening; one loop per step at the start of each section.
- **Files**: `four-loops`, with step frames `four-loops-step-1` to `four-loops-step-4`, one loop
  per step, Section 1: Agent loop first.
- **Source in the code**: `platform/src/datapilot/loop1_agent/analyst.py` and `scout.py`;
  `loop2_verification/loop.py` and `reviewer.py`; `loop3_events/router.py`, `worker.py`,
  `autonomy.py`, `killswitch.py`, and `reaper.py`; `loop4_hill_climbing/analyzer.py`,
  `candidates.py`, `overfit_guard.py`, `gate.py`, and `runner.py`; the 25 dev and 15 holdout items in
  `platform/packs/datapilot_us/benchmark/`.

### The run lifecycle

![The run lifecycle: twelve states from received to posted, and 23 numbered transitions, each listed with the component that writes it, taken from the contract in lifecycle.py](./run-lifecycle.svg)

*Notice that every arrow has one named writer, the API, the worker, or the reaper, and that six states end a run, only one of them with a posted answer.*

```markdown
![The run lifecycle: twelve states from received to posted, and 23 numbered transitions, each listed with the component that writes it, taken from the contract in lifecycle.py](diagrams/run-lifecycle.svg)

*Notice that every arrow has one named writer, the API, the worker, or the reaper, and that six states end a run, only one of them with a posted answer.*
```

- **What it teaches**: the states a run passes through and which component may move it.
- **Slide topic**: the run lifecycle, in Section 3: Event loop, and the console's lanes.
- **Files**: `run-lifecycle`.
- **Source in the code**: `RunStatus`, `TERMINAL`, and `TRANSITIONS` in
  `platform/src/datapilot/contracts/lifecycle.py`. The key on the diagram is built from
  `TRANSITIONS`, and `platform/tests/unit/test_diagrams.py` fails if they drift apart.

### The warehouse data model

![The five warehouse tables and the marketing view, with the keys between them; red boxes point at the columns where the traps hide, order_ts, status, total_cents, the customer email, and the product names; green diamonds mark the four personal-data columns](./warehouse-data-model.svg)

*Notice that no column name or comment states a business rule: each trap is invisible in the schema, so only a knowledge version can teach it.*

```markdown
![The five warehouse tables and the marketing view, with the keys between them; red boxes point at the columns where the traps hide, order_ts, status, total_cents, the customer email, and the product names; green diamonds mark the four personal-data columns](diagrams/warehouse-data-model.svg)

*Notice that no column name or comment states a business rule: each trap is invisible in the schema, so only a knowledge version can teach it.*
```

- **What it teaches**: Harbor & Pine Outfitters' warehouse, and where a naive answer goes wrong:
  fiscal year, net revenue, cancelled orders, Eastern time, and internal accounts.
- **Slide topic**: meet the warehouse, in the opening and in Section 1: Agent loop.
- **Files**: `warehouse-data-model`.
- **Source in the code**: `platform/ops/sql/warehouse_schema.sql` and `warehouse_indexes.sql`;
  the data conditions in `platform/planted/registry.yaml`; business rules 1 to 6 in
  `platform/packs/datapilot_us/benchmark/business_rules.md`; the personal-data columns in
  `platform/packs/datapilot_us/pack.yaml`.

## How the renders are made

The renders are made at authoring time only. Learners never run the export, the renders are
committed, and nothing in the app or the learner's setup uses Node.

1. Each diagram is written as a function in `platform/tools/diagrams/definitions.py`, built from
   the fixed kinds in `platform/tools/diagrams/scene.py`, so every label can be traced to the file
   it comes from. `--build` writes the `.excalidraw` sources (and the step frames) from them.
   After that the `.excalidraw` file is the source: edit it at excalidraw.com, or change the
   function and build again, which overwrites hand edits.
2. `platform/tools/diagrams/export_diagrams.py` opens headless Chromium through Playwright for
   Python on `platform/tools/diagrams/export_page.html`, a local page that loads one pinned
   Excalidraw build from jsDelivr
   (`https://cdn.jsdelivr.net/npm/@excalidraw/excalidraw@0.18.1/+esm`), with its fonts from the
   same package. The page measures each label with the real font (so a label is centred as
   Excalidraw would centre it), then calls `exportToSvg` (fonts embedded) and `exportToBlob` at
   scale 2 for each source.
3. The script writes `<name>.svg` and `<name>.png` beside the source, and records the SHA-256 of
   the source and of both renders in the folder's `renders.json`. Renders are deterministic: the
   same source gives the same bytes.
4. `platform/tests/unit/test_diagrams.py` runs in `make test` with no browser and no network. It
   fails when a source changed without a new render or a render was changed by hand, and it checks
   the canvas, the 20-pixel labels, the embedded font, the step frames, the naming rule on every
   label, and the run lifecycle key against the contract.

Run it from the repository root (the dev dependency group, once per machine
`uv run playwright install chromium`):

```bash
uv run python platform/tools/diagrams/export_diagrams.py          # render what is stale
uv run python platform/tools/diagrams/export_diagrams.py --build  # write sources, then render
uv run python platform/tools/diagrams/export_diagrams.py --check  # report stale renders
```

| Pinned | Version | Note |
|---|---|---|
| `@excalidraw/excalidraw` on npm | 0.18.1 | Released 2026-04-20; loaded as jsDelivr's `+esm` build |
| React, through that build | 19.2.5 | jsDelivr fixes it inside the `+esm` build |
| Playwright for Python | 1.63.0 | Already in the dev dependency group |
| Chromium | 153.0.8010.12 | The build Playwright 1.63.0 installs |
