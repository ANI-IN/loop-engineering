"""The problem, 0:13-0:37: 9 slides, 24 minutes, under design system 3.

The owner's specification of 27 October 2026, section 3, in the reference deck's format (its
slides 14 to 22): what we are building, the week of failures, the challenge in four quotes, what a
failure and the loops cost, the four critical gaps, the data model, the business rules in plain
words, how we measure, and the glossary. It absorbs the second rebuild's problem slides and its
foundations block (the five traps, the four failures, how we measure).

Grounding: the week of failures in the true form of .dev/deck3-evidence.md, part 1 (the writers'
guide, "The week of failures, as the evidence allows it"); the costs from part 2; the quotes word
for word from part 4; the rules from platform/packs/datapilot_us/benchmark/business_rules.md and
pack.yaml; the terms from docs/glossary.md. Run ids, sample sizes and dates are in the notes only.
The four asking teams are the owner's scenario; the repository names no asking teams.
"""

RULES = "design system 3"

SLIDES = [
    # 14 what are we building -------------------------------------------------------------------
    dict(
        kind="concept",
        title="Problem statement: What are we building?",
        minutes=3,
        says="DataPilot for Harbor & Pine Outfitters: who asks, how they ask, and what it must "
        "give back",
        src="the owner's specification of 27 October 2026, section 3, item 1; pack.yaml "
        "(display name, digest); the demo registry (webhook, digest); "
        ".dev/review/deck3-diagrams-concept.md, what-we-build",
        figure={
            "diagram": "what-we-build",
            "alt": "DataPilot for Harbor & Pine Outfitters: who asks, finance, sales, operations, "
            "and marketing; how they ask, through the console, webhooks, and a daily digest; "
            "DataPilot, the analyst agent with its four loops, the agent loop, the verification "
            "loop, the event loop, and the hill-climbing loop, reading a read-only warehouse; and "
            "what it must give back, answers that are right, safe, unattended, and improving.",
        },
        on_slide=[
            "Lead: DataPilot, a text-to-SQL agent for Harbor & Pine Outfitters, an American "
            "outdoor retailer.",
            "Key idea: Same model; we add loops that make its answers right, safe, unattended and "
            "improving.",
        ],
        notes=[
            "Purpose: Show what the class builds: who asks DataPilot questions, how the questions "
            "arrive, and what every answer must be.",
            "What to say: Today we build one agent and the four loops around it. The agent is "
            "DataPilot, a text-to-SQL agent: it turns a question in plain words into a query, "
            "runs it on the warehouse, and answers. The company is Harbor & Pine Outfitters, a "
            "fictional outdoor retailer that sells camping and hiking gear. Walk the diagram from "
            "left to right. First column, who asks: finance, sales, operations and marketing. "
            "The teams are our scenario; their questions come from the course's benchmark. "
            "Finance wants net revenue for the board, operations wants the previous day's order count, "
            "sales wants the best-selling products, marketing wants an export of its California "
            "customers. Second column, how they ask. Someone types into the console. Another "
            "system sends a webhook, a request that arrives with nobody watching. And a "
            "scheduler asks for a daily digest at 8 a.m. Eastern time. Third column, DataPilot: "
            "the analyst agent, the blue oval, and under it the four loops we build today, one "
            "per section. To the right, the warehouse, which DataPilot may only read. And last, "
            "what it must give back: answers that are right, safe, unattended and improving. "
            "Right needs all four loops; the business rules arrive last, in Section 4: "
            "Hill-climbing loop. Safe needs checks in code and in the database. "
            "Unattended needs events, approvals and a stop that survive restarts. Improving "
            "needs changes measured before they go live. Notice what never changes: the model. "
            "We use the same model in every run today.",
            "The point to land: The model stays the same all day; what we build are the four "
            "loops of code around it.",
            "Example: The question that runs through every section is finance's: what was our "
            "net revenue in fiscal year 2025? Its checked answer is 64,015,091.21 dollars.",
            'Ask the room: "Which of these three ways in does your own agent support today?" '
            "Expect: a chat box, the console; rarely webhooks or a schedule.",
            "Misconceptions: That a stronger model would make the loops unnecessary. A stronger "
            "model reads the same schema, gets the same duplicate events, and still needs "
            "someone to measure its changes.",
            "Transition: Here is what happens when a team gives this agent a week of real "
            "questions without the loops.",
        ],
    ),
    # 15 the week of failures -------------------------------------------------------------------
    dict(
        kind="problem",
        title="Problem statement: The problem in the real world",
        minutes=3,
        says="A week of business questions, one costly failure a day, each from the course's runs",
        src="the owner's specification of 27 October 2026, section 3, item 2; "
        ".dev/deck3-evidence.md, part 1 (the true form of each day); docs/benefits.md",
        on_slide=[
            "Lead: Your team gives a week of business questions to a data agent.",
            "- **Monday:** Finance asks for fiscal year 2025 net revenue; the agent answers "
            "$72,394,572.08, wrong by about 8.4 million dollars. | warning",
            "- **Tuesday:** A first-word check passes a DELETE hidden behind a SELECT; 10,000 "
            "rows burn three run budgets. | lock",
            "- **Wednesday:** A question sent three times is answered three times; two digests "
            "disagree on one day. | copy",
            "- **Thursday:** A worker restart loses a customer export's approval; after stop is "
            "pressed, a run posts anyway. | pause",
            "- **Friday:** A plausible rule, exclude discounted orders, turns nine right answers "
            "wrong, and nothing errors. | branch",
            "Footer: Each failure costs more than the question saved.",
        ],
        notes=[
            "Purpose: Make the problem concrete: one week of business questions, one costly "
            "failure a day, each taken from the course's own runs.",
            "What to say: Monday: "
            "finance asks for net revenue in fiscal year 2025. The agent answers 72,394,572.08 "
            "dollars in one fluent sentence. The right figure is 64,015,091.21, so it is wrong "
            "by about 8.4 million dollars, and nothing errors. Tuesday: a product name could carry "
            "hidden instructions to delete orders, our illustration; we ran the statement itself. A guard that reads only the first "
            "word passes a DELETE hidden behind a SELECT, and only the database stops it: the "
            "read-only transaction refuses the write, and the role has no write grant behind it. "
            "The same day, a request runs a query of 10,000 rows and every row reaches the "
            "model: about three run budgets. Wednesday: a "
            "chat tool "
            "resends a question three times and it is answered three times; the morning digest "
            "fires twice, and leadership gets two digests for the same day with different "
            "revenue. Thursday: a California customer export waits for a person's approval, the "
            "worker restarts, the approval is gone and the run fails. Someone presses stop, and "
            "a run already under way posts anyway. Friday: someone adds a rule that sounds "
            "right, exclude discounted orders from revenue, and nine answers that used to be "
            "right are now wrong.",
            "The point to land: Every failure this week looked like a success; none of them "
            "raised an error.",
            "Example: The runs behind each day. Monday, run 9182df01: in our runs the reviewer, "
            "a second model that reads each answer before it posts, held that answer, so it never posted; the gold answer is run 59174f10. Tuesday, "
            "runs 1d9b4169 and be82d6f6: no row changed, and the uncapped run took 182,654 "
            "tokens against a run budget of 60,000. Wednesday, run d5817278: 3 answers and 2 "
            "digests, in 5 of 5 planted runs. Thursday, runs 88a0227a and 47ad546f, "
            "6 of 6 each. Friday, experiment 84417bfe: a planted demo version, "
            "9 regressions, blocked by the gate.",
            'Ask the room: "Which day has your team already lived through?" Expect: Monday and '
            "Wednesday.",
            "Misconceptions: That these are model failures. Each one is a missing piece of the "
            "system around the model.",
            "Transition: The rules for all of this exist somewhere. So why does the agent still "
            "miss them?",
        ],
    ),
    # 16 the challenge, in four quotes ----------------------------------------------------------
    dict(
        kind="quotes",
        title="The challenge is: The rules exist, the agent still misses",
        minutes=3,
        says="Four verified sources on context, repeated delivery, overfitting and improvement",
        src=".dev/deck3-evidence.md, part 4 (each quote read on its page on 27 October 2026); "
        "sources.py entries 61, 88, 110 and 1",
        on_slide=[
            "Lead: The rules live in heads and runbooks, not the schema; four sources name the "
            "failures.",
            "Quote: Context, therefore, must be treated as a finite resource with diminishing "
            "marginal returns. | 61",
            "Quote: Design your applications to be idempotent (they should not be affected "
            "adversely when processing the same message more than once). | 88",
            "Quote: Doing many rounds of this procedure might cause the model to implicitly fit "
            "the peculiarities of the test set. | 110",
            "Quote: The first three loops automate work. The fourth (and arguably most "
            "important) automates improvement! | 1",
        ],
        notes=[
            "Purpose: Show, in four published sources' own words, why an agent misses rules that "
            "exist: context, repeated delivery, overfitting, and improvement.",
            "What to say: Every rule behind this week's failures exists somewhere: in the "
            "finance lead's head, in a policy, in a runbook. None of it is in the schema, and "
            "the agent reads only the schema and what its tools return. Four sources name the "
            "failures the loops answer. Top left, Anthropic's guide to "
            "context engineering, Source [^61]: context is a finite resource with diminishing "
            "returns. Paste every rule and every row in, and the rule that matters drowns. That "
            "is Section 1: Agent loop. Top right, Amazon's guide to its message queue, Source [^88]: design "
            "your applications to be idempotent, because the same message can arrive more than "
            "once. Delivery systems promise at least once, not exactly once. That is "
            "Wednesday, and Section 3: Event loop. Bottom left, Google's machine learning course, Source "
            "[^110], in the answer to one of its own quiz questions: many rounds of tuning "
            "against the same test questions make a model fit the peculiarities of that test "
            "set. A rule that fixes the questions you looked at can "
            "break the ones you did not. That is Friday, and Section 4: Hill-climbing loop. Bottom right, "
            "LangChain's article that names the four loops, Source [^1]: the first three loops "
            "automate work, the fourth automates improvement, and the author calls it arguably "
            "the most important. Read the four together. The agent misses because it sees too "
            "much or too little, because the world around it repeats and restarts, and because "
            "changes made to fix it are not measured. Checking the answer, the verification "
            "loop, sits between them: nothing on this slide checks anything.",
            "The point to land: Writing rules down is not enough; the agent must see them, be "
            "checked against them, and learn them under measurement.",
            "Example: The fiscal year rule is in the course's business rules page all along; the "
            "agent never reads that page, and learns the rule only in Section 4.",
            'Ask the room: "Where do your business rules live today?" Expect: a wiki, a few '
            "people, or a query someone wrote years ago.",
            "Misconceptions: That a longer prompt holding every rule solves it. It crowds the "
            "context, goes stale, and nothing checks it.",
            "Transition: So what does a failure cost a data team, and what do the loops cost?",
        ],
    ),
    # 17 what failures and loops cost -----------------------------------------------------------
    dict(
        kind="costs",
        title="Why this matters for data teams",
        minutes=2.5,
        says="What a failure costs, and what each loop cost in the course's measured runs",
        src=".dev/deck3-evidence.md, part 2; docs/benefits.md, Section 1: Agent loop and Section 2: Verification loop; "
        "docs/calibration-report.md, Agents on and off, Model bake-off, Wall time",
        on_slide=[
            "Lead: Each failure costs the team; each loop costs too. No run measured the whole "
            "stack on and off.",
            "Panel: What a failure costs",
            "- A wrong number in a board deck, believed",
            "- Personal data in an export nobody approved",
            "- A duplicate alert: two digests for one day",
            "- A broken metric nobody notices",
            "Panel: What the loops cost, measured",
            "- Agent loop: about 1,100 more tokens a run",
            "- Verification loop: 8,000 more tokens a run",
            "- Event loop: no extra model calls",
            "- Hill-climbing: 6 to 9 cents an experiment",
        ],
        notes=[
            "Purpose: Weigh what a failure costs a data team against what each loop cost in the "
            "course's measured runs, and say plainly what was not measured.",
            "What to say: Left panel, what a failure costs. A wrong number in a board deck is "
            "the worst kind, because it is believed. Personal data "
            "in an export nobody approved costs a disclosure and an audit. A duplicate alert "
            "costs attention: after two digests for one day, people stop reading digests. A "
            "broken metric nobody notices costs every decision made on it until someone does. "
            "Right panel, what the loops cost, each measured against its own without. The agent "
            "loop's better tools took about 1,100 more tokens a run; the dollar figures come "
            "from different runs, so they are not comparable, and we claim no saving. The verification loop took about 8,000 more tokens a run, about six "
            "hundredths of a cent. The event loop adds no model calls: its keys, leases, "
            "approvals and kill switch are database and code checks. The hill-climbing loop "
            "costs per improvement, not per run: one experiment of 70 runs measured 6 to 9 cents, "
            "and a whole improvement, baseline, analyzer team and candidate, about 25 to 34 "
            "cents, our estimate. Now what "
            "we did not measure. No run turned the whole stack on and off on the same "
            "questions, and seconds were measured only for the two helper agents. So read these "
            "as each loop's own cost, not a total.",
            "The point to land: The loops cost tokens and cents on every run; one wrong number "
            "in a board deck costs trust for a long time.",
            "Example: Agent loop: 3,738 against 4,857 tokens a run, "
            "seven questions, 21 runs a side, rehearsal session 56894641. Verification loop: "
            "9,311 against 17,344 tokens, 0.0361 against 0.0605 dollars for 40 runs a side, "
            "twenty trap questions. An experiment of 70 runs: 0.0594 to 0.0914 dollars. Seconds: "
            "the schema helper and the reviewer each added about 2.7 seconds a question, on 4 "
            "questions with 1 run each.",
            'Ask the room: "What did your last wrong number cost?" Expect: a meeting, a '
            "correction email, and some trust.",
            "Misconceptions: That the loops are free. They are not, so we measure their cost the "
            "same way we measure their benefit.",
            "Transition: Each failure of the week has a cause. There are only four.",
        ],
    ),
    # 18 the four critical gaps -----------------------------------------------------------------
    dict(
        kind="concept",
        title="Why we need loops: The four critical gaps",
        minutes=3,
        says="Each story of the week has a cause, and each cause gets one loop",
        src="the owner's specification of 27 October 2026, section 3, item 5; "
        ".dev/review/deck3-diagrams-concept.md, four-gaps; docs/benefits.md",
        figure={
            "diagram": "four-gaps",
            "alt": "Four rows of story, cause, and loop, each story named by its day: Tuesday, 10,000 "
            "rows flood the run, because the agent can't see enough, or sees too much, answered "
            "by the agent loop; Monday and Tuesday, a wrong number nobody checks and a hidden "
            "DELETE that reaches the database, because nothing checks the answer, answered by the"
            " verification loop; Wednesday and Thursday, duplicates, a lost approval, and an "
            "ignored stop, because events repeat and processes restart, answered by the event "
            "loop; and Friday, a plausible rule breaks nine answers, because changes aren't "
            "measured, answered by the hill-climbing loop",
        },
        on_slide=[
            "Lead: Each day's failure has a cause, and each cause gets one loop; Monday's answer "
            "needs all four.",
            "Key idea: One loop per cause.",
        ],
        notes=[
            "Purpose: Turn the week of failures into four causes, give each cause the one loop "
            "that answers it, and show why Monday needs all four.",
            "What to say: Five days, four causes, one per row: the story, its cause, the "
            "loop. Row one: the agent can't "
            "see enough, or sees too much. That is Tuesday's 10,000 rows flooding the run, and "
            "the start of Monday: a column named total says nothing about tax. The agent loop "
            "answers it with tools that show the right view, capped, and stops in code. Row two: "
            "nothing checks the answer. That is Monday's wrong number, which nothing in the agent could "
            "check; in our runs the reviewer held it, and it never went out. And Tuesday's DELETE "
            "hidden behind a SELECT. The verification loop answers it: parse the query, "
            "rely on the database's grants, retry with feedback, and hold doubtful answers for "
            "a person. Row three, Wednesday and Thursday: duplicates, a lost approval, an "
            "ignored stop. The cause underneath is that events repeat and processes restart, "
            "while the state lived in one process. The event loop answers it: keys by meaning, "
            "leases, approvals that survive a restart, and a kill switch checked at every step. "
            "Row four, Friday: a plausible rule breaks nine answers, because changes aren't "
            "measured. The hill-climbing loop answers it: gold questions, holdout questions the "
            "rule writers never see, and a gate. Now Monday again. Its answer needs all four: "
            "the agent loop shows the right columns, the verification loop flags the number, "
            "the event loop holds it safely while nobody watches, and only the hill-climbing "
            "loop learns the fiscal year rule. Nothing here changes the model.",
            "The point to land: Each failure has a cause outside the model; one loop answers "
            "each cause, and the hardest question needs all four.",
            "Example: Without a reviewer, 39 of 40 wrong answers to trap questions went out "
            "unflagged, in 40 runs on twenty development trap questions; with the guard, graders "
            "and reviewer, 20 still went out, so a check that shares the writer's knowledge is "
            "half an answer.",
            'Ask the room: "Which row is your agent missing today?" Expect: the second or the '
            "fourth.",
            "Misconceptions: That one loop can cover two rows. A checker cannot stop a "
            "duplicate event, and a gate cannot widen what the agent sees.",
            "Transition: Before we build anything, here is the data the agent works on.",
        ],
    ),
    # 19 the data model -------------------------------------------------------------------------
    dict(
        kind="concept",
        title="Harbor & Pine: The data model",
        minutes=2,
        says="Five tables, their key columns, the business date, and no business rule anywhere",
        src="platform/ops/sql/warehouse_schema.sql and warehouse_indexes.sql; "
        "benchmark/business_rules.md, Business date; .dev/review/deck3-diagrams-concept.md, "
        "data-model",
        figure={
            "diagram": "data-model",
            "alt": "Harbor & Pine's warehouse: five tables with their key columns, customers, "
            "orders, order_items, products, and categories; arrows join orders to customers, "
            "order_items to orders and to products, products to categories, and categories to "
            "their parent category; a box gives the business date, 31 January 2026; and a grey "
            "box says no column or comment states a business rule: not the fiscal year, net "
            "revenue, what status 5 means, Eastern time, or which accounts are internal.",
        },
        on_slide=[
            "Lead: Five tables and a fixed business date; not one column or comment states a "
            "business rule.",
            "Key idea: Nothing in the schema states the business rules.",
        ],
        notes=[
            "Purpose: Show the warehouse the agent reads, its five tables and business date, and "
            "that no business rule is written anywhere in it.",
            "What to say: This is everything the agent can learn from the schema. Five tables. "
            "Customers, with an email, a state, and a flag for customers who opted out of "
            "the sale of their personal data. Orders, the heart of it: a customer, a timestamp, "
            "a status, and money columns in cents: subtotal, discount, tax, shipping and total; "
            "the diagram shows three. Order items join orders "
            "to products, with a quantity. Products belong to categories, and categories nest "
            "under a parent category. Follow the arrows: they are the foreign keys, the joins "
            "the agent can trust. Now the box on the left, under customers: the business date. DataPilot "
            "treats 31 January 2026 as today, the last day of fiscal year 2026, so the previous day, "
            "last month and this quarter always mean the same days, in class and in every "
            "measurement. And the grey box, the point of the slide. No column or comment says "
            "the fiscal year starts in February. Nothing says net revenue is subtotal minus "
            "discount, and total sits right there looking like revenue. Nothing says status 5 "
            "means cancelled. Nothing says days count in Eastern time while the timestamps are "
            "stored in Coordinated Universal Time. Nothing says which accounts are staff and "
            "test accounts. A model with perfect reading of this schema still has to guess "
            "every one of them. That is why Monday's answer was fluent and wrong.",
            "The point to land: A schema stores the data, not the business; every rule that "
            "decides the answer lives somewhere else.",
            "Example: The warehouse holds three fiscal years, 2024 to 2026, and a second "
            "database with the same schema and different data, which we use to check answers.",
            'Ask the room: "Where is your fiscal calendar written down?" Expect: a finance '
            "spreadsheet, a wiki, or one person.",
            "Misconceptions: That column comments would fix this. Comments describe storage; "
            "these rules describe the business and change with it.",
            "Transition: So here are those rules, in plain words.",
        ],
    ),
    # 20 the business rules in plain words ------------------------------------------------------
    dict(
        kind="table",
        title="Business rules: The rules in plain words",
        minutes=3,
        says="The five traps and three safety rules, each with a concrete example",
        src="platform/packs/datapilot_us/benchmark/business_rules.md, rules 1 and 3 to 6; "
        "pack.yaml personal_data and autonomy; docs/glossary.md; .dev/deck-evidence.md E5, E6",
        on_slide=[
            "Lead: Five kinds of trap and three safety rules, each with Harbor & Pine's example.",
            "| Kind of rule | Example |",
            "|---|---|",
            "| Fiscal year | Runs February to January, named for the year it ends |",
            "| Net revenue | Subtotal minus discount; total adds tax and shipping |",
            "| Cancelled orders | Status 5 means cancelled, written nowhere; leave them out |",
            "| Eastern time | A 9 p.m. order lands on the next Coordinated Universal Time day |",
            "| Internal accounts | Staff and test accounts on the company domain; left out |",
            "| Read-only | The agent only reads; the database refuses every write |",
            "| Personal data | A query returning emails, phones or names waits for approval |",
            "| Approvals | A held answer posts only after a person approves it |",
        ],
        notes=[
            "Purpose: State every business rule and safety rule in plain words, each with an "
            "example, so learners recognise each trap when it appears later.",
            "What to say: These are the rules an answer must follow, as the finance team would "
            "say them. The first five are the traps. Fiscal year: it runs February to January "
            "and is named for the year it ends, so fiscal year 2025 is mostly calendar 2024. "
            "Net revenue: subtotal minus discount; the total column adds tax and shipping, and "
            "it looks like revenue. Cancelled orders: status 5 means cancelled, the codes are "
            "written down nowhere in the warehouse, and cancelled orders are left out of every "
            "count. Eastern time: timestamps are stored in Coordinated Universal Time, but the "
            "business counts its days in Eastern time, so an order at 9 in the evening lands on "
            "the next day if you do not convert it. Internal accounts: staff and test accounts "
            "use the company's own email domain and are left out of every metric. The last three "
            "are safety rules. Read-only: the agent only reads, and the database itself refuses "
            "any write, whatever the query says. Personal data: a query that returns customer "
            "emails, phone numbers or names waits for a person's approval; using an email in a "
            "filter, as every revenue query does to drop internal accounts, does not. Approvals: an answer "
            "that is held posts only after a person approves it, and when a new version of the "
            "rules is promoted, the approver types their name. Every answer must follow all "
            "eight, and the schema states none of them.",
            "The point to land: The rules that decide whether an answer is right live outside "
            "the schema, so the agent cannot read them there.",
            "Example: Monday's answer broke three at once: calendar dates, the wrong time zone, "
            "and internal accounts left in. With none of the rules written for the agent, 0 of "
            "99 runs on 33 trap questions passed, calibration experiment 322f604d.",
            'Ask the room: "Which of these five traps does your warehouse have?" Expect: a '
            "fiscal calendar and test accounts, almost everyone.",
            "Misconceptions: That a prompt line saying read-only makes the agent safe. The "
            "database's grants enforce it; the prompt only asks.",
            "Transition: With the rules in place, here is how we measure whether each loop helps.",
        ],
    ),
    # 21 how we measure -------------------------------------------------------------------------
    dict(
        kind="concept",
        title="How we'll measure: The same questions, before and after",
        minutes=2.5,
        says="The same question with and without each loop, checked on two databases, run "
        "several times, on development and holdout questions, with planted bugs",
        src=".dev/review/deck3-diagrams-concept.md, how-we-measure; docs/benefits.md; "
        "docs/calibration-report.md, Setup; pack.yaml evaluation; sources.py entry 12",
        figure={
            "diagram": "how-we-measure",
            "alt": "Benchmark questions, development or holdout, asked two ways with the same questions,"
            " model, and data: without the change, its protection off by a planted bug or the "
            "starting version, and with the change, its protection on; repeated runs on each "
            "side; every run checked against gold results on two databases, or by the forced "
            "failure seen; and the results read as counts per side, not rates",
        },
        on_slide=[
            "Lead: Each loop is measured as a pair: same questions, model and data, with and "
            "without it.",
            "Key idea: One question, measured the same way, before and after each loop.",
        ],
        notes=[
            "Purpose: Show how every measurement today was made, so each number later can be "
            "read the same way.",
            "What to say: Every number today comes from a pair like this, and each section's "
            "evidence slide says which questions and how many runs. The key idea says one question: every question is asked both ways, the same way. Five ideas. One: the same "
            "questions with and without a change. Start at the left: benchmark questions. They "
            "go down two paths, and the dashed box says what stays fixed: the same questions, "
            "model and data. Two: planted bugs where a failure must be forced. On the top path "
            "the protection is off, by a planted bug or, in Section 4: Hill-climbing loop, the "
            "starting rules; in the demos the failure then happens every time. On the bottom "
            "path the protection is on. Three: repeated runs. The model can answer differently "
            "on the next run, so each side runs several times. Four: gold checked on two "
            "databases, where a gold answer exists. The result is compared with the "
            "hand-checked gold result on two databases with the same schema and different data, "
            "so a query that only recalls a number cannot match both; Zhong and colleagues "
            "showed that one database can pass a wrong query, Source [^12]. The event loop's "
            "demos have no gold answer: there we count what happened, posts, losses and stops. "
            "Five: development and holdout questions. The rule writers may study the development "
            "questions; the holdout questions are kept from them and decide whether a change "
            "goes live. Last box: counts per side, such as 17 of 21, not rates.",
            "The point to land: Change one thing, keep everything else fixed, repeat the runs, "
            "and check the result, never the query text.",
            "Example: The benchmark holds 25 development and 15 holdout questions. A holdout "
            "question runs three times and passes on two of the three; one experiment is 70 "
            "runs.",
            'Ask the room: "How does your team know a prompt change helped?" Expect: someone '
            "tried a few questions by hand.",
            "Misconceptions: That one passing run proves a fix. Answers vary between runs, so "
            "one pass is a sample of one.",
            "Transition: Last, the words we use for all of this, on one slide.",
        ],
    ),
    # 22 the glossary ---------------------------------------------------------------------------
    dict(
        kind="table",
        title="Glossary: The terms used in every section",
        minutes=2,
        says="The specification's terms and the reviewer, two term-meaning pairs a row",
        src="the owner's specification of 27 October 2026, section 3, item 9; docs/glossary.md; "
        "pack.yaml limits and evaluation",
        on_slide=[
            "Lead: Two terms a row; come back here when a word is new.",
            "| Term | Meaning | Term | Meaning |",
            "|---|---|---|---|",
            "| Agent loop | Call tools, read results, repeat | "
            "Idempotency key | Repeats of one meaning absorbed |",
            "| Run budget | Tokens one run may spend | "
            "At-least-once delivery | An event may arrive more than once |",
            "| Answer envelope | Status, answer, evidence, assumptions | "
            "Lease | A job claim that expires |",
            "| Gold answer | The checked right result | "
            "Checkpoint | Saved state a restart resumes |",
            "| Execution match | Matches gold on two databases | "
            "Kill switch | Stops every run, checked each step |",
            "| Trap question | Hinges on an unstated business rule | "
            "Autonomy level | Report-only, assisted, or unattended |",
            "| Run | One question, start to final status | "
            "Overfitting | Fits the questions, not the rule |",
            "| Development, holdout | Studied; kept back from the rule writers | "
            "Promotion gate | Decides if new rules go live |",
            "| Regression | Passed before a change, fails after | "
            "Metric family | Questions on one measure |",
            "| Planted bug | A flag that turns one protection off | "
            "Reviewer | Judges each answer before it posts |",
        ],
        notes=[
            "Purpose: Define the twenty terms every section uses, in a few words each, and expand "
            "the few whose meaning is not obvious.",
            "What to say: Twenty terms; read the slide, and I expand the few whose "
            "meaning is not obvious. The answer envelope is what a run returns: its status, its "
            "answer, the evidence behind it, the query and its rows, and the assumptions it "
            "made, so a check can read it instead of trusting prose. A run ends posted, held for a "
            "person's approval, or escalated: stopped without an answer and handed to a person "
            "with its reasons. An execution match means the agent's query returns the same "
            "result as the gold query on both databases; we compare results, never query text. "
            "The run budget is the most tokens one run may spend, 60,000 here, beside limits on "
            "model calls and tool calls, all enforced in code. On the right, an idempotency key is one key per meaning of an "
            "event, so a repeat finds its key and does nothing new; we need it because of "
            "at-least-once delivery. A lease is a job's claim on a worker that expires if the "
            "worker dies, so another worker can take the job. And the promotion gate is the "
            "check a new version of the rules must pass before it goes live. The reviewer is "
            "DataPilot's judge: a second model that reads each answer before it posts.",
            "The point to land: Every word on a later slide is defined here first.",
            "Example: The fiscal year 2025 question is a trap question in the revenue family; "
            "its first answer was held by the reviewer.",
            'Ask the room: "Which term do you use differently at work?" Expect: lease.',
            "Misconceptions: That an execution match compares query text. It compares results.",
            "Transition: Next: how a text-to-SQL system is designed, before any loop.",
        ],
    ),
]
