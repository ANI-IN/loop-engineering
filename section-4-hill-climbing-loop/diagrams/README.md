# Module: Loop Engineering - Diagrams for Section 4: Hill-climbing loop

Each diagram here has an `.excalidraw` source, a `.svg` with the font embedded for pages, and a
`.png` at 2x for slides. The colours, the shapes, the step frames, and how the renders are made are
explained once, in [the shared diagrams page](../../docs/diagrams/README.md#colours-and-shapes).

## The hill-climbing loop

![The hill-climbing cycle: the benchmark, 25 development and 15 holdout questions, feeds an experiment that measures execution match on two databases; the analyzer team of three agents reads only the failed development questions; the overfit guard rejects a rule that copies a question or a gold query; of two candidates the better one is kept; the promotion gate needs all four conditions, more holdout passes than the active version, zero confirmed regressions on both splits, human approval, and every new rule passing the overfit guard; the promoted version becomes the active knowledge version and the next baseline](./hill-climbing-loop.svg)

*Notice that the agents only propose: code decides whether a rule overfits and whether a version is better, and a person approves the promotion.*

The snippet for this folder's README or the section's `concepts.md` (both sit one level above
`diagrams/`):

```markdown
![The hill-climbing cycle: the benchmark, 25 development and 15 holdout questions, feeds an experiment that measures execution match on two databases; the analyzer team of three agents reads only the failed development questions; the overfit guard rejects a rule that copies a question or a gold query; of two candidates the better one is kept; the promotion gate needs all four conditions, more holdout passes than the active version, zero confirmed regressions on both splits, human approval, and every new rule passing the overfit guard; the promoted version becomes the active knowledge version and the next baseline](diagrams/hill-climbing-loop.svg)

*Notice that the agents only propose: code decides whether a rule overfits and whether a version is better, and a person approves the promotion.*
```

- **What it teaches**: the hill-climbing cycle: the benchmark and its two databases, the
  analyzer team (failure analyst, rule writer, critic), the overfit guard, two candidates, and
  the promotion gate with its four conditions. Autonomy per metric family is explained in the
  section's concepts page.
- **Slide topic**: the hill-climbing loop, in Section 4: Hill-climbing loop.
- **Files**: `hill-climbing-loop`, with step frames `hill-climbing-loop-step-1` (the benchmark and
  the experiment), `-step-2` (the analyzer team), `-step-3` (the overfit guard and the two
  candidates), and `-step-4` (the gate's four conditions, the approval, and the promoted
  version).
- **Source in the code**: `platform/packs/datapilot_us/benchmark/dev.yaml` and `holdout.yaml`,
  `platform/src/datapilot/loop4_hill_climbing/evaluator.py`, `experiment.py`, `measurement.py`,
  `analyzer.py`, `overfit_guard.py`, `candidates.py`, and `gate.py` (the four conditions, in
  `decide`), and `analyzer` and `evaluation` in `platform/packs/datapilot_us/pack.yaml`.
