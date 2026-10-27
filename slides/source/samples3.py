"""Sample slides of design system 3, one of every type, with full speaker notes.

The third rebuild's proof and the content writers' model: each slide follows the schema of
slides/design-system.md, section "The third rebuild (design system 3)", and the format of the
previous module's deck, uses real course content, and states only numbers from the paired
measurements page, the calibration report, or a listed source. The copied types (the
introduction, the instructor profile, the seven logistics slides, Ask about anything, the break
and the poll) hold the visible text of the reference's slide, adapted to the course's style, as
lines in the order the deck builder fills them. This module is not a block of the class deck:
build.py --samples OUT samples3 writes its outline, and the deck builder's --type-samples3 flag
builds it. Each slide names the block it would belong to, for its colours.
"""

RULES = "design system 3"

DEMO_PAGE = "https://github.com/ANI-IN/loop-engineering/tree/main/section-1-agent-loop/demo"
EXPECTED = "section-1-agent-loop/demo/expected/"


def short(purpose: str, say: str, transition: str, *do: str) -> list[str]:
    """The short notes form: Purpose, What to say, any Do lines, Transition."""
    return [
        f"Purpose: {purpose}",
        f"What to say: {say}",
        *(f"Do: {x}" for x in do),
        f"Transition: {transition}",
    ]


