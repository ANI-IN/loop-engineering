"""Closing block, 3:45-4:00, 15 minutes: the payoff (the fiscal year 2025 revenue question,
answered), the four loops together, build or buy, ten insights as transferable lessons, the design
checklist for text-to-SQL, Monday's checklist, the assignments and the final project; then the
sources slides at 0 minutes (the owner's specification of 27 October 2026, section 4, item 9).

The payoff's numbers follow .dev/deck2-reconcile.md ("The hook" and "The payoff"): before, run
9182df01 (version 1, held, never posted); after, run 59174f10 (version 13, posted at the unattended
level). The insights follow .dev/review/deck-round-3/lead-rulings.md, rulings 2, 3 and 7, and the
reconciliation's item 3; every number sits in the notes, none on the slide. Course numbers come
from .dev/deck-evidence.md (entry ids in each slide's src); external claims name their source by
the number sources.py holds ([1] to [54] from .dev/deck-sources.md, [55] to [118] from
.dev/deck2-sources.md).
"""

from sources import ENTRIES, SLIDE_WHO, entry_line

RULES = "design system 2"

# The sources slides are a bibliography: the owner's specification gives them zero minutes.
SOURCES_MINUTES = 0

SOURCES_SRC = ".dev/deck-sources.md; .dev/deck2-sources.md; slides/source/sources.py"

# The sources slides list exactly the 83 sources the deck cites, on seven slides, each one panel
# across the slide so that every entry keeps to one line where its address allows. Every entry
# shows its authors or organisation; to save a line, these show no year on the slide. The full
# entry, with its year, is in sources.py and on the course's sources page (docs/sources.md).
NO_YEAR = {4, 12, 29, 39, 56, 67, 68, 69, 71, 77, 79, 83, 106, 113, 118}


def slide_entry(n: int) -> str:
    """One entry as its sources slide shows it: '[n] Short title, authors, year, address', with
    no year for the numbers above."""
    _n, _topic, _title, short, who, _year, url = ENTRIES[n - 1]
    if n in NO_YEAR:
        return f"[{n}] {short}, {SLIDE_WHO.get(n, who)}, {url}"
    return entry_line(n)


def sources_slide(*panels: tuple[str, tuple[int, ...]]) -> list[str]:
    """A sources slide's lines: for each group, its 'Group:' heading, then its entries in number
    order."""
    lines = []
    for heading, numbers in panels:
        lines.append(f"Group: {heading}")
        lines += [slide_entry(n) for n in sorted(numbers)]
    return lines


