"""Foundations block, 0:17-0:30: 5 slides, 13 minutes, under design system 2.

Why the hook's answer was wrong (the five traps, taught as general kinds of trap), the four ways
agents fail in production (one per loop, in the one mapping of requirements to loops: the agent
loop for grounded answers inside a bounded cost and latency, the verification loop for safety, the
event loop for operations, the hill-climbing loop for improvement and trust; correctness is the
class's test and needs all four), the four loops on one map, how the class measures (six terms
defined once), and what learners will be able to do, set against the session plan. Course numbers
come from .dev/deck-evidence.md (entry ids in each slide's src) and the wording of "39 of 40" from
.dev/deck2-reconcile.md, item 1; at most one number from our runs on any slide, run ids and dates
in the notes only. Review round 1 rulings: .dev/review/deck2-round-1/lead-rulings.md.

The session plan uses the closing type's layout (numbered items in two columns, each disc in the
colour of the section named at its end), the one layout that holds a skill per section with its
clock; the agenda type has a 45-word limit and no second column.
"""

RULES = "design system 2"

SLIDES = [
    # 1 problem: the five traps, as general kinds of trap -----------------------------------------
    dict(
        kind="problem",
        title="Five traps: rules the schema never states",
        minutes=3,
        says="The hook's answer missed business rules no column states; five kinds of trap, "
        "each with its example, and what not knowing them cost",
        src=".dev/deck-evidence.md E1, E3, E5, E6, E7 (docs/calibration-report.md, Traps; "
        "platform/packs/datapilot_us/benchmark/business_rules.md, rules 1 and 3 to 6); "
        ".dev/deck2-reconcile.md, The hook (status 4 equals status not 5 in that period); "
        ".dev/deck-audit-2.md, F1 (old opening slides 5 and 6)",
        on_slide=[
            "Lead: Five rules no column states, so no model can read them from the schema",
            "- Calendar definitions: the fiscal year runs February to January",
            "- Metric definitions: net revenue is subtotal minus discount",
            "- Undocumented codes: status 5 means cancelled, written nowhere",
            "- Time zones: stored in Coordinated Universal Time, reported in Eastern time",
            "- Who counts: staff and test accounts, known only by email domain",
            "- The cost: with none written down, 0 of 99 runs on these traps passed",
        ],
        notes=[
            "Purpose: Explain why the hook's answer was wrong, and generalise its causes into five "
            "kinds of trap every warehouse has: business definitions the schema never states.",
            "What to say: The hook showed one wrong number. Here is why it was wrong, and why the "
            "same thing will happen in your warehouse. The query ran cleanly, and every column it "
            "used exists. What it missed are business rules that no column states. I teach them as "
            "five kinds of trap, because every company has its own version of each. One, calendar "
            "definitions. Our fiscal year runs February to January and is named for the year it "
            "ends, so fiscal year 2025 is 1 February 2024 to 31 January 2025. Two, metric "
            "definitions. Net revenue is subtotal minus discount; the total column, with tax and "
            "shipping in it, looks like revenue and is not. Three, undocumented codes. Status 5 "
            "means cancelled, and cancelled orders are left out, but the codes are written down "
            "nowhere in the warehouse. Four, time zones. Timestamps are stored in Coordinated "
            "Universal Time, while the business counts its days in Eastern time, so an evening "
            "order lands on the wrong day. Five, who counts. Staff and test accounts are known "
            "only by the company's email domain, and they must be left out. The hook's query hit "
            "three of these: calendar dates, the wrong time zone, and internal accounts. It got "
            "net revenue right with subtotal minus discount, and missed the cancelled-orders trap "
            "only by luck: that year the only statuses were 4 and 5, so its status equals 4 "
            "matched. The last card is what not knowing cost. The agent started with one rule, "
            "that money is stored in cents, and none of these; we call that the starting "
            "knowledge. Under it, not one run of a question carrying these traps passed. None of "
            "the five is a model failure. The rules live in people's heads, in a finance wiki, in "
            "a query someone wrote two years ago. A stronger model reads the same schema and "
            "makes the same guess. That is why this class is about loops: one that catches the "
            "guess, and one that learns the rule safely.",
            "The point to land: Every trap is a business definition outside the schema; no model "
            "can read a rule that is not in the data.",
            "Example: The hook is run 9182df01 of 25 October 2026, with three trap labels: "
            "calendar-year range, Coordinated Universal Time truncation, and a missing internal "
            "filter. The 0 of 99 is calibration experiment 322f604d: 33 trap questions, 3 runs "
            "each, under the starting knowledge, so 99 runs of 33 different questions, not 99 runs "
            "of this one. By trap, 0 of 75 runs carrying the fiscal year passed, 0 of 51 net "
            "revenue, 0 of 99 cancelled orders, 0 of 57 Eastern time, and 0 of 90 internal "
            "accounts; most questions carry several traps. The same shape appears outside data "
            "agents: a support agent told to refund within 30 days must know whether those are "
            "calendar days or business days, and in which time zone. That example is "
            "illustrative.",
            'Ask the room: "Which of these five does your warehouse have, and where is the rule '
            'written down?" Expect: a fiscal calendar and test accounts, almost everyone; status '
            "codes known only to one team; written down in a wiki, or nowhere.",
            "Misconceptions: That documenting the schema solves it. Column comments describe "
            "storage; these rules describe the business. They have to reach the agent as "
            "knowledge, and Section 4 shows how to earn that knowledge behind a gate.",
            "Transition: Traps explain one wrong number. Next, the four ways agents fail in "
            "production, each with the loop that fixes it.",
        ],
    ),
    # 2 problem: four ways agents fail in production ----------------------------------------------
    dict(
        kind="problem",
        title="Four ways agents fail in production",
        minutes=3,
        says="Correctness needs all four loops; each loop fixes one measured failure: grounded "
        "answers, bounded cost; safety; operations; improvement and trust",
        src=".dev/deck-evidence.md E16, E17 (the uncapped result), E24 (wording from "
        ".dev/deck2-reconcile.md, item 1), E33, E47; .dev/deck-audit-2.md, F2 (old opening "
        "slide 3); .dev/review/deck2-round-1/lead-rulings.md, rulings 1, 13 and 14",
        on_slide=[
            "Lead: Correctness is the test all four loops must pass; each loop fixes one failure",
            "- Grounded answers, bounded cost: one uncapped result blew the token budget | "
            "Agent loop",
            "- Safety: with no reviewer, 39 of 40 wrong answers went out unflagged | "
            "Verification loop",
            "- Operations: one event sent three times posted three answers | Event loop",
            "- Improvement and trust: one plausible new rule broke 9 working answers | "
            "Hill-climbing loop",
        ],
        notes=[
            "Purpose: Tie each loop to the measured failure it fixes and the requirement group it "
            "owns, with correctness as the test that needs all four.",
            "What to say: On the problem slides you heard these failures as a user meets them. "
            "Here they are as we measured them, grouped by the loop that fixes each. First, the "
            "lead line. Correctness is not one loop's job. The fiscal year 2025 question is right "
            "only when all four loops do their part, which is why it is the class's test. Now "
            "the cards. Blue, the agent loop: grounded answers, bounded cost. "
            "Its tools decide what the model sees, and its stops are code, not hope. With the row "
            "cap removed, one large result blew straight through the run's token budget. In your "
            "system that means a row cap, a size cap on each value, and a token budget checked "
            "in code. You will watch this one happen live in Section 1. Its answer also carries "
            "its query and assumptions, so the other loops can check it. "
            "Teal, the verification loop: safety. Nothing checks what leaves the agent unless you "
            "build it. In our runs, with no reviewer, 39 of 40 wrong answers went out unflagged. "
            "The checks in code passed them, because a query that runs cleanly passes them "
            "whatever it means. The same gap lets a disguised write or a column of customer "
            "emails through. Orange, "
            "the event loop: operations. Production agents run from webhooks and schedules. "
            "Webhooks arrive at least once, workers restart, and someone must stop a run already "
            "under way. With the duplicate protection switched off, one event sent three times "
            "posted three answers. Lime, the hill-climbing loop: improvement and trust. You will "
            "change the rules, the prompt, the model. Without measurement, a change that looks "
            "right breaks what worked: one plausible new rule, exclude discounted orders from "
            "revenue, broke 9 answers that passed before, and only the promotion gate's "
            "comparison showed it; the promotion gate is the check that decides whether a new "
            "version of the rules goes live. Section 4 opens with this rule, told, not run live; "
            "it is the failure that loop exists to stop. Trust lives here too: "
            "autonomy granted only where the evidence has earned it.",
            "The point to land: Agents fail around the model, not inside it: in what they see, "
            "what checks them, how they run, and how they change.",
            "Example: The run detail behind each number. Agent loop: with the row cap removed, a "
            "10,000-row result took one run to 182,654 tokens against a 60,000-token budget, "
            "because the budget is checked before each call and one call overshot it. Safety: "
            "on 24 October 2026 we asked 20 trap questions twice each, 40 runs, with the checks "
            "in code on, a guard that reads only the first word, and no reviewer: every "
            "answer was wrong, 39 went out with no flag, and the one stopped was escalated by the "
            "retry cap, not caught as wrong. Operations: with both duplicate bugs on, the same "
            "event sent three times gave 3 answers and 2 digests in every planted run; with the "
            "fix, 1 answer in 7 of 7 runs. Improvement: version 11 plus the rule broke 4 "
            "development and 5 holdout questions, 9 regressions, and the gate blocked it, run "
            "84417bfe on 24 October. The same four in a coding agent: a tool that dumps a whole "
            "log into context, a command that deletes a branch, a webhook that opens two reviews, "
            "a prompt change that breaks last week's fixes. That example is illustrative.",
            'Ask the room: "Which of the four has hurt you?" Expect: wrong numbers nobody caught, '
            "and duplicate or runaway jobs; rarely a change measured before release.",
            "Misconceptions: That the loops can wait until after launch. Each needs something the "
            "agent must carry from day one: a status, a query to check, an event key, a knowledge "
            "version.",
            "Transition: One loop for each failure. Here are the four on one map.",
        ],
    ),
    # 3 concept: the four loops on one map, roles first ------------------------------------------
    dict(
        kind="concept",
        title="Four requirement groups, four loops",
        minutes=2.5,
        says="The four loops by role: grounded answers with bounded cost, safety, operations, "
        "improvement and trust; then DataPilot's part for each role",
        src="docs/diagrams/four-loops-generic.excalidraw; docs/architecture.md; "
        ".dev/deck-sources.md [1]; .dev/deck-audit-2.md, F3 (old opening slide 4); "
        ".dev/review/deck2-round-1/lead-rulings.md, rulings 1, 9 and 18",
        figure={
            "diagram": "four-loops-generic",
            "alt": "The four loops nested, each part named by its job: in the agent loop, a model "
            "answers with tools and code stops it; in the verification loop, layered checks, then"
            " a person decides a doubtful answer; in the event loop, events arrive, each is keyed"
            " once and queued with leases, a kill switch points at the queue and stops every run,"
            " and human approval comes before a post; beside them the hill-climbing loop, where "
            "failures on a benchmark lead agents to propose rules, the rules are judged on unseen"
            " questions, and a person promotes them, an arrow that runs under the event loop and "
            "up into the model",
        },
        on_slide=[],
        notes=[
            "Purpose: Present the four loops by role, as the answer to the four failures, on the "
            "one map every section points back to; then name DataPilot's part for each role.",
            "What to say: Here is the answer on one map, drawn by role, so you can lay it over "
            "your own agent. In the middle, in blue, the agent loop: a model answers with tools, "
            "and stops in code end the run. That is grounded answers, bounded cost. "
            "Around it, in teal, the verification loop, for safety: layered checks read every "
            "query and answer, and a doubtful answer goes to a person. Around both, in orange, "
            "the event loop, for operations. Events arrive, each is keyed once, then queued with "
            "a lease so one worker owns it. A kill switch stops every run, and human approval "
            "comes before a post, or the answer is held. Far right, in lime, the hill-climbing "
            "loop, for improvement and trust: failures on a benchmark lead agents to propose "
            "rules, the rules are judged on questions the proposers never saw, and a person "
            "promotes them back to the model. Now DataPilot's parts, role by role. The model is "
            "the analyst agent, with the schema helper agent, a helper that may only list and "
            "describe tables. The layered checks are graders in code, "
            "then a reviewer agent. The key is the sender's event id or the digest's business "
            "day, and the queue is a jobs table in Postgres. The proposers are the analyzer team, "
            "and the judge is the promotion gate. Count the ovals: models appear only where "
            "judgement is needed. Routing, checks and the gate are code, because they must "
            "behave the same way every time.",
            "The point to land: One agent, four loops around it, each owning one failure; models "
            "only where judgement is needed, code everywhere else.",
            "Example: LangChain's article that names these four loops calls the fourth arguably "
            "the most important, because it automates improvement, Source 1. DataPilot's sizes: "
            "25 development and 15 holdout questions, seven graders, an analyzer team of three "
            "agents (a failure analyst, a rule writer and a critic), and a gate with four "
            "conditions.",
            'Ask the room: "Which box on this map is code in your system, and which is a model?" '
            "Expect: routing and checks are often a model; push for code there.",
            "Misconceptions: That more agents give a system more capability. Here the router, the "
            "graders, and the gate are code on purpose: they must behave the same every time.",
            "Transition: Every loop is judged by measurement. Before we start, six terms that "
            "every number today depends on.",
        ],
    ),
    # 4 problem: how we measure, six terms defined once -------------------------------------------
    dict(
        kind="problem",
        title="How we measure",
        minutes=3,
        says="Gold answer, trap question, run, development and holdout, regression, planted bug: "
        "plain definitions with examples",
        src=".dev/deck-evidence.md E2, E11, E12, E33 to E35, E40, E41, E49, E51; "
        ".dev/deck2-sources.md [106]; .dev/deck-audit-2.md, F4",
        on_slide=[
            "Lead: Six terms every number today depends on",
            "- Gold answer: the checked result a question must return",
            "- Trap question: its answer hinges on a rule the schema never states",
            "- Run: one request, question to status; repeated, since answers vary",
            "- Development and holdout: questions to learn from; questions held back to judge",
            "- Regression: passed before a change, fails after, confirmed by re-runs",
            "- Planted bug (a forced failure): a known defect we switch on to test a guard",
        ],
        notes=[
            "Purpose: Define the six measurement terms the class uses, each with an example, "
            "before any number depends on them.",
            "What to say: Six terms, because every number today uses them and each hides a "
            "choice you will make in your own system. A gold answer is the result a question must "
            "return, checked by a person. Our fiscal year 2025 question has one: 64,015,091.21 "
            "dollars. We compare results, not query text, because two different queries can both "
            "be right, and we compare on two databases with the same schema and different data, "
            "so a query cannot match by recalling a number. A trap question is one whose right "
            "answer depends on a rule the schema never states, any of the five traps. A run is "
            "one request to the agent, from the question to a status: answered, held for a "
            "person, or escalated. The same question can get a different answer on the next run, "
            "so we repeat runs: a holdout question runs three times and passes when two of the "
            "three match gold. Development and holdout questions are the split every evaluation "
            "needs. The improver may study the development questions. Holdout questions are held "
            "back; only the promotion gate sees them, so a rule that memorised the test cannot "
            "pass. A regression is a question that passed under the active version and fails "
            "under the candidate; an apparent one is re-run before it counts, because one failure "
            "can be noise. A planted bug is a forced failure: a known defect, switched on by a "
            "flag, that removes one real protection. Each demo with a planted bug runs with the "
            "bug on, so you watch "
            "the failure, then with it off, so you watch the fix. One more word you will meet: a "
            "metric family is questions of one kind, such as revenue, promoted together. If you "
            "leave with one habit from this slide, make it the gold answer: a small set of "
            "questions with checked answers, started from real failures, is the first thing to "
            "build.",
            "The point to land: Measure results against checked answers, repeat runs because "
            "answers vary, and decide on questions the improver never saw.",
            "Example: The benchmark has 25 development and 15 holdout questions, 33 of them trap "
            "questions; one experiment is 70 runs, development questions once and holdout "
            "questions three times. A regression, confirmed or not: under version 4, the fiscal "
            "year 2026 revenue question passed 1 of 3 runs, an apparent regression, then passed 3 "
            "of 3 re-runs, and the gate recorded it as not a regression. A planted bug: with the "
            "kill switch checked only when a job is claimed, an answer posted after the switch "
            "was engaged. A metric family earns its autonomy level on its own holdout questions; "
            "revenue has 4. Anthropic's guidance on agent evaluation says 20 to 50 simple tasks "
            "drawn from real failures are a great start for a gold set, Source 106.",
            'Ask the room: "Does your team have a gold answer for its most important number?" '
            "Expect: a spreadsheet someone trusts, or nobody is sure.",
            "Misconceptions: That one passing run proves a question is answered. Answers vary "
            "from run to run, so a single pass is a sample of one; repeat it, and decide on "
            "questions the improver never saw.",
            "Transition: With the terms in place, here is what you will be able to do by the end "
            "of today, and when each part comes.",
        ],
    ),
    # 5 the session plan: one skill per section, with its clock ---------------------------------
    dict(
        kind="closing",
        title="What you will be able to do, and when",
        minutes=1.5,
        says="Learning objectives as skills, one per section and one for the design segment, "
        "on the session's clock with the breaks and the poll",
        src=".dev/review/deck2-brief.md, the block plan; .dev/deck-spec-2.md, section 2; "
        ".dev/review/deck2-round-1/lead-rulings.md, ruling 11; .dev/deck-audit-2.md, F5 (old "
        "opening slide 7)",
        on_slide=[
            "1. 0:30 Choose where rules live and how much schema to show | Design",
            "2. 0:40 Design a tool that truncates with a notice; put stops in code | Section 1",
            "3. 1:15 Order checks cheap to strong; read-only by grants | Section 2",
            "4. 1:50 Break",
            "5. 2:00 Make handlers idempotent; keep approvals through restarts | Section 3",
            "6. 2:48 Poll, then a break at 2:53",
            "7. 3:03 Split development and holdout; gate on zero regressions | Section 4",
            "8. 3:45 Closing: the question, answered",
        ],
        notes=[
            "Purpose: Set the learning objectives as skills, one per section and one for the "
            "design segment, on the session's clock with the breaks and the poll.",
            "What to say: These are times from the start of class; I post the local times of the "
            "two breaks in the chat. At 0:30, designing text-to-SQL: choose where business rules "
            "live and how much schema the agent sees. Section 1 at 0:40: design a tool that "
            "returns what the model needs and says what it cut, with stops in code. Section 2 at "
            "1:15: order checks cheap to strong, our rule, with grants as the last line. Section "
            "3 at 2:00: make a handler idempotent, and keep a human approval alive across a "
            "restart. Section 4 at 3:03: split development and holdout questions, and gate a "
            "change on zero regressions. Every demo is live; if one stalls, I reset it and run "
            "it again.",
            "The point to land: Each section ends with a skill you can use on Monday, in any "
            "agent, not only this one.",
            "Example: Section 3's skill on a support agent: a ticket webhook keyed by the "
            "sender's event id, so a retried delivery never refunds twice. That example is "
            "illustrative.",
            'Ask the room: "Which of these skills does your team need first?" Expect: the event '
            "loop or the gold set; say which section answers it.",
            "Misconceptions: That a live demo that misbehaves is a failed class. A surprise is "
            "what the loops exist to catch.",
            "Transition: Before the first loop, how do you design a text-to-SQL system at all? "
            "Business knowledge decides the answer.",
        ],
    ),
]
