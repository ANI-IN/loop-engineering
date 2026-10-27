"""Closing block, 3:38-4:00, 22 minutes, 12 slides, modelled on the reference deck's slides 65 to
75 (the owner's specification of 27 October 2026, section 5; the lead's brief, .dev/review/
deck3-brief.md, "Closing"): the question answered (the payoff, kept from the second deck and read
live), all results in one table, which loop when, build or buy, using the loops in your own
repository, the final project, the assignments and the Thursday review, the loops in one picture,
the key takeaways (the design checklist in their notes), the two references tables, and Ask about
anything.

Every number comes from .dev/deck3-evidence.md (parts 2 and 3), .dev/deck2-reconcile.md ("The
hook", "The payoff", items 4 and 5), docs/costs.md and the assignments' pages; run ids, dates and
sample sizes sit in the notes. The owner's decisions of 27 October 2026 are true of the code: a
reviewer that gives no verdict holds the answer (fail closed), and the gate's approval needs a typed
person's name and refuses an empty name or "console". The closing cites sources 30, 36 and 42 (build
or buy) and reuses source 12 from the shortlist; the references tables list every source the deck
cites, numbered in order of first citation, generated from the citations.
"""

RULES = "design system 3"


def short(purpose: str, say: str, transition: str, *do: str) -> list[str]:
    """The short notes form: Purpose, What to say, any Do lines, Transition."""
    return [
        f"Purpose: {purpose}",
        f"What to say: {say}",
        *(f"Do: {x}" for x in do),
        f"Transition: {transition}",
    ]


