"""Opening block, 0:00-0:05: 3 slides under design system 2 (slides/design-system.md).

The title (the one place in the deck that spells out Structured Query Language), the instructor,
and the hook: the agent answered the fiscal year 2025 revenue question, and the answer was wrong.
The hook's notes lead into the problem statement (slides/source/problem.py). The slides that taught
the traps, the failure classes, the four loops and the class plan moved to the foundations block.
Every number comes from .dev/deck2-reconcile.md ("The hook") and .dev/deck-evidence.md; the run id
and the date stay in the notes, as the evidence diet sets.
"""

RULES = "design system 2"

SLIDES = [
    # 1 title -----------------------------------------------------------------------------------
    dict(
        kind="title",
        title="Module: Loop Engineering",
        minutes=0.5,
        says="The course title, and the skill learners leave with",
        src="README.md; .dev/deck-spec-2.md, section 4, item 1, and section 5, item 3",
        on_slide=[
            "Module: Loop Engineering",
            "An agent that turns questions into Structured Query Language (SQL)",
            "Design, check, run and improve it: four loops, every demo live",
        ],
        notes=[
            "Purpose: Open the class and name the skill: designing, checking, running and "
            "improving a text-to-SQL agent you can trust in production.",
            "What to say: Welcome to Module: Loop Engineering. You already build agents, so "
            "today is about what comes after the demo works. You will learn to design an agent "
            "that turns plain questions into Structured Query Language, SQL, for a real "
            "warehouse, then to check it, run it from events, and improve it with evidence. "
            "Four loops around one agent, and every demo runs live.",
            "The point to land: The agent is the easy part; the loops around it decide whether "
            "you can trust it.",
            "Example: DataPilot, the course's data agent, answers plain-language questions about "
            "the warehouse of Harbor & Pine Outfitters, a fictional outdoor retailer.",
            "Ask the room: Not on this slide; the first question to the room comes on the next "
            "one, in the chat.",
            "Misconceptions: That this is a course about one framework. The loops are patterns "
            "that transfer to any agent whose output you can check.",
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
            "Transition: Keep your answer in mind. Here is one question we asked our own agent, "
            "and the answer it gave.",
        ],
    ),
    # 3 the hook: the agent answered, and the answer was wrong ----------------------------------
    dict(
        kind="story",
        title="The agent answered. The answer was wrong.",
        minutes=3.5,
        says="A clean run returns $72,394,572.08 for fiscal year 2025; the correct answer is "
        "$64,015,091.21",
        src="docs/images/agent-confident-wrong-answer-sql.png and the capture "
        "agent-loop-20261025T144436Z.json (run 9182df01, 25 October 2026, held, never posted); "
        ".dev/deck2-reconcile.md, The hook; platform/packs/datapilot_us/benchmark/"
        "business_rules.md, rules 1, 5 and 6",
        on_slide=[
            '"What was our net revenue in fiscal year 2025?"',
            "Value: The agent answered | $72,394,572.08",
            "Value: The correct answer | $64,015,091.21",
            "1. Internal accounts included",
            "2. Calendar dates, both bounds",
            "3. Coordinated Universal Time, both bounds",
            "Footer: No error and no warning; only a reviewer's doubt held it for a person",
        ],
        code={
            "language": "sql",
            "origin": "the agent's query in run 9182df01, 25 October 2026, as the console showed "
            "it (docs/images/agent-confident-wrong-answer-sql.png), rewrapped so every line holds "
            "at most 50 characters; no clause changed",
            "lines": [
                "SELECT ROUND(SUM(subtotal_cents - discount_cents)",
                "    / 100.0, 2) AS net_revenue_usd FROM orders",
                "WHERE order_ts >=",
                "        TIMESTAMPTZ '2025-01-01 00:00:00+00'",
                "  AND order_ts <",
                "        TIMESTAMPTZ '2026-01-01 00:00:00+00'",
                "  AND status = 4",
            ],
            # numbered top to bottom; traps 2 and 3 are highlighted on both bounds, disc 2 on
            # the first bound and disc 3 on the second, so no two discs share or touch a line
            "marks": [
                (1, "FROM orders", 1),
                (3, "'2025-01-01", 2),
                (5, "'2026-01-01", 2),
                (3, "+00'", 3),
                (5, "+00'", 3, True),
            ],
        },
        notes=[
            "Purpose: Make the failure felt before anything is explained: a fluent, clean run "
            "returned a wrong number, and nothing in the run reported an error.",
            "What to say: Here is a real run from this course, run 9182df01 on 25 October. The "
            "question is the one that runs through the whole class: what was our net revenue in "
            "fiscal year 2025? The agent did everything a good agent does. It listed the "
            "tables, described them, wrote one clean SQL query, and returned one number: "
            "72,394,572.08 dollars. The correct answer is 64,015,091.21. Look at the query. "
            "Marker one, from orders: it reads every order with no join to customers, so staff "
            "and test accounts stay in, and they are known only by their email domain. Marker two, on both bounds: calendar dates, "
            "January to December 2025. This company's fiscal year runs February to January "
            "and is named for the year it ends, so fiscal year 2025 ended on 31 January 2025. "
            "Marker three, again on both bounds: the plus zero zero means Coordinated Universal "
            "Time, while the business counts its days in Eastern time, so evening orders land on "
            "the wrong day. "
            "None of the three is in the schema; each lives in someone's head. And notice what "
            "did not happen: no error, no exception, and every automatic check passed on its "
            "last attempt. Only a reviewer's doubt about the fiscal year, a second model that "
            "reads each answer and which you meet in Section 2, held this run for a person, so "
            "it never posted. Without that reviewer, as you will see, answers like it go "
            "out. Keep this number in mind: we come back to this question at the end "
            "of every section, and by the close of class it comes back right.",
            "The point to land: The dangerous agent failure is not a crash; it is a confident, "
            "plausible number that is wrong.",
            'Example: The agent even wrote its assumption into the answer, "for calendar year '
            '2025", in a clean sentence a busy reader would skim past.',
            'Ask the room: "How would your current stack have caught this?" Expect: tests on the '
            "SQL, a person reading it, or nothing; most say nothing.",
            'Misconceptions: "A better model fixes this." It does not: the rules are not in the '
            "data, so no model can read them there.",
            "Transition: So who asks a question like this, and why does a wrong answer matter so "
            "much? Meet Harbor & Pine, the business behind it.",
        ],
    ),
]
