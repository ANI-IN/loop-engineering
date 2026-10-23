"""Closing block: 8 slides, 3:50-4:00."""

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
            "1. Agent loop: confident and wrong; four traps in one query",
            "2. Verification loop: every grader green, gold still fails on both databases",
            "3. Event loop: runs as an event, holds for approval, stops when told",
            "4. Hill-climbing loop: right under a gated version, posted at the level its "
            "family earned",
            "Lesson: each loop fixed a different failure, and none needed a bigger model",
        ],
        "notes": [
            "Say: Retell the spine question's path. In Section 1: Agent loop it was confident and "
            "wrong. In Section 2: Verification loop every check turned green and it was still "
            "wrong. In Section 3: Event loop it ran as an event with an approval and a stop that "
            "works. In Section 4: Hill-climbing loop it became right, through rules that passed a "
            "gate on questions the analyzer never saw, and it posted at the level its metric "
            "family earned: the unattended level if revenue cleared on the confirmed standard. If "
            "revenue did not clear in the class run, say so: the answer was right and posted at the "
            "assisted level, because the gate did not see enough evidence. In calibration revenue "
            "has not yet cleared on the confirmed standard.",
            R.format(
                "stage 4, once the finale chain with the SQL guidance check and two candidates has "
                "run live: the spine answer against gold and the level it posted at"
            ),
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
        "says": "One row per section, as counts from the class run",
        "src": "docs/evidence.md",
        "on_slide": [
            "| Loop | What calibration showed |",
            "|---|---|",
            "| Agent loop | 0 of 99 trap runs passed under the starting rules |",
            "| Verification loop | No write landed; retry cap escalated after 3 attempts |",
            "| Event loop | 2 duplicates absorbed; approval survived a restart |",
            "| Hill-climbing loop | Holdout 2 of 15, then 10 to 12 of 15; 0 regressions |",
            "How to read this: counts from calibration; say today's class counts beside them",
            R.format(
                "the hill-climbing row once the finale chain with the SQL guidance check and two "
                "candidates has run live: the kept candidate's holdout count and the families cleared"
            ),
        ],
        "notes": [
            "Say: Read one row per section as counts, not percentages, then say what today's runs "
            "showed beside each. Under the starting rules no trap item passed in 99 runs. No "
            "malicious statement changed a warehouse row, and the retry cap ended the run escalated "
            "after 3 attempts. The event loop absorbed 2 duplicates and kept an approval across a "
            "worker restart. The promoted rules moved the holdout from 2 of 15 to 12 of 15, flipping "
            "10 of 13 holdout trap items with 0 regressions, and a later promotion to 10 of 15. Say "
            "plainly where a result was weaker than hoped: the same analyzer input also gave "
            "candidates of 2, 3, 5, 6, and 9 of 15, which is why the analyzer now writes two and "
            "keeps the better on dev; revenue has not yet cleared on the confirmed standard; and 15 "
            "holdout items rest on few questions per family.",
            "Re-check after live runs: every count on the slide against the calibration report and "
            "the evidence pages.",
            "Point at: the hill-climbing row.",
            'Likely question: "Where are the runs behind these counts?" Answer: on the evidence '
            "pages, one per section, with their trace links.",
            "Transition: Which loop to reach for, and when.",
        ],
        "container": "table: loop | what the class run showed",
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
            "What can the agent see, and what is capped? Tool output decides what it can know",
            "Which stop is not the model's choice? A loop the model can extend has no end",
            "What makes a repeated event harmless? Delivery is at least once",
            "Which questions does your gate never learn from? Only unseen questions measure "
            "learning",
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
            "Each has a live check on the real stack with your own OpenAI key: pass or fail per requirement, a trace link, and its cost",
            "Solutions published when the Thursday review starts",
        ],
        "notes": [
            "Say: Each assignment adds a capability class code does not have. Each assignment has "
            "a live check, `make check-assignment NAME=<slug>`. It runs the done-when scenario on "
            "the real stack with your own OpenAI key, reports pass or fail per requirement with a "
            "trace link and a live stamp, and prints its cost estimate first and the actual cost at the "
            "end. There are no stubs or canned model answers in any check: every check is live. "
            "Solutions are published when the Thursday review starts. The deadline is set by "
            "the instructor.",
            "Point at: Assignment 4, which turns the open question about small holdouts into a "
            "rule.",
            'Likely question: "What does the check cost me?" Answer: it prints its estimate '
            "before it starts and the actual cost when it ends, on your own key. Measured in the "
            "build's verification: about 0.4 cents for a full check of Assignment 1, 0.34 to 0.42 "
            "cents over six checks; about 2 cents for Assignment 2, 1.84 to 2.28 over six; about 0.3 "
            "cents for Assignment 3, 0.23 to 0.40 over six; and for Assignment 4, which runs the "
            "benchmark, 30.66 cents for the first check of a live session and about 15 cents for "
            "each later one, 10.69 to 20.56 over five. Every check stops at its own spend cap of 1 "
            "dollar.",
            R.format(
                "the cost of Assignment 4's check once it is verified live again with the gate's "
                "fourth condition and two analyzer candidates"
            ),
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
        "says": "Every source, in order of first use",
        "src": "the course research synthesis",
        "on_slide": [
            "| Sources | Topic |",
            "|---|---|",
            "| 1 | The four loops |",
            "| 2 to 7 | Agent loop: evidence, enterprise schemas, schema linking, structured "
            "output |",
            "| 8 to 12 | Verification loop: false positives, permissions, error codes, stops |",
            "| 13 to 17 | Event loop: queues, durable approval, autonomy levels |",
            "| 18 to 23 | Hill-climbing loop: learned rules, evidence quality, prior art |",
            "How to read this: numbered in order of first use; full titles and links close the "
            "outline",
        ],
        "notes": [
            "Say: The sources are numbered in the order the notes first cite them. The full list, "
            "with titles, authors, and links, closes this outline and each section page.",
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
            "See you at the Thursday review",
        ],
        "notes": [
            "Say: Take the last questions. Remind everyone to post Thursday questions in the chat. "
            "End at 4:00.",
            "Point at: the Thursday line.",
            'Likely question: "Where do I start after class?" Answer: setup, then the Section 1 '
            "demos on your own machine.",
            "Transition: End of class.",
        ],
        "container": "key-idea box: fixed question wording",
    },
]
