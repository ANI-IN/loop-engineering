"""Opening block, 0:00-0:10: 7 slides under the design system (slides/design-system.md).

The title, the instructor, why agents fail in production (the four failure classes the four loops
answer), the four loops on one map, the fiscal year 2025 revenue question as a problem story and
its five traps, and how the class runs. Every course number comes from .dev/deck-evidence.md
(entry ids in each slide's src); every external one from .dev/deck-sources.md, cited with its
number there. "What to say" fits the slide's minutes: at most minutes x 130 words, less 40 when the
slide asks the room (round 1, ruling 1).
"""

RULES = "design system"

SLIDES = [
    # 1 title -----------------------------------------------------------------------------------
    dict(
        kind="title",
        title="Module: Loop Engineering",
        minutes=0.5,
        says="The course title and what learners leave able to do",
        src="README.md; the owner's specification, section 1",
        on_slide=[
            "Module: Loop Engineering",
            "Turn questions into Structured Query Language (SQL), safely, in production",
            "Four loops around one agent, every demo live",
        ],
        notes=[
            "Purpose: Open the class and name the outcome: designing and running a text-to-SQL "
            "agent safely, and making it improve with evidence.",
            "What to say: Welcome to Module: Loop Engineering. You already build agents, so today "
            "is about what comes after the demo works: designing a text-to-SQL agent for your own "
            "warehouse, running it safely, and improving it with evidence. Four loops around one "
            "agent, and every demo runs live against the real model.",
            "The point to land: The agent is the easy part; the loops around it decide whether "
            "you can trust it.",
            "Example: DataPilot, the course's data agent, answers plain-language questions about "
            "the warehouse of Harbor & Pine Outfitters, a fictional outdoor retailer.",
            "Ask the room: Not on this slide; the first question to the room comes on the next "
            "one, in the chat.",
            "Misconceptions: That this is a course about one framework. The loops transfer to any "
            "agent whose output you can check.",
            "Transition: First, who is teaching today.",
        ],
    ),
    # 2 title: the instructor (the owner's decision: this exact line) ---------------------------
    dict(
        kind="title",
        title="Your instructor",
        minutes=1,
        says="Who is teaching, and where questions go",
        src="DECISIONS.md, 26 October 2026, the owner's decisions after session 7, item 3",
        on_slide=[
            "Your instructor",
            "Taught by [INSTRUCTOR NAME]; questions go in the class chat",
        ],
        notes=[
            "Purpose: Introduce the instructor and set where questions go. Replace the name in "
            "square brackets before class.",
            "What to say: Introduce yourself in two sentences: what you build, and one loop that "
            "saved you or cost you in production. Then: questions go in the class chat at any "
            "time, and I answer them between slides. A question that needs more than a minute "
            "goes to the Thursday review session, which answers every parked question in "
            "writing.",
            "The point to land: Ask early in the chat; nothing is too small.",
            "Example: A loop that saved you, such as a retry cap that stopped a runaway bill.",
            'Ask the room: "Post one line: which agent do you run, and what stops it when it is '
            'wrong?" Expect: a person reads the output, or nothing.',
            "Misconceptions: That questions wait until the end. They go in the chat as they come.",
            "Transition: Let me start with why agents fail once they reach production.",
        ],
    ),
    # 3 insight: why agents fail in production, the four failure classes ------------------------
    dict(
        kind="insight",
        title="Why agents fail in production",
        minutes=1.5,
        says="Four failures around the model, one measured number each, one loop for each",
        src=".dev/deck-evidence.md E7 (docs/calibration-report.md, Traps), E24 (docs/benefits.md, "
        "Section 2), E33, E34, E35 (planted halves: 5, 6 and 6 runs), E47 (the over-broad rule); "
        ".dev/review/deck-round-1/lead-rulings.md, ruling 7",
        on_slide=[
            "Insight: Agents fail around the model, in four ways.",
            "Evidence: One failure per loop, built in on purpose and measured live.",
            "- Missing rules: 0 of 99 trap runs passed",
            "- Unchecked answers: 39 of 40 wrong ones went out unflagged",
            "- Unattended runs: planted bugs failed 17 of 17 runs",
            "- Unmeasured change: one plausible rule broke 9 answers",
        ],
        notes=[
            "Purpose: Open with the four ways agents fail around the model, one measured number "
            "each, so the four loops arrive with a reason.",
            "What to say: Why do agents fail in production? Here is what failed in "
            "this course's runs, in four classes. One, missing rules. The rules that decide "
            "whether a number is right live in people's heads: 33 trap questions, three runs "
            "each, 99 runs, and 0 passed. Two, unchecked answers. Without the verification "
            "layer, 39 of 40 wrong answers went out with no flag. Three, unattended runs. "
            "Planted bugs in delivery, state, and control, such as a kill switch checked only at "
            "claim, failed in 17 of 17 runs. Four, unmeasured change. One plausible new rule, "
            "exclude discounted orders, broke 9 answers that passed before; holdout passes "
            "fell from 12 to 7, and the gate named each broken answer. We built all four into the course's system "
            "on purpose, so you can watch each one fail live. That is why today is four loops "
            "around one agent, and why each section opens with one of these failures.",
            "The point to land: Agents fail around the model: missing rules, unchecked answers, "
            "unattended runs, unmeasured change; each needs its own loop.",
            "Example: The 17 runs are the planted halves of three Section 3 demos: duplicate "
            "events posted 3 answers, a restart lost a pending approval, and an answer posted "
            "after the kill switch.",
            'Ask the room: "Which of the four has hurt you?" Expect: wrong numbers nobody caught, '
            "and duplicate or runaway jobs; rarely a change measured before release.",
            'Misconceptions: "A better model fixes this." This course compared no models, and '
            "none of the four is a model skill: a rule that is not in the data, a missing check, "
            "a bug in delivery code, a change nobody measured.",
            "Transition: One loop for each failure: here they are on one map.",
        ],
    ),
    # 4 concept diagram: the four loops on one map ----------------------------------------------
    dict(
        kind="concept",
        title="The four loops on one map",
        minutes=2,
        says="Answer, check, run on events, improve: four loops, agents only where judgement is needed",
        src="docs/diagrams/four-loops.excalidraw; docs/architecture.md; .dev/deck-sources.md [1]",
        figure={
            "diagram": "four-loops",
            "alt": "The event loop frame holds an event arriving, a router that is a fixed "
            "table, and a jobs table with claim and lease, which hands the run to the analyst "
            "agent. Inside it, the verification loop holds seven graders and the reviewer agent, "
            "and inside that the agent loop holds the analyst agent and the schema scout. The "
            "checked answer goes to human approval, then is posted or held for a person; a kill "
            "switch stops every run. Beside them, the hill-climbing loop runs from the benchmark "
            "of 25 development and 15 holdout questions, through the analyzer team of three "
            "agents and the promotion gate with four conditions, to the active knowledge "
            "version, which is fed back to the analyst agent when promoted.",
        },
        on_slide=[],
        notes=[
            "Purpose: Give the whole system in one picture, so every section can point back to "
            "its place on this map.",
            "What to say: The idea on this slide: Four loops around one agent: answer, check, run on events, improve. "
            "This is the map for the day; each section highlights its own part. In "
            "the middle, in blue, the agent loop: the analyst agent answers with its tools, and "
            "the schema scout reads the schema for it. Section 1. Around it, in teal, the "
            "verification loop: seven deterministic graders, then a reviewer agent for what they "
            "cannot judge. Section 2. Around both, in orange, the event loop, Section 3. Top "
            "left, an event arrives. The router is a fixed table, not an agent. The run goes "
            "into a jobs table, where a worker claims it under a lease. On the right, a checked "
            "answer meets human approval when it needs one, then is posted or held. The kill "
            "switch stops every run, including the one in flight. Far right, in lime, the "
            "hill-climbing loop, Section 4: from a benchmark of 25 development and 15 holdout "
            "questions, an analyzer team writes rules from failures, the promotion gate checks "
            "four conditions, and a promoted version becomes the knowledge the analyst reads on "
            "every run. Count the ovals: agents appear only where judgement is needed.",
            "The point to land: One agent, four loops around it; agents only where judgement is "
            "needed, code everywhere else.",
            "Example: LangChain's article that names these four loops calls the fourth arguably "
            "the most important, because it automates improvement, Source 1.",
            'Ask the room: "Which of these loops does your agent have today?" Expect: the agent '
            "loop, sometimes a human check; rarely an event loop with a stop, almost never a "
            "gated improvement loop.",
            "Misconceptions: That more agents give a system more capability. Here the router, the "
            "graders, and the gate are code on purpose: they must behave the same every time.",
            "Transition: One question will travel through all four loops today. Here is the first "
            "time we asked it.",
        ],
    ),
    # 5 problem story: the worked example of the specification ---------------------------------
    dict(
        kind="story",
        title="The agent answered. The answer was wrong.",
        minutes=2.5,
        says="A fluent answer to the fiscal year 2025 revenue question misses three traps",
        src="docs/images/agent-confident-wrong-answer-sql.png (run 9182df01, 25 October 2026); "
        ".dev/deck-evidence.md Part A, E2, E3, E7, E26; DECISIONS.md, 26 October 2026",
        on_slide=[
            '"What was our net revenue in fiscal year 2025?"',
            "Value: The agent answered | $72,394,572.08",
            "Value: The correct answer | $64,015,091.21",
            "1. Internal accounts included",
            "2. Calendar dates, not the fiscal year",
            "3. Coordinated Universal Time, not Eastern time",
            "Footer: 0 of 99 trap runs passed under the starting knowledge",
        ],
        code={
            "language": "sql",
            "origin": "the agent's query in run 9182df01, 25 October 2026 "
            "(docs/images/agent-confident-wrong-answer-sql.png), one clause per line; the "
            "markers are numbered top to bottom, so they differ from the capture's (fiscal year "
            "1, Eastern time 2, internal accounts 3 on WHERE); the slide marks internal accounts "
            "on FROM orders, the clause with no join to customers and so no email filter",
            "lines": [
                "SELECT ROUND(SUM(subtotal_cents - discount_cents)",
                "             / 100.0, 2) AS net_revenue_usd",
                "FROM orders",
                "WHERE order_ts >= TIMESTAMPTZ '2025-01-01 00:00:00+00'",
                "  AND order_ts <  TIMESTAMPTZ '2026-01-01 00:00:00+00'",
                "  AND status = 4",
            ],
            "marks": [
                (2, "FROM orders", 1),
                (3, "'2025-01-01 00:00:00+00'", 2),
                (4, "'2026-01-01 00:00:00+00'", 2),
                (3, "order_ts", 3),
                (4, "order_ts", 3),
            ],
        },
        notes=[
            "Purpose: Show that a fluent, plausible answer can be wrong in ways the schema cannot "
            "reveal, and nothing in the run reports an error.",
            "What to say: This is a real run from this course, run 9182df01. The question is the "
            "one that runs through the whole class: what was our net revenue in fiscal year "
            "2025? The agent did everything a good agent does. It listed the tables, described "
            "them, wrote one clean query, and returned one number: 72,394,572.08 dollars. The "
            "correct answer is 64,015,091.21. Look at the query, top to bottom. Marker one: it "
            "reads every order, with no join to customers, so staff and test accounts, known "
            "only by their email domain, stay in. Marker two: calendar dates, January to "
            "December 2025. Our fiscal year runs February to January and is named for the year "
            "it ends, so fiscal year 2025 is 1 February 2024 to 31 January 2025. Marker three: "
            "it compares the raw timestamp, stored in Coordinated Universal Time, while business "
            "days are in Eastern time, so evening orders land on the wrong day. Each trap lives in business "
            "knowledge, not in the data. And notice what did not happen: no error, no exception, "
            "and every grader passed. Only the reviewer's doubt held this run for a person. The "
            "footer is the 0 of 99 you saw a few minutes ago, on why agents fail: 33 trap "
            "questions, 3 runs each.",
            "The point to land: The dangerous agent failure is not a crash; it is a confident "
            "number that is wrong.",
            'Example: The agent even wrote its own wrong assumption into the answer, "for '
            'calendar year 2025", in a clean sentence a reader would skim past.',
            'Ask the room: "How would your current stack have caught this?" Expect: tests on the '
            "SQL, a human review, or nothing; most say nothing.",
            'Misconceptions: "A better model fixes this." It does not: the rules are not in the '
            "data, so no model can read them there.",
            "Transition: Three traps hit this query. Two more hide in the same question.",
        ],
    ),
    # 6 evidence: the five traps, the thread of the class ---------------------------------------
    dict(
        kind="evidence",
        title="One question, five traps no column states",
        minutes=1.5,
        says="Five business rules hide in the question; under the starting knowledge no trap run passed",
        src=".dev/deck-evidence.md E1, E4, E5, E6, E7, E53 (docs/calibration-report.md, Traps; "
        "platform/packs/datapilot_us/benchmark/business_rules.md)",
        chart={
            "type": "column",
            "title": "Trap-question runs under the starting knowledge, by trap",
            "categories": [
                "Fiscal year",
                "Net revenue",
                "Cancelled orders",
                "Eastern time",
                "Internal accounts",
            ],
            "series": [
                ("Runs whose question carries the trap", [75, 51, 99, 57, 90]),
                ("Runs passed", [0, 0, 0, 0, 0]),
            ],
            "x_label": "Trap in the question",
            "y_label": "Runs, of 99",
            "maximum": 120,
        },
        on_slide=[
            "Sample: 33 trap questions, 3 runs each, 99 runs, starting knowledge",
            "Fiscal year 2025: 1 February 2024 to 31 January 2025",
            "Net revenue: subtotal minus discount; cancelled orders out",
            "Dates in Eastern time, not Coordinated Universal Time",
            "Internal accounts, known by email domain, excluded",
        ],
        notes=[
            "Purpose: Name the five traps of the fiscal year 2025 revenue question, the thread of "
            "the class, and show none was passed under the starting knowledge.",
            "What to say: The fiscal year 2025 revenue question carries all five traps of our "
            "benchmark. You meet it in Sections 1, 2 and 4, and in Section 4 it arrives through "
            "Section 3's event pipeline. The cards: the fiscal year runs "
            "February to January, named for the year it ends. Net revenue is subtotal minus "
            "discount, not the total column with tax and shipping. Cancelled orders carry status "
            "5, documented nowhere. Timestamps are stored in Coordinated Universal Time, but "
            "business days are Eastern time days. Internal accounts are known only by the "
            "company's email domain. The chart: the grey bar is how many "
            "runs carried each trap; most questions carry several, so the grey bars add up to more "
            "than 99. The bar beside each, how many passed: zero, for every one of the five. In "
            "Section 4 the hill-climbing loop learns these rules from failures, and this "
            "question comes back right, 64,015,091.21.",
            "The point to land: Every trap is a business rule outside the schema; the class is "
            "about catching and then learning such rules safely.",
            "Example: Run 9182df01 used subtotal minus discount and kept only status 4, so it "
            "hit three traps; six other runs answered 76,981,355.95 dollars with four trap "
            "labels.",
            'Ask the room: "Which of these five does your warehouse have?" Expect: a fiscal '
            "calendar and test accounts, almost everyone; undocumented status codes, most.",
            "Misconceptions: That documenting the schema solves it. That document is the "
            "knowledge the agent needs, and Section 4 shows how to earn it behind a gate.",
            "Transition: Here is how the next four hours run.",
        ],
    ),
    # 7 agenda: how the class runs --------------------------------------------------------------
    dict(
        kind="agenda",
        title="How the class runs",
        minutes=1,
        says="Design, four sections, two breaks, one poll; every demo live; recovery is reset and "
        "run again",
        src="docs/instructor-guide.md; .dev/review/deck-brief.md, the block plan; "
        "platform/demos/registry.yaml",
        on_slide=[
            "Every demo live; if one stalls: reset, run again",
            "1. Designing text-to-SQL (Structured Query Language)",
            "2. Section 1: Agent loop",
            "3. Section 2: Verification loop; break",
            "4. Section 3: Event loop; poll; break",
            "5. Section 4: Hill-climbing loop",
            "6. Closing: ten insights, next steps",
        ],
        notes=[
            "Purpose: Set the plan, the two breaks and the poll, and the live-demo rule with its "
            "recovery.",
            "What to say: First, fifteen minutes on designing text-to-SQL for a real warehouse. "
            "Then one section per loop, each with one live demo segment. A break after Section 2; "
            "after Section 3, a short poll and the second break. Every demo runs live; if one "
            "stalls, I reset that section and run it again, never a recording.",
            "The point to land: Every result today is live and every number is measured; a "
            "stalled demo is reset and run again.",
            "Example: Section 4's baseline experiment starts at the poll and finishes early in "
            "the second break; the naive analyzer, queued at the break, runs through it.",
            'Ask the room: "Which loop is your biggest gap today?" Expect: verification or '
            "events; say which section answers it.",
            "Misconceptions: That a live demo that misbehaves is a failed class. A surprise is "
            "what the loops exist to catch.",
            "Transition: Before the first loop, how do you design a text-to-SQL system at all?",
        ],
    ),
]
