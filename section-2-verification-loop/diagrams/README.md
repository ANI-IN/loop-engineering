# Module: Loop Engineering - Diagrams for Section 2: Verification loop

Each diagram here has an `.excalidraw` source, a `.svg` with the font embedded for pages, and a
`.png` at 2x for slides. The colours, the shapes, the step frames, and how the renders are made are
explained once, in [the shared diagrams page](../../docs/diagrams/README.md#colours-and-shapes).

## The verification layers

![Two stages of checks. Every query: graders 1 to 5, parse, SELECT only, schema, cost estimate, and personal data, then the read-only executor and grader 6, execution; a block sends the reason back to the analyst, personal data goes to human approval, and a write the database refuses ends the run. The answer: graders 1 to 6 again, then grader 7, final answer, then the reviewer agent, which can hold the answer for a person; a failure retries and is escalated after 3 attempts. A stop box: before every model call and every tool call, the kill switch and the budgets](./verification-layers.svg)

*Notice the order: the reviewer only ever sees an answer that every grader passed, and the stop before every call can end the run at any point.*

The snippet for this folder's README or the section's `concepts.md` (both sit one level above
`diagrams/`):

```markdown
![Two stages of checks. Every query: graders 1 to 5, parse, SELECT only, schema, cost estimate, and personal data, then the read-only executor and grader 6, execution; a block sends the reason back to the analyst, personal data goes to human approval, and a write the database refuses ends the run. The answer: graders 1 to 6 again, then grader 7, final answer, then the reviewer agent, which can hold the answer for a person; a failure retries and is escalated after 3 attempts. A stop box: before every model call and every tool call, the kill switch and the budgets](diagrams/verification-layers.svg)

*Notice the order: the reviewer only ever sees an answer that every grader passed, and the stop before every call can end the run at any point.*
```

- **What it teaches**: the seven deterministic graders by stage, the read-only database role
  under them, the retry cap, a refused write that ends the run with no retry, the reviewer agent
  after the graders (it can hold an answer for a person, never pass a failed one), and the stop
  that runs before every model and tool call.
- **Slide topic**: the verification layers, in Section 2: Verification loop.
- **Files**: `verification-layers`, with step frames `verification-layers-step-1` (graders 1 to 5,
  the block, and human approval), `-step-2` (the executor, the execution grader, the refused
  write), `-step-3` (the answer stage and the retry cap), `-step-4` (the reviewer and the
  person it can hand an answer to), and `-step-5` (the stop before every call).
- **Source in the code**: `platform/src/datapilot/loop2_verification/checker.py` (the order),
  `graders/` (one file per grader, numbered 1 to 7), `executor.py`, `loop.py` (the answer stage,
  the reviewer, held answers), `limits.py`, `reviewer.py`,
  `platform/src/datapilot/loop1_agent/guard.py`, `loop3_events/killswitch.py`, and
  `loop3_events/budget.py` (the stop),
  `platform/ops/sql/roles.sql`, and `limits` in `platform/packs/datapilot_us/pack.yaml` (3
  attempts, a 5,000 millisecond statement timeout).
