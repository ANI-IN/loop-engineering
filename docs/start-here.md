# Start here

> **Terms on this page**
>
> - **Agent loop**: The model calls tools, reads the results, and repeats until it answers.
> - **Verification loop**: Graders check each query and answer, and send failures back to the agent.
> - **Event loop**: Events become jobs that workers run, with approvals, budgets, and a kill switch.
> - **Hill-climbing loop**: Experiments find failures, an analyzer team proposes rules, and a gate decides.

Module: Loop Engineering builds four loops around one analytics agent, DataPilot, and measures
each one on the same benchmark. Work through it in order: setup, the four sections, the four
assignments, the final project, and then your own repository. Keep three pages at hand: the
[glossary](glossary.md) for any term, the [costs page](costs.md) for what each command calls, and
the [frequently asked questions](faq.md).

## How the times were set

Two kinds of time appear on these pages:

- **Reading time** is a page's word count divided by 200, rounded up: to the minute on the
  concepts pages, and to 5 minutes for the post-class readings.
- **Run time** is what a command took on the course machine, as the range over the measured runs
  with their date. The run times on these pages come from the calibration and live sessions of 22
  and 23 October 2026.

The assignment effort is the planned time for one learner, stated in each assignment's README.

## The path at a glance

| Step | What you do | Reading time |
|---|---|---|
| Setup | Install the tools, run `make preflight`, run the first live demo | The page for your system |
| Section 1: Agent loop | The analyst, its tools, and the confident wrong answer | Concepts: about 8 minutes |
| Section 2: Verification loop | Graders, the read-only role, the retry cap, the reviewer | Concepts: about 9 minutes |
| Section 3: Event loop | Events, the job queue, durable approval, the kill switch | Concepts: about 9 minutes |
| Section 4: Hill-climbing loop | The benchmark, the analyzer team, the gate | Concepts: about 10 minutes |
| Assignments | One live extension per section | Each README states its effort |
| Final project | Your own dataset, traps, benchmark, and one extension | Open-ended |
| Your own repository | DataPilot on your own Postgres or a new domain pack | The guide's steps |

## Step 1: Setup

[Setup](../setup/README.md) takes a machine with nothing installed to a first live demo. Then
work through the [before-class checklist](../setup/pre-class.md). Your OpenAI key comes from the
operations team; LangSmith is your own free account.

## Steps 2 to 5: the four sections

Each section has the same parts, in the same order: the README, concepts, the demo and its
walkthrough, the assignment, the post-class readings, and the session notes.

- [Section 1: Agent loop](../section-1-agent-loop/README.md): better tools before more rules. The
  section ends with the spine question still answered wrong.
- [Section 2: Verification loop](../section-2-verification-loop/README.md): deterministic graders,
  caps the model cannot argue with, and an independent reviewer. Every grader passes, and the
  answer is still wrong.
- [Section 3: Event loop](../section-3-event-loop/README.md): the same agent driven by events,
  schedules, and people, with approvals that survive a restart and a kill switch.
- [Section 4: Hill-climbing loop](../section-4-hill-climbing-loop/README.md): the loop that learns
  the missing rules from failures, guarded by holdout questions and human approval.

## Step 6: Assignments

Each section's `assignment/` folder holds one standalone extension of what the section showed.
You run its live check while you work, `make check-assignment NAME=<slug>`, with your own key. The
solutions are published at the start of the [Thursday review](review-session.md).

## Step 7: Final project

The [final project](../final-project/README.md) is open-ended: your own dataset, at least three
traps of your own, your own benchmark with dev and holdout splits, one extension, and a
before-and-after report.

## Step 8: Use it in your repository

[Use it in your repository](../use-in-your-repo/README.md) points DataPilot at your own Postgres,
or builds a new domain pack from `platform/packs/_template/`.

## After class

- Read each section's [session notes](../section-1-agent-loop/session-notes.md) and its
  post-class readings.
- Work through the four assignments before the Thursday review, with their live checks.
- Bring the question you could not ask in class: questions marked Thursday in the chat are
  answered in the review session, then added to the [frequently asked questions](faq.md).
- Start the final project once the assignments pass.
