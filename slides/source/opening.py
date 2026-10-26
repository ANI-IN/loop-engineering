"""Opening block: 16 slides, 0:00-0:10."""

R = "<!-- refresh after the session: {} -->"

SLIDES = [
    {
        "kind": "title",
        "title": "Module: Loop Engineering",
        "layout": "title",
        "minutes": 0.5,
        "says": "Four loops around one data agent, each measured on one benchmark",
        "src": "README.md",
        "on_slide": [
            "Module: Loop Engineering",
            "Agent, verification, event, and hill-climbing loops: build each, then measure it.",
            "[CLASS DATE]",
        ],
        "notes": [
            "Say: Welcome to Module: Loop Engineering. You already build agents. Today is about "
            "the loops around them: the loop that answers, the loop that checks, the loop that "
            "runs on events, and the loop that improves from evidence. We build all four around "
            "one data agent and measure each one. Every demo you see runs live against the real "
            "model.",
            "Point at: the four loop names in the subtitle.",
            "Placeholder: the class date in square brackets is replaced before class.",
            'Likely question: "Is this specific to SQL agents?" Answer: SQL makes every check '
            "concrete, so we use it; each principle transfers to any agent whose output you can "
            "check.",
            "Transition: First, who is teaching.",
        ],
        "container": "title slide",
    },
    {
        "kind": "opening",
        "title": "Instructor",
        "layout": "blank",
        "minutes": 0.5,
        "says": "Who is teaching, and how to reach them",
        "src": "-",
        "on_slide": ["Instructor", "[INSTRUCTOR NAME AND CONTACT]"],
        "notes": [
            "Say: Introduce yourself in two sentences: what you build, and one loop that saved or "
            "cost you in production. Say how learners reach you during and after class.",
            "Placeholder: the instructor's name and contact in square brackets are replaced "
            "before class.",
            "Point at: the contact line.",
            'Likely question: "Where do I ask during class?" Answer: in the chat; questions that '
            "do not fit go to the Thursday review.",
            "Transition: One line from you in the chat before we start.",
        ],
        "container": "title slide: name, role, contact",
    },
    {
        "kind": "opening",
        "title": "Welcome: before we begin, in the chat",
        "layout": "concept",
        "minutes": 0.5,
        "says": "Post one line: which agent you run, and what stops it when it is wrong",
        "src": "-",
        "on_slide": [
            "In the chat: which agent do you run today?",
            "What stops it when it is wrong?",
        ],
        "notes": [
            'Say: Post one line in the chat. Read two or three answers aloud. Most answers are "a '
            'person reads the output". Keep that answer in mind: by the end of class you will have '
            "three other answers that do not depend on someone noticing.",
            "Point at: the two questions.",
            'Ask: "What stops your agent today when it is wrong?" Expected: a person, or nothing.',
            'Likely question: "Will the slides be shared?" Answer: yes, the deck and its outline '
            "are in the course repository.",
            "Transition: Here is how the four hours run.",
        ],
        "container": "key-idea box: the chat prompt",
    },
    {
        "kind": "opening",
        "title": "How the class runs",
        "layout": "diagram",
        "minutes": 1,
        "says": "Four sections, two breaks, one poll; every demo live; recovery is reset and run again",
        "src": "docs/instructor-guide.md",
        "on_slide": [
            "Opening, four sections, two breaks, one poll, wrap-up",
            "Each section: failure, question, four concepts, live demos, code, questions",
            "Every result shows a live stamp: start time and trace link",
            "A stalled demo is reset and run again; no recordings",
        ],
        "notes": [
            "Say: Each section has the same shape. A failure story, a tempting question with a "
            "verdict, four concepts, then one demo segment where I run several live demos and open "
            "the code in the editor, then questions. Breaks follow Section 2: Verification loop "
            "and the poll after Section 3: Event loop. Every demo is live. Each result on screen "
            "carries a live stamp: when the run started, in your own local time, and a link to its "
            "trace. If a demo stalls, I reset that section and run it again. There are no "
            "recordings.",
            "Point at: the section shape, then the live-stamp line.",
            'Likely question: "What if the model API is down?" Answer: I say so, open the code for '
            "that section, and return to the demo when the API answers.",
            'Likely question: "Why no recordings as a backup?" Answer: a recording cannot show '
            "what a loop does when the model surprises you, which is the point of the class.",
            "Transition: Where to get help while we go.",
        ],
        "container": "step cards: the section shape",
    },
    {
        "kind": "opening",
        "title": "Support during the class",
        "layout": "concept",
        "minutes": 0.5,
        "says": "Ask in the chat; a parking lot holds the rest for the Thursday review",
        "src": "docs/review-session.md",
        "on_slide": [
            "Ask in the chat at any time",
            'Overflow: write "Thursday" and it goes to the two-hour review session',
        ],
        "notes": [
            "Say: Ask in the chat at any time. When a question needs more than a minute, I say "
            "Thursday, and you post it with that word. The Thursday review session is two hours on "
            "the four assignments; it also answers the parking lot in writing.",
            "Point at: the Thursday line.",
            'Likely question: "When is the Thursday review?" Answer: [THURSDAY REVIEW TIME], a '
            "placeholder replaced before class; the solutions are published when it starts.",
            "Transition: Keys next.",
        ],
        "container": "icon row: chat, parking lot",
    },
    {
        "kind": "opening",
        "title": "Your OpenAI key and its limit",
        "layout": "concept",
        "minutes": 0.5,
        "says": "Your OpenAI key comes from the operations team; it lives in your environment file, "
        "never in a commit",
        "src": ".env.example",
        "on_slide": [
            "Your OpenAI key comes from the operations team",
            "Paste it into your local environment file; that file is never committed",
            "Recommended on the key's project: a 3-dollar limit and an alert at 1.50 dollars",
        ],
        "notes": [
            "Say: You get your OpenAI key from the operations team. Paste it into your .env file "
            "and never commit it; the file is ignored by git. The recommended limit on your key's "
            "project is 3 dollars, with an alert at 1.50 dollars. That is plenty: one analyst run "
            "costs about a tenth of a cent, a full experiment of 70 runs about 6 to 9 cents, and "
            "each assignment check stops at its own spend cap of 1 dollar. Every run shows its "
            "tokens and cost on the console, so you can see what your own experiments spend.",
            "Point at: the never-committed line, then the limit line.",
            'Likely question: "Which model does the class use?" Answer: gpt-6-luna, named in the '
            "model setting of the example environment file; it is a reasoning model, which matters "
            "in Section 1: Agent loop.",
            "Transition: LangSmith is the second key.",
        ],
        "container": "icon row: key, file, never committed",
    },
    {
        "kind": "opening",
        "title": "LangSmith setup",
        "layout": "concept",
        "minutes": 0.5,
        "says": "Set the LangSmith key and project so every demo and check run links to its trace",
        "src": "setup/pre-class.md",
        "on_slide": [
            "Set your LangSmith key and keep tracing on",
            "Pass and fail are computed locally; LangSmith holds the traces",
        ],
        "notes": [
            "Say: Set your LangSmith key and keep tracing on. Pass and fail are computed locally "
            "and shown at once; LangSmith is the trace record behind every result. Every demo run "
            "and every assignment check run is traced in full. Experiment runs are traced as a "
            "sample, about 1 run in 5, tagged with knowledge version, split, item, and repetition, "
            "so one learner stays well inside the free plan's 5,000 traces a month; every run is "
            "still scored locally. Use your own free account; feedback is written with extended "
            "retention off.",
            "If LangSmith refuses traces when its free plan's monthly limit is spent, a trace link "
            "never fills; say so once, and point at the run's start time and run id as the "
            "evidence. Every result is still scored locally.",
            "Point at: the local-scoring line.",
            'Likely question: "Do I need a paid plan?" Answer: no; the class keeps to base traces '
            "on the free plan.",
            "Transition: The checks that must pass before the first demo.",
        ],
        "container": "icon row: key, tracing, local scoring",
    },
    {
        "kind": "opening",
        "title": "Setup checks",
        "layout": "concept",
        "minutes": 1,
        "says": "Services healthy, then the preflight canary: easy questions pass, trap questions still "
        "fail",
        "src": "setup/README.md",
        "allow_commands": True,
        "on_slide": [
            "1. Services report healthy",
            "2. Canary: three easy questions pass",
            "3. Canary: two trap questions still fail under the starting knowledge",
            "4. The class session starts; the status line shows its start time",
        ],
        "notes": [
            "Say: Before class I ran two checks, and you will run the same ones at home. First, "
            "every service reports healthy. Second, the preflight canary: three easy questions "
            "must pass, and two trap questions must still fail under the starting knowledge. If "
            "the trap questions start passing, the model changed under us, so calibration runs "
            "again before anyone teaches with it. When every check passes, preflight starts the "
            "class's live session; the console's status line shows when it started, and every run "
            "until the next preflight belongs to it. In every preflight recorded in calibration, the "
            "canary read as expected. Preflight reads its data check and its canary from the selected domain pack.",
            "Instructor reference, not on the slide: do not run preflight now. You ran `make ps`, "
            "then `make preflight PURPOSE=class`, thirty minutes before class (the preflight "
            "checklist); a second preflight would start a new live session and leave the class "
            "session's runs behind.",
            "Point at: the two canary lines of that output, in the terminal where it ran.",
            'Likely question: "Why must a check fail?" Answer: the demos teach a failure the loops '
            "then fix; a trap that passes unaided would make the story untrue, so the canary "
            "proves it still fails.",
            "Transition: Where the Harness Engineering module left off.",
        ],
        "container": "step cards: four checks in order",
    },
    {
        "kind": "opening",
        "title": "Recap: from one harness to four loops",
        "layout": "concept",
        "minutes": 0.5,
        "says": "The Harness Engineering module built the harness around one run; this module builds "
        "loops around many",
        "src": "README.md",
        "on_slide": [
            "The Harness Engineering module: around one run",
            "- Instructions the agent reads",
            "- State across sessions",
            "- Scope and sandbox",
            "- Verification of one run",
            "This module: around many runs",
            "- An agent loop with good tools",
            "- Verification of every run",
            "- Runs triggered by events",
            "- Improvement from evidence",
        ],
        "notes": [
            "Say: Two cards. On the left, the Harness Engineering module, built around one run: "
            "the instructions the agent reads, state that carries across sessions, scope and a "
            "sandbox for what it may touch, and verification of that one run. On the right, this "
            "module, built around many runs: an agent loop with good tools, verification of every "
            "run, runs triggered by events, and improvement from evidence. The agent stays; the "
            "loops around it are new.",
            "Point at: the left card, then each line of the right card in turn, then the arrow "
            "from one run to many runs.",
            'Likely question: "Do I need the Harness Engineering module first?" Answer: It builds '
            "on it. The recap slide covers what you need, and the setup pages list the "
            "prerequisites.",
            "Transition: The product we build.",
        ],
        "container": "two-column cards: the Harness Engineering module, around one run | this module, around many runs; then a one-run-to-many-runs diagram",
        "diagram": {
            "kind": "one run to many runs",
            "describe": "One run pill under the left card, an arrow, and a grid of eight run pills "
            "under the right card.",
        },
    },
    {
        "kind": "opening_content",
        "title": "Problem statement: what are we building?",
        "layout": "concept",
        "minutes": 1,
        "says": "A data agent that answers business questions in SQL, live in a console with one page "
        "per loop",
        "src": "README.md",
        "on_slide": [
            "Harbor & Pine Outfitters: a fictional outdoor retailer; data ends 31 January 2026",
            "DataPilot answers business questions in Structured Query Language (SQL), live in a "
            "console:",
            "- Agent: the tool timeline, the SQL, the answer against gold",
            "- Verify: the grader checklist and which defense layer stopped what",
            "- Events: the run board lanes, approvals, and the channel",
            "- Improve: experiments, the holdout ledger, the gate verdict",
        ],
        "notes": [
            "Say: Harbor & Pine Outfitters is a fictional outdoor retailer with a Postgres "
            "warehouse whose data ends on 31 January 2026, the business date for everything today. "
            "Finance and marketing ask questions in plain words. DataPilot writes SQL, runs it, "
            "and answers. The console has one page per loop: Agent, Verify, Events, and Improve. "
            "The data is generated with a fixed seed, and the traps in it are planted on purpose.",
            "Point at: the four page names.",
            'Likely question: "Why a fixed business date?" Answer: so "the previous day" and "the '
            'last completed fiscal quarter" mean the same thing in every run, whatever the wall '
            "clock says.",
            "Transition: One question runs through the whole class.",
        ],
        "container": "icon row: the four console pages",
    },
    {
        "kind": "opening_content",
        "title": "The spine question: net revenue in fiscal year 2025",
        "layout": "diagram",
        "minutes": 1,
        "says": "One question, five traps the schema does not reveal",
        "src": "platform/planted/registry.yaml",
        "on_slide": [
            '"What was our net revenue in fiscal year 2025?"',
            "1. **Fiscal year**: calendar dates; the fiscal year runs February to January",
            "2. **Net revenue**: the total adds tax and shipping; use subtotal minus discount",
            "3. **Cancelled orders**: no status filter; status 5 is undocumented",
            "4. **Eastern time**: universal timestamps move evening orders to the next day",
            "5. **Internal accounts**: no email filter; they hold 3 of the top 10",
        ],
        "diagram": {
            "kind": "annotated query",
            "describe": "The naive query, with a numbered marker where each trap hides; the five "
            "callouts above sit below it, one per marker.",
            "origin": "platform/console/design/specimen.py lines 260-266 (the join line split in two)",
            "query": [
                "SELECT SUM(o.total_cents) / 100.0 AS net_revenue",
                "FROM warehouse.orders AS o",
                "JOIN warehouse.customers AS c",
                "  ON c.customer_id = o.customer_id",
                "WHERE o.order_ts >= '2025-01-01'",
                "  AND o.order_ts <  '2026-01-01'",
            ],
            # (line, fragment, callout number); the first mark of a number places its marker.
            "marks": [
                (4, "'2025-01-01'", 1),
                (5, "'2026-01-01'", 1),
                (0, "o.total_cents", 2),
                (4, "WHERE", 3),
                (4, "o.order_ts", 4),
                (5, "o.order_ts", 4),
                (2, "JOIN warehouse.customers AS c", 5),
            ],
        },
        "notes": [
            "Say: Five traps hide in this one question, and the schema reveals none of them. The "
            "fiscal year runs February to January and is named for the year it ends. Net revenue "
            "is subtotal minus discount, not the tempting total column that includes tax and "
            "shipping. Cancelled orders carry an undocumented status code. Business days are in "
            "Eastern time, so evening orders cross the UTC date. Internal accounts are known only "
            "by their email domain, and they hold exactly 3 of the top 10 revenue spots in each "
            "fiscal year.",
            "Point at: each numbered marker in the naive query, then its callout below: the "
            "calendar dates, the total column, the missing status filter, the UTC timestamp, and "
            "the join with no email filter.",
            'Likely question: "Why not document the schema and be done?" Answer: that document is '
            "the knowledge the agent needs; Section 4: Hill-climbing loop shows how to earn it "
            "behind a gate instead of guessing it.",
            "Transition: Why this is worth four hours.",
        ],
        "container": "annotated query: the naive net-revenue query | five trap callouts",
    },
    {
        "kind": "opening_content",
        "title": "Why this matters",
        "layout": "concept",
        "minutes": 0.5,
        "says": "A confident wrong number costs more than no answer; each loop removes one way to ship "
        "it",
        "src": "README.md",
        "on_slide": [
            "Wrong but confident: a board deck carries a number nobody can trace",
            "Unsafe or unbounded: a stacked write reaches the warehouse; a loop bills without end",
            "Duplicated or unstoppable: a digest posts twice; a stop misses the running job",
            "**Right on the test, wrong next month:** a rule fits the cases it was written from",
            "Each loop removes one of these, at a cost you will see",
        ],
        "notes": [
            "Say: Four failures, one per loop. A wrong number lands in a board deck. Unsafe SQL "
            "reaches the warehouse. A digest posts twice, or a stop does not stop. A rule fits the "
            "test and breaks next month. Each loop removes one of these, and each costs something "
            "you will see.",
            "Point at: the four lines, top to bottom.",
            'Likely question: "Do I need all four loops?" Answer: start with the loop that matches '
            "your worst failure today.",
            "Transition: The four loops together.",
        ],
        "container": "four cards: one failure per loop",
    },
    {
        "kind": "diagram",
        "title": "Four loops: one system, the answer path",
        "layout": "diagram",
        "minutes": 0.5,
        "says": "Answer, check, run on events: three nested loops, agents only where judgement is needed",
        "src": "docs/architecture.md; docs/diagrams/four-loops.png (the same boxes, redrawn)",
        "on_slide": [],
        "diagram": {
            "kind": "boxes",
            "describe": "The left part of the four-loops diagram, redrawn from shapes with 18-point "
            "labels: the agent loop inside the verification loop, inside the event loop.",
            "frames": [
                (0.6, 1.05, 12.13, 5.45, "Section 3: Event loop"),
                (0.75, 2.45, 9.3, 3.95, "Section 2: Verification loop"),
                (0.9, 2.85, 4.8, 3.45, "Section 1: Agent loop"),
            ],
            "boxes": [
                (0.8, 1.45, 2.2, 0.75, "edge", "Event: webhook or schedule"),
                (3.2, 1.45, 2.2, 0.75, "step", "Insert with a key: one run"),
                (5.6, 1.45, 2.2, 0.75, "step", "Router: a table, no agent"),
                (8.0, 1.45, 2.2, 0.75, "data", "Jobs table: claim, lease"),
                (10.4, 1.45, 2.2, 0.75, "step", "Reaper: requeue expired"),
                (1.05, 3.3, 1.45, 0.6, "edge", "Question"),
                (2.75, 3.25, 2.75, 0.7, "agent", "Analyst agent"),
                (1.05, 4.2, 2.15, 0.95, "step", "Tools: list, describe, query"),
                (3.4, 4.2, 2.15, 0.95, "agent", "Schema scout agent"),
                (1.05, 5.35, 4.5, 0.8, "data", "Active knowledge version, in every prompt"),
                (5.85, 3.25, 1.95, 0.95, "step", "Seven graders"),
                (8.0, 3.2, 1.9, 1.05, "agent", "Reviewer agent"),
                (5.85, 4.45, 1.95, 1.25, "stop", "Retry with feedback; cap at 3"),
                (8.0, 4.45, 1.9, 0.95, "person", "Human approval"),
                (10.3, 3.2, 2.3, 0.95, "step", "Autonomy policy: post or hold"),
                (10.3, 4.35, 2.3, 0.6, "edge", "Channel post"),
                (10.3, 5.15, 2.3, 0.95, "stop", "Kill switch: before every call"),
            ],
            "arrows": [
                (3.0, 1.825, 3.2, 1.825),
                (5.4, 1.825, 5.6, 1.825),
                (7.8, 1.825, 8.0, 1.825),
                (10.2, 1.825, 10.4, 1.825),
                (8.6, 2.2, 8.6, 2.45),
                (2.5, 3.6, 2.75, 3.6),
                (3.3, 3.95, 2.6, 4.2),
                (4.45, 3.95, 4.45, 4.2),
                (5.5, 3.6, 5.85, 3.6),
                (7.8, 3.7, 8.0, 3.7),
                (6.8, 4.2, 6.8, 4.45),
                (8.95, 4.25, 8.95, 4.45),
                (9.9, 3.7, 10.3, 3.7),
                (11.45, 4.15, 11.45, 4.35),
            ],
        },
        "notes": [
            "On the slide: the left part of the four-loops diagram, redrawn from shapes so every "
            "label is 18-point text; the full picture is in the course repository. The agents are "
            "the orange ovals: the analyst and the schema scout in the agent loop, the reviewer in "
            "the verification loop, and none in the event loop.",
            "Say: The agent loop answers; the verification loop checks every query and the answer; "
            "the event loop runs work on events, with keys, approvals, and a stop. Look at where the "
            "agents are: the analyst and one helper, one reviewer after the deterministic checks, "
            "none at all in the event loop.",
            "Point at: the router box, a table with no agent, then the three orange ovals.",
            "Transition: The fourth loop sits beside them and feeds them.",
        ],
        "container": "box diagram drawn from shapes: Sections 1 to 3",
    },
    {
        "kind": "diagram",
        "title": "Four loops: the hill-climbing loop feeds back",
        "layout": "diagram",
        "minutes": 0.5,
        "says": "The hill-climbing loop improves the others from failures, behind a gate",
        "src": "docs/architecture.md; docs/diagrams/four-loops.png (the same boxes, redrawn)",
        "on_slide": [],
        "diagram": {
            "kind": "boxes",
            "describe": "The right part of the four-loops diagram, redrawn from shapes with "
            "18-point labels: the hill-climbing loop from the benchmark to the new active version.",
            "frames": [
                (0.6, 1.05, 12.13, 5.45, "Section 4: Hill-climbing loop"),
                (5.85, 1.2, 6.85, 1.65, "Analyzer team: failed dev items only"),
            ],
            "boxes": [
                (0.8, 1.6, 2.2, 0.95, "data", "Benchmark: 25 dev, 15 holdout"),
                (3.3, 1.6, 2.35, 0.95, "step", "Experiment: two databases"),
                (6.0, 1.6, 2.05, 0.95, "agent", "Failure analyst"),
                (8.3, 1.6, 2.05, 0.95, "agent", "Rule writer"),
                (10.6, 1.6, 1.95, 0.95, "agent", "Critic: only cuts"),
                (10.35, 3.3, 2.2, 1.0, "step", "Overfit guard: no quoted question"),
                (7.85, 3.3, 2.2, 1.0, "step", "Two candidates, kept on dev"),
                (5.1, 3.3, 2.45, 1.0, "step", "Promotion gate: four conditions"),
                (2.85, 3.3, 1.95, 1.0, "person", "Human approval"),
                (0.8, 4.75, 4.0, 0.95, "data", "The new active version, in every prompt"),
                (
                    5.1,
                    4.75,
                    7.45,
                    0.95,
                    "step",
                    "Autonomy per metric family, from its holdout items",
                ),
            ],
            "arrows": [
                (3.0, 2.075, 3.3, 2.075),
                (5.65, 2.075, 6.0, 2.075),
                (8.05, 2.075, 8.3, 2.075),
                (10.35, 2.075, 10.6, 2.075),
                (11.55, 2.55, 11.55, 3.3),
                (10.35, 3.8, 10.05, 3.8),
                (7.85, 3.8, 7.55, 3.8),
                (5.1, 3.8, 4.8, 3.8),
                (3.8, 4.3, 3.8, 4.75),
                (6.3, 4.3, 6.3, 4.75),
            ],
        },
        "notes": [
            "On the slide: the right part of the four-loops diagram, redrawn from shapes with "
            "18-point labels. The orange ovals are the "
            "analyzer team: the failure analyst, the rule writer, and the critic. Their output meets "
            "code, the overfit guard and the promotion gate, and then a person.",
            "Say: The hill-climbing loop improves from failures behind a gate, and a promoted "
            "version becomes the active knowledge version every analyst prompt carries. An analyzer "
            "team whose output code and a person must accept: agents appear only where judgement "
            "is needed.",
            "Source 1: The art of loop engineering "
            '(https://www.langchain.com/blog/the-art-of-loop-engineering): "The fourth (and arguably '
            'most important) automates improvement!" It names the same four loops; the fourth is '
            "the hill-climbing loop.",
            "Point at: the promotion gate, then the human approval beside it.",
            'Likely question: "How does this differ from LangChain\'s version?" Answer: theirs '
            "climbs on production traces; ours climbs on benchmark failures behind a holdout gate.",
            "Transition: How we will know any of it works.",
        ],
        "container": "box diagram drawn from shapes: Section 4",
    },
    {
        "kind": "opening_content",
        "title": "How we will measure",
        "layout": "diagram",
        "minutes": 0.5,
        "says": "Hand-written gold queries, results compared on two databases, dev and holdout splits",
        "src": "platform/packs/datapilot_us/pack.yaml",
        "on_slide": [
            "Each question has a hand-written gold query",
            "Pass: the result matches gold on two databases, never the query text",
            "40 questions: 25 dev the analyzer team may learn from; 15 holdout it never sees",
            "Holdout items run 3 times and pass on 2 of 3",
            "The gate decides on holdout only, with human approval",
        ],
        "notes": [
            "Say: Every benchmark question has a gold query written by hand. An answer passes when "
            "its result matches gold on two databases, never by comparing query text. The "
            "benchmark has 40 questions: the analyzer team learns from the dev split only, and the "
            "gate decides on the holdout split, where each item runs 3 times and passes on 2 of 3.",
            "Re-check after live runs: 40 items and the 3 runs and 2 passes against the benchmark "
            "files and the evaluation settings.",
            "Point at: the two splits.",
            'Likely question: "Why two databases?" Answer: a wrong query can match the right '
            "result on one database by chance; Section 2: Verification loop gives the numbers.",
            "Transition: Eight words you will hear all day.",
        ],
        "container": "labelled diagram: question, gold, two databases, two splits",
    },
    {
        "kind": "opening_content",
        "title": "Glossary",
        "layout": "table",
        "minutes": 0.5,
        "says": "Eight terms, one line each",
        "src": "docs/glossary.md",
        "on_slide": [
            "| Term | Meaning |",
            "|---|---|",
            "| Trap | A business rule the schema does not reveal |",
            "| Gold query | The hand-written query with the right answer |",
            "| Holdout split | Questions the analyzer team never sees |",
            "| Grader | A deterministic check of one stage |",
            "",
            "| Term | Meaning |",
            "|---|---|",
            "| Reviewer | An agent that reads after the graders pass |",
            "| Knowledge version | A numbered set of business rules |",
            "| Promotion gate | The check a new version must pass |",
            "| Autonomy level | How much runs unattended |",
        ],
        "notes": [
            "Say: Read each term in one breath. The full glossary is in the course repository.",
            "Point at: grader and reviewer, the pair people mix up.",
            'Likely question: "Grader or reviewer: which one decides?" Answer: graders decide; the '
            "reviewer can only add a concern.",
            "Transition: Section 1: Agent loop starts with the agent on its own.",
        ],
        "container": "two tables of four terms",
    },
]
