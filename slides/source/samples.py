"""Sample slides, one of every slide type of the design system, with full speaker notes.

The deck engine's proof and the content writers' model: each slide follows the slide schema in
slides/design-system.md, uses real course content, and states only numbers from the calibration
report, the paired measurements page, or the evidence pages. This module is not a block of the class
deck: build.py --samples writes its outline, and the deck builder's --type-samples flag builds it.
Each slide names the block it would belong to, for its colour and its progress tracker.
"""

RULES = "design system"

SLIDES = [
    # 1 title -----------------------------------------------------------------------------------
    dict(
        kind="title",
        block="opening",
        title="Module: Loop Engineering",
        minutes=0.5,
        says="The course title and what learners leave able to do",
        src="README.md",
        on_slide=[
            "Module: Loop Engineering",
            "Turn questions into Structured Query Language (SQL), safely, in production",
            "Four loops around one agent, each one measured live",
        ],
        notes=[
            "Purpose: Open the class and name the outcome: designing and running a text-to-SQL "
            "agent safely, and making it improve with evidence.",
            "What to say: Welcome to Module: Loop Engineering. You already build agents with "
            "LangChain and LangGraph, so we skip the basics. Today you learn to design a "
            "text-to-SQL agent for your own warehouse and to run it safely in production. We do "
            "it with four loops around one agent: the loop that answers, the loop that checks, "
            "the loop that runs on events, and the loop that improves from evidence. Every demo "
            "you see runs live against the real model, and every number on a slide comes from a "
            "measured run or a listed source.",
            "The point to land: The agent is the easy part; the loops around it decide whether "
            "you can trust it.",
            "Example: DataPilot, the course's data agent, answers questions about a fictional "
            "outdoor retailer's warehouse in plain words.",
            'Ask the room: "Who runs an agent in production today?" Expect: a few hands; most '
            "run prototypes.",
            "Misconceptions: That this is a course about one framework. The loops transfer to any "
            "agent whose output you can check.",
            "Transition: First, who is teaching today.",
        ],
    ),
    # 2 title: the instructor -------------------------------------------------------------------
    dict(
        kind="title",
        block="opening",
        title="Your instructor",
        minutes=0.5,
        says="Who is teaching, and where questions go",
        src="-",
        on_slide=[
            "Your instructor",
            "[INSTRUCTOR NAME]",
            "Questions go in the class chat at any time",
        ],
        notes=[
            "Purpose: Introduce the instructor and set where questions go.",
            "What to say: Introduce yourself in two sentences: what you build, and one loop that "
            "saved or cost you in production. The course owner fills in the name in square "
            "brackets before class. Ask in the chat at any time. When a question needs more than "
            "a minute, I park it for the Thursday review session, which answers every parked "
            "question in writing.",
            "The point to land: Ask early in the chat; nothing is too small.",
            "Example: A loop that saved you, such as a retry cap that stopped a runaway bill.",
            'Ask the room: "Post one line: which agent do you run, and what stops it when it is '
            'wrong?" Expect: a person reads the output, or nothing.',
            "Misconceptions: That questions wait until the end. They go in the chat as they come.",
            "Transition: Here is the plan for the four hours.",
        ],
    ),
    # 3 agenda ----------------------------------------------------------------------------------
    dict(
        kind="agenda",
        block="s1",
        title="Where we are: the agent loop",
        minutes=0.5,
        says="The class plan, Section 1 highlighted",
        src="docs/instructor-guide.md",
        on_slide=[
            "1. Opening: why agents fail in production",
            "2. Designing text-to-SQL (Structured Query Language)",
            "3. Section 1: Agent loop (now)",
            "4. Section 2: Verification loop",
            "5. Section 3: Event loop",
            "6. Section 4: Hill-climbing loop",
            "7. Closing: ten insights and your next steps",
        ],
        notes=[
            "Purpose: Show where Section 1 sits in the class and what it sets up.",
            "What to say: We have seen why agents fail and how a text-to-SQL system is designed. "
            "Now we build the first loop: the agent itself. Everything later depends on two "
            "things it does here: what its tools let it see, and the shape of the answer it "
            "returns. The verification loop can only check an answer that has a shape, and the "
            "hill-climbing loop can only improve rules the agent can use.",
            "The point to land: The agent loop decides what every later loop can check.",
            "Example: The progress tracker at the bottom of every slide shows the current loop in "
            "its colour.",
            'Ask the room: "Which of the four loops does your agent have today?" Expect: the '
            "agent loop only, sometimes a human check.",
            "Misconceptions: That the agent loop is the whole system. It is the first of four.",
            "Transition: Section 1 starts with the failure it fixes.",
        ],
    ),
    # 4 section opener --------------------------------------------------------------------------
    dict(
        kind="opener",
        block="s1",
        title="Section 1: Agent loop",
        minutes=0.5,
        says="The agent loop fixes answers built on what the agent cannot see",
        src="section-1-agent-loop/README.md",
        on_slide=[
            "Fixes: a confident answer built on rules the schema never shows",
            "Insight: A wrong number looks like a right one: 0 of 99 trap runs passed.",
        ],
        notes=[
            "Purpose: Open Section 1 and name the one failure it addresses.",
            "What to say: Section 1 is the agent loop: one analyst agent, four tools, and hard "
            "stops on every run. The failure it addresses is the one this whole class "
            "starts from: the agent answers with confidence, and the number rests on rules the "
            "schema never shows. The insight on the band is the section's opening fact: under the "
            "starting knowledge, 0 of 99 trap runs passed in calibration, and the next slide shows "
            "how ordinary one of those wrong answers looks. Watch for two things in this section: what "
            "the tools let the "
            "agent see, and what the answer gives you to check.",
            "The point to land: The agent can only use what its tools show it.",
            "Example: The fiscal year starts in February, and no column says so.",
            'Ask the room: "Where do your business rules live today?" Expect: in people\'s heads, '
            "a wiki, or old queries.",
            "Misconceptions: That a schema describes the business. It describes the storage.",
            "Transition: Here is the failure, from a real run.",
        ],
    ),
    # 5 problem story: the worked example of the specification ---------------------------------
    dict(
        kind="story",
        block="s1",
        title="The agent answered. The answer was wrong.",
        minutes=3,
        says="A fluent answer to the fiscal year 2025 revenue question misses three traps",
        src="docs/images/agent-confident-wrong-answer-sql.png (run 9182df01); "
        "docs/evidence/section-1-agent-loop.md; docs/calibration-report.md, Traps",
        on_slide=[
            '"What was our net revenue in fiscal year 2025?"',
            "Value: The agent answered | $72,394,572.08",
            "Value: The correct answer | $64,015,091.21",
            "1. Calendar dates, not the fiscal year",
            "2. Coordinated Universal Time, not Eastern time",
            "3. Internal accounts included",
            "Footer: 0 of 99 trap runs passed under the starting knowledge",
        ],
        code={
            "language": "sql",
            "origin": "the agent's query in run 9182df01, 25 October 2026, as the console showed "
            "it (docs/images/agent-confident-wrong-answer-sql.png), one clause per line",
            "lines": [
                "SELECT ROUND(SUM(subtotal_cents - discount_cents)",
                "             / 100.0, 2) AS net_revenue_usd",
                "FROM orders",
                "WHERE order_ts >= TIMESTAMPTZ '2025-01-01 00:00:00+00'",
                "  AND order_ts <  TIMESTAMPTZ '2026-01-01 00:00:00+00'",
                "  AND status = 4",
            ],
            "marks": [
                (3, "'2025-01-01", 1),
                (4, "'2026-01-01", 1),
                (3, "+00'", 2),
                # the second mark's disc goes on the second date line, beside the first's
                (4, "+00'", 2, True),
                (2, "FROM orders", 3),
            ],
        },
        notes=[
            "Purpose: Show that a fluent, plausible answer can be wrong in ways the schema cannot "
            "reveal.",
            "What to say: This is a real run from this course. The question is the one that runs "
            "through the whole class: what was our net revenue in fiscal year 2025? The agent did "
            "everything a good agent does. It listed the tables, described them, wrote one clean "
            "query, and returned one number: 72,394,572.08 dollars. The correct answer is "
            "64,015,091.21. Look at the query. Marker one: it uses calendar dates, January to "
            "December 2025. Our fiscal year runs February to January and is named for the year it "
            "ends, so fiscal year 2025 ended on 31 January 2025. Marker two: the plus zero zero on "
            "both bounds means Coordinated Universal Time, while business days are in Eastern "
            "time, so evening orders land on the wrong day. Marker three: it reads every order, "
            "including staff and test accounts, which are known only by their email domain. Each "
            "trap lives in business knowledge, not in the data. And notice what did not happen: "
            "no error, no exception, no warning. The run looked clean. Under the starting "
            "knowledge, 0 of 99 trap runs passed in calibration.",
            "The point to land: The dangerous agent failure is not a crash; it is a confident "
            "number that is wrong.",
            "Example: The same question in an earlier calibration run came back as 76,981,355.95 "
            "dollars with four traps hit: the wrong value changes, the failure does not.",
            'Ask the room: "How would your current stack have caught this?" Expect: tests on the '
            "SQL, a human review, or nothing; most say nothing.",
            'Misconceptions: "A better model fixes this." It does not: the rules are not in the '
            "data, so no model can read them there.",
            "Transition: So how does the agent see a warehouse at all? That is the agent loop.",
        ],
    ),
    # 6 concept diagram -------------------------------------------------------------------------
    dict(
        kind="concept",
        block="s1",
        title="The agent loop: one agent, four tools",
        minutes=4,
        says="The analyst sees the warehouse only through its tools, inside hard stops per run",
        src="section-1-agent-loop/diagrams/agent-loop.excalidraw; pack.yaml limits",
        figure={
            "diagram": "agent-loop",
            "alt": "A question goes to the analyst agent, which calls list_tables, describe_table, "
            "run_query, and scout_schema; every query passes the checker, graders then the "
            "read-only executor, and at most 50 rows come back with the total count; the schema "
            "scout has no run_query; stops every run at 12 model calls, 16 tool calls, and 60,000 "
            "tokens; the agent returns the answer envelope",
        },
        on_slide=[],
        notes=[
            "Purpose: Give the mental model of the agent loop in one picture, before any code.",
            "What to say: The idea of this slide: the agent sees the warehouse only through its "
            "tools. Let me walk the diagram from left to right. A question arrives on the "
            "left and goes to the analyst agent, the large oval. Above it, the prompt it gets on "
            "every model call carries the business date and the active knowledge version. On the "
            "right are its four tools: list tables, describe a table, run a query, and ask the "
            "schema scout. Those tools are the only way it sees the warehouse; if a tool does not "
            "show a fact, the agent does not have it. Every query goes through the checker before "
            "it touches data, graders and then a read-only executor, and at most 50 rows come "
            "back with the total count. Bottom right, the schema scout is a second agent inside "
            "its own tool boundary: it can list and describe tables, and it has no tool to run a "
            "query. Bottom left are the stops for every run: 12 model calls, 16 tool calls, and "
            "60,000 tokens, set in configuration rather than in the prompt. At the bottom is what "
            "comes back: an answer envelope with a status, the query, the rows, the answer, and "
            "the assumptions. That envelope is what the next three loops check, route, and "
            "improve.",
            "The point to land: Design the tools and the answer shape first; the prompt comes "
            "last.",
            "Example: With column names only, a status column shows a number; with its distinct "
            "values, the agent sees a handful of codes and can ask what they mean.",
            'Ask the room: "Which of these stops does your agent have?" Expect: a timeout, '
            "rarely a token budget.",
            "Misconceptions: That stops belong in the prompt. A prompt asks; a limit in the "
            "middleware stops the run.",
            "Transition: Here is how one of those tools keeps the context small.",
        ],
    ),
    # 7 mechanism -------------------------------------------------------------------------------
    dict(
        kind="mechanism",
        block="s1",
        title="Cap rows in the tool, not in the prompt",
        minutes=4,
        says="The query tool returns at most 50 rows, the total count, and a notice",
        src="platform/src/datapilot/loop1_agent/tools.py lines 39-48; pack.yaml limits.row_cap",
        code={
            "language": "python",
            "origin": "platform/src/datapilot/loop1_agent/tools.py lines 39-48 (lines 41-44 "
            "left out; line 48 wrapped after its list)",
            "lines": [
                "def format_result(result: QueryResult, row_cap: int) -> str:",
                "    rows, truncated = cap_rows(list(result.rows), row_cap)",
                "    ...",
                '        "total_row_count": result.total_row_count,',
                '        "truncated": truncated,',
                "    }",
                '    notices = [f"Showing {len(rows)} of {result.total_row_count} rows."]',
                "               if truncated else []",
            ],
            "marks": [
                (1, "cap_rows(list(result.rows), row_cap)", 1),
                (3, '"total_row_count"', 2),
                (6, "notices", 3),
            ],
        },
        on_slide=[
            "Idea: the tool decides how much reaches the model",
            "1. At most 50 rows go back to the model",
            "2. The total count still goes back",
            "3. A notice says rows were cut",
        ],
        notes=[
            "Purpose: Show the real code that bounds what a tool returns, and why it sits in the "
            "tool.",
            "What to say: This is the function that formats every query result before it goes "
            "back to the model. Marker one: the rows are capped right here, in the tool. The cap "
            "is 50 rows, set in the pack's limits, not in the prompt. Every row a tool returns "
            "stays in the conversation and is sent again on every later model call, so one large "
            "result is paid for many times. Marker two: the total row count still goes back, so "
            "the agent knows what it did not see. Without the count, a capped list looks like a "
            "complete one. Marker three: when rows were cut, a notice says so, and the agent "
            "learns to aggregate or narrow the query instead of asking for everything. The "
            "trade-off is real: a cap can hide rows a question needs, which is exactly why the "
            "count and the notice travel with it. In the demo, the planted bug removes this cap "
            "and you will watch the token counter.",
            "The point to land: A budget in a prompt is a hope; a budget in a tool is a fact.",
            "Example: With the cap removed, a 10,000-row result used 182,654 tokens and hit the "
            "run budget; with the cap, 30,216 tokens, the reviewer's round trip included.",
            'Ask the room: "Which of your tools can return an unbounded list?" Expect: search, '
            "list, and query tools.",
            "Misconceptions: That a bigger context window removes the need for a cap. Every token "
            "is re-sent and paid for on every later call.",
            "Transition: Time to see the loop run live.",
        ],
    ),
    # 8 demo ------------------------------------------------------------------------------------
    dict(
        kind="demo",
        block="s1",
        title="Live: the simple question, then the wrong answer",
        minutes=14,
        says="The simple question, then the confident wrong answer, live",
        src="platform/demos/registry.yaml",
        on_slide=[
            "Badge: DEMO - 1",
            "What to watch for:",
            "- Each tool call on the timeline",
            "- One clean query, one envelope",
            "- The gold check: no match",
            "Guaranteed moment: a confident, wrong answer to the fiscal year 2025 revenue "
            "question, exposed by the gold check.",
            "Link: Demo page on GitHub | https://github.com/ANI-IN/loop-engineering/tree/main/"
            "section-1-agent-loop/demo#the-confident-wrong-answer",
        ],
        notes=[
            "Purpose: Run the agent loop live: one correct answer, then a confident wrong one "
            "that only the gold check exposes.",
            "What to say: Two demos, both live against the class model. First the simple "
            "question, so you see the loop work end to end: list the tables, describe one, run "
            "one query, return an envelope. Then the fiscal year 2025 revenue question, under "
            "the starting knowledge, which has almost no business rules. Watch the timeline on "
            "the left and the gold check at the bottom. The wrong value changes from run to run; "
            "the failure does not. Keep the console on the Agent page throughout, and read each "
            "number aloud as it appears.",
            "Demo: The simple question.",
            "Command: make demo NAME=agent-simple-question, or Agent > Ask in the console.",
            "Point at: the tool timeline as each call appears, then the one-line query, then the "
            "answer and its token count.",
            "Expected output: posted, 405,738 orders, about 5,100 tokens, in 14 to 16 seconds in "
            "the recorded runs.",
            "While it runs: say that the agent chose these tools itself; nothing here is scripted.",
            "If it fails: reset with make reset NAME=agent-loop and run it again; a missing trace "
            "link is not a failure, the run still counts.",
            "Backup screenshot: docs/images/agent-simple-question-answer.png, the posted answer "
            "with its three tool calls.",
            "Demo: The confident wrong answer.",
            "Command: make demo NAME=agent-confident-wrong-answer, or the console's button for "
            "the fiscal year 2025 revenue question on the Agent page.",
            "Point at: the annotated query and its trap notes, then the answer against gold.",
            "Expected output: a mismatch against 64,015,091.21 dollars with one or more trap "
            "notes; recorded runs gave 72,394,572.08 and 76,981,355.95.",
            "While it runs: ask the room to predict which traps the query will hit.",
            "If it fails: if no number comes back there is no gold check; reset with make reset "
            "NAME=agent-loop and ask again; if a reviewer concern holds it, leave it held.",
            "Backup screenshot: docs/images/agent-confident-wrong-answer-sql.png, the query with "
            "three trap notes and the mismatch.",
            "The point to land: A clean run and a correct answer are different things; only the "
            "gold check told them apart.",
            "Example: Run 9182df01 answered 72,394,572.08 dollars with three trap notes.",
            'Ask the room: "What in the envelope would let a reviewer catch this?" Expect: the '
            "SQL and the stated assumptions.",
            "Misconceptions: That the demo was set up to fail. The model chose every query; the "
            "rules are simply not in the data.",
            "Transition: One run is a story; here is the measurement.",
        ],
    ),
    # 9 evidence --------------------------------------------------------------------------------
    dict(
        kind="evidence",
        block="s1",
        title="What the agent loop's tools are worth",
        minutes=3,
        says="Full descriptions, capped rows, and the scout: 17 of 21 correct against 12 of 21",
        src="docs/benefits.md, Section 1: Agent loop",
        chart={
            "type": "column",
            "title": "Seven questions without traps, asked 3 times on each side",
            "categories": ["Answered correctly", "Wrong answers that went out"],
            "series": [("Without the tools", [12, 9]), ("With the tools", [17, 4])],
            "x_label": "Outcome of each run",
            "y_label": "Runs, out of 21",
            "maximum": 21,
        },
        on_slide=[
            "Sample: 21 runs per side, gpt-6-luna, 24 October 2026",
            "Without: column names only, unbounded rows, no scout",
            "With: full descriptions, capped rows, the scout",
            "Tokens per run: 3,738 without, 4,857 with",
        ],
        notes=[
            "Purpose: Show what the agent loop's tool design measured, with the sample size, and "
            "what it cost.",
            "What to say: This is the paired measurement from the live runs of 24 October. Seven "
            "questions without traps, each asked three times on each side, so 21 runs per side, "
            "with the reviewer off on both sides. Without means the tools showed column names "
            "only, results were not capped, and there was no schema scout. With means full "
            "column descriptions, capped rows, and the scout. Read the chart left to right: 12 "
            "of 21 runs correct without, 17 of 21 with. Wrong answers that went out fell from 9 "
            "to 4. The cost was more tokens per run, 3,738 against 4,857, yet the 21 runs cost "
            "less in dollars with the tools, 0.0083 against 0.0097. Two cautions. This row mixes "
            "three changes, so it tells you what happened, not which change did it. And 21 runs "
            "per side is a small sample: treat it as a direction, not a rate. The earlier, "
            "smaller measurement of 23 October agreed in direction: 6 of 7 against 4 of 7.",
            "The point to land: Better tools made more answers right on easy questions, and they "
            "did nothing for the traps.",
            "Example: The fiscal year 2025 revenue question still failed with every tool on.",
            'Ask the room: "Which of the three changes would you test first, alone?" Expect: the '
            "column descriptions.",
            "Misconceptions: That 17 of 21 is an accuracy rate. It is one session's count on "
            "seven questions.",
            "Transition: Tools help on easy questions. What about checking the hard ones? That is "
            "the verification loop.",
        ],
    ),
    # 10 insight with a cropped screenshot ------------------------------------------------------
    dict(
        kind="insight",
        block="s2",
        title="Every grader passed. The answer was still wrong.",
        minutes=3,
        says="Checks that cannot see the business rules pass a wrong number",
        src="docs/images/verify-graders-pass-still-wrong-checklist.png (run ccfd37fb); "
        "docs/benefits.md, Section 2: Verification loop",
        image={
            "path": "docs/images/verify-graders-pass-still-wrong-checklist.png",
            "alt": "The checklist of attempt 2 of 3: seven graders passed, from parse to final "
            "answer",
            "crop": (0.065, 0.5884, 0.685, 0.0667),
            "callouts": [(0.78, 0.062, 1), (0.70, 0.948, 2)],
        },
        on_slide=[
            "Insight: Checks that cannot see the business rules pass a wrong number.",
            "Evidence: 20 trap questions, 40 runs: the layer made 0 correct.",
            "1. Seven graders passed, attempt 2 of 3",
            "2. Final answer passed too",
        ],
        notes=[
            "Purpose: Land the section's opening insight: passing checks is not being right.",
            "What to say: This is the Verify page from a live run. Marker one: the checklist of "
            "attempt 2 of 3. Every grader passed: one statement, the statement policy, the schema "
            "allowlist, the cost threshold, the read-only role, personal data routing, and the "
            "final answer. Marker two: the final answer passed too. And the answer was "
            "72,394,572.08 dollars against a gold answer of 64,015,091.21, a mismatch on both "
            "databases. The graders check that the SQL is safe and well formed; none of them "
            "knows the fiscal year starts in February. Now the measurement behind the insight: "
            "on 20 trap questions from the development split, asked twice on each side, the full "
            "verification layer made 0 of 40 answers correct, against 0 of 40 without it. What "
            "it did change is how many wrong answers got through unflagged: 19 instead of 39, "
            "because 20 were held or escalated. The reviewer approved the other 19, because it "
            "shares the analyst's knowledge.",
            "The point to land: Verification catches unsafe and malformed answers; only business "
            "knowledge makes a wrong number right.",
            "Example: In this run the reviewer raised a concern about the fiscal year and held "
            "the run for a person.",
            'Ask the room: "Which of your checks would know your fiscal calendar?" Expect: none, '
            "or a hand-written test.",
            "Misconceptions: That a green checklist means a correct answer. It means a safe, "
            "well-formed one.",
            "Transition: Here are the numbers side by side.",
        ],
    ),
    # 11 without-and-with comparison ------------------------------------------------------------
    dict(
        kind="comparison",
        block="s2",
        title="The verification layer: what it caught, what it cost",
        minutes=3,
        says="The layer flagged 20 wrong answers instead of 1, at about twice the tokens",
        src="docs/benefits.md, Section 2: Verification loop",
        on_slide=[
            "| 20 trap questions, 40 runs per side | Without the layer | With the layer |",
            "|---|---|---|",
            "| Runs answered correctly | 0 of 40 | 0 of 40 |",
            "| Wrong answers held or escalated | 1 | 20 |",
            "| Wrong answers out, unflagged | 39 | 19 |",
            "| Tokens per run, on average | 9,311 | 17,344 |",
            "Insight: The layer stops wrong answers going out; it does not correct them.",
        ],
        notes=[
            "Purpose: Show the measured trade-off of the verification layer: what it caught and "
            "what it cost.",
            "What to say: Same 20 trap questions, each asked twice on each side, 40 runs per "
            "side, all under the starting knowledge. Without means the naive guard and no "
            "reviewer. With means the full layer: the syntax-tree guard, the graders, and the "
            "reviewer. Read the table top to bottom. Correct answers: zero on both sides. That "
            "is the honest headline. Wrong answers held for a person or escalated: 1 without, 20 "
            "with. Wrong answers that went out with no flag: 39 without, 19 with. The price is "
            "on the last row: 17,344 tokens per run against 9,311, because the layer retries and "
            "the reviewer reads every answer. In dollars, the 40 runs cost 0.0605 against "
            "0.0361. So you pay roughly twice the tokens to stop about half the wrong answers "
            "from going out unflagged. Whether that is worth it depends on what a wrong number "
            "costs you; for a board deck, it usually is.",
            "The point to land: Measure what a check catches and what it costs, on the same "
            "questions, before you keep it.",
            "Example: The reviewer approved 19 wrong answers because, like the analyst, it had no "
            "rule for the fiscal year.",
            'Ask the room: "What does one wrong number cost in your business?" Expect: a '
            "decision made on it, a retraction, lost trust.",
            "Misconceptions: That a second agent is an independent check. It shares the first "
            "agent's knowledge and blind spots.",
            "Transition: So where do the checks go in a text-to-SQL design?",
        ],
    ),
    # 12 design callout -------------------------------------------------------------------------
    dict(
        kind="design_callout",
        block="s2",
        title="Validate generated queries before and after they run",
        minutes=3,
        says="Checks before execution, at execution, and after it, with the gold check last",
        src="section-2-verification-loop/README.md; docs/benefits.md",
        on_slide=[
            "Decision: where do you check a generated query?",
            "| Before it runs | While it runs | After it runs |",
            "|---|---|---|",
            "| Parse: one statement, allowed tables | Read-only role and transaction | Graders on "
            "the result |",
            "| Cost estimate before execution | Statement timeout, row cap | Gold check on two "
            "databases[^8] |",
            "DataPilot: all three stages; a person approves what the reviewer doubts.",
        ],
        notes=[
            "Purpose: Turn the verification loop into a design decision for the learner's own "
            "text-to-SQL system.",
            "What to say: When you design text-to-SQL, the question is not whether to validate, "
            "but where. Read the table by column. Before the query runs: parse it into a syntax "
            "tree, allow exactly one statement and only the tables you list, and estimate its "
            "cost from the plan so a join with no join condition is refused before it starts. "
            "While it runs: the database itself is the last line, with a read-only role, a "
            "read-only transaction, a statement timeout, and a cap on the rows that come back. "
            "After it runs: graders check the result's shape, and in evaluation a gold check "
            "compares the result with a hand-written answer on two databases. Why two? A wrong "
            "query can match the right result on one database by accident; research on test "
            "suites for text-to-SQL evaluation, Source 8, shows that checking on more than one "
            "database catches those false matches. DataPilot uses all three stages, and a "
            "person approves any answer the reviewer doubts.",
            "The point to land: Put a check at each stage; the database is the last line, not "
            "the only one.",
            "Example: With the naive guard, the read-only transaction and the role's grants still "
            "refused every write in the malicious query demo.",
            'Ask the room: "Which stage does your system check today?" Expect: before it runs, '
            "with a regular expression.",
            "Misconceptions: That a regular expression on the query text is a guard. Parse it; "
            "text tricks pass pattern checks.",
            "Transition: What do you do with this next week?",
        ],
    ),
    # 13 apply-it checklist ---------------------------------------------------------------------
    dict(
        kind="checklist",
        block="s1",
        title="Apply it: audit your agent's view this week",
        minutes=2,
        says="Five things to do on your own agent next week",
        src="section-1-agent-loop/README.md",
        on_slide=[
            "- List what each tool returns for one real table",
            "- Cap every list tool: rows, total count, a notice",
            "- Return an envelope: status, query, rows, assumptions",
            "- Set stops per run: model calls, tool calls, tokens",
            "- Ask five questions whose rules live in people's heads",
        ],
        notes=[
            "Purpose: Give five concrete actions a learner can take on their own agent next week.",
            "What to say: Five things for next week, each about an hour. One: pick one real table "
            "and print exactly what each of your tools returns for it. Is the field your agent "
            "needs visible, typed, and shown with examples? Two: give every tool that returns a "
            "list a row cap, the total count, and a notice when rows were cut. Three: have the "
            "agent return a structured envelope, not prose: a status, the final query, the rows, "
            "and the assumptions it made. Without it, nothing later can check the answer. Four: "
            "set hard stops for every run in your middleware: model calls, tool calls, and "
            "tokens. Five: write down five questions whose rules live only in people's heads, "
            "like your fiscal calendar, and compare your agent's answers with answers a person "
            "checked by hand. That last one is the start of the gold question set you build in "
            "Section 4: Hill-climbing loop.",
            "The point to land: Fix what the agent can see before you tune what it says.",
            "Example: Our five planted traps are exactly such questions: the fiscal year, net "
            "revenue, cancelled orders, Eastern time, and internal accounts.",
            'Ask the room: "Which item would take you longest?" Expect: the hand-checked answers.',
            "Misconceptions: That this needs a new framework. Each item is a change to tools you "
            "already have.",
            "Transition: Before we move on, the mistakes teams repeat here.",
        ],
    ),
    # 14 pitfalls -------------------------------------------------------------------------------
    dict(
        kind="pitfalls",
        block="s3",
        title="Event loop pitfalls that post twice or never stop",
        minutes=3,
        says="Three event-loop mistakes, what each did in our runs, and the fix",
        src="docs/benefits.md, Section 3: Event loop",
        on_slide=[
            "| Pitfall | What happened without the fix | Do instead |",
            "|---|---|---|",
            "| Retrying without a key | One event three times: 3 answers, 2 digests | A unique "
            "key: one run per event |",
            "| Approval kept in memory | A restart lost it; the run failed | Store the pending "
            "approval in the database |",
            "| A stop checked only at the start | An answer posted after the switch | Check the "
            "switch before posting |",
        ],
        notes=[
            "Purpose: Name the three event-loop mistakes that cost the most, each with what it did "
            "in our runs.",
            "What to say: Three pitfalls, each measured with one run of each half. First, "
            "retrying without an idempotency key. Webhooks are delivered at least once, so the "
            "same event arrives again. Without a key, the same event sent three times gave three "
            "answers and two digests. With a unique key, one answer, two duplicates absorbed, one "
            "digest. Second, keeping a pending approval in memory. A worker restart is routine, "
            "and without the fix the approval was lost and the run failed after a person "
            "approved it. Stored in the database, the run was still held after the restart and "
            "posted after approval. Third, a kill switch checked only when a job starts. Without "
            "the in-flight check, an answer posted after the switch was engaged. With it, the "
            "running job stopped. Each fix is a few lines; each failure is the kind you find in "
            "production at the worst possible time, on a busy day.",
            "The point to land: Assume every event arrives twice, every worker restarts, and "
            "every stop must reach running work.",
            "Example: The kill switch demo engages the switch while a run is in flight.",
            'Ask the room: "Which of these has bitten you?" Expect: duplicates from retries.',
            "Misconceptions: That exactly-once delivery solves duplicates. Design for at least "
            "once, and keep handling idempotent.",
            "Transition: Let me check what stuck.",
        ],
    ),
    # 15 recap and question ---------------------------------------------------------------------
    dict(
        kind="recap",
        block="s4",
        title="Recap: the hill-climbing loop",
        minutes=2,
        says="Three points to keep, and one question to check understanding",
        src="section-4-hill-climbing-loop/README.md; docs/benefits.md",
        on_slide=[
            "- Agents propose rules; code and a person decide",
            "- Decide on a holdout split the analyzer never sees",
            "- Promote only with zero regressions",
            "Question: The naive analyzer's rules quote the development questions. Which gate "
            "condition stops them, even when no regression appears?",
        ],
        notes=[
            "Purpose: Consolidate the hill-climbing loop and check one idea with a question.",
            "What to say: Three points to keep. First, agents propose and code decides: the "
            "analyzer team writes rules, the overfit guard and the promotion gate judge them, and "
            "a person approves. Second, the gate decides on the 15 holdout items, which the "
            "analyzer team never sees. Third, a version is promoted only with zero regressions. "
            "Now the question on the slide; give the room thirty seconds. The answer: every new "
            "rule must pass the overfit guard, and a rule that quotes a development question "
            "fails it. In this course's runs, the naive analyzer wrote 21 such rules, the guard "
            "rejected every one, and the gate blocked the version.",
            "The point to land: A rule that quotes the test is not knowledge; the gate checks for "
            "it in code.",
            "Example: Version 11 passed 13 of 15 holdout items against 2 of 15 for the starting "
            "version, with 0 regressions.",
            "Ask the room: the question on the slide. Expect: the overfit guard; some will say "
            "the holdout score, which is the second line of defence.",
            "Misconceptions: That a higher score is enough to promote. The gate has four "
            "conditions: holdout, regressions, the overfit guard, and human approval.",
            "Transition: Questions before the poll?",
        ],
    ),
    # 16 poll -----------------------------------------------------------------------------------
    dict(
        kind="poll",
        block="poll",
        title="Live Zoom Poll",
        minutes=5,
        says="We are launching a poll on Zoom. Please take 2 minutes to fill out the form.",
        src="docs/instructor-guide.md",
        on_slide=[
            "Live Zoom Poll",
            "We are launching a poll on Zoom. Please take 2 minutes to fill out the form.",
        ],
        notes=[
            "Purpose: Ask which autonomy level learners would grant, before Section 4 shows what "
            "evidence each level should need.",
            'What to say: Launch the poll: "Which autonomy level would you grant the revenue '
            'digest today, and why?" The options are the report-only level, the assisted level, '
            "and the unattended level. Read the result aloud and keep it for Section 4.",
            "Do: Before you launch the poll, start the baseline experiment on the Improve page so "
            "it runs through the break.",
            "Transition: A 10-minute break; the baseline keeps running.",
        ],
    ),
    # 17 break ----------------------------------------------------------------------------------
    dict(
        kind="break",
        block="break1",
        title="Time for a Break",
        minutes=10,
        says="A 10-minute break is starting now. Please return when the timer ends to continue "
        "the presentation",
        src="-",
        on_slide=[
            "Time for a Break",
            "A 10-minute break is starting now. Please return when the timer ends to continue "
            "the presentation",
        ],
        notes=[
            "Purpose: Give a 10-minute break and set the return time.",
            "What to say: Write the return time in the chat and say it once. Stay near the "
            "machine so you can see the stack is ready for the next section.",
            "Do: During the break, reset the event loop section so Section 3 starts clean.",
            "Transition: Welcome back. Answers are now checked; next, who asks, when, and who may "
            "approve.",
        ],
    ),
    # 18 closing --------------------------------------------------------------------------------
    dict(
        kind="closing",
        block="closing",
        title="Ten insights to take away",
        minutes=3,
        says="Ten evidenced insights, each linked to the section that proves it",
        src="docs/benefits.md; docs/calibration-report.md",
        on_slide=[
            "1. A wrong number looks right: 0 of 99 trap runs passed | Section 1",
            "2. Tools decide what the agent sees: 17 of 21 correct against 12 | Section 1",
            "3. Cap rows in the tool: 182,654 tokens uncapped, 30,216 capped | Section 1",
            "4. Every grader can pass a wrong answer; only gold catches it | Section 2",
            "5. A reviewer with the same knowledge approved 19 wrong answers | Section 2",
            "6. The database is the last guard: its grants refused every write | Section 2",
            "7. A unique key turns one event sent 3 times into 1 answer | Section 3",
            "8. A stop must reach running work, or answers post after it | Section 3",
            "9. Earned rules lifted holdout passes from 2 of 15 to 13 of 15 | Section 4",
            "10. The gate blocked all 21 rules that quoted the test | Section 4",
        ],
        notes=[
            "Purpose: Leave learners with ten evidenced insights, each tied to the section that "
            "proved it.",
            "What to say: Ten insights, and each one came from a measured run today, not from a "
            "blog post. Read them with me, two per breath. The first three are about the agent "
            "loop: a wrong number looks exactly like a right one, tools decide what the agent "
            "sees, and caps belong in the tool. The next three are verification: green graders "
            "can pass a wrong answer, a reviewer that shares the analyst's knowledge shares its "
            "blind spots, and the database is the last guard. Then the event loop: one event, one "
            "run, and a stop that reaches running work. And the hill-climbing loop: rules earned "
            "on held-out questions, and a gate that refuses rules that quote the test. If you "
            "remember one, remember the first: the failure to design against is the confident "
            "wrong number.",
            "The point to land: Every insight here was measured; build the measurement into your "
            "own system first.",
            "Example: Insight 9: version 11 of the knowledge passed 13 of 15 holdout items, "
            "against 2 of 15 for the starting version.",
            'Ask the room: "Which one would change your design next week?" Expect: the gold '
            "check, or the unique key.",
            "Misconceptions: That these numbers are rates. Each one is a count from this course's "
            "runs, with its sample size on the slide that proved it.",
            "Transition: Every source behind these slides is on the last page.",
        ],
    ),
    # 19 sources --------------------------------------------------------------------------------
    dict(
        kind="sources",
        block="closing",
        title="Sources",
        minutes=1,
        says="Every external source and the course's own evidence, numbered as the markers",
        src="slides/source/sources.py",
        on_slide=[
            "Group: Text-to-Structured Query Language (SQL) research and benchmarks",
            "[3] Spider 2.0: Evaluating Language Models on Real-World Enterprise Text-to-SQL "
            "Workflows, Fangyu Lei and others, 2024, https://arxiv.org/abs/2411.07763",
            "[4] LinkAlign: Scalable Schema Linking for Real-World Large-Scale Multi-Database "
            "Text-to-SQL, Yihan Wang and others, 2025, https://arxiv.org/html/2503.18596v3",
            "[8] Semantic Evaluation for Text-to-SQL with Distilled Test Suites, Ruiqi Zhong and "
            "others, 2020, https://arxiv.org/abs/2010.02840",
            "Group: Event-driven systems",
            "[15] You don't need a job queue: Postgres already has SKIP LOCKED, Prisma, 2026, "
            "https://www.prisma.io/blog/you-dont-need-a-job-queue-postgres-already-has-skip-locked",
            "[16] LangChain human-in-the-loop, LangChain, documentation, "
            "https://docs.langchain.com/oss/python/langchain/human-in-the-loop",
            "Group: The course's own evidence",
            "[24] Calibration report, Loop Engineering, 2026, https://github.com/ANI-IN/"
            "loop-engineering/blob/main/docs/calibration-report.md",
            "[25] What each loop is worth: paired live measurements, Loop Engineering, 2026, "
            "https://github.com/ANI-IN/loop-engineering/blob/main/docs/benefits.md",
        ],
        notes=[
            "Purpose: List every source the slides and notes rely on, numbered as the markers on "
            "the slides.",
            "What to say: Every marker you saw on a slide, a small number in square brackets, "
            "points to an entry here. They are grouped by topic: research and benchmarks, "
            "event-driven systems, and the course's own evidence. The course's evidence pages "
            "hold every run behind every number. The same list is on the sources page of the "
            "course repository, with working links.",
            "The point to land: Every claim in this deck traces to a source or a recorded run.",
            "Example: Marker 8 on the design callout points to the test-suite research on "
            "checking queries on more than one database.",
            'Ask the room: "Which source would you read first?" Expect: Spider 2.0.',
            "Misconceptions: That the benchmarks measure your warehouse. They measure theirs; "
            "build your own gold questions.",
            "Transition: Thank you; the assignments are where you build each loop yourself.",
        ],
    ),
]
