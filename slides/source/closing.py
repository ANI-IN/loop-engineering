"""Closing block, 3:48-4:00, 12 minutes: the four loops together, ten insights, the design
checklist for text-to-SQL (Structured Query Language), Monday's checklist, the assignments and
the final project, and the sources.

Every course number comes from .dev/deck-evidence.md (entry ids in each slide's src); every
external claim names its source by the number of .dev/deck-sources.md, which sources.py holds.
"""

from sources import sources_slide

RULES = "design system"

SLIDES = [
    # 1 concept diagram: the four loops together ------------------------------------------------
    dict(
        kind="concept",
        title="The four loops together",
        minutes=1.5,
        says="One agent inside three loops: checked, run on events, and improved with evidence",
        src="docs/diagrams/four-loops.excalidraw; deck-evidence E11, E53",
        figure={
            "diagram": "four-loops",
            "alt": "The agent loop (the analyst agent and the schema scout) sits inside the "
            "verification loop (seven graders and the reviewer agent); the event loop's router "
            "and jobs table feed the analyst, and its answers are posted or held for a person "
            "after human approval, with a kill switch that stops every run; the hill-climbing "
            "loop's benchmark, analyzer team and promotion gate send the active knowledge "
            "version back to the analyst",
        },
        on_slide=[],
        notes=[
            "Purpose: Show the four loops as one system, and what each loop covers that the "
            "others cannot.",
            "What to say: The idea on this slide: One agent inside three loops: checked, run on events, improved with evidence. "
            "One agent sits in the middle, and three loops surround it: one checks every answer, "
            "one runs it from events with approvals and a stop, and one improves its knowledge "
            "behind a gate. The arrow along the bottom is the point: the active knowledge version "
            "goes back into the analyst, so the agent improves because its knowledge changed, "
            "after the gate and a person agreed. Now notice what each loop cannot do alone. The "
            "agent loop answers but cannot tell right from wrong. The verification loop flags a "
            "wrong number but cannot correct it. The event loop runs work safely but does not "
            "know whether the number is correct. Only the hill-climbing loop changes the answer, "
            "and only because the other three keep the work safe, bounded, and measurable while it "
            "learns from its failures.",
            "The point to land: Each loop fixes a failure the others cannot; the fiscal year "
            "2025 answer became right only with all four working together.",
            "Example: The fiscal year 2025 revenue question was confidently wrong in Section 1 "
            "and flagged but still wrong in Section 2. In Section 4 it arrived through Section "
            "3's event pipeline and came back as 64,015,091.21 dollars, matching gold, at the "
            "level its metric family had earned.",
            'Ask the room: "Which loop is missing from the agent you run today?" Expect: a '
            "check beyond a person glancing at the output, and almost always the hill-climbing "
            "loop.",
            "Misconceptions: That more autonomy comes from a better model. Here it came from "
            "knowledge the gate accepted, and from evidence earned one metric family at a time.",
            "Transition: Here is what the four loops taught us, as ten insights to take away.",
        ],
    ),
    # 2 closing: ten insights to take away -------------------------------------------------------
    dict(
        kind="closing",
        title="Ten insights to take away",
        minutes=2,
        says="Ten measured lessons, each linked to the section whose runs proved it",
        src="deck-evidence E16 (1), E24 (2), E24 and E27 (3), E25 (4), E33 to E35 and slide 42 "
        "(5, 17 of 17), E37 (6), E45 (7), E46 and E40 (8), E42 and E54 (9), E51 (10, slide 64)",
        on_slide=[
            "1. Cap rows in the tool: uncapped, 182,654 to 187,030 tokens | Section 1",
            "2. Without checks, 39 of 40 wrong answers went unflagged | Section 2",
            "3. Same knowledge, same blind spot: 19 of 40 wrong approved | Section 2",
            "4. Checks: 8,000 tokens a run, 19 more of 40 wrong flagged | Section 2",
            "5. Force each failure: planted bugs failed 17 of 17 | Section 3",
            "6. A row cap is not a size cap: one row, 109,380 tokens | Section 3",
            "7. One improver run is a lottery: 2 to 12 of 15 | Section 4",
            "8. A holdout score can pass rules copied from the test: 15 of 15 | Section 4",
            "9. Same model, rules for the five traps: holdout 2, then 13 of 15 | Section 4",
            "10. Autonomy is earned per metric family: revenue 7 of 11 | Section 4",
        ],
        notes=[
            "Purpose: Leave learners with ten measured lessons, each tied to the section whose "
            "runs proved it.",
            "What to say: Ten insights, each from a run of this course; the colour of each "
            "number is the section that proved it. Section 1: a cap belongs in the tool, not in "
            "the prompt. Section 2: without checks, 39 of 40 wrong answers went out with no "
            "flag, because a wrong number looks exactly like a right one; the checks flag wrong "
            "answers without fixing them, 0 of 40 right either way; a reviewer that shares the "
            "analyst's knowledge shares its blind spot; and the whole layer's flags have a price, "
            "about 8,000 more tokens a run, from retries and the reviewer together, to flag 19 "
            "more of 40 wrong answers; holds on right answers were not measured. Section 3: around the model, a one-line bug breaks every time its trigger "
            "happens, so force each failure on purpose; and a row cap is not a size cap. Section "
            "4: one improver run is a lottery; a holdout score can pass rules copied from the "
            "test; with the same "
            "model, learned rules for the five traps lifted the holdout from 2 to 13 of 15 "
            "questions with 0 regressions; and autonomy is "
            "earned one metric family at a time.",
            "The point to land: Every insight here was measured; build the measurement into your "
            "own system before you trust the agent.",
            "Example: Insight 8: on 23 October a naive analyzer that copied the development "
            "questions and their gold queries into its rules passed 15 of 15 holdout questions, "
            "because the holdout tests the same five rules, and the three-condition gate said "
            "ready. The overfit guard was added as the fourth condition after that; the naive "
            "analyzer's later runs scored only 0 to 2 of 15, so the guard has not yet met a "
            "high-scoring copied version live. Insight 4: every one of the 40 answers on each "
            "side was wrong, so holds on right answers were not measured. Insight 10: revenue cleared the unattended level in 7 of 11 live "
            "promotions; orders never cleared.",
            'Ask the room: "Which one would change your design next week?" Expect: the gold '
            "check, forcing each failure, or two improver candidates.",
            "Misconceptions: That these counts are rates. Each is a count from this course's "
            "runs on one model and one warehouse, with its sample size on the slide that proved "
            "it.",
            "Transition: Now turn the insights into a design for your own warehouse.",
        ],
    ),
    # 3 closing: the text-to-SQL design checklist ------------------------------------------------
    dict(
        kind="closing",
        title="Designing text-to-SQL (Structured Query Language) for your warehouse",
        minutes=2,
        says="Ten design steps, each pointing to the part of the course that teaches it",
        src="docs/text-to-sql-design.md, The checklist (steps and Taught in); "
        "deck-evidence E5, E11, E12, E28; deck-sources [12], [13], [33], [36], [40], [43], [44], "
        "[45], [49]",
        on_slide=[
            "1. Inventory the business rules | Designing text-to-SQL",
            "2. Build a gold question set before the agent | Section 4: Hill-climbing loop",
            "3. Choose where each rule lives[^44] | Designing text-to-SQL",
            "4. Run each query read-only[^13], as the asker | Section 2: Verification loop",
            "5. Scope and describe tables; cap rows and values | Section 1: Agent loop",
            "6. Add value lookup | Assignment 1: Agent loop",
            "7. Validate every query before it runs | Section 2: Verification loop",
            "8. Assume, and ask when a term has no rule | Assignment 2: Verification loop",
            "9. Execution match, two databases, always | Section 4: Hill-climbing loop",
            "10. Start report-only; earn autonomy per family | Sections 3 and 4",
        ],
        notes=[
            "Purpose: Give learners the ten-step design checklist of the course page, each step "
            "tied to the part of the course that taught it.",
            "What to say: Ten steps, in the order a team would take them on a new warehouse. "
            "Inventory every business rule an answer depends on, with an owner. Build a gold "
            "question set with checked results, split into development and holdout, before you "
            "build the agent. Choose where each rule lives: a semantic layer or a view enforces a "
            "metric only if the agent's role can read nothing else. Run each query read-only, "
            "with the asker's own access, as Snowflake and Cube apply it, Sources 36 and 33. "
            "Scope and describe the tables, about five per agent, Source 44, and cap rows and "
            "values. Add value lookup. Validate every query before it runs. State your "
            "assumptions, and ask when a term has no rule. Measure execution match on two "
            "databases, Source 12, and re-run the benchmark on every change to the schema, a "
            "rule, or the data, and pin the dates in gold answers, as Snowflake warns, Source 40. "
            "Start every "
            "metric family at the report-only level, and let it earn autonomy.",
            "The point to land: Design the knowledge, the walls, and the measurement first; the "
            "prompt is the last thing you tune.",
            "Example: Each step's other course parts: step 1 also in Section 1: Agent loop, where "
            "the five traps fail; step 2 in Assignment 4: Hill-climbing loop; step 3 in Section "
            "4: Hill-climbing loop; step 7 in Assignment 2: Verification loop; step 8 in Section "
            "1: Agent loop; step 9 in Section 2: Verification loop, the gold check; step 10 in "
            "Section 3: Event loop and Section 4: Hill-climbing loop. The page adds an optional "
            "eleventh step: improve the rules from failures behind a gate, taught in Section 4: "
            "Hill-climbing loop and Assignment 4: Hill-climbing loop. Your second database is the "
            "same schema with different rows, a reseeded or masked copy; compare results "
            "ignoring row order, with a numeric tolerance, as Genie's benchmarks round to 4 "
            "significant digits, Source 43. Databricks keeps text instructions as a last resort, "
            "Source 44, and Uber had a person confirm the tables its agent picked, Source 49. "
            "DataPilot runs as one role, and approved rows also go to the model provider.",
            'Ask the room: "Which step does your system skip today?" Expect: the gold questions '
            "and the holdout split.",
            "Misconceptions: That a semantic-layer product removes steps 1 and 2. A product is "
            "where the rules live, not where they come from: the Databricks blog's agent "
            "answered 0 of 13 benchmark questions until its context was added, Source 45.",
            "Transition: The full checklist, with the decisions and pitfalls for each step, is on the course page Designing text-to-SQL for your own warehouse. Now, Monday morning.",
        ],
    ),
    # 4 apply-it checklist: use it on Monday ----------------------------------------------------
    dict(
        kind="checklist",
        title="Use it on Monday",
        minutes=1.5,
        says="Six actions for the learner's own agent, each under an hour",
        src="deck-evidence E7, E16, E28, E30, E33; section READMEs",
        on_slide=[
            "- Ask five questions whose rules live in people's heads; check answers by hand",
            "- Cap every list tool: rows, value length, total count, a notice",
            "- Try one write as your agent's database role; it must fail",
            "- Put stops in code: attempts, tool calls, tokens per run",
            "- Give every effect a unique key, so a retry posts nothing new",
            "- Write down which answers may go out without a person",
        ],
        notes=[
            "Purpose: Give six concrete actions a learner can take on their own agent on Monday.",
            "What to say: Six things for Monday, each under an hour. One: ask your agent five "
            "questions whose rules live only in people's heads, and compare its answers with "
            "hand-checked ones; they start your gold set. Two: cap every tool that returns a "
            "list: rows, the length of each value, the total count, and a notice. Three: connect as your agent's database "
            "role and try one write; if it succeeds, nothing else you built matters. Four: move "
            "every stop into code: attempts, tool calls, and tokens per run. Five: give every "
            "effect a unique key, so a retried webhook posts nothing new. Six: write down which "
            "answers may go out without a person reading them; that list is your report-only "
            "level, and it is the first thing your manager will ask for. If you do only one, do "
            "the first: the five questions show you, in an afternoon, whether your agent knows "
            "the rules your business runs on.",
            "The point to land: Start with five hand-checked questions; everything else in the "
            "course grows from them.",
            "Example: Our own five traps came from exactly this exercise: the fiscal year, net "
            "revenue, cancelled orders, Eastern time, and internal accounts. Under our starting "
            "knowledge, none of 99 trap-question runs passed; without our retry cap, runs went "
            "to 13 attempts. Where each was taught: one, the design segment and Section 4; two, "
            "Section 1; three, Section 2; four, Sections 1 and 2; five, Section 3; six, Sections "
            "3 and 4.",
            'Ask the room: "Which item would take you longest?" Expect: the hand-checked '
            "answers, then the database role, which often belongs to another team.",
            "Misconceptions: That these wait until the agent is finished. Each one is cheaper "
            "before production than after the first wrong number goes out.",
            "Transition: Now the practice: the four assignments and the final project.",
        ],
    ),
    # 5 closing: assignments and the final project ----------------------------------------------
    dict(
        kind="closing",
        title="Assignments, final project, and the Thursday review",
        minutes=1.5,
        says="Four assignments with live checks, the final project, the deadline and the solutions",
        src="section-1-agent-loop/assignment/README.md to section-4-hill-climbing-loop/"
        "assignment/README.md; final-project/README.md; docs/review-session.md; "
        "deck-evidence E61",
        on_slide=[
            "Deadline: in the class chat. Solutions: when the Thursday review starts.",
            "1. Assignment 1: Agent loop: a value lookup for informal product names | Section 1",
            "2. Assignment 2: Verification loop: clarify undefined terms; block leaks | Section 2",
            "3. Assignment 3: Event loop: a nightly revenue anomaly alert, keyed and stoppable | "
            "Section 3",
            "4. Assignment 4: Hill-climbing loop: a new metric family; at least three holdout "
            "questions per family | Section 4",
            "5. Final project: the four loops on your own data, with your own benchmark",
        ],
        notes=[
            "Purpose: Set up the practice: four assignments with live checks, the final project, "
            "the deadline, and when solutions appear.",
            "What to say: Four assignments, one per loop, each adding a capability the class "
            "code lacks. Assignment 1: a value lookup, so informal product names resolve to "
            "stored values and a tie becomes a question. Assignment 2: two graders, one that "
            "asks when a business term is undefined, one that blocks personal data unless a "
            "person approved it. Assignment 3: a nightly revenue anomaly alert, one per day by "
            "its key, that respects the kill switch. Assignment 4: a repeat-customer metric "
            "family, and a rule that a family needs at least three holdout questions before the "
            "unattended level. Each has a live check on your own OpenAI key, stopped at 1 "
            "dollar. The final project runs all four loops on your own data. The deadline is in "
            "the class chat; solutions are published when the Thursday review starts.",
            "The point to land: Each assignment builds one loop's missing capability yourself, "
            "checked live on the real model.",
            "Example: A typical full check of a working solution cost about 0.4 cents for "
            "Assignment 1, about 2 cents for Assignment 2, and 12.62 to 19.22 cents for a later "
            "check of Assignment 4, across 5 recorded checks; each check prints its estimate "
            "before it "
            "starts.",
            'Ask the room: "Which assignment matches a problem you have at work?" Expect: '
            "Assignment 1 for users' wording, or Assignment 2 for personal data.",
            "Misconceptions: That the checks grade you. Nobody grades the assignments: the "
            "rubric is for assessing your own work, and the check says which requirements pass "
            "live.",
            "Transition: Every source behind these slides is on the next four pages.",
        ],
    ),
    # 6 sources: the sources the deck cites, part 1 ---------------------------------------------
    dict(
        kind="sources",
        title="Sources: agent design",
        minutes=0.75,
        says="The agent design sources the deck cites, by number",
        src=".dev/deck-sources.md; slides/source/sources.py",
        on_slide=sources_slide(
            (
                "Agent design, with Structured Query Language (SQL) agents",
                (1, 2, 3, 4, 5, 8, 10, 54),
            )
        ),
        notes=[
            "Purpose: List the agent design sources the deck cites, numbered as the markers on "
            "the slides.",
            "What to say: Every number in square brackets on a slide points to an entry on these "
            "four pages, which list only what the deck cites. This page is agent design: "
            "LangChain, Anthropic, and Cobus Greyling, with LangChain's SQL toolkit code last.",
            "The point to land: Every claim in this deck traces to a numbered source or a "
            "recorded run.",
            "Example: Source 4, Anthropic's guide to writing tools, recommends truncating large "
            "tool responses and steering the agent when you do: the row cap and its notice in "
            "Section 1.",
            "Ask the room: None on this slide.",
            "Misconceptions: That the tutorial is a production design. Its own page says its "
            "database tools are not intended to be secure or used in production, Source 5.",
            "Transition: Next, verification and the text-to-SQL research.",
        ],
    ),
    # 7 sources: the sources the deck cites, part 2 ---------------------------------------------
    dict(
        kind="sources",
        title="Sources: verification and research",
        minutes=0.75,
        says="The verification and research sources the deck cites, by number",
        src=".dev/deck-sources.md; slides/source/sources.py",
        on_slide=sources_slide(
            ("Verification and evaluation of Structured Query Language (SQL)", (12, 13)),
            ("Text-to-SQL research and benchmarks", (16, 17, 18, 21)),
        ),
        notes=[
            "Purpose: List the verification and research sources the deck cites, numbered as "
            "the markers on the slides.",
            "What to say: Verification: the test-suite study and the Open Worldwide Application "
            "Security Project cheat sheet. Then the research: BIRD, Spider 2.0, LinkAlign, and "
            "the SEED audit, on why real warehouses are hard.",
            "The point to land: The research agrees with our runs: the hard part is the knowledge "
            "outside the schema, and the measurement.",
            "Example: Source 16, BIRD: GPT-4's execution accuracy on the test set rose from 34.88 "
            "to 54.89 percent when each question came with its evidence sentence.",
            "Ask the room: None on this slide.",
            "Misconceptions: That written business rules are correct because people wrote them. "
            "The SEED audit found wrong evidence in 105 of 1,534 BIRD development pairs, Source "
            "21.",
            "Transition: Next, event-driven systems and the first products.",
        ],
    ),
    # 8 sources: the sources the deck cites, part 3 ---------------------------------------------
    dict(
        kind="sources",
        title="Sources: event-driven systems and products",
        minutes=0.75,
        says="The event-driven sources and the first product sources the deck cites, by number",
        src=".dev/deck-sources.md; slides/source/sources.py",
        on_slide=sources_slide(
            ("Event-driven systems", (26, 27, 28, 29)),
            ("Products and documentation", (30, 32, 33, 36, 37)),
        ),
        notes=[
            "Purpose: List the event-driven and first product sources the deck cites, numbered "
            "as the markers on the slides.",
            "What to say: First the event-driven sources: queues in Postgres, SKIP LOCKED, and "
            "idempotent retries. Then the "
            "products from the design segment: the dbt Semantic Layer, Cube, and Snowflake's "
            "Cortex Analyst with its semantic views.",
            "The point to land: The products give your rules a home and measure them; you still "
            "write the rules and decide what the gate allows.",
            "Example: Source 37: Snowflake's own example of a poorly named column is gross "
            "revenue in a column named amt_ttl_pre_dsc.",
            "Ask the room: None on this slide.",
            "Misconceptions: That buying a product removes the need to write business rules. "
            "Snowflake's own page says schemas lack business process definitions and metrics, "
            "Source 36.",
            "Transition: The last page: the remaining products and the course's own evidence.",
        ],
    ),
    # 9 sources: the sources the deck cites, part 4 ---------------------------------------------
    dict(
        kind="sources",
        title="Sources: products and the course's evidence",
        minutes=1.25,
        says="The remaining product sources the deck cites, and the course's own evidence",
        src=".dev/deck-sources.md; slides/source/sources.py",
        on_slide=sources_slide(
            ("Products and documentation, continued", (39, 40, 42, 43, 44, 45, 49)),
            ("The course's own evidence, on GitHub", (50, 51, 52, 53)),
        ),
        notes=[
            "Purpose: List the remaining product sources and the course's own evidence, then "
            "close the class.",
            "What to say: Snowflake's suggestions and evaluations, Databricks's Genie pages and "
            "blog, and Uber's QueryGPT. The last group is the course's own evidence: the "
            "calibration report, the benefits page with the paired measurements, the evidence "
            "page, and the costs page. Every course number traces to these pages or the section "
            "evidence pages they link, and two dollar amounts are derived from them by "
            "subtraction, such as the 1,577,441.23 dollars on slide 8. That is the end of the "
            "class. Post any last question in the chat now; "
            "anything longer goes to the Thursday review, which answers every parked question "
            "in writing. Thank you.",
            "The point to land: Every course number traces to the evidence pages, and two are "
            "derived from them by subtraction.",
            "Example: Source 45: the Databricks blog's agent answered 0 of 13 benchmark "
            "questions at first; the blog puts it down to missing context, not to the model.",
            "Ask the room: None on this slide beyond the last-questions call; if a learner asks "
            "where to start after class, answer: the setup, then the Section 1 demos on your own "
            "machine.",
            "Misconceptions: That the course numbers are general rates. They are counts from "
            "this course's runs, on one model and one warehouse, with run ids on the evidence "
            "pages.",
            "Transition: That is the end of the class at 4:00; see you at the Thursday review.",
        ],
    ),
]
