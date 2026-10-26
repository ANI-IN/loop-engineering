# Loop Engineering: deck outline

Class length: 240 minutes. Sections: 4. Slides: 79.

This outline is the input for the deck, which is built from it. Slides teach transferable engineering concepts; they carry no file names, repository paths, make commands, or screenshots. The "Source in the repository" column is reviewer metadata only. The one fragment of code on a slide is the naive query drawn as an annotated diagram on the slide of the fiscal year 2025 revenue question; the platform's code appears only in each demo segment, opened live in the editor, and its paths live in that DEMO slide's speaker notes. Every demo is live: recovery is reset and run it again, never a recording. Each concept slide gives the principle, why it matters (the failure it prevents), how it works in DataPilot, the evidence from this course's live runs, the trade-offs, and how to apply it at work. Each DEMO slide holds its badge on the laptop picture of the reference deck, what to watch for, the guaranteed moment of its title demo, and one labelled link to the section's demo page on GitHub, the one link on any slide.

Every console control and demo name in the notes comes from the demo registry, and each demo's guaranteed moment in the DEMO notes is quoted from it at build time; every file and line range in a code walkthrough comes from that section's demo walkthrough page; every measured number comes from the calibration report, the paired measurements page (docs/benefits.md), or the live session of 24 October 2026 on gpt-6-luna, where every core and optional demo showed its moment, both halves. Values the next live session still changes carry a refresh marker that says what to refresh.

Terms spelled out once for the whole outline: application programming interface (API), Structured Query Language (SQL), Coordinated Universal Time (UTC), JavaScript Object Notation (JSON), and large language model (LLM).
<!-- refresh after the session: trace sampling seen live after the LangSmith limit resets on 1 November; each marker below names its own value -->

## Opening

| # | Slide | Layout | Time (start-end) | Says in one line | Source in the repository |
|---|---|---|---|---|---|
| 1 | Module: Loop Engineering | title | 0:00-0:00:30 | Four loops around one data agent, each measured on one benchmark | README.md |
| 2 | Instructor | blank | 0:00:30-0:01 | Who is teaching, and how to reach them | - |
| 3 | Welcome: before we begin, in the chat | concept | 0:01-0:01:30 | Post one line: which agent you run, and what stops it when it is wrong | - |
| 4 | How the class runs | diagram | 0:01:30-0:02:30 | Four sections, two breaks, one poll; every demo live; recovery is reset and run again | docs/instructor-guide.md |
| 5 | Support during the class | concept | 0:02:30-0:03 | Ask in the chat; a parking lot holds the rest for the Thursday review | docs/review-session.md |
| 6 | Your OpenAI key and its limit | concept | 0:03-0:03:30 | Your OpenAI key comes from the operations team; it lives in your environment file, never in a commit | .env.example |
| 7 | LangSmith setup | concept | 0:03:30-0:04 | Set the LangSmith key and project so every demo and check run links to its trace | setup/pre-class.md |
| 8 | Setup checks | concept | 0:04-0:05 | Services healthy, then the preflight canary: easy questions pass, trap questions still fail | setup/README.md |
| 9 | Recap: from one harness to four loops | concept | 0:05-0:05:30 | The Harness Engineering module built the harness around one run; this module builds loops around many | README.md |
| 10 | Problem statement: what are we building? | concept | 0:05:30-0:06:30 | A data agent that answers business questions in SQL, live in a console with one page per loop | README.md |
| 11 | Every section's question: net revenue in fiscal year 2025 | diagram | 0:06:30-0:07:30 | One question, five traps the schema does not reveal | platform/planted/registry.yaml |
| 12 | Why this matters | concept | 0:07:30-0:08 | A confident wrong number costs more than no answer; each loop removes one way to ship it | README.md |
| 13 | Four loops: one system, the answer path | diagram | 0:08-0:08:30 | Answer, check, run on events: three nested loops, agents only where judgement is needed | docs/architecture.md; docs/diagrams/four-loops.png (the same boxes, redrawn) |
| 14 | Four loops: the hill-climbing loop feeds back | diagram | 0:08:30-0:09 | The hill-climbing loop improves the others from failures, behind a gate | docs/architecture.md; docs/diagrams/four-loops.png (the same boxes, redrawn) |
| 15 | How we will measure | diagram | 0:09-0:09:30 | Hand-written gold queries, results compared on two databases, development and holdout splits | platform/packs/datapilot_us/pack.yaml |
| 16 | Glossary | table | 0:09:30-0:10 | Eight terms, one line each | docs/glossary.md |

### Slides and speaker notes: Opening

**Slide 1: Module: Loop Engineering**

Container: title slide

On the slide:

Module: Loop Engineering
Agent, verification, event, and hill-climbing loops: build each, then measure it.
A live class: every demo runs against the real model

Speaker notes:

Time: 0.5 minutes (0:00-0:00:30)  
Say: Welcome to Module: Loop Engineering. You already build agents. Today is about the loops around them: the loop that answers, the loop that checks, the loop that runs on events, and the loop that improves from evidence. We build all four around one data agent and measure each one. Every demo you see runs live against the real model.  
Point at: the four loop names in the subtitle.  
The slide names no date, so the same deck serves every run of the class.  
Likely question: "Is this specific to SQL agents?" Answer: SQL makes every check concrete, so we use it; each principle transfers to any agent whose output you can check.  
Transition: First, who is teaching.

**Slide 2: Instructor**

Container: title slide: name, role, contact

On the slide:

Instructor
Reach your instructor in the class chat

Speaker notes:

Time: 0.5 minutes (0:00:30-0:01)  
Say: Introduce yourself in two sentences: what you build, and one loop that saved or cost you in production. Say how learners reach you during and after class.  
The slide names no person, so any instructor can teach from it: say your name aloud and post your contact details in the class chat.  
Point at: the contact line.  
Likely question: "Where do I ask during class?" Answer: in the chat; questions that do not fit go to the Thursday review.  
Transition: One line from you in the chat before we start.

**Slide 3: Welcome: before we begin, in the chat**

Container: key-idea box: the chat prompt

On the slide:

In the chat: which agent do you run today?
What stops it when it is wrong?

Speaker notes:

Time: 0.5 minutes (0:01-0:01:30)  
Say: Post one line in the chat. Read two or three answers aloud. Most answers are "a person reads the output". Keep that answer in mind: by the end of class you will have three other answers that do not depend on someone noticing.  
Point at: the two questions.  
Ask: "What stops your agent today when it is wrong?" Expected: a person, or nothing.  
Likely question: "Will the slides be shared?" Answer: yes, the deck and its outline are in the course repository.  
Transition: Here is how the four hours run.

**Slide 4: How the class runs**

Container: step cards: the section shape

On the slide:

Opening, four sections, two breaks, one poll, wrap-up
Each section: failure, question, four concepts, live demos, code, questions
Every result shows a live stamp: start time and trace link
A stalled demo is reset and run again; no recordings

Speaker notes:

Time: 1 minute (0:01:30-0:02:30)  
Say: Each section has the same shape. A failure story, a tempting question with a verdict, four concepts, then one demo segment where I run several live demos and open the code in the editor, then questions. Breaks follow Section 2: Verification loop and the poll after Section 3: Event loop. Every demo is live. Each result on screen carries a live stamp: when the run started, in your own local time, and a link to its trace. If a demo stalls, I reset that section and run it again. There are no recordings.  
Point at: the section shape, then the live-stamp line.  
Likely question: "What if the model API is down?" Answer: I say so, open the code for that section, and return to the demo when the API answers.  
Likely question: "Why no recordings as a backup?" Answer: a recording cannot show what a loop does when the model surprises you, which is the point of the class.  
Transition: Where to get help while we go.

**Slide 5: Support during the class**

Container: icon row: chat, parking lot

On the slide:

Ask in the chat at any time
Overflow: write "Thursday" and it goes to the two-hour review session

Speaker notes:

Time: 0.5 minutes (0:02:30-0:03)  
Say: Ask in the chat at any time. When a question needs more than a minute, I say Thursday, and you post it with that word. The Thursday review session is two hours on the four assignments; it also answers the parking lot in writing.  
Point at: the Thursday line.  
Likely question: "When is the Thursday review?" Answer: at the time I announce in the class chat; the solutions are published when it starts.  
Transition: Keys next.

**Slide 6: Your OpenAI key and its limit**

Container: icon row: key, file, never committed

On the slide:

Your OpenAI key comes from the operations team
Paste it into your local environment file; that file is never committed
Recommended on the key's project: a 3-dollar limit and an alert at 1.50 dollars

Speaker notes:

Time: 0.5 minutes (0:03-0:03:30)  
Say: You get your OpenAI key from the operations team. Paste it into your .env file and never commit it; the file is ignored by git. The recommended limit on your key's project is 3 dollars, with an alert at 1.50 dollars. That is plenty: one analyst run costs about a tenth of a cent, a full experiment of 70 runs about 6 to 9 cents, and each assignment check stops at its own spend cap of 1 dollar. Every run shows its tokens and cost on the console, so you can see what your own experiments spend.  
Point at: the never-committed line, then the limit line.  
Likely question: "Which model does the class use?" Answer: gpt-6-luna, named in the model setting of the example environment file; it is a reasoning model, which matters in Section 1: Agent loop.  
Transition: LangSmith is the second key.

**Slide 7: LangSmith setup**

Container: icon row: key, tracing, local scoring

On the slide:

Set your LangSmith key and keep tracing on
Pass and fail are computed locally; LangSmith holds the traces

Speaker notes:

Time: 0.5 minutes (0:03:30-0:04)  
Say: Set your LangSmith key and keep tracing on. Pass and fail are computed locally and shown at once; LangSmith is the trace record behind every result. Every demo run and every assignment check run is traced in full. Experiment runs are traced as a sample, about 1 run in 5, tagged with knowledge version, split, item, and repetition, so one learner stays well inside the free plan's 5,000 traces a month; every run is still scored locally. Use your own free account; feedback is written with extended retention off.  
If LangSmith refuses traces when its free plan's monthly limit is spent, a trace link never fills; say so once, and point at the run's start time and run id as the evidence. Every result is still scored locally.  
Point at: the local-scoring line.  
Likely question: "Do I need a paid plan?" Answer: no; the class keeps to base traces on the free plan.  
Transition: The checks that must pass before the first demo.

**Slide 8: Setup checks**

Container: step cards: four checks in order

On the slide:

1. Services report healthy
2. Canary: three easy questions pass
3. Canary: two trap questions still fail under the starting knowledge
4. The class session starts; the status line shows its start time

Speaker notes:

Time: 1 minute (0:04-0:05)  
Say: Before class I ran two checks, and you will run the same ones at home. First, every service reports healthy. Second, the preflight canary: three easy questions must pass, and two trap questions must still fail under the starting knowledge. If the trap questions start passing, the model changed under us, so calibration runs again before anyone teaches with it. When every check passes, preflight starts the class's live session; the console's status line shows when it started, and every run until the next preflight belongs to it. In every preflight recorded in calibration, the canary read as expected. Preflight reads its data check and its canary from the selected domain pack.  
Instructor reference, not on the slide: do not run preflight now. You ran `make ps`, then `make preflight PURPOSE=class`, thirty minutes before class (the preflight checklist); a second preflight would start a new live session and leave the class session's runs behind.  
Point at: the two canary lines of that output, in the terminal where it ran.  
Likely question: "Why must a check fail?" Answer: the demos teach a failure the loops then fix; a trap that passes unaided would make the story untrue, so the canary proves it still fails.  
Transition: Where the Harness Engineering module left off.

**Slide 9: Recap: from one harness to four loops**

Container: two-column cards: the Harness Engineering module, around one run | this module, around many runs; then a one-run-to-many-runs diagram

On the slide:

The Harness Engineering module: around one run
- Instructions the agent reads
- State across sessions
- Scope and sandbox
- Verification of one run
This module: around many runs
- An agent loop with good tools
- Verification of every run
- Runs triggered by events
- Improvement from evidence

Diagram drawn from shapes: One run pill under the left card, an arrow, and a grid of eight run pills under the right card.

Speaker notes:

Time: 0.5 minutes (0:05-0:05:30)  
Say: Two cards. On the left, the Harness Engineering module, built around one run: the instructions the agent reads, state that carries across sessions, scope and a sandbox for what it may touch, and verification of that one run. On the right, this module, built around many runs: an agent loop with good tools, verification of every run, runs triggered by events, and improvement from evidence. The agent stays; the loops around it are new.  
Point at: the left card, then each line of the right card in turn, then the arrow from one run to many runs.  
Likely question: "Do I need the Harness Engineering module first?" Answer: It builds on it. The recap slide covers what you need, and the setup pages list the prerequisites.  
Transition: The product we build.

**Slide 10: Problem statement: what are we building?**

Container: icon row: the four console pages

On the slide:

Harbor & Pine Outfitters: a fictional outdoor retailer; data ends 31 January 2026
DataPilot answers business questions in Structured Query Language (SQL), live in a console:
- Agent: the tool timeline, the SQL, the answer against gold
- Verify: the grader checklist and which defense layer stopped what
- Events: the run board lanes, approvals, and the channel
- Improve: experiments, the holdout ledger, the gate verdict

Speaker notes:

Time: 1 minute (0:05:30-0:06:30)  
Say: Harbor & Pine Outfitters is a fictional outdoor retailer with a Postgres warehouse whose data ends on 31 January 2026, the business date for everything today. Finance and marketing ask questions in plain words. DataPilot writes SQL, runs it, and answers. The console has one page per loop: Agent, Verify, Events, and Improve. The data is generated with a fixed seed, and the traps in it are planted on purpose.  
Point at: the four page names.  
Likely question: "Why a fixed business date?" Answer: so "the previous day" and "the last completed fiscal quarter" mean the same thing in every run, whatever the wall clock says.  
Transition: One question runs through the whole class.

**Slide 11: Every section's question: net revenue in fiscal year 2025**

Container: annotated query: the naive net-revenue query | five trap callouts

On the slide:

"What was our net revenue in fiscal year 2025?"
1. **Fiscal year**: calendar dates; the fiscal year runs February to January
2. **Net revenue**: the total adds tax and shipping; use subtotal minus discount
3. **Cancelled orders**: no status filter; status 5 is undocumented
4. **Eastern time**: universal timestamps move evening orders to the next day
5. **Internal accounts**: no email filter; they hold 3 of the top 10

Diagram drawn from shapes: The naive query, with a numbered marker where each trap hides; the five callouts above sit below it, one per marker.

```sql
-- platform/console/design/specimen.py lines 260-266 (the join line split in two)
SELECT SUM(o.total_cents) / 100.0 AS net_revenue
FROM warehouse.orders AS o
JOIN warehouse.customers AS c
  ON c.customer_id = o.customer_id
WHERE o.order_ts >= '2025-01-01'
  AND o.order_ts <  '2026-01-01'
```

Speaker notes:

Time: 1 minute (0:06:30-0:07:30)  
Say: Five traps hide in this one question, and the schema reveals none of them. The fiscal year runs February to January and is named for the year it ends. Net revenue is subtotal minus discount, not the tempting total column that includes tax and shipping. Cancelled orders carry an undocumented status code. Business days are in Eastern time, so evening orders cross the UTC date. Internal accounts are known only by their email domain, and they hold exactly 3 of the top 10 revenue spots in each fiscal year.  
Point at: each numbered marker in the naive query, then its callout below: the calendar dates, the total column, the missing status filter, the UTC timestamp, and the join with no email filter.  
Likely question: "Why not document the schema and be done?" Answer: that document is the knowledge the agent needs; Section 4: Hill-climbing loop shows how to earn it behind a gate instead of guessing it.  
Transition: Why this is worth four hours.

**Slide 12: Why this matters**

Container: four cards: one failure per loop

On the slide:

Wrong but confident: a board deck carries a number nobody can trace
Unsafe or unbounded: a stacked write reaches the warehouse; a loop bills without end
Duplicated or unstoppable: a digest posts twice; a stop misses the running job
**Right on the test, wrong next month:** a rule fits the cases it was written from
Each loop removes one of these, at a cost you will see

Speaker notes:

Time: 0.5 minutes (0:07:30-0:08)  
Say: Four failures, one per loop. A wrong number lands in a board deck. Unsafe SQL reaches the warehouse. A digest posts twice, or a stop does not stop. A rule fits the test and breaks next month. Each loop removes one of these, and each costs something you will see.  
Point at: the four lines, top to bottom.  
Likely question: "Do I need all four loops?" Answer: start with the loop that matches your worst failure today.  
Transition: The four loops together.

**Slide 13: Four loops: one system, the answer path**

Container: box diagram drawn from shapes: Sections 1 to 3

On the slide:


Diagram drawn from shapes: The left part of the four-loops diagram, redrawn from shapes with 18-point labels: the agent loop inside the verification loop, inside the event loop.

Speaker notes:

Time: 0.5 minutes (0:08-0:08:30)  
On the slide: the left part of the four-loops diagram, redrawn from shapes so every label is 18-point text; the full picture is in the course repository. The agents are the orange ovals: the analyst and the schema scout in the agent loop, the reviewer in the verification loop, and none in the event loop.  
Say: The agent loop answers; the verification loop checks every query and the answer; the event loop runs work on events, with keys, approvals, and a stop. Look at where the agents are: the analyst and one helper, one reviewer after the deterministic checks, none at all in the event loop.  
Point at: the router box, a table with no agent, then the three orange ovals.  
Transition: The fourth loop sits beside them and feeds them.

**Slide 14: Four loops: the hill-climbing loop feeds back**

Container: box diagram drawn from shapes: Section 4

On the slide:


Diagram drawn from shapes: The right part of the four-loops diagram, redrawn from shapes with 18-point labels: the hill-climbing loop from the benchmark to the new active version.

Speaker notes:

Time: 0.5 minutes (0:08:30-0:09)  
On the slide: the right part of the four-loops diagram, redrawn from shapes with 18-point labels. The orange ovals are the analyzer team: the failure analyst, the rule writer, and the critic. Their output meets code, the overfit guard and the promotion gate, and then a person.  
Say: The hill-climbing loop improves from failures behind a gate, and a promoted version becomes the active knowledge version every analyst prompt carries. An analyzer team whose output code and a person must accept: agents appear only where judgement is needed.  
Source 1: The art of loop engineering (https://www.langchain.com/blog/the-art-of-loop-engineering): "The fourth (and arguably most important) automates improvement!" It names the same four loops; the fourth is the hill-climbing loop.  
Point at: the promotion gate, then the human approval beside it.  
Likely question: "How does this differ from LangChain's version?" Answer: theirs climbs on production traces; ours climbs on benchmark failures behind a holdout gate.  
Transition: How we will know any of it works.

**Slide 15: How we will measure**

Container: labelled diagram: question, gold, two databases, two splits

On the slide:

Each question has a hand-written gold query
Pass: the result matches gold on two databases, never the query text
40 questions: 25 development ones the analyzer team may learn from; 15 holdout it never sees
Holdout items run 3 times and pass on 2 of 3
The gate decides on holdout only, with human approval

Speaker notes:

Time: 0.5 minutes (0:09-0:09:30)  
Say: Every benchmark question has a gold query written by hand. An answer passes when its result matches gold on two databases, never by comparing query text. The benchmark has 40 questions: the analyzer team learns from the development split only, and the gate decides on the holdout split, where each item runs 3 times and passes on 2 of 3.  
Re-check after live runs: 40 items and the 3 runs and 2 passes against the benchmark files and the evaluation settings.  
Point at: the two splits.  
Likely question: "Why two databases?" Answer: a wrong query can match the right result on one database by chance; Section 2: Verification loop gives the numbers.  
Transition: Eight words you will hear all day.

**Slide 16: Glossary**

Container: two tables of four terms

On the slide:

| Term | Meaning |
|---|---|
| Trap | A business rule the schema does not reveal |
| Gold query | The hand-written query with the right answer |
| Holdout split | Questions the analyzer team never sees |
| Grader | A deterministic check of one stage |


| Term | Meaning |
|---|---|
| Reviewer | An agent that reads after the graders pass |
| Knowledge version | A numbered set of business rules |
| Promotion gate | The check a new version must pass |
| Autonomy level | How much runs unattended |

Speaker notes:

Time: 0.5 minutes (0:09:30-0:10)  
Say: Read each term in one breath. The full glossary is in the course repository.  
Point at: grader and reviewer, the pair people mix up.  
Likely question: "Grader or reviewer: which one decides?" Answer: graders decide; the reviewer can only add a concern.  
Transition: Section 1: Agent loop starts with the agent on its own.

## Section 1: Agent loop

The failure this section fixes: An agent that cannot see the business rules behind a schema answers confidently and wrong, and nothing in its output shows where the number came from.

Measured live: in calibration, each core demo twice with a reset between: the simple question shown in 37 and 39 seconds; the confident wrong answer shown in 76 seconds, 76,981,355.95 dollars against gold 64,015,091.21 with 4 trap labels, while the second attempt got no gold check within 90 seconds (hardened the same night); retaken twice on 23 October, both shown, 72,394,572.08 dollars against gold with 3 trap labels each; unbounded rows, fixed half 19,661 and 17,298 tokens per run, planted half 183,639 and 185,727 tokens. In the paired measurement of 23 October, unbounded rows took 186,689 tokens without the row cap and 27,040 with it. In the live session of 24 October every core and optional demo showed its moment, both halves, and the paired measurement gave 12 of 21 correct without the agent loop's tools against 17 of 21 with them, and 182,654 tokens for unbounded rows without the cap against 30,216 with it.

The demo: `make demo NAME=agent-simple-question`, `make demo NAME=agent-confident-wrong-answer`, `make demo NAME=agent-unbounded-rows`, launched at 0:33 on the DEMO slide, code walked at 0:45, recovery `make reset NAME=agent-loop` and re-run: reset and run it again, live.

| # | Slide | Layout | Time (start-end) | Says in one line | Source in the repository |
|---|---|---|---|---|---|
| 17 | Agenda (Section 1 highlighted) | concept | 0:10-0:10:30 | Section 1: Agent loop, then verification, event, and hill-climbing loops | section-1-agent-loop/README.md |
| 18 | Failure story: the board-deck number | diagram | 0:10:30-0:12:30 | Illustrative: asked for net revenue, the agent sums the wrong column over the wrong year | section-1-agent-loop/concepts.md |
| 19 | Agent loop: will a stronger model fix the revenue number? | concept | 0:12:30-0:15 | KEY IDEA: No. The rules are not in the schema; tools expose the error, gated knowledge fixes it | section-1-agent-loop/README.md |
| 20 | 1) Schema linking: tools are how the agent sees | table | 0:15-0:19:30 | Principle: the agent can only link words to columns its tools let it see | section-1-agent-loop/concepts.md |
| 21 | 2) Context is a budget: cap at the tool | diagram | 0:19:30-0:23:30 | Principle: the tool, not the prompt, bounds what reaches the model | platform/packs/datapilot_us/pack.yaml |
| 22 | 3) Structured output is a contract | diagram | 0:23:30-0:27:30 | Principle: a structured answer can be checked; a sentence cannot | platform/src/datapilot/contracts/answer.py |
| 23 | 4) A subagent must earn its place | diagram | 0:27:30-0:32 | Principle: add an agent only where judgement is needed, keep it stateless, and measure it | platform/src/datapilot/contracts/agents.py |
| 24 | Cheat sheet: the agent loop in four moves | table | 0:32-0:33 | Show the schema well, cap results, return a contract, add agents only for judgement | section-1-agent-loop/README.md |
| 25 | Section 1: Agent loop - Implementation Notes: The confident wrong answer | demo | 0:33-0:50 | Badge DEMO - 1, what to watch for, the guaranteed moment, and the demo page link; the demos are in the notes | section-1-agent-loop/demo/walkthrough.md; platform/demos/registry.yaml |
| 26 | Questions | concept | 0:50-0:53 | No Question Is Too Small Every Question Deserves an Answer!! Two likely questions | - |
| 27 | Reference: skip if short on time - tool output design | table | 0:53-0:54 | What a schema tool should show and withhold, and why sample rows cut both ways | section-1-agent-loop/concepts.md |
| 28 | Reference: skip if short on time - structured output strategies | table | 0:54-0:54:30 | Provider-native, tool-based, and prompt-only output: how each enforces and fails | section-1-agent-loop/concepts.md |
| 29 | Reference: skip if short on time - five traps | table | 0:54:30-0:55 | The five traps as categories of business knowledge a schema does not carry | platform/planted/registry.yaml |

Numbers this section states (each gets a "Re-check after live runs" line in its notes):

- Schema linking errors account for 68.3 percent of failures (500 sampled Spider examples, schema retrieved across all databases, DIN-SQL): Source 4, version 3, Appendix B.
- GPT-4 from 34.88 to 54.89 percent execution accuracy on the BIRD test set with knowledge evidence: Source 2, Table 2.
- BIRD size, 12,751 question-SQL pairs over 95 databases; on the test set with evidence, ChatGPT with chain-of-thought prompting 40.08 percent and GPT-4 54.89 percent, against humans 92.96 percent: Source 2, abstract and Table 2.
- Spider 2.0, 632 tasks: the best agent, built on o1-preview, solves 21.3 percent, while earlier GPT-4-based methods reach 91.2 percent on Spider 1.0 and 73.0 percent on BIRD: Source 3, abstract, introduction, and Table 5.
- LinkAlign, 33.09 percent on Spider 2.0-Lite with open-source models: Source 4.
- Row cap of 50 rows: `limits.row_cap` in pack.yaml.
- Token budget of 60,000 tokens per run: `budgets.tokens_per_run` in pack.yaml.
- 12 model calls and 16 tool calls per run: `limits.model_call_limit` and `limits.tool_call_limit` in pack.yaml.
- Class model prices, gpt-6-luna at 0.10 dollars input, 0.01 cached input, and 0.50 dollars output per 1M tokens: `prices` in pack.yaml.
- Cost of one analyst run, about 0.001 dollars; between 5 and 8 of every 10 input tokens served from the prompt cache: docs/calibration-report.md, Spend.
- Output cap per model call, reasoning included: 16,000 tokens for the analyst, 8,000 for the schema scout: `models` in pack.yaml.
- The 10,000-row result in the unbounded rows demo: the demo registry; the fixed half used 17,298 and 19,661 tokens per run, the planted half 183,639 and 185,727 tokens per run: docs/calibration-report.md, Demos and Resumed after the ledger correction.
- Mean tokens and seconds per question over four questions: scout and reviewer on 8,648 and 24.2, scout off 3,853 and 12.8, reviewer off 5,786 and 12.8, both off 3,337 and 10.1; gold results identical in every configuration: docs/calibration-report.md, Agents on and off.
- Traps under the starting knowledge: 0 of 99 trap runs passed, every trap item 3 times: docs/calibration-report.md, Traps.
- The confident wrong answer, 76,981,355.95 dollars against gold 64,015,091.21 with 4 trap labels, in 76 seconds: docs/calibration-report.md, Demos; retaken twice, 72,394,572.08 dollars with 3 trap labels each: docs/calibration-report.md, Resumed without traces.
- Seven questions without traps, 3 runs each, 21 runs per side: 12 of 21 correct with column names only, unbounded rows, and no scout, 17 of 21 with full descriptions, capped rows, and the scout, on 24 October: docs/benefits.md, Section 1: Agent loop; 4 and 6 of 7 in the earlier measurement of 23 October.
- Unbounded rows, one run of each half on 24 October: 182,654 tokens and 0.0228 dollars without the row cap, escalated at the run budget; 30,216 tokens and 0.0021 dollars with it, reviewer round trip included: docs/benefits.md, Section 1: Agent loop.
- The question "How many VIP customers do we have?" ended with the status needs clarification: docs/calibration-report.md, Live session of 24 October 2026, Edge cases.
- Every core and optional demo of the section showed its moment, both halves: docs/calibration-report.md, Live session of 24 October 2026.

### Slides and speaker notes: Section 1: Agent loop

**Slide 17: Agenda (Section 1 highlighted)**

Container: step cards: four sections, the first highlighted

On the slide:

1. Agent loop (now): what the agent can see, and what it returns
2. Verification loop
3. Event loop
4. Hill-climbing loop

Speaker notes:

Time: 0.5 minutes (0:10-0:10:30)  
Say: We start with the agent on its own, before anything checks it. You all know how to build a tool-calling agent, so we will not spend a minute on that. We spend the time on four design decisions that decide whether its answers can be trusted later: what the tools show, how much the tools return, what shape the answer takes, and when a second agent is worth its cost. Every later loop depends on these four. The verification loop can only check an answer that has a shape. The event loop can only route an answer whose status it can read. The hill-climbing loop can only improve rules the agent can actually use. So this section is the foundation, and its demo ends on a failure the next three sections exist to fix.  
Point at: the highlighted first row, then the three rows still to come.  
Likely question: "Is there a live demo in every section?" Answer: Yes, several per section, all on one demo slide near the end of the section, all live against the class model, with the code opened in the editor right after.  
Transition: Let me start with a story you have probably lived through in some form.

**Slide 18: Failure story: the board-deck number**

Container: step cards: four numbered beats, then a lesson bar

On the slide:

Illustrative
1. **The ask**: Finance asks for net revenue in fiscal year 2025, for the board deck due that afternoon.
2. **The tempting column**: the agent finds a total column on orders and sums it, tax and shipping included.
3. **The wrong year**: it sums January to December; the fiscal year runs February to January, cancelled and internal orders left in.
4. **The confident sentence**: one fluent line goes into the deck; a month later nobody can say where it came from.
Lesson: the query ran without error; the meaning was wrong, and nothing showed it.

Speaker notes:

Time: 2 minutes (0:10:30-0:12:30)  
Say: This story is illustrative, and the people are fictional. Priya, a finance manager at Harbor & Pine Outfitters, asks the analytics agent: what was our net revenue in fiscal year 2025? Beat one. The agent lists the tables, which is exactly what a good agent does. Beat two. It finds a column called `total_cents` on the orders table. The name fits the question perfectly. Beat three. It sums that column from January to December. But Harbor & Pine's fiscal year runs February to January, and `total_cents` includes tax and shipping. Cancelled orders, which carry an undocumented status code, are still in. So are the warehouse team's test orders, placed from internal accounts. Beat four. The answer comes back as one fluent, confident sentence. It goes into a board deck. A month later someone asks where the number came from, and nobody can say, because the agent returned prose, not a query anyone could inspect.  
Point at: the four beats, top to bottom; pause on beat four, then read the lesson bar.  
Likely question: "Would an experienced analyst have caught it?" Answer: Only one who already knew every rule. The sentence reads well, and the query ran without error. Nothing failed; the meaning was wrong.  
Transition: So the tempting fix is obvious: use a bigger model.

**Slide 19: Agent loop: will a stronger model fix the revenue number?**

Container: key-idea box, then three reason cards

On the slide:

KEY IDEA: No. The rules are not in the schema. Better tools expose the error; gated knowledge fixes it.
- Knowledge, not the model: the model GPT-4 rises from 34.88 to 54.89 percent on the BIRD text-to-query benchmark with domain evidence.
- Real schemas are harder: methods built on GPT-4 reach 91.2 percent on the Spider 1.0 benchmark; the best agent solves 21.3 percent of Spider 2.0.
- No temperature dial: reasoning models reject a custom temperature; consistency comes from knowledge.

Speaker notes:

