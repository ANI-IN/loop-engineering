# Module: Loop Engineering - Assignment 4: Hill-climbing loop, starter files

The starter is the complete working class system for Section 4: Hill-climbing loop, with nothing
removed. The analyzer team and the eligibility rule
(`platform/src/datapilot/loop4_hill_climbing/eligibility.py`) already call every hook in
`platform/src/datapilot/loop4_hill_climbing/extension.py`, and each does nothing yet: the critic
gets no more guidance, the screen drops nothing, and every family has enough holdout items (the
benchmark questions the analyzer team never sees, on which the gate decides). Each place to fill is
marked `# EXTENSION POINT, TODO K (hill-climbing-loop-K)`.

| Extension point | What you fill | Who calls it | Step |
|---|---|---|---|
| `hill-climbing-loop-1` | A new benchmark file with six items, the family in `pack.yaml` | the experiments | 3 and 4 |
| `hill-climbing-loop-2` | `CRITIC_GUIDANCE` and `screen` | the analyzer team, before and in the critic | 5 |
| `hill-climbing-loop-3` | `enough_holdout_items` | the eligibility rule | 6 |

`pack.yaml` already has a comment that names this assignment beside `autonomy.metric_families`.
Work through the points in the order of the [assignment steps](../README.md#step-by-step), and run
`make check-assignment NAME=hill-climbing-loop` after each one. The deterministic lines need no
model call; the live lines run only once the six items exist.
