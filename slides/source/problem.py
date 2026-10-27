"""The problem, 0:05-0:17: 4 problem statement slides under design system 2.

The owner's specification of 27 October 2026, section 3: the business situation, the obvious
solution and its five failures, the requirements, and the acceptance criteria, mapped onto the four
loops, whose names are revealed on the last slide. Each slide is 3 minutes with 300 to 400 words of
talk track and a question for the room.

Grounding: the company, its warehouse, its business rules and its questions come from
platform/packs/datapilot_us/ (pack.yaml, benchmark/business_rules.md, benchmark/dev.yaml) and the
demo registry. The four teams, the ticket queue and the mismatched definitions between teams are
not in the course materials: the notes say they are part of the scenario. No statistic is invented;
the slides hold no number from our runs, which belong to later sections.
"""

RULES = "design system 2"

SLIDES = [
    # 1 the business situation ------------------------------------------------------------------
    dict(
        kind="problem",
        title="Harbor & Pine needs answers it can trust",
        minutes=3,
        says="Four teams ask the warehouse everyday questions; today they wait on tickets and get "
        "mismatched numbers",
        src="platform/packs/datapilot_us/pack.yaml (display name); benchmark/dev.yaml (fiscal "
        "year revenue, best-selling products, first and repeat customers); "
        "platform/src/datapilot/demo_questions.py (the webhook question); demo registry, The "
        "approval that survives a restart (the California export); the teams and the ticket "
        "queue are the scenario's",
        on_slide=[
            "Lead: An outdoor retailer's teams ask the warehouse questions every day, and wait.",
            "- Finance: what was our net revenue in fiscal year 2025?",
            "- Operations: how many orders were placed the previous day?",
            "- Sales: which products sold the most units, by category?",
            "- Marketing: how many customers came back and ordered again?",
            "- Marketing: export our California customers for a campaign",
            "- Today: a ticket to a small data team, a wait, and two teams' numbers that disagree",
        ],
        notes=[
            "Purpose: Set the business situation: who asks the warehouse what, how they get "
            "answers today, and what slow or mismatched answers cost.",
            "What to say: Meet the company behind every question today. Harbor & Pine "
            "Outfitters is a fictional outdoor retailer, the course's scenario. It sells camping "
            "and hiking gear through its website and its app, and every order, customer and "
            "product sits in one warehouse. Four teams ask that warehouse questions. The team "
            "names and the way they work today are part of the scenario; the questions are drawn "
            "from the course's benchmark and demos. Finance asks for net revenue in fiscal "
            "year 2025, for the board. Operations asks every morning how many orders came in the "
            "day before. Sales asks which products sold the most units, by category. Marketing "
            "asks how many customers came back and ordered again, and then asks for an export of "
            "its California customers for a campaign. These are ordinary questions. Now the last "
            "card: how they get answered today. Each question becomes a ticket to a small data "
            "team. The ticket waits behind others. An analyst writes a query, checks it by eye, "
            "and sends a number back. If that analyst is out, the question waits for the one "
            "person who knows which tables to trust. And when finance and marketing both ask "
            "about revenue, they can get two different numbers, because each team carries its own definition. "
            "One counts cancelled orders and one leaves them out; one means the calendar year and "
            "one the fiscal year. What does that cost? Decisions wait for the queue, or they are "
            "made on numbers that do not match, and the next meeting is spent arguing about "
            "whose number is right instead of what to do. Notice what nobody here asks for: a "
            "cleverer model. They ask for answers they can trust, fast enough to use, and for "
            "personal data to be handled with care. That is the bar for everything we build "
            "today. Keep these four teams in mind: each failure on the next slide lands on one "
            "of them.",
            "The point to land: The business does not want a chatbot; it wants answers it can "
            "trust, on its own definitions, without waiting in a queue.",
            "Example: At your company: the weekly review where the finance deck and the sales "
            "dashboard show different revenue for the same week, one before refunds and one "
            "after. This example is illustrative.",
            'Ask the room: "Who has seen two teams report different revenue for the same month?" '
            "Expect: most hands; the cause is almost always a definition, not a bug.",
            "Misconceptions: That the data team is the bottleneck because it is slow. The "
            "bottleneck is that the definitions live in a few people's heads, so every answer "
            "needs one of them.",
            "Transition: The obvious fix for the queue is to let anyone ask the warehouse "
            "directly: just put a chatbot on it. Here is why that fails.",
        ],
    ),
    # 2 the ask, and why the obvious solution fails ---------------------------------------------
    dict(
        kind="problem",
        title="Just put a chatbot on the warehouse",
        minutes=3,
        says="A model with database access looks done in a demo and fails five ways in production",
        src=".dev/deck-sources.md [5] (the tutorial's own warning); docs/calibration-report.md, "
        "Traps; demo registry: The cost guard, Malicious SQL, The approval that survives a "
        "restart, Duplicate events, The kill switch in flight, The over-broad rule, blocked",
        on_slide=[
            "Lead: A tutorial-style model with database access[^5] fails in production five ways.",
            "- Wrong numbers, no error: calendar dates for a fiscal year",
            "- Unsafe or runaway queries: a join with no join condition",
            "- Personal data leaks: a customer export with every email",
            "- Breaks on events: posts twice, forgets approvals, cannot be stopped",
            "- No safe way to improve: a new rule breaks a working answer",
            "- Why it looks done: demo questions are easy, and a person is watching",
        ],
        notes=[
            "Purpose: Show why the obvious solution, a model with database access, looks finished "
            "in a demo and fails in five specific ways in production.",
            "What to say: Here is the ask every data team hears: just put a chatbot on the "
            "warehouse. The obvious build is the standard tutorial SQL agent: a model, a "
            "connection string, a tool to list tables, a tool to run a query, and a prompt that "
            "says do not write. In a demo it looks done. You ask an easy question once, it "
            "writes a clean query, and the number is right. The tutorial itself, Source 5, warns "
            "that its tools are not intended to be secure or used in production. We did not run "
            "the tutorial itself; these are the five ways a build like it fails in production. "
            "Today you see most of them live; the runaway join is an optional demo, and the rule "
            "that breaks a working answer is told at the start of Section 4. One: wrong numbers "
            "with no error. Finance asks for fiscal year 2025, the agent filters on calendar "
            "dates, and nothing says it was wrong. Two: unsafe or runaway queries. A join with "
            "no join condition multiplies the rows until the database times out, and a model "
            "that can run a statement can run a delete, whatever the prompt says. Three: leaks "
            "of personal data. Marketing asks for the California export, and the agent returns "
            "every email address, because to it a column is just a column. Four: it breaks when "
            "it runs from events. Webhooks are delivered at least once, so the same request "
            "arrives twice and the answer is posted twice; a worker restarts and a pending "
            "approval is lost; and nothing can stop a run already under way. Five: no safe way "
            "to improve it. You add a rule to fix the fiscal year, and an answer that worked "
            "last week quietly breaks. The last card is why none of this shows in the demo: a "
            "demo asks easy questions, once, with someone watching. Production asks hard "
            "questions, many times, with nobody watching. Each loop we build today closes one or "
            "more of these gaps, and the next slide turns them into requirements.",
            "The point to land: A demo proves the agent can answer; production asks whether you "
            "can trust the answer, run it unattended, and change it safely.",
            "Example: A support agent fails the same way: it answers well in a demo, then "
            "refunds one order twice when the ticket system retries its webhook. This example is "
            "illustrative.",
            'Ask the room: "Which of these five has your team already met?" Expect: wrong '
            "numbers with no error, and duplicates from retries; rarely a change measured before "
            "release.",
            "Misconceptions: That the tutorial's warning is boilerplate. It names the gap: its "
            "no-write rule is a prompt line, and its query check is another model call, Source 5.",
            "Transition: So what would good have to mean? Next, the requirements, group by group.",
        ],
    ),
    # 3 the requirements and constraints --------------------------------------------------------
    dict(
        kind="problem",
        title="What 'good' has to mean",
        minutes=3,
        says="Six groups of requirements: correctness, safety, operations, improvement, cost and "
        "latency, trust",
        src="platform/packs/datapilot_us/benchmark/business_rules.md (the definitions, the "
        "product names with injected text); pack.yaml limits, budgets and levels; demo registry "
        "(webhooks, the digest, restarts, the kill switch); .dev/deck-spec-2.md section 3, item 3",
        on_slide=[
            "Lead: Before any design, write down what the system must do. Six groups.",
            "- Correctness: business definitions the schema never states",
            "- Safety: never writes; personal data only with approval; ignores instructions "
            "hidden in data",
            "- Operations: runs from webhooks and schedules; one effect per event; survives "
            "restarts; stops mid-run",
            "- Improvement: learns new rules without breaking working answers",
            "- Cost and latency: a fixed bound on every question",
            "- Trust: every claim provable; autonomy granted only when earned",
        ],
        notes=[
            "Purpose: Turn the five failures into requirements a team can write down and test, "
            "before any design choice is made.",
            "What to say: Before we pick a single tool or framework, write down what good has to "
            "mean. Six groups. Correctness: the answer follows the business's definitions, and "
            "most of them are written nowhere in the schema. At Harbor & Pine the fiscal year "
            "starts in February, net revenue is subtotal minus discount, and cancelled orders "
            "carry a status code that no table explains: the rules from the hook. Safety: the "
            "system never writes to the warehouse, whatever the question or the prompt; personal data, such as customer "
            "emails, leaves only with a person's approval; and it resists instructions hidden in "
            "the data itself. In this warehouse, a few product names carry text that tells the "
            "agent to ignore its instructions, and a product name is just data. Operations: it "
            "runs from webhooks and schedules, not only from a chat box, such as the daily digest "
            "at 8 a.m. Eastern time; each event has exactly one effect, however many times it "
            "arrives; a pending approval survives a restart; and a person can stop it mid-run, "
            "including the run already in flight. Improvement: it learns new rules without "
            "breaking answers that already work, and you can show that it did not. Cost and "
            "latency: every question has a fixed bound on model calls, tool calls, tokens and "
            "query time, set in code, not hoped for in a prompt. A question that cannot be "
            "answered inside the bound stops and says so, instead of running up a bill. In "
            "class, DataPilot bounds model calls, tool calls, tokens and the time of each query; "
            "it has no deadline on a whole run's wall-clock time, so add one in yours. Trust: "
            "every claim it makes can be proved, with the query, the result and the run behind it, so a reviewer can check "
            "an answer without trusting the agent; and it gets autonomy, "
            "from report-only up to unattended, only when evidence has earned it. Notice that "
            "you can write a test for every group before you write a line of agent code.",
            "The point to land: Write the requirements first, in six groups, each one testable "
            "before you choose a tool or a framework.",
            "Example: A coding agent has the same six: tests that define correct, no push to the "
            "main branch, one run per pull request event, new prompts checked against old tasks, "
            "a budget per task, and a diff a person can review. This example is illustrative.",
            'Ask the room: "Which of these six did your team write down before building?" Expect: '
            "correctness, sometimes cost; operations and improvement almost never.",
            "Misconceptions: That safety is a prompt line. A prompt asks; a database role, a "
            "parser and a person's approval enforce.",
            "Transition: Requirements are not yet proof. Next: what we must prove by the end of "
            "today, and the four loops that prove it.",
        ],
    ),
    # 4 the success criteria, mapped onto the four loops ----------------------------------------
    dict(
        kind="problem",
        title="What we must prove by the end of today",
        minutes=3,
        says="Acceptance criteria, one group per loop; the fiscal year 2025 revenue question "
        "tests correctness across all four",
        src=".dev/deck-spec-2.md section 3, item 4, and section 4, item 8 (the scoreboard); "
        "docs/architecture.md (the four loops); pack.yaml (levels, the promotion gate); "
        "benchmark/dev.yaml (the fiscal year 2025 revenue question and its gold answer)",
        on_slide=[
            "Lead: Each requirement becomes a test; ours is fiscal year 2025 net revenue.",
            "- Grounded answers, bounded cost: each shows its query and assumptions, on a fixed "
            "budget | Agent loop",
            "- Safety: no write runs; personal data waits for a person; doubtful answers are "
            "held | Verification loop",
            "- Operations: one effect per event; approvals survive a restart; a stop reaches "
            "each job | Event loop",
            "- Improvement and trust: new rules break no working answer; autonomy is earned | "
            "Hill-climbing loop",
        ],
        notes=[
            "Purpose: Turn the requirements into acceptance criteria, reveal the four loops as "
            "their owners, and set the fiscal year 2025 revenue question as the class's test.",
            "What to say: Requirements become tests, and each group of tests belongs to one "
            "loop. A test is a condition you can check with a run, and pass or fail without "
            "debate. This is the first time you see the loops by name. The agent loop: the "
            "model, its tools and its stops. It passes when every answer is grounded, carrying "
            "its query and the assumptions it made, inside a bounded cost and latency per "
            "question: grounded answers, bounded cost. The verification loop: checks around the "
            "agent. It passes when no write ever runs, personal data waits for a person, and a doubtful answer is held instead "
            "of posted. That is safety. The event loop: the agent run from webhooks and "
            "schedules. It passes when one event has one effect however often it arrives, an "
            "approval survives a restart, and a stop reaches a run already in flight. That is "
            "operations. The hill-climbing loop: improvement with evidence. It passes when a "
            "new rule helps questions it never saw and breaks no answer that worked; breaking a "
            "working answer is called a regression. In class I click Approve at the promotion "
            "gate, the check that decides whether a new version of the rules goes live. The "
            "console records the approver as console, a known gap you meet in Section 4; in "
            "your system, record a signed-in person. A family of questions, the questions about "
            "one measure such as revenue, earns more autonomy only on that evidence. That "
            "is improvement and trust. Now the lead line: the test that runs through the class, "
            "what was our net revenue in fiscal year 2025? That is correctness, and no single "
            "loop owns it: it needs all four, and it is met only after Section 4. At the end of "
            "each section a scoreboard shows where this question stands. It passes only when it "
            "matches the gold answer, a hand-checked result, and posts at a level its family has "
            "earned. Each criterion is checked live today. If one fails live, you will see that "
            "too, and I will say what it means.",
            "The point to land: Four loops, each owning a group of acceptance criteria; one "
            "question, fiscal year 2025 revenue, tests correctness across all four.",
            "Example: In your own system: pick one question your executives actually ask, write "
            "its correct answer by hand, and make it the test every change must pass. This "
            "example is illustrative.",
            'Ask the room: "Which of these four could your agent pass today?" Expect: the agent '
            "loop's, sometimes the verification loop's; rarely the event or hill-climbing "
            "loop's.",
            "Misconceptions: That a better score on one run proves a criterion. Each criterion "
            "is checked by a run you can repeat, on questions the system never learned from.",
            "Transition: First, why was that number wrong? Next, the five traps hidden in that "
            "one question.",
        ],
    ),
]
