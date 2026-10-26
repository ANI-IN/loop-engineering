# Final project checklist

The final project is done when you can show the items below. There is no grader.

## What to show

1. **Your domain pack**: the folder `platform/packs/<your pack>/`, with its `pack.yaml`, its
   business rules, its benchmark, and its starting knowledge.
2. **Your traps**: at least three, in `benchmark/business_rules.md`, each with the question that
   shows it and the naive query it breaks.
3. **The pack check**: the terminal output of `final-project/run.sh <your pack>`, ending with
   `0 problems`.
4. **Your extension**: the files you changed, and one sentence on what the class code could not do
   before.
5. **The before-and-after report**: the holdout items passed (the questions the analyzer team
   never sees) under version 1 of your knowledge (the starting version) and under the candidate,
   the regressions on both splits (development and holdout), the gate verdict, and the trace
   links of both experiments.

## Self-check

- [ ] Every number in the report comes from your terminal or your console screens.
- [ ] Results are counts, such as "3 of 4 holdout items", never percentages.
- [ ] Each of your traps fails at least once under the starting knowledge; one that passed is
      reported as passing.
- [ ] The holdout questions are worded away from the development questions.
- [ ] A run that ended early, at a cap or with a blocked gate, is reported with its counts.
- [ ] The report says what one run cannot tell you.