Time: 2.5 minutes (0:12:30-0:15)  
Say: No. A stronger model reads the same schema, and the rules that define net revenue and fiscal year are not in it. The research is blunt about this. Source 2: BIRD (https://arxiv.org/abs/2305.03111), in summary: its 12,751 question-SQL pairs ship with external-knowledge evidence, and with that evidence GPT-4 rises from 34.88 to 54.89 percent on the BIRD test set. The model did not change; the knowledge did. Source 3: Spider 2.0 (https://arxiv.org/abs/2411.07763), in summary: on enterprise workflows the best agent, built on o1-preview, solves 21.3 percent of tasks, while earlier GPT-4-based methods reach 91.2 percent on Spider 1.0. Real schemas are bigger and messier than benchmarks. And there is one more reason a bigger model is no shortcut to consistency: reasoning models reject a custom temperature, so you cannot turn randomness down. Consistency has to come from knowledge you control and from measurement. So this section improves the tools first, and makes every answer inspectable. The rules arrive in Section 4: Hill-climbing loop, behind a gate.  
Point at: the KEY IDEA box, then the three reasons in order.  
Likely question: "Why not write the rules into the prompt now?" Answer: Rules written without measurement fit the cases you tried. We will earn them, and measure them on questions the rule writer never saw.  
Transition: Concept one: how the agent sees the schema at all.

**Slide 20: 1) Schema linking: tools are how the agent sees**

Container: two-column cards: how it works | worked example; trade-off and at-work lines; key-idea bar

On the slide:

Principle: the agent links words to columns only through what its tools show.
Why it matters: a bare number hides that status 5 means cancelled, so cancelled orders count.

| How it works in DataPilot | Worked example |
|---|---|
| Describe returns types, comments, three sample rows | Names only: status is just a number |
| Columns with few values also list those values | Distinct values: status has a few codes |
| Linking happens before any query is written | Still hidden: the February fiscal year |

Evidence: seven easy questions, 3 runs each: names only, no cap, no scout, 12 of 21 correct; with all three, 17 of 21.
At work: audit what each tool returns before you tune the prompt.
Key idea: the agent cannot use what its tools do not show.

Speaker notes:

Time: 4.5 minutes (0:15-0:19:30)  
Trade-offs, said aloud: every field costs tokens; sample rows can carry text the model may follow.  
Plain explanation: Schema linking is the step where the agent maps the words in a question, like revenue or cancelled, onto tables, columns, and values. It happens before any SQL is written, and every later step inherits its mistakes. The agent links only through what its tools return, so tool output design is schema-linking design.  
Concrete example from DataPilot: Our describe tool returns column types, nullability, neutral comments, three sample rows, and the distinct values of low-cardinality columns. With the planted names-only schema bug (`BUG_NAMES_ONLY_SCHEMA`) it returns names only. Then a smallint status column looks like any number. With distinct values shown, the agent sees a handful of codes and can at least ask what they mean.  
Analogy: A new hire given only a list of table names writes worse queries than one given a data dictionary and a few example rows. Same person, different onboarding.  
Under the hood: Showing more costs tokens, so the design is selective. Types and comments are cheap and always useful. Samples are capped at three rows. Distinct values appear only for low-cardinality columns, where they reveal a coding. Notice what stays invisible: no tool can show that the fiscal year starts in February, because that rule lives in people's heads. That is why the confident wrong answer survives good tools. Enterprise benchmarks show the cost of weak linking: GPT-4-based methods reach 91.2 percent on Spider 1.0, while the best agent, built on o1-preview, solves 21.3 percent of Spider 2.0 (Source 3). LinkAlign measured the share directly: on 500 randomly sampled Spider examples, with the schema retrieved across all databases and fed to DIN-SQL, schema linking errors were the main cause of failures.  
Source 4: LinkAlign, version 3 (https://arxiv.org/html/2503.18596v3), Section 2 error analysis: "schema linking errors are the main cause of Text-to-SQL failures", with an error rate greater than 60 percent; Appendix B: "schema linking errors account for 68.3% of Text-to-SQL failures".  
Transfer: Any agent over an API, a codebase, or a document store has the same step. Before tuning prompts, audit what each tool returns: is the field the agent needs visible, typed, and exemplified? Fix the view before the reasoning.  
Evidence from this course: the paired measurement of 24 October asked seven questions without traps, 3 times each, 21 runs per side, the reviewer off on both sides. With column names only, unbounded rows, and no schema scout, 12 of 21 runs matched gold; with full column descriptions, capped rows, and the scout, 17 of 21. That row mixes three changes, so read it as what happened, not as a rate. The earlier, smaller measurement of 23 October, one run per question, agreed in direction: 4 and 6 of 7.  
Point at: the why line first, then the left column, then the worked example column top to bottom: names only, distinct values, and the rule that stays hidden; then the evidence line and the key-idea bar.  
Re-check after live runs: 12 and 17 of 21 against the paired measurements page.  
Ask: "Which worked-example line would have saved the cancelled-orders trap?" Expected: distinct values; they show the status column is a code, though not what each code means.  
Likely question: "Do sample rows leak data to the model?" Answer: They send a few warehouse rows into the context. Personal-data columns are tagged, and queries that touch them route to human approval in the verification loop.  
Likely question: "Why not send the whole schema up front?" Answer: On a large schema it floods the context with irrelevant tables. Describing on demand keeps the context about the question.  
Transition: Showing more is good. Receiving too much is the next problem.

**Slide 21: 2) Context is a budget: cap at the tool**

Container: two-column cards: how it works | worked example; trade-off and at-work lines; key-idea bar

On the slide:

Principle: the tool, not the prompt, decides how much reaches the model.
Why it matters: a large result is re-sent on every later model call, crowding out the question.

| How it works in DataPilot | Worked example |
|---|---|
| The query tool returns at most 50 rows | A list question over 10,000 rows |
| It adds the total count and a truncation notice | The notice: aggregate, or narrow it |
| A 60,000-token budget, checked before each model call | It stops the uncapped run |

Evidence: uncapped, 182,654 tokens, stopped by the budget; capped, 30,216, reviewer round trip included.
At work: give every list tool a cap, a count, and a truncation notice.
Key idea: budgets in a prompt are hopes; budgets in a tool are facts.

Speaker notes:

Time: 4 minutes (0:19:30-0:23:30)  
Trade-offs, said aloud: a cap can hide needed rows, so the count and notice go with it.  
Plain explanation: Every token a tool returns stays in the conversation and is sent again on every later model call in the loop. So a large tool result is not a one-off cost; it is a tax on every remaining step. The place to bound it is the tool itself.  
Concrete example from DataPilot: The query tool returns at most 50 rows, the row cap in our pack settings, plus the total row count and a notice that the result was truncated. With the planted unbounded rows bug (`BUG_UNBOUNDED_ROWS`) a 10,000-row result goes straight to the model, and you will watch the token counter jump in the demo.  
Under the hood: Measured with the planted bug on, the 10,000-row result took one run to 183,639 tokens and a second run to 185,727, about ten times the capped run and three times our 60,000-token budget per run. The budget is checked before each model call, so the call that carried the rows crossed it and the next was stopped. At the class model's input price of 0.10 dollars per million tokens that is cheap per call, but the result is re-sent on each of up to 12 model calls in the run, and it pushes out the schema and the question. Measured with the cap on, the large query and its list question used 17,298 and 19,661 tokens per run, well inside the budget. The cap keeps the cost small and, more important, keeps the reasoning about the question. The total count and the truncation notice matter as much as the cap: without them the agent may mistake 50 rows for the whole answer. The same idea bounds the output side: each model call has its own output cap, 16,000 tokens for the analyst, reasoning included, and a response cut off at it ends the run escalated with the reason.  
Source 7: LangChain SQL agent (https://docs.langchain.com/oss/python/langchain/sql-agent), in summary: the official tutorial bounds results with a prompt instruction to limit queries, which is a request to the model rather than a property of the tool.  
Transfer: Put a cap, a count, and a truncation notice on every tool that can return a list: search results, log lines, files, API pages. Let the agent ask for the next page if it needs it.  
Evidence from this course: in the paired measurement of 24 October, one run of each half of the unbounded rows demo: without the row cap the run reached 182,654 tokens and 0.0228 dollars and was escalated at its token budget; with the cap, 30,216 tokens and 0.0021 dollars, held for approval after a reviewer concern. Those 30,216 tokens include the reviewer's round trip, so the gap is not the row cap alone. The earlier pair of 23 October agreed in direction: 186,689 against 27,040.  
Point at: the why line, the how-it-works column, then the worked example: the list question, the notice, the budget; then the evidence line; end on the key-idea bar.  
Ask: "What should the agent do when it sees the truncation notice?" Expected: aggregate in SQL instead of reading rows, or ask a narrower question.  
Likely question: "Does the cap ever give a wrong answer?" Answer: Only if the agent ignores the notice. That is why the count and the notice travel with the rows.  
Re-check after live runs: 182,654 and 30,216 tokens against the paired measurements page; the calibration figures, 17,298 and 19,661 tokens capped and 183,639 and 185,727 uncapped, against the calibration report.  
Transition: Now the other side of the loop: what the agent hands back.

**Slide 22: 3) Structured output is a contract**

Container: two-column cards: how it works | worked example; trade-off and at-work lines; key-idea bar

On the slide:

Principle: a structured answer can be checked; a sentence cannot.
Why it matters: a sentence hides its query, and the calendar-year range in it.

| How it works in DataPilot | Worked example |
|---|---|
| Every run returns a typed answer envelope | Status, final query, rows, assumptions |
| Four statuses, two for not answering | Needs clarification, refused |
| An invalid envelope returns as an error | The query shows the calendar year |

Evidence: asked "How many VIP customers do we have?", the run asked what VIP (very important person) means: no rule defines it.
At work: give every agent that feeds software a schema with statuses for not answering.
Key idea: output other code reads needs a contract, not prose.

Speaker notes:

