"""Closing block: 8 slides, 3:50-4:00."""

from sources import SOURCES

R = "<!-- refresh after the session: {} -->"
QA = "No Question Is Too Small Every Question Deserves an Answer!!"

SLIDES = [
    {
        "kind": "closing",
        "title": "Final run: one question through four loops",
        "layout": "diagram",
        "minutes": 1.5,
        "says": "Wrong alone, green but wrong, safe and stoppable, then right and cleared",
        "src": "final-project/README.md",
        "on_slide": [
            '"What was our net revenue in fiscal year 2025?"',
            "1. Agent loop: confident and wrong; several of the five traps in one query",
            "2. Verification loop: every grader green, gold still fails on both databases",
            "3. Event loop: the same agent runs on events, with keys, durable approval, and a stop; "
            "the finale arrives this way",
            "4. Hill-climbing loop: right under a gated version, posted at the level its "
            "family earned",
            "Lesson: each loop fixed a different failure, and none needed a bigger model",
        ],
        "notes": [
            "Say: Retell the spine question's path. In Section 1: Agent loop it was confident and "
            "wrong. In Section 2: Verification loop every check turned green and it was still "
            "wrong; on 24 October its SQL carried 3 trap labels. In Section 3: Event loop the same "
            "agent ran on events, with keys, durable approval, and a stop that reaches running "
            "work; the spine question itself returns in Section 4, as a webhook. In Section 4: Hill-climbing loop it became right, through rules that passed a "
            "gate on questions the analyzer never saw, and it posted at the level its metric "
            "family earned: the unattended level if revenue cleared on the confirmed standard. If "
            "revenue did not clear in the class run, say so: the answer was right and posted at the "
            "assisted level, because the gate did not see enough evidence. In the live session of 24 "
            "October revenue cleared under the promoted version, v11, and the spine answer, "
            "64,015,091.21 dollars, matching gold, posted at the unattended level, as it had under "
            "v8 and v9; under v5 revenue did not clear and the answer was wrong.",
            "Point at: the four stages in order.",
            'Likely question: "Can I run the whole path myself?" Answer: yes; the final project '
            "runs it end to end on your machine.",
            "Transition: All the results on one slide.",
        ],
        "container": "step cards: the spine question's four stages",
    },
    {
        "kind": "closing",
        "title": "All results: one picture",
        "layout": "table",
        "minutes": 1.5,
        "says": "One row per section: what the loop changed, as counts from the paired live runs of 24 October",
        "src": "docs/benefits.md; docs/calibration-report.md",
        "on_slide": [
            "| Loop | Without it | With it |",
            "|---|---|---|",
            "| Agent loop, 21 runs | 12 of 21 correct | 17 of 21 correct |",
            "| Verification loop, 40 runs | 0 of 40 correct; 1 escalated | 0 of 40 correct; 20 held or escalated |",
            "| Event loop, one run per half | 3 answers for one event | 1 answer, 2 duplicates absorbed |",
            "| Hill-climbing loop, 15 items | Holdout 2 of 15 | 13 of 15, no regressions |",
            "How to read this: samples differ per row; read the rows as what happened, not as rates.",
        ],
        "notes": [
            "Say: Read one row per section as counts, not percentages. Each row is the same "
            "questions or demo with the loop's protection switched off, then on, in one rehearsal "
            "session of 24 October. Agent loop: seven questions without traps, 3 runs each, 12 of "
            "21 correct with names-only tools, no row cap, and no scout, 17 of 21 with them; the "
            "unbounded rows demo took 182,654 tokens without the cap against 30,216 with it. "
            "Verification loop: 20 trap questions, twice each, 0 of 40 correct either way; without "
            "the layer 1 wrong answer was escalated, with it 20 were held or escalated; the retry "
            "cap stopped at 3 attempts, and no malicious statement changed a warehouse row in "
            "either half. Event loop: one event sent three times posted 3 answers without the "
            "key, 1 with it. Hill-climbing loop: the starting version passed 2 of 15 holdout items; the version "
            "promoted on 24 October, v11, passed 13 of 15 with 0 regressions, and the finale posted "
            "the correct spine answer at the unattended level.",
            "Say plainly where a loop did not help: the verification layer made no trap answer "
            "correct; it held or escalated 20 of 40 wrong answers against 1, and the reviewer, "
            "which shares the analyst's knowledge, approved the other 19; the event loop prevents duplicates and lost approvals, not wrong "
            "numbers; and the analyzer's quality varies from run to run, candidates of 2 to 11 of "
            "15 from the same input, which is why it writes two and keeps the better on dev.",
            "Re-check after live runs: every count on the slide against the paired measurements "
            "page of 24 October.",
            "Point at: the hill-climbing row.",
            'Likely question: "Where are the runs behind these counts?" Answer: on the page of '
            "paired measurements in the course repository, with each run's id.",
            "Transition: Which loop to reach for, and when.",
        ],
        "container": "table: loop | without it | with it",
    },
    {
        "kind": "closing",
        "title": "Which loop when: match the failure",
        "layout": "table",
        "minutes": 1.5,
        "says": "Match the failure you see to the loop that fixes it",
        "src": "docs/architecture.md",
        "on_slide": [
            "| You see | Reach for | First check |",
            "|---|---|---|",
            "| Wrong because the agent cannot see enough | Agent loop | What does each tool "
            "return? |",
            "| Unsafe, unbounded, or endless work | Verification loop | Which stop is not the "
            "model's? |",
            "| Duplicates, unwatched risk, a stop that misses | Event loop | Is every effect "
            "keyed? |",
            "| The same kind of error, again and again | Hill-climbing loop | Which questions "
            "never train it? |",
        ],
        "notes": [
            "Say: Use this as a decision table at work. Find the failure you see in the left "
            "column. If the agent cannot see enough, fix the tools first. If work is unsafe or "
            "never ends, add layers and caps. If effects repeat or nobody can stop them, add keys, "
            "durable approval, and a stop that reaches running work. If the same kind of mistake "
            "keeps returning, learn rules from failures, but only behind a gate on held-out "
            "questions.",
            "Point at: the right column, in order.",
            'Likely question: "Which one first?" Answer: the one matching your most expensive '
            "failure this quarter.",
            "Transition: Taking it to your own systems.",
        ],
        "container": "table: you see | reach for | first check",
    },
    {
        "kind": "closing",
        "title": "Use it at work: four questions to ask",
        "layout": "concept",
        "minutes": 1,
        "says": "Questions to ask of any agent system you run",
        "src": "use-in-your-repo/README.md",
        "on_slide": [
            "**What can the agent see, and what is capped?** Tool output decides what it can know.",
            "**Which stop is not the model's choice?** A loop the model can extend has no end.",
            "**What makes a repeated event harmless?** Delivery is at least once.",
            "**Which questions does your gate never learn from?** Only unseen questions measure "
            "learning.",
        ],
        "notes": [
            "Say: Take these four questions to any agent system you run, SQL or not. Each one maps "
            "to a loop. The course repository also has a template domain pack, so you can point "
            "the same loops at your own database, write gold queries for your own questions, and "
            "start from an empty knowledge version. One pack setting selects the pack every "
            "component reads; each pack keeps its own knowledge versions, and preflight reads its "
            "data check and canary from it.",
            "Point at: the four questions.",
            'Likely question: "Does it work beyond Postgres?" Answer: the class runs on Postgres; '
            "the principles do not depend on it, and the final project covers your own Postgres.",
            "Transition: Practice comes next.",
        ],
        "container": "four cards: one question per loop, each with why",
    },
    {
        "kind": "closing",
        "title": "Assignments, final project, and the Thursday review",
        "layout": "concept",
        "minutes": 1.5,
        "says": "Four assignments, each with a live check; solutions published when the Thursday review starts",
        "allow_commands": True,
        "src": "docs/review-session.md",
        "on_slide": [
            "Assignment 1: Agent loop: a value lookup for informal names, recorded in assumptions",
            "Assignment 2: Verification loop: clarify or abstain, and a personal-data leak grader",
            "Assignment 3: Event loop: a nightly revenue anomaly alert, keyed and stoppable",
            "Assignment 4: Hill-climbing loop: a repeat-customer family and a minimum-holdout rule",
            "Each has a live check with your own OpenAI key. Deadline: [ASSIGNMENT DEADLINE]; "
            "solutions published when the Thursday review starts.",
            "Final project: one question through all four loops, on your machine",
        ],
        "notes": [
            "Say: Each assignment adds a capability class code does not have. Each assignment has "
            "a live check, `make check-assignment NAME=<slug>`. It runs the done-when scenario on "
            "the real stack with your own OpenAI key, reports pass or fail per requirement with a "
            "trace link and a live stamp, and prints its cost estimate first and the actual cost at the "
            "end. There are no stubs or canned model answers in any check: every check is live. "
            "Solutions are published when the Thursday review starts. The deadline in square "
            "brackets is a placeholder, replaced before class. The final project runs the spine "
            "question through all four loops end to end on your own machine, with its own "
            "walkthrough and checklist.",
            "Point at: Assignment 4, which turns the open question about small holdouts into a "
            "rule.",
            'Likely question: "What does the check cost me?" Answer: it prints its estimate '
            "before it starts and the actual cost when it ends, on your own key. Measured in the "
            "build's verification: typically about 0.4 cents for a full check of Assignment 1, "
            "about 2 cents for Assignment 2, and about 0.2 cents for Assignment 3; and for "
            "Assignment 4, which runs the benchmark, about 13 to 24 cents for each later check of "
            "a live session (12.62 to 23.95 cents, seven checks: five audited clean, and two, of "
            "23 October at 13.58 and 23.95 cents, not confirmed clean). The first check of a live "
            "session, which also runs the baseline, is an estimate, about 24 cents: no clean first "
            "check has been measured. These are measured costs, not bounds; the costs page lists "
            "every measured check. Every check stops at its own spend cap of 1 dollar.",
            "Transition: The class in three lines.",
        ],
        "container": "four cards, one per assignment",
    },
    {
        "kind": "closing",
        "title": "Summary: key takeaways",
        "layout": "concept",
        "minutes": 1,
        "says": "Agents only where judgement is needed; code and people decide; autonomy is earned",
        "src": "README.md",
        "on_slide": [
            "Tools and caps decide what the agent can know: no model sees what a tool withholds",
            "Deterministic checks and gates decide; agents advise: code cannot be talked out of "
            "a rule",
            "Autonomy is earned per metric family, from held-out evidence: a stop that reaches "
            "running work takes it back",
            "One rule under all three: never let an agent grade its own work",
        ],
        "notes": [
            "Say: Three lines. What the agent can know is decided by its tools and their caps. "
            "Deterministic checks and gates decide; agents advise them. Autonomy is earned per "
            "metric family, from evidence the learner never saw, and taken back by a stop that "
            "reaches running work.",
            "Point at: the three lines.",
            'Likely question: "What is the one rule?" Answer: never let an agent grade its own '
            "work.",
            "Transition: Where every claim came from.",
        ],
        "container": "three cards: takeaway | why",
    },
    {
        "kind": "closing",
        "title": "References",
        "layout": "table",
        "minutes": 1,
        "says": "Every source, numbered by section",
        "src": "slides/source/sources.py, the source register",
        "on_slide": [
            "| Sources | Topic |",
            "|---|---|",
            "| 1 | The four loops |",
            "| 2 to 7 | Agent loop: evidence, enterprise schemas, schema linking, structured "
            "output |",
            "| 8 to 12 | Verification loop: false positives, permissions, error codes, stops |",
            "| 13 to 17 | Event loop: queues, durable approval, autonomy levels |",
            "| 18 to 23 | Hill-climbing loop: learned rules, evidence quality, prior art |",
            "How to read this: numbered by section, Source 1 first; full titles and links are in this "
            "slide's notes.",
        ],
        "notes": [
            "Say: The sources are numbered by section: Source 1 for the four loops, then each "
            "section's sources in a range of its own. The full list, with titles, authors, and links, is below and closes each section page.",
            *SOURCES,
            "Point at: the hill-climbing row: the prior art you can compare with.",
            'Likely question: "Which one should I read first?" Answer: BIRD for evidence, then the '
            "test-suite accuracy paper for why one database is not enough.",
            "Transition: Last questions.",
        ],
        "container": "table: sources by topic",
    },
    {
        "kind": "questions",
        "title": "Questions and close",
        "layout": "concept",
        "minutes": 1,
        "says": "No Question Is Too Small Every Question Deserves an Answer!!",
        "src": "-",
        "on_slide": [
            "No Question Is Too Small Every Question Deserves an Answer!!",
            "See you at the Thursday review: [THURSDAY REVIEW TIME]",
        ],
        "notes": [
            "Say: Take the last questions. Remind everyone to post Thursday questions in the chat. "
            "End at 4:00. The review time in square brackets is a placeholder, replaced before "
            "class.",
            "Point at: the Thursday line.",
            'Likely question: "Where do I start after class?" Answer: setup, then the Section 1 '
            "demos on your own machine.",
            "Transition: End of class.",
        ],
        "container": "key-idea box: fixed question wording",
    },
]
