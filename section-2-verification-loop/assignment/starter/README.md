# Module: Loop Engineering - Assignment 2: Verification loop, starter files

The starter is the complete working class system for Section 2: Verification loop, with nothing
removed. The verification loop already calls two registration hooks in
`platform/src/datapilot/loop2_verification/extension.py` on every run, and both return no grader
yet. Each place to fill is marked `# EXTENSION POINT, TODO K (verification-loop-K)`.

| Extension point | What you fill | Who calls it | Step |
|---|---|---|---|
| `verification-loop-1` | A new module in `graders/`: the clarify-or-abstain grader | `question_graders()` | 3 |
| `verification-loop-2` | A new module in `graders/`: the personal-data leak grader | `answer_graders()` | 4 |
| `verification-loop-3` | Return both graders from the two hooks | the verification loop | 5 |

Both graders implement the `Grader` protocol in `platform/src/datapilot/contracts/grading.py`. The
docstring of `extension.py` says what each kind of grader receives. Work through the points in the
order of the [assignment steps](../README.md#step-by-step), and run
`make check-assignment NAME=verification-loop` after each one.