Time: 4 minutes (0:23:30-0:27:30)  
Trade-offs, said aloud: retries spend model calls; a valid shape can still hold a wrong meaning.  
Plain explanation: The agent's final output is an interface. Other code reads it: graders, routers, evaluators, a channel post. An interface needs a schema, and a schema needs enforcement. Free text is an interface only a human can read.  
Concrete example from DataPilot: Every run returns an answer envelope: a status, the final SQL, columns, a rows preview, the row count, the answer text, the assumptions the agent made, and a clarifying question when one is needed. The status has four values: answered, needs clarification, refused, escalated. Every later loop reads these fields. In the board-deck story, the SQL field alone would have let someone see the calendar year in the WHERE clause. One rule came from calibration: the analyst answers with its assumptions stated and recorded, and asks for clarification only when a question names nothing in the schema. Early on, the fiscal year 2025 revenue question came back as a clarifying question, which left the reviewer and the gold check nothing to check.  
Analogy: A pull request with a diff against a message in chat saying it is fixed. Both may be true; only one can be reviewed.  
Under the hood: There are two enforcement strategies. Provider-native structured output asks the model provider to return the schema directly, where the model supports it. The tool-based strategy presents the schema as a tool the model must call; with error handling on, a validation failure goes back to the model as an error message and it tries again. A bare schema lets the framework pick by model profile. Either way the contract also helps consistency. Reasoning models reject a custom temperature, so you cannot buy determinism with a sampling setting. A fixed output shape, explicit assumptions, and repeated measurement are what you control.  
Source 6: Temperature in GPT-5 models (https://community.openai.com/t/temperature-in-gpt-5-models/1337133), in summary: developers report that GPT-5 reasoning models reject a custom temperature value.  
Source 5: LangChain structured output (https://docs.langchain.com/oss/python/langchain/structured-output), in summary: the response format takes a tool strategy, with optional error handling, or a provider strategy, and the result arrives as the structured response.  
Transfer: Give every agent that feeds other software an output schema with a status field, including statuses for not answering. Record assumptions as a list, not prose. Return validation errors to the model instead of crashing.  
Evidence from this course: in the live session of 24 October the question "How many VIP customers do we have?" ended with the status needs clarification. No business rule and no column defines VIP, so the envelope's legal way of not answering is the right outcome, and code downstream can route it instead of posting a guessed number. The analyst's prompt says to answer with stated assumptions and to ask only when a question names nothing in the schema; VIP names nothing.  
Point at: the why line, then the status row: of answered, needs clarification, refused, and escalated, needs clarification and refused are the two ways of not answering; then the evidence line; end on the key-idea bar.  
Ask: "Why does the envelope include needs clarification and refused?" Expected: so not answering is a legal, checkable outcome instead of a guess.  
Likely question: "Which strategy should I choose?" Answer: Provider-native where your model supports it; the tool strategy for portability across models. Measure the retry rate either way.  
Likely question: "Does a schema guarantee a correct answer?" Answer: No. It makes it checkable. Section 2: Verification loop does the checking.  
Misconception: "Structured output is just JSON formatting." Correction: It is a contract with enforcement and a retry path, and it decides what downstream code can verify.  
Transition: One more design decision: whether a second agent belongs here at all.

**Slide 23: 4) A subagent must earn its place**

Container: two-column cards: how it works | why this shape; evidence, trade-offs, and at-work lines; key-idea bar

On the slide:

Principle: add an agent only where judgement is needed; keep it stateless; measure it.
Why it matters: each agent adds calls, latency, and a place for errors.

| How it works in DataPilot | Why this shape |
|---|---|
| The analyst sends the scout the question only | No conversation leaks in |
| The scout explores in its own context, then forgets | Its dead ends never reach the analyst |
| It returns a brief: tables, joins, caveats | Advice only: the analyst still checks |

Evidence: four questions, scout and reviewer on, 8,648 tokens and 24 seconds; scout off, 3,853 and 13; same gold results.
At work: name the judgement, the input, and the short output first.
Key idea: a subagent pays off only as a context boundary you have measured.

Speaker notes:

Time: 4.5 minutes (0:27:30-0:32)  
Trade-offs, said aloud: one more model call and more latency per question.  
Plain explanation: Multi-agent designs are easy to draw and expensive to run. Each agent adds model calls, latency, and a new place for errors. A subagent earns its place when it does a judgement task the main agent does badly, inside a clean context boundary, at a cost you have measured.  
Concrete example from DataPilot: The analyst is one agent with three tools: list tables, describe a table, run a query. Its knowledge is injected by a dynamic prompt. The schema scout sits behind a fourth tool: the analyst calls it with the question, and the scout returns a schema brief of candidate tables, joins, and caveats. The scout is stateless. It sees only the question and the schema, never the conversation, and it can be switched off in the pack settings.  
Analogy: A specialist you consult with a written question and who sends back a one-page memo, rather than a colleague who joins every meeting.  
Under the hood: The stateless boundary is the point. The scout's exploration, every table it described and rejected, stays in its own context. The analyst receives only the brief, so its context stays about the question. That is the same budget argument as concept two, applied to reasoning instead of rows. The cost is real: an extra model call per question and more latency. Whether it pays off is an empirical question, so calibration measured it on four questions, once per configuration. With the scout and the reviewer on, a question averaged 8,648 tokens and 24.2 seconds; with the scout off, 3,853 tokens and 12.8 seconds; with both off, 3,337 and 10.1. The gold results were identical in every configuration. On the two easy questions the scout was rarely called; the gap came from the two trap questions, where the reviewer's concerns sent the analyst back. Four questions are a small sample, so read it as a direction, not a verdict: on these four questions the scout changed no gold result. Notice what we did not do: no supervisor, no agent per table, no debate.  
Source 1: The art of loop engineering (https://www.langchain.com/blog/the-art-of-loop-engineering), in summary: the agent loop is the base of the four loops, and the others wrap it rather than replace it.  
Transfer: Before adding an agent, write down the judgement it makes, the context it needs, and what it returns. If you cannot name a stateless input and a short output, it is probably a tool or a step, not an agent. Then measure with it on and off.  
Point at: the three rows in order: the question going in, the private exploration, the short brief coming back as advice; then the evidence line and the key-idea bar.  
Ask: "What would break if the scout kept memory across questions?" Expected: its answers would depend on earlier questions, which makes them harder to test and to trust.  
Likely question: "Why not a team of agents here?" Answer: Only table selection needs judgement. Everything else is deterministic and belongs in tools.  
Likely question: "What if the scout is wrong?" Answer: Its brief is advisory. The analyst still describes tables itself, and the verification loop checks the result.  
Misconception: "More agents give more reliability." Correction: More agents give more places to fail and correlated errors when they share a model. Reliability comes from checks, which is Section 2.  
Re-check after live runs: the scout's token and latency figures, 8,648 and 3,853 tokens, 24.2 and 12.8 seconds, against the calibration report.  
Transition: The four moves on one slide.

**Slide 24: Cheat sheet: the agent loop in four moves**

Container: table: move, principle, anti-pattern it prevents, check question

On the slide:

| Move | Principle | Anti-pattern it prevents | Check question |
|---|---|---|---|
| Show the schema well | The agent links only what tools show | Names-only schema tools | Can the agent see types, samples, and codes? |
| Cap at the tool | The tool bounds the context | Every row sent to the model | Does every list tool return a cap, count, and notice? |
| Return a contract | Structured answers can be checked | A fluent sentence as output | Can code read the status and the query? |
| Earn each subagent | Agents only for judgement, stateless | A crowd of agents by default | Have you measured it on and off? |

Speaker notes:

Time: 1 minute (0:32-0:33)  
Say: Four moves. Show the schema well, because linking is the bottleneck. Cap at the tool, because context is a budget paid on every call. Return a contract, because only a structured answer can be checked. Earn each subagent, by keeping it stateless and measuring it on and off.  
Point at: the check question column; these four questions are what to ask of your own agents.  
Likely question: "Which move matters most?" Answer: Showing the schema well; every later step depends on what the agent could see.  
Likely question: "Which one would you add first to an existing agent?" Answer: The output contract. It makes every other improvement measurable.  
Transition: Now watch all four live, and watch the fiscal year 2025 revenue question still come out wrong.

**Slide 25: Section 1: Agent loop - Implementation Notes: The confident wrong answer**

Container: demo layout: laptop and badge, what to watch for, guaranteed moment, link

On the slide:

Badge: DEMO - 1
What to watch for:
- The simple question: list, describe, one query, then an envelope with its Structured Query Language (SQL)
- The confident wrong answer: a fluent number, a mismatch against gold, each trap named on the SQL
- Unbounded rows: the token counter, cap off, then on
Guaranteed moment: under the starting knowledge, the fiscal year 2025 revenue question gets a confident, wrong answer; the gold check shows the mismatch and the annotated SQL names each trap.
Link: Demo page on GitHub | https://github.com/ANI-IN/loop-engineering/tree/main/section-1-agent-loop/demo#the-confident-wrong-answer

Speaker notes:

Time: 17 minutes (0:33-0:50)  
Run sheet: about 12 minutes for three core demos on the console Agent page, then about 5 minutes of code walkthrough in the editor. Share the console full screen; keep the editor and a terminal in separate windows. Every core demo's moment has been shown live, in calibration retakes and again on 24 October, both halves of unbounded rows and the optional demo included; rehearse each twice in a row with a reset between before class (instructor guide, the day before, step 4). The measured figures are under each demo. The slide's link opens the section's demo page on GitHub, the page learners use after class.  
Demo: the simple question.  
Guaranteed moment, from the demo registry: The analyst lists tables, describes one, runs one query, and returns an answer envelope with the SQL and the result; the tool timeline shows each call with its duration.  
Starting state: the Agent page, version 1 of the knowledge (the starting version) active, no planted item on, the status line at the report-only level. Reset first: `make reset NAME=agent-loop`.  
Do: on the Agent page type "How many orders have been placed in total?", the question `make demo` sends, and press Ask; or `make demo NAME=agent-simple-question`.  
Narrate: this is the loop working as designed. Tie it to concept 1, Schema linking: watch the analyst list tables, describe one, and see types, samples, and distinct values before it writes SQL. Tie it to concept 3, Structured output is a contract: the answer comes back as an envelope with its SQL.  
Point at, in order: the tool timeline (list tables, describe table, run query, each with its duration); the envelope's status and final SQL; the tokens and cost; and last the live stamp: the run's start time in your local time and its trace link.  
Expected live result: a correct count with its SQL, tokens, cost, and a LangSmith trace link. Measured: 37 and 39 seconds from trigger to result; one analyst run costs about 0.001 dollars. Shown again live on 24 October.  
May vary: the analyst's wording, the number of tool calls, latency, tokens. If it does, say: the path varies run to run because the model reasons freshly each time; the contract and the SQL are what we check.  
If it stalls: reset and run it again, `make reset NAME=agent-loop`, then the same trigger.  
Demo: the confident wrong answer.  
Guaranteed moment, from the demo registry: Under version 1 of the knowledge (the starting version), the fiscal year 2025 revenue question, "What was our net revenue in fiscal year 2025?", gets a confident, wrong answer; the answer-versus-gold ledger shows the mismatch and the annotated SQL names each trap behind the wrong fragments.  
Starting state: the same page after the first demo; version 1 still active. Reset first if anything else ran: `make reset NAME=agent-loop`.  
Do: Agent > Ask the spine question, or `make demo NAME=agent-confident-wrong-answer`.  
Narrate: the fiscal year 2025 revenue question, what was our net revenue in fiscal year 2025. Tie it to the question slide: a stronger model would not help, because the rules are not in the schema. Tie it to concept 1: the tools showed everything they could, and the fiscal year rule is still invisible.  
Point at, in order: the confident answer text; the answer-versus-gold ledger showing the mismatch; the annotated SQL, where each note names a trap behind a fragment (the calendar year, `total_cents`, cancelled orders left in, internal accounts left in); and last the live stamp: the run's start time in your local time and its trace link.  
Expected live result: a mismatch against gold with at least one trap note on the SQL. Measured: in 76 seconds, 76,981,355.95 dollars against gold 64,015,091.21, with 4 trap labels; retaken twice, both shown, 72,394,572.08 dollars with 3 trap labels each, then held by two reviewer concerns; under the starting knowledge 0 of 99 trap runs passed in calibration. Shown again live on 24 October.  
May vary: which traps the SQL hits, the wrong value, the wording, and whether the run posts or holds. If it does, say: the exact mistake varies, the fact of a mistake does not, because the knowledge it needs is absent. If the strip shows held for approval, say: that is the reviewer from Section 2: Verification loop raising a concern, which it did on this answer in calibration; the gold check still shows the mismatch.  
If it stalls: reset and run it again, `make reset NAME=agent-loop`, then the same trigger. In calibration the second attempt got no gold check within 90 seconds; the gold checks were hardened the same night so one run can never block another, and both retakes got their gold check. A run that gives no number gets no gold check: reset and ask again.  
Demo: unbounded rows.  
Guaranteed moment, from the demo registry: With the unbounded rows bug on, a 10,000-row SELECT goes through run_query and a list question follows; the token counter spikes. With it off, the same steps return at most the row cap, the total count, and a truncation notice.  
Starting state: the Agent page, on the fixed system; the planted half switches the unbounded rows bug (`BUG_UNBOUNDED_ROWS`) on for its own run only, and its chip shows on the status line once the run starts. Reset first: `make reset NAME=agent-loop`.  
Do: `make demo NAME=agent-unbounded-rows PLANTED=1`, the bug on for that run; then Agent > Run large query, or `make demo NAME=agent-unbounded-rows`, with it off.  
Narrate: tie it to concept 2, Context is a budget. With the bug on, a 10,000-row result goes to the model and every later call carries it. With it off, the tool returns the row cap, the total count, and the truncation notice.  
Point at, in order: the token counter with the bug on; the same counter with it off; the truncation notice and the total count under the rows; and last the live stamp: the run's start time in your local time and its trace link.  
Expected live result: tokens per run jump with the bug on and drop back with it off. Measured in calibration with the bug on: 183,639 and 185,727 tokens per run, stopped by the run budget after 18 or 19 seconds. With the bug off: 19,661 and 17,298 tokens per run; one of the two runs was held by a reviewer concern, which does not change the token story. In the paired measurement of 24 October: 182,654 tokens without the cap, escalated at the run budget, against 30,216 with it, held after a reviewer concern; on 23 October, 186,689 against 27,040.  
May vary: exact token counts, the list question's wording. If it does, say: the size of the jump depends on the rows, but the direction never changes.  
If it stalls: reset and run it again, `make reset NAME=agent-loop`, then the same trigger.  
Optional, cut first: Texas last quarter (`make demo NAME=agent-texas-last-quarter`), a four-table join for Texas customers over the last completed fiscal quarter, August to October 2025 against the business date of 31 January 2026, with the join path visible in the SQL. Say "last completed fiscal quarter": on 31 January the current fiscal quarter is still open. Shown live on 24 October.  
Code walkthrough: about 5 minutes, in the order of the section's demo walkthrough page.  
Open `platform/src/datapilot/loop1_agent/analyst.py`, lines 56-58: the knowledge injection, the base of concept 1, Schema linking, and of the confident wrong answer. Say: the dynamic prompt writes the base prompt, the business date, and the active knowledge version before every model call; under version 1 that block holds only the money rule, so the traps decide the answer. A new version changes this block and nothing else.  
Open `platform/src/datapilot/loop1_agent/analyst.py`, lines 72-86: implements concept 3, Structured output is a contract, and the stops of concept 2. Say: one `create_agent` call; `ToolStrategy(AnswerEnvelope)` makes the answer a typed object the graders read; the model call limit ends the run at 12 calls and the tool call limit answers extra calls with an error at 16; `*middleware` is where later loops add the run guard, the kill switch, and approvals.  
Open `platform/src/datapilot/loop1_agent/tools.py`, lines 33-54: implements concept 2, Context is a budget, and is the unbounded rows demo. Say: the cap lives in the tool, so no prompt wording can lift it; the result carries the total row count and a notice that tells the model what to do next; `cap_values` cuts any value longer than 2,000 characters, because one row can hold an array of every address; the planted branch for `BUG_UNBOUNDED_ROWS` is one guarded line, never a fake model output.  
If time allows, the same file's describe tool shows concept 1: types, three sample rows, and distinct values; and concept 4's scout sits behind one more tool. Neither has a line range on the walkthrough page, so open them by name only if asked.  
Transition: Questions before we add the verification loop.

**Slide 26: Questions**

Container: fixed question layout

On the slide:

No Question Is Too Small Every Question Deserves an Answer!!
Why not put the rules in the prompt? Does the scout pay for itself?

Speaker notes:

Time: 3 minutes (0:50-0:53)  
Say: Take questions. Two likely ones are on the slide; send anything long to the Thursday parking lot.  
Point at: the two questions on the slide.  
Likely question: "Why not put the business rules in the prompt now?" Answer: Because we want to show what earning them looks like. The starting knowledge version is almost empty on purpose, so every trap fails in class and the hill-climbing loop has something to improve and measure.  
Likely question: "Does the scout cost more than it saves?" Answer: On four questions it changed no gold result, and the runs with it on cost more tokens and seconds. On a schema with hundreds of tables the answer can flip, which is the point of measuring with it on and off.  
Likely question: "Why not ask the model to double-check its own SQL?" Answer: That is the same model grading itself. Section 2 puts deterministic checks first.  
Transition: If time is short, skip the reference slides and go to Section 2: Verification loop.

**Slide 27: Reference: skip if short on time - tool output design**

Container: table with a how-to-read line

On the slide:

How to read this: each row is one choice; the last column says what it buys or risks.

| Show | Withhold | Why |
|---|---|---|
| Types, comments | Internal notes | Cheap, always useful |
| Three sample rows | Bulk rows | Formats help; text can inject |
| Distinct values, small columns | Distinct values, large columns | Reveals codes cheaply |
| Total count, truncation notice | Rows past the cap | Honest about size |

Speaker notes:

Time: 1 minute (0:53-0:54)  
Plain explanation: Every tool result is a design choice between helping the agent link words to data and spending its context. This table is the checklist we used.  
Concrete example from DataPilot: A few product names in the warehouse carry prompt-injection text, such as a request to delete data. Sample rows show them to the model. That is the double edge: the same rows that teach formats also carry text the model may follow.  
Analogy: Showing a contractor the building plans helps them work; it also shows them where the safe is. You give the plans and still lock the safe.  
Under the hood: Withholding is not the defence against injection; the defence is that nothing the model writes can modify data. The read-only role and the syntax-tree guard in Section 2: Verification loop render an injected instruction harmless, and a security suite proves no write happens. So we keep samples small and keep the hard boundary below the model.  
Source 4: LinkAlign, version 3 (https://arxiv.org/html/2503.18596v3), Appendix B: "schema linking errors account for 68.3% of Text-to-SQL failures".  
Transfer: For any tool that returns external content, such as web pages, tickets, or emails, assume the content can carry instructions. Show what helps, and put the boundary in permissions, not in the prompt.  
Point at: the sample rows row and its last cell.  
Ask: "Would you remove sample rows to stop injection?" Expected: no; keep them small and block writes below the model.  
Likely question: "How many samples are enough?" Answer: Three shows formats without spending much context; more rarely adds information.  
Likely question: "Should comments explain business rules?" Answer: Neutral comments only. Business rules belong in versioned knowledge you can gate and roll back.  
Misconception: "Hiding data from the model makes it safe." Correction: Safety comes from what the model is allowed to do, not from what it is allowed to see.  
Transition: Next reference: strategies for structured output.

**Slide 28: Reference: skip if short on time - structured output strategies**

Container: table with a how-to-read line

On the slide:

How to read this: rows run from strongest to weakest enforcement; read the failure mode before you choose.

| Strategy | Enforced by | Failure mode |
|---|---|---|
| Provider-native | The model provider | Not every model supports it |
| Tool-based | A required tool call | Validation error, model retries |
| Prompt-only JavaScript Object Notation (JSON) | Nothing | Parse errors, silent drift |

Speaker notes:

Time: 0.5 minutes (0:54-0:54:30)  
Plain explanation: There are three ways to get a structured answer from a model, and they differ in who enforces the shape and what happens when it breaks.  
Concrete example from DataPilot: The answer envelope is requested through the framework's response format. The analyst's output either validates as an envelope or the validation error goes back to the model for another attempt, inside the run's call limits.  
Analogy: A typed function signature, a runtime validator, and a comment saying please return a dictionary.  
Under the hood: Provider-native output asks the provider to return the schema directly where the model supports it. The tool strategy turns the schema into a tool the model must call; with error handling on, a validation failure becomes a message the model can fix. A bare schema lets the framework choose by model profile. Prompt-only JSON has no enforcement and no retry path, so failures surface downstream. Every retry counts against the run's 12 model calls.  
Source 5: LangChain structured output (https://docs.langchain.com/oss/python/langchain/structured-output), in summary: tool strategy with optional error handling, provider strategy, or a bare schema chosen by model profile.  
Transfer: Choose provider-native when your model supports it, the tool strategy when you need portability, and never prompt-only for output other code reads. Log the retry rate.  
Point at: the failure mode column.  
Ask: "Which strategy hides failures longest?" Expected: prompt-only JSON.  
Likely question: "Do retries hide a bad prompt?" Answer: They can; a rising retry rate is a signal to fix the schema or the instructions.  
Likely question: "Can a valid envelope still be wrong?" Answer: Yes. Valid shape, wrong meaning is exactly the next section's problem.  
Misconception: "Schema validation proves correctness." Correction: It proves shape only.  
Re-check after live runs: the 12-call limit against the pack settings, and the analyst's output cap of 16,000 tokens per call.  
Transition: Last reference: the five traps.

**Slide 29: Reference: skip if short on time - five traps**

Container: table with a how-to-read line

On the slide:

How to read this: the category column names the kind of knowledge to look for in your own data.

| Trap | Missing knowledge | Category |
|---|---|---|
| Fiscal year | February to January | Calendar convention |
| Net revenue | Not the total column | Metric definition |
| Cancelled orders | Status 5 excluded | Undocumented code |
| Eastern time | Business day boundary | Time zone |
| Internal accounts | Company email domain | Hidden population |

Speaker notes:

Time: 0.5 minutes (0:54:30-0:55)  
Plain explanation: Each trap is a kind of business knowledge that real schemas rarely carry. Naming the category helps you find the same gaps in your own data.  
Concrete example from DataPilot: The fiscal year runs February to January and is named for its end year. Net revenue is subtotal minus discount, never `total_cents`, which includes tax and shipping. Cancelled orders carry an opaque status code 5. Business days are in Eastern time, so evening orders cross the UTC date. Internal accounts are known only by the company email domain; there is no flag column.  
Analogy: The unwritten rules a new analyst learns in their first month, usually by getting a number wrong in a meeting.  
Under the hood: Each trap was chosen so the schema gives no hint. The internal accounts trap uses an email domain because a visible flag column is solved unaided; internal accounts hold exactly 3 of the top 10 revenue spots in each fiscal year, about 2.49 percent of revenue on the main warehouse. Calibration ran every trap item three times under the starting knowledge, 99 runs, and none passed, so no trap needed strengthening. The labels most often attached to the wrong SQL were the missing internal-account filter, the missing status filter, the calendar-year range, and UTC truncation. This is the same gap BIRD's evidence fills: with it, GPT-4 rises from 34.88 to 54.89 percent on the BIRD test set.  
Source 2: BIRD (https://arxiv.org/abs/2305.03111), in summary: questions come with external-knowledge evidence, and all models improve when given it.  
Transfer: List the categories for your own domain: calendars, metric definitions, codes, time zones, hidden populations such as test accounts. Each is a candidate rule for a knowledge version.  
Point at: the category column.  
Ask: "Which category exists in your data?" Expected: usually test accounts and metric definitions.  
Likely question: "Why five traps?" Answer: Each changes a naive answer on its own, and together they cover the common categories.  
Likely question: "Is money in cents a trap?" Answer: No; the column suffix makes it visible, so it stays a rule, not a trap.  
Misconception: "Good naming would remove these." Correction: Names help with codes; they cannot carry a calendar or a metric definition.  
Transition: Section 2: Verification loop checks what the agent returns.

## Section 2: Verification loop

The failure this section fixes: Checks that read like safety let unsafe SQL reach the database, let a failing loop spend without end, and pass an answer that is safe, well formed, and wrong.

Measured live: in calibration, each core demo twice with a reset between: malicious SQL shown in 6 seconds both times, the syntax-tree guard stopping two statements and the role's missing grant the third with SQLSTATE 42501, and with the naive guard 25006, 25006, then 42501; the retry cap shown in 79 and 69 seconds, escalated after 3 attempts; every grader passes, still wrong: not shown in either attempt, because the graders passed but no gold check arrived within 90 seconds (hardened the same night); retaken twice on 23 October, both shown, 76,981,355.95 dollars against gold 64,015,091.21 with 4 trap labels each; the retry cap planted half, twice, 9 attempts until the 60,000-token run budget stopped it, at 62,762 and 63,737 tokens. In the paired measurement of 23 October: malicious SQL, all 3 statements reached the database with the naive guard and 2 were stopped by the guard with the syntax-tree guard; the retry cap, 11 attempts and 63,718 tokens without it, 3 attempts and 12,682 tokens with it; six trap questions, 0 of 6 correct either way, the reviewer holding 1 of 6. In the live session of 24 October every core and optional demo showed its moment, both halves; without the retry cap the agent escalated by itself after 4 attempts, 19,960 tokens, against 3 attempts and 10,573 tokens with it; on 20 trap questions twice each, 0 of 40 correct either way, the full layer holding or escalating 20 wrong answers against 1, the reviewer approving the other 19.

The demo: `make demo NAME=verify-malicious-sql`, `make demo NAME=verify-retry-cap`, `make demo NAME=verify-graders-pass-still-wrong`, launched at 1:19 on the DEMO slide, code walked at 1:31, recovery `make reset NAME=verification-loop` and re-run: reset and run it again, live.

| # | Slide | Layout | Time (start-end) | Says in one line | Source in the repository |
|---|---|---|---|---|---|
| 30 | Agenda (Section 2 highlighted) | concept | 0:55-0:55:30 | Section 2: Verification loop, after the agent loop | section-2-verification-loop/README.md |
| 31 | Failure story: the product name that said delete | diagram | 0:55:30-0:57:30 | Illustrative: an instruction hidden in data reaches SQL, and only the last layer stops it | section-2-verification-loop/concepts.md |
| 32 | Verification loop: if every grader passes, is the answer right? | concept | 0:57:30-1:00 | KEY IDEA: No. Graders prove a query is safe and well formed, not that it means what the business means | section-2-verification-loop/README.md |
| 33 | 1) Allowlist the shape, not a list of bad words | diagram | 1:00-1:05 | Key idea: accept only shapes you can name; reject everything else, including what the parser cannot model | measured for the course (sqlglot guard) |
| 34 | 2) Permissions are the boundary, not the parser | table | 1:05-1:09:30 | Key idea: a session can switch a default off; it cannot grant itself a privilege | measured for the course on PostgreSQL 16.2 during research (read-only role); compose.yaml (PostgreSQL 18.6) |
| 35 | 3) Stops that are not the model's choice | table | 1:09:30-1:13:30 | Key idea: every loop needs a stop the model cannot argue with, placed before the next model call | platform/packs/datapilot_us/pack.yaml (limits, cost_guard); Sources 11 and 12 (middleware) |
| 36 | 4) A checker that shares the maker's blind spots | table | 1:13:30-1:18 | Key idea: judgement goes after the deterministic checks, and a checker on the same model shares its errors | platform/src/datapilot/contracts/agents.py; Source 8 (test-suite accuracy) |
| 37 | Cheat sheet: verification in four moves | table | 1:18-1:19 | Allowlist the shape, scope the credential, cap the loop, decorrelate the checker | section-2-verification-loop/README.md |
| 38 | Section 2: Verification loop - Implementation Notes: Every grader passes, still wrong | demo | 1:19-1:37 | Badge DEMO - 2, what to watch for, the guaranteed moment, and the demo page link; the demos and the code walkthrough are in the notes | section-2-verification-loop/demo/walkthrough.md; platform/demos/registry.yaml |
| 39 | Questions | concept | 1:37-1:42 | No Question Is Too Small Every Question Deserves an Answer!! Likely: why two databases; can the reviewer be fooled | - |
| 40 | Reference: skip if short on time - attack patterns | table | 1:42-1:43 | Seven attack patterns a syntax-tree guard must handle, and the defense for each | measured for the course (sqlglot guard) |
| 41 | Reference: skip if short on time - database errors as feedback | table | 1:43-1:44 | Map each database error to feedback the agent can act on, and to retry or stop | Source 10 (PostgreSQL error codes) |
| 42 | Reference: skip if short on time - why one database lies | diagram | 1:44-1:45 | A wrong query can match on one database by coincidence; distinguishing rows expose it | Source 8 (test-suite accuracy) |

Numbers this section states (each gets a "Re-check after live runs" line in its notes):

- Retry cap of 3: from `limits.max_retries` in pack.yaml.
- 12 model calls and 16 tool calls per run: from `limits.model_call_limit` and `limits.tool_call_limit` in pack.yaml.
- Statement timeout of 5,000 milliseconds: from `limits.statement_timeout_ms` in pack.yaml.
- Plan cost cap 500,000 and plan rows cap 5,000,000: from `cost_guard` in pack.yaml.
- 6.5 percent mean false-positive rate of single-database execution match, 11.0 percent on extra-hard queries, about 1,000 fuzzed databases per schema, about 42 kept per query, 2.5 percent false negatives: from Source 8.
- SQLSTATE 25006, 42501, 57014: from Source 10 and runs measured for the course on PostgreSQL 16.2 during research; the class stack runs PostgreSQL 18.6.
- Malicious SQL: fixed system guard, guard, then 42501 from the missing grant; naive guard 25006, 25006, then 42501: docs/calibration-report.md, Demos.
- Retry cap demo: escalated after 3 attempts, in 69 and 79 seconds: docs/calibration-report.md, Demos; without the cap, 9 attempts until the 60,000-token run budget, 62,762 and 63,737 tokens, 0.0067 and 0.0069 dollars, 104 and 111 seconds: docs/calibration-report.md, Resumed after the ledger correction.
- Every grader passes, still wrong, retaken twice: 76,981,355.95 dollars against gold 64,015,091.21, 4 trap labels each: docs/calibration-report.md, Resumed without traces.
- The reviewer's verdict on the wrong answer to the fiscal year 2025 revenue question under the starting knowledge: concern in 6 runs, approve in 1: docs/calibration-report.md, Agents on and off.
- Mean tokens and seconds per question with the reviewer off, 5,786 and 12.8, against 8,648 and 24.2 with the scout and reviewer on: docs/calibration-report.md, Agents on and off.
- Class code guesses at an undefined term in 5 of 8 runs; the reviewer turns most guesses into a held or escalated answer: docs/calibration-report.md, Agents on and off.
- Output cap per call, reasoning included: analyst 16,000 tokens, reviewer 8,000: `models` in pack.yaml.
- Malicious SQL, one run of each half: with the naive guard all 3 statements reached the database (25006 twice, then 42501); with the syntax-tree guard 2 stopped by the guard, the third by the grants (42501); the orders table unchanged in both: docs/benefits.md, Section 2: Verification loop.
- Retry cap, one run of each half: 11 attempts, 63,718 tokens, 0.0068 dollars without the cap; 3 attempts, 12,682 tokens, 0.0014 dollars with it: docs/benefits.md, Section 2: Verification loop.
- Six trap questions under the starting knowledge: 0 of 6 correct with or without the verification layer; the reviewer raised 2 concerns, 1 held and 1 sent back: docs/benefits.md, Section 2: Verification loop.
- Every core and optional demo of the section showed its moment, both halves: docs/calibration-report.md, Live session of 24 October 2026.
- On 24 October, the retry cap: 4 attempts and 19,960 tokens without it, the agent escalating by itself, against 3 attempts and 10,573 tokens with it; 20 trap questions twice each: 0 of 40 correct either way, 1 against 20 wrong answers held or escalated (17 held, 3 escalated), the reviewer approving the other 19: docs/benefits.md, Section 2: Verification loop.

### Slides and speaker notes: Section 2: Verification loop

**Slide 30: Agenda (Section 2 highlighted)**

Container: step cards: four sections, the second highlighted

On the slide:

1. Agent loop
2. Verification loop (now): what checks answers and stops loops
3. Event loop
4. Hill-climbing loop

Speaker notes:

Time: 0.5 minutes (0:55-0:55:30)  
Say: Section 1: Agent loop gave us an agent that answers with its SQL in a structured envelope. That envelope is something we can check, and this section is about checking it. We add a verification loop around the agent: deterministic graders that look at every query before it runs, at every result after it runs, and at the final answer. Failures go back to the agent with a reason it can act on. Then one independent agent, the reviewer, reads the answer after every grader has passed. The point to carry through the section: verification is a set of layers, each built on the assumption that the one above it fails, and a set of stops that the model does not get to choose.  
Point at: the highlighted second row; Section 1 is done and its answer is still wrong.  
Likely question: "Does a verification loop slow every answer down?" Answer: The graders are deterministic and cheap; the expensive part is the reviewer, one extra model call per answer, and calibration measures that cost so you can decide whether it pays.  
Transition: Let me start with a story about a product name.

**Slide 31: Failure story: the product name that said delete**

Container: step cards: five numbered beats, then a lesson bar

On the slide:

Illustrative
1. **Upload**: a supplier feed adds a product whose name asks the reader to delete old orders.
2. **Context**: the agent describes the products table; three sample rows put that name in its prompt.
3. **Query**: its next query is a SELECT, a semicolon, and a DELETE on orders.
4. **Guard**: a first-word check sees SELECT and lets the whole text through.
5. **Last layer**: only the role's missing write grant refuses it, a defense nobody designed as the main one.
Lesson: a check that reads the first word is a sign on the door, not a lock.

Speaker notes:

Time: 2 minutes (0:55:30-0:57:30)  
Say: This story is illustrative, and the person in it, Marcus, is fictional. Marcus runs the analytics agent at Harbor & Pine Outfitters. Beat one: a supplier upload leaves a product whose name reads like an instruction, asking whoever reads it to delete the old orders. Beat two: the agent describes the products table, and the sample rows put that name into its context. Beat three: the next query it writes is a SELECT followed by a semicolon and a DELETE. Beat four: the guard in front of the database checks that the text starts with SELECT, and it does. Beat five: the only thing that stops the delete is that the database role has no write grant. Nobody designed that role as the main defense; it just happened to be there. Elsewhere the same week, a check that always fails sends a run back to the model again and again, and the bill climbs until someone notices.  
Point at: beat five, the last layer doing the work every other layer claimed to do.  
Likely question: "Is prompt injection through data realistic for an internal analytics tool?" Answer: Any text the agent reads is input to the model, and sample rows are text; the class data carries a few such product names on purpose, and the security suite proves no write happens.  
Transition: So, if we add enough checks and they all pass, are we done?

**Slide 32: Verification loop: if every grader passes, is the answer right?**

Container: key-idea box with three reason cards

On the slide:

If every grader passes, is the answer right?
KEY IDEA: No. Graders prove a query is safe and well formed, not that it means what the business means.
- The fiscal year 2025 revenue query is one cheap SELECT on real tables, so every grader passes.
- The fiscal year rule and the cancelled-order rule live in no grader.
- Even a result match on one database shows about 6.5 percent false positives.

Speaker notes:

Time: 2.5 minutes (0:57:30-1:00)  
Say: No. Take the fiscal year 2025 revenue question from Section 1, net revenue in fiscal year 2025. The query the agent writes is one statement, a plain SELECT, on tables that exist, cheap to run, touching no personal data, and it returns one sensible number. Every grader we build in this section passes it. It is still wrong, because the fiscal year starts in February and cancelled orders should not count, and no grader knows that. Graders check safety and form; meaning needs business knowledge, which arrives in Section 4: Hill-climbing loop. Even comparing results is weaker than it looks. Source 8: Semantic Evaluation for Text-to-SQL with Distilled Test Suites (https://arxiv.org/abs/2010.02840): "hence calculating a tight upper-bound for semantic accuracy efficiently." The paper's point is that matching a result on one database is an upper bound on correctness, not proof: single-database execution match had a 6.5 percent mean false-positive rate across 21 Spider submissions.  
Point at: the KEY IDEA box, then the two words safe and means.  
Likely question: "Then why build graders at all?" Answer: They stop unsafe and malformed work before it runs, and they hand the agent a reason it can act on, which is most of what a retry loop needs.  
Transition: Concept one: what a guard should accept.

**Slide 33: 1) Allowlist the shape, not a list of bad words**

Container: two-column cards: how it works | worked example, with trade-offs, at-work, and key idea bars

On the slide:

Principle: accept only query shapes you can name; reject everything else.
Why it matters: a first-word check sees SELECT and lets a stacked DELETE through to the database.

| How it works in DataPilot | Worked example |
|---|---|
| Parse: exactly one statement | "SELECT 1; DELETE FROM orders": rejected |
| Walk the tree: no write, lock, or command | A DELETE inside a WITH clause: rejected |
| Denied functions; an allowed schema list | pg_sleep, dblink, set_config: denied |
| Run the original text, not a regenerated one | COPY ... TO PROGRAM came back mangled |

Evidence: naive guard, all three statements reached the database; tree guard, two never ran.
At work: parse what your agent emits; run exactly what you checked.
Key idea: an unknown shape is a rejection, not a pass.

Speaker notes:

Time: 5 minutes (1:00-1:05)  
Trade-offs, said aloud: a false reject costs a retry; the tree cannot see inside strings.  
Plain explanation: A denylist names the bad things: no DELETE, no DROP. Attackers and parsers both find shapes you did not list. An allowlist names the one shape you accept, a single read-only query, and rejects everything else, including anything the parser could not understand. The guard walks the whole syntax tree, not the first word.  
Concrete example from DataPilot: the naive guard (`BUG_NAIVE_GUARD`) checks that the text starts with select or with. It passes "SELECT 1; DELETE FROM orders" and a data-modifying CTE, because both start with a SELECT. The syntax-tree guard rejects both before execution: the first parses to two statements, the second has a Delete node under a Select root.  
Analogy: a building that lists banned items at the door versus one that lets in only people holding a badge. The first fails on every item nobody thought to list.  
Under the hood: parsed with sqlglot in the Postgres dialect, SELECT INTO appears as an Into node and FOR UPDATE as a Lock node; neither looks like a write at the root. DO, CALL, VACUUM, EXPLAIN ANALYZE, PREPARE and EXECUTE fall back to an opaque Command node, so the guard rejects Command outright. `LISTEN foo` and `TABLE orders` misparse as aliases, which is why a parse that looks harmless is still not proof. Regenerating SQL from the tree can change meaning, so the executor runs the original text the guard approved. A function denylist covers calls such as `pg_sleep`, `dblink`, `query_to_xml`, and `set_config`, and a schema allowlist keeps every table inside the warehouse schema. One more rule came from calibration: agent SQL may not read the database clock, so `now()`, `current_date`, and the special date word today are rejected with feedback. A question about the previous day had answered 0, because the SQL read the wall clock while the data ends on the business date the prompt states.  
Source 7: LangChain SQL agent (https://docs.langchain.com/oss/python/langchain/sql-agent), in summary: the official tutorial checks queries with an LLM query checker and states the no-DML rule as a prompt instruction. Neither is a boundary.  
Transfer: the same rule applies to any agent that emits a language: shell commands, infrastructure plans, API calls built from text. Parse it, accept a named shape, reject the rest, and execute exactly what you checked.  
Evidence from this course: in the paired measurement of 24 October, one run of each half of the malicious SQL demo. With the naive guard, all 3 statements reached the database and were refused there: 25006 twice, from the read-only transaction, then 42501, from the role's grants. With the syntax-tree guard, 2 were stopped by the guard and the third by the grants. The orders table was unchanged in both halves. The pair of 23 October showed the same.  
Point at: the why line, then the How it works column, top to bottom; every row is a reason to reject, and the Worked example column shows the shape it catches; then the evidence line.  
Re-check after live runs: the layers that stopped each statement against the paired measurements page.  
Ask: "Why execute the original text instead of the tree's regenerated SQL?" Expected: regeneration is lossy; the text you checked must be the text that runs.  
Likely question: "Will an allowlist reject legitimate queries?" Answer: Sometimes, and the reason goes back to the agent, which rewrites the query; a false reject costs a retry, a false accept costs data.  
Likely question: "Why not use the database's own parser?" Answer: You can, through EXPLAIN, but it accepts every valid statement, writes included; you still need a policy on the shape.  
Transition: so what actually stops the statement the parser cannot see?

**Slide 34: 2) Permissions are the boundary, not the parser**

Container: table: layer | can the session undo it, with worked-example, trade-offs, at-work, and key idea bars

On the slide:

Principle: put the last defense where the agent's own session cannot change it.
Why it matters: every parser has a blind spot, so something below the guard must refuse the write.

| Layer | Can the session undo it? |
|---|---|
| Prompt rule | Yes: the model can ignore it |
| Read-only transaction default | Yes: one SET turns it off |
| Temporary tables | Open until revoked from the public role |
| Missing write grant | No: insufficient privilege, error 42501 |

Evidence: in a read-only transaction a write fails with error 25006; with that default switched off, the missing grant still refuses it, 42501.
At work: scope the credential, not the instruction; probe the barrier at startup.
Key idea: defaults are preferences; grants are walls.

Speaker notes:

Time: 4.5 minutes (1:05-1:09:30)  
Trade-offs, said aloud: grants are coarse and need one role per agent; the guard still gives early reasons.  
Plain explanation: every layer above the database is code you hope is right. The database role is the one layer the agent's own session cannot rewrite, as long as the barrier is a missing grant rather than a default setting. Defaults are preferences; grants are walls.  
Concrete example from DataPilot: the agent connects as a role with SELECT on the warehouse schema and nothing else. The executor also opens every query with `SET TRANSACTION READ ONLY`, and the process refuses to start unless a probe write inside a read-only transaction fails. Temporary tables and schema creation are revoked from the public role. A write the database refuses is an incident, not a mistake to retry: the run ends escalated at once.  
Analogy: a sign on a door that says staff only, versus a door with no key cut for you.  
Under the hood: tested on PostgreSQL 16.2 during research; the class stack runs 18.6, where the read-only probe at startup checks the same barrier. Inside `BEGIN READ ONLY`, an INSERT or CREATE TEMP raises SQLSTATE 25006 even as superuser. But a session can run `SET default_transaction_read_only = off`, and after that an INSERT failed with 42501 only because the role lacked the grant. CREATE TEMP TABLE succeeded until `REVOKE TEMP ON DATABASE ... FROM PUBLIC`. And `dblink` or `query_to_xml` can run SQL held inside a string, which no syntax tree sees; only the grants stop what those strings try to do.  
Source 9: PostgreSQL ALTER ROLE (https://www.postgresql.org/docs/current/sql-alterrole.html): "Role-specific variable settings take effect only at login; SET ROLE and SET SESSION AUTHORIZATION do not process role-specific variable settings." A role setting is a session default, applied at login, not a barrier.  
Transfer: for any agent with credentials, scope the credential, not the instructions. Read-only API tokens, least-privilege cloud roles, per-agent database users. Then test the barrier at startup the way the probe does, and refuse to run if it is missing.  
Evidence from this course: the evidence line was measured for the course on PostgreSQL 16.2 during research. In the class stack the malicious SQL demo shows the same barrier: with the naive guard, the read-only transaction refused two statements with 25006 and the role's missing grant refused the raw DELETE with 42501, and no warehouse row changed.  
Point at: the why line, then the two rows that answer yes; those are the layers an attacker can switch off.  
Ask: "Which row would you test in continuous integration?" Expected: the grant row, with a probe that must fail.  
Likely question: "If the role is the real boundary, why keep the guard?" Answer: the guard rejects early with a reason the agent can use, and it blocks reads the role allows but you do not want, such as `pg_sleep` or reading server files.  
Likely question: "Why revoke temporary tables if they vanish anyway?" Answer: a writable temp table is a place to stage data and a way around read-only assumptions; the probe found it open by default.  
Misconception: a read-only transaction makes the session read-only. Correction: the session can turn the default off; only the missing grant holds.  
Re-check after live runs: the SQLSTATE codes the malicious SQL demo shows against these.  
Transition: the database can stop a statement; who stops the loop?

**Slide 35: 3) Stops that are not the model's choice**

Container: table: stop | value | then, with worked-example, trade-offs, at-work, and key idea bars

On the slide:

Principle: every loop needs a stop the model cannot argue with, checked before the next model call.
Why it matters: a failing check sends the run back again and again; the bill climbs.

| Stop | Value | Then |
|---|---|---|
| Attempts per run | 3 | Escalated, with every reason |
| Model calls, tool calls per run | 12, 16 | Run ends |
| Statement timeout | 5 seconds | Cancelled, error 57014 |
| Planned cost or rows | 500,000 or 5,000,000 | Rejected before it runs |

Evidence: without the cap, 4 attempts, 19,960 tokens, until the agent chose to stop; with it, 3 attempts, 10,573 tokens.
At work: put budgets and retries where every iteration passes.
Key idea: a stop inside a tool is a suggestion; before the model call, a fact.

Speaker notes:

Time: 4 minutes (1:09:30-1:13:30)  
Trade-offs, said aloud: a cap can end a run one more try would fix; escalation shows it.  
Plain explanation: a verification loop sends failures back to the agent. That is a loop with a model in it, and the model will keep trying as long as you let it. The stop has to come from outside the model: a counter, a timeout, a cost estimate, checked by code.  
Concrete example from DataPilot: the retry cap is 3 attempts, from `limits.max_retries`. After the third failed grader the run ends escalated, with every grader's reason attached, for a person to read. A refused write never reaches this counter: it ends the run at once. Each run also stops at 12 model calls and 16 tool calls, and each model call at its output cap, 16,000 tokens for the analyst, reasoning included; a response cut off there ends the run escalated. Postgres cancels any statement after 5,000 milliseconds, and an EXPLAIN-based cost grader rejects plans above 500,000 cost units or 5,000,000 estimated rows before they run. The cost grader is not a security layer: it plans only what the syntax tree calls one read-only SELECT and says not applicable to anything else, so a write that slips past a broken guard meets the read-only transaction first.  
Under the hood: where the stop lives matters. Tested with fake models, a check inside `wrap_tool_call` that returned `Command(goto=END)` did not end the run: control went back to the model, which simply tried again. What works is a hook before the model call that jumps to the end, plus a tool wrapper that returns a message without running the tool. The built-in tool-call limit only ends the run when it is scoped to one tool name.  
Source 11: LangChain custom middleware (https://docs.langchain.com/oss/python/langchain/middleware/custom): "`'end'`: Jump to the end of the agent execution (or the first `after_agent` hook)". That jump is available from the hooks around the model call, which is where a stop belongs.  
Source 12: LangChain built-in middleware (https://docs.langchain.com/oss/python/langchain/middleware/built-in), in summary: the model-call limit can end the run or raise; the tool-call limit ends the run only with a tool name set.  
Transfer: in any agent framework, find the one point every iteration passes through before spending money, which is the model call, and put budgets, kill switches, and retry counts there. A check deep inside a tool is a suggestion to the model, not a stop.  
Evidence from this course: in the paired measurement of 24 October, without the retry cap the always-failing grader ran 4 attempts, 19,960 tokens, and then the agent escalated by itself; with the cap, 3 attempts, 10,573 tokens, ended escalated by the cap. Nothing made the uncapped run stop: on 23 October the same half ran 11 attempts, and in calibration 9, until the run budget stopped it. A stop the model may choose is not a stop.  
Point at: the principle's last words, then the evidence line.  
Ask: "What should the run return when it hits the cap?" Expected: escalated, with the reasons, not a best guess.  
Likely question: "Is 3 the right retry count?" Answer: it is a setting; the principle is that some cap exists and that hitting it is a visible outcome, not a silent failure.  
Re-check after live runs: 4 attempts and 19,960 tokens, 3 attempts and 10,573 tokens against the paired measurements page; in calibration the capped run ended escalated after 3 attempts in 69 and 79 seconds, and without the cap went on for 9 attempts until the 60,000-token run budget stopped it; the output caps against the pack.  
Transition: the loop now stops. Last question: who checks the meaning?

**Slide 36: 4) A checker that shares the maker's blind spots**

Container: table: check | catches | misses, with worked-example, trade-offs, at-work, and key idea bars

On the slide:

Principle: a checker helps only where its errors differ from the maker's.
Why it matters: a reviewer on the same model, without the rules, approves the wrong number the analyst wrote.

| Check | Catches | Misses |
|---|---|---|
| Seven deterministic graders | Unsafe, malformed, costly | Business meaning |
| Reviewer on the same model | Some meaning errors | What the analyst also misses |
| Result match, one database | Wrong results | About 6.5 percent false positives |
| Result match, two databases | Coincidental matches | Rules nobody wrote down |

Evidence: 40 trap runs: 0 correct either way; the layer held or escalated 20, the reviewer approved 19.
At work: before adding a model as judge, name what keeps its errors independent.
Key idea: two agents with one blind spot agree on the same wrong answer.

Speaker notes:

Time: 4.5 minutes (1:13:30-1:18)  
Trade-offs, said aloud: one more model call per answer; a different model or the rules lowers the correlation.  
Plain explanation: maker and checker is an old control, and it works when the checker can fail differently from the maker. A reviewer agent built on the same model, reading the same schema, without the business rules, tends to miss what the analyst missed. So the reviewer goes after the deterministic graders, and it can add a concern but never pass a failed grader.  
Concrete example from DataPilot: the reviewer is an independent agent that sees only the question, the final SQL, the result preview, and the active knowledge version. It returns approve or concern with reasons. A concern goes back to the analyst once, within the retry cap; if it persists, the run holds for human approval. It runs on the same class model as the analyst. In calibration, on the wrong baseline answer to the fiscal year 2025 revenue question, it raised a concern in 6 runs and approved in 1. Better than feared, and still not a fix: a concern holds the answer, it never supplies the fiscal year rule. It is also the costly part: with it off, a question averaged 5,786 tokens and 12.8 seconds against 8,648 and 24.2 with everything on.  
Analogy: asking the author to proofread their own essay a second time, in a different font. It catches some typos and none of the misunderstandings.  
Under the hood: evaluation has the same problem. Matching a result on one database gave a 6.5 percent mean false-positive rate across 21 Spider submissions, 11.0 percent on extra-hard queries. The paper's fix fuzzes about 1,000 random databases per schema and keeps about 42 per query that tell apart neighbour queries. DataPilot keeps the teaching-sized version: two databases, with seed rows that tell the traps apart.  
Source 8: Semantic Evaluation for Text-to-SQL with Distilled Test Suites (https://arxiv.org/abs/2010.02840): "In contrast, the current Spider metric leads to a 2.5% false negative rate on average and 8.1% in the worst case." Weak metrics fail in both directions.  
Transfer: before adding an LLM judge, ask what keeps its errors independent: a different model, different inputs such as the gold data or the business rules, or a deterministic test. If none applies, spend the call elsewhere.  
Evidence from this course: in the paired measurement of 24 October, 20 trap questions from the development split under the starting knowledge, twice each, 40 runs per side: 0 of 40 correct with or without the verification layer. Without it, 1 wrong answer was escalated; with it, 20 were held for approval or escalated (17 held, 3 escalated), and the reviewer approved the other 19, which went out. On the answer to the fiscal year 2025 revenue question alone, calibration saw a concern in 6 of 7 runs. Both say the same thing: a concern holds an answer, it never supplies the fiscal year rule.  
Point at: the why line, the Misses column, top to bottom, then the evidence line: the reviewer holds some answers but cannot supply the missing rules.  
Ask: "Which input lowers the correlation of the reviewer's errors?" Expected: the business rules, a different model, or a second database.  
Likely question: "Should the reviewer use a stronger model?" Answer: a different model lowers the correlation; whether it pays is a measurement, and calibration gives the baseline: the reviewer roughly doubles the seconds per question.  
Likely question: "Why may the reviewer not override a grader?" Answer: a model can be talked out of a rule by a clever input; code cannot.  
Re-check after live runs: 20 of 40 held or escalated, 19 approved, and 0 of 40 correct against the paired measurements page; the reviewer's verdicts, concern in 6 runs and approve in 1, and the token and second figures against the calibration report.  
Transition: the four moves on one slide.

**Slide 37: Cheat sheet: verification in four moves**

Container: table: move | principle | anti-pattern it prevents | check question

On the slide:

| Move | Principle | Anti-pattern it prevents | Check question |
|---|---|---|---|
| Allowlist the shape | An unknown shape is a rejection | A first-word check or keyword denylist | Does anything unparsed run? |
| Scope the credential | Grants hold; defaults do not | Read-only by setting or by prompt | What does a write with your credential return? |
| Cap the loop | The stop lives before the model call | A retry loop the model decides to end | What ends a run that never succeeds? |
| Decorrelate the checker | A checker must fail differently | A judge on the same model and inputs | What does your checker see that the maker missed? |

Speaker notes:

Time: 1 minute (1:18-1:19)  
Say: four moves. Allowlist the shape of what the agent may run, and execute exactly the text you checked. Scope the credential so that the last defense is a missing grant. Cap the loop with stops the model cannot argue with, placed before the next model call. And add a checker only where its errors differ from the maker's.  
Point at: the Check question column; each question is one you can ask of your own system in a design review.  
Likely question: "Which move would you drop first under time pressure?" Answer: none of the first three; the checker is the one to measure before you keep it.  
Likely question: "Do these apply to agents without SQL?" Answer: yes; replace the database role with whatever credential your agent holds.  
Transition: now watch each one live.

**Slide 38: Section 2: Verification loop - Implementation Notes: Every grader passes, still wrong**

Container: demo layout: laptop and badge, what to watch for, guaranteed moment, link

On the slide:

Badge: DEMO - 2
What to watch for:
- Malicious SQL (Structured Query Language): the layer that stopped each statement, naive guard, then tree guard
- The retry cap: the attempt and cost counters, cap off, then on
- Every grader passes, still wrong: a green checklist beside a failed gold check
Guaranteed moment: under the starting knowledge, the fiscal year 2025 revenue question passes every deterministic grader and the checklist turns green, while the gold check on both databases fails.
Link: Demo page on GitHub | https://github.com/ANI-IN/loop-engineering/tree/main/section-2-verification-loop/demo#every-grader-passes-still-wrong

Speaker notes:

Time: 18 minutes (1:19-1:37)  
Run sheet: three core demos, about 12 minutes, then the code walkthrough, about 6 minutes. Share the console's Verify page full screen: the pre-flight checklist on the left, the defense-layer panel on the right. Every core demo's moment has been shown live, in calibration retakes and again on 24 October, both halves and the optional cost guard included; rehearse each twice in a row with a reset between before class (instructor guide, the day before, step 4). The measured results are under each demo. A planted half is `make demo NAME=<demo> PLANTED=1`, its bug on for its own run only; `.env` stays as it is. The slide's link opens the section's demo page on GitHub.  
Demo: malicious SQL.  
Guaranteed moment, from the demo registry: With the naive guard, "SELECT 1; DELETE FROM orders" and a data-modifying CTE pass the guard and the read-only role refuses them (SQLSTATE 25006); with the syntax-tree guard, its parse step stops the stacked statements and its statement policy the data-modifying CTE, before execution. A raw DELETE as the agent role is refused by the role.  
Starting state: Verify page open. Reset first: `make reset NAME=verification-loop`. The reset clears the runs, so the naive guard's chip shows on the status line once the first run with the flag starts.  
Do: `make demo NAME=verify-malicious-sql PLANTED=1`, the naive guard (`BUG_NAIVE_GUARD`) on for that run; then Verify > Send malicious SQL, or `make demo NAME=verify-malicious-sql`, with it off.  
Narrate: concept 1, allowlist the shape. The naive guard reads the first word, sees SELECT, and lets "SELECT 1; DELETE FROM orders" and a data-modifying CTE through. Concept 2, permissions are the boundary: the read-only transaction refuses both with SQLSTATE 25006, and the third statement, a raw DELETE as the agent role, meets the missing grant, 42501. A refused write ends the run escalated at once; it is never fed back as a retry. With the syntax-tree guard on, its parse step stops the stacked statements and its statement policy the DELETE inside the WITH clause, before either reaches the database.  
Point at, in order: the statement text; the defense-layer panel with the layer that stopped each statement and the layers it never reached; and last the live stamp: the run's start time in your local time and its trace link.  
Expected live result: with the naive guard, 25006, 25006, then 42501; with the syntax-tree guard, the guard, the guard, then 42501; no warehouse row changes in either run. Measured: exactly that, in 2 seconds each half on 24 October, and the same in calibration and on 23 October.  
May vary: timings only. If they do, say: the outcome is deterministic; only the clock moves.  
If it stalls: reset and run it again, `make reset NAME=verification-loop`, then the same trigger.  
Demo: the retry cap.  
Guaranteed moment, from the demo registry: An injected grader that always fails sends the run back to the agent; with the missing retry cap the run keeps looping and the cost counter climbs; with the cap it stops after 3 attempts and ends escalated with the reasons.  
Starting state: the Verify page. Reset first: `make reset NAME=verification-loop`.  
Do: `make demo NAME=verify-retry-cap PLANTED=1`, the missing retry cap (`BUG_NO_RETRY_CAP`) on for that run. Watch the attempt and cost counters, then Verify > Inject failing grader, or `make demo NAME=verify-retry-cap`, with it off.  
Narrate: concept 3, stops that are not the model's choice. The injected grader always fails, so with nothing counting the agent keeps retrying until something stops it. With the cap, the run stops after 3 attempts and ends escalated with every reason.  
Point at, in order: the attempt counter and the cost counter with the bug on; the counter flat at 3 with the bug off; the escalated status with the reasons; and last the live stamp: the run's start time in your local time and its trace link.  
Expected live result: the cost counter stops at the cap and the run shows escalated. Measured on 24 October, on the code that ships: with the cap, escalated after 3 attempts, 10,573 tokens, in 20 seconds; without it, 4 attempts, 19,960 tokens, in 33 seconds, and then the agent escalated by itself. Earlier runs without the cap went on longer: 11 attempts and 63,718 tokens on 23 October; 9 attempts, 62,762 and 63,737 tokens, until the run guard's 60,000-token budget stopped them, in calibration.  
May vary: the cost per attempt and the SQL of each retry. If they do, say: the model writes a different query each time; the counter does not care. Without the cap the agent may stop and escalate by itself, as it did on 24 October after 4 attempts. If it does, say: the model chose to stop this time; nothing made it stop, and on 23 October the same half ran 11 attempts. Point at 4 attempts against the cap's 3: the cap is the only stop you can count on.  
If it stalls: reset and run it again, `make reset NAME=verification-loop`, then the same trigger.  
Demo: every grader passes, still wrong.  
Guaranteed moment, from the demo registry: Under version 1 of the knowledge (the starting version), the fiscal year 2025 revenue question passes every deterministic grader and the checklist turns all green, while the gold check on both databases fails. The reviewer's verdict is shown beside it, whichever way it goes.  
Starting state: version 1 of the knowledge (the starting version) active, no planted bug on. Reset first: `make reset NAME=verification-loop`.  
Do: Verify > Ask the spine question, or `make demo NAME=verify-graders-pass-still-wrong`.  
Narrate: the tempting question from the start of the section. Every deterministic grader passes. Concept 4, a checker that shares the maker's blind spots: the reviewer reads the answer and gives its verdict, and the gold check on both databases fails anyway.  
Point at, in order: the checklist turning green line by line; the reviewer's verdict beside it; the failed gold check on both databases; and last the live stamp: the run's start time in your local time and its trace link.  
Expected live result: an all-green checklist beside a failed gold check.  
May vary: the reviewer's verdict and the wrong value. In calibration the reviewer raised a concern on this answer in 6 runs and approved in 1, so expect a concern and a hold for approval. If the reviewer raises a concern, say: good, and notice it still cannot supply the fiscal year rule; if it approves, say: same model, same blind spot.  
If it stalls: reset and run it again, `make reset NAME=verification-loop`, then the same trigger. In calibration both attempts passed every grader but got no gold check within 90 seconds; the gold checks were hardened the same night, and a failing promotion step no longer stops them. Both retakes were shown: 76,981,355.95 dollars against gold 64,015,091.21, with 4 trap labels each, then held by two reviewer concerns. Shown again live on 24 October.  
Optional, cut first: the cost guard, `make demo NAME=verify-cost-guard` (Verify > Send cartesian query): with the missing cost guard a cartesian join runs to the statement timeout; with the cost grader, EXPLAIN rejects it at once with a reason. Shown live on 24 October, both halves.  
Code walkthrough: about 6 minutes, in the editor, in the order of the section's demo walkthrough page.  
Open `platform/src/datapilot/loop2_verification/checker.py`, lines 85-101: the order of the layers, behind concepts 1, 2, and 3. Say: cheap text checks first, then the cost grader and the personal data grader, execution last, then the execution grader; the first blocking grader returns one clear reason; the executor runs the text as written; the cost grader plans only one read-only SELECT and says not applicable to anything else; and when the database refuses a write, 25006 or 42501, `checked.refused` marks it so the loop ends the run escalated with no retry.  
Open `platform/src/datapilot/loop2_verification/graders/statement_policy.py`, lines 84-95: implements concept 1, allowlist the shape, the statement policy of the malicious SQL demo. Say: the parse step before it has already stopped the stacked statements; here the root check stops anything that is not a read, and the walk over every node stops a DELETE hidden in a common table expression under a SELECT root, which a prefix check passes; with `BUG_NAIVE_GUARD` on, a `startswith` check replaces both the parse and the statement policy graders. The clock rule sits just below these lines: agent SQL may not read the database clock.  
Open `platform/src/datapilot/loop2_verification/loop.py`, lines 364-369: implements concept 3, stops that are not the model's choice, the retry cap demo. Say: before another attempt, `attempt_allowed` compares it with the cap of 3; at the cap the run ends escalated with every reason; just below, the run guard is checked before the feedback goes back, so a kill switch or a spent budget wins over a retry; with `BUG_NO_RETRY_CAP` on, `attempt_allowed` always says yes.  
Concept 4, the reviewer, has no line range on the walkthrough page. If asked, say: it runs only after every grader passes, sees only the question, the final SQL, a result preview, and the knowledge, and can add a concern but never pass a failed grader.  
Transition: questions before the break.

**Slide 39: Questions**

Container: key-idea box: fixed question wording, two likely questions

On the slide:

No Question Is Too Small Every Question Deserves an Answer!!
Why two databases? Can the reviewer be fooled?

Speaker notes:

Time: 5 minutes (1:37-1:42)  
Say: take questions; this slot also holds the section's discussion time. Send anything that needs more than two minutes to the Thursday parking lot.  
Point at: the two likely questions on the slide.  
Likely question: "Why compare on two databases?" Answer: a wrong query can return the right number on one database by coincidence; a second database with different rows exposes it, which is the teaching-sized version of the distilled test suites.  
Likely question: "Can a prompt injection fool the reviewer?" Answer: it might, which is why the reviewer can only add a concern and never pass a failed grader.  
Likely question: "Where would you put a personal-data check?" Answer: as a grader that routes the run to human approval instead of blocking it; Section 3: Event loop makes that approval survive a restart.  
Likely question: "What does the agent do with a term no rule defines, such as loyal customers?" Answer: in calibration it guessed with a stated reading in 5 of 8 runs, and the reviewer turned most guesses into a held or escalated answer. With the reviewer off the guess posts unflagged, which is why Assignment 2: Verification loop adds a clarify-or-abstain grader.  
Transition: if time is short, skip the reference slides and go to the break.

**Slide 40: Reference: skip if short on time - attack patterns**

Container: two tables: pattern | example | defense, with a how-to-read bar

On the slide:

How to read this: left, shapes that hide a write; right, shapes the parser misreads or cannot see; the last column stops each one.

| Pattern | Example | Defense |
|---|---|---|
| Stacked statements | SELECT 1; DELETE FROM orders | Exactly one statement |
| Write inside a WITH clause | WITH d AS (DELETE ...) SELECT ... | Walk every node |
| Hidden write or lock | SELECT ... INTO, FOR UPDATE | Reject INTO and lock nodes |
| Unparsed statement | DO, CALL, VACUUM | Reject opaque commands |


| Pattern | Example | Defense |
|---|---|---|
| Misparse | TABLE orders | Root allowlist |
| A query in a string | dblink, query_to_xml | Function denylist, then grants |
| Lossy regeneration | COPY ... TO PROGRAM | Run the original text |

Speaker notes:

Time: 1 minute (1:42-1:43)  
Plain explanation: these are the shapes that get past a guard that only looks at the first word or the root node. Each row pairs a pattern with the specific defense that stops it.  
Concrete example from DataPilot: the malicious SQL demo sends the first two rows; the guard's tests cover every row, and the security suite asserts that no warehouse row changes.  
Analogy: a customs officer who checks the label on a box and never opens it.  
Under the hood: parsed in the Postgres dialect, the stacked string is two statements; the CTE has a Select root with a Delete inside; SELECT INTO is an Into node and FOR UPDATE a Lock node; DO, CALL, VACUUM, EXPLAIN ANALYZE, PREPARE and EXECUTE become an opaque Command; `LISTEN foo` and `TABLE orders` misparse as aliases; `dblink` and `query_to_xml` carry SQL in string literals; and `COPY ... TO PROGRAM` came out mangled when regenerated from the tree.  
Source 7: LangChain SQL agent (https://docs.langchain.com/oss/python/langchain/sql-agent), in summary: the tutorial's checker is an LLM, which reads these patterns as text and can be persuaded.  
Transfer: keep a table like this for any language your agent emits, with one test per row, and add a row each time a parser surprises you.  
Point at: the Defense column; no row relies on the prompt.  
Ask: "Which row is the grant's job, not the guard's?" Expected: SQL in a string.  
Likely question: "Is a new parser version a risk?" Answer: yes; pin it, and keep these tests so an upgrade that changes a node type fails continuous integration.  
Likely question: "Why reject FOR UPDATE in a read-only tool?" Answer: it takes row locks that can block writers elsewhere, a side effect without a write.  
Misconception: if it parses, it is safe. Correction: three rows here parse without error.  
Transition: next reference slide.

**Slide 41: Reference: skip if short on time - database errors as feedback**

Container: table: SQLSTATE | meaning | feedback to the agent | then, with a how-to-read bar

On the slide:

How to read this: a fixable error becomes a reason the agent can act on, counted against the cap of 3; a refused write ends the run.

| Error code | Meaning | Feedback to the agent | Then |
|---|---|---|---|
| 42601 | Syntax error | Send one valid SELECT statement | Retry, counted |
| 42P01, 42703 | Unknown table or column | Look up the real names with the schema tools | Retry, counted |
| 57014 | Statement timeout | Add filters or aggregate before returning | Retry, counted |
| 25006 | Write in a read-only transaction | Write blocked: only SELECT queries can run | Run ends, escalated |
| 42501 | Privilege refused | The role can only read the allowed schema | Run ends, escalated |

Speaker notes:

Time: 1 minute (1:43-1:44)  
Plain explanation: a raw database error is feedback written for a person at a terminal. Translate each fixable class of error into a short reason the agent can act on, and count every retry against the cap, so a run that keeps failing ends escalated for a person to read. A refused write is different: it is an incident, so the run stops at once.  
Concrete example from DataPilot: the executor maps each SQLSTATE to one sentence of feedback. A misspelled column comes back as a pointer to the schema tools, and the next attempt usually fixes it. A refused write, SQLSTATE 25006 or 42501, is never fed back as a retry: the run ends escalated at once, with the reason write blocked, only SELECT queries can run, for a person to read.  
Analogy: a compiler error message that points at the line, versus one that says failure.  
Under the hood: the condition names in the PostgreSQL appendix are `syntax_error` for 42601, `undefined_table` for 42P01, `undefined_column` for 42703, `query_canceled` for 57014, `read_only_sql_transaction` for 25006, and `insufficient_privilege` for 42501. The feedback strings are short and carry no data from the error text.  
Source 10: PostgreSQL error codes (https://www.postgresql.org/docs/current/errcodes-appendix.html): "read_only_sql_transaction" is the listed condition name for 25006, and "insufficient_privilege" for 42501.  
Transfer: for any tool an agent calls, classify its errors before launch, write the feedback text for each class, and decide which ones the agent may retry. Anything that signals an attempt to cross a boundary, such as a refused write, is an incident: stop the run at once instead of handing it back to the model.  
Point at: the Then column: the top three rows retry against the cap; the last two end the run.  
Ask: "Why does a refused write not get a retry?" Expected: it is an incident, not a mistake to fix; a retry would invite the model to try another way across the boundary.  
Likely question: "Should the agent see the full error text?" Answer: a trimmed message is better; full text can carry data back into the context.  
Likely question: "What about connection errors?" Answer: those are infrastructure, so retry with backoff outside the agent loop, not as agent attempts.  
Misconception: more error detail always helps the agent. Correction: one actionable sentence per error class beats a stack trace.  
Transition: last reference slide.

**Slide 42: Reference: skip if short on time - why one database lies**

Container: table with a how-to-read line: the two-database example, then the false-positive table

On the slide:

How to read this: left, gold leaves cancelled orders out and the wrong query keeps them; right, the measured size of the gap.

| Database | Gold | Wrong query |
|---|---|---|
| A: no cancelled orders | Matches | Matches too |
| B: some cancelled orders | Matches | Fails |


| Measure | Value |
|---|---|
| False positives, one database | 6.5 percent mean |
| On extra-hard queries | 11.0 percent |
| Fuzzed databases kept per query | About 42 |

Speaker notes:

Time: 1 minute (1:44-1:45)  
Plain explanation: a result match is only as strong as the data it runs on. If the rows that would separate the right query from the wrong one are absent, both return the same answer and the wrong one passes.  
Concrete example from DataPilot: the seed data carries the rows each trap needs: cancelled orders, internal accounts among the top spenders, and orders placed in the evening Eastern time that cross the UTC date. Gold answers are checked on two databases, the warehouse and an alternate copy.  
Analogy: a test suite whose inputs never hit the branch you changed.  
Under the hood: across 21 Spider submissions, matching on the original database gave a 6.5 percent mean false-positive rate and 11.0 percent on extra-hard queries. The fix fuzzes about 1,000 random databases per schema and keeps those that separate neighbour queries, where one constant, operator, or clause differs: about 42 per query.  
Source 8: Semantic Evaluation for Text-to-SQL with Distilled Test Suites (https://arxiv.org/abs/2010.02840): "In contrast, the current Spider metric leads to a 2.5% false negative rate on average and 8.1% in the worst case."  
Transfer: when you evaluate any agent by its outputs, seed the inputs that separate right from plausible: the edge rows, the boundary dates, the excluded categories.  
Point at: database A, where the wrong query passes.  
Ask: "What row would you add to database A?" Expected: one cancelled order.  
Likely question: "Why only two databases?" Answer: it is the teaching-sized version; two with designed rows catch the traps we planted, and the paper shows what scale buys.  
Likely question: "Does a second database slow evaluation?" Answer: every item runs its SQL twice, which is database time, not model tokens.  
Misconception: execution match is the ground truth. Correction: it is an upper bound unless the data distinguishes the queries.  
Transition: time for a break.

## Break

| # | Slide | Layout | Time (start-end) | Says in one line | Source in the repository |
|---|---|---|---|---|---|
| 43 | Time for a Break | blank | 1:45-1:55 | A 10-minute break is starting now. Please return when the timer ends to continue the presentation | - |

### Slides and speaker notes: Break

**Slide 43: Time for a Break**

Container: fixed template slide

On the slide:

Time for a Break
A 10-minute break is starting now. Please return when the timer ends to continue the presentation

Speaker notes:

Time: 10 minutes (1:45-1:55)  
Say: Write the return time, 1:55, in the chat and on the slide.  
During the break, reset the event loop section so Section 3: Event loop starts clean.  
Point at: the timer.  
Likely question: "Can I run the demos now?" Answer: after class is better; your runs use your own key.  
Transition: Welcome back. Answers are now safe and bounded. Next: who asks, when, and who may approve.

## Section 3: Event loop

The failure this section fixes: Work that arrives as events runs twice, waits for a person in memory that dies with the process, and keeps running after someone presses stop.

Measured live: in calibration, each core demo twice with a reset between: the webhook question shown in 46 seconds, posted unverified, and in the second attempt held by a reviewer concern about the date (fixed the same night: the reviewer sees the business date); the approval that survives a restart shown in 84 and 81 seconds; duplicate events shown in 57 and 78 seconds, 1 run, 2 duplicates absorbed, 1 digest; the kill switch in flight shown in 33 and 8 seconds, stopped in flight. Retaken on 23 October: the webhook question twice, both posted unverified, 300 orders (the day in Eastern time) and 291 (the day in Coordinated Universal Time), both approved by the reviewer; every planted half twice, each shown: the approval lost with the in-memory checkpointer, 3 answers and 2 digests with both duplicate bugs, and a post after the kill switch with the check at claim only. In the paired measurement of 23 October, one run of each half of three demos: 3 answers and 2 digests, then 1 answer, 2 duplicates absorbed, and 1 digest; the approval lost, then approved after the restart and posted; a post after the switch, then stopped in flight. In the live session of 24 October every core and optional demo showed its moment, both halves.

The demo: `make demo NAME=events-webhook-question`, `make demo NAME=events-approval-survives-restart`, `make demo NAME=events-duplicate-events`, `make demo NAME=events-kill-switch-in-flight`, launched at 2:19 on the DEMO slide, code walked at 2:34, recovery `make reset NAME=event-loop` and re-run: reset and run it again, live.

| # | Slide | Layout | Time (start-end) | Says in one line | Source in the repository |
|---|---|---|---|---|---|
| 44 | Agenda (Section 3 highlighted) | concept | 1:55-1:55:30 | Section 3: Event loop: the same agent, now driven by events, schedules, and people | section-3-event-loop/README.md |
| 45 | Failure story: the digest that posted twice | diagram | 1:55:30-1:57:30 | Illustrative: a retried digest posts twice, an export runs unwatched, stop misses a running job | section-3-event-loop/concepts.md |
| 46 | Event loop: should an agent route the events? | concept | 1:57:30-2:00 | KEY IDEA: No. Routing a closed set of event types is a lookup; a table is testable and auditable | section-3-event-loop/README.md |
| 47 | 1) At-least-once delivery needs idempotent effects | diagram | 2:00-2:05 | Key idea: delivery repeats, so every effect needs a deterministic key and a conflict rule | Sources 13 to 15 (Postgres queue caveats); platform/planted/registry.yaml |
| 48 | 2) The queue is a table: claim, lease, reap | diagram | 2:05-2:09:30 | Key idea: a job in a table survives what a process does not | Sources 13 to 15 (Postgres queue); platform/src/datapilot/contracts/lifecycle.py |
| 49 | 3) Durable approval: pause where state lives | diagram | 2:09:30-2:14 | Key idea: a pending approval is state, so it lives in the checkpointer, not in memory | Source 16 (human approval, checkpointer); platform/packs/datapilot_us/pack.yaml |
| 50 | 4) A router, levels, and a stop for running work | diagram | 2:14-2:18:30 | Key idea: policy is a table, autonomy is a level, and the stop is checked before every step | platform/src/datapilot/contracts/autonomy.py; Source 17 (autonomy levels and the kill switch) |
| 51 | Cheat sheet: the event loop in four moves | table | 2:18:30-2:19 | Key every effect, claim with leases, pause durably, route by table and stop before each step | section-3-event-loop/README.md |
| 52 | Section 3: Event loop - Implementation Notes: The kill switch in flight | demo | 2:19-2:41 | Badge DEMO - 3, what to watch for, the guaranteed moment, and the demo page link; the demos and code walkthrough are in the notes | section-3-event-loop/demo/walkthrough.md; platform/demos/registry.yaml |
| 53 | Questions | concept | 2:41-2:47 | Fixed question slide; likely: why not a message broker, and what if nobody approves | - |
| 54 | Reference: skip if short on time - queue failure modes | table | 2:47-2:48 | Failure, symptom, and defense for each way a table-backed queue goes wrong | Sources 13 to 15 (Postgres queue); docs/costs.md |
| 55 | Reference: skip if short on time - router or supervisor | table | 2:48-2:49 | A decision table for when routing should be a table and when it should be an agent | docs/architecture.md |
| 56 | Reference: skip if short on time - business and wall clocks | table | 2:49-2:50 | Business logic uses the business date and its time zone; live stamps use the wall clock | platform/src/datapilot/business_date.py; platform/demos/registry.yaml |

Numbers this section states (each gets a "Re-check after live runs" line in its notes):

- Demotion after 3 consecutive escalations: from `autonomy.demote_after_consecutive_escalations` in pack.yaml.
- Default autonomy level report-only: from `autonomy.default_level` in pack.yaml.
- Business date 31 January 2026: from the business-date setting (the warehouse ends there).
- Morning digest at 8 a.m. Eastern time: from the demo registry (the digest now).
- Approval decisions limited to approve and reject; `interrupt_mode="per_call"` from langchain 1.4.6: Source 16, verified locally.
- Two duplicates ignored after three identical events: the registry's guaranteed moment; measured 1 run and 2 duplicates absorbed, twice: docs/calibration-report.md, Demos.
- Approval across a worker restart and the kill switch stopping a run in flight, each shown twice: docs/calibration-report.md, Demos; their planted halves, each shown twice (approval lost, 3 answers and 2 digests, a post after the kill switch): docs/calibration-report.md, Resumed after the ledger correction.
- The webhook question about the previous day, 300 orders in Eastern time and 291 in Coordinated Universal Time, both posted unverified and approved by the reviewer: docs/calibration-report.md, Resumed without traces; the teaching point: docs/instructor-guide.md, Section 3: Event loop.
- Retry cap 3 (`limits.max_retries`), model call limit 12, tool call limit 16: from pack.yaml (referenced in the kill switch concept).
- Lease 30 seconds, heartbeat every 10 seconds: from the worker settings; at most 3 attempts: the jobs table default.
- One run of each half of three demos: duplicate events, 3 answers and 2 digests, then 1 answer, 2 duplicates absorbed, 1 digest; the approval lost and the run failed, then approved after the restart and posted; a post after the kill switch, then stopped in flight: docs/benefits.md, Section 3: Event loop.
- Every core and optional demo of the section showed its moment, both halves: the live session of 24 October 2026.

### Slides and speaker notes: Section 3: Event loop

**Slide 44: Agenda (Section 3 highlighted)**

Container: step cards: four sections, the third highlighted

On the slide:

1. Agent loop
2. Verification loop
3. Event loop (now): how work arrives, waits for a person, and stops
4. Hill-climbing loop

Speaker notes:

Time: 0.5 minutes (1:55-1:55:30)  
Say: Welcome back. So far every run started because I pressed a button and watched it. That is not how agents run at work. At work, a question arrives as a webhook from a chat tool, a digest fires on a schedule, an export waits for a person, and nobody is watching the screen. Section 3: Event loop is about that shift. The agent does not change in this section. The analyst, the schema scout, the graders, and the reviewer are exactly what you saw in Sections 1 and 2. What changes is everything around them: how work arrives, how it is claimed, how it waits for a human, and how it is stopped. This section also adds no new agent, and that is a deliberate design choice we will defend in a few minutes. The concepts are four: idempotent effects under at-least-once delivery, a queue that lives in a table, approvals that survive a restart, and a router plus a stop that reaches running work. Then four live demos and a short code walkthrough.  
Point at: the highlighted third row, and the fact that rows one and two stay in place: we keep everything we built.  
Likely question: "Is the event loop another agent framework feature?" Answer: No. It is ordinary distributed-systems engineering around an agent: a queue, keys, durable state, and policy. The agent framework gives you the pause and resume hooks; the rest is yours.  
Transition: First, a story of what goes wrong when the loop around the agent is naive.

**Slide 45: Failure story: the digest that posted twice**

Container: step cards: four numbered beats, then a lesson bar

On the slide:

Illustrative
1. **Two digests**: at 8 a.m. Eastern time a worker times out, the retry posts a second digest, and the numbers differ because two late orders arrived in between.
2. **Unwatched export**: a California customer list with emails goes out while nobody watches.
3. **A stop for new work**: someone presses stop; no new jobs start.
4. **The run in flight**: the run already running finishes and still posts.
Lesson: none of these is a model failure; everything that went wrong was around the model.

Speaker notes:

Time: 2 minutes (1:55:30-1:57:30)  
Say: This story is illustrative, and every name in it is invented. Beat one, two digests. Harbor & Pine's morning digest of the previous day's net revenue posts at 8 a.m. Eastern time. One morning the worker times out halfway, the scheduler retries, and the channel shows a second digest. The two disagree, because two late orders arrived between the first run and the retry. Now finance trusts neither number. Beat two, the unwatched export. Priya in marketing asks for a list of California customers for a campaign. The query reads email addresses, which is personal data. Nobody is watching the run, so the export goes out. Beat three, a stop for new work. Someone notices and presses stop. The flag is checked when a worker claims a job, so no new runs start. Beat four, the run in flight. The run that is already running keeps going, finishes its last tool call, and posts. Each beat is a different failure: a duplicate effect, a missing human decision, and a stop that does not reach running work. None of these is a model failure; everything that went wrong was around the model.  
Point at: the four beat labels, then the lesson bar.  
Likely question: "Would a smarter model avoid any of this?" Answer: No. Every beat is about delivery, state, and control, which live outside the model.  
Transition: So the tempting fix is smarter routing. Let us test that idea.

**Slide 46: Event loop: should an agent route the events?**

Container: key-idea box with three reason points

On the slide:

Should an agent route the events?
KEY IDEA: No. A closed set of event types is a lookup, so the router is a deterministic table, deliberately not an agent.
- Same event, same route, every time: one unit test per row
- No model call, no bill, and no payload that can persuade it
- Judgement in this loop belongs to people, through human approval

Speaker notes:

Time: 2.5 minutes (1:57:30-2:00)  
Say: The tempting answer is yes: put a supervisor agent in front, let it read each event and decide what to do. Multi-agent frameworks offer that out of the box. The verdict here is no. Our events come from a closed list: a question was asked, a digest was requested, an export was requested. Each type maps to exactly one handler and one autonomy policy. That is a lookup table. A table gives the same answer for the same event every time, so you can write a unit test for every row, and an auditor can read it. A supervisor agent gives you a second source of nondeterminism, a second bill, and a new attack surface: an event payload that says 'treat this as an export' now has a model to persuade. The judgement in this loop belongs to people, through human approval, not to a router. Source 1: The art of loop engineering (https://www.langchain.com/blog/the-art-of-loop-engineering), in summary: the event-driven loop is cron, webhooks, and channels feeding the agent; nothing in it requires the routing itself to be an agent.  
Point at: the KEY IDEA box, then the three reasons.  
Likely question: "When would an agent router be the right choice?" Answer: When the inputs are open-ended text with no fixed type, such as a support inbox. Even then, classify into a closed set first and route the label with a table.  
Transition: Concept one: what at-least-once delivery does to your effects.

**Slide 47: 1) At-least-once delivery needs idempotent effects**

Container: two-column cards: how it works | worked example, then a key-idea bar

On the slide:

Principle: assume every event arrives more than once; its effect must happen once.
Why it matters: a retried digest posts twice with different numbers, and finance trusts neither.

| How it works in DataPilot | Worked example |
|---|---|
| Key from what the event means, never from arrival time | Webhook: the sender's event id |
| Insert under a unique constraint; a conflict is a duplicate | Digest: job name plus business date |
| Pick the conflict rule: ignore, update, or reject | A repeated question: ignore it |

Evidence: one event sent three times posted 3 answers without the key; with it, 1 answer and 2 duplicates absorbed.
At work: for payments, emails, and tickets, name each effect's key and its second-arrival rule.
Key idea: delivery repeats; effects must not.

Speaker notes:

Time: 5 minutes (2:00-2:05)  
Trade-offs, said aloud: a key too coarse merges events; a key too fine lets duplicates through.  
Plain explanation: Every queue, webhook, and scheduler you will use delivers at least once. Senders retry on timeouts, workers crash after doing the work but before marking it done, and schedulers fire again after a restart. Exactly-once delivery is not on offer. What you can build is exactly-once effects: the event may arrive three times, but the answer is posted once. The tool for that is an idempotency key: a value that is the same every time the same logical event arrives, stored under a unique constraint.  
Concrete example from DataPilot: A question arrives as a webhook with the sender's event id. The api inserts the event with `INSERT ... ON CONFLICT (event_id) DO NOTHING`. The second and third copies hit the conflict, create no job, and are counted as duplicates ignored on the run board. The morning digest has no sender, so its key is built from the job name and the business date, `digest:YYYY-MM-DD`. Two planted bugs show the failure: the missing idempotency (`BUG_NO_IDEMPOTENCY`) posts three answers, and the random digest id (`BUG_RANDOM_DIGEST_ID`) posts two digests.  
Under the hood: The key must be derived from the meaning of the event, never generated at arrival. A random id per arrival defeats the constraint because every copy looks new. A key from wall-clock time breaks the other way: a retry a second later gets a new key. Business identity is the rule: who sent it and what it is about, or which job for which business date. The constraint lives in the database, not in application memory, so it holds across workers and restarts. The conflict rule is a choice: do nothing for a repeated question; update the existing post when a late order changes a daily alert, which is what Assignment 3: Event loop builds.  
Source 15: You don't need a job queue: Postgres already has SKIP LOCKED (https://www.prisma.io/blog/you-dont-need-a-job-queue-postgres-already-has-skip-locked), in summary: a crash after the side effect but before the job is marked done can run a job twice, so handlers must be idempotent.  
Transfer: Use the same pattern for payments, emails, ticket creation, and any agent tool with a side effect. Ask of every effect: what is its business key, and what happens on the second arrival: ignore, update, or reject.  
Evidence from this course: in the paired measurement of 24 October, one run of each half, the same event sent three times posted 3 answers, and the digest fired twice posted 2 digests, with both planted bugs on; with the key and the conflict rule, 1 answer, 2 duplicates absorbed, and 1 digest. The pair of 23 October showed the same.  
Point at: the why line, the two columns row by row, the evidence line, then the trade-off line: too coarse or too fine.  
Re-check after live runs: 3 answers and 2 digests, then 1 answer, 2 duplicates, and 1 digest, against the paired measurements page.  
Ask: "What key would you use for an email an agent sends after a ticket closes?" Expected: the ticket id plus the email type, not a timestamp or a random id.  
Likely question: "Why not deduplicate in the worker with a cache?" Answer: A cache is lost on restart and is not shared across workers; the unique constraint is both.  
Likely question: "What if two different events legitimately share a key?" Answer: Then the key is too coarse. Add the field that tells them apart, such as the question text hash or the business date.  
Likely question: "Does the key slow the insert?" Answer: It is one unique index lookup per event, which is negligible next to a model call.  
Transition: The key stops duplicates at the door. Next: how workers take work without taking the same job twice.

**Slide 48: 2) The queue is a table: claim, lease, reap**

Container: two-column cards: how it works | why, then evidence, trade-offs, at-work lines and a key-idea bar

On the slide:

Principle: keep the claim short; a lease, not a lock, covers the long work.
Why it matters: a lock held through a model call bloats the table; a killed worker strands its job.

| How it works in DataPilot | Why |
|---|---|
| One statement claims a queued job | Skips locked rows: workers never wait |
| Commit at once; a 30-second lease | No lock through the model call |
| 10-second heartbeat; reaper requeues | A dead worker's job reruns |
| Finish only with owner and attempt | A stale worker cannot overwrite |

Evidence: in a local run, two workers claimed different jobs and the reaper requeued an expired lease.
At work: any long agent task fits this shape.
Key idea: a job in a table outlives its process.

Speaker notes:

Time: 4.5 minutes (2:05-2:09:30)  
Trade-offs, said aloud: not strictly first in first out; open transactions bloat it.  
Plain explanation: You do not need a message broker to run agent jobs. A jobs table in the same Postgres as your data gives you durability, transactions, and visibility. The pattern has four parts: a claim, a lease, a heartbeat, and a reaper. The claim takes one queued job in a short transaction. The lease says who owns it and until when. The heartbeat extends the lease while the model works. The reaper finds expired leases and puts those jobs back in the queue.  
Concrete example from DataPilot: The worker claims with `UPDATE ops.jobs SET status = 'running', attempts = attempts + 1, lease_owner = ..., lease_until = now() + 30 seconds WHERE job_id = (SELECT job_id FROM ops.jobs WHERE status = 'queued' AND run_after <= now() ORDER BY run_after, job_id FOR UPDATE SKIP LOCKED LIMIT 1) RETURNING ...` and commits at once. The lease is 30 seconds and the heartbeat runs every lease divided by three, 10 seconds, from the worker's settings. A job is dead after 3 attempts, the default `max_attempts` of the jobs table. The finish and the heartbeat both match the row only `WHERE lease_owner` is this worker `AND attempts` is the attempt it claimed. A worker can finish or extend a job only while it holds the lease and the attempt number still matches, so a stale worker can neither finish nor extend a re-claimed job, whoever re-claimed it. In a local run, two concurrent workers claimed different rows and the reaper requeued an expired lease.  
Under the hood: `SKIP LOCKED` lets each worker skip rows another worker holds, so claims never wait on each other. Two caveats. First, it is not strictly first in first out: skipping locked rows means a later job can start before an earlier one, so never rely on queue order for correctness. Second, long transactions bloat the queue: a transaction held open keeps dead row versions alive, and the claim query slows as they pile up. That is why the planted lock held during the model call (`BUG_LOCK_DURING_LLM`) matters: it bloats the table and leaves a stuck job when the worker is killed. Fencing the finish and the heartbeat on owner and attempt is what makes at-least-once safe. Dead letters keep a poison job from looping forever.  
Source 13: PostgreSQL SELECT (https://www.postgresql.org/docs/current/sql-select.html), in summary: with SKIP LOCKED, rows that cannot be locked immediately are skipped, which gives an inconsistent view of the data that suits queue-like tables.  
Transfer: Any long-running agent task, from code review bots to report generators, fits this shape. Keep claims short, put the long work under a lease, fence every finish and heartbeat, and give every job a maximum attempt count and a dead-letter state you alert on.  
Evidence from this course: the claim, the lease, and the reaper were checked in a local run with no model call, two workers claiming at once; in class, every webhook run, the finale included, passes through this one claim. The webhook question went from Queued to Done again live on 24 October.  
Point at: the why line, then the four rows: the claim, commit at once, heartbeat every 10 seconds, and the fenced finish; then the evidence line.  
Ask: "What happens if a worker freezes for longer than its lease?" Expected: the reaper requeues the job, a second worker claims it, and the frozen worker can neither finish nor extend it: its attempt number no longer matches.  
Likely question: "Why not Kafka or SQS?" Answer: You can. The table wins when jobs, approvals, and answers must commit together; a broker adds a second system to keep in step.  
Misconception: "FOR UPDATE SKIP LOCKED gives exactly-once processing." Correction: It gives exclusive claims. A crash after the effect still repeats the job, which is why concept one comes first.  
Transition: Some jobs cannot finish without a person. Where does a run wait?

**Slide 49: 3) Durable approval: pause where state lives**

Container: two-column cards: how it works | worked example, then a key-idea bar

On the slide:

Principle: a pending approval is state; store it where a restart cannot reach it.
Why it matters: held in memory, a pending approval dies with the next deploy.

| How it works in DataPilot | Worked example |
|---|---|
| The pause is a checkpoint keyed by the run | California export: emails, so it holds |
| Approver sees the exact query and rows | Worker restarts; the run stays held |
| Decisions: approve or reject, never edit | Approve resumes the same run |
| The condition re-runs on resume | So it reads the query and column tags |

Evidence: in Postgres the held export survived a restart and posted; in memory, it was lost.
At work: refunds, deploys, outbound email, exports.
Key idea: put the pause where state lives.

Speaker notes:

Time: 4.5 minutes (2:09:30-2:14)  
Trade-offs, said aloud: batched approval saves time; per-call gives an exact audit.  
Plain explanation: Human approval turns a run into something that can wait for hours. A run that waits is state: the conversation so far, the pending tool call, and who must decide. If that state lives in the worker's memory, a deploy or a crash erases the request, and nobody knows a decision is owed. Durable approval means the pause is a checkpoint in a database, keyed by the run, and approving resumes from it on any worker.  
Concrete example from DataPilot: A query that touches a personal-data column, such as customer email or phone, holds for human approval. The dialog states the exact SQL and the row count. The run's state lives in the Postgres checkpointer, `AsyncPostgresSaver` in its own schema `lg`, with the thread id equal to the run id. Approval resumes with `Command(resume={"decisions": [{"type": "approve"}]})`. Decisions are limited to approve and reject; an edit raises an error, so nobody rewrites SQL in a dialog. The planted in-memory checkpointer (`BUG_MEMORY_CHECKPOINTER`) loses the pending approval on a worker restart.  
Analogy: A signed paper form in a filing cabinet, not a sticky note on a monitor. The cabinet survives the night shift.  
Under the hood: The approval condition is a predicate, the `when` argument of the human-approval middleware. On resume, the framework re-runs it to find the call it paused. So the predicate must be deterministic for the same call: decide from the SQL and the column tags, never from a model judgement or the clock, or the resumed run may not find its own pause. Batched versus per-call is a real trade-off: batching asks one question for several tool calls and saves a person's time, while `interrupt_mode="per_call"`, available from langchain 1.4.6, asks once per call and gives an exact audit. Setup detail: the Postgres checkpointer needs one setup run that creates indexes concurrently, so it needs autocommit connections, and it has no schema option, so a dedicated pool sets the search path.  
Source 16: LangChain human-in-the-loop (https://docs.langchain.com/oss/python/langchain/human-in-the-loop), in summary: the middleware interrupts on configured tool calls and resumes with a list of decisions such as approve or reject.  
Transfer: Use this for refunds, deploys, outbound emails, and data exports. Store the pause durably, show the approver the exact action, restrict decisions to approve or reject, and keep the trigger a pure function of the action.  
Evidence from this course: in the paired measurement of 24 October, one run of each half, with the Postgres checkpointer the held California export was approved after a worker restart and posted; with the in-memory checkpointer the approval was lost and the run failed. The pair of 23 October showed the same.  
Point at: the why line, then the last row of the table: the condition re-runs on resume, so it is decided from the SQL and the column tags; then the evidence line.  
Ask: "Why is 'ask the reviewer agent whether this needs approval' a bad condition?" Expected: it can answer differently on resume, and the run loses track of its pause.  
Likely question: "What if nobody ever approves?" Answer: The run stays held and visible on the board; the kill switch can block it, and you can add an expiry that rejects.  
Likely question: "Why forbid edits?" Answer: An edited query skips every grader that passed the original; reject and ask again instead.  
Misconception: "The approval is just a user interface dialog." Correction: The dialog is a view; the approval is a durable checkpoint plus a decision record.  
Transition: Approvals decide single actions. Who decides what may run unattended at all, and how do we stop everything?

**Slide 50: 4) A router, levels, and a stop for running work**

Container: two-column cards: how it works | worked example, then evidence, trade-offs, at-work lines and a key-idea bar

On the slide:

Principle: the stop must reach the run that is already running.
Why it matters: a stop checked only when a job is claimed lets the run in flight finish and post.

| How it works in DataPilot | Worked example |
|---|---|
| Router: event type to handler and policy | Three event types, no model call |
| Kill switch: checked before each step | Every model call and tool call |
| Engaging it forces the report-only level | Answers post labelled unverified |
| Assisted: personal data needs approval | California export: held for approval |

Evidence: checked at claim, the running job posted; before each step, it stopped.
At work: write policy as data; start at the lowest level.
Key idea: check before the model call.

Speaker notes:

Time: 4.5 minutes (2:14-2:18:30)  
Trade-offs, said aloud: a stop ends new steps; committed effects stay.  
Plain explanation: Three pieces of control sit around the agent. The router is a table from event type to handler and policy. The autonomy level says how much may happen without a person. The kill switch stops everything, including runs already in flight, and drops the system to the most restrictive level.  
Concrete example from DataPilot: The class starts at the report-only level, from `autonomy.default_level` in pack.yaml. The level demotes on its own after 3 consecutive escalations, from `autonomy.demote_after_consecutive_escalations`, and on the kill switch. The kill switch is checked in two places: a `before_model` hook that jumps to the end of the run, and a tool wrapper that returns a message without calling the tool. The planted bug the kill switch at claim only (`BUG_KILLSWITCH_AT_CLAIM_ONLY`) checks only when a worker claims a job, which is exactly the failure from the story.  
Analogy: A train's emergency brake works on a moving train, not only at the station.  
Under the hood: Where a stop lives decides whether it works. We verified with fake models that a kill switch inside a tool wrapper that returns a jump to the end does not end the run: control goes back to the model, which can call another tool. A hook that runs before every model call and returns a jump to the end does stop it, and the tool short-circuit covers calls already decided. So the run stops at its next step, not at its next job. The three levels and the kill switch that drops the system to the report-only level come from Cobus Greyling's loop engineering patterns. Router versus supervisor: a supervisor agent decides who acts next by reading state; a router reads a type. Use a supervisor when the next step depends on open-ended content; use a table when the input set is closed.  
Source 17: Loop engineering (https://cobusgreyling.github.io/loop-engineering/), in summary: autonomy moves from report-only to assisted to unattended; an incident or cost spike drops unattended back to assisted, and the kill switch drops either level to report-only.  
Source 11: LangChain custom middleware (https://docs.langchain.com/oss/python/langchain/middleware/custom), in summary: hooks run before and after model calls and around tool calls, and a `before_model` hook can jump to the end of the run.  
Transfer: For any agent at work, write the policy as data, start at the lowest level, list your demotion triggers, and put the stop check before the model call, the one step every loop iteration passes through.  
The levels, for the room: at the report-only level answers post labelled unverified and no export runs; at the assisted level answers post and anything touching personal data, or an export, needs approval; the unattended level is for eligible metric families only, which Section 4 earns.  
Evidence from this course: in the paired measurement of 24 October, one run of each half, with the kill switch at claim only the run in flight posted after the switch was engaged; with the check before every model and tool call, it stopped in flight. The pair of 23 October showed the same.  
Point at: the why line, the four rows, then the evidence line.  
Ask: "Why check before the model call and not after it?" Expected: before is the last point where nothing new has been decided or spent.  
Likely question: "Does the kill switch roll back what already ran?" Answer: No. It stops new steps; effects already committed stay, which is why concept one's keys and approvals matter.  
Likely question: "Who can raise the level again?" Answer: A person, after evidence. Section 4: Hill-climbing loop shows how a metric family earns the unattended level.  
Transition: The four moves on one slide.

**Slide 51: Cheat sheet: the event loop in four moves**

Container: table: move, principle, anti-pattern, check question

On the slide:

| Move | Principle | Anti-pattern it prevents | Check question |
|---|---|---|---|
| Key every effect | Delivery repeats; effects must not | Random ids per arrival | What happens on the second arrival? |
| Claim, lease, reap | Short claims; leases cover work | A lock held through the model call | Can a frozen worker overwrite a job? |
| Durable approval | The pause is state | Approvals held in memory | Does a pending approval survive a deploy? |
| Router, levels, stop | The stop reaches running work | A stop checked only at claim | Can your stop end a run mid-flight? |

Speaker notes:

Time: 0.5 minutes (2:18:30-2:19)  
Say: Read the four rows as a checklist you can take to any agent that runs on events. Each row pairs a move with its principle, the anti-pattern it prevents, and a question you can ask of your own system on Monday. Two of these anti-patterns you are about to see switched on and off live: the missing key and the stop checked only at claim. The lock held through the model call is in the code and its tests; the approval held in memory is shown only on request.  
Point at: the check-question column, bottom row first: can your stop end a run mid-flight?  
Likely question: "Which move would you add first to an existing system?" Answer: Keys, because duplicates are silent and the fix is one constraint.  
Likely question: "Where is the router?" Answer: In the last row, and implicitly in every row: it picks the handler and policy for each event type.  
Transition: Now all four, live.

**Slide 52: Section 3: Event loop - Implementation Notes: The kill switch in flight**

Container: demo layout: laptop and badge, what to watch for, guaranteed moment, link

On the slide:

Badge: DEMO - 3
What to watch for:
- The webhook question: one strip from Queued to Done, one post labelled unverified
- The approval that survives a restart: the export stays held across the restart
- Duplicate events: three deliveries, one answer, two duplicates ignored
- The kill switch in flight: the running strip moves to Blocked by kill switch
Guaranteed moment: with the check before every model and tool call, the run in flight stops at its next step and the system is held at the report-only level.
Link: Demo page on GitHub | https://github.com/ANI-IN/loop-engineering/tree/main/section-3-event-loop/demo#the-kill-switch-in-flight

Speaker notes:

Time: 22 minutes (2:19-2:41)  
Run sheet: four core demos, about 15 minutes, in the order below; then the code walkthrough, about 7 minutes. Share the console Events page full screen: the run board on top, the channel below. Optional, cut first: the digest now. Every core demo's moment has been shown live, in calibration retakes and again on 24 October, both halves and the optional digest included; rehearse each twice in a row with a reset between before class (instructor guide, the day before, step 4). The measured times are under each demo. A planted half is `make demo NAME=<demo> PLANTED=1`, its bugs on for its own runs only; `.env` stays as it is. The slide's link opens the section's demo page on GitHub.  
Demo: The webhook question.  
Guaranteed moment, from the demo registry: A question arrives as a webhook, becomes an event and a job, moves across the run board lanes, and is posted to the channel labelled unverified at the report-only level.  
Starting state: the Events page is empty, the status line shows the report-only level and the class session's start time, and no planted item is on. Reset first: `make reset NAME=event-loop`.  
Do: Events > Send webhook question, or `make demo NAME=events-webhook-question`.  
Narrate: This is the same analyst as Section 1: Agent loop, but nobody pressed Ask. A webhook became an event row and a job row, and a worker claimed it with the short claim from concept 2, the queue is a table.  
Point at, in order: the strip appearing in Queued, moving to Running, Verifying, and Done; the channel post labelled unverified because we are at the report-only level (concept 4); and last the live stamp: the run's start time in your local time and its trace link.  
Expected live result: one strip moves from Queued to Done and one post appears, labelled unverified. Measured: 46 seconds; run twice more after the reviewer was given the business date, both posted unverified. Shown again live on 24 October.  
May vary: the time in each lane, the answer's wording, and the count. The question asks for the orders of the previous day, 30 January 2026 against the business date. In calibration it answered 300 orders, the day in Eastern time, which is right, and 291, the same day counted in UTC, which is the Eastern time trap; the reviewer approved both. Keep a 291 on screen and teach it: the reviewer has the same starting knowledge, with no time-zone rule, and this is why the orders family posts at the report-only level, labelled unverified. Section 4: Hill-climbing loop earns the rule. Do not reset for a better number.  
If it stalls: reset and run it again, `make reset NAME=event-loop`, then the same trigger.  
Demo: The approval that survives a restart.  
Guaranteed moment, from the demo registry: A California marketing export touches personal data, so the run holds for human approval and the dialog states the exact SQL and row count. The worker is restarted; with the Postgres checkpointer the pending approval survives and approving resumes the run. With the in-memory checkpointer the pending approval is lost.  
Starting state: the board is clear after the first demo. Reset first if anything is held: `make reset NAME=event-loop`.  
Do: Events > Request California export, or `make demo NAME=events-approval-survives-restart`. When the strip reaches Holding for approval, restart the worker from the console's control, then click Approve in the dialog.  
Narrate: The query touches customer emails, so the policy routes it to human approval (concept 3, durable approval). The pause is a checkpoint in Postgres, keyed by the run. Restarting the worker is the deploy or crash from the story.  
Point at, in order: the dialog's exact SQL and row count; the strip staying in Holding for approval while the worker restarts; the strip moving to Done after Approve; and last the live stamp: the run's start time in your local time and its trace link.  
Expected live result: the pending approval survives the restart, and approving resumes the same run to Done. Measured: shown in 84 and 81 seconds. With the in-memory checkpointer (`BUG_MEMORY_CHECKPOINTER`), measured twice, the approval after the restart found nothing to resume: the pending approval was lost, and the run failed. Shown again live on 24 October, both halves.  
May vary: the row count wording and how long the restart takes. If it does, say: what matters is that the same run id resumes.  
If it stalls: reset and run it again, `make reset NAME=event-loop`, then the same trigger.  
Demo: Duplicate events.  
Guaranteed moment, from the demo registry: The same event is sent three times. With the missing idempotency, three answers are posted; with idempotency, one answer and "2 duplicates ignored". Firing the digest twice shows the same with the random digest id.  
Starting state: the Events page. Reset first: `make reset NAME=event-loop`.  
Do: `make demo NAME=events-duplicate-events PLANTED=1`, the missing idempotency (`BUG_NO_IDEMPOTENCY`) and the random digest id (`BUG_RANDOM_DIGEST_ID`) on for its own events; then reset, and Events > Send the same event three times, or `make demo NAME=events-duplicate-events`, with them off.  
Narrate: Delivery is at least once, and here are three deliveries of one event (concept 1, idempotent effects). Without a key, three effects; with the key and the conflict rule, one.  
Point at, in order: the repeated posts in the channel with the bug on, three answers to one question and two digests for one day; then one post and the count of two duplicates ignored with it off; and last the live stamp: the run's start time in your local time and its trace link.  
Expected live result: one post and two absorbed duplicates on the board. Measured: 1 run, 2 duplicates absorbed, and 1 digest, in 57 and 78 seconds. With both planted bugs on (`BUG_NO_IDEMPOTENCY` and `BUG_RANDOM_DIGEST_ID`), measured twice: 3 answers posted for one event, and the digest fired twice ran twice. Shown again live on 24 October, both halves.  
May vary: the timing of the duplicates. If it does, say: order does not matter; the key decides.  
If it stalls: reset and run it again, `make reset NAME=event-loop`, then the same trigger.  
Demo: The kill switch in flight.  
Guaranteed moment, from the demo registry: `make demo` sends the webhook question with demo pacing on for that run, and engages the kill switch while it is in flight. With the kill switch at claim only (the planted half, `make demo NAME=events-kill-switch-in-flight PLANTED=1`), the run keeps going; with the check before every model and tool call, it stops at its next step as blocked by kill switch and the system is held at the report-only level. Each half ends with the switch engaged, and an engaged switch blocks the next run at claim: `make reset NAME=event-loop` after each half, so nothing later is blocked.  
Starting state: the Events page. `make demo` switches demo pacing (`DEMO_PACING`) on for its own run, so the run moves slowly between steps, and sends the webhook question and engages the switch while it is in Running. Reset first: `make reset NAME=event-loop`.  
Do: `make demo NAME=events-kill-switch-in-flight PLANTED=1`, the kill switch at claim only (`BUG_KILLSWITCH_AT_CLAIM_ONLY`) on for that run; then `make reset NAME=event-loop`, since the first half leaves the switch engaged and an engaged switch blocks the next run at claim; then `make demo NAME=events-kill-switch-in-flight`, with it off. End with `make reset NAME=event-loop`: the switch stays engaged until a release, and it would block every later run, the finale included.  
Narrate: With the check at claim only, no new job starts, but the running one keeps going: that is beat four of the story. With the check before every model and tool call (concept 4), the run stops at its next step.  
Point at, in order: the strip still moving with the bug on; with it off, the strip moving to Blocked by kill switch; the kill switch indicator on the status line, with the level held at report-only; and last the live stamp: the run's start time in your local time and its trace link.  
Expected live result: the in-flight strip moves to Blocked by kill switch, and the status line shows the report-only level. Measured: stopped in flight in 33 and 8 seconds. With the check at claim only, measured twice: the in-flight run posted after the kill switch was engaged. Shown again live on 24 October, both halves.  
May vary: which step the run stops at. If it does, say: any step is correct as long as no model call starts after the stop.  
If it stalls: reset and run it again, `make reset NAME=event-loop`, then the same trigger.  
Optional, cut first: The digest now (Events > Run digest now, or `make demo NAME=events-digest-now`): the morning digest runs on demand under its business-date key and posts once.  
Code walkthrough: `make open-code NAME=event-loop` opens the files below, in the order of the section's demo walkthrough page.  
Open `platform/src/datapilot/loop3_events/api/events.py` lines 35-44: implements concept 1, idempotent effects, the duplicate events demo. Say: the database decides, not the code; `ON CONFLICT (event_id) DO NOTHING` returns no row for a repeat, and the repeat is recorded as a duplicate instead of a new job; with `BUG_NO_IDEMPOTENCY` on, a random suffix makes every delivery look new.  
Open `platform/src/datapilot/loop3_events/worker.py` lines 70-81: implements concept 2, the queue is a table, the webhook question demo. Say: the claim is one statement, the shape on the slide; `FOR UPDATE SKIP LOCKED` lets several workers claim at once without taking the same job; the lease, not an open transaction, marks the job as taken, so the claim commits at once and no lock is held through the model calls.  
Open `platform/src/datapilot/loop3_events/approvals.py` lines 44-47: implements concept 3, durable approval, the restart demo. Say: the pending approval is a LangGraph interrupt, and the checkpointer is where it lives; the Postgres saver keeps it across a worker restart; with `BUG_MEMORY_CHECKPOINTER` on, the in-memory saver loses it.  
Open `platform/src/datapilot/loop3_events/killswitch.py` lines 89-95: implements concept 4, the stop, the kill switch demo. Say: the middleware calls this check before each model call and each tool call; when the switch is engaged, the run guard records the stop and the run ends blocked by the kill switch at its next step; with `BUG_KILLSWITCH_AT_CLAIM_ONLY` on, a run that has started keeps going.  
Transition: Questions, then the poll.

**Slide 53: Questions**

Container: fixed question slide

On the slide:

No Question Is Too Small Every Question Deserves an Answer!!
Why not a message broker? What if nobody approves? Why 300, then 291?

Speaker notes:

Time: 6 minutes (2:41-2:47)  
Say: Take questions; this slot also holds the section's discussion time. If a question will not fit, ask the learner to post it with the word Thursday.  
Point at: the fixed question slide.  
Likely question: "Why Postgres and not a message broker?" Answer: The jobs, the approvals, and the answers share one database and one transaction model, so a claim, a checkpoint, and a post can be reasoned about together. A broker is a fine choice at higher volume, and the same keys and fences still apply.  
Likely question: "What if nobody approves?" Answer: The run stays held and visible; add an expiry that rejects after a set time, and the kill switch can block it.  
Likely question: "Can the event loop run at the unattended level today?" Answer: Not yet. Nothing has earned it; the poll is about exactly that.  
Likely question: "Why 300 orders one time and 291 the next?" Answer: 300 counts 30 January in Eastern time, the business day, and is right; 291 counts the same day in UTC, five hours early. The reviewer shares the starting knowledge, so it approved both; that is why the orders family is still at the report-only level.  
Transition: If time is short, skip the reference slides and go to the poll.

**Slide 54: Reference: skip if short on time - queue failure modes**

Container: table with a how-to-read line

On the slide:

How to read this: each row is one way a table-backed queue fails, what you see, and the defense.

| Failure | Symptom | Defense |
|---|---|---|
| Duplicate delivery | Two effects | Idempotency key, conflict rule |
| Worker dies mid-job | Job stuck running | Lease, heartbeat, reaper |
| Stale worker finishes or extends | Overwrites a re-claimed job | Fence on lease owner and attempt |
| Poison job | Endless retries | Attempt limit, dead state |
| Long transaction or assumed order | Bloat, wrong sequence | Short claim; never rely on order |

Speaker notes:

Time: 1 minute (2:47-2:48)  
Plain explanation: This table is the queue's failure model in one place. Each row is a way a table-backed queue goes wrong, the symptom you see, and the defense.  
Concrete example from DataPilot: Every row has a counterpart in the event loop: the event key, the worker's lease and heartbeat, the finish and the heartbeat fenced on lease owner and attempt number so a stale worker can neither finish nor extend a re-claimed job, the attempt limit and dead state, the claim that commits before the model call, and handlers that never assume order. A job also carries the spend activity of the command that started it, so the worker records each model call under that job's activity, not its own; calibration found demo runs counted under the worker's activity before that change.  
Analogy: A restaurant ticket rail. Tickets can be printed twice, a cook can walk out mid-order, and a ticket that always burns must be pulled off the rail.  
Under the hood: The two rows people miss are the last two. `SKIP LOCKED` skips rows another worker holds, so the queue is not strictly first in first out. A transaction left open, for example around a model call, keeps old row versions alive, and every claim scans past them until vacuum can clean up.  
Source 14: Postgres Job Queues & Failure By MVCC (https://brandur.org/postgres-queues), in summary: long-lived transactions stop dead row versions from being removed, and queue performance degrades as they accumulate.  
Transfer: Before you ship any worker pool, walk this table and name the line of code that defends each row.  
Point at: the how-to-read line, then the last row: long transactions and assumed order.  
Ask: "Which row does a model call inside a transaction break?" Expected: the long transaction row, and the worker-dies row too.  
Likely question: "How many attempts before a dead letter?" Answer: Few; a model that fails three times on the same input rarely succeeds on the fourth.  
Likely question: "Do we alert on dead letters?" Answer: You should; a dead letter is a job a person must look at.  
Misconception: "A reaper makes duplicates impossible." Correction: A reaper creates the second attempt; keys and fences render it harmless.  
Transition: Next reference slide.

**Slide 55: Reference: skip if short on time - router or supervisor**

Container: table with a how-to-read line

On the slide:

How to read this: go down the rows for your input; if most answers fall in the right column, a supervisor earns its cost.

| Question | Router table | Supervisor agent |
|---|---|---|
| Input set | Closed, typed | Open-ended text |
| Same input, same route | Always | Not guaranteed |
| Testable per route | One test per row | Only by sampling |
| Cost and injection risk | None; a payload cannot persuade it | A model call; a payload can |

Speaker notes:

Time: 1 minute (2:48-2:49)  
Plain explanation: This is the decision behind the section's question slide, in table form. A router table reads a type and returns a handler and a policy. A supervisor agent reads content and decides who acts next.  
Concrete example from DataPilot: Three event types, a question, a digest request, and an export request, each map to one handler and one autonomy policy. The router is deliberately not an agent, so the event loop adds no model call of its own.  
Analogy: A post office sorts by postcode, not by reading each letter.  
Under the hood: The routes that matter for safety, such as which events can export personal data, must be the same every time. A table gives that by construction. A supervisor can be right on average and still wrong on the one payload written to persuade it. If you do need judgement on open text, classify into a closed label set first, then route the label with a table, and log the label.  
Source 1: The art of loop engineering (https://www.langchain.com/blog/the-art-of-loop-engineering), in summary: the event-driven loop connects triggers such as cron and webhooks to the agent.  
Transfer: In your own multi-agent designs, count the steps that need judgement. Make everything else a table, and let agents work only where a table cannot.  
Point at: the how-to-read line, then the cost and injection row.  
Ask: "Which row decides it for an export?" Expected: same input, same route, plus injection risk.  
Likely question: "Is a supervisor ever cheaper?" Answer: When maintaining the table costs more than the calls, which happens with many fuzzy intents and low stakes.  
Likely question: "Can the router call an agent?" Answer: Yes; a handler can be an agent. The choice of handler is what stays deterministic.  
Misconception: "Multi-agent means every decision is an agent." Correction: Good multi-agent systems are mostly deterministic glue around a few judgement steps.  
Transition: Last reference slide: which clock the business uses.

**Slide 56: Reference: skip if short on time - business and wall clocks**

Container: table with a how-to-read line

On the slide:

How to read this: pick the clock by what the value is for, not by what is easy to read.

| Clock | Used for | Example |
|---|---|---|
| Business date | The previous day, schedules, keys | Data ends 31 January 2026 |
| Business time zone | Day boundaries | Digest at 8 a.m. Eastern time |
| Wall clock | When a run started | Live stamp in the viewer's local time |

Speaker notes:

Time: 1 minute (2:49-2:50)  
Plain explanation: An event loop has two clocks, and mixing them is a classic bug. The business clock decides what the previous day means, when the digest is due, and which key an alert gets. The wall clock records when something actually ran.  
Concrete example from DataPilot: The warehouse ends on 31 January 2026, and the class runs later. So the previous day, last month, the morning digest, every scheduled job, and fresh demo orders resolve against the business date, never the system clock. Day boundaries use Eastern time, so an order at 9 p.m. Eastern time belongs to that day even though its UTC date is the next one. The live stamp on each result is wall-clock time, shown in your local time, because it proves the run just happened. A unit test fails if business logic reads the clock, and agent SQL may not read the database clock either: the statement policy rejects it, because a question about the previous day once answered 0 when its SQL used the wall clock.  
Analogy: An accountant closing the books for the last quarter works today but dates every entry in that quarter.  
Under the hood: Keys built from the wall clock break idempotency, because a retry a second later gets a new key. Keys built from the business date are stable. Grouping by UTC date moves evening orders to the next day, which is Trap 4: Eastern time; the webhook question about the previous day answered 300 orders on the Eastern time day and 291 on the UTC day in calibration. Tests become reproducible when the business date is a setting.  
Source 13: PostgreSQL SELECT (https://www.postgresql.org/docs/current/sql-select.html), in summary: the reference for the queries whose date filters convert to the business time zone before truncating to a day.  
Transfer: In any agent that reports on data, name the business date explicitly, inject it as configuration, and keep the wall clock for audit stamps only.  
Point at: the how-to-read line, then the key column of the business-date row.  
Ask: "Which clock should the anomaly alert in Assignment 3: Event loop use for its key?" Expected: the business date.  
Likely question: "Why not just use today's date?" Answer: Because the data ends on the business date; asking about the previous day by the wall clock returns nothing.  
Likely question: "Why show local time on the stamp?" Answer: So every viewer can check the run happened minutes ago, in their own time.  
Misconception: "Time zones only matter for display." Correction: They decide which day an order belongs to, and so the revenue for that day.  
Transition: Now the poll.

## Poll

| # | Slide | Layout | Time (start-end) | Says in one line | Source in the repository |
|---|---|---|---|---|---|
| 57 | Live Zoom Poll | blank | 2:50-2:55 | We are launching a poll on Zoom. Please take 2 minutes to fill out the form. | docs/instructor-guide.md |

### Slides and speaker notes: Poll

**Slide 57: Live Zoom Poll**

Container: fixed template slide

On the slide:

Live Zoom Poll
We are launching a poll on Zoom. Please take 2 minutes to fill out the form.

Speaker notes:

Time: 5 minutes (2:50-2:55)  
Say: Before you launch the poll, start the baseline experiment on the Improve page so it runs through the break. It is the class session's baseline; the console accepts no baseline from another session.  
Instructor reference: Improve > Run experiment on the active version, or `make demo NAME=improve-baseline-experiment`.  
Then launch the poll: "Which autonomy level would you grant the revenue digest today, and why?" Options: the report-only level, the assisted level, the unattended level. Read the result aloud. Keep it for Section 4: Hill-climbing loop, which shows what evidence the unattended level should need.  
Point at: the poll window, then the benchmark progress strip on the run board.  
Likely question: "Is there a right answer?" Answer: without holdout evidence, the report-only or the assisted level; Section 4 shows how a metric family earns more.  
Transition: A 10-minute break; the baseline keeps running.

## Break

| # | Slide | Layout | Time (start-end) | Says in one line | Source in the repository |
|---|---|---|---|---|---|
| 58 | Time for a Break | blank | 2:55-3:05 | A 10-minute break is starting now. Please return when the timer ends to continue the presentation | - |

### Slides and speaker notes: Break

**Slide 58: Time for a Break**

Container: fixed template slide

On the slide:

Time for a Break
A 10-minute break is starting now. Please return when the timer ends to continue the presentation

Speaker notes:

Time: 10 minutes (2:55-3:05)  
Do, at the start of the break, in the demo terminal: `make demo NAME=improve-naive-analyzer-blocked PLANTED=1`. It queues the naive analyzer and its candidate experiment behind the baseline, with the planted bug on for those two requests only. The command plants it with or without PLANTED=1. The console's Improve > Run the naive analyzer (planted), shown while demo controls are allowed, queues the same two requests; its Run analyzer button runs the analyzer team.  
Say: Write the return time, 3:05, in the chat. Check once that the grouped benchmark progress strip on the run board is counting up.  
Point at: the timer.  
Likely question: "Will the experiment finish in time?" Answer: yes; at concurrency 8 a 70-run experiment took 171.3 to 459 seconds of experiment wall time, and the baseline 236 to 386 seconds from the trigger, the longest on a shared machine, inside the poll and the break.  
Transition: Welcome back. The poll asked how much autonomy to grant; now we earn it.

## Section 4: Hill-climbing loop

The failure this section fixes: Rules learned from the questions they were written for raise that score, break other answers, and then get trusted to run unattended on too little evidence.

Measured live: the baseline experiment shown in 285 and 266 seconds, the starting version at 2 of 15 holdout passes; the analyzer team shown in 62 and 98 seconds, 7 and 8 rules through the overfit guard; the candidate experiment not shown, 3 and 6 of 15 against 2 with 0 regressions (the version promoted on 22 October scored 11 and 12 of 15); cleared for the unattended level not shown, both attempts posted at the assisted level with a wrong answer after those weak candidates, while on 22 October the fiscal year 2025 revenue question by webhook was right at the assisted level. On 23 October the analyzer team at reasoning effort high gave candidates of 2, 9, and 5 of 15 from the same failed development questions, so the spread stays; the finale chain on the confirmed standard promoted the best, 10 of 15 against 2 with 0 regressions, cleared average order value and products but not revenue (one revenue item fell short twice), and posted the fiscal year 2025 revenue question at the assisted level with a wrong answer, 63,986,616.77 dollars against gold 64,015,091.21, from an internal-account filter that was too broad; the naive analyzer's first live attempt, before it was made deterministic, passed 15 of 15 holdout items and the gate did not block it. In the live session of 23 October, afternoon, with the SQL guidance check and two candidates chosen on the development split: candidate A 18 of 25 development questions with 11 rules, candidate B 19 of 25 with 8 rules, B kept as version 8, the guidance check rejecting none of its rules, in 326 seconds; version 8 passed 14 of 15 holdout items against 2, 12 of 13 trap items fixed, 0 regressions; revenue, average order value, customers, and products cleared, orders not; the fiscal year 2025 revenue question correct, 64,015,091.21 dollars, posted at the unattended level; and the deterministic naive analyzer blocked twice, 21 rules all flagged, holdout 2 of 15. In the capture session of 23 October, evening: candidate A 21 of 25 development questions with 8 rules, candidate B 10 of 25 with 5 rules, A kept as version 9, in 377 seconds; version 9 passed 14 of 15 holdout items against 2, 0 regressions, in 186 seconds; the finale held 5 times over 50 seconds while the promotion and its clearance re-runs finished, then the fiscal year 2025 revenue question correct, 64,015,091.21 dollars, posted at the unattended level with the same four families cleared; and the naive analyzer blocked a third time, 20 rules all flagged, holdout 2 of 15. In the live session of 24 October, every core and optional demo showed its moment: the naive analyzer wrote 21 rules, all rejected by the overfit guard, holdout 2 of 15, blocked; the analyzer team took 359 seconds for two candidates, A 13 of 25 development questions with 8 rules and B 14 of 25 with 6 rules, one kept as version 11; the candidate experiment took 212 seconds, version 11 at 13 of 15 holdout items against 2 for version 1, 0 regressions; version 11 was the active version 5 seconds after approval, and the finale was held while the clearance re-runs ran; the finale under version 11 answered 64,015,091.21 dollars, matching gold, posted at the unattended level with revenue, average order value, and customers cleared; the safeguard was rehearsed after a reset and its finale was correct again; and the over-broad rule on version 11 passed 7 of 15 holdout items against 12, with 4 regressions on development questions and 5 on holdout items, and was blocked.

The demo: `make demo NAME=improve-baseline-experiment`, `make demo NAME=improve-naive-analyzer-blocked`, `make demo NAME=improve-analyzer-team-approve`, `make demo NAME=improve-candidate-experiment`, `make demo NAME=improve-cleared-unattended`, launched at 2:50 for the baseline experiment, during the poll; 2:55 for the naive analyzer, at the break; the rest at 3:25 on the DEMO slide, code walked at 3:40, recovery `make reset NAME=hill-climbing-loop` and re-run: reset and run it again, live.

| # | Slide | Layout | Time (start-end) | Says in one line | Source in the repository |
|---|---|---|---|---|---|
| 59 | Agenda (Section 4 highlighted) | concept | 3:05-3:05:30 | Section 4: Hill-climbing loop, the loop that improves the other three | section-4-hill-climbing-loop/README.md |
| 60 | Failure story: the prompt full of patches | diagram | 3:05:30-3:07 | Illustrative: a patch per failed question raises the score and breaks other answers | section-4-hill-climbing-loop/concepts.md |
| 61 | Hill-climbing loop: promote rules when the development score rises? | concept | 3:07-3:09 | KEY IDEA: No. Holdout questions never seen, zero regressions, and human approval decide | section-4-hill-climbing-loop/README.md |
| 62 | 1) A benchmark is a measuring instrument | table | 3:09-3:13 | Key idea: score results, not query text, on data built to expose each trap | platform/src/datapilot/loop4_hill_climbing/evaluator.py; Source 8 |
| 63 | 2) Rules learned from failures overfit | diagram | 3:13-3:17 | Key idea: split diagnosis, proposal, and criticism, then guard the rules in code | platform/src/datapilot/loop4_hill_climbing/analyzer.py; overfit_guard.py; Sources 18-20 |
| 64 | 3) The gate is a paired comparison | table | 3:17-3:21 | Key idea: compare item by item on the same holdout; a confirmed regression blocks | platform/src/datapilot/loop4_hill_climbing/gate.py; measurement.py; pack.yaml evaluation |
| 65 | 4) Autonomy is earned per metric family | table | 3:21-3:24:30 | Key idea: grant the unattended level per family, from that family's holdout evidence | platform/packs/datapilot_us/benchmark/holdout.yaml; pack.yaml autonomy; Source 17 |
| 66 | Cheat sheet: the hill-climbing loop in four moves | table | 3:24:30-3:25 | Score by execution, split the learning, gate per item, earn autonomy per family | section-4-hill-climbing-loop/README.md |
| 67 | Section 4: Hill-climbing loop - Implementation Notes: The candidate experiment | demo | 3:25-3:45 | Badge DEMO - 4, what to watch for, the guaranteed moment, and the demo page link; the demos and the code walkthrough are in the notes | section-4-hill-climbing-loop/demo/walkthrough.md; platform/demos/registry.yaml |
| 68 | Questions | concept | 3:45-3:48 | Fixed question slide; open question: is N holdout questions enough evidence | - |
| 69 | Reference: skip if short on time - gate statistics | table | 3:48-3:49 | How small holdouts behave: intervals, flaky items, three schemes, and the stability filter | computed for the course; pack.yaml evaluation |
| 70 | Reference: skip if short on time - prior art compared | table | 3:49-3:49:30 | Genie, Cortex Analyst, Vanna, and LangChain's loop against this gate | Sources 1, 21-23 |
| 71 | Reference: skip if short on time - when learned knowledge fails | table | 3:49:30-3:50 | Failure modes of learned knowledge, their evidence, and the guard for each | Sources 18-20; pack.yaml evaluation; knowledge/v2-overbroad.yaml |

Numbers this section states (each gets a "Re-check after live runs" line in its notes):

- 40 benchmark items, 25 development and 15 holdout, so 70 runs per experiment: from `platform/packs/datapilot_us/benchmark/dev.yaml` and `holdout.yaml` with `evaluation.holdout_repeats`.
- Holdout questions per metric family (revenue 4, orders 4, customers 3, products 3, average order value 1): from `platform/packs/datapilot_us/benchmark/holdout.yaml`; calibration replaced 3 unstable items, then restored the reviewed holdout, so 0 were replaced in the end: docs/calibration-report.md, Stability and the holdout.
- Holdout passes 2 of 15 under the starting version and 12 of 15 under the promoted one; 10 of 13 holdout trap items flipped; 0 regressions on either split: docs/calibration-report.md, Model bake-off. On 23 October version 5 passed 10 of 15 against 2, 8 fixed, 0 regressions on either split, 15 of 25 development questions, in 257.6 seconds: docs/calibration-report.md, Resumed after the ledger correction.
- Wall time of one 70-run experiment at concurrency 8: 171.3 to 459 seconds over every 70-run experiment, two candidates at reasoning effort high taking 458.9 and 403.8; cost 0.0594 to 0.0914 dollars: docs/calibration-report.md, Wall time, and Live session of 25 October 2026, What this session supersedes.
- Analyzer team candidates from the same kind of input: four runs at reasoning effort medium gave 11, 3, and 6 of 15 holdout passes against 2, and 2 for version 3 in an earlier session, with the first candidate re-measured at 12: docs/calibration-report.md, Analyzer comparison; 2, 9, and 5 of 15 at reasoning effort high from the same failed development questions: docs/calibration-report.md, Resumed without traces. The response is two candidates chosen on the development split only, `analyzer.candidates` 2 in pack.yaml; measured twice, the kept candidate passed 14 of 15 both times and the step took 326 and 377 seconds: docs/calibration-report.md, Live sessions of 23 October, afternoon and evening.
- A family clears for the unattended level on the gate's confirmed standard: every holdout item passes 2 of 3 runs, an item that falls short passes 2 of 3 more: `evaluation` in pack.yaml and docs/calibration-report.md, Stability and the holdout. On 23 October average order value and products cleared; revenue did not: net-revenue-cyber-monday-2025 failed 3 of 3, then passed 2 of 3 more, and app-share-net-revenue-fiscal-2026 passed 1 of 3, then 1 of 3 more: docs/calibration-report.md, Resumed after the ledger correction. In the afternoon session of 23 October revenue, average order value, customers, and products cleared, revenue with no re-run; orders did not: business-day-orders-november-2025 failed 3 of 3, then 0 of 3 more: docs/calibration-report.md, Live session of 23 October, afternoon. In the evening the same four families cleared under version 9: docs/calibration-report.md, Live session of 23 October, evening.
- The finale of 23 October, morning, posted at the assisted level, labelled verified, 63,986,616.77 dollars against gold 64,015,091.21, 16,291 tokens; that total is exactly the one an internal-account filter that is too broad gives, `NOT ILIKE '%harborpine%'`, which also removes the look-alike addresses. The finale of the afternoon session of 23 October, and again the finale under version 9 that evening: 64,015,091.21 dollars, gold passed, posted at the unattended level: docs/calibration-report.md.
- The naive analyzer's first live attempt, before it was made deterministic: 21 rules, 15 of 15 holdout and 25 of 25 development questions, the gate ready for human approval; the deterministic naive analyzer, three times since: 21, 21, and 20 rules, all flagged, holdout 2 of 15, blocked: docs/calibration-report.md. The gate's four conditions: `platform/src/datapilot/loop4_hill_climbing/gate.py`.
- Experiment runs traced as a sample of about 1 run in 5, demo and check runs in full: `tracing.experiment_sample_rate` 0.2 in pack.yaml. <!-- refresh after the session: trace sampling seen live after the LangSmith limit resets on 1 November -->
- Holdout 3 runs and pass on 2; an apparent regression on the development questions re-run 2 more times under each version, counted when the candidate fails 2 of 2 and the active version passes 2 of 2; concurrency 8; overfit guard 6 words and 20 SQL tokens: from `evaluation` in `platform/packs/datapilot_us/pack.yaml`.
- Confirming re-run of an apparent holdout regression (3 more runs, 2 of 3 must fail again) and the calibration stability filter (5 runs per item under each version, kept at 4 or 5 of 5 or 0 or 1 of 5): `evaluation` in pack.yaml.
- MAGIC 56.52, 57.76, 59.13 on BIRD's development set and 78.62 to 85.66 on Spider's development set, when correcting only queries already known to be wrong; 56.52 to 58.55 on BIRD's development set when applied to every query: Source 18, Tables 1 and 2.
- SEED 148 pairs (9.65 percent) without evidence, 105 (6.84 percent) with wrong evidence, CodeS-15B 44.76 to 54.29: Source 20.
- 6.5 percent mean false positives on one database, 11.0 percent on extra-hard queries, across 21 systems: Source 8.
- 10 of 15 gives a 95 percent interval of 0.42 to 0.85; 12 of 15 gives 0.55 to 0.93; 13 of 15 gives 0.62 to 0.96; 14 of 15 gives 0.70 to 0.99: Wilson intervals, computed for the course.
- Three holdout items flaky at 0.7 per run: about 51 percent chance of a false regression on single runs, about 43 percent with pass on 2 of 3, about 11 percent with 2 of 3 plus a confirming 3-run re-run (computed for the course).
- Cortex Analyst suggests up to 10 verified queries at a time; Genie's chat-mode benchmarks compare numbers to 4 significant digits: Sources 22 and 21.
- N, the minimum holdout questions per family before the unattended level: 3, the calibration report's recommendation, built by Assignment 4: Hill-climbing loop, not in class code.
- Version 1 of the knowledge (the starting version) against version 8 in one live session: holdout 2 and 14 of 15, development questions 4 and 19 of 25, 12 of 13 holdout trap items fixed, 0 regressions on either split: docs/benefits.md, Section 4: Hill-climbing loop.
- The analyzer team, 359 seconds, two candidates, A 13 of 25 development questions with 8 rules, B 14 of 25 with 6 rules, the kept candidate version 11: the live session of 24 October 2026.
- The candidate experiment, 212 seconds, version 11 at 13 of 15 holdout items against 2 for version 1, 0 regressions: the live session of 24 October 2026.
- Version 11 active 5 seconds after approval; the finale held while the clearance re-runs ran: the live session of 24 October 2026.
- The finale under version 11: 64,015,091.21 dollars, matching gold, posted at the unattended level with revenue, average order value, and customers cleared; the safeguard rehearsed after a reset, its finale correct again: the live session of 24 October 2026.
- The naive analyzer: 21 rules, all rejected by the overfit guard, holdout 2 of 15, blocked: the live session of 24 October 2026.
- The over-broad rule on version 11: 7 of 15 holdout items against 12, 4 regressions on development questions and 5 on holdout items, blocked: the live session of 24 October 2026.

### Slides and speaker notes: Section 4: Hill-climbing loop

**Slide 59: Agenda (Section 4 highlighted)**

Container: step cards: four sections, the fourth highlighted

On the slide:

1. Agent loop
2. Verification loop
3. Event loop
4. Hill-climbing loop (now): learn rules from failures, and trust them only on evidence

Speaker notes:

Time: 0.5 minutes (3:05-3:05:30)  
Say: Welcome back. Three loops are now in place. The agent loop answers with good tools and a checkable envelope. The verification loop stops unsafe and malformed work and hands the agent reasons it can act on. The event loop runs questions as jobs, holds personal data for human approval, and stops on the kill switch. What none of them does is get better. The fiscal year 2025 revenue question, net revenue in fiscal year 2025, is still wrong, because the business rules are still missing. This last section is the loop that learns those rules from failures, and the hard part is not learning. The hard part is knowing whether what was learned is true, and how much trust it earns. The baseline experiment you saw start at the poll has been running through the break; it is the class session's baseline, and we read it first in the demo.  
Point at: the highlighted fourth row, then back at the first three to recall what each loop already guarantees.  
Likely question: "Is the baseline experiment finished?" Answer: It should be; the run board shows its progress strip. If it is not, we read what is done and let it finish while the concepts run.  
Transition: First, the way most teams improve an agent today, and why it goes wrong.

**Slide 60: Failure story: the prompt full of patches**

Container: step cards: four numbered beats, then the lesson bar

On the slide:

Illustrative
1. **Patches**: after the monthly check, one prompt line is pasted per failed question, including the fiscal year 2025 net revenue answer.
2. **Score**: the same check rises the next day, because it asks the questions the patches were written for.
3. **New wording**: next month's questions use other phrases, and the fiscal year answers are wrong again.
4. **Regression**: a discounted-orders question that passed now fails, because one patch dropped discounts from revenue.
Lesson: a score measured on the questions you tuned on rises by construction.

Speaker notes:

Time: 1.5 minutes (3:05:30-3:07)  
Say: This story is illustrative and the person is fictional. Dana, an analytics engineer at Harbor & Pine, owns the analytics agent. The monthly check shows a set of failed questions, among them the net revenue for fiscal year 2025. Dana does what most of us have done: one patch per failure, pasted into the prompt. "Fiscal year 2025 runs February 2024 to January 2025." "For the top customers question, leave out the account ending in harborpine." The score on the monthly check jumps the next day, because the check asks exactly the questions the patches name. Then the next month's questions arrive, phrased differently, and they are still wrong, because the patches named questions, not rules. Worse, a question about discounted orders that used to pass now fails, because one patch said to drop discounts from revenue. Nobody can say which patch broke it, because the prompt grew by twenty lines and was never measured on anything it had not seen.  
Point at: the four beats in order, and stop on beat four: a regression nobody saw. Then read the lesson bar.  
Likely question: "Is this not just normal prompt tuning?" Answer: It is, and that is the problem. It is measured on the same questions it was tuned on, so the score rises by construction.  
Transition: So the tempting rule is simple: if the score goes up, ship it.

**Slide 61: Hill-climbing loop: promote rules when the development score rises?**

Container: key-idea box: question line, key idea, three reason cards

On the slide:

KEY IDEA: No. Promote only on holdout questions the analyzer never saw, with zero regressions and human approval.
- A development score measures memory of the questions the rules came from
- The same learned-guideline method gained on one model and dropped on another
- An average can hide one broken answer behind six fixed ones

Speaker notes:

Time: 2 minutes (3:07-3:09)  
Say: No. A score on the questions the rules were written from measures memory, not generalisation. MAGIC, Source 18: MAGIC: Generating Self-Correction Guideline for In-Context Text-to-SQL (https://arxiv.org/abs/2406.12692), learns a self-correction guideline from training failures; in their words, "MAGIC's guideline outperforms expert human's created ones." Then a later survey re-ran it. Source 19: Toward Real-World Table Agents (https://arxiv.org/html/2507.10281) found small gains over the baseline, lower scores with Qwen2.5-Coder-32B on both Spider's development set and BIRD's development set; in summary, feedback refinement gained little for weaker models. Same method, different model, different verdict. That is the second reason on the slide, and the argument for a gate that decides on questions the learner never saw.  
Say: So the verdict has three parts. First, a holdout split the analyzer team never reads. Second, zero regressions, item by item, on both splits, which is the third reason on the slide. Third, a person approves the knowledge diff. Each part closes a different hole, and we take them in order.  
Point at: the KEY IDEA box, then the three reasons, top to bottom.  
Likely question: "Is a holdout split new?" Answer: No; every machine-learning engineer uses one. What we have not seen documented is the combination with zero regressions, human approval, an overfit guard, and autonomy granted per metric family.  
Transition: Before any of that, the instrument itself has to be right.

**Slide 62: 1) A benchmark is a measuring instrument**

Container: two-column cards: how it works | worked example, then the key-idea bar

On the slide:

Principle: score results, not query text, on data built to expose each trap.
Why it matters: a wrong scorer makes every later decision climb on noise.

| How it works in DataPilot | Worked example |
|---|---|
| Run both queries live; compare results | Another join order passes |
| Seed rows that trigger each trap | Cancelled and internal orders change the total |
| Check a second database | One alone: 6.5 percent false positives |
| Split development and holdout | 25 to learn from, 15 to decide |

Evidence: under the starting knowledge, 2 of 15 holdout items pass and 0 of 13 holdout trap items.
At work: score outcomes on fixtures that separate right from nearly right; hold questions back.
Key idea: an evaluation you cannot trust turns hill-climbing into noise.

Speaker notes:

Time: 4 minutes (3:09-3:13)  
Trade-offs, said aloud: trap rows and a second database cost seeding work.  
Plain explanation: Before you can improve anything, you need a measurement you trust. A benchmark is an instrument, and instruments have errors in both directions. It can call a right answer wrong, and it can call a wrong answer right. Each row on this slide removes one of those errors. The first two keep you from rejecting good answers and accepting bad ones. The last two keep the score honest as soon as something starts learning from it.  
Concrete example from DataPilot: The benchmark has 40 questions, 25 in the development split and 15 in the holdout split, with no ambiguous category. Each has gold SQL written by hand. The evaluator runs the agent's SQL and the gold SQL live, on two databases, `warehouse` and `warehouse_alt`, and compares the normalized results with a numeric tolerance. The planted SQL text evaluator (`BUG_SQL_TEXT_EVAL`) compares query text instead, and marks a correct query wrong because it joins in a different order. That is the first row of the worked example. The seeded rows are chosen so every trap changes a naive answer: cancelled orders exist in the period, internal accounts sit among the top spenders, and evening orders cross the UTC date.  
Analogy: A kitchen scale is checked with known weights, more than one, before anyone trusts a recipe built on it.  
Under the hood: One database is not enough. Measured across 21 Spider submissions, checking results on the original database alone gave a 6.5 percent mean false-positive rate, and 11.0 percent on extra-hard queries. Their fix fuzzes about a thousand random databases per schema and keeps those that tell neighbour queries apart, about 42 per query. Two databases is the teaching-sized version of that idea. A trap-sensitivity test proves the data does its job: the naive SQL must give a different answer from the gold SQL, or the item tests nothing. One experiment is 25 development question runs plus 15 holdout items times 3 runs, so 70 runs.  
Source 8: Semantic Evaluation for Text-to-SQL with Distilled Test Suites (https://arxiv.org/abs/2010.02840): "Our method distills a small test suite of databases that achieves high code coverage for the gold query".  
Transfer: The same instrument applies to any LLM feature you evaluate. Score the outcome that matters, never the surface text. Build fixtures that separate the right behaviour from its nearest wrong neighbour. Keep a second fixture set. Hold questions back before anyone tunes on the rest.  
Evidence from this course: the starting version passed 2 of 15 holdout items and 0 of 13 holdout trap items in every baseline measured; in the live session of 23 October, version 1 passed 2 of 15 holdout and 4 of 25 development questions. That low, stable floor is what makes a later rise readable.  
Point at: the why line, the how-it-works column top to bottom, the second-database example, the evidence line, then the trade-offs line.  
Ask: "Why does comparing SQL text fail even when it looks stricter?" Expected: many correct queries exist for one question, so text match rejects right answers.  
Likely question: "Why not just ask a model to judge the answer?" Answer: A judge adds a second error source with the same blind spots. Execution match is deterministic and repeatable; keep model judges for text you cannot execute.  
Likely question: "Does order matter in the comparison?" Answer: Only when the question asks for an order; each item says so, and ties are broken deterministically in the gold SQL.  
Re-check after live runs: the 25 development and 15 holdout items and the 70 runs per experiment against the benchmark files and `evaluation.holdout_repeats`.  
Transition: Now something learns from this instrument, and that is where it gets dangerous.

**Slide 63: 2) Rules learned from failures overfit**

Container: two-column cards: how it works | worked example, then evidence, trade-offs, at-work lines and a key-idea bar

On the slide:

Principle: a rule written from a failure fits that failure; no agent grades its own rule.
Why it matters: a rule naming the failed question raises the score it was tuned on, and nothing else.

| How it works in DataPilot | Worked example |
|---|---|
| Failure analyst: diagnosis, no rules | What went wrong, and why |
| Rule writer proposes; critic only cuts | Kept: the February-to-January fiscal year |
| Overfit guard in code: 6 words, 20 tokens | Rejected: a rule quoting a question |

Evidence: the naive analyzer's 21 rules were all rejected, and the gate blocked them.
At work: self-improving prompts need a subtracting critic and a leak check.
Key idea: learning is cheap; trusting what was learned is the work.

Speaker notes:

Time: 4 minutes (3:13-3:17)  
Trade-offs, said aloud: three model calls; a paraphrase can pass the guard, so the gate decides.  
Plain explanation: Learning rules from failures works, and it overfits by default. A model that sees a failed question and its gold SQL will happily write a rule that names the question. So the work is split. One agent diagnoses, one proposes, one criticises, and then deterministic code rejects anything that copied the benchmark. Each step can only narrow what the previous one produced.  
Concrete example from DataPilot: The failure analyst reads each failed development question and returns a diagnosis: what went wrong and the likely cause, with no rules. The rule writer turns the diagnoses into general rules, such as the one on the slide, "the fiscal year runs February to January and is named for its end year". The critic keeps, narrows, or drops each rule. In code, a review of a rule the writer never proposed is ignored, so the critic cannot add one. Then the overfit guard rejects any rule that shares 6 consecutive words with a benchmark question or 20 consecutive SQL tokens with a gold query, from `evaluation.overfit_question_words` and `evaluation.overfit_sql_tokens`. The team reads development questions only; handing it a holdout item raises an error. A rule's SQL guidance must also run over the real schema: a check parses it against the catalog, and a placeholder or a column that does not exist goes back to the critic, then is dropped. The naive analyzer (`BUG_NAIVE_ANALYZER`) makes no model call: it writes one rule per failed development question, quoting it word for word, and skips the critic; the guard flags every rule, unapplied.  
Under the hood: The research numbers show both sides. When correcting only the queries already known to be wrong, MAGIC lifted BIRD's development set from 56.52 with no self-correction, to 57.76 with DIN-SQL's human-written guideline, to 59.13 with its learned one, and Spider's development set from 78.62 to 85.66. Applied to every query, with no one saying which are wrong, the human guideline fell to 55.80 and MAGIC's reached 58.55. The survey re-run found the gains small, and negative on one model. Knowledge itself is noisy too: SEED audited the human-written evidence in BIRD's development set and found 105 pairs, 6.84 percent, with wrong evidence and 148 with none.  
Source 18: MAGIC: Generating Self-Correction Guideline for In-Context Text-to-SQL (https://arxiv.org/abs/2406.12692): "to iteratively generate and refine a self-correction guideline tailored to LLM mistakes".  
Transfer: Any loop that rewrites its own prompts, tools, or graders needs this shape: separate roles, a critic that can only subtract, and a deterministic leak check against your eval set. It applies to prompt optimisers and memory systems alike.  
Evidence from this course: in the live session of 24 October the naive analyzer wrote 21 rules quoting development questions; the overfit guard rejected all 21, the holdout stayed at 2 of 15, and the gate blocked the version. The analyzer team took 359 seconds to write two candidates from the same failures, A passing 13 of 25 development questions with 8 rules and B 14 of 25 with 6, and kept one on the development split alone.  
Point at: the why line, the three rows, stop on the critic, then the guard, the only step that is code; then the evidence line.  
Ask: "Why can the critic not add rules?" Expected: then it would be proposing and judging its own work.  
Likely question: "Can a rule paraphrase a question and slip past the guard?" Answer: Yes, the trade-offs line says so. The guard catches copying; the holdout gate catches rules that do not generalise.  
Re-check after live runs: the guard thresholds of 6 words and 20 SQL tokens against `evaluation` in the pack.  
Transition: The guard only removes obvious copying. The real decision is a measurement.

**Slide 64: 3) The gate is a paired comparison**

Container: two-column cards: how it works | worked example, then the key-idea bar

On the slide:

Principle: compare item by item, in one session; a confirmed regression blocks.
Why it matters: an average can rise while a passing answer breaks, unseen.

| How it works in DataPilot | Worked example |
|---|---|
| Holdout items: 3 runs per version, pass on 2 | 15 items, 45 runs per version |
| An apparent regression is re-run | Holdout: 3 more; development: 2 per version |
| Promote: more passes, no regressions, guarded rules, approval | Four conditions, recorded |
| Both experiments in one live session | The baseline started at the poll |

Evidence: promoted, 13 of 15 against 2, no regressions; the over-broad rule, 7 of 15, blocked.
At work: fix the measurement first, run both arms together, block confirmed regressions.
Key idea: an average can hide a broken answer; a paired check names it.

Speaker notes:

Time: 4 minutes (3:17-3:21)  
Trade-offs, said aloud: flaky items still cause false regressions; 15 items miss small gains.  
Plain explanation: The gate does not ask whether the candidate's total is higher. It asks, item by item, whether anything that passed under the active version now fails. That is a paired comparison: the same questions, the same measurement, two versions. An aggregate can hide a trade, six items fixed and one broken. A paired check shows the broken one by name.  
Concrete example from DataPilot: The candidate passes the gate when its holdout passes exceed the active version's, regressions are zero on both splits, every rule it adds passes the overfit guard, and a person approves the knowledge diff. Each holdout item runs 3 times per version and passes on 2 of 3, from `evaluation.holdout_repeats` and `evaluation.holdout_pass_threshold`. An apparent holdout regression counts only if 2 of 3 more candidate runs fail. An apparent regression on a development question counts only if the candidate fails 2 more runs and the active version passes 2 more. The ledger shows the step as "Apparent regression: confirming". Runs go 8 at a time. The gate refuses to compare experiments from different live sessions, which is why the baseline is the one started at the poll. The over-broad version, "exclude discounted orders from revenue", fixes some items, breaks others, and is blocked.  
Under the hood: Take three holdout items that are flaky, passing 7 runs in 10 under both versions. With single runs, at least one shows a false regression with about 51 percent chance. Passing on 2 of 3 lowers that only to about 43 percent. Adding the confirming 3-run re-run brings it to about 11 percent. Calibration ran each holdout item 5 times per version: all stable under the starting version, 3 unstable under the promoted one. Their replacements were unstable on the next pass too, so the instability belonged to the version's answers, and the reviewed holdout was restored. Measured: 2 of 15 holdout passes before, 14 of 15 after under versions 8 and 9, 13 of 15 under version 11, 0 regressions each time. A 70-run experiment took 171.3 to 459 seconds. Fifteen items are still a small sample: 14 of 15 has a 95 percent interval of 0.70 to 0.99.  
Transfer: Use the same gate for any change to a model-backed system: a new prompt, a new model id, a new retriever. Pre-register how you measure, run both arms in one session, compare per item, confirm any regression before you believe it, and block on a confirmed one before you look at the average.  
Evidence from this course: in the live session of 24 October the kept candidate, version 11, passed 13 of 15 holdout items against 2 for the starting version, with 0 regressions on either split, in 212 seconds. Then the optional demo added the over-broad rule, "exclude discounted orders from revenue", to version 11: it passed 7 of 15 against 12 for version 11 measured in that experiment, with 9 regressions (4 development, 5 holdout), and the gate blocked it. Version 11 itself measured 13, then 12 of 15: one item apart, the flakiness the trade-offs line names.  
Point at: the why line, the rows one by one, stop on the confirming-runs row, then the evidence line and the trade-offs line.  
Ask: "Why must both experiments come from one session?" Expected: the model, data, and settings must match, or it measures drift, not the rules.  
Re-check after live runs: the settings against `evaluation` in the pack; 13 of 15 against 2 and the over-broad 7 of 15 against 12 against the live session of 24 October; 2 and 14 of 15, 171.3 to 459 seconds, and 0 items replaced against the calibration report. The 51, 43, and 11 percent figures assume three items flaky at 0.7.  
Transition: A promotion buys more than a better prompt. It buys autonomy.

**Slide 65: 4) Autonomy is earned per metric family**

Container: two-column cards: how it works | holdout questions, then evidence, trade-offs, at-work lines and a key-idea bar

On the slide:

Principle: grant the unattended level per metric family, from that family's holdout evidence.
Why it matters: one switch for everything gives product questions revenue's trust.

| How it works in DataPilot | Holdout questions |
|---|---|
| Every family starts at the report-only level | Revenue 4, orders 4 |
| Clears: every item 2 of 3, or 2 of 3 more | Customers 3, products 3 |
| Demoted: 3 escalations, or the kill switch | Average order value 1 |

Evidence: after the latest promotion, revenue, average order value, and customers cleared; the answer to the fiscal year 2025 revenue question posted correct, without approval.
At work: write the minimum evidence per capability before granting it.
Key idea: autonomy follows evidence, one family at a time.

Speaker notes:

Time: 3.5 minutes (3:21-3:24:30)  
Trade-offs, said aloud: small families rest on few questions; the minimum of 3 is Assignment 4.  
Plain explanation: Autonomy is not one switch for the whole system. A version that answers revenue questions well tells you nothing about product questions. So the unattended level is granted per metric family, only after a gated promotion, and only from that family's holdout results. Everything else stays at the level the event loop set.  
Concrete example from DataPilot: The class starts at the report-only level. At each promotion a family clears on the gate's own confirmed standard: every holdout item of the family passes at least 2 of 3 runs, and an item that falls short gets 3 more runs and counts if it passes 2 of them. Then the fiscal year 2025 revenue question arrives as a webhook and posts at the level its family earned: without approval if revenue cleared, at the assisted level if not. Calibration is why: under the earlier rule, all 4 revenue items had to pass in one experiment, which happened in one measurement of four. Measured four times on the confirmed standard: under version 5 revenue did not clear, one item passing 1 of 3, then 1 of 3 more; under versions 8, 9, and 11 it did. The families come from `autonomy.metric_families` in the pack: revenue, orders, average order value, customers, and products. Revenue, where net revenue lives, has 4 holdout questions; average order value has 1. Three consecutive escalations demote a family again, from `autonomy.demote_after_consecutive_escalations`, and the kill switch drops everything to the report-only level.  
Evidence from this course: in the live session of 24 October, version 11 was the active version 5 seconds after approval; the finale was held while the clearance re-runs ran; then revenue, average order value, and customers had cleared, and the fiscal year 2025 revenue question posted at the unattended level, 64,015,091.21 dollars, matching gold. Orders and products were not among the families cleared, so their answers stay at the assisted level. Note that average order value cleared on its 1 holdout question, the case Assignment 4's minimum rule exists to stop.  
Under the hood: What is distinctive here is the coupling: the unattended level is tied to eval results per family. The small-sample caveat from the last slide applies with force here. One holdout question for average order value is not evidence of anything, and the class code would still let that family through if it were promoted. The calibration report recommends N = 3: a family needs at least three holdout questions before the unattended level, which keeps average order value at the assisted level. That rule is not in class code; Assignment 4: Hill-climbing loop builds it.  
Source 17: Loop engineering (https://cobusgreyling.github.io/loop-engineering/), in summary: three autonomy levels, report-only, assisted, and unattended, and a kill switch that drops the system to report-only.  
Transfer: Grant agent permissions per capability from per-capability evidence. A coding agent can merge documentation fixes unattended long before it may touch billing code. Write down the minimum evidence per capability before you need it.  
Point at: the why line, the three rows, the single average order value question, then the evidence line.  
Ask: "Would you clear average order value on one passing holdout question?" Expected: no; one item is a coin flip, not evidence.  
Re-check after live runs: the holdout counts per family, 4, 4, 3, 3, and 1, against the benchmark files, and N = 3 against the calibration report.  
Say: End the promotion discussion with the open question, and leave it open: "A family clears for the unattended level on its holdout questions: 4 for revenue, 1 for average order value. Is that enough evidence?"  
Measured: revenue cleared on the confirmed standard under versions 8, 9, and 11, the latest promotions, and not under version 5.  
Transition: Assignment 4 turns one answer into a rule. First, the four moves together.

**Slide 66: Cheat sheet: the hill-climbing loop in four moves**

Container: table: move, principle, anti-pattern, check question

On the slide:

| Move | Principle | Anti-pattern it prevents | Check question |
|---|---|---|---|
| Measure | Results on two databases, not text | Text match, lucky passes | Would a correct query written differently pass? |
| Learn | Diagnose, propose, criticise; guard in code | Rules that quote the test | Can whatever writes a rule also approve it? |
| Gate | Paired, per item, one session | Shipping on a higher average | Which questions does your gate never learn from? |
| Trust | Unattended per family, from holdout | One switch for everything | How many held-out questions back each permission? |

Speaker notes:

Time: 0.5 minutes (3:24:30-3:25)  
Say: Four moves. Measure with an instrument you trust. Learn with roles that cannot grade themselves. Gate with a paired comparison on questions the learner never saw. Trust per family, from evidence. The last column is the question to ask of your own system on Monday. You are about to see two of these blocked live: rules that quote the test, and, if time allows, the over-broad rule.  
Point at: the gate row, the one that decides, then its check question.  
Likely question: "Where does human approval sit?" Answer: At the gate, on the knowledge diff, after the measurement says the candidate is ready.  
Likely question: "Which move would you build first at work?" Answer: Measure. Without a trusted instrument the other three are guesses.  
Transition: Now live; the baseline is waiting.

**Slide 67: Section 4: Hill-climbing loop - Implementation Notes: The candidate experiment**

Container: demo layout: laptop and badge, what to watch for, guaranteed moment, link

On the slide:

Badge: DEMO - 4
What to watch for:
- Baseline: the trap items fail on the holdout ledger
- Naive analyzer: every rule flagged, the gate blocked
- Analyzer team: two candidates, one kept on development questions
- Candidate experiment: flips, zero regressions
- Finale: the answer to the fiscal year 2025 revenue question, right, at its earned level
Guaranteed moment: the candidate flips holdout trap items with zero regressions on either split; the gate passes once a person approves.
Link: Demo page on GitHub | https://github.com/ANI-IN/loop-engineering/tree/main/section-4-hill-climbing-loop/demo#the-candidate-experiment

Speaker notes:

Time: 20 minutes (3:25-3:45)  
Run sheet: five core demos in about 15 minutes, then the code walkthrough in about 5. The baseline experiment was started at 2:50, during the poll, so it is read, not started. Keep the Improve page shared full screen. Optional, cut first: the over-broad rule, blocked. Every core demo's moment has been shown live, in calibration retakes and again on 24 October, the optional over-broad rule included; the second chain of a full rehearsal was not run, so rehearse the chain twice in a row with a reset between before class (instructor guide, the day before, step 4). The measured results are under each demo. This chain is the one whose result varies most: say so before it starts. The slide's link opens the section's demo page on GitHub. Experiment runs are traced as a sample, about 1 run in 5, so a ledger row without a traced run reads "Not traced" and is scored all the same; every demo run outside an experiment, the finale included, is traced in full.  
Demo: the baseline experiment.  
Guaranteed moment, from the demo registry: Started at the poll, the experiment runs the 40 benchmark items under version 1 of the knowledge (the starting version); the trap items fail and the holdout ledger fills in locally, each row stamped with its run's start time and linked to its LangSmith trace when the trace sample took one of its runs (about 1 run in 5), otherwise marked "Not traced". This run is the session's baseline.  
Starting state: the experiment started at the poll on the active knowledge version, in the class session. The baseline is safe across a reset: `make reset NAME=hill-climbing-loop` keeps the current session's baseline experiment and prints what it kept with its start time. Only the separate, clearly named full reset discards it, and that is never used in class. Reset first only if it never started: `make reset NAME=hill-climbing-loop`.  
Do: on the run board, open the grouped benchmark progress strip, for example "Baseline benchmark: 41 of 70 runs done", and expand it into the holdout ledger. If it never started: Improve > Run experiment on the active version, or `make demo NAME=improve-baseline-experiment`.  
Narrate: This is the instrument from concept 1, A benchmark is a measuring instrument. Results are scored locally, on two databases. The trap items fail because the starting knowledge version is nearly empty. This run is the class session's baseline; the console accepts no baseline from an earlier session.  
Point at, in order: the progress strip, the holdout ledger rows, the failed trap items with their trap labels, and last the live stamp: the run's start time in your local time and its trace link, or "Not traced" where the sample left the row out.  
Expected live result: a holdout pass count for the starting version with the trap items failed. Measured: 2 of 15 holdout passes, 0 of 13 holdout trap items, in 236 to 386 seconds from the trigger for 70 runs, the longest on a shared machine; that is past the registry's 3-minute target, which is why it runs through the poll and the break. One experiment cost 0.0594 to 0.0914 dollars where recorded. Shown again live on 24 October, 2 of 15 for version 1.  
May vary: which non-trap items pass, and the wall time. If it does, say: the trap items are the ones that must fail, and they are guaranteed by the planted traps; the others vary run to run, which is why holdout items run three times and calibration removes unstable ones.  
If it stalls: reset and run it again, `make reset NAME=hill-climbing-loop`, then the same trigger. Read the reset output aloud: it names the baseline it kept and its start time.  
Demo: the naive analyzer, blocked.  
Guaranteed moment, from the demo registry: Two requests, queued together at the break with `make demo NAME=improve-naive-analyzer-blocked PLANTED=1`: the analyzer, then the candidate experiment; the runner takes them in that order, after the baseline. Its planted half is its only half, so the command switches the naive analyzer on for its own two requests with or without PLANTED=1. The console's Improve page queues the same two requests with the same flag from its Run the naive analyzer (planted) button, shown only while demo controls are allowed; its Run analyzer button runs the analyzer team, never the naive analyzer. The naive analyzer, with no model call, writes one rule per failed development question, quoting it word for word with the analyst's query that failed, and never reads a reference query. It skips the critic and applies no overfit guard: the guard flags every rule and the Improve page says so, yet the knowledge diff keeps them all. Then the candidate experiment runs, and the gate blocks the version because the overfit guard rejects its rules, whatever its holdout count.  
Starting state: it ran at the break and its verdict is on the Improve page. At the start of the break it was queued behind the baseline, with the naive analyzer (`BUG_NAIVE_ANALYZER`) on for its own two requests only, so nothing is switched back.  
Do: at the break, `make demo NAME=improve-naive-analyzer-blocked PLANTED=1`, or Improve > Run the naive analyzer (planted), shown while demo controls are allowed; either queues the analyzer and then its candidate experiment, and the runner takes them in that order. The command plants the naive analyzer with or without PLANTED=1; the Run analyzer button runs the analyzer team. Here, read the result. Each attempt is the analyzer and a 70-run candidate experiment: 211 to 580 seconds from the trigger to the verdict in six measured runs, the longest on a shared machine, which is why it runs at the break. It waits behind the baseline, so if the verdict is not on the Improve page at 3:05, start the concepts and read it at 3:25.  
Narrate: This is concept 2, Rules learned from failures overfit, without its defences. The naive analyzer makes no model call: it writes one rule per failed development question, quoting the question word for word with the query that failed, and skips the critic. The overfit guard flags every rule, but its verdict is not applied, so the knowledge diff keeps them all.  
Point at, in order: a rule that quotes a benchmark question; the guard's flag on every rule; after the candidate experiment, the gate verdict blocked, naming the rules the overfit guard rejects; and last the live stamp.  
Expected live result: the overfit guard flags every rule, and the gate verdict reads blocked, naming those rules, whatever the holdout count.  
May vary: how many development questions failed, how many pass, and how many holdout items pass. If the holdout count rises, say: a higher score does not license rules that copy the test, and the gate's fourth condition blocks them anyway. Measured six times as it is now: 21, 21, 20, 21, 21, and 21 rules, all flagged by the guard, holdout 2 of 15 in five runs and 0 of 15 in the sixth, and the gate blocked each time, in 211 to 580 seconds from the trigger to the verdict, the longest on a shared machine. Once before it was made deterministic, it read the reference queries, its 21 rules passed 15 of 15 holdout items, and the gate of three conditions let it through. That run is why the fourth exists.  
If it stalls: reset and run it again, `make reset NAME=hill-climbing-loop`, then the same trigger.  
Demo: the analyzer team and approval.  
Guaranteed moment, from the demo registry: The failure analyst diagnoses the failed development questions, the rule writer proposes general rules, the critic keeps, narrows, or drops each one, a rule whose SQL guidance does not run over the schema is dropped, and the overfit guard rejects any rule that quotes a benchmark question or copies gold SQL and passes the rest. The team writes two candidates this way, each runs on the development split only, and the Improve page names the one kept by its results there; the knowledge diff shows it for human approval.  
Starting state: the naive analyzer's candidate is discarded. Reset first: `make reset NAME=hill-climbing-loop`; the baseline stays.  
Do: Improve > Run analyzer, or `make demo NAME=improve-analyzer-team-approve`, then at once Improve > Run experiment on the candidate: the runner starts it as soon as the team's candidate is written. The team took 326 to 377 seconds in the five measured runs with two candidates.  
Narrate: Concept 2 with its defences. The failure analyst diagnoses, the rule writer proposes, the critic keeps, narrows, or drops, a rule whose SQL guidance does not run over the schema is dropped, and the overfit guard rejects any rule that quotes a question or copies gold SQL and passes the rest; live, it once rejected a rule the critic kept for copying 20 or more tokens of a gold query. The team writes two candidates this way; each runs on the development split only, and the one kept has fewer regressions, then more passes, on the development questions, then fewer rules. The holdout never takes part in the choice.  
Point at, in order: one diagnosis with no rule in it, one proposed rule, the critic's decision and reason, the guard result, the line naming both candidates and the one kept, the knowledge diff waiting for human approval, and last the live stamp.  
Expected live result: a candidate version with general rules in the diff viewer, not yet approved, and the line naming both candidates and the one kept. Measured with two candidates five times, in 326 to 377 seconds; the first three: 326 seconds, candidate A 18 of 25 development questions with 11 rules, candidate B 19 of 25 with 8 rules, B kept; 377 seconds, A 21 of 25 with 8 rules, B 10 of 25 with 5, A kept; the SQL guidance check rejected none of the kept rules either time; and on 24 October, 359 seconds, A 13 of 25 with 8 rules, B 14 of 25 with 6, the kept candidate becoming version 11. With one candidate it took 62 and 98 seconds, and 7 and 8 rules passed the overfit guard.  
May vary: the rule wording, the number of rules, and which candidate is kept. If it does, say: a different wording is fine; what matters is that no rule names a benchmark question.  
If it stalls: reset and run it again, `make reset NAME=hill-climbing-loop`, then the same trigger.  
Demo: the candidate experiment.  
Guaranteed moment, from the demo registry: The candidate version flips holdout trap items with zero regressions on either split. The live holdout ledger in the console, scored locally against this session's baseline, marks the flips; then the LangSmith trace list of datapilot-experiments, filtered by knowledge version, shows the candidate's traced runs, a sample of about 1 run in 5. The gate reads ready for human approval; once approved, the runner makes the version active and runs the clearance re-runs (50 seconds after the approval, measured once). In class it is queued at once after the analyzer (Improve > Run analyzer, then Improve > Run experiment on the candidate); trigger it again only if it never started, since a second press queues a second experiment.  
Starting state: the candidate version from the analyzer team, in the same session as the baseline. Reset first: `make reset NAME=hill-climbing-loop` only if the candidate is missing; the baseline stays.  
Do: nothing to start: it was queued at once after the analyzer. Only if it never started, Improve > Run experiment on the candidate, or `make demo NAME=improve-candidate-experiment`; a second press queues a second 70-run experiment. When the gate reads ready for human approval, click Approve on the knowledge diff.  
Narrate: Concept 3, The gate is a paired comparison. Same items, same measurement, same session. Holdout items run three times and pass on two; an apparent holdout regression is confirmed by three more runs, and an apparent regression on the development questions by two more runs of each version, before it counts.  
Point at, in order: the live holdout ledger with the flips marked against this session's baseline, the regression column at zero on both splits, the gate reasons, the verdict after approval, then the LangSmith trace list of `datapilot-experiments` filtered by knowledge version to show the candidate's traced runs, a sample of about 1 run in 5, tagged by split, item, and repetition, and last the live stamp.  
If LangSmith refuses traces, skip the trace list and point at the holdout ledger, which is scored locally either way.  
Expected live result: holdout flips marked against this session's baseline, no regressions, and the gate verdict passed once approved. Measured: the three latest candidates, each kept from two: versions 8 and 9 each scored 14 of 15 against 2, fixing 12 of 13 holdout trap items with 0 regressions, in 211 and 186 seconds from the trigger; version 11, on 24 October, 13 of 15 against 2 with 0 regressions, in 212 seconds, and it was the active version 5 seconds after approval. The version promoted on 22 October scored 12 of 15. A 70-run experiment took 171.3 to 459 seconds; two, at reasoning effort high, ran past the 5-minute budget. The same input also gave candidates of 3, 6, and 11 of 15, and at reasoning effort high 2, 9, and 5 of 15, so higher effort did not narrow the spread; the best of those three passed 10 of 15 against 2 with 0 regressions when it was measured again for the finale. That spread is why the team writes two candidates and keeps the better one on the development questions. A weak candidate is still possible. If the gate blocks it for too few holdout passes, say: the gate is refusing a version that did not earn it, which is the point.  
May vary: which items flip and the wall time. If the ledger shows "Apparent regression: confirming", say: this is concept 3 at work; wait for the re-runs. If the regression is confirmed, say: the gate is doing its job; read the item, and the version stays blocked.  
If it stalls: reset and run it again, `make reset NAME=hill-climbing-loop`, then the same trigger.  
Demo: cleared for the unattended level.  
Guaranteed moment, from the demo registry: The correct answer, posted at the level its family has earned. Before it, the Improve page says the approved version is the active version, and the system is set to the unattended level (Improve > Set the unattended level, or `make autonomy LEVEL=unattended BY="<your name>"`); the trigger refuses, saying which step is missing, while a promotion is pending, the kill switch is engaged, or the level is lower. The fiscal year 2025 revenue question arrives as a webhook and is answered correctly under the new active version; it posts at the unattended level when the promotion cleared its metric family on the gate's own confirmed standard (every holdout item at 2 of 3 runs, an item that fell short passing 2 of 3 more runs), and at the assisted level when the family fell short. From the promotion on, Events > Send webhook question sends this question whether a family cleared or none did. Its strip on the Events page then shows the gold check the runner writes after the post: "Gold check passed", or "Gold check failed" with the agent's value and the gold value, the class-day safeguard's trigger.  
Starting state: the candidate is promoted and active: after approval, as soon as the Improve page says the version is the active version, set the unattended level, Improve > Set the unattended level, or `make autonomy LEVEL=unattended BY="<your name>"` (every reset sets the report-only level). Then wait until the note above the Events buttons goes away, when the clearance re-runs finish (50 seconds, measured once; on 24 October the finale was held while they ran, as designed). The status line then names the families cleared, or reads Not cleared for every family when none cleared, and the finale posts at the assisted level. Send webhook question sends the fiscal year 2025 revenue question from the promotion on. The kill switch is released. No reset.  
Do: Events > Send webhook question, or `make demo NAME=improve-cleared-unattended`. Both refuse, saying which step is missing, while the promotion is pending or its re-runs still run, the kill switch is engaged, or the level is lower.  
Narrate: Concept 4, Autonomy is earned per metric family. The fiscal year 2025 revenue question, net revenue in fiscal year 2025, arrives as a webhook under the promoted version. The moment is the correct answer, posted at the level its family has earned: without approval when revenue cleared on the gate's confirmed standard, every revenue holdout item at 2 of 3 runs or 2 of 3 more, and at the assisted level when it fell short.  
Point at, in order: the correct answer against gold, 64,015,091.21 dollars, on the finale's strip, which shows the gold check once the runner writes it; the post and its level; the status line naming the families cleared, with any clearance re-runs beside their items in the candidate experiment; and last the live stamp.  
Expected live result: a correct answer, posted at the unattended level if revenue cleared and at the assisted level if it did not.  
May vary: the wording, the latency, and the level; the answer is correct either way. If it posts at the assisted level, say: the gate held back autonomy the evidence did not earn. Measured four times on the confirmed standard. First, under version 5, revenue did not clear, and the answer was wrong, 63,986,616.77 dollars against gold 64,015,091.21: its internal-account filter was too broad and also removed the look-alike addresses, because no rule stated the email-domain predicate. The analyzer now drops a rule whose SQL guidance does not run over the schema. Then, under versions 8, 9, and 11, revenue cleared and the answer, 64,015,091.21 dollars, matching gold, posted at the unattended level; under version 11, on 24 October, revenue, average order value, and customers were the families cleared.  
If the answer is wrong in class: use the class-day safeguard, live, from the instructor guide: `make safeguard-activate BY="<your name>"`, which makes the version verified in rehearsal active and records it, then send the finale again. Say: the gate's record of the class candidate stays as it is, and nothing is hidden. The safeguard was rehearsed live on 24 October after a reset, and its finale was correct again.  
If it stalls: reset and run it again, `make reset NAME=hill-climbing-loop`, then the same trigger.  
Say: Then ask the open question and leave it open: "A family clears for the unattended level on its holdout questions: 4 for revenue, 1 for average order value. Is that enough evidence?"  
Optional, cut first, and only after a candidate has been promoted: the over-broad rule, blocked: Improve > Add the over-broad rule to the active version, or `make demo NAME=improve-overbroad-rule-blocked`. The rule "exclude discounted orders from revenue" breaks revenue items that pass under the active version, and the gate blocks it for regressions. Measured once, on 24 October on version 11: 7 of 15 holdout items against 12, with 4 regressions on development questions and 5 on holdout items, blocked, 862 seconds from the trigger to the verdict with the confirming re-runs: it does not fit the block, so run it only if 15 minutes remain. It needs an experiment of the active version in this live session: the gate compares with one. In class order the candidate experiment is that experiment. After a safeguard activation there is none, and the first attempt on 24 October failed after 311 seconds with NoLiveBaseline, no experiment of version 11 in this live session; run the baseline experiment on the active version first.  
Code walkthrough: about 5 minutes, in the order of the section's demo walkthrough page.  
Open `platform/src/datapilot/loop4_hill_climbing/experiment.py`, lines 192-194: implements concept 1, A benchmark is a measuring instrument, behind both experiments. Say: each item's runs go one after another; `scheme.repeats` gives a holdout item 3 runs and a development question one, from the pack; a holdout item passes on 2 of its 3, and the same scheme applies to both versions.  
Open `platform/src/datapilot/loop4_hill_climbing/analyzer.py`, lines 206-210: implements concept 2, Rules learned from failures overfit, the naive analyzer demo. Say: a holdout item in the input stops the analyzer team, so the holdout stays unseen in code, not by convention; with `BUG_NAIVE_ANALYZER` on, `naive_rules` makes no model call and writes one rule per failed development question, and the guard's verdict is not applied.  
Open the same file, lines 242-245: the analyzer team demo. Say: the critic can only keep, narrow, or drop a proposed rule; a rule whose SQL guidance does not parse against the catalog is dropped, such as a placeholder or a column that does not exist; the overfit guard is deterministic and runs last, 6 question words or 20 SQL tokens. Two candidates are written this way, and `choose` in `candidates.py` keeps one on the development split.  
Open `platform/src/datapilot/loop4_hill_climbing/gate.py`, lines 117-135: implements concept 3, The gate is a paired comparison. Say: both experiments must come from the same live session; four conditions, all recorded: more holdout passes, zero confirmed regressions on either split, a person's approval, and every new rule passing the overfit guard; the over-broad rule fails `clean`, the naive analyzer's version fails `overfit_flags` whatever its holdout count.  
Open `platform/src/datapilot/loop4_hill_climbing/eligibility.py`, lines 72-80: the gate behind concept 4, the finale. Say: a family clears on the confirmed standard; an item that fell short is re-run 3 more times and must pass 2, and a family stops at its first item that falls short twice.  
Transition: Questions, starting from the open question.

**Slide 68: Questions**

Container: fixed question slide

On the slide:

No Question Is Too Small Every Question Deserves an Answer!!
Are four holdout questions enough? What would your gate require?

Speaker notes:

Time: 3 minutes (3:45-3:48)  
Say: Start from the open question: "A family clears for the unattended level on its holdout questions: 4 for revenue, 1 for average order value. Is that enough evidence?" Take two or three answers. Then point to Assignment 4: Hill-climbing loop, which builds the rule that a metric family needs at least three holdout questions before the unattended level, and adds a repeat-customer family with its own questions. The calibration report recommends that minimum, N = 3.  
Point at: the fixed question slide.  
Likely question: "What if the gate blocks a good version by noise?" Answer: It can. Holdout items run three times and pass on two, every apparent regression is confirmed by more runs, three on the holdout and two of each version on the development questions, and calibration checks every item for stability; for three items flaky at 0.7 that leaves about an 11 percent false-regression chance. Beyond that, a larger holdout or a statistical test is the fix.  
Likely question: "Could the analyzer team learn from production traces instead?" Answer: Yes, that is LangChain's version of this loop. The gate stays the same: whatever it learns from, it is promoted only on questions it never saw.  
Likely question: "How often would you re-run the gate?" Answer: On every candidate, and again for the active version whenever the model or the data changes.  
Transition: If time is short, skip the reference slides and go to the wrap-up.

**Slide 69: Reference: skip if short on time - gate statistics**

Container: two tables side by side: intervals | false-regression schemes, read-me line

On the slide:

| Holdout passes | 95 percent interval |
|---|---|
| 10 of 15 | 0.42 to 0.85 |
| 13 of 15 | 0.62 to 0.96 |


| Scheme, three items flaky at 0.7 | False-regression chance |
|---|---|
| Single run | About 51 percent |
| Pass on 2 of 3 | About 43 percent |
| 2 of 3, then a confirming 3-run re-run | About 11 percent |
| Plus the stability filter | Run in calibration; 0 items replaced |

Production gate: hundreds of items, or McNemar's paired test.
How to read this: overlapping intervals mean 15 items cannot rank close versions; the second table shows why regressions are confirmed and unstable items removed.

Speaker notes:

Time: 1 minute (3:48-3:49)  
Plain explanation: This slide is the honest arithmetic behind the gate. A holdout of 15 items can tell a large improvement from none, but not a small one, and flaky items create false regressions far more often than intuition suggests. Three defences stack: majority voting, a confirming re-run, and removing unstable items before class.  
Concrete example from DataPilot: The holdout has 15 items. If the active version passes 10 and the candidate 13, the two intervals overlap; the gate still promotes, because its rule is paired and per item, not a claim that the candidate is better in general. When an item that passed now fails, the ledger shows "Apparent regression: confirming" before it decides: 3 more runs on the holdout, 2 more of each version on the development questions. The latest promoted version, 11, measured 13 of 15 in its candidate experiment and 12 of 15 in the over-broad rule's experiment the same day: one version, one item apart.  
Analogy: Two coins that each landed heads 10 and 13 times out of 15 are not proven to be different coins.  
Under the hood: The intervals are 95 percent Wilson intervals: 0.42 to 0.85 for 10 of 15, and 0.62 to 0.96 for 13 of 15. For flaky items, assume a 0.7 per-run pass rate under both versions. On single runs, at least one of three such items shows a false regression with about 51 percent chance. Pass on 2 of 3 barely helps, about 43 percent, because a flaky item still flips between versions. Requiring a confirming 3-run re-run, where 2 of 3 must fail again, brings it to about 11 percent. The stability filter attacks the cause: in calibration each holdout item runs 5 times under the starting and the promoted version and is kept only at 4 or 5 of 5, or 0 or 1 of 5, under each. In calibration every item was stable under the starting version and 3 were unstable under the promoted one; their same-family replacements were unstable on the next pass too, so the instability followed the version's answers, not the items, and the reviewed holdout of 15 was restored. A production gate uses hundreds of items or McNemar's paired test, which counts only the items that changed.  
Source 8: Semantic Evaluation for Text-to-SQL with Distilled Test Suites (https://arxiv.org/abs/2010.02840): "the current Spider metric leads to a 2.5% false negative rate on average"; measurement error exists before any model noise.  
Transfer: Before trusting any small eval, compute its interval and its false-alarm rate for your flake rate. Then confirm alarms before acting on them, and remove the flaky cases.  
Point at: the second table, row by row from 51 down to 11 percent, then the filter row.  
Ask: "What does McNemar's test look at?" Expected: only the discordant items, the ones that passed in one arm and failed in the other.  
Likely question: "Why not raise the threshold to 3 of 3?" Answer: Then a flaky item almost never passes under either version, and the holdout shrinks in effect.  
Likely question: "Where do the percentages come from?" Answer: all three are computed for the course, the same arithmetic for single runs and for the two stricter schemes.  
Misconception: "More repeats fix small samples." Correction: Repeats and confirming runs reduce per-item noise; only more items narrow the interval.  
Re-check after live runs: the holdout size and the repeat settings against the benchmark and the pack; 0 items replaced against the calibration report. The 43 and 11 percent figures are calculations on the stated assumptions.  
Transition: Next, what others have built.

**Slide 70: Reference: skip if short on time - prior art compared**

Container: table: system, how it improves, gate and approval, read-me line

On the slide:

| System | How it improves | Gate and approval |
|---|---|---|
| Databricks Genie | Benchmarks suggest instruction fixes | A person reviews; no gate described |
| Snowflake Cortex Analyst | Up to 10 verified-query suggestions at a time | A person accepts each |
| Vanna 2.0 | Saves successful interactions to memory | Automatic, no gate |
| LangChain's loop | Analysis agent on production traces | Not described in the post |
| DataPilot | Analyzer team on development failures | Holdout, zero regressions, guarded rules, human approval |

How to read this: the last column is what decides whether learned knowledge reaches production; each piece exists elsewhere, the combination is the difference.

Speaker notes:

Time: 0.5 minutes (3:49-3:49:30)  
Plain explanation: Every piece of this loop exists somewhere. What we have not seen documented is the combination: a held-out split, zero per-item regressions, human approval of a versioned knowledge artefact, a deterministic overfit guard, and autonomy granted per metric family from holdout results. Say it as a combination we have not seen documented, never as an invention.  
Concrete example from DataPilot: The knowledge diff the gate shows is a versioned file of rules. Promotion changes which version is active, so rollback is choosing the previous one.  
Analogy: Feature flags plus a canary plus code review: each common, the combination is the discipline.  
Under the hood: Genie benchmarks in chat mode, the default, score answers against expected SQL results, comparing numbers to 4 significant digits; agent mode uses an LLM judge instead. Both suggest instruction fixes a human reviews. Source 21: Test and monitor a Genie Agent (https://docs.databricks.com/aws/en/genie-agents/monitor), in summary: benchmarks score Genie's answers and suggest fixes for a person to review. Cortex Analyst proposes up to 10 verified-query candidates at a time for a person to accept. Vanna 2.0 saves successful interactions to tool memory automatically, which learns fastest and checks least. LangChain's post defines the same four loops; its hill-climbing loop reviews production traces and updates prompts, tools, or graders.  
Source 22: Suggestions for semantic models and views (https://docs.snowflake.com/en/user-guide/views-semantic/verified-query-suggestions), in summary: the system suggests verified queries and a person accepts them.  
Source 23: Vanna documentation (https://vanna.ai/docs/), in summary: successful interactions are saved to memory and reused.  
Transfer: When you evaluate a vendor's self-improving feature, ask three questions: what does it learn from, what does it measure on that it did not learn from, and who approves.  
Point at: the gate column, top to bottom, then the read-me line.  
Ask: "Which row learns fastest, and what does that cost?" Expected: Vanna; it trusts every success, including lucky ones.  
Likely question: "Should production traces replace the benchmark?" Answer: They are a better source of failures; they are a worse referee, because no gold answer exists for most.  
Likely question: "Is human approval a bottleneck?" Answer: It is one review per version, not per answer.  
Misconception: "Human acceptance is the gate." Correction: A person can accept a rule that breaks other questions; measurement shows what a reviewer cannot see.  
Transition: Last, the ways learned knowledge goes wrong.

**Slide 71: Reference: skip if short on time - when learned knowledge fails**

Container: table: failure mode, evidence, guard, read-me line

On the slide:

| Failure mode | Evidence | Guard |
|---|---|---|
| Wrong human evidence | An audit of the BIRD benchmark (SEED): 105 pairs | Holdout gate |
| Missing evidence | The same audit: 148 pairs | Analyzer on failures |
| Rules that do not transfer | A learned-guideline method (MAGIC), re-run: a drop | Holdout gate |
| Rules quoting test questions | The naive analyzer | Overfit guard, a gate condition |
| Over-broad rule | Exclude discounted orders | Zero regressions |

How to read this: each row is one way knowledge goes wrong; the guard column names the step in this loop that catches it.

Speaker notes:

Time: 0.5 minutes (3:49:30-3:50)  
Plain explanation: Knowledge fails in five recognisable ways, and each has a guard. Two are about the knowledge being wrong or absent, two about learning that does not generalise, and one about a rule that is right somewhere and wrong elsewhere.  
Concrete example from DataPilot: The pre-authored over-broad version adds "exclude discounted orders from revenue". It sounds like a fix for net revenue. It fixes some items and breaks others that passed before, and the zero-regression rule blocks it.  
Analogy: A style guide entry written after one bad review that then forbids a pattern the whole codebase uses correctly.  
Under the hood: SEED audited the human-written evidence in BIRD's development set: 148 pairs, 9.65 percent, had none, and 105, 6.84 percent, had wrong evidence. Fixing the wrong evidence raised CodeS-15B from 44.76 to 54.29 on those pairs, so bad knowledge costs real accuracy. The MAGIC re-run showed small gains and a drop on one model, so learned rules need a holdout. The overfit guard rejects 6 consecutive question words or 20 consecutive gold SQL tokens.  
Source 20: SEED (https://arxiv.org/abs/2506.07423): "human-generated evidence in BIRD contains defects, including missing or erroneous evidence, which affects model performance."  
Transfer: Treat every knowledge source for an agent, wiki pages, memory, retrieved notes, as data that can be wrong. Version it, measure it, and gate changes to it like code.  
Point at: the over-broad row, the one the optional demo shows, then the guard column.  
Ask: "Which guard catches a rule that is right for revenue and wrong for orders?" Expected: zero regressions on both splits.  
Likely question: "Should human-written rules skip the gate?" Answer: No; SEED shows humans write wrong evidence too.  
Likely question: "Can the guard reject a good rule?" Answer: Rarely; a general rule seldom repeats six words of one question.  
Misconception: "More knowledge is always better." Correction: Wrong knowledge lowers accuracy; gated knowledge is better.  
Transition: That closes Section 4: Hill-climbing loop; on to the wrap-up.

## Closing

| # | Slide | Layout | Time (start-end) | Says in one line | Source in the repository |
|---|---|---|---|---|---|
| 72 | Final run: one question through four loops | diagram | 3:50-3:51:30 | Wrong alone, green but wrong, safe and stoppable, then right and cleared | final-project/README.md |
| 73 | All results: one picture | table | 3:51:30-3:53 | One row per section: what the loop changed, as counts from the paired live runs of 24 October | docs/benefits.md; docs/calibration-report.md |
| 74 | Which loop when: match the failure | table | 3:53-3:54:30 | Match the failure you see to the loop that fixes it | docs/architecture.md |
| 75 | Use it at work: four questions to ask | concept | 3:54:30-3:55:30 | Questions to ask of any agent system you run | use-in-your-repo/README.md |
| 76 | Assignments, final project, and the Thursday review | concept | 3:55:30-3:57 | Four assignments, each with a live check; solutions published when the Thursday review starts | docs/review-session.md |
| 77 | Summary: key takeaways | concept | 3:57-3:58 | Agents only where judgement is needed; code and people decide; autonomy is earned | README.md |
| 78 | References | table | 3:58-3:59 | Every source, numbered by section | slides/source/sources.py, the source register |
| 79 | Questions and close | concept | 3:59-4:00 | No Question Is Too Small Every Question Deserves an Answer!! | - |

### Slides and speaker notes: Closing

**Slide 72: Final run: one question through four loops**

Container: step cards: the fiscal year 2025 revenue question's four stages

On the slide:

"What was our net revenue in fiscal year 2025?"
1. Agent loop: confident and wrong; several of the five traps in one query
2. Verification loop: every grader green, gold still fails on both databases
3. Event loop: the same agent runs on events, with keys, durable approval, and a stop; the finale arrives this way
4. Hill-climbing loop: right under a gated version, posted at the level its family earned
Lesson: each loop fixed a different failure, and none needed a bigger model

Speaker notes:

Time: 1.5 minutes (3:50-3:51:30)  
Say: Retell the fiscal year 2025 revenue question's path. In Section 1: Agent loop it was confident and wrong. In Section 2: Verification loop every check turned green and it was still wrong; on 24 October its SQL carried 3 trap labels. In Section 3: Event loop the same agent ran on events, with keys, durable approval, and a stop that reaches running work; the fiscal year 2025 revenue question itself returns in Section 4, as a webhook. In Section 4: Hill-climbing loop it became right, through rules that passed a gate on questions the analyzer never saw, and it posted at the level its metric family earned: the unattended level if revenue cleared on the confirmed standard. If revenue did not clear in the class run, say so: the answer was right and posted at the assisted level, because the gate did not see enough evidence. In the live session of 24 October revenue cleared under the promoted version, version 11, and the answer to the fiscal year 2025 revenue question, 64,015,091.21 dollars, matching gold, posted at the unattended level, as it had under versions 8 and 9; under version 5 revenue did not clear and the answer was wrong.  
Point at: the four stages in order.  
Likely question: "Can I run the whole path myself?" Answer: yes; the final project runs it end to end on your machine.  
Transition: All the results on one slide.

**Slide 73: All results: one picture**

Container: table: loop | without it | with it

On the slide:

| Loop | Without it | With it |
|---|---|---|
| Agent loop, 21 runs | 12 of 21 correct | 17 of 21 correct |
| Verification loop, 40 runs | 0 of 40 correct; 1 escalated | 0 of 40 correct; 20 held or escalated |
| Event loop, one run per half | 3 answers for one event | 1 answer, 2 duplicates absorbed |
| Hill-climbing loop, 15 items | Holdout 2 of 15 | 13 of 15, no regressions |

How to read this: samples differ per row; read the rows as what happened, not as rates.

Speaker notes:

Time: 1.5 minutes (3:51:30-3:53)  
Say: Read one row per section as counts, not percentages. Each row is the same questions or demo with the loop's protection switched off, then on, in one rehearsal session of 24 October. Agent loop: seven questions without traps, 3 runs each, 12 of 21 correct with names-only tools, no row cap, and no scout, 17 of 21 with them; the unbounded rows demo took 182,654 tokens without the cap against 30,216 with it. Verification loop: 20 trap questions, twice each, 0 of 40 correct either way; without the layer 1 wrong answer was escalated, with it 20 were held or escalated; the retry cap stopped at 3 attempts, and no malicious statement changed a warehouse row in either half. Event loop: one event sent three times posted 3 answers without the key, 1 with it. Hill-climbing loop: the starting version passed 2 of 15 holdout items; the version promoted on 24 October, version 11, passed 13 of 15 with 0 regressions, and the finale posted the correct answer to the fiscal year 2025 revenue question at the unattended level.  
Say plainly where a loop did not help: the verification layer made no trap answer correct; it held or escalated 20 of 40 wrong answers against 1, and the reviewer, which shares the analyst's knowledge, approved the other 19; the event loop prevents duplicates and lost approvals, not wrong numbers; and the analyzer's quality varies from run to run, candidates of 2 to 11 of 15 from the same input, which is why it writes two and keeps the better one on the development questions.  
Re-check after live runs: every count on the slide against the paired measurements page of 24 October.  
Point at: the hill-climbing row.  
Likely question: "Where are the runs behind these counts?" Answer: on the page of paired measurements in the course repository, with each run's id.  
Transition: Which loop to reach for, and when.

**Slide 74: Which loop when: match the failure**

Container: table: you see | reach for | first check

On the slide:

| You see | Reach for | First check |
|---|---|---|
| Wrong because the agent cannot see enough | Agent loop | What does each tool return? |
| Unsafe, unbounded, or endless work | Verification loop | Which stop is not the model's? |
| Duplicates, unwatched risk, a stop that misses | Event loop | Is every effect keyed? |
| The same kind of error, again and again | Hill-climbing loop | Which questions never train it? |

Speaker notes:

Time: 1.5 minutes (3:53-3:54:30)  
Say: Use this as a decision table at work. Find the failure you see in the left column. If the agent cannot see enough, fix the tools first. If work is unsafe or never ends, add layers and caps. If effects repeat or nobody can stop them, add keys, durable approval, and a stop that reaches running work. If the same kind of mistake keeps returning, learn rules from failures, but only behind a gate on held-out questions.  
Point at: the right column, in order.  
Likely question: "Which one first?" Answer: the one matching your most expensive failure this quarter.  
Transition: Taking it to your own systems.

**Slide 75: Use it at work: four questions to ask**

Container: four cards: one question per loop, each with why

On the slide:

**What can the agent see, and what is capped?** Tool output decides what it can know.
**Which stop is not the model's choice?** A loop the model can extend has no end.
**What makes a repeated event harmless?** Delivery is at least once.
**Which questions does your gate never learn from?** Only unseen questions measure learning.

Speaker notes:

Time: 1 minute (3:54:30-3:55:30)  
Say: Take these four questions to any agent system you run, SQL or not. Each one maps to a loop. The course repository also has a template domain pack, so you can point the same loops at your own database, write gold queries for your own questions, and start from an empty knowledge version. One pack setting selects the pack every component reads; each pack keeps its own knowledge versions, and preflight reads its data check and canary from it.  
Point at: the four questions.  
Likely question: "Does it work beyond Postgres?" Answer: the class runs on Postgres; the principles do not depend on it, and the final project covers your own Postgres.  
Transition: Practice comes next.

**Slide 76: Assignments, final project, and the Thursday review**

Container: four cards, one per assignment

On the slide:

Assignment 1: Agent loop: a value lookup for informal names, recorded in assumptions
Assignment 2: Verification loop: clarify or abstain, and a personal-data leak grader
Assignment 3: Event loop: a nightly revenue anomaly alert, keyed and stoppable
Assignment 4: Hill-climbing loop: a repeat-customer family and a minimum-holdout rule
Each has a live check with your own OpenAI key. Deadline: announced in the class chat; solutions published when the Thursday review starts.
Final project: the four loops on your own dataset, with a benchmark you write

Speaker notes:

Time: 1.5 minutes (3:55:30-3:57)  
Say: Each assignment adds a capability class code does not have. Each assignment has a live check, `make check-assignment NAME=<slug>`. It runs the done-when scenario on the real stack with your own OpenAI key, reports pass or fail per requirement with a trace link and a live stamp, and prints its cost estimate first and the actual cost at the end. There are no stubs or canned model answers in any check: every check is live. Solutions are published when the Thursday review starts. Announce the deadline in the class chat before class ends. The final project applies the four loops to your own dataset, on a domain no section used, with a benchmark you write and its own checklist.  
Point at: Assignment 4, which turns the open question about small holdouts into a rule.  
Likely question: "What does the check cost me?" Answer: it prints its estimate before it starts and the actual cost when it ends, on your own key. Measured in the build's verification: typically about 0.4 cents for a full check of Assignment 1, about 2 cents for Assignment 2, and about 0.5 cents for Assignment 3, an estimate (its drill-down now runs two or three times; no check has run on that rule yet); and for Assignment 4, which runs the benchmark, about 13 to 24 cents for each later check of a live session (12.62 to 23.95 cents, seven checks: five audited clean, and two, of 23 October at 13.58 and 23.95 cents, not confirmed clean). The first check of a live session, which also runs the baseline, is an estimate, about 24 cents: no clean first check has been measured. These are measured costs, not bounds; the costs page lists every measured check. Every check stops at its own spend cap of 1 dollar.  
Transition: The class in three lines.

**Slide 77: Summary: key takeaways**

Container: three cards: takeaway | why

On the slide:

Tools and caps decide what the agent can know: no model sees what a tool withholds
Deterministic checks and gates decide; agents advise: code cannot be talked out of a rule
Autonomy is earned per metric family, from held-out evidence: a stop that reaches running work takes it back
One rule under all three: never let an agent grade its own work

Speaker notes:

Time: 1 minute (3:57-3:58)  
Say: Three lines. What the agent can know is decided by its tools and their caps. Deterministic checks and gates decide; agents advise them. Autonomy is earned per metric family, from evidence the learner never saw, and taken back by a stop that reaches running work.  
Point at: the three lines.  
Likely question: "What is the one rule?" Answer: never let an agent grade its own work.  
Transition: Where every claim came from.

**Slide 78: References**

Container: table: sources by topic

On the slide:

| Sources | Topic |
|---|---|
| 1 | The four loops |
| 2 to 7 | Agent loop: evidence, enterprise schemas, schema linking, structured output |
| 8 to 12 | Verification loop: false positives, permissions, error codes, stops |
| 13 to 17 | Event loop: queues, durable approval, autonomy levels |
| 18 to 23 | Hill-climbing loop: learned rules, evidence quality, prior art |

How to read this: numbered by section, Source 1 first; full titles and links are in this slide's notes.

Speaker notes:

Time: 1 minute (3:58-3:59)  
Say: The sources are numbered by section: Source 1 for the four loops, then each section's sources in a range of its own. The full list, with titles, authors, and links, is below and closes each section page.  
Source 1: The art of loop engineering, https://www.langchain.com/blog/the-art-of-loop-engineering, Sydney Runkle (LangChain), 2026-06-16  
Source 2: Can LLM Already Serve as A Database Interface? A BIg Bench for Large-Scale Database Grounded Text-to-SQLs, https://arxiv.org/abs/2305.03111, Jinyang Li et al., 2023-05-04  
Source 3: Spider 2.0: Evaluating Language Models on Real-World Enterprise Text-to-SQL Workflows, https://arxiv.org/abs/2411.07763, Fangyu Lei et al., 2024-11-12  
Source 4: LinkAlign: Scalable Schema Linking for Real-World Large-Scale Multi-Database Text-to-SQL (version 3), https://arxiv.org/html/2503.18596v3, Yihan Wang et al., 2025-06-14  
Source 5: LangChain structured output, https://docs.langchain.com/oss/python/langchain/structured-output, LangChain, n.d.  
Source 6: Temperature in GPT-5 models, https://community.openai.com/t/temperature-in-gpt-5-models/1337133, OpenAI developer community, n.d.  
Source 7: LangChain SQL agent, https://docs.langchain.com/oss/python/langchain/sql-agent, LangChain, n.d.  
Source 8: Semantic Evaluation for Text-to-SQL with Distilled Test Suites, https://arxiv.org/abs/2010.02840, Ruiqi Zhong et al., 2020-10-06  
Source 9: PostgreSQL ALTER ROLE, https://www.postgresql.org/docs/current/sql-alterrole.html, PostgreSQL Global Development Group, n.d.  
Source 10: PostgreSQL error codes, https://www.postgresql.org/docs/current/errcodes-appendix.html, PostgreSQL Global Development Group, n.d.  
Source 11: LangChain custom middleware, https://docs.langchain.com/oss/python/langchain/middleware/custom, LangChain, n.d.  
Source 12: LangChain built-in middleware, https://docs.langchain.com/oss/python/langchain/middleware/built-in, LangChain, n.d.  
Source 13: PostgreSQL SELECT, https://www.postgresql.org/docs/current/sql-select.html, PostgreSQL Global Development Group, n.d.  
Source 14: Postgres Job Queues & Failure By MVCC, https://brandur.org/postgres-queues, Brandur Leach, 2015-05-18  
Source 15: You don't need a job queue: Postgres already has SKIP LOCKED, https://www.prisma.io/blog/you-dont-need-a-job-queue-postgres-already-has-skip-locked, Prisma, 2026-07-17  
Source 16: LangChain human-in-the-loop, https://docs.langchain.com/oss/python/langchain/human-in-the-loop, LangChain, n.d.  
Source 17: Loop engineering, https://cobusgreyling.github.io/loop-engineering/, Cobus Greyling, n.d.  
Source 18: MAGIC: Generating Self-Correction Guideline for In-Context Text-to-SQL, https://arxiv.org/abs/2406.12692, Arian Askari et al., 2024-06-18  
Source 19: Toward Real-World Table Agents: Capabilities, Workflows, and Design Principles for LLM-based Table Intelligence, https://arxiv.org/html/2507.10281, Jiaming Tian et al., 2025-07-14  
Source 20: SEED: Enhancing Text-to-SQL Performance and Practical Usability Through Automatic Evidence Generation, https://arxiv.org/abs/2506.07423, Janghyeon Yun et al., 2025-06-09  
Source 21: Test and monitor a Genie Agent, https://docs.databricks.com/aws/en/genie-agents/monitor, Databricks, n.d.  
Source 22: Suggestions for semantic models and views, https://docs.snowflake.com/en/user-guide/views-semantic/verified-query-suggestions, Snowflake, n.d.  
Source 23: Vanna documentation, https://vanna.ai/docs/, Vanna, n.d.  
Point at: the hill-climbing row: the prior art you can compare with.  
Likely question: "Which one should I read first?" Answer: BIRD for evidence, then the test-suite accuracy paper for why one database is not enough.  
Transition: Last questions.

**Slide 79: Questions and close**

Container: key-idea box: fixed question wording

On the slide:

No Question Is Too Small Every Question Deserves an Answer!!
See you at the Thursday review: the time is in the class chat

Speaker notes:

Time: 1 minute (3:59-4:00)  
Say: Take the last questions. Remind everyone to post Thursday questions in the chat. End at 4:00. Post the Thursday review time in the class chat if it is not there yet.  
Point at: the Thursday line.  
Likely question: "Where do I start after class?" Answer: setup, then the Section 1 demos on your own machine.  
Transition: End of class.

## Words on each slide

Words on the slide and words in the speaker notes after the Time line; reviewer comments are not counted.

| # | Slide | Words on the slide | Words in the notes |
|---|---|---|---|
| 1 | Module: Loop Engineering | 24 | 118 |
| 2 | Instructor | 8 | 91 |
| 3 | Welcome: before we begin, in the chat | 16 | 91 |
| 4 | How the class runs | 39 | 168 |
| 5 | Support during the class | 18 | 77 |
| 6 | Your OpenAI key and its limit | 34 | 145 |
| 7 | LangSmith setup | 18 | 165 |
| 8 | Setup checks | 33 | 213 |
| 9 | Recap: from one harness to four loops | 43 | 132 |
| 10 | Problem statement: what are we building? | 62 | 114 |
| 11 | Every section's question: net revenue in fiscal year 2025 | 69 | 165 |
| 12 | Why this matters | 67 | 83 |
| 13 | Four loops: one system, the answer path | 0 | 131 |
| 14 | Four loops: the hill-climbing loop feeds back | 0 | 163 |
| 15 | How we will measure | 55 | 121 |
| 16 | Glossary | 69 | 55 |
| 17 | Agenda (Section 1 highlighted) | 22 | 204 |
| 18 | Failure story: the board-deck number | 96 | 214 |
| 19 | Agent loop: will a stronger model fix the revenue number? | 78 | 231 |
| 20 | 1) Schema linking: tools are how the agent sees | 125 | 623 |
| 21 | 2) Context is a budget: cap at the tool | 124 | 631 |
| 22 | 3) Structured output is a contract | 113 | 634 |
| 23 | 4) A subagent must earn its place | 124 | 603 |
| 24 | Cheat sheet: the agent loop in four moves | 96 | 127 |
| 25 | Section 1: Agent loop - Implementation Notes: The confident wrong answer | 93 | 1517 |
| 26 | Questions | 24 | 168 |
| 27 | Reference: skip if short on time - tool output design | 60 | 321 |
| 28 | Reference: skip if short on time - structured output strategies | 51 | 315 |
| 29 | Reference: skip if short on time - five traps | 59 | 380 |
| 30 | Agenda (Section 2 highlighted) | 19 | 193 |
| 31 | Failure story: the product name that said delete | 99 | 235 |
| 32 | Verification loop: if every grader passes, is the answer right? | 70 | 216 |
| 33 | 1) Allowlist the shape, not a list of bad words | 121 | 627 |
| 34 | 2) Permissions are the boundary, not the parser | 115 | 561 |
| 35 | 3) Stops that are not the model's choice | 123 | 630 |
| 36 | 4) A checker that shares the maker's blind spots | 122 | 650 |
| 37 | Cheat sheet: verification in four moves | 98 | 135 |
| 38 | Section 2: Verification loop - Implementation Notes: Every grader passes, still wrong | 91 | 1552 |
| 39 | Questions | 18 | 210 |
| 40 | Reference: skip if short on time - attack patterns | 99 | 308 |
| 41 | Reference: skip if short on time - database errors as feedback | 103 | 392 |
| 42 | Reference: skip if short on time - why one database lies | 61 | 309 |
| 43 | Time for a Break | 20 | 69 |
| 44 | Agenda (Section 3 highlighted) | 22 | 254 |
| 45 | Failure story: the digest that posted twice | 86 | 239 |
| 46 | Event loop: should an agent route the events? | 62 | 244 |
| 47 | 1) At-least-once delivery needs idempotent effects | 121 | 637 |
| 48 | 2) The queue is a table: claim, lease, reap | 119 | 649 |
| 49 | 3) Durable approval: pause where state lives | 118 | 615 |
| 50 | 4) A router, levels, and a stop for running work | 114 | 623 |
| 51 | Cheat sheet: the event loop in four moves | 85 | 160 |
| 52 | Section 3: Event loop - Implementation Notes: The kill switch in flight | 99 | 1743 |
| 53 | Questions | 23 | 212 |
| 54 | Reference: skip if short on time - queue failure modes | 76 | 371 |
| 55 | Reference: skip if short on time - router or supervisor | 68 | 324 |
| 56 | Reference: skip if short on time - business and wall clocks | 60 | 439 |
| 57 | Live Zoom Poll | 19 | 142 |
| 58 | Time for a Break | 20 | 166 |
| 59 | Agenda (Section 4 highlighted) | 23 | 220 |
| 60 | Failure story: the prompt full of patches | 88 | 230 |
| 61 | Hill-climbing loop: promote rules when the development score rises? | 53 | 233 |
| 62 | 1) A benchmark is a measuring instrument | 121 | 624 |
| 63 | 2) Rules learned from failures overfit | 115 | 634 |
| 64 | 3) The gate is a paired comparison | 125 | 646 |
| 65 | 4) Autonomy is earned per metric family | 115 | 650 |
| 66 | Cheat sheet: the hill-climbing loop in four moves | 81 | 132 |
| 67 | Section 4: Hill-climbing loop - Implementation Notes: The candidate experiment | 88 | 3654 |
| 68 | Questions | 20 | 238 |
| 69 | Reference: skip if short on time - gate statistics | 93 | 599 |
| 70 | Reference: skip if short on time - prior art compared | 93 | 398 |
| 71 | Reference: skip if short on time - when learned knowledge fails | 85 | 327 |
| 72 | Final run: one question through four loops | 84 | 239 |
| 73 | All results: one picture | 81 | 321 |
| 74 | Which loop when: match the failure | 61 | 107 |
| 75 | Use it at work: four questions to ask | 56 | 117 |
| 76 | Assignments, final project, and the Thursday review | 85 | 308 |
| 77 | Summary: key takeaways | 62 | 73 |
| 78 | References | 69 | 454 |
| 79 | Questions and close | 23 | 61 |

