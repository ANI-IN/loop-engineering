# Module: Loop Engineering - Diagrams for Section 4: Hill-climbing loop

Each diagram here has an `.excalidraw` source, a `.svg` with the font embedded for pages, and a
`.png` at 2x for slides. The colours, the shapes, the step frames, and how the renders are made are
explained once, in [the shared diagrams page](../../docs/diagrams/README.md#colours-and-shapes).

### The hill-climbing loop

![The benchmark, 25 development and 15 holdout items, and two databases feed the experiment runner; failed development items go to the analyzer team of three agents, then the overfit guard, then a candidate knowledge version; the promotion gate, with its confirming runs and a person's approval, makes the active version; a band below explains autonomy per metric family](./hill-climbing-loop.svg)

*Notice that the agents only propose: code decides whether a rule overfits and whether a version is better, and a person approves the promotion.*

The snippet for this folder's README or the section's `concepts.md` (both sit one level above
`diagrams/`):

```markdown
![The benchmark, 25 development and 15 holdout items, and two databases feed the experiment runner; failed development items go to the analyzer team of three agents, then the overfit guard, then a candidate knowledge version; the promotion gate, with its confirming runs and a person's approval, makes the active version; a band below explains autonomy per metric family](diagrams/hill-climbing-loop.svg)

*Notice that the agents only propose: code decides whether a rule overfits and whether a version is better, and a person approves the promotion.*
```

- **What it teaches**: the benchmark and its two databases, the analyzer team (failure analyst,
  rule writer, critic), the overfit guard, the paired promotion gate with its confirming runs,
  and autonomy per metric family.
- **Slide topic**: the hill-climbing loop, in Section 4: Hill-climbing loop.
- **Files**: `hill-climbing-loop`, with step frames `hill-climbing-loop-step-1` (the benchmark and
  the experiment), `-step-2` (the analyzer team), `-step-3` (the overfit guard and the candidate),
  `-step-4` (the gate, the confirming runs, the approval), and `-step-5` (autonomy per metric
  family).
- **Source in the code**: `platform/packs/datapilot_us/benchmark/dev.yaml` and `holdout.yaml`,
  `platform/src/datapilot/loop4_hill_climbing/evaluator.py`, `experiment.py`, `measurement.py`,
  `analyzer.py`, `overfit_guard.py`, and `gate.py`, `loop3_events/autonomy.py`, and `evaluation`
  and `autonomy` in `platform/packs/datapilot_us/pack.yaml`.
