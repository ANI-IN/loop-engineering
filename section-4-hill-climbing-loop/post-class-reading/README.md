# Module: Loop Engineering - Reading list for Section 4: Hill-climbing loop

Three readings that go past the class time of the hill-climbing loop. Each page sums up one primary
source in plain words and shows how to apply it to your own repository. Each page takes a few
minutes; the reading time in the table is for the full source, at 200 words a minute, rounded up
to 5 minutes.

> **Terms on this page**
>
> - **Hill-climbing loop**: Experiments find failures, an analyzer team proposes rules, and a gate decides.
> - **Holdout split**: The benchmark questions the analyzer team never sees; the gate decides on them.

## Readings

| Reading | Reading time | Why read it |
|---|---|---|
| [01 Rules learned from failures](01-magic-self-correction.md) | 40 minutes | How agents turn failures into guidance, and why that needs a holdout split |
| [02 Evidence written by a machine](02-seed-evidence-generation.md) | 30 minutes | Why the knowledge you give a model can be missing or wrong |
| [03 The four loops](03-art-of-loop-engineering.md) | 10 minutes | The post that names the four loops, and where people stay in them |

## How to use these

- Read the first two together: one learns rules from failures, the other writes evidence from the
  schema. Both need a gate.
- Read the third last, as a map of the whole module.
- After each reading, do the first step of its "Apply it to your repository" list.
