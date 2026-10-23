# Module: Loop Engineering - Diagrams for Section 2: Verification loop

Each diagram here has an `.excalidraw` source, a `.svg` with the font embedded for pages, and a
`.png` at 2x for slides. The colours, the shapes, the step frames, and how the renders are made are
explained once, in [the shared diagrams page](../../docs/diagrams/README.md#colours-and-shapes).

### The verification layers

![Two stages of checks. Stage 1: each query passes the parse, statement policy, schema, cost, and personal data graders, then the read-only executor and the execution grader; a block sends feedback to the analyst, personal data goes to a person, and a write the database refuses ends the run at once. Stage 2: the answer envelope's query runs through graders 1 to 6 again, then the final-answer grader, then the reviewer agent; a failure retries, up to 3 attempts. A red band on top: the stop before every model call and every tool call](./verification-layers.svg)

*Notice the order: the reviewer only ever sees an answer that every grader passed, and the stop before the model call can end the run at any point.*

The snippet for this folder's README or the section's `concepts.md` (both sit one level above
`diagrams/`):

```markdown
![Two stages of checks. Stage 1: each query passes the parse, statement policy, schema, cost, and personal data graders, then the read-only executor and the execution grader; a block sends feedback to the analyst, personal data goes to a person, and a write the database refuses ends the run at once. Stage 2: the answer envelope's query runs through graders 1 to 6 again, then the final-answer grader, then the reviewer agent; a failure retries, up to 3 attempts. A red band on top: the stop before every model call and every tool call](diagrams/verification-layers.svg)

*Notice the order: the reviewer only ever sees an answer that every grader passed, and the stop before the model call can end the run at any point.*
```

- **What it teaches**: the seven deterministic graders by stage, the read-only database role
  under them, the retry cap, a refused write that ends the run with no retry, the reviewer agent
  after the graders (it can hold an answer for a person, never pass a failed one), and the stop
  that runs before every model and tool call.
- **Slide topic**: the verification layers, in Section 2: Verification loop.
- **Files**: `verification-layers`, with step frames `verification-layers-step-1` (graders 1 to 5
  and the block), `-step-2` (the executor, the execution grader, the database role, the refused
  write), `-step-3` (the answer stage and the retry cap), `-step-4` (the reviewer), and `-step-5`
  (the stop before the model call).
- **Source in the code**: `platform/src/datapilot/loop2_verification/checker.py` (the order),
  `graders/` (one file per grader, numbered 1 to 7), `executor.py`, `loop.py` (the answer stage,
  the reviewer, held answers), `limits.py`, `reviewer.py`,
  `platform/src/datapilot/loop1_agent/guard.py` and `loop3_events/killswitch.py` (the stop),
  `platform/ops/sql/roles.sql`, and `limits` in `platform/packs/datapilot_us/pack.yaml` (3
  attempts, a 5,000 millisecond statement timeout).