SLIDES = [
    # title ---------------------------------------------------------------------------------------
    dict(
        kind="title",
        block="opening",
        title="Loop Engineering for Data Agents",
        minutes=1,
        says="The course title and the subtitle in the reference's style",
        src="the owner's specification of 27 October 2026, section 2",
        on_slide=[
            "Loop Engineering for Data Agents",
            "Agent, verification, events, improvement: build each loop, then measure it",
            "Text-to-SQL, SQL being Structured Query Language",
        ],
        notes=short(
            "Open the class and name what learners leave able to do.",
            "Welcome to Loop Engineering for Data Agents. Today we build one text-to-SQL agent "
            "and the four loops around it: the agent loop, the verification loop, the event loop "
            "and the hill-climbing loop. We build each loop, then we measure it, live, on the "
            "real model.",
            "First, who is teaching today.",
        ),
    ),
    # intro (copied) ------------------------------------------------------------------------------
    dict(
        kind="intro",
        block="opening",
        title="Introduction",
        minutes=0.5,
        says="The instructor introduces themselves",
        src="the reference deck, slide 2",
        on_slide=["**Introduction -** {Instructor_Details}"],
        notes=short(
            "Introduce the instructor.",
            "Introduce yourself in two sentences: what you build, and one loop that saved you, "
            "or cost you, in production.",
            "Before we begin, tell us about yourself in the chat.",
            "Replace {Instructor_Details} with your name before class.",
        ),
    ),
    # profile (copied) ----------------------------------------------------------------------------
    dict(
        kind="profile",
        block="opening",
        title="Welcome to today's class",
        minutes=0.5,
        says="Learners post their name, role, location and company in the chat",
        src="the reference deck, slide 3",
        on_slide=[
            "Welcome to today’s class, before we begin,",
            "pop into the chat:",
            "{Instructor_Name}",
            "{Instructor_Role}",
            "{Instructor_Location}",
            "{Instructor_Company}",
        ],
        notes=short(
            "Get every learner talking in the chat in the first minute.",
            "Before we begin, pop into the chat and tell us four things about yourself: your "
            "name, your role, where you are, and your organization. I go first.",
            "Here is how the class runs.",
            "Fill in the four placeholders with your own details before class.",
        ),
    ),
    # logistics (copied), its seven variants ------------------------------------------------------
    dict(
        kind="logistics",
        variant="structure",
        block="opening",
        title="Structure of Class",
        minutes=1,
        says="The live class, then the assignments",
        src="the reference deck, slide 4",
        on_slide=[
            "Structure of Class",
            "Sunday Class - 4 hours (Sunday)",
            "**Assignments -** Quiz and coding assignment",
        ],
        notes=short(
            "Set the shape of the class: the live session, then the assignments.",
            "This class follows the shape of every class in the program: a four-hour live "
            "session on Sunday, then a quiz and a coding assignment. The session is recorded. "
            "Pace yourself: four hours is long, and the breaks are there for a reason.",
            "How to get the most out of it.",
        ),
    ),
    dict(
        kind="logistics",
        variant="optimise",
        block="opening",
        title="Optimize Your Experience",
        minutes=0.5,
        says="Interact, ask, do the assignments, use the resources",
        src="the reference deck, slide 5",
        on_slide=[
            "Optimize Your Experience",
            "Interact with your instructors in Sunday's live class.",
            "Don’t be shy to speak up and ask for clarifications!",
            "Solve your assignments, quizzes and other assessments and get feedback (Thursday "
            "review session)",
            "Use your resources! It’s your experience – what you put in is what you’ll get out.",
        ],
        notes=short(
            "Ask learners to take part and to use the review session.",
            "Interact, ask when something is unclear, solve the assignments, and bring your "
            "questions to the Thursday review session.",
            "And you are not on your own.",
        ),
    ),
    dict(
        kind="logistics",
        variant="support_team",
        block="opening",
        title="Don't worry! We are here to help",
        minutes=0.5,
        says="The support team is there at every step",
        src="the reference deck, slide 6",
        on_slide=["Don’t worry!", "We are here to help at your every step!", "But, how???"],
        notes=short(
            "Reassure learners that help is available.",
            "Don't worry: we are here to help at every step of the course, in class and after "
            "it. Here is how.",
            "The support features.",
        ),
    ),
    dict(
        kind="logistics",
        variant="support_features",
        block="opening",
        title="Support features",
        minutes=0.5,
        says="Uplevel, videos, coaching, Discord, teaching assistants, support tickets",
        src="the reference deck, slide 7",
        on_slide=[
            "Are you using all these support features?",
            "**Uplevel** - holds all the learning resources: videos, quizzes, assignments",
            "Optional **Post class videos** for additional reference",
            "**Technical coaching sessions** on Wednesday to clarify all your queries",
            "**Discord** community for peer learning",
            "**Teaching assistants** to help answer the queries in the live class",
            "**Support tickets** - raise one on Uplevel any time you need a clarification",
        ],
        notes=short(
            "Name every support channel once.",
            "Uplevel holds everything; the coaching sessions on Wednesday answer your questions; "
            "Discord is for learning from each other; the teaching assistants answer in the chat "
            "today; and a support ticket on Uplevel reaches us any time.",
            "Some habits that help.",
        ),
    ),
    dict(
        kind="logistics",
        variant="success",
        block="opening",
        title="Success Hacks",
        minutes=0.5,
        says="Habits that help learners finish",
        src="the reference deck, slide 8",
        on_slide=[
            "Success Hacks",
            "Be prepared for the class by watching the pre-class videos",
            "Attend every class",
            "Participate in class",
            "Attempt all the assignments",
            "Actively advocate for yourself",
            "Keep your goal in mind",
            "Consistency is the key",
            "Be patient with yourself!",
        ],
        notes=short(
            "Share the habits that help learners finish.",
            "The pre-class videos are required and make today easier; the post-class videos are "
            "optional and nothing later depends on them. Above all: be consistent, and be "
            "patient with yourself.",
            "Now the two keys you need today.",
        ),
    ),
    dict(
        kind="logistics",
        variant="api_key",
        block="opening",
        title="Check Your Email for Your OpenAI Key",
        minutes=1,
        says="The OpenAI key from operations, its 3-dollar limit, and where to ask",
        src="the reference deck, slide 9; the owner's specification of 27 October 2026",
        on_slide=[
            "Check Your Email for Your OpenAI Key",
            "You should have received an email from operations with your OpenAI key, limited "
            "to 3 dollars.",
            "If you do not see this email:",
            "Please check your inbox",
            "Also check your spam or junk folder",
            "If you still cannot find it, please reach out to the Operations Team "
            "{operations_email}",
            "{API_Key_Email_Screenshot}",
        ],
        notes=short(
            "Make sure every learner has the OpenAI key for the assignments.",
            "The Operations Team emailed you an OpenAI key with a 3-dollar limit, enough for "
            "every assignment check. If it is not in your inbox or your spam folder, write to "
            "the address on the slide.",
            "And the tracing key.",
            "Replace the placeholder card with a screenshot of the real email once one is sent.",
        ),
    ),
    dict(
        kind="logistics",
        variant="langsmith",
        block="opening",
        title="LangSmith Setup Guide",
        minutes=1,
        says="The steps to a LangSmith key, and the free plan's trace limit",
        src="the reference deck, slide 10; README.md, the free plan's limit",
        on_slide=[
            "LangSmith Setup Guide",
            "Steps to Generate a LangSmith API Key",
            "Note: The free plan allows 5,000 traces a month; the class stays well inside it.",
        ],
        notes=short(
            "Make sure every learner can see the traces of their runs.",
            "Every run you make today and in the assignments sends a trace to LangSmith. The "
            "free plan allows 5,000 traces a month, and the class stays well inside it. Follow "
            "the guide behind the link to create your key.",
            "Before the problem, a two-slide recap of the previous module.",
        ),
    ),
    # concept: a recap of the previous module ------------------------------------------------------
    dict(
        kind="concept",
        block="opening",
        title="Recap: Harness engineering made one run trustworthy",
        minutes=2.5,
        says="The previous module's four layers around one agent run",
        src="the owner's specification of 27 October 2026, section 2, item 3",
        figure={
            "diagram": "harness-recap",
            "alt": "One agent run in the middle, with the four harness layers around it: "
            "instructions, what it knows; state, what it remembers; scope, what it may change; "
            "verification, what proves it is done.",
        },
        on_slide=[
            "Lead: A harness wraps one agent run: what it knows, remembers, may change, proves.",
            "Key idea: One run is trustworthy; production runs many, unattended, and changes.",
        ],
        notes=[
            "Purpose: Recall the previous module's harness in one picture, as the base this "
            "module builds on.",
            "What to say: Last module you built a harness around a coding agent. Walk the picture "
            "from the middle out. In the middle is one agent run: the model, its tools, and one "
            "task. Around it are four layers. Instructions decide what the agent knows: a short "
            "map of where each rule lives, with the details loaded on demand. State decides what "
            "it remembers when a session ends: a handoff file and a progress log that the next "
            "session reads first. Scope decides what it may change: allowed paths per phase, "
            "checked by code, inside a sandbox. Verification decides what proves the work is "
            "done: checks the agent does not own, run when it claims it is finished. Each layer "
            "is code and files around an unchanged model. Together they made one run "
            "trustworthy. Today the question changes. A data agent in production does not run "
            "once: it runs many times a day, it runs from events with nobody watching, and the "
            "knowledge it runs on changes week by week. A harness around one run does not cover "
            "that, which is why this module is about loops.",
            "The point to land: The harness made one run trustworthy; loops make a system of many "
            "runs trustworthy over time.",
            "Example: The previous module's verification layer ran hidden tests when the agent "
            "said done; today's verification loop checks every answer before it is posted.",
            'Ask the room: "Which of the four layers did you add to your own agent?" Expect: '
            "instructions, most often.",
            "Misconceptions: That loops replace the harness. Every loop today runs inside a "
            "harness of its own; the loops add what one run cannot show.",
            "Transition: The next slide says what the loops add.",
        ],
    ),
    # agenda: the opening's, with no star ---------------------------------------------------------
    dict(
        kind="agenda",
        block="opening",
        title="Today's Agenda",
        minutes=1.5,
        says="The four loops, one per section, no star yet",
        src="the owner's specification of 27 October 2026, section 2, item 4",
        on_slide=[
            "1. Agent loop: what can the agent see?",
            "2. Verification loop: is the answer right?",
            "3. Event loop: does it run unattended?",
            "4. Hill-climbing loop: does it improve safely?",
        ],
        notes=[
            "Purpose: Show the plan of the class: four loops, one per section.",
            "What to say: Four loops, one per section, each a question about the same agent. "
            "What can it see? Is its answer right? Does it run with nobody watching? Does it get "
            "better without breaking what works? Before each section this slide comes back with "
            "a star on the loop we are about to build.",
            "The point to land: Four loops around one agent, built in this order.",
            "Example: The fiscal year 2025 question runs through all four.",
            'Ask the room: "Which question does your agent answer worst today?" Expect: is the '
            "answer right.",
            "Misconceptions: That the four are alternatives. They stack: each works on the "
            "output of the one before.",
            "Transition: First, the problem these loops solve.",
        ],
    ),
    # concept -------------------------------------------------------------------------------------
    dict(
        kind="concept",
        block="problem",
        title="Why we need loops: The four critical gaps",
        minutes=3,
        says="Each failure of the week has a cause, and each cause gets one loop",
        src="the owner's specification of 27 October 2026, section 3, item 5",
        figure={
            "diagram": "four-critical-gaps",
            "alt": "Four causes, each over the loop that answers it: cannot see enough over the "
            "agent loop, nothing checks the answer over the verification loop, unattended runs "
            "break over the event loop, changes are not measured over the hill-climbing loop.",
        },
        on_slide=[
            "Lead: Each story has a cause, and each cause gets one loop.",
            "Key idea: One loop per cause.",
        ],
        notes=[
            "Purpose: Turn the week of failures into four causes, and give each cause the loop "
            "that answers it.",
            "What to say: The week of failures looks like five different problems. Look at what "
            "caused each, and there are only four causes, one per column. Walk the diagram from "
            "left to right. First column: the agent cannot see enough. It sees the warehouse only "
            "through its tools, so a column named amount tells it nothing about discounts, and an "
            "unbounded result floods its context. The agent loop answers that: tools that show "
            "the right view, capped, with stops in code. Second column: nothing checks the "
            "answer. A clean query that returns a plausible number is not a right number. The "
            "verification loop answers that: parse the query, enforce grants, retry with "
            "feedback, and send doubtful answers to a person. Third column: unattended runs "
            "break. Events arrive more than once, workers restart, and someone presses stop. The "
            "event loop answers that: keys by meaning, leases, durable approvals and a kill "
            "switch. Fourth column: changes are not measured. Someone adds a rule that fixes one "
            "question and breaks nine. The hill-climbing loop answers that: gold questions, a "
            "holdout the improver never sees, and a gate. Read the arrows downward: a cause, "
            "then its loop. Nothing in this diagram changes the model; every loop is code "
            "around it.",
            "The point to land: Each failure has a cause outside the model, and each cause gets "
            "one loop of code around the same model.",
            "Example: Monday's wrong revenue is the first column; Wednesday's duplicate digests "
            "are the third.",
            'Ask the room: "Which column is your agent missing today?" Expect: the verification '
            "loop or the hill-climbing loop.",
            "Misconceptions: That a stronger model closes these gaps. Each gap is in the system "
            "around the model; a stronger model reads the same schema and makes the same guess.",
            "Transition: Before we build anything, here is the data the agent works on.",
        ],
    ),
    # agenda --------------------------------------------------------------------------------------
    dict(
        kind="agenda",
        block="s1",
        title="Today's Agenda",
        minutes=0.5,
        says="The four loops, the star on the agent loop",
        src="the owner's specification of 27 October 2026, section 1",
        on_slide=[
            "1. Agent loop: what can the agent see?",
            "2. Verification loop: is the answer right?",
            "3. Event loop: does it run unattended?",
            "4. Hill-climbing loop: does it improve safely?",
            "Now: 1",
        ],
        notes=[
            "Purpose: Show where the class is: the first of the four loops.",
            "What to say: Four loops, one per section. The star is on the first: the agent loop, "
            "and what the agent can see. We start here because every later loop checks, runs or "
            "improves what this one produces.",
            "The point to land: The agent loop comes first: the others work on its output.",
            "Example: The fiscal year question runs through all four sections.",
            'Ask the room: "Which loop do you expect to matter most?" Expect: the verification '
            "loop.",
            "Misconceptions: That the loops are layers of one prompt. Each is code.",
            "Transition: Here is the failure this section fixes.",
        ],
    ),
    # problem rows --------------------------------------------------------------------------------
    dict(
        kind="problem",
        block="problem",
        title="Problem statement: The problem in the real world",
        minutes=3,
        says="A week of business questions, one failure a day",
        src="the owner's specification of 27 October 2026, section 3, item 2; docs/benefits.md; "
        ".dev/deck-evidence.md",
        on_slide=[
            "Lead: Your team gives a week of business questions to a data agent.",
            "- **Monday:** fiscal year 2025 revenue comes back as $72,394,572.08, fluent and "
            "wrong; nothing errors | warning",
            "- **Tuesday:** a product name with hidden instructions slips a DELETE past a "
            "first-word check | lock",
            "- **Wednesday:** the chat tool resends one event three times; leadership gets two "
            "digests | copy",
            "- **Thursday:** a worker restarts and an approval is lost; a stopped run posts "
            "anyway | pause",
            "- **Friday:** a plausible rule, exclude discounted orders, quietly breaks nine "
            "answers | branch",
            "Footer: Each failure costs more than the question saved.",
        ],
        notes=[
            "Purpose: Make the course's problem concrete: one week of business questions, one "
            "costly failure a day, each from the course's real runs.",
            "What to say: Picture your team giving a data agent a week of business questions. On "
            "Monday the finance lead asks for net revenue in fiscal year 2025. The answer comes "
            "back fluent, formatted, and confident: 72,394,572.08 dollars. It is wrong by about "
            "8.4 million dollars, and nothing errors. On Tuesday a product name in the catalogue "
            "carries hidden instructions, and the query the agent writes starts with a harmless "
            "word but carries a DELETE behind it; a check that reads only the first word lets it "
            "through. On Wednesday the chat tool sends the same event three times, as delivery "
            "systems do, and leadership receives two different digests for the same day. On "
            "Thursday a California customer export waits for a person's approval, the worker "
            "restarts, and the approval is gone; then someone presses stop, and the run posts "
            "anyway. On Friday an analyst adds a rule that sounds right, exclude discounted "
            "orders, and nine other answers quietly break. Each day the agent did what it was "
            "built to do. Each failure cost more than the question saved: a wrong number in a "
            "board deck, a deleted row, a confused leadership team, a leak of personal data, and "
            "a slow loss of trust in every answer.",
            "The point to land: The agent did not crash once this week; every failure looked "
            "like a success.",
            "Example: The Monday number is the course's own: the first live answer to the fiscal "
            "year 2025 question, held by the reviewer and never posted, against a gold answer of "
            "64,015,091.21 dollars.",
            'Ask the room: "Which day has your team already lived through?" Expect: Monday, the '
            "plausible wrong number, and Wednesday, the duplicate message.",
            "Misconceptions: That these are model failures. Each one is a missing piece of the "
            "system around the model, which is why the fix is a loop and not a better prompt.",
            "Transition: The rules for all of this exist. So why does the agent still miss?",
        ],
    ),
    # quotes --------------------------------------------------------------------------------------
    dict(
        kind="quotes",
        block="problem",
        title="The challenge is: The rules exist, the agent still misses",
        minutes=3,
        says="Three sources on why an agent with the rules nearby still misses",
        src="slides/source/sources.py entries 1, 4 and 5, each quote checked against the page",
        on_slide=[
            "Lead: The rules live in people's heads, policies and runbooks, not in the schema. "
            "The agent still misses, because:",
            "Quote: it's wasting its limited context space on irrelevant information | 4",
            "Quote: It can be prudent to check the agent’s SQL queries before they are executed "
            "for any unintended actions or inefficiencies. | 5",
            "Quote: The fourth (and arguably most important) automates improvement! | 1",
        ],
        notes=[
            "Purpose: Show, in the words of three published sources, why an agent misses rules "
            "that exist: context, checking, and improvement.",
            "What to say: Every rule from Monday's failure exists somewhere: in the finance "
            "team's heads, in a policy, in a runbook. None of it is in the schema, and the agent "
            "reads only the schema and what its tools return. Three sources say why that is not "
            "enough. The first is Anthropic's guide to writing tools for agents, Source [^4]. It "
            "warns that a tool returning everything leaves the agent wasting its limited context "
            "space on irrelevant information. Context is a budget, and what fills it decides what "
            "the agent can know. That is Section 1. The second is LangChain's tutorial for a SQL "
            "agent, Source [^5]. It says it can be prudent to check the agent's queries before "
            "they run. A tutorial already admits the model's query needs a check; we build that "
            "check in Section 2. The third is LangChain's article that names the four loops, "
            "Source [^1]. After three loops that automate work, it calls the fourth, the loop that "
            "automates improvement, arguably the most important. That is Section 4. Read the "
            "three together: the agent misses because it sees too little or too much, because "
            "nobody checks it, and because nobody measures what changes. Rules alone do not fix "
            "any of the three.",
            "The point to land: Writing the rules down is not enough; the agent must see them, be "
            "checked against them, and learn them safely.",
            "Example: The fiscal year rule was in the course's business rules page all along; "
            "the agent never saw it until Section 4 promoted it.",
            'Ask the room: "Where do your business rules live today?" Expect: a wiki, a few '
            "people, or a query someone wrote years ago.",
            "Misconceptions: That a longer prompt with every rule solves it. It crowds the "
            "context, goes stale, and nothing checks it.",
            "Transition: So what does a failure cost a data team, and what do the loops cost?",
        ],
    ),
    # costs ---------------------------------------------------------------------------------------
    dict(
        kind="costs",
        block="problem",
        title="Why this matters for data teams",
        minutes=2.5,
        says="What a failure costs, and what the loops cost, measured",
        src="docs/benefits.md, The comparison and Where a loop did not help",
        on_slide=[
            "Lead: Each failure costs the team; each loop costs too.",
            "Panel: What a failure costs",
            "- A wrong number in a board deck, believed",
            "- A data leak: personal data in an export",
            "- A duplicate alert: two digests for one day",
            "- A broken metric nobody notices",
            "Panel: What the loops cost, measured",
            "- Agent loop: 4,857 tokens a run, not 3,738",
            "- Verification loop: 17,344 tokens, not 9,311",
            "- Verification loop: 1.88 attempts, not 1.1",
        ],
        notes=[
            "Purpose: Weigh what a failure costs a data team against what the loops cost, with "
            "the course's measured numbers.",
            "What to say: Left panel: what a failure costs. A wrong number in a board deck is "
            "the worst kind of failure, because it is believed. A data leak costs a disclosure "
            "and an audit. A duplicate alert costs trust: after two digests for one day, people "
            "stop reading digests. A broken metric that nobody notices costs every decision made "
            "on it until someone does. Right panel: what the loops cost, measured on the course's "
            "runs of 24 October 2026. Better tools in the agent loop took more tokens per run on "
            "seven easy questions, 4,857 against 3,738, and answered 17 of 21 runs correctly "
            "against 12 of 21. The verification loop took 17,344 tokens per run against 9,311 on "
            "twenty trap questions, and 1.88 attempts a run against 1.1, because it retries with "
            "feedback. For that, it held or escalated 20 of the 40 wrong answers, against 1 "
            "without it. These are small numbers per run, fractions of a cent. Set them against "
            "one wrong number in a board deck and the trade is easy. But measure it: a loop that "
            "costs more and catches nothing is a cost, not a safeguard.",
            "The point to land: The loops cost tokens and seconds on every run; a failure costs "
            "trust once, and for a long time.",
            "Example: The 40 verification runs cost 0.0605 dollars with the loop and 0.0361 "
            "without it, measured on the paired measurements page.",
            'Ask the room: "What did your last wrong number cost?" Expect: a meeting, a '
            "correction email, and some trust.",
            "Misconceptions: That the loops are free. They are not; we measure their cost the "
            "same way we measure their benefit.",
            "Transition: Each story has a cause. Here are the four.",
        ],
    ),
    # table: the business rules (problem block) ----------------------------------------------------
    dict(
        kind="table",
        block="problem",
        title="Business rules: The rules in plain words",
        minutes=3,
        says="The five traps and the safety rules, each with an example",
        src=".dev/deck-evidence.md E1, E5, E6; the pack's business rules page; docs/benefits.md",
        on_slide=[
            "Lead: Five traps and three safety rules, each with an example.",
            "| Rule | Example |",
            "|---|---|",
            "| Fiscal year | Runs February to January, named for the year it ends |",
            "| Net revenue | Subtotal minus discount, never the total with tax and shipping |",
            "| Cancelled orders | Status 5 means cancelled; those orders are left out |",
            "| Eastern time | Days count in Eastern time; stored in Coordinated Universal Time |",
            "| Internal accounts | Staff and test accounts, known by email domain, are left out |",
            "| Read-only | The agent reads; it never writes or deletes |",
            "| Personal data | No customer email or phone number without human approval |",
            "| Approvals | A held answer posts only after a named person approves it |",
            "Key idea: Every answer must follow all of them; the schema states none of them.",
        ],
        notes=[
            "Purpose: State every business rule and safety rule in plain words, with an example "
            "each, so learners can recognise each trap later.",
            "What to say: Here are the rules an answer must follow, as the finance team would "
            "say them. The first five are the traps. The fiscal year runs February to January "
            "and is named for the year it ends, so fiscal year 2025 ends in January 2025. Net "
            "revenue is subtotal minus discount; the total column carries tax and shipping and "
            "looks like revenue. Status 5 means cancelled, and cancelled orders are left out; "
            "the code is written down nowhere in the warehouse. Days count in Eastern time, "
            "while timestamps are stored in UTC, so an evening order can land on the wrong day. "
            "Staff and test accounts are known only by the company's email domain, and they are "
            "left out. The last three are safety rules. The agent only reads: a query that "
            "writes or deletes must never reach the data. Personal data, a customer's email or "
            "phone number, leaves only with a person's approval. And a held answer posts only "
            "after a named person approves it. Every answer must follow all eight, and the "
            "schema states none of them.",
            "The point to land: The rules that decide whether an answer is right live outside "
            "the schema, so the agent cannot read them there.",
            "Example: Monday's wrong revenue broke three of them at once: calendar dates, the "
            "wrong time zone, and internal accounts left in.",
            'Ask the room: "Which of these five traps does your warehouse have?" Expect: a '
            "fiscal calendar and test accounts, almost everyone.",
            "Misconceptions: That documenting the columns fixes it. Column comments describe "
            "storage; these rules describe the business.",
            "Transition: Next, the words we use for all of this, in one place.",
        ],
    ),
    # table: the glossary, two term-meaning pairs a row --------------------------------------------
    dict(
        kind="table",
        block="problem",
        title="Glossary: The terms used in every section",
        minutes=2,
        says="Two term-meaning pairs a row; the terms every section uses",
        src="docs/glossary.md",
        on_slide=[
            "Lead: Two terms a row; come back here when a word is new.",
            "| Term | Meaning | Term | Meaning |",
            "|---|---|---|---|",
            "| Agent loop | Call the model, run its tool, repeat | Idempotency key | One key per "
            "meaning; repeats find it |",
            "| Tool budget | Most calls and tokens a run may use | At-least-once delivery | An "
            "event may arrive more than once |",
            "| Answer envelope | Status, query, rows, assumptions | Lease | A job's claim; it ends "
            "if its worker dies |",
            "| Gold answer | The checked right result of a question | Checkpoint | State a restarted "
            "run picks up from |",
            "| Execution match | Same rows as gold on both databases | Kill switch | A stop that "
            "every step checks first |",
            "| Trap question | A business rule makes it hard | Autonomy level | How far a run acts "
            "without a person |",
            "| Development questions | What the improver may learn from | Overfitting | Rules that "
            "fit only the seen questions |",
            "| Holdout questions | Kept from the improver, to decide | Promotion gate | Checks a "
            "change must pass to ship |",
            "| Regression | A right answer that turns wrong | Planted bug | A known fault, on to "
            "show a failure |",
        ],
        notes=[
            "Purpose: Define the terms every section uses, before any slide uses them.",
            "What to say: Two terms a row. An agent loop calls the model, runs the tool it asks "
            "for, and repeats until it answers. The tool budget is the most model calls, tool "
            "calls and tokens one run may use, enforced in code. The answer envelope is what a "
            "run returns: a status, the query, the rows and the assumptions it made, so a person "
            "or a check can read it. A gold answer is the checked right result of a benchmark "
            "question. An execution match means the agent's query returns the same rows as the "
            "gold query, on both of the course's databases, so it cannot match by recalling a "
            "number. A trap question is one whose right answer depends on a business rule the "
            "schema does not state. An idempotency key is one key per meaning of an event, so a "
            "repeat of the same event finds its key and does nothing new. And a lease is a job's "
            "claim on a worker that expires if the worker dies, so another worker can pick the "
            "job up. Development questions are the ones the improver may learn from; holdout "
            "questions are kept from it and decide whether a change ships, at the promotion gate. "
            "Come back to this slide whenever a word is new.",
            "The point to land: Every word on later slides is defined here first.",
            "Example: The fiscal year 2025 question is a trap question with a gold answer of "
            "64,015,091.21 dollars.",
            'Ask the room: "Which of these terms do you use differently at work?" Expect: lease '
            "and idempotency key.",
            "Misconceptions: That an execution match compares numbers. It compares the rows, on "
            "two databases.",
            "Transition: Here is how we will measure every loop today.",
        ],
    ),
    # failure story -------------------------------------------------------------------------------
    dict(
        kind="failure",
        block="s1",
        title="Failure story: The revenue answer nobody questioned",
        minutes=2.5,
        says="Five steps from a reasonable question to a wrong number in a board deck",
        src="the owner's specification of 27 October 2026, section 3, item 2 (Monday); "
        ".dev/deck2-reconcile.md, The hook",
        on_slide=[
            "Lead: An illustrative question: what was net revenue in fiscal year 2025?",
            "1. The finance lead asks for net revenue in fiscal year 2025.",
            "2. The agent sees column names only and guesses the calendar year.",
            "3. Its query runs cleanly, so nothing errors and nothing is flagged.",
            "4. The answer reads well: $72,394,572.08, stated with confidence.",
            "5. The number reaches the board deck, wrong by about 8.4 million dollars.",
        ],
        notes=[
            "Purpose: Walk the illustrative path from a reasonable question to a costly wrong "
            "number, one step causing the next.",
            "What to say: This story is illustrative: it is how Monday's failure would play out "
            "if nothing stopped it. Step one: the finance lead asks a reasonable question, net "
            "revenue in fiscal year 2025. Step two: the agent sees the warehouse through its "
            "tools, and its tools show column names only. Nothing says the fiscal year starts in "
            "February, so it guesses the calendar year. Step three: its query is valid. It runs "
            "cleanly, returns one number, and nothing errors, so nothing raises a flag. Step "
            "four: the answer reads well. It states 72,394,572.08 dollars with confidence, "
            "formatted like every right answer. Step five, in red, is the costly end: the number "
            "reaches the board deck, wrong by about 8.4 million dollars, and every decision made "
            "on it inherits the error. Notice that each step is reasonable on its own. No step "
            "crashed, no step was malicious, and the model did what it was asked. The failure is "
            "in what the agent could see, which is where Section 1 starts, and in the fact that "
            "nothing checked the number, which is Section 2.",
            "The point to land: A wrong answer that looks right travels further than any crash.",
            "Example: In the course's runs the agent answered 72,394,572.08 dollars; the gold "
            "answer is 64,015,091.21. That run was held by the reviewer and never posted.",
            'Ask the room: "At which step could your system have stopped this?" Expect: step '
            "four, with a review, and step two, with better tools.",
            "Misconceptions: That a more careful prompt prevents step two. The rule is not in "
            "the data, so no prompt can make the agent see it.",
            "Transition: So why not simply give the agent everything?",
        ],
    ),
    # question ------------------------------------------------------------------------------------
    dict(
        kind="question",
        block="s1",
        title="Agent loop: Why not show the whole schema and every row?",
        minutes=2.5,
        says="The naive fix, more context, and why it fails",
        src="the owner's specification of 27 October 2026, section 4, item 3; sources.py "
        "entry 4; docs/benefits.md",
        on_slide=[
            "Lead: The warehouse is small enough to paste in. Why not give the agent everything?",
            "Key idea: Context is a budget: show what is needed, on demand, capped.",
            "1. A whole schema crowds out the question, and the right column gets lost",
            "2. One unbounded result can use up a run's whole token budget",
            "3. More context is not more knowledge: the business rules are not in it",
        ],
        notes=[
            "Purpose: Answer the naive fix, give the agent everything, with the section's key "
            "idea and three reasons.",
            "What to say: Here is the obvious fix for Monday. Our warehouse is small: five "
            "tables. Why not paste the whole schema into the prompt and let every query return "
            "all its rows? The key idea says no: context is a budget. Show what is needed, on "
            "demand, and capped. Three reasons. One: a whole schema crowds out the question. In "
            "a real warehouse with hundreds of tables, the right column is lost among the wrong "
            "ones, and every call pays for all of them. Anthropic's guide to tools makes the "
            "same point about tools that return everything, Source [^4]. Two: one unbounded "
            "result can use up a run's whole budget. In the course's runs, a 10,000-row result "
            "took 182,654 tokens with no row cap and 30,216 with it, a reviewer's round trip "
            "included. Three, and this one matters "
            "most: more context is not more knowledge. Pasting the schema shows every column "
            "named amount, and still says nothing about the fiscal year, cancelled orders or "
            "internal accounts. Monday's wrong answer would come back exactly as wrong, only "
            "slower and more expensive.",
            "The point to land: Giving the agent everything costs more and fixes nothing that "
            "matters; design what it sees instead.",
            "Example: The unbounded-rows demo shows the token counter jump on the uncapped run "
            "and stay low on the capped one.",
            'Ask the room: "How many tables does your warehouse have?" Expect: hundreds, which '
            "settles reason one.",
            "Misconceptions: That a long context window removes the budget. A long window still "
            "costs tokens and still buries the column that matters.",
            "Transition: So how should tools decide what the agent sees? The first technique.",
        ],
    ),
    # technique -----------------------------------------------------------------------------------
    dict(
        kind="technique",
        block="s1",
        title="1) Tools decide what the agent sees",
        minutes=2.5,
        says="Schema linking and progressive disclosure: the agent's whole view is its tools",
        src="the owner's specification of 27 October 2026, section 4, item 4; sources.py "
        "entry 4; section-1-agent-loop/README.md",
        figure={
            "diagram": "pattern-progressive-disclosure",
            "alt": "Progressive disclosure: a short list of names first, then the details of the "
            "one item the task needs, on demand.",
        },
        on_slide=[
            "- **What:** the agent sees the warehouse only through its tools; their outputs are "
            "its whole view.",
            "- **How:** list the tables first, describe one table on demand, and give each "
            "column's meaning, not only its name.",
            "- **Example:** a column named amount says nothing; net of discount, in cents, tells "
            "the agent how to sum it.",
            "- **Elsewhere:** a support agent's search tool shapes its answers the same way.[^4]",
            "Key idea: What a tool returns is all the agent knows; design that view first.",
        ],
        notes=[
            "Purpose: Teach the first technique: tools decide what the agent sees, through "
            "schema linking and progressive disclosure.",
            "What to say: The first technique is a change of mind. The agent never sees your "
            "warehouse. It sees what its tools return, and nothing else. So the tools are the "
            "agent's whole view, and designing them is designing what it can know. Walk the "
            "diagram from left to right. First a short list: the table names, cheap to show "
            "every time. Then, only when the task needs it, the details of one table: its "
            "columns, their types, and what each one means. That is progressive disclosure: "
            "names first, details on demand. Schema linking is the step in between, choosing "
            "which tables and columns a question needs. The example on the slide is the one that "
            "matters for Monday: a column named amount says nothing, while a description that "
            "says net of discount, in cents, tells the agent how to add it up. The same design "
            "shows up outside data agents. Anthropic's guide to writing tools for agents, Source "
            "[^4], makes the point for search tools: return what the task needs, not everything. "
            "In the course's runs, better descriptions and capped rows took easy questions from "
            "12 of 21 correct runs to 17 of 21.",
            "The point to land: Design the tools' outputs before you touch the prompt; they are "
            "everything the agent knows.",
            "Example: DataPilot's describe tool returns each column's description from the "
            "pack, so the agent reads that revenue is net of discount.",
            'Ask the room: "What does your agent see when it lists your tables?" Expect: names '
            "only, or everything at once.",
            "Misconceptions: That descriptions fix the traps. They help easy questions; the "
            "business rules still need the hill-climbing loop.",
            "Transition: Next: what happens when a tool returns too much.",
        ],
    ),
    # design callout ------------------------------------------------------------------------------
    dict(
        kind="design_callout",
        block="s1",
        title="Text-to-SQL design: Schema exposure and value lookup",
        minutes=1.5,
        says="How much schema the agent sees, and how it finds values, by warehouse size",
        src="section-1-agent-loop/assignment/README.md; sources.py entries 44 and 49",
        on_slide=[
            "Lead: Two decisions of the agent loop, by the size of your warehouse.",
            "Decision: how much schema to show, how to find values",
            "| Choice | Small warehouse | Large warehouse |",
            "|---|---|---|",
            "| Tables | List every name | An agent picks tables; a person confirms[^49] |",
            "| Columns | Describe on demand | Prune to the columns in play[^49] |",
            "| Values | Look up before filtering | Match stored values, fix spelling[^44] |",
            "DataPilot: lists every table, describes on demand; value lookup is Assignment 1.",
        ],
        notes=[
            "Purpose: Turn the agent loop into the schema and value decisions of the learner's "
            "own text-to-SQL design, by warehouse size.",
            "What to say: The agent loop holds two text-to-SQL decisions, and the answer depends "
            "on the size of your warehouse. Read the table by row. Tables: in a small warehouse, "
            "list every name; in a large one, an agent proposes candidate tables and a person "
            "confirms them, as Uber's table agent does, Source [^49]. Columns: describe on demand "
            "in a small one; in a large one, prune to the columns in play, Source [^49]. Values: "
            "always look a value up before filtering on it; Databricks maps the user's words to "
            "stored values, Source [^44]. DataPilot's warehouse is small, so it lists every table "
            "and describes on demand. Value lookup is Assignment 1: a tool that finds the stored "
            "value closest to the user's words, records the match in the envelope's assumptions, "
            "and asks the user when two stored values are equally close. Decide which column of "
            "this table you are in before you write a prompt: a large warehouse needs the "
            "retrieval step and its review, and a small one only needs good descriptions.",
            "The point to land: Size decides how much schema to show; values are always looked "
            "up, never typed in from the question.",
            "Example: The catalogue holds two spellings of one backpack; a lookup must ask which "
            "one, not pick.",
            'Ask the room: "Which column of this table is your warehouse?" Expect: most say large.',
            "Misconceptions: That retrieval removes the need for review. Retrieval can miss the "
            "table that matters.",
            "Transition: Now let us run the loop live.",
        ],
    ),
    # table: the cheat sheet ----------------------------------------------------------------------
    dict(
        kind="table",
        block="s1",
        title="Cheat Sheet: The agent loop in four techniques",
        minutes=1.5,
        says="The section's four techniques: what each does and how to apply it",
        src="section-1-agent-loop/README.md, Apply it in a real system",
        on_slide=[
            "Lead: Refer back to this when you design your own agent's tools.",
            "| Technique | What it does | How to apply it in your system |",
            "|---|---|---|",
            "| Tools decide what it sees | Names first, details on demand | Print what each "
            "tool returns for a table |",
            "| Cap rows in the tool | At most 50 rows, a count, a notice | Cap rows and values "
            "in every list tool |",
            "| Stops in code | Ends a run at its budget | Read the limits from settings |",
            "| Value lookup | Matches words to stored values | Look a value up before a filter |",
        ],
        notes=[
            "Purpose: Sum up the section's four techniques as a table learners can apply to "
            "their own agent.",
            "What to say: Four techniques, one row each. Tools decide what the agent sees: show "
            "the names first and a table's details only when the task needs them; to apply it, "
            "print exactly what each of your tools returns for one real table and read it as the "
            "model would. Cap rows in the tool: a list tool returns at most 50 rows, the total "
            "count and a notice, so one result cannot flood the run; give every list tool a row "
            "cap and a cap on each value's length. Stops in code: the run ends when it reaches "
            "its budget of calls and tokens, whatever the model wants; read those limits from "
            "settings, never from the prompt. Value lookup: match the user's words to the values "
            "the warehouse stores before filtering on them, and ask when two are equally close. "
            "Read the table as a checklist for next week: one row, one change to your tools or "
            "your code, each small enough for an afternoon.",
            "The point to land: Each technique changes the tools and the code around the model, "
            "not the prompt.",
            "Example: The capped run of the unbounded-rows demo showed 50 of 10,000 rows with "
            "the notice.",
            'Ask the room: "Which row would take you longest to apply?" Expect: value lookup.',
            "Misconceptions: That a cap hides answers. The count and the notice tell the agent "
            "to filter or aggregate.",
            "Transition: Now let us run the loop live.",
        ],
    ),
    # demo ----------------------------------------------------------------------------------------
    dict(
        kind="demo",
        block="s1",
        title="Section 1: Agent loop - Implementation Notes: Right, then wrong",
        minutes=12,
        says="The simple question, live, with its tools, tokens and envelope",
        src="platform/demos/registry.yaml (section agent-loop); "
        "section-1-agent-loop/demo/walkthrough.md",
        on_slide=[
            "Badge: DEMO - 1",
            "What to watch for:",
            "- Simple: each tool call, then an envelope",
            "- Wrong answer: fluent, then misses gold",
            "- Unbounded rows: tokens, cap off then on",
            "Guaranteed moment: a confident, wrong fiscal year 2025 revenue answer, each trap "
            "named on its query.",
            "Link: Demo page on GitHub | " + DEMO_PAGE,
        ],
        notes=[
            "Purpose: Run the agent loop live: one correct answer first, so learners see the "
            "loop end to end.",
            "What to say: Let's watch the agent loop answer, live. Nothing here is recorded and "
            "nothing is scripted: each run calls the class model, and the model chooses its own "
            "tools. First a simple question, so you see the loop work end to end. Watch three "
            "things: the tool timeline, the envelope, and the token counter. When the result "
            "lands I will read its numbers aloud and show its live stamp, the start time and the "
            "trace link, so you know it ran just now.",
            "Demo: The simple question.",
            "Command: First check the status line: the report-only level, the kill switch "
            'released, and Planted None. Then type "How many orders have been placed in total?" '
            "in the console and press Agent > Ask; or, in the demo terminal, make demo "
            "NAME=agent-simple-question.",
            "Point at: the tool timeline as each call appears, list_tables, describe_table, "
            "run_query; then the count query and the envelope's status; then the tokens and "
            "cost; last the live stamp.",
            "Expected output: Posted, 405,738 orders, one count query, about 5,100 tokens and "
            "0.0005 dollars; 14 to 39 seconds in the recorded runs.",
            "While it runs: 14 to 39 seconds. Say that nothing is scripted: the model chose these "
            "tools itself, and the path can differ run to run.",
            "If it fails: 1. Read the status aloud. 2. If it stalls, run make reset "
            "NAME=agent-loop in the demo terminal (about 7 seconds). 3. Press Agent > Ask again.",
            "Backup screenshot: "
            + EXPECTED
            + "agent-simple-question-answer.png; show it only while the reset runs.",
            "The point to land: A clean run and a correct answer are different things; only the "
            "gold check tells them apart.",
            "Example: The count matched the warehouse on both databases.",
            'Ask the room: "What in the envelope would let a reviewer check this?" Expect: the '
            "query and its stated assumptions.",
            "Misconceptions: That the demo is rigged. The model chose every query.",
            "Transition: One run is a story. Next, the measurement.",
        ],
    ),
    # evidence ------------------------------------------------------------------------------------
    dict(
        kind="evidence",
        block="s1",
        title="Measured: With and without the agent loop's tools",
        scoreboard=1,
        minutes=2,
        says="Full descriptions, capped rows, the schema helper: 17 of 21 correct against 12",
        src="docs/benefits.md, Section 1: Agent loop",
        chart={
            "type": "column",
            "title": "Seven easy questions, 3 runs a side",
            "categories": ["Answered correctly", "Wrong, sent out"],
            "series": [("Without the tools", [12, 9]), ("With the tools", [17, 4])],
            "x_label": "Outcome of each run",
            "y_label": "Runs, out of 21",
            "maximum": 21,
        },
        on_slide=[
            "Lead: Seven easy questions, 3 runs a side: better tools, more right answers.",
            "Sample: 21 runs per side, seven questions asked 3 times each, reviewer off",
            "- **Without:** column names only, unbounded rows, no schema helper",
            "- **With:** full descriptions, capped rows, the schema helper",
            "- **Tokens a run:** 3,738, then 4,857",
        ],
        notes=[
            "Purpose: Show the measured effect of the agent loop's tool design, with its sample "
            "size and its cost, and where the fiscal year question stands.",
            "What to say: This is the paired measurement of 24 October 2026. Seven questions "
            "without traps, each asked three times on each side, so 21 runs per side, with the "
            "reviewer off on both sides. Without means column names only, unbounded rows and no "
            "schema helper; with means full descriptions, capped rows and the schema helper. "
            "Read the chart: 12 of 21 correct without, 17 of 21 with; wrong answers sent out fell "
            "from 9 to 4. The cost: more tokens per run, 4,857 against 3,738. Two cautions. This "
            "row mixes three changes, so it says what happened, not which change did it. And 21 "
            "runs per side is a direction, not a rate. The scoreboard says where the fiscal year "
            "question stands: the agent sees enough, but the answer is still wrong. Whether the "
            "schema helper earns its place is an open question for you: measure a helper before "
            "you keep it.",
            "The point to land: Better tools made more easy answers right, and did nothing for "
            "the business rules.",
            "Example: In dollars the 21 runs cost 0.0083 with the tools and 0.0097 without.",
            'Ask the room: "Which of the three changes would you test first, alone?" Expect: the '
            "descriptions.",
            "Misconceptions: That 17 of 21 is an accuracy rate. It is one session's count.",
            "Transition: Questions before we move on.",
        ],
    ),
    # Ask about anything (copied) -----------------------------------------------------------------
    dict(
        kind="qa",
        block="s1",
        title="Ask about anything",
        minutes=2.5,
        says="Questions about the agent loop",
        src="the reference deck, slide 31",
        on_slide=[
            "No Question Is Too Small Every Question Deserves an Answer!!",
            "Ask about anything:",
            "Concepts from today's sections",
            "How this applies to your work",
            "Implementation details",
            "Clarifications on what we covered",
            "Quick Request",
            "Please do not mind if a question gets skipped accidentally",
            "Repost politely in chat if needed",
            "We will try our best to cover as many questions as possible",
            "**Remember:** If you're wondering about it, others probably are too.",
        ],
        notes=short(
            "Take questions on the agent loop before the next section.",
            "Take questions from the chat first; the teaching assistants pick the top ones. "
            "Likely: does a longer context window make the row cap unnecessary? No: it still "
            "costs tokens and buries the column that matters.",
            "Next, the verification loop.",
        ),
    ),
    # break (copied) ------------------------------------------------------------------------------
    dict(
        kind="break",
        block="break1",
        title="Time for a Break",
        minutes=10,
        says="A 10-minute break",
        src="the reference deck, slide 32",
        on_slide=[
            "Time for a Break",
            "A 10-minute break is starting now. Please return when the timer ends to continue "
            "the presentation",
        ],
        notes=short(
            "Give a 10-minute break.",
            "Time for a 10-minute break. I will write the return time in the chat now.",
            "Welcome back. Next, the event loop.",
            "Write the return time in the chat.",
        ),
    ),
    # poll (copied) -------------------------------------------------------------------------------
    dict(
        kind="poll",
        block="poll",
        title="Live Zoom Poll",
        minutes=5,
        says="Which of the four loops does your production agent have today?",
        src="the reference deck, slide 53; the owner's specification of 27 October 2026",
        on_slide=[
            "Live Zoom Poll",
            "We are launching a poll on Zoom. Please take 2 minutes to fill out the form.",
            "Question: Which of the four loops does your production agent have today?",
        ],
        notes=short(
            "Ask which of the four loops learners' production agents have today.",
            "One poll before the break: which of the four loops does your production agent have "
            "today? Pick every one that applies, or none.",
            "Read the counts aloud, then the break.",
            "Launch the Zoom poll with the four loops and None as its options.",
        ),
    ),
    # payoff --------------------------------------------------------------------------------------
    dict(
        kind="payoff",
        block="closing",
        title="Final: The question, answered",
        minutes=3,
        says="The fiscal year 2025 revenue question, wrong at the start and right at the end",
        src=".dev/deck2-reconcile.md, The hook and The payoff",
        on_slide=[
            "Lead: The fiscal year 2025 question, wrong at the start, right at the end.",
            "Before: first answer | $72,394,572.08",
            "After: matches gold | $64,015,091.21",
            "Level: unattended, earned",
            "Loop: Section 1 | One query, bounded cost",
            "Loop: Section 2 | Every check passed; nothing flagged",
            "Loop: Section 3 | Held, then posted once",
            "Loop: Section 4 | Learned rules, approved at the gate",
            "- Correctness: right on two databases",
            "- Safety: read-only; no personal data",
            "- Operations: one event, one post",
            "- Improvement: zero regressions",
            "Sample: same model throughout, only the knowledge changed; one published run",
        ],
        notes=[
            "Purpose: Close the story: the question that was wrong at the start is right, posted "
            "at an earned level, with each loop's part.",
            "What to say: At the start of class this question came back as 72,394,572.08 "
            "dollars: no error, a clean sentence, wrong by about 8.4 million dollars. In the "
            "middle, the same question, answered 64,015,091.21 dollars, which matches the gold "
            "answer on both databases. On the right is the level: it posted unattended, because "
            "the revenue family earned that level on its holdout questions. Now the scoreboard. "
            "The agent loop ran one query inside its budget. The verification loop passed every "
            "check and flagged nothing. The event loop took one webhook event, held it while the "
            "clearance re-runs finished, and posted it once. The hill-climbing loop supplied the "
            "learned rules, measured on questions the analyzer team never saw and approved at "
            "the gate by a named person. At the foot, the requirement groups, each checked "
            "against this run: right on two databases, read-only with no personal data, one "
            "event and one post, and no regression on the holdout questions. What one run cannot "
            "show was proved earlier in the day. The model never changed; only the knowledge "
            "did.",
            "The point to land: No single loop fixed the answer: the four together made a "
            "correct answer that could post with nobody watching.",
            "Example: The after card is run 59174f10, version 13 of the knowledge; the before "
            "card is run 9182df01, version 1, held by the reviewer and never posted.",
            'Ask the room: "Which requirement would your agent fail first?" Expect: correctness '
            "on business rules.",
            "Misconceptions: That an approval proves a person read the change. The gate needs a "
            "typed name; production systems use a signed-in identity.",
            "Transition: Here are the four loops side by side.",
        ],
    ),
    # closing list --------------------------------------------------------------------------------
    dict(
        kind="closing",
        block="closing",
        title="Summary: Key takeaways",
        minutes=3,
        says="Ten transferable lessons, one per line",
        src="the sections' READMEs; docs/benefits.md",
        on_slide=[
            "Lead: Ten lessons, each proved in a section today.",
            "1. Tools decide what the agent sees | Section 1",
            "2. Cap rows and values in the tool | Section 1",
            "3. Parse queries; never pattern-match them | Section 2",
            "4. Grants are walls; settings are preferences | Section 2",
            "5. A judge with the same knowledge shares its blind spots | Section 2",
            "6. Key events by their meaning | Section 3",
            "7. Approvals and stops live in the database | Section 3",
            "8. Decide on questions the improver never saw | Section 4",
            "9. Agents propose; code decides | Section 4",
            "10. Measure a loop before you keep it",
        ],
        notes=[
            "Purpose: Leave learners with ten lessons that transfer to any agent.",
            "What to say: Ten lessons, each proved in a section today. The agent sees only what "
            "its tools return, so design those first, and cap what they return in the tool, "
            "never in the prompt. Parse a query before it runs, and let the database's grants be "
            "the wall. A judge that knows what the analyst knows misses what the analyst misses. "
            "Key every event by what it means, and keep approvals and stops in the database, "
            "where a restart cannot lose them. Decide on questions the improver never saw, and "
            "let code, not an agent, decide what is promoted. And the last one, from every "
            "section: measure a loop before you keep it.",
            "The point to land: Every lesson here is a pattern you can apply to your own agent "
            "next week.",
            "Example: The design checklist in the notes of the closing turns each lesson into a "
            "question for your own system.",
            'Ask the room: "Which lesson will you apply first?" Expect: the row cap or the grants.',
            "Misconceptions: That these are DataPilot features. They are patterns; DataPilot is "
            "the worked example.",
            "Transition: The sources follow.",
        ],
    ),
    # references ----------------------------------------------------------------------------------
    dict(
        kind="references",
        block="closing",
        part=1,
        title="References (1 of 2): Sources in the order cited",
        minutes=0,
        says="Every source cited, numbered in order of first use, with its link",
        src="slides/source/sources.py",
        on_slide=["Lead: Every source cited today, numbered in order of first use, with its link."],
        notes=short(
            "List every source the sample cites, in the order first cited.",
            "These tables list every source cited today, in the order we first used each one, "
            "with its link. They stay on screen for anyone copying a link.",
            "The second table follows.",
        ),
    ),
    # references, part 2 --------------------------------------------------------------------------
    dict(
        kind="references",
        block="closing",
        part=2,
        title="References (2 of 2): The remaining sources",
        minutes=0,
        says="The sources cited after the first twelve",
        src="slides/source/sources.py",
        on_slide=["Lead: The rest of today's sources, with links."],
        notes=short(
            "List the sources cited after the first twelve.",
            "The second table lists the sources cited after the first twelve, in the same "
            "order, each with its link.",
            "That is the end of the sample slides.",
        ),
    ),
]
