# Module: Loop Engineering - Live Demo Guide

This folder holds the Live Demo Guide: every live demo of the class, one command and one screen at
a time, with what to look at, what it means, and what to say in class. Read it here on GitHub, or
build the PDF with the command at the end of this page.

## Who it is for

- Instructors who run the demos live. Every step has an instructor note, including what to say
  when a result differs from the guide's.
- Learners who run the demos on their own copy after class, and compare their screens with the
  captured ones.
- Teaching assistants who rehearse a demo, or help a learner whose screen looks different.

## What you need first

- A set-up copy of the repository: follow [setup](../setup/README.md) to the first live demo.
- Your two keys in `.env`: the OpenAI key from the operations team and your own LangSmith key.
  Never paste a key into a terminal, a document, or a chat.
- [Part 0: Before you start](part0.md), which ends with `make preflight PURPOSE=class` and its
  last line, `Live session started at`.

## How to follow it

1. Read [Part 0: Before you start](part0.md): it starts the services, checks your copy, resets
   every section, starts the class session, and puts the console on screen.
2. Work through the chapters in order, one per section:
   - [Section 1: Agent loop](chapters/1-agent-loop.md)
   - [Section 2: Verification loop](chapters/2-verification-loop.md)
   - [Section 3: Event loop](chapters/3-event-loop.md)
   - [Section 4: Hill-climbing loop](chapters/4-hill-climbing-loop.md)
3. Every step reads the same way: where (which terminal or screen), what to type or press, what
   you should see, where to look, what it means, a checkpoint, what to do if it looks different,
   and an instructor note.
4. Each chapter ends with a result summary, the time and cost, and what to say in class.
5. The [appendix](appendix.md) has a command cheat sheet, a troubleshooting table, a glossary,
   and the recovery for a stalled demo: reset the section and run the same demo again. Every
   demo is live; there is no replay and no recording.

## Time and cost

The times are wall time from the trigger to the checked result, from the calibration demo pass of
22 and 23 October 2026 and the live session of 23 October, afternoon, each demo run alone with a
reset between ([calibration report](../docs/calibration-report.md)). A range spans the runs that
showed the demo's moment; a single value means one run did. The malicious Structured Query Language
(SQL) demo makes no model call.

| Chapter | Core demos, time per demo | Not timed | Cost |
|---|---|---|---|
| [Section 1](chapters/1-agent-loop.md) | Simple question 14 to 39 s; confident wrong answer 37 to 76 s | None | About 0.001 dollars per analyst run |
| [Section 2](chapters/2-verification-loop.md) | Malicious SQL 2 to 6 s; retry cap 14 to 79 s; graders pass 52 to 58 s | None | 0 tokens for malicious SQL |
| [Section 3](chapters/3-event-loop.md) | Webhook 14 to 46 s; approval 50 to 84; duplicates 35 to 78; kill switch 3 to 33 | Planted halves | About 0.001 dollars per analyst run |
| [Section 4](chapters/4-hill-climbing-loop.md) | Baseline 266 to 285 s; analyzer team 326 to 377 s; candidate 186 to 211 s | The finale | 0.0594 to 0.0914 dollars per 70-run experiment |

Section 4's analyzer team writes two candidates and measures each on the dev split, so its step
took 326 and 377 s; with one candidate it took 62 to 98 s. The candidate experiment demo took 186
and 211 s with two candidates, and candidate experiments ran 182 to 459 s over every measurement.
The naive analyzer, blocked, took 211 to 285 s from the trigger to the verdict. The fixed half of
Section 1's unbounded rows demo took 26 s, once.

Part 0's preflight asks the drift canary's five questions, each one agent run (about 40 model
calls, under a cent). Setting up a new
machine is in [setup](../setup/README.md); the time to follow the whole guide has not been
measured in one sitting.

## The slides

The class deck that goes with these demos is handed out separately; its outline and speaker
notes are in [slides/](../slides/README.md).

## Build the PDF

For maintainers. The build makes no model calls and starts no container. It needs the
development dependency group and Playwright's Chromium (`uv run playwright install chromium`,
once per machine):

```bash
uv run python guide/source/build_pdf.py --config guide/guide.json
```

It writes the PDF to `guide/build/`, which git ignores. Images stay where they live, in each
section's `demo/expected/` folder, so nothing is copied. Before you share the PDF, read its text for
keys, host paths, account links, and placeholders; a missing image prints as an orange box and is
listed by the build.

| Path | What it holds |
|---|---|
| `part0.md` | Part 0: Before you start |
| `chapters/` | One chapter per section's demos |
| `appendix.md` | Cheat sheet, troubleshooting, glossary, and reset-and-re-run recovery |
| `guide.json` | The build's titles, output file, and parts in order |
| `source/` | The introduction, the build sources, and [the Markdown conventions](source/CONVENTIONS.md) |