SLIDES = [
    # 78 payoff: the question, answered, read live ---------------------------------------------------
    dict(
        kind="payoff",
        title="Final: The question, answered",
        minutes=3,
        says="The fiscal year 2025 revenue question, wrong at the start and right at the end, read "
        "live, with the level it posted at and what each loop contributed",
        src=".dev/deck2-reconcile.md, The hook and The payoff (runs 9182df01 and 59174f10); "
        ".dev/deck3-evidence.md part 3, Section 4; the closing of the second deck, kept",
        on_slide=[
            "Lead: Fiscal year 2025 net revenue: the first answer, the last one, and what each "
            "loop added.",
            "Before: first answer | $72,394,572.08",
            "After: matches gold | $64,015,091.21",
            "Level: unattended, cleared",
            "Loop: Section 1 | One query, bounded cost",
            "Loop: Section 2 | Every check passed; nothing flagged",
            "Loop: Section 3 | Waited for clearance, posted once",
            "Loop: Section 4 | Learned rules, approved at the gate",
            "- Correctness: right on two databases",
            "- Safety: read-only; no personal data out",
            "- Operations: one event, one post",
            "- Improvement: zero regressions",
            "- Cost: under a tenth of a cent",
            "- Trust: run record and gold check on record",
            "Sample: one run of version 13 (14 of 15 holdout), promoted after the chart's version "
            "11; only the knowledge changed",
        ],
        notes=[
            "Purpose: Read today's last run live, then close the story: the question that was "
            "wrong at the start is right, posted at the level the gate cleared, with each loop's "
            "part.",
            "Do: Share the Events page; read the last run's strip: the value, the level, the gold "
            "check and its live stamp; then share the slides.",
            "What to say: That was today's run. If it "
            "posted at the assisted level, the gate held back autonomy the evidence had not "
            "earned; if the gate blocked it, that verdict is the loop working. Now the cards, "
            "which show the published run. At the start of class this question came back as "
            "72,394,572.08 dollars: no error, a clean sentence, wrong by about 8.4 million "
            "dollars. In the middle, the same question answered 64,015,091.21 dollars, which "
            "matches the gold answer on both databases. On the right, the level: it posted "
            "unattended because revenue, a metric family, cleared on its holdout questions, each "
            "passing 2 of 3 runs. That is a small sample, so the level is a decision with a "
            "review date, not a proof. Now the scoreboard, complete. The agent loop ran one "
            "query inside its budget. The verification loop passed every check, and the reviewer "
            "approved; an approval is a second opinion, not proof, and a reviewer that gives no "
            "verdict now holds the answer. The event loop took one webhook event, made it wait "
            "while the clearance re-runs finished, and posted it once. The hill-climbing loop supplied "
            "the learned rules, measured on questions the analyzer team never saw and approved "
            "at the gate's approval step, recorded then as console; today the gate needs a typed "
            "person's name. The model never changed; only the knowledge did.",
            "The point to land: No single loop fixed the answer: the four together made a "
            "correct answer that could post with nobody watching.",
            "Example: The after card is run 59174f10 of 24 October 2026: a webhook event with no "
            "duplicate; one query carrying all five rules, 12,667 tokens and 0.00055 dollars; "
            "every grader passed and the reviewer raised no concern; it waited 5 times for the "
            "clearance re-runs and posted 74 seconds after the first send. It has no trace: "
            "LangSmith refused traces from 23 October at its monthly limit, so the run is proven "
            "by its run id, its operations record and the spend ledger; today's live run carries "
            "its trace link. Its query reads email "
            "only in a filter, to drop internal accounts, and returns no personal data, so "
            "nothing waited for approval. Version 13 came from the analyzer team's candidate A of "
            "two; its experiment passed 14 of 15 holdout questions against 2 for version 1, with "
            "0 regressions, a later promotion than the version 11 of the Section 4 chart. Revenue "
            "cleared on its 4 holdout questions; Assignment 4 makes at least 3 the rule. The same "
            "rule cleared revenue in 7 of 8 promotions, so the clearance itself varies. The "
            "before card is run 9182df01 of 25 October 2026, version 1, held by the reviewer's "
            "two concerns and never posted. Compare them by knowledge version, not by date: the "
            "after run is a day older. Eight runs in all posted 64,015,091.21 dollars at the "
            "unattended level.",
            'Ask the room: "Which requirement group would your agent fail first?" Expect: '
            "correctness on business rules, or operations when a webhook is retried.",
            "Misconceptions: That an approval proves a person read the change. Version 13's "
            "approval was recorded as console, before the name rule; the gate now needs a typed "
            "person's name and refuses an empty name or console. Production systems use a "
            "signed-in identity and record what the person read.",
            "Transition: That was one question. Here is every loop's measurement, side by side.",
        ],
    ),
    # 79 table: all results ------------------------------------------------------------------------
    dict(
        kind="table",
        title="All results: Four loops, one picture",
        minutes=2.5,
        says="One row per loop: its measure without and with the loop, and its sample",
        src=".dev/deck3-evidence.md part 3 (docs/benefits.md, Sections 1 to 4; the evidence "
        "pages); .dev/deck2-reconcile.md items 1 to 3",
        on_slide=[
            "Lead: One row per loop: the same measure without the loop and with it, and its "
            "sample.",
            "| Loop and sample | Without the loop | With the loop |",
            "|---|---|---|",
            "| Agent loop: 7 questions, 21\u00a0runs\u00a0a\u00a0side | 12 of 21 runs correct | 17 of 21 "
            "runs correct |",
            "| Verification loop: 20 trap questions, 40\u00a0runs\u00a0a\u00a0side | 39 of 40 wrong answers went "
            "out | 20 of 40 went out; 20 held or escalated |",
            "| Event loop: 3 demos, 4 planted bugs | The bugs failed 17 of 17 runs | The fixes held 23 of 23 |",
            "| Hill-climbing loop: 15 holdout questions, 3 runs each | Starting rules: 2 of 15 "
            "| 13 of 15, no regression |",
            "Key idea: Each loop moved the failure it was built for, measured the same way "
            "before and after.",
        ],
        notes=[
            "Purpose: Put the four measurements side by side, each with its sample, so learners "
            "see what each loop changed and what it did not.",
            "What to say: One row per loop, read left to right: the sample, the measure without "
            "the loop, and with it. The agent loop: seven easy questions, three runs each, so 21 "
            "runs a side; 12 correct without the tools, 17 with them. The verification loop: "
            "twenty trap questions, two rounds, 40 runs a side, every answer wrong on both sides; "
            "without a reviewer 39 of the 40 wrong answers went out, with the full layer 20 went "
            "out and 20 were held or escalated. The event loop: three demos and four planted bugs, "
            "since the duplicates demo plants two, forced on purpose; they failed in all 17 of "
            "their planted runs, every recorded run, and the fixes held in 23 of 23. The hill-climbing loop: the 15 "
            "holdout questions the analyzer team never saw, three runs each, a question passing on two "
            "of three; the starting rules, version 1, passed 2, the learned rules of version 11 "
            "passed 13, with no regression. Notice two things. Each loop moved its own measure "
            "and none of the others: the verification loop made no answer right, it only stopped "
            "wrong ones going out. And no row turns the whole stack on and off: each loop was "
            "measured against its own without.",
            "The point to land: Each loop fixes one failure and needs its own measurement; no "
            "single number describes the whole system.",
            "Example: The rows come from the rehearsal session of 24 October 2026, 56894641, for "
            "the first two; the event loop's runs are 5, 6 and 6 planted, then 7, 7 and 9 fixed, "
            "over 23 to 25 October; the hill-climbing row is experiments 74ff242b and b50131b4. "
            "One verification run went out with no verdict, b95481b8, before the fail-closed "
            "change; the runs were not repeated, so the count stays 20 of 40.",
            'Ask the room: "Which row would you want to measure first on your own agent?" '
            "Expect: the verification row, then the hill-climbing row.",
            "Misconceptions: That these are rates. Each is a count from one model and one "
            "warehouse, in one session; the method transfers, the numbers do not.",
            "Transition: So which loop should you add first? Start from the failure.",
        ],
    ),
    # 80 table: which loop when --------------------------------------------------------------------
    dict(
        kind="table",
        title="Which loop when: Match the loop to the failure",
        minutes=2,
        says="Each failure you have seen points to one loop, and to what to measure",
        src="the owner's specification of 27 October 2026, section 5, item 3; the four critical "
        "gaps (problem segment); the poll (breaks.py)",
        on_slide=[
            "Lead: Each loop is a bet on one thing the model cannot do on its own.",
            "| Failure you have seen | Loop to add | What to measure |",
            "|---|---|---|",
            "| Fluent answers that miss what the tools never showed | Agent loop: tools, caps, "
            "stops | Correct runs, tokens a run |",
            "| Wrong or unsafe answers that nobody checked | Verification loop: parser, grants, "
            "judge | Wrong answers that go out |",
            "| Repeated effects, lost approvals, stops ignored | Event loop: keys, leases, "
            "checkpoints, kill switch | Each failure, forced on purpose |",
            "| A fix that quietly breaks other answers | Hill-climbing loop: gold questions, "
            "holdout, gate | Holdout passes, regressions |",
            "Key idea: Add the loop that matches a failure you have seen, then measure it.",
        ],
        notes=[
            "Purpose: Turn the day into a decision rule: add the loop whose failure you have "
            "seen, and know what to measure; read the poll's two counts back.",
            "What to say: Read the table from the left. Start from a failure you have already "
            "seen, not from the loop you find most interesting. If your agent gives fluent "
            "answers that miss what its tools never showed it, add the agent loop: tools that "
            "show the right view, capped, with stops in code, and measure correct runs and tokens "
            "a run. If wrong or unsafe answers go out because nothing checked them, add the "
            "verification loop: a parser, the database's grants, and a judge for doubtful "
            "answers, and count the wrong answers that still go out. If events repeat, approvals "
            "vanish in a restart, or a stop is ignored, add the event loop, and force each "
            "failure on purpose to prove its fix. If a fix keeps breaking other answers, add the "
            "hill-climbing loop: gold questions, a holdout the rule writers never see, and a gate, "
            "and measure holdout passes and regressions. Now the poll from before the break: "
            "[number] of you have a hill-climbing loop in production, and [number] have none of "
            "the four. If you have none, the agent loop and a handful of checked gold questions "
            "come first; the hill-climbing loop needs something to measure against.",
            "The point to land: Match the loop to a failure you have seen, then measure it; a "
            "loop added on faith is a cost, not a safeguard.",
            "Example: A support agent that drafts refund replies, as an illustration: it quotes "
            "the wrong policy because its search tool returned stale pages, an agent loop "
            "failure; it refunds twice when the ticket system retries, an event loop failure.",
            'Ask the room: "Which row describes your last incident?" Expect: the first or the '
            "second row; the third for teams that run agents on a schedule.",
            "Misconceptions: That the hill-climbing loop comes first because it improves "
            "everything. It needs gold questions and checks to decide on, so it comes last.",
            "Transition: Some of these pieces you can buy. When to buy them, and when to build: "
            "next.",
        ],
    ),
    # 81 design callout: build or buy --------------------------------------------------------------
    dict(
        kind="design_callout",
        title="Text-to-SQL design: Build or buy layers and assistants",
        minutes=2,
        says="When to buy a semantic layer or a warehouse assistant, when to build, and why the "
        "loops are built either way",
        src="the closing of the second deck (Build or buy), moved here; .dev/deck-sources.md "
        "[30], [36], [42] and its build-or-buy part; docs/text-to-sql-design.md, Build or buy",
        on_slide=[
            "Lead: Buy where the rules are already defined; build the loops that prove them.",
            "Decision: buy or build",
            "| Your situation | Lean toward | Why |",
            "|---|---|---|",
            "| Metrics defined in one platform | Buy its layer | One "
            "definition for every tool[^30] |",
            "| You must choose and pin the model | Own the model call | Cortex Analyst "
            "picks the model[^36] |",
            "| Rules unwritten, or learned | Build the loops | Teams still write them[^42] |",
            "DataPilot: Built, so learned rules are gated and can roll back.",
        ],
        notes=[
            "Purpose: Give learners a decision framework for buying a semantic layer or a "
            "warehouse assistant against building, and show why the loops are built either way.",
            "What to say: Treat this as a decision, not a product comparison: three situations, "
            "three answers. First, your metrics are already defined in one platform. Then buy "
            "its layer or its assistant. The dbt Semantic Layer's point is that a metric is "
            "defined once and every downstream tool, assistants included, uses the same "
            "definition, Source [^30]. Second, you must choose and pin the model. Then build, or "
            "at least own the model call: Snowflake's Cortex Analyst says you cannot choose a "
            "model directly, Source [^36]. Third, the case every team meets: rules nobody has "
            "written down, or rules you want learned from failures. Databricks describes its "
            "Genie Agents as environments where data teams configure trusted data, metrics and "
            "business rules, Source [^42]: the product holds the rules, and someone still writes "
            "them. Snowflake says the same from the other side: a schema lacks business process "
            "definitions and metrics, Source [^36]. So whichever you choose, you still build the "
            "loops around it: gold questions, a holdout the rule writers never see, a gate that "
            "blocks on a confirmed regression, and checks on executed results. We measured "
            "DataPilot; we did not compare it with any product.",
            "The point to land: A product is a place to put your rules, not their source; the "
            "loops decide whether a rule is right.",
            "Example: DataPilot built because its rules are learned: the hill-climbing loop "
            "proposes, tests and rolls back rules in a versioned knowledge file. As an "
            "illustration, a team already on Databricks could keep its metrics in a Genie Agent "
            "and still run its own gold questions and holdout against its answers.",
            'Ask the room: "Which platform holds your metrics today?" Expect: dbt, Snowflake, '
            "Databricks, or a spreadsheet; the spreadsheet means the rules are not written yet.",
            "Misconceptions: That buying removes the business rules. Every one of these products "
            "asks your team to write the definitions; the five traps would still be yours.",
            "Transition: Whether you buy or build, here is how to take the loops to your own "
            "repository.",
        ],
    ),
    # 82 problem rows: use it in your repository ----------------------------------------------------
    dict(
        kind="problem",
        title="Use it in your repository: The kit and the pack setting",
        minutes=2,
        says="The domain pack, the one setting that selects it, the template, the pack check, and "
        "a read-only role on your own Postgres",
        src="use-in-your-repo/README.md; use-in-your-repo/apply-to-your-repo.md, parts 1 to 3; "
        "platform/packs/_template/",
        on_slide=[
            "Lead: Everything specific to one warehouse lives in a domain pack; one setting "
            "picks the pack.",
            "- **Domain pack:** one folder: settings, rules, benchmark, knowledge, drift questions "
            "| branch",
            "- **Pack setting:** one line picks the pack every process reads | swap",
            "- **Template:** a complete small pack, Lantern Coffee Club, with four rules and "
            "three traps | copy",
            "- **Pack check:** runs every gold query on both databases and proves each naive "
            "query differs | check",
            "- **Your own Postgres:** point the platform at it through a read-only role | lock",
        ],
        notes=[
            "Purpose: Show how to take the four loops off the course's warehouse and onto the "
            "learner's own data, with the kit the repository ships.",
            "What to say: Everything you saw today ran on Harbor & Pine, but nothing in the "
            "platform depends on it. Everything specific to one warehouse lives in a domain pack: "
            "its settings, business rules, benchmark with both splits, knowledge versions, and "
            "the drift canary, the questions re-run on a schedule to catch drift. One line in the settings file, the pack setting, selects the pack "
            "every process reads, and each pack keeps its own knowledge versions, so switching "
            "never mixes rules. Start by copying the template, Lantern Coffee Club, a made-up "
            "coffee subscription business with four rules, three traps, a benchmark and a "
            "canary. Then run the pack check: it runs every gold query on both databases and "
            "proves that each trap's naive query gives a different answer, before any model "
            "call. Last, point the platform at your own Postgres through a role that can only "
            "read. If your warehouse is not Postgres, load a sample of it into Postgres for the "
            "pack and the benchmark, and carry the patterns, not the code, to the warehouse "
            "itself: the read-only role, the parser, the keys and the gate.",
            "The point to land: The loops are the platform; the warehouse is a pack you write: "
            "rules, traps, benchmark and knowledge.",
            "Example: Not to read aloud. The hard part of a new pack is not code: it is writing "
            "down the rules, the gold query for each question, and the traps, the knowledge a "
            "model cannot read from the schema. A trap whose naive query returns the gold result "
            "teaches the loops nothing, and the pack check fails it. The kit's guide has three "
            "parts: the template end to end, your own pack, and your own database.",
            'Ask the room: "Which three traps would you write for your warehouse?" Expect: the '
            "fiscal calendar, test accounts, and a status code nobody documented.",
            "Misconceptions: That the pack check proves the agent works. It proves the benchmark "
            "is sound before any model call; the experiments measure the agent.",
            "Transition: The final project is that path, end to end, with a report.",
        ],
    ),
    # 83 problem rows: the final project -------------------------------------------------------------
    dict(
        kind="problem",
        title="Final project: The four loops on your own data",
        minutes=1.5,
        says="Five things to build on a domain no section used, and a before-and-after report",
        src="final-project/README.md, What you'll see and What the result means; "
        "final-project/CHECKLIST.md",
        on_slide=[
            "Lead: A capstone: a domain no section used, a benchmark you write, a report of what "
            "changed.",
            "- **Your dataset:** a Postgres schema you can share, loaded into two differently "
            "seeded databases | chart",
            "- **Three original traps:** business rules your schema does not reveal, none "
            "copied from the course | warning",
            "- **Your benchmark:** development and holdout questions, gold SQL, a naive query per "
            "trap | search",
            "- **One extension:** one capability the class code lacks, in any of the four "
            "loops | branch",
            "- **A before-and-after report:** baseline, gated candidate, what your extension "
            "changed | check",
            "Key idea: Report counts from your own runs, never a percentage: one run is one run.",
        ],
        notes=[
            "Purpose: Set up the final project: the four loops on a domain no section used, with "
            "a benchmark the learner writes and a report of what changed.",
            "What to say: The final project is the day, repeated on your own data. Five things. "
            "Your own dataset, loaded into two differently seeded databases, because the gold "
            "check runs on both. At least three original traps: rules your schema does not "
            "reveal, none copied from Harbor & Pine or the template. Your own benchmark: "
            "development questions for the analyzer team, holdout questions for the gate, each "
            "with a gold query, and for each trap a naive query that gives a different answer. "
            "One extension the class code lacks, in any loop. And a before-and-after report: the "
            "baseline, the candidate after the gate, and what your extension changed. There is "
            "no grader; a checklist lists what to show. Report counts, such as 3 of 4 holdout "
            "items, never a percentage, and a blocked candidate is a result too.",
            "The point to land: The final project proves you can write the knowledge and the "
            "measurement for a warehouse nobody prepared for you.",
            "Example: Not to read aloud. The course's own over-broad rule is the model of a "
            "blocked result: the gate refused it with 9 confirmed regressions, and that refusal "
            "was the finding. The data can be real or generated, as long as you can share it; a "
            "small holdout is weak evidence, so say how many questions it holds.",
            'Ask the room: "Which domain would you choose?" Expect: their own company\'s '
            "warehouse, or a public dataset with a fiscal calendar.",
            "Misconceptions: That a trap the model solves unaided is a success. It means the "
            "schema reveals the rule; strengthen the trap, or the loops have nothing to learn.",
            "Transition: Before the project, the four assignments, one per loop.",
        ],
    ),
    # 84 problem rows: the assignments and the Thursday review ----------------------------------------
    dict(
        kind="problem",
        title="Assignments: One loop each, reviewed on Thursday",
        minutes=2,
        says="Four assignments with live checks, one per loop; the deadline and the solutions at "
        "the Thursday review",
        src="section-1-agent-loop/assignment/README.md to section-4-hill-climbing-loop/"
        "assignment/README.md; docs/costs.md, Each check has its own spend cap and The learner "
        "key limit; docs/review-session.md",
        on_slide=[
            "Lead: Each assignment adds one capability the class code lacks, checked live on "
            "your own key.",
            "- **Assignment 1: Agent loop:** a value lookup for informal names; a tie becomes a "
            "question | search",
            "- **Assignment 2: Verification loop:** ask about undefined terms; block unapproved "
            "personal data | lock",
            "- **Assignment 3: Event loop:** a nightly revenue alert, one a day, that obeys the "
            "kill switch | clock",
            "- **Assignment 4: Hill-climbing loop:** a new metric family that needs three holdout "
            "questions | chart",
            "- **Thursday review:** the deadline is in the class chat; the solutions appear when "
            "the review starts | check",
        ],
        notes=[
            "Purpose: Set up the practice: four assignments with live checks, one per loop, the "
            "deadline, and when the solutions appear.",
            "What to say: Four assignments, one per loop, each adding a capability the class "
            "code lacks. Assignment 1: Agent loop: a value lookup, so informal or misspelled "
            "product names resolve to stored values, and a tie becomes a question back. "
            "Assignment 2: Verification loop: one grader that asks when a business term has no "
            "definition, and one that blocks an email address or phone number in an answer "
            "unless a person approved it. Assignment 3: Event loop: a nightly revenue anomaly "
            "alert, one per day by its key, that checks the kill switch before it posts. "
            "Assignment 4: Hill-climbing loop: a new metric family, the repeat-customer rate, "
            "that needs three holdout questions before the unattended level. Each has a live "
            "check on the real model with your own key; it prints its estimate before it "
            "starts, then PASS or FAIL per requirement. The deadline is in the class chat; the "
            "solutions are published when the Thursday review starts.",
            "The point to land: Each assignment builds one loop's missing capability yourself, "
            "checked live on the real model, at a cost you can see before it starts.",
            "Example: Not to read aloud. A full check of a working solution typically cost about "
            "0.4 cents for Assignment 1, about 2 cents for Assignment 2, an estimated 0.5 cents "
            "for Assignment 3, and 12.62 to 19.22 cents for the five audited checks of Assignment "
            "4. Each check stops at its own 1-dollar cap, and your key has a 3-dollar limit. The "
            "details the slide leaves out: the value lookup's match goes into the answer's "
            "assumptions; the alert is updated, not repeated, after late orders; and Assignment "
            "4's critic drops a planted over-broad rule.",
            'Ask the room: "Which assignment matches a problem you have at work?" Expect: '
            "Assignment 1 for users' wording, or Assignment 2 for personal data.",
            "Misconceptions: That the check grades you. Nobody grades the assignments: the "
            "rubric is for assessing your own work, and the check says which requirements pass "
            "live.",
            "Transition: One picture of everything you will build.",
        ],
    ),
    # 85 concept: the loops in one picture ---------------------------------------------------------
    dict(
        kind="concept",
        title="The loops in one picture",
        minutes=1.5,
        says="Four loops around one model: it answers, is checked, runs on events, and improves "
        "with evidence",
        src="platform/tools/diagrams/definitions.py four_loops_concept (four-loops-generic on the "
        "concept canvas); docs/diagrams/README.md, alt text; the closing of the second deck",
        figure={
            "diagram": "four-loops-concept",
            "alt": "The four loops nested, each part named by its job: in the agent loop, a model "
            "answers with tools, code stops it, and it reads the promoted rules; in the "
            "verification loop, layered checks, then a person decides a doubtful answer; in the "
            "event loop, events arrive, each is keyed once and queued with leases, a kill switch "
            "read before every step points at the model, and each answer posts or is held for a "
            "person, then waits for human approval; beside them the hill-climbing loop, where "
            "failures on a benchmark lead agents to propose rules, the rules are judged on unseen"
            " questions, and a person promotes them into the promoted rules the model reads",
        },
        on_slide=[
            "Lead: Four loops around one model: it answers, is checked, runs on events, improves "
            "with evidence.",
            "Key idea: Each loop catches what the others cannot; together they let an answer post "
            "unwatched.",
        ],
        notes=[
            "Purpose: Show the four loops as one system, what each covers that the others cannot, "
            "as a picture learners can redraw for their own agent.",
            "What to say: Here is the whole system, as a pattern you can carry to any agent. In "
            "the middle, the agent loop: a model answers with tools, and stops in code end the "
            "run. Around it, the verification loop: layered checks first, and a person decides a "
            "doubtful answer; a check that gives no verdict counts as doubtful. Around both, the "
            "event loop: events arrive, each is keyed once by its meaning and queued with leases, "
            "a kill switch stops every run, and an answer posts or waits for human approval. "
            "Beside them, the hill-climbing loop: failures on a benchmark lead agents to propose "
            "rules, the rules are judged on unseen questions, and a person promotes them, today "
            "by name. The arrow at the bottom carries promoted rules into the model: that is how "
            "the fiscal year rule reached the last run.",
            "The point to land: Each loop fixes a failure the others cannot; an answer may post "
            "with nobody watching only when all four are in place.",
            "Example: Not to read aloud. A support agent that drafts refund replies, as an "
            "illustration: the agent loop drafts from the order history; the verification loop "
            "checks the amount against the order; the event loop runs once per new ticket, with "
            "a stop; the hill-climbing loop learns policy rules from rejected drafts, measured on "
            "held-back tickets. Version 13's promotion was recorded as console, before the gate "
            "asked for a typed name.",
            'Ask the room: "Which box would you build next, and what must exist beneath it '
            'first?" Expect: a gold check before any rule writers; a key and a stop before running '
            "from events.",
            "Misconceptions: That the loops are built once. The gold set grows with every "
            "failure, the grants follow the schema, and the holdout wears out with use.",
            "Transition: Ten lessons from today, written so they hold beyond this warehouse.",
        ],
    ),
    # 86 closing: key takeaways, the design checklist in the notes --------------------------------
    dict(
        kind="closing",
        title="Summary: Key takeaways",
        minutes=2,
        says="Ten portable lessons, each tagged with the section that taught it; the design "
        "checklist for text-to-SQL in the notes",
        src=".dev/deck3-evidence.md parts 2 and 3; .dev/deck2-reconcile.md items 1 to 5; "
        "docs/text-to-sql-design.md, The checklist; round 1 ruling 22",
        on_slide=[
            "Lead: Ten lessons that carry to any agent, and the rule that joins them.",
            "1. The agent knows only what its tools return | Section 1",
            "2. Caps and stops belong in code, not prompts | Section 1",
            "3. Parse queries; let the grants be the wall | Section 2",
            "4. Retry with feedback, a bounded number of times | Section 2",
            "5. A same-knowledge judge shares its blind spots | Section 2",
            "6. Key each event by meaning | Section 3",
            "7. Prove each safeguard by forcing its failure | Section 3",
            "8. Decide on questions the rule writers never saw | Section 4",
            "9. Promote through a gate; earn autonomy per family | Section 4",
            "10. Measure before you keep it | All sections",
        ],
        notes=[
            "Purpose: Leave learners with ten portable lessons, each tied to the section that "
            "taught it, and the design checklist for their own warehouse.",
            "What to say: At the start I said you would be able to do four things; here are the "
            "ten lessons behind them. The agent knows only what its tools return, so design that "
            "view, and put caps and stops in code, where the model cannot talk past them. Parse "
            "every query and let the database's grants be the wall. Retry with feedback, a "
            "bounded number of times. A judge that knows what the writer knows shares its blind "
            "spots, and its silence must hold the answer. Key every event by what it means, and "
            "prove each safeguard by forcing its failure on purpose. Decide on questions the "
            "rule writers never saw, promote only through a gate that can block, and let each family "
            "earn its autonomy. And the rule that joins them: measure a loop before you keep it.",
            "The point to land: Every lesson is a pattern you can apply to your own agent next "
            "week; DataPilot was only the worked example.",
            "Do: Do not read the Example aloud; point learners to the checklist on the course page "
            "Designing text-to-SQL for your own warehouse.",
            "Example: The evidence, one line each. 1: 12 of "
            "21 runs correct with column names only, 17 of 21 with described tools. 2: an "
            "uncapped query of 10,000 rows reached 182,654 to 187,030 tokens against a "
            "60,000-token run budget. 3: a first-word guard passed a hidden DELETE; the read-only "
            "transaction and the grants refused every write, and no row changed. 4: the retry cap "
            "ended a looping run at 3 attempts and 10,573 tokens; without it, runs went to 9 to 13 "
            "attempts and the 60,000-token run budget, and one model stopped itself at 19,960. 5: the reviewer "
            "approved 19 of 40 wrong answers. 6: one event sent three times posted three answers "
            "without a key, one with it. 7: the planted bugs failed 17 of 17 runs and the fixes "
            "held 23 of 23. 8: version 11 passed 13 of 15 holdout questions against 2. 9: revenue "
            "cleared the unattended level in 7 of 11 promotions, 0 of 3 under the old clearance "
            "rule, then 7 of 8. 10: the schema helper cost 2,449 more tokens a question on 4 "
            "questions, with identical results; it stays on until the holdout measurement that "
            "rehearsal owes. The design checklist, in the order a team takes it: 1, inventory the "
            "business rules, each with an owner; 2, build gold questions, split into development "
            "and holdout, before the agent; 3, choose where each rule lives; 4, run every query "
            "read-only, and where askers have different rights, as the asker: a role per asker or "
            "row-level security, never one role for all; 5, describe the tables and cap rows and "
            "values; 6, add value lookup; 7, validate every query before it runs; 8, state "
            "assumptions, and ask when a term has no rule; 9, match executed results on two "
            "databases, Source [^12], and run the benchmark again on every change; 10, start "
            "every metric family at the report-only level and let it earn autonomy.",
            'Ask the room: "Which lesson would change your design next week?" Expect: the '
            "grants, the gold questions, or keys by meaning.",
            "Misconceptions: That the lessons are DataPilot's. Each is a pattern; DataPilot was the "
            "worked example, and its counts do not transfer.",
            "Transition: The references follow, then your questions.",
        ],
    ),
    # 87 references, part 1 ------------------------------------------------------------------------
    dict(
        kind="references",
        part=1,
        title="References (1 of 2): Sources in the order cited",
        minutes=0,
        says="Every source cited today, numbered in order of first use, with its link",
        src="slides/source/sources.py; the deck's citations, in order of first use",
        on_slide=["Lead: Every source cited today, numbered in order of first use, with its link."],
        notes=short(
            "List the first twelve sources the deck cites, in the order first cited.",
            "No time of its own: page past; it stays in the deck for anyone copying a link. These "
            "two tables list every source cited today, numbered in the order we first used each "
            "one, with its link.",
            "The second table, then questions.",
        ),
    ),
    # 88 references, part 2 ------------------------------------------------------------------------
    dict(
        kind="references",
        part=2,
        title="References (2 of 2): The remaining sources",
        minutes=0,
        says="The remaining sources, in order of first use, with their links",
        src="slides/source/sources.py; the deck's citations, in order of first use",
        on_slide=["Lead: The remaining sources, continuing the numbering of the first table."],
        notes=short(
            "List the remaining sources the deck cites, in the order first cited.",
            "No time of its own: page past; it stays in the deck for anyone copying a link. The "
            "rest of the sources, continuing the numbering; the course's sources page holds every "
            "entry, with the claims each one supports.",
            "Now, your questions.",
        ),
    ),
    # 89 Ask about anything (copied) ---------------------------------------------------------------
    dict(
        kind="qa",
        title="Ask about anything",
        minutes=3.5,
        says="Questions about anything from today, until 4:00",
        src="the reference deck, slide 74",
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
            "Take the last questions of the class, then close at 4:00.",
            "Take questions from the chat first; the teaching assistants pick the top ones. "
            "Likely: which loop to build first? The one whose failure you have seen. Does a "
            "stronger model remove the loops? No: the rules are not in the schema. Anything left "
            "at 4:00 goes to the Thursday review. Thank you.",
            "That is the end of the class.",
            "Mark the questions you could not answer for the Thursday review.",
        ),
    ),
]
