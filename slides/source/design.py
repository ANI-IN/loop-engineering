"""Designing text-to-SQL (Structured Query Language): the design segment, 0:10 to 0:25, 15 minutes, 6 slides.

The owner's specification, section 2 item 1: why text-to-SQL is hard in a real company, the
reference architecture with DataPilot's implementation of each stage, the key design decisions with
their trade-offs, and how this approach compares with semantic-layer products and warehouse-native
assistants. Course numbers come from .dev/deck-evidence.md (entries E1 and on, named in each slide's
src); external figures come from .dev/deck-sources.md, and every source marker [^n] uses its
numbering. Round 1 review: the lead's rulings 1, 2, 3, 7, 8 and 16 and the text-to-SQL design
review's findings shape this version; "What to say" stays within minutes x 130 words, less 40 for
the room question.
"""

RULES = "design system"

SLIDES = [
    # 1 insight: what one business rule is worth -------------------------------------------------------
    dict(
        kind="insight",
        title="Business knowledge decides the answer; check it like code",
        minutes=2,
        says="One unwritten rule moves revenue by 1.6 million dollars, and written rules are "
        "often wrong too",
        src="deck-evidence E8 (derived: 65,592,532.44 against 64,015,091.21), E6; deck-sources "
        "part 2: [21] Section I and Table II; [16] Table 2; [45]",
        on_slide=[
            "Insight: A rule nobody wrote down moved our answer by 1.6 million dollars; a rule "
            "written wrong moves it too.",
            "Evidence: Internal accounts alone add 1,577,441.23 dollars to fiscal year 2025 "
            "net revenue.",
            "- The SEED audit of BIRD's evidence: 105 of 1,534 rules wrong, 148 missing[^21]",
            "- Correcting those 105: execution accuracy rose from 44.76 to 54.29 percent[^21]",
        ],
        notes=[
            "Purpose: Open the design segment with what a business rule is worth, and why written "
            "rules need the same checking as code.",
            "What to say: You saw the 0 of 99 at the start; here is what one rule is worth in "
            "money. On our warehouse, fiscal year 2025 net revenue with every other rule applied "
            "is 64,015,091.21 dollars. Leave out the internal-accounts rule and it is "
            "65,592,532.44. That one unwritten rule is 1,577,441.23 dollars, by subtraction. "
            "Be honest about where that comes from: we built the five traps into this warehouse "
            "on purpose, so the mechanism is visible. Nobody planted anything in BIRD, where "
            "GPT-4's execution accuracy rose from 34.88 to 54.89 percent on the test set when "
            "given the rule sentence, "
            "Source 16, or in the Databricks team's Genie Agent, which answered none of its 13 "
            "questions before it had context, Source 45. And writing rules down is not the end. "
            "The SEED audit of BIRD's evidence, its rule sentences, found 105 of the 1,534 in the "
            "development set wrong and 148 missing; on those 105, correcting the rule raised a "
            "fine-tuned model's execution accuracy from 44.76 to 54.29 percent, Source 21. We compared no models in this course. The lesson for "
            "design: rules need an owner, a version, and a test.",
            "The point to land: Treat business rules as code: write them down, version them, and "
            "test them against answers you checked by hand.",
            "Example: A filter on the word harborpine anywhere in the email, instead of the "
            "domain, drops a few real customers and comes out 28,474.44 dollars low: a written "
            "rule, still wrong.",
            'Ask the room: "Who owns your definition of net revenue?" Expect: finance, an '
            "analyst, or nobody in particular.",
            "Misconceptions: That writing the rules down solves it. Written rules have defects "
            "too; only a gold check tells you which.",
            "Transition: So why are questions over a real warehouse hard? Four reasons.",
        ],
    ),
    # 2 evidence: why questions over a real warehouse are hard ----------------------------------------
    dict(
        kind="evidence",
        title="Why questions over a real warehouse are hard",
        minutes=2,
        says="Rules in heads, large and poorly named schemas, informal values, and wrong numbers "
        "that look right",
        src="deck-evidence E5, E6, E10; deck-sources part 2: [17] abstract and Table 5, [18] "
        "Appendix B, [49], [12] Table 2, [37]",
        on_slide=[
            "| Why it is hard | Evidence |",
            "|---|---|",
            "| Rules live in people's heads | Five traps; the schema states none |",
            "| Schemas are large, poorly named | Often over 1,000 columns; the paper's best agent: 21.3 "
            "percent[^17] |",
            "| Values are informal | A guessed status filter returned nothing[^49] |",
            "| A wrong number looks right | Single-database checks: 6.5 percent false "
            "passes[^12] |",
            "Sample: Spider 2.0, 632 tasks; 21 Spider submissions",
        ],
        notes=[
            "Purpose: Name the four reasons questions over a real warehouse go wrong, each with "
            "evidence, so every later design decision answers one of them.",
            "What to say: Four reasons, one per row. First, the rules live in people's heads: "
            "our five traps, and nothing in the schema states any of them. Second, schemas are "
            "large and poorly named. Spider 2.0's 632 tasks run on enterprise databases often over "
            "1,000 columns, and the paper's best agent in 2024, on o1-preview, solved 21.3 "
            "percent, Source 17. "
            "Snowflake's documentation gives the example of gross revenue in a column named amt "
            "ttl pre dsc, Source 37. And when LinkAlign pooled every Spider database's schema, "
            "choosing the tables caused 68.3 percent of failures, Source 18. Third, values are "
            "informal. A user asks about the blue hiking jacket; the warehouse stores a name "
            "nobody says aloud, and our catalog holds two near-identical backpack names on "
            "purpose. Uber's tool filtered on status Finished when the stored value was "
            "Completed: the query ran and returned nothing, Source 49. Fourth, a wrong number "
            "looks exactly like a right one. Checking results on the one database a benchmark "
            "ships passed wrong queries 6.5 percent of the time, on average over 21 Spider "
            "submissions, Source 12. Those are percentages as the papers publish them.",
            "The point to land: Each difficulty is about meaning, not syntax: the model can write "
            "valid SQL and still answer the wrong question.",
            "Example: The run you saw at the start used calendar dates, Coordinated Universal "
            "Time, and every account, and nothing failed.",
            'Ask the room: "Which of the four hurts your warehouse most?" Expect: the naming, '
            "then, after a pause, the rules in people's heads.",
            "Misconceptions: That classic benchmark scores describe your warehouse. Classic "
            "benchmarks have small, clean schemas; Spider 2.0 was built because enterprise work "
            "looks different.",
            "Transition: Here is a design that answers all four, stage by stage.",
        ],
    ),
    # 3 concept diagram: the reference architecture ------------------------------------------------
    dict(
        kind="concept",
        title="Nine stages from question to checked answer",
        minutes=4,
        says="Nine stages from question to evaluated answer, each with DataPilot's implementation",
        src="platform/tools/diagrams/definitions.py text_to_sql_architecture; "
        "platform/src/datapilot/loop3_events/router.py; loop1_agent/scout.py, knowledge.py, "
        "extension.py, analyst.py, prompts.py, tools.py; loop2_verification/graders/, "
        "executor.py, reviewer.py; contracts/answer.py, knowledge.py; "
        "loop4_hill_climbing/evaluator.py; pack.yaml limits, cost_guard, personal_data; "
        "deck-sources [18] Appendix B",
        figure={
            "diagram": "text-to-sql-architecture",
            "alt": "Nine stages in three rows, each with DataPilot's implementation and its loop: "
            "1 question routing by a fixed router; 2 schema retrieval and linking by the schema "
            "scout agent; 3 business knowledge in the knowledge version, a light semantic layer; "
            "4 value lookup, Assignment 1; 5 SQL generation by the analyst agent; 6 validation "
            "by the syntax-tree guard, the cost estimate, and the personal-data rules; 7 capped "
            "execution through the read-only executor, at most 50 rows back; 8 an answer with "
            "stated assumptions or a clarifying question, Assignment 2; 9 evaluation by "
            "execution match with gold queries on two databases, which feeds business knowledge",
        },
        on_slide=[],
        notes=[
            "Purpose: Give learners one reference architecture for text-to-SQL and show how "
            "DataPilot implements each of its nine stages.",
            "What to say: Every stage from question to checked answer is a design decision. "
            "Follow the numbers. One, routing: a fixed table maps each event to its "
            "handler and queue, and a keyword table names the metric family. Never a model, so "
            "routing is predictable. Two, schema linking: the schema scout, an agent that may "
            "only list and describe tables, returns a brief of tables, joins, and caveats. Three, "
            "business knowledge: a versioned file of rules, each with when it applies and its "
            "SQL guidance, put into the prompt on every model call; a lightweight semantic layer. "
            "Four, value lookup: empty in class; Assignment 1 builds it, at most five stored "
            "values close to the user's words, and a question back when two tie. Five, "
            "generation: the analyst writes one read-only select, with up to three attempts. "
            "Six, validation before anything runs: graders on the syntax tree allow one select "
            "over allowed tables, estimate cost from the query plan, and hold any query that "
            "returns personal columns for a person. Seven, execution: a read-only role and "
            "transaction, a 5-second timeout, at most 50 rows back with the total count. Eight, "
            "the answer: a reviewer agent reads the query and its result, then an envelope with "
            "the stated assumptions, or a clarifying question. Nine, evaluation: the query must "
            "return the gold result on two databases with different data. The arrow back to "
            "three is the analyzer team, agents that turn failures into proposed rules.",
            "The point to land: Text-to-SQL is a pipeline of nine decisions; the model writes the "
            "query in only one of them.",
            "Example: In the run you saw at the start, every grader of stage 6 passed and the query "
            "ran cleanly in stage 7; the reviewer could only doubt it, and only the gold check of "
            "stage 9 proved the number wrong.",
            'Ask the room: "Which stages does your system have today?" Expect: generation and '
            "execution; rarely value lookup or evaluation.",
            "Misconceptions: That stage 5 is the system. In LinkAlign's pooled-schema sample, "
            "Source 18, schema linking caused 68.3 percent of failures, and our traps all sit in "
            "stage 3: most failures come from what the model was given or chose to look at, not "
            "from SQL syntax.",
            "Transition: Each stage hides a choice. Here are the first three, with their "
            "trade-offs.",
        ],
    ),
    # 4 design callout: rules, generation, clarification -------------------------------------------
    dict(
        kind="design_callout",
        title="Design decisions: rules, generation, and clarification",
        minutes=2.5,
        says="Where rules live, one shot or an agent, and assume or ask, with what DataPilot chose",
        src="deck-evidence E19, E20, E43; deck-sources [3], [37], [44]; "
        "platform/src/datapilot/loop1_agent/prompts.py; contracts/knowledge.py; "
        "section-2-verification-loop/assignment/README.md",
        on_slide=[
            "Decision: where rules live, how queries are written, when to ask",
            "| Decision | Options | DataPilot chose |",
            "|---|---|---|",
            "| Where rules live | Prompt, knowledge file, semantic layer, views[^37][^44] | A "
            "versioned, gated knowledge file |",
            "| How the query is written | One shot, or an agent with tools | An agent; not "
            "measured against one shot |",
            "| An unclear question | State assumptions, or ask | Assume; Assignment 2 asks on "
            "undefined terms |",
            "DataPilot: versioned rules the gate tests and can roll back.",
        ],
        notes=[
            "Purpose: Lay out three design decisions with their trade-offs, what DataPilot chose, "
            "and where the course measured the choice and where it did not.",
            "What to say: First, where rules live. In the prompt is fastest and drifts. A "
            "knowledge file is versioned and can be learned and gated, but it is still text the "
            "model may misread. A semantic layer or a view computes a metric once, in code, but "
            "it enforces the formula only if the agent's role can read nothing else, and a metric "
            "layer answers only what its metrics express, so keep a path for the rest. "
            "Databricks advises text instructions only as a last resort, Source 44. We chose a "
            "knowledge file because the hill-climbing loop must propose, test, and roll back "
            "rules. Second, one shot or an agent. One shot is cheaper and faster; an agent can "
            "inspect tables and fix a blocked query. Anthropic advises the simplest solution that "
            "works, Source 3. We chose an agent and never measured it against one shot. Third, "
            "assume or ask. When the fiscal year question once came back as a question, nothing "
            "was left to check. So answer with stated assumptions, and ask when a business term "
            "has no rule. Our class prompt says assume, and ask only when nothing maps; yet the "
            "analyst asked a clarifying question about VIP customers and about loyal customers, "
            "one run each. "
            "Assignment 2 makes the rule a grader, so it no longer depends on the model.",
            "The point to land: Put rules where you can version, test, and roll them back; state "
            "assumptions a checker can judge, and ask when a term has no rule.",
            "Example: The standard view-side fix for our first trap is a calendar table with a "
            "fiscal-year column, joined instead of computed.",
            'Ask the room: "Which of your rules could become a view or a metric today?" Expect: '
            "net revenue, active customer.",
            "Misconceptions: That a semantic layer guarantees the formula. Only if the agent "
            "cannot reach the base tables, and it can still pick the wrong metric or grain.",
            "Transition: Four more decisions: what the agent sees, touches, spends, and how you "
            "judge it.",
        ],
    ),
    # 5 design callout: schema, access, cost, evaluation -------------------------------------------
    dict(
        kind="design_callout",
        title="Design decisions: schema, permissions, cost, and evaluation",
        minutes=2.5,
        says="Schema at scale, access for each user, cost and latency, and evaluation by result "
        "on two databases",
        src="deck-evidence E12, E14, E15, E21, E22, E28, E37, E58, E59; deck-sources [12] Table "
        "2, [33], [36], [40], [44], [49]; platform/src/datapilot/loop4_hill_climbing/"
        "evaluator.py",
        on_slide=[
            "Decision: what the agent sees, touches, and spends",
            "| Decision | DataPilot chose | Measured |",
            "|---|---|---|",
            "| Schema shown | Described tables, a scout | 17 of 21 against 12; 3 changes |",
            "| Access, personal data | Read-only role; approvals | Every write refused |",
            "| Cost, latency | About 0.001 dollars a run | Helpers more than double it (4 questions) |",
            "| Evaluation | Results on two databases | One database alone: 6.5 percent false "
            "passes[^12] |",
            "DataPilot: one role; at work, run each query as its asker.",
        ],
        notes=[
            "Purpose: Cover the remaining decisions, including schema at scale, access for each "
            "user, and drift, with DataPilot's choice and what was measured.",
            "What to say: Schema. Described tables and the scout took seven easy questions from "
            "12 of 21 runs right to 17 of 21, three changes mixed. At scale even the table list "
            "is too long: retrieve candidate tables from their descriptions, scope each agent to "
            "about five tables, Source 44, and let a person confirm the tables, as Uber does, "
            "Source 49. Access. DataPilot runs as one read-only role, and every write was "
            "refused. In your company, run each query with the asker's own permissions, through "
            "row-level security or the warehouse's access control, Sources 36 and 33. Approved "
            "rows still go to the model provider. Cost and latency. An analyst run costs about a "
            "tenth of a cent; budget warehouse compute too, with the plan estimate as the guard. "
            "On four questions, one run each, turning off either the scout or the reviewer "
            "roughly halved the seconds. Evaluation. Compare results, not query text, on a second database: the same "
            "schema with different rows, a reseeded or masked copy; ignore row order and allow a "
            "numeric tolerance. Re-run the benchmark when the schema, a rule, or the data "
            "changes; and pin the dates in gold answers, as Snowflake warns, Source 40.",
            "The point to land: Enforce in code and in the database, give each asker their own "
            "access, and re-measure by result on every change.",
            "Example: The revenue question took 35 to 76 seconds end to end with both helpers on. "
            "For a person waiting in a chat, one option is to keep the scout and run the reviewer "
            "after posting, labelled unverified until it approves; we did not measure that "
            "ordering.",
            'Ask the room: "How do you decide today that a generated query is right?" Expect: '
            "someone reads it, or a test compares the text.",
            "Misconceptions: That a read-only role is access control. It stops writes; it does not "
            "stop one person reading another region's rows, or 5,261 approved addresses reaching "
            "the model.",
            "Transition: Products already do parts of this. When should you buy instead of build?",
        ],
    ),
    # 6 design callout: how this compares, build or buy --------------------------------------------
    dict(
        kind="design_callout",
        title="Build or buy: semantic layers and warehouse assistants",
        minutes=2,
        says="What dbt, Cube, Cortex Analyst, and Genie Agents give you, and what the four loops add",
        src="deck-sources part 3: [30], [32], [33], [36], [37], [39], [40], [42], [43], [44], [45]",
        on_slide=[
            "Decision: buy a rules layer, or build loops around it?",
            "| Aspect | dbt, Cube | Cortex Analyst, Genie Agents | DataPilot |",
            "|---|---|---|---|",
            "| Rules live in | Metric definitions[^30][^33] | Views, query expressions[^37][^44] | "
            "A gated knowledge file |",
            "| Access per user | Layer's policies[^33] | Warehouse access control[^36][^42] | One "
            "service role |",
            "| Measured by | Not on their pages | Held-back queries[^40][^45] | Two-database "
            "results |",
            "DataPilot: the improver never sees the holdout; one confirmed regression blocks.",
        ],
        notes=[
            "Purpose: Compare DataPilot's approach fairly with semantic-layer products and "
            "warehouse assistants, and say when to build and when to buy.",
            "What to say: Semantic layers define metrics once. With dbt, MetricFlow writes the "
            "SQL, Source 32; Cube's agents write a Semantic SQL the layer validates, Source 33; "
            "their pages do not describe measuring answer quality. Warehouse assistants give you "
            "access control for each user, a maintained interface, and evaluation: Snowflake runs "
            "held-back verified queries judged by a model and counts regressions, Source 40, and "
            "Snowflake now recommends Cortex Agents in Cortex Analyst's place, Source 36. Both "
            "assistants suggest improvements a person reviews, Sources 39 and 43. Buy "
            "when your metrics already live in one platform. But buying does not write your "
            "rules: Databricks's own example is a Genie Agent using calendar quarters instead of "
            "the fiscal calendar, Source 43. Build when you must pin the model: Cortex Analyst "
            "picks it from those your role may use, and Snowflake may change that choice, Source "
            "36. What the loops add: the improver never sees the holdout "
            "questions that decide, one confirmed regression blocks a promotion, a guard rejects "
            "rules that quote the test, and answers match on two databases. A combination we "
            "have not seen documented.",
            "The point to land: A product is a place to put your rules, not their source; the "
            "loops decide whether a rule is right.",
            "Example: Our fiscal-year trap is Databricks's own worked example of a context fix.",
            'Ask the room: "Which platform holds your metrics today?" Expect: dbt, Snowflake, '
            "Databricks, or a spreadsheet.",
            "Misconceptions: That the products have no evaluation. They do; the difference is "
            "who sees the deciding questions and whether a regression blocks.",
            "Transition: Now we build the first loop of that design: the agent loop.",
        ],
    ),
]
