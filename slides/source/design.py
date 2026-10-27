"""Designing text-to-SQL: the design segment, 0:37 to 0:47, 10 minutes, 4 slides (the third rebuild).

The owner's specification for the third rebuild (.dev/deck-spec-3.md), section 2, item 6: why real
warehouses are hard; the nine-stage reference architecture; the key design decisions; and each
section later gets its own design callout. "Build or buy" lives in the closing. The plan is the
lead's brief (.dev/review/deck3-brief.md, slides 23 to 26) and the audit (.dev/deck-audit-3.md,
current slides 13 to 16): the four hard parts become a table with the benchmark gap from BIRD [16]
and Spider 2.0 [17] and the false-pass figure of the test-suite paper [12]; the architecture diagram
moves to the concept canvas with a lead and a Key idea; the four decisions grow to seven with their
trade-offs; the new pointer table names the design callout of each section and of the closing.
External figures are verified in .dev/deck-sources.md (part 2 holds their conditions); course
numbers come from .dev/deck-evidence.md (entries named in each slide's src). Sources cited: 17, 16
and 12 (slide 23), 61, 65 and 30 (slide 25), all from the writers' shortlist.
"""

RULES = "design system 3"

SLIDES = [
    # 23 table: why real warehouses are hard -----------------------------------------------------------
    dict(
        kind="table",
        title="Text-to-SQL: Why real warehouses are hard",
        minutes=2.5,
        says="Five hard parts, each about meaning, not syntax: benchmark scores that do not carry "
        "over, rules outside the schema, ambiguous names and values, scale, and wrong numbers that "
        "look right",
        src=".dev/deck-sources.md [17] abstract and Table 5 (21.3 percent; over 1,000 columns), "
        "[16] Table 2 (34.88 and 54.89 percent, test set; humans 92.96) and its abstract (dirty "
        "database contents), [12] Table 2 (6.5 percent, 21 submissions); .dev/deck-evidence.md E5, "
        "E6, E8 (1,577,441.23 dollars, derived), E10 (two backpack names); docs/text-to-sql-design.md, "
        "Why your warehouse is harder than a benchmark; .dev/deck-audit-3.md, current slides 13 and 14",
        on_slide=[
            "Lead: Scores fall on real warehouses, and every hard part is about meaning, not syntax.",
            "| Hard part | What it looks like | What breaks |",
            "|---|---|---|",
            "| Benchmark gap | On enterprise tasks, the paper's best agent solved 21.3 "
            "percent[^17] | Classic scores do not predict yours |",
            "| Rules outside the schema | On BIRD's test set, given each question's rule, GPT-4 "
            "rose from 34.88 to 54.89 percent[^16] | Valid SQL, wrong rule |",
            "| Ambiguous names and values | A column named amount; one product spelled two ways | "
            "The filter misses rows; nothing errors |",
            "| Scale | Spider 2.0's real databases often hold more than 1,000 columns[^17] | The right "
            "column is lost among the rest |",
            "| Wrong numbers look right | One database wrongly passed 6.5 percent of queries, on "
            "average over 21 submissions[^12] | Nobody notices |",
            "Key idea: Valid SQL can still answer the wrong question; design for meaning first.",
        ],
        notes=[
            "Purpose: Name the five reasons questions over a real warehouse go wrong, with the "
            "published evidence, so every later design decision answers one of them.",
            "What to say: Structured Query Language, SQL, is the easy part. Five reasons make a "
            "real warehouse hard, one per row. First, the benchmark gap. Spider 2.0 built 632 "
            "tasks on real enterprise databases, and the paper's best agent solved 21.3 percent "
            "of them, Source [^17]. Earlier methods scored far higher on the classic benchmarks, "
            "so a leaderboard number tells you little about your warehouse. Second, the rules "
            "live outside the schema. On BIRD's test set, GPT-4 went from 34.88 to 54.89 percent "
            "when each question came with its rule sentence, Source [^16]. That is the same model, "
            "with the rule written down. Third, names and values are ambiguous. A column named "
            "amount says nothing about discounts, and our catalogue spells one backpack two ways. "
            "Filter on the user's words and the query runs cleanly and misses rows, or returns "
            "nothing. Fourth, scale. "
            "Spider 2.0's databases often hold over 1,000 columns, Source [^17], so the right one "
            "is lost among the rest. Fifth, a wrong number looks exactly like a right one. "
            "Checking results on the one database a benchmark ships wrongly passed 6.5 percent of "
            "predicted queries, averaged over 21 submissions, Source [^12]. Notice what the five "
            "share: in every case the model can write valid SQL, and the answer is still wrong.",
            "The point to land: Each hard part is about meaning, not syntax: the model writes "
            "valid SQL and still answers the wrong question.",
            "Example: One rule in our warehouse, leave out staff and test accounts, is worth "
            "about 1.6 million dollars: fiscal year 2025 net revenue is 64,015,091.21 dollars "
            "with it and 65,592,532.44 without. With every rule written down, BIRD's humans "
            "reached 92.96 percent and GPT-4 54.89, Source [^16]; the 34.88 and 54.89 are in "
            "the paper's Table 2, not the abstract the link opens. The Spider 2.0 figure is the "
            "paper's own agent on o1-preview, not the classic scores' method.",
            'Ask the room: "Which of the five hurts your warehouse most?" Expect: the naming '
            "first, then, after a pause, the rules that live in one team's heads.",
            "Misconceptions: That a stronger model closes the gap. BIRD's jump came from giving "
            "the same model the rule, not from a bigger model.",
            "Transition: Here is a reference architecture that answers all five, in nine stages.",
        ],
    ),
    # 24 concept: the nine-stage reference architecture ------------------------------------------------
    dict(
        kind="concept",
        title="Text-to-SQL: The nine-stage reference architecture",
        minutes=3,
        says="Nine stages from question to evaluated answer, each with its loop; models work in "
        "four of them, and every guarantee lives in a code stage",
        src="platform/tools/diagrams/definitions.py text_to_sql_architecture_concept (the same "
        "stages, places and arrows as text_to_sql_architecture_generic); docs/diagrams/README.md, "
        "its alternative text; docs/text-to-sql-design.md, The reference architecture and What "
        "the course did not measure; .dev/deck-audit-3.md, current slide 15",
        figure={
            "diagram": "text-to-sql-architecture-concept",
            "alt": "The text-to-SQL reference architecture in nine stages, each box its job in two lines"
            " and its loop's name on a white tag: question routing, where fixed code sends the "
            "question to its path, event loop; schema linking, which finds the tables and columns"
            " needed, agent loop; business knowledge, rules versioned and tested, hill-climbing "
            "loop; value lookup, which matches words to stored values, agent loop; query "
            "generation, where a model writes the query, agent loop; validation by syntax tree, "
            "cost, and personal data, verification loop; capped execution with a read-only role "
            "and a row cap, verification loop; an answer that is reviewed, states its "
            "assumptions, or asks back, verification loop; and evaluation, which matches gold "
            "answers on two databases and sends failures back to the business knowledge, hill-"
            "climbing loop",
        },
        on_slide=[
            "Lead: Nine stages to a checked answer; models work in four, and code holds every "
            "guarantee.",
            "Key idea: Put every guarantee in a code stage; use a model only where judgement is "
            "needed.",
        ],
        notes=[
            "Purpose: Give one reference architecture for text-to-SQL that fits any warehouse, "
            "and show that models work in four of its nine stages and code holds every guarantee.",
            "What to say: Every text-to-SQL system, product or your own code, has "
            "these nine stages. Each box names its job and the loop that builds it. Follow the "
            "arrows. Top row, left to right. One, routing: fixed code sends each question to its "
            "path; it carries the event loop's name because the router is a fixed table where each "
            "event arrives, a question, an export or a digest, never a model's choice. Two, schema linking: find the tables and columns that matter. Three, business "
            "knowledge: the rules, versioned and tested. Down to the middle row, which runs right "
            "to left. Four, value lookup: match the user's words to stored values. Five, query "
            "generation: here, and only here, a model writes the query. Six, validation before "
            "anything runs: parse the syntax tree, estimate the cost, and hold personal data. "
            "Down to the bottom row. Seven, capped execution: a read-only role, a timeout and a "
            "row cap. Eight, the answer: reviewed, with its assumptions stated, or a question "
            "back. Nine, evaluation: compare results, not query text, with gold answers on two "
            "databases. The long arrow from nine back to three is how failures become new rules. "
            "Now count: routing, validation, execution and evaluation are code; models work in "
            "four places: they link the schema, write the query, review the answer and propose "
            "rules from failures. A model can be wrong in a new way on every run, so every "
            "guarantee belongs in a code stage.",
            "The point to land: Text-to-SQL is a pipeline of nine decisions; models work in four "
            "of them, and every guarantee lives in a code stage.",
            "Example: Monday's revenue answer from the problem segment passed every check of "
            "stage six and ran cleanly in stage seven; the reviewer of stage eight held it, and "
            "only the gold check of stage nine proved it wrong.",
            'Ask the room: "Which stages does your system have today?" Expect: generation and '
            "execution; rarely value lookup or evaluation.",
            "Misconceptions: That stage five is the system. Most failures come from what the "
            "model was given in stages two to four, not from its syntax.",
            "Transition: Each stage hides a choice. Seven of them decide most designs; here they "
            "are, with their trade-offs.",
        ],
    ),
    # 25 table: the key design decisions ---------------------------------------------------------------
    dict(
        kind="table",
        title="Text-to-SQL: The key design decisions",
        minutes=2.5,
        says="Seven decisions every text-to-SQL design makes, each with its options and its "
        "trade-off",
        src=".dev/deck2-sources.md [61] (context a finite resource), [65] (agents about 4 times "
        "the tokens of chat); .dev/deck-sources.md [30] (one definition, refreshed everywhere); "
        "docs/text-to-sql-design.md, steps 3, 5 to 8 and What the course did not measure; the "
        "section design callouts (s1.py to s4.py); .dev/deck-audit-3.md, current slide 16",
        on_slide=[
            "Lead: Each option buys something and costs something; choose it on purpose.",
            "| Decision | Options | Trade-off |",
            "|---|---|---|",
            "| How much schema | All, scoped, or retrieved | More crowds the context[^61]; "
            "retrieval can miss one |",
            "| How values are found | The user's words, or a lookup | A lookup costs a call; raw "
            "words match nothing |",
            "| Where checks run | Before, during, after the query | Each catches what the others "
            "miss; each adds time |",
            "| Which queries wait | All, a model's call, or tagged columns | All trains reflex "
            "clicks; tags need upkeep |",
            "| Where rules live | Prompt, file, view, semantic layer | One definition for every "
            "tool[^30]; a file is tested |",
            "| One shot or an agent | One model call, or a loop with tools | An agent repairs, at "
            "several times the tokens[^65] |",
            "| Assume or ask | State it, or ask back | Checked later, or a turn spent to avoid a "
            "guess |",
            "Key idea: No option is free: write down the choice, then measure it on your questions.",
        ],
        notes=[
            "Purpose: Give the seven design decisions every text-to-SQL system faces, each with "
            "its options and its trade-off.",
            "What to say: Seven decisions, one per row. How much schema: all of it is simplest, "
            "but context is a finite resource, Source [^61], and retrieval at scale can miss the "
            "table that matters. How values are found: filter on the user's words and a "
            "misspelled product returns nothing; a lookup costs one more call. Where checks run: "
            "before the query, while it runs, and after; each stage catches what the others miss. "
            "Which queries wait for a person: hold everything and approvals become a reflex; hold "
            "by tagged columns and someone must keep the tags. Where rules live: a view or a "
            "semantic layer computes a formula once and shares it with every tool, Source [^30]; "
            "a versioned file can be learned, tested and rolled back. One shot or an agent: an "
            "agent can inspect tables and repair a refused query, and Anthropic reports that agents "
            "typically use about four times the tokens of a chat, Source [^65]. Assume or ask: a "
            "stated assumption gives a reviewer and a gold check something to judge later; a "
            "question back costs the user a turn, but when a term is truly ambiguous it avoids a "
            "wrong answer. So assume and say so when a rule answers the question, and ask when a "
            "business term has no rule.",
            "The point to land: Every text-to-SQL design makes these seven choices; make each on "
            "purpose, write it down, and measure it on your own questions.",
            "Example: DataPilot's choices: tables listed and described on demand, value lookup left to "
            "Assignment 1: Agent loop, checks at all three stages, holds on tagged personal-data "
            "columns, a versioned knowledge file, an agent with tools, and stated assumptions.",
            'Ask the room: "Which of your rules could become a view today?" Expect: net revenue '
            "and active customer.",
            "Misconceptions: That a semantic layer guarantees the formula. Only if the agent "
            "cannot reach the base tables; it can still pick the wrong metric or grain.",
            "Transition: You will not decide all seven now. Each comes back in the section that "
            "builds its loop.",
        ],
    ),
    # 26 table: where each decision is made next -------------------------------------------------------
    dict(
        kind="table",
        title="Text-to-SQL: One design callout in each section",
        minutes=2,
        says="Where each decision comes back: one Text-to-SQL design slide in each section, and "
        "build or buy in the closing",
        src="the design callouts of s1.py to s4.py and closing.py (their tables); "
        ".dev/review/deck3-brief.md, the section rhythm (slide 8 of each section); "
        ".dev/deck-audit-3.md, the new slide 26",
        on_slide=[
            "Lead: Each decision returns where its loop is built, just before that section's "
            "cheat sheet.",
            "| Where | Decision | What the callout shows |",
            "|---|---|---|",
            "| Section 1: Agent loop | How much schema; how values are found | Small and large "
            "warehouses side by side |",
            "| Section 2: Verification loop | Where checks run | Checks before, during and after "
            "a query |",
            "| Section 3: Event loop | What waits for approval | Three hold rules and what each "
            "costs |",
            "| Section 4: Hill-climbing loop | Where learned rules live | Each option, what "
            "decides it, what to watch for |",
            "| Closing | Build or buy | Semantic layers and warehouse assistants against "
            "building |",
            "Key idea: Every loop you build settles one design decision for your own warehouse.",
        ],
        notes=[
            "Purpose: Show learners where each design decision comes back, so they carry the "
            "seven choices through the day and leave with a design for their own warehouse.",
            "What to say: You will not decide these now. Each decision comes back where its loop "
            "is built, on a slide titled Text-to-SQL design, just before that section's cheat "
            "sheet. Read the table by row. In Section 1: Agent loop, how much schema the agent "
            "sees and how it finds values, with a small warehouse and a large one side by side. "
            "In Section 2: Verification loop, where to check a generated query: before it runs, "
            "while it runs, and after. In Section 3: Event loop, which queries wait for a person: "
            "hold everything, let a model judge, or hold by tagged columns, and what each costs. "
            "In Section 4: Hill-climbing loop, where learned rules live and what decides a "
            "change. And in the closing, build or buy: what semantic layers and warehouse "
            "assistants give you, and what you build either way. Two decisions have no callout "
            "of their own. One shot or an agent stays open, because we never measured it. Assume "
            "or ask comes back in Assignment 2: Verification loop.",
            "The point to land: Each section ends its techniques with one decision for your own "
            "warehouse; collect them and you have a design.",
            "Example: Keep a note open with seven lines, one per decision, and fill in your "
            "choice as each callout passes; by the closing it is a first design.",
            'Ask the room: "Which decision are you least sure of for your warehouse?" Expect: '
            "where rules live, and which queries need a person.",
            "Misconceptions: That the decisions are independent. Where rules live decides what "
            "the evaluation can test, and how much schema decides what a check sees.",
            "Transition: Now we build the first loop of that design: the agent loop.",
        ],
    ),
]