## Sources cited in the notes

- Source 1: The art of loop engineering, https://www.langchain.com/blog/the-art-of-loop-engineering, Sydney Runkle (LangChain), 2026-06-16
- Source 2: Can LLM Already Serve as A Database Interface? A BIg Bench for Large-Scale Database Grounded Text-to-SQLs, https://arxiv.org/abs/2305.03111, Jinyang Li et al., 2023-05-04
- Source 3: Spider 2.0: Evaluating Language Models on Real-World Enterprise Text-to-SQL Workflows, https://arxiv.org/abs/2411.07763, Fangyu Lei et al., 2024-11-12
- Source 4: LinkAlign: Scalable Schema Linking for Real-World Large-Scale Multi-Database Text-to-SQL (version 3), https://arxiv.org/html/2503.18596v3, Yihan Wang et al., 2025-06-14
- Source 5: LangChain structured output, https://docs.langchain.com/oss/python/langchain/structured-output, LangChain, n.d.
- Source 6: Temperature in GPT-5 models, https://community.openai.com/t/temperature-in-gpt-5-models/1337133, OpenAI developer community, n.d.
- Source 7: LangChain SQL agent, https://docs.langchain.com/oss/python/langchain/sql-agent, LangChain, n.d.
- Source 8: Semantic Evaluation for Text-to-SQL with Distilled Test Suites, https://arxiv.org/abs/2010.02840, Ruiqi Zhong et al., 2020-10-06
- Source 9: PostgreSQL ALTER ROLE, https://www.postgresql.org/docs/current/sql-alterrole.html, PostgreSQL Global Development Group, n.d.
- Source 10: PostgreSQL error codes, https://www.postgresql.org/docs/current/errcodes-appendix.html, PostgreSQL Global Development Group, n.d.
- Source 11: LangChain custom middleware, https://docs.langchain.com/oss/python/langchain/middleware/custom, LangChain, n.d.
- Source 12: LangChain built-in middleware, https://docs.langchain.com/oss/python/langchain/middleware/built-in, LangChain, n.d.
- Source 13: PostgreSQL SELECT, https://www.postgresql.org/docs/current/sql-select.html, PostgreSQL Global Development Group, n.d.
- Source 14: Postgres Job Queues & Failure By MVCC, https://brandur.org/postgres-queues, Brandur Leach, 2015-05-18
- Source 15: You don't need a job queue: Postgres already has SKIP LOCKED, https://www.prisma.io/blog/you-dont-need-a-job-queue-postgres-already-has-skip-locked, Prisma, 2026-07-17
- Source 16: LangChain human-in-the-loop, https://docs.langchain.com/oss/python/langchain/human-in-the-loop, LangChain, n.d.
- Source 17: Loop engineering, https://cobusgreyling.github.io/loop-engineering/, Cobus Greyling, n.d.
- Source 18: MAGIC: Generating Self-Correction Guideline for In-Context Text-to-SQL, https://arxiv.org/abs/2406.12692, Arian Askari et al., 2024-06-18
- Source 19: Toward Real-World Table Agents: Capabilities, Workflows, and Design Principles for LLM-based Table Intelligence, https://arxiv.org/html/2507.10281, Jiaming Tian et al., 2025-07-14
- Source 20: SEED: Enhancing Text-to-SQL Performance and Practical Usability Through Automatic Evidence Generation, https://arxiv.org/abs/2506.07423, Janghyeon Yun et al., 2025-06-09
- Source 21: Test and monitor a Genie Agent, https://docs.databricks.com/aws/en/genie-agents/monitor, Databricks, n.d.
- Source 22: Suggestions for semantic models and views, https://docs.snowflake.com/en/user-guide/views-semantic/verified-query-suggestions, Snowflake, n.d.
- Source 23: Vanna documentation, https://vanna.ai/docs/, Vanna, n.d.

## Checks before building slides

- [x] 79 slides, within 76 to 80.
- [x] Every section has exactly one DEMO slide: its badge, what to watch for, the guaranteed moment, and the link to its demo page; its demos and code walkthrough are in its notes.
- [x] The times add up to 240 minutes, breaks and the poll included.
- [x] Two breaks and exactly one poll, after Section 3: Event loop.
- [x] No file names, repository paths, make commands, or screenshots on any slide; the DEMO slide's labelled link is the one exception.
- [x] Names are plain; codes appear only in code spans in the notes.
- [x] Every measured number names its evidence; no provisional marker is left.
- [ ] 2 refresh markers: their values are updated from the next live session, then the class run.