SLIDES = [
    # 1 payoff: the question, answered ------------------------------------------------------------
    dict(
        kind="payoff",
        title="The question, answered",
        minutes=3,
        says="The fiscal year 2025 revenue question, wrong at the start and right at the end, "
        "with what each loop contributed and every requirement checked",
        src=".dev/deck2-reconcile.md, The hook and The payoff (runs 9182df01 and 59174f10, "
        "capture hill-climbing-loop-20261024T142825Z.json); deck-evidence E2, E3, E43 (version "
        "13, 0e1cbfe7), E51, E53",
        on_slide=[
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
            "- Cost: under a tenth of a cent",
            "- Trust: every claim traced to a run",
            "Sample: same model throughout, only the knowledge changed; one published run; 8 "
            "runs posted it unattended",
        ],
        notes=[
            "Purpose: Close the story: the question that was wrong at the start is right, posted "
            "at an earned level, with each loop's part and what this run proves checked off.",
            "What to say: At the start of class this question came back as 72,394,572.08 "
            "dollars: no error, a clean sentence, wrong by about 8.4 million dollars. These "
            "cards show the published run. If today's chain posted at the assisted level, the "
            "gate held back autonomy the evidence had not earned; if it was blocked, that "
            "verdict is the loop working; if the safeguard ran, the version is the one verified "
            "in rehearsal. In the middle, the same question, answered 64,015,091.21 dollars, "
            "which matches the gold answer on both databases. On the right is the level: it "
            "posted unattended, because revenue, a metric family, meaning questions of one kind "
            "promoted together, earned that level on its holdout questions. Now the scoreboard. "
            "The agent loop, grounded answers at a bounded cost: it listed and described the "
            "tables and ran one query, inside its budget; the rules in that query came from the "
            "hill-climbing loop. The verification loop: every check passed and nothing was flagged; the "
            "reviewer approved, and you know an approval is a second opinion, not proof. The "
            "event loop took one webhook event, held it while the clearance re-runs finished, "
            "and posted it once. The hill-climbing loop supplied version 13 of the knowledge, "
            "measured on questions the analyzer team never saw and accepted at the gate's "
            "approval step. At the foot, the requirement groups, each checked against this run, "
            "and improvement against the experiment that promoted its version. What one run "
            "cannot show was proved earlier: Section 2's parser and grants stopped the hidden "
            "delete; in Section 3 an approval survived a restart and the kill switch stopped a "
            "run in flight. With those, every card on the slide What we must prove by the end "
            "of today has passed. The model never changed; only the knowledge did.",
            "The point to land: No single loop fixed the answer: the four together made a "
            "correct answer that could post with nobody watching.",
            "Example: The after card is run 59174f10 of 24 October: the question arrived as a "
            "webhook event with no duplicate; the agent listed the tables once, described tables "
            "twice, and ran one query, 12,667 tokens and 0.00055 dollars; every grader passed, "
            "the reviewer approved with no concern, and the gold check matched after the post. "
            "It was held 5 times while the clearance re-runs ran and posted 74 seconds after the "
            "first send; DataPilot has no wall-clock deadline per run, so latency is measured, "
            "not bounded: add a deadline in yours. Revenue cleared the unattended level on its 4 "
            "holdout questions. Version 13 came from the analyzer team's candidate A of two, 22 "
            "of 25 development questions with 9 rules, whose experiment passed 14 of 15 holdout "
            "questions against 2 for version 1, with 0 regressions: that promotion experiment, "
            "0e1cbfe7, is where the Improvement check comes from. It was approved in rehearsal on "
            "24 October by the build session standing in for the instructor; in class the "
            "instructor approves today's candidate. The before card is run "
            "9182df01 of 25 October, version "
            "1: it passed every grader on its last attempt and was held only by the reviewer's "
            "two concerns about the fiscal year, so it never posted. The after run is a day older "
            "than the before run, so compare them by knowledge version, not by date. Eight runs "
            "in all posted 64,015,091.21 dollars at the unattended level with the gold check "
            "passed. The gap, 8,379,480.87 dollars, is derived by subtraction.",
            'Ask the room: "Which of these requirement groups would your current agent fail '
            'first?" Expect: correctness on business rules, or operations when a webhook is '
            "retried.",
            "Misconceptions: That an approval at the gate means a person read the change. In "
            "DataPilot the console records the approver as console and the gate checks only that "
            "the name is not empty, a known gap; in your system, record a signed-in person and "
            "the change they read. And that the hill-climbing loop did the work alone: "
            "without the graders, the holds, and an earned level, a correct answer could not "
            "have posted unattended, and nothing would have stopped a wrong one.",
            "Transition: Here are the four loops again, as one system you can draw for your own "
            "agent.",
        ],
    ),
    # 2 concept diagram: the four loops together ------------------------------------------------
    dict(
        kind="concept",
        title="The four loops together",
        minutes=2,
        says="One agent inside three loops: checked, run on events, and improved with evidence; "
        "the poll's result read back on the map",
        src="docs/diagrams/four-loops.excalidraw; deck-evidence E11, E53; the poll (breaks.py)",
        figure={
            "diagram": "four-loops-generic",
            "alt": "The four loops nested, each part named by its job: in the agent loop, a model "
            "answers with tools and code stops it; in the verification loop, layered checks, then"
            " a person decides a doubtful answer; in the event loop, events arrive, each is keyed"
            " once and queued with leases, a kill switch points at the queue and stops every run,"
            " and human approval comes before a post; beside them the hill-climbing loop, where "
            "failures on a benchmark lead agents to propose rules, the rules are judged on unseen"
            " questions, and a person promotes them, an arrow that runs under the event loop and "
            "up into the model",
        },
        on_slide=[],
        notes=[
            "Purpose: Show the four loops as one system, what each covers that the others cannot, "
            "and read the poll's result back onto the map.",
            "What to say: Here is the map once more, drawn as a pattern you can carry to any "
            "agent. In the middle, the agent loop: a model answers with tools, and code stops "
            "it; its job is grounded answers, bounded cost. Around it, the "
            "verification loop: checks in code first, then a person for a doubtful answer; its "
            "job is safety. The event loop: each event is keyed once and queued with a lease, a "
            "kill switch stops every run, and human approval comes before a post; its job is "
            "operations. Beside them, the hill-climbing loop: failures on a benchmark lead agents "
            "to propose rules, the rules are judged on questions they never saw, and a person "
            "promotes them back; its job is improvement and trust. Correctness is the test that "
            "needs all four, which is why our question was right only after Section 4. In "
            "DataPilot the boxes are the analyst and its schema helper, seven graders and a reviewer, "
            "a jobs table with leases, and an analyzer team behind the promotion gate. Now the "
            "poll: [number] of you have a hill-climbing loop in production, and [number] have "
            "none of the four. If you have the agent loop and nothing else, start with a few "
            "checked gold questions and a check against them: the hill-climbing loop needs "
            "something to measure against.",
            "The point to land: Each loop fixes a failure the others cannot; an answer may go out "
            "with nobody watching only when all four are in place.",
            "Example: A support agent that drafts refund replies, as an illustration: the agent "
            "loop drafts from the order history; the verification loop checks the refund "
            "against policy and the amount against the order; the event loop runs it once per "
            "new ticket, with a stop; the hill-climbing loop learns new policy rules from "
            "rejected drafts, measured on held-back tickets before any rule goes live.",
            'Ask the room: "Which box on this map would you build next, and what must exist '
            'beneath it first?" Expect: a gold check before an improver; a key and a stop before '
            "running from events.",
            "Misconceptions: That the loops are built once. Each needs upkeep: the gold set grows "
            "with every failure, the keys and grants follow the schema, and the holdout wears out "
            "with use.",
            "Transition: Products already cover parts of this map. When should you buy them, and "
            "when build? That decision is next.",
        ],
    ),
    # 3 design callout: build or buy, as a decision framework -----------------------------------
    dict(
        kind="design_callout",
        title="Build or buy: semantic layers and assistants",
        minutes=2.5,
        says="When to buy a semantic layer or warehouse assistant, when to build, and why the "
        "loops are built either way",
        src="docs/text-to-sql-design.md, Build or buy; deck-sources part 3: [30], [32], [33], "
        "[36], [39], [40], [43], [44]; old design.py slide 6 at dev 3c13aa9; deck2-sources part 4 "
        "checked (no forbidden claim)",
        on_slide=[
            "Decision: buy where rules live; build what proves them",
            "| Your situation | Lean toward | Why |",
            "|---|---|---|",
            "| Metrics already in one platform | Buy its layer | Access per asker, "
            "maintained[^33][^36] |",
            "| You must pin the model | Build | Cortex Analyst chooses the model[^36] |",
            "| Rules unwritten or learned | Build the loops | "
            "Products suggest rule changes; you decide and test them[^39][^43] |",
            "DataPilot: Built, so learned rules pass a gate and roll back.",
        ],
        notes=[
            "Purpose: Give learners a decision framework for buying a semantic layer or warehouse "
            "assistant against building, and show why the loops are built either way.",
            "What to say: Treat this as a decision, not a product comparison: three situations, "
            "three answers. First, your metrics already live in one platform: a dbt or Cube "
            "semantic layer, or Snowflake, or Databricks. Then buy its layer or assistant. You "
            "get access control for each asker, applied by the platform, and an interface "
            "someone else maintains. With dbt, MetricFlow writes the SQL, Source 32; Cube's "
            "agents write a Semantic SQL that the layer validates against its model and access "
            "policies, Source 33. Snowflake runs held-back verified queries, judged by a model, "
            "and counts regressions, Source 40, and it now recommends Cortex Agents in Cortex "
            "Analyst's place, Source 36, so check which product is current. Second, you must "
            "choose or pin the model. Then build, or at least own the model call: Cortex "
            "Analyst does not let you choose the model, Source 36. Third, the case every team "
            "meets: rules nobody has written down, or rules you want learned from failures. A "
            "product can suggest rule changes from failures, Sources 39 and 43, but someone "
            "still supplies the first rules and decides which changes to keep. Databricks's own "
            "example is a Genie Agent using calendar quarters instead of "
            "the fiscal calendar, Source 43: our first trap. So whichever you choose, you still "
            "build the loops around it: gold questions, a holdout the improver never sees, a "
            "gate that blocks on a confirmed regression, and checks on executed results. Each "
            "part exists somewhere; the combination is what this course measured, and we did not "
            "compare it with any product.",
            "The point to land: A product is a place to put your rules, not their source; the "
            "loops decide whether a rule is right.",
            "Example: DataPilot built because its rules are learned: the hill-climbing loop "
            "proposes, tests, and rolls back rules in a versioned knowledge file. As an "
            "illustration, a team already on Databricks could keep its metrics in a Genie Agent "
            "and still run its own gold questions and holdout against the Genie Agent's answers; "
            "Databricks itself advises text instructions only as a last resort, Source 44.",
            'Ask the room: "Which platform holds your metrics today?" Expect: dbt, Snowflake, '
            "Databricks, or a spreadsheet; the spreadsheet answer means the rules are not written "
            "yet.",
            "Misconceptions: That the products have no evaluation. They do; the questions to ask "
            "are who sees the deciding questions, and whether a regression blocks a change.",
            "Transition: Next, ten lessons from today, written so they hold beyond this warehouse.",
        ],
    ),
    # 4 closing: ten insights, as transferable lessons ------------------------------------------
    dict(
        kind="closing",
        title="Ten insights to take away",
        minutes=2.5,
        says="Ten lessons that transfer to any agent, each with its evidence in the notes; two "
        "are judgement from what we saw",
        src="deck-evidence E16, E17 and E37 (1), E24 and deck2-reconcile item 1 (2), E24, E27 and "
        "reconcile item 2 (3), E25, reconcile item 3 and round-3 ruling 3 (4), E33 to E35 (5), "
        "E33 (6), E45 and ruling 2 (7), E46 and rulings 2 and 7 (8), E54 and ruling 7 (9), E51 "
        "and reconcile item 5 (10)",
        on_slide=[
            "1. Cap what a tool returns, rows and each value | Section 1",
            "2. Shape checks pass wrong numbers; check meaning too | Section 2",
            "3. A judge with the same knowledge shares the blind spot | Section 2",
            "4. Measure a check layer's cost before you keep it | Section 2",
            "5. Force each failure on purpose to prove each fix | Section 3",
            "6. Key the effect, not the delivery | Section 3",
            "7. One improver run is a sample; write two, gate the one you keep | Section 4",
            "8. A holdout score can pass rules copied from the test | Section 4",
            "9. Fix the knowledge before you change the model | Section 4",
            "10. Grant autonomy per capability, not per system | Section 4",
        ],
        notes=[
            "Purpose: Leave learners with ten lessons that transfer to any agent, each with its "
            "evidence in the notes, tied to the section that taught it.",
            "What to say: Ten lessons, each with its evidence in these notes, and each written so "
            "it holds for an agent that never touches a warehouse. Eight were measured here; two "
            "lessons, seven and nine, are judgement from what we saw. The colour of each number "
            "is the section that taught it. From the agent loop: cap what a tool returns, rows "
            "and each value, inside the tool, because a run budget checked between calls arrives "
            "too late. From verification: checks of shape pass wrong numbers, so something must "
            "check meaning; a judge that shares the writer's knowledge shares its blind spot; and "
            "a check layer has a price, so measure it before you keep it. From the event loop: "
            "prove each fix by forcing its failure on purpose, and key each effect by the "
            "sender's event id or by its meaning, never by the delivery. From hill-climbing: one "
            "improvement run is a sample, so write two, keep one on development questions, and "
            "gate the one you keep; a holdout score alone can pass rules copied from the test; "
            "fix the knowledge first, as the payoff showed; and grant autonomy per capability, "
            "never to the whole system.",
            "The point to land: Eight lessons were measured here and two lessons, seven and nine, "
            "are judgement; build the "
            "same measurement into your own system before you trust its agent.",
            "Example: The evidence, one line per lesson. 1: a 10,000-row query with no cap in the "
            "tool reached 182,654 to 187,030 tokens a run, past a 60,000-token run budget checked "
            "before each call; capped, 17,298 to 30,216. And a row cap is not a size cap: one "
            "approved export row held 5,261 addresses and pushed a run to 109,380 tokens under a "
            "50-row cap; a 2,000-character value cap brought the same export to 7,670. 2: with the graders on but no reviewer, "
            "39 of 40 wrong answers to 20 trap questions went out unflagged; the one stopped was "
            "escalated by the retry cap, not caught as wrong. 3: the reviewer, holding the "
            "analyst's knowledge, approved 19 of the 40 wrong answers and they went out; one more "
            "went out when the reviewer gave no verdict on the retry, so the layer let 20 "
            "through. DataPilot still releases an answer when the reviewer gives no verdict, a "
            "known gap; in yours, hold it. 4: the layer, the reviewer and the syntax-tree guard, "
            "cost about 8,000 more tokens a run and flagged 19 more of 40 wrong answers, 20 of 40 "
            "against 1 of 40, and made none right; every answer on both sides was wrong, so holds "
            "on right answers were not measured: measure them too, as advice. 5: the three planted "
            "event-loop bugs failed in all 17 of their planted runs, 5, 6 and 6, and each fix "
            "held, 7 of 7, 7 of 7, and 9 of 9. 6: the same event sent three times posted 3 answers and 2 digests in "
            "every run with no key, 5 runs, and 1 answer and 1 digest in 7 of 7 runs with the "
            "key. 7, judgement: "
            "single candidates scored 2 to 11 of 15 holdout questions, one of them 12 on a "
            "re-measurement, as the chart showed; pairs, with two candidates "
            "and the analyzer fixes of that session, 12 to 14, so which change helped is "
            "unmeasured; version 15's pair, from the same input, scored 7 and 24 of 25 "
            "development questions. 8: a naive analyzer that copied development "
            "questions and their gold queries into its rules passed 15 of 15 holdout questions "
            "and the three-condition gate said ready; the rules generalised because the holdout "
            "shares its five rules with development. The overfit guard was added after that, and "
            "the naive analyzer's later runs scored 0 to 2 of 15, so the holdout condition alone "
            "would have blocked them: the guard has not yet met a high-scoring copied version "
            "live. 9, judgement: the payoff's point; rules for the five traps took the holdout "
            "from 2 to 13 of 15 under version 11, with 0 regressions; we compared no models. 10: revenue cleared the unattended level in 7 of 11 "
            "promotions, 7 of 8 under today's rule; orders never cleared.",
            'Ask the room: "Which one would change your design next week?" Expect: the gold '
            "check, forcing each failure, or two improvement candidates.",
            "Misconceptions: That these counts are rates. Each is a count from this course's "
            "runs on one model and one warehouse; the lessons transfer, the numbers do not.",
            "Transition: Now turn the lessons into a design for your own warehouse: the checklist.",
        ],
    ),
    # 5 closing: the text-to-SQL design checklist ------------------------------------------------
    dict(
        kind="closing",
        title="Designing text-to-SQL for your warehouse",
        minutes=1.5,
        says="Ten design steps, each pointing to the part of the course that teaches it",
        src="docs/text-to-sql-design.md, The checklist (steps and Taught in); "
        "deck-evidence E5, E11, E12, E28; deck-sources [12], [13], [33], [36], [40], [43], [44], "
        "[45], [49]; round-3 ruling 8 (slide 71)",
        on_slide=[
            "1. Inventory the business rules | Design",
            "2. Build gold questions before the agent | Section 4",
            "3. Choose where each rule lives[^44] | Design",
            "4. Run queries read-only[^13], as the asker | Section 2",
            "5. Describe tables; cap rows and values | Section 1",
            "6. Add value lookup | Assignment 1",
            "7. Validate every query before it runs | Section 2",
            "8. Assume; ask when a term has no rule | Assignment 2",
            "9. Match results on two databases | Section 4",
            "10. Start report-only; earn autonomy | Sections 3 and 4",
        ],
        notes=[
            "Purpose: Give learners the ten-step design checklist of the course page, each step "
            "tied to the part of the course that taught it.",
            "What to say: Ten steps, in the order a team takes them on a new warehouse. "
            "Inventory every business rule an answer depends on, with an owner. Build a gold "
            "question set, split into development and holdout, before you build the agent. "
            "Choose where each rule lives: a view or a semantic layer enforces a metric only if "
            "the agent's role can read nothing else. Run each query read-only, with the asker's "
            "own access. Scope and describe the tables, and cap rows and values. Add value "
            "lookup. Validate every query before it runs. State your assumptions, and ask when a "
            "term has no rule. Measure by execution match on more than one database, Source 12; "
            "two is our minimum, not the paper's. Run the benchmark again on every change to the "
            "schema, a rule, or the data. Start every "
            "metric family at the report-only level, and let it earn autonomy.",
            "The point to land: Design the knowledge, the walls, and the measurement first; the "
            "prompt is the last thing you tune.",
            "Example: The label at the end of each step names where it was taught: Design is "
            "the segment Designing text-to-SQL; Section 1: Agent loop to Section 4: "
            "Hill-climbing loop; Assignment 1: Agent loop and Assignment 2: Verification loop. "
            "Step 9 in full: execution match on two databases, re-run on every change. "
            "Read-only with the asker's own access, as Snowflake and Cube apply it, "
            "Sources 36 and 33; about five tables per agent, Source 44; pin the dates in gold "
            "answers, as Snowflake warns, Source 40. Each step's other course parts: step 1 also "
            "in Section 1: Agent loop, where the five traps fail; step 2 in Assignment 4: "
            "Hill-climbing loop; step 7 in Assignment 2: Verification loop; step 9 in Section 2: "
            "Verification loop, the gold check. Your second database is the same schema with "
            "different rows, a reseeded or masked copy; compare results ignoring row order, with "
            "a numeric tolerance, as Genie's benchmarks round to 4 significant digits, Source "
            "43. Uber had a person confirm the tables its agent picked, Source 49.",
            'Ask the room: "Which step does your system skip today?" Expect: the gold questions '
            "and the holdout split.",
            "Misconceptions: That a semantic-layer product removes steps 1 and 2. A product is "
            "where the rules live, not where they come from: the Databricks blog's agent "
            "answered 0 of 13 benchmark questions until its context was added, Source 45.",
            "Transition: The full checklist, with the decisions and pitfalls for each step, is on "
            "the course page Designing text-to-SQL for your own warehouse. Now, Monday morning.",
        ],
    ),
    # 6 apply-it checklist: use it on Monday ----------------------------------------------------
    dict(
        kind="checklist",
        title="Use it on Monday",
        minutes=2,
        says="Six actions for the learner's own agent, each under an hour",
        src="deck-evidence E5, E16, E28, E30, E33; section READMEs",
        on_slide=[
            "- Ask five questions whose rules live in people's heads; check answers by hand",
            "- Try one write as your agent's database role; it must fail",
            "- Make a check that returns no verdict hold the answer",
            "- Send one event three times; exactly one effect must happen",
            "- Run your gold questions before and after every change",
            "- Write down which answers may go out without a person",
        ],
        notes=[
            "Purpose: Give six concrete actions a learner can take on their own agent on Monday.",
            "What to say: Six things for Monday, each under an hour. One: ask your agent five "
            "questions whose rules live only in people's heads, and compare its answers with "
            "hand-checked ones; they start your gold set. Two: connect as your agent's database "
            "role and try one write; if it succeeds, nothing else you built matters. Three: find "
            "every check whose silence lets an answer through, such as a judge that returns no "
            "verdict, and make silence hold the answer. Four: send one event three times, and "
            "count the effects; anything but one means you need a key. Five: run your gold "
            "questions before and after your next change, and look for answers that broke. Six: "
            "write down which answers may go out without a person reading them; that list is "
            "your report-only level. If you do only one, do the first: the five questions show "
            "you, in an afternoon, whether your agent knows the rules your business runs on.",
            "The point to land: Start with five hand-checked questions; everything else in the "
            "course grows from them.",
            "Example: Our own five traps came from exactly this exercise: the fiscal year, net "
            "revenue, cancelled orders, Eastern time, and internal accounts. For a support agent, "
            "as an illustration, the same exercise is five refund questions whose policy lives in "
            "one manager's head. Where each action was taught: one, the design segment and "
            "Section 4; two, Section 2; three, Section 2, where DataPilot itself still lets a "
            "missing verdict through; four, Section 3; five, Section 4; six, Sections 3 and 4. "
            "Capping tools and putting stops in code are on Section 1's list already.",
            'Ask the room: "Which item would take you longest?" Expect: the hand-checked '
            "answers, then the database role, which often belongs to another team.",
            "Misconceptions: That these wait until the agent is finished. Each one is cheaper "
            "before production than after the first wrong number goes out.",
            "Transition: Now the practice: the four assignments and the final project.",
        ],
    ),
    # 7 closing: assignments and the final project ----------------------------------------------
    dict(
        kind="closing",
        title="Assignments, final project, and the Thursday review",
        minutes=1.5,
        says="Four assignments with live checks, the final project, the deadline and the "
        "solutions; the end of the class",
        src="section-1-agent-loop/assignment/README.md to section-4-hill-climbing-loop/"
        "assignment/README.md; final-project/README.md; docs/review-session.md; "
        "deck-evidence E61",
        on_slide=[
            "Deadline: in the class chat. Solutions: when the Thursday review starts.",
            "1. Assignment 1, Agent loop: a value lookup for informal product names | Section 1",
            "2. Assignment 2, Verification loop: clarify undefined terms; block leaks | Section 2",
            "3. Assignment 3, Event loop: a nightly revenue alert, keyed and stoppable | Section 3",
            "4. Assignment 4, Hill-climbing loop: a new metric family and its holdout | Section 4",
            "5. Final project: the four loops on your own data, with your own benchmark",
        ],
        notes=[
            "Purpose: Set up the practice: four assignments with live checks, the final project, "
            "the deadline, and when solutions appear; then end the class.",
            "What to say: Four assignments, one per loop, each adding a capability the class "
            "code lacks. One: a value lookup, so informal product names resolve to stored values "
            "and a tie becomes a question. Two: graders that ask when a business term is "
            "undefined and block personal data unless a person approved it. Three: a nightly "
            "revenue anomaly alert, one per day by its key, that respects the kill switch. Four: "
            "a new metric family that needs at least three holdout questions before the "
            "unattended level. Each has a live check on your own OpenAI key, stopped at 1 "
            "dollar. The final project runs all four loops on your own data. The deadline is in "
            "the class chat; solutions are published when the Thursday review starts. That is "
            "the end of the class. Post any last question in the chat now; anything longer goes "
            "to the Thursday review. Thank you.",
            "The point to land: Each assignment builds one loop's missing capability yourself, "
            "checked live on the real model.",
            "Example: A typical full check of a working solution cost about 0.4 cents for "
            "Assignment 1 and about 2 cents for Assignment 2, each over 6 clean checks, and 12.62 "
            "to 19.22 cents for a later check of Assignment 4, over 5 audited checks; each check "
            "prints its estimate before it starts.",
            'Ask the room: "Which assignment matches a problem you have at work?" Expect: '
            "Assignment 1 for users' wording, or Assignment 2 for personal data.",
            "Misconceptions: That the checks grade you. Nobody grades the assignments: the "
            "rubric is for assessing your own work, and the check says which requirements pass "
            "live.",
            "Transition: That is the end of the class at 4:00. The sources pages that follow "
            "stay on screen for anyone copying a link.",
        ],
    ),
    # 8 sources, 1 of 7 ---------------------------------------------------------------------------
    dict(
        kind="sources",
        title="Sources: agent design, tools and outputs",
        minutes=SOURCES_MINUTES,
        says="The agent design, tool, stop-condition and structured output sources the deck "
        "cites, by number",
        src=SOURCES_SRC,
        on_slide=sources_slide(
            (
                "Agent design, tools, stop conditions and structured outputs",
                (1, 2, 3, 4, 5, 7, 55, 56, 57, 58, 59, 60, 63, 64),
            ),
        ),
        notes=[
            "Purpose: List the agent design, tool, stop-condition and structured output sources "
            "the deck cites, numbered as the markers on the slides.",
            "What to say: Not presented in class: these seven pages hold every source the slides "
            "and notes cite, numbered as the markers, in number order within each page, the "
            "pages in the order of the class. This page: loop engineering and agent design, "
            "tools and the agent loop, tool search for large tool sets, stop conditions in code, "
            "and structured outputs from OpenAI and LangChain.",
            "The point to land: Every claim in this deck traces to a numbered source or a "
            "recorded run.",
            "Example: Source 4, Anthropic's guide to writing tools, recommends truncating large "
            "tool responses and steering the agent when you do: the row cap and its notice.",
            "Ask the room: None on this slide.",
            "Misconceptions: That the tutorial is a production design. Its own page says its "
            "database tools are not intended to be secure or used in production, Source 5.",
            "Transition: Next, context, helper agents, prompt injection, and parsing.",
        ],
    ),
    # 9 sources, 2 of 7 ---------------------------------------------------------------------------
    dict(
        kind="sources",
        title="Sources: context, prompt injection and parsing",
        minutes=SOURCES_MINUTES,
        says="The context, helper agent, prompt injection, parsing and personal data middleware "
        "sources the deck cites, by number",
        src=SOURCES_SRC,
        on_slide=sources_slide(
            (
                "Context, helper agents, prompt injection and parsing",
                (9, 61, 62, 65, 67, 70, 71, 72, 73, 80, 81),
            ),
        ),
        notes=[
            "Purpose: List the context, helper agent, prompt injection and parsing sources the "
            "deck cites, numbered as the markers on the slides.",
            "What to say: Not presented in class. LangChain's prebuilt middleware, including its "
            "personal-data middleware; context as a budget, progressive disclosure, and helper "
            "agents with their own context; then defence in depth, prompt injection arriving "
            "through data, and parsing SQL into a syntax tree.",
            "The point to land: The patterns of Sections 1 and 2 are documented practice in other "
            "stacks; each slide's Elsewhere line points here.",
            "Example: Source 70, the Open Worldwide Application Security Project's cheat sheet, "
            "treats a guardrail model as one layer in a defence-in-depth design, not a "
            "replacement for input validation or least privilege.",
            "Ask the room: None on this slide.",
            "Misconceptions: That a parser is a security boundary. Source 72 calls SQLGlot a "
            "transpiler, not a validator; the grant is the boundary.",
            "Transition: Next, least privilege, personal data, retries, and judges.",
        ],
    ),
    # 10 sources, 3 of 7 --------------------------------------------------------------------------
    dict(
        kind="sources",
        title="Sources: least privilege, personal data and judges",
        minutes=SOURCES_MINUTES,
        says="The least privilege, personal data, retry and judge sources the deck cites, by "
        "number",
        src=SOURCES_SRC,
        on_slide=sources_slide(
            (
                "Least privilege, personal data, retries and judges",
                (13, 68, 69, 74, 75, 76, 77, 79, 82, 83, 84, 85),
            ),
        ),
        notes=[
            "Purpose: List the least privilege, personal data, retry and judge sources the deck "
            "cites, numbered as the markers on the slides.",
            "What to say: Not presented in class. Least privilege in PostgreSQL, Snowflake and "
            "BigQuery terms, with the Open Worldwide Application Security Project's database "
            "example; sensitive information disclosure; the known biases of a model judging a "
            "model; and bounded retries.",
            "The point to land: The database's grants are the boundary; a session setting or a "
            "prompt is not.",
            "Example: Source 74: a read-only default can be overridden by SET TRANSACTION for an "
            "individual transaction, so it is a setting, not a boundary.",
            "Ask the room: None on this slide.",
            "Misconceptions: That a judge model is neutral. Source 82 names position, verbosity "
            "and self-enhancement biases, Source 83 finds evaluators favour their own "
            "generations, and Source 84 finds model mistakes becoming more alike: a general risk, "
            "not a study of SQL judges.",
            "Transition: Next, the research, queues, and delivery.",
        ],
    ),
    # 11 sources, 4 of 7 --------------------------------------------------------------------------
    dict(
        kind="sources",
        title="Sources: research, queues and delivery",
        minutes=SOURCES_MINUTES,
        says="The text-to-SQL research, queue, idempotency and delivery sources the deck cites, "
        "by number",
        src=SOURCES_SRC,
        on_slide=sources_slide(
            (
                "Text-to-SQL research, queues, idempotency and delivery",
                (16, 17, 18, 21, 26, 27, 28, 86, 87, 88, 89),
            ),
        ),
        notes=[
            "Purpose: List the text-to-SQL research, queue, idempotency and delivery sources the "
            "deck cites, numbered as the markers on the slides.",
            "What to say: Not presented in class. The research on why real warehouses are hard: "
            "BIRD, Spider 2.0, LinkAlign, and the SEED audit; then queues in Postgres and SKIP "
            "LOCKED, Stripe's keys and webhook events, at-least-once delivery, and Amazon's "
            "visibility timeout.",
            "The point to land: The research agrees with our runs: the hard part is the knowledge "
            "outside the schema, and the measurement.",
            "Example: Source 89: a message not deleted before its visibility timeout becomes "
            "visible again, and another consumer can take it: a lease, in a managed queue.",
            "Ask the room: None on this slide.",
            "Misconceptions: That written business rules are correct because people wrote them. "
            "The SEED audit found wrong evidence in 105 of 1,534 BIRD development pairs, Source "
            "21.",
            "Transition: Next, leases, durable execution, stopping, and autonomy.",
        ],
    ),
    # 12 sources, 5 of 7 --------------------------------------------------------------------------
    dict(
        kind="sources",
        title="Sources: leases, durable execution and autonomy",
        minutes=SOURCES_MINUTES,
        says="The lease, durable execution, stopping, autonomy and evaluation sources the deck "
        "cites, by number",
        src=SOURCES_SRC,
        on_slide=sources_slide(
            (
                "Leases, durable execution, stopping, autonomy and evaluation",
                (10, 90, 91, 92, 93, 95, 96, 98, 100, 103, 104, 105, 106),
            ),
        ),
        notes=[
            "Purpose: List the lease, durable execution, stopping, autonomy and evaluation "
            "sources the deck cites, numbered as the markers on the slides.",
            "What to say: Not presented in class. Human-in-the-loop in LangChain; dead-letter "
            "queues, Google's lease management and Kafka's delivery semantics; durable execution "
            "and human approval in Temporal and LangGraph; interruptibility, levels of autonomy, "
            "and chaos engineering's forced failures; then evaluation-driven development.",
            "The point to land: Every queue named here delivers at least once; exactly one effect "
            "is the consumer's job, with a key.",
            "Example: Source 95: Temporal recommends that Activities be idempotent, because they "
            "may be executed more than once.",
            "Ask the room: None on this slide.",
            "Misconceptions: That the three autonomy levels need no credit. Their names and the "
            "drops on an incident and on the kill switch follow Greyling, Source 2; Feng and "
            "others, Source 103, define five levels by the user's role, and placing ours on them "
            "is our reading, not theirs: assisted maps to their approver role, unattended to "
            "their observer role. Nor does a managed queue give exactly-once side effects: Kafka's needs "
            "the destination's cooperation, Source 92.",
            "Transition: Next, datasets, executed results, variation, and Goodhart's law.",
        ],
    ),
    # 13 sources, 6 of 7 --------------------------------------------------------------------------
    dict(
        kind="sources",
        title="Sources: evaluation, variation and Goodhart's law",
        minutes=SOURCES_MINUTES,
        says="The dataset, executed-result, repetition, holdout, variation, Goodhart's law and "
        "first promotion gate sources the deck cites, by number",
        src=SOURCES_SRC,
        on_slide=sources_slide(
            (
                "Datasets, executed results, variation, Goodhart's law and promotion",
                (12, 108, 109, 110, 111, 112, 113, 114, 116),
            ),
        ),
        notes=[
            "Purpose: List the dataset, executed-result, holdout, variation, Goodhart's law and "
            "promotion sources the deck cites, numbered as the markers on the slides.",
            "What to say: Not presented in class. Evaluation by executed result on more than one "
            "database; datasets, repeated runs, development and holdout splits; run-to-run "
            "variation even at temperature zero; Goodhart's law in Strathern's phrasing; and "
            "promoting a model only when it beats the current one.",
            "The point to land: Holdouts wear out and models vary; a gate re-measures on every "
            "change instead of trusting one score.",
            "Example: Source 113 gives Strathern's phrasing of Goodhart's law, from her 1997 "
            "paper, Source 114: when a measure becomes a target, it ceases to be a good measure.",
            "Ask the room: None on this slide.",
            "Misconceptions: That temperature zero makes runs repeatable. Source 111 shows "
            "inference endpoints are not deterministic in practice; repeat runs instead.",
            "Transition: The last page: promotion gates, drift, and the products.",
        ],
    ),
    # 14 sources, 7 of 7 --------------------------------------------------------------------------
    dict(
        kind="sources",
        title="Sources: gates, drift and the products",
        minutes=SOURCES_MINUTES,
        says="The promotion gate, drift, semantic layer and warehouse assistant sources the deck "
        "cites, by number",
        src=SOURCES_SRC,
        on_slide=sources_slide(
            (
                "Promotion gates, drift, semantic layers and warehouse assistants",
                (32, 33, 36, 37, 39, 40, 43, 44, 45, 49, 117, 118),
            ),
        ),
        notes=[
            "Purpose: List the promotion gate, drift and product sources the deck cites, numbered "
            "as the markers on the slides.",
            "What to say: Not presented in class. This page: the dbt Semantic Layer, Cube, and Snowflake's "
            "Cortex Analyst with its semantic views, suggestions and evaluations; Databricks's "
            "Genie pages and blog, and Uber's QueryGPT; then required reviewers on a deployment, "
            "and drift behind one model name. Every course number traces to the course's own "
            "evidence pages, listed on the course's sources page.",
            "The point to land: A product is a place to put your rules; the sources show what each "
            "product measures and what it leaves to you.",
            "Example: Source 45: the Databricks blog's agent answered 0 of 13 benchmark "
            "questions at first; the blog puts it down to missing context, not to the model.",
            "Ask the room: None on this slide.",
            "Misconceptions: That buying a product removes the need to write business rules. "
            "Snowflake's own page says schemas lack business process definitions and metrics, "
            "Source 36.",
            "Transition: None: the class ended on the assignments slide; this page stays on "
            "screen for anyone copying a link.",
        ],
    ),
]
