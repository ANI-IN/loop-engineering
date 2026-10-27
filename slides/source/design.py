"""Designing text-to-SQL: the design segment, 0:30 to 0:40, 10 minutes, 4 slides (the second rebuild).

The owner's specification for the second rebuild (.dev/deck-spec-2.md), section 4 item 6: business
knowledge decides the answer; why real warehouses are hard; the nine-stage reference architecture;
one decisions slide (where rules live, one shot or an agent, assume or ask, how much schema).
"Build or buy" moved to the closing. The block is taught as transferable design judgement, with
DataPilot as the worked example: at most one course number on a slide, run ids and sample sizes in
the notes. Course numbers come from .dev/deck-evidence.md (entries named in each slide's src);
external figures from .dev/deck-sources.md, whose numbering every source marker [^n] uses. The audit
(.dev/deck-audit-2.md, current slides 8 to 13) decided what was kept, moved to the notes, or moved
to other blocks. "What to say" stays within minutes x 130 words, less 40 for the room question.
"""

RULES = "design system 2"

SLIDES = [
    # 1 insight: what one business rule is worth -----------------------------------------------------
    dict(
        kind="insight",
        title="Business rules decide answers: test like code",
        minutes=2,
        says="One unwritten rule moves revenue by 1.6 million dollars, and written rules are often "
        "wrong too: give every rule an owner, a version, and a test",
        src="deck-evidence E8 (derived: 65,592,532.44 against 64,015,091.21), E6, E5; deck-sources "
        "part 2: [21] Section I and Table II; [16] Table 2; [45]; audit 8 (T-improve)",
        on_slide=[
            "Insight: One rule nobody wrote down moved our revenue answer by "
            "1.6\u00a0million\u00a0dollars.",
            "Evidence: Audited, a public benchmark's written rules were 105 of 1,534 wrong, 148 "
            "missing[^21]",
            "- Give every rule an owner who can say it still holds",
            "- Version rules, so a bad one can be rolled back",
            "- Test rules on questions with hand-checked answers",
        ],
        notes=[
            "Purpose: Open the design segment with what one business rule is worth, and why "
            "written rules need an owner, a version, and a test, like code.",
            "What to say: You know rules decide the number; here is what one is worth. "
            "On our warehouse, fiscal year 2025 net revenue with every rule applied is "
            "64,015,091.21 dollars. Leave out the rule that excludes internal accounts and it is "
            "65,592,532.44: one unwritten rule, 1.6 million dollars. We built that trap on purpose, "
            "so the mechanism is visible. Nobody planted anything in BIRD, a public benchmark, "
            "where GPT-4's execution accuracy on the test set rose from 34.88 to 54.89 percent "
            "when each question came with its rule sentence, Source 16. And writing rules down is "
            "not the end. The SEED audit of BIRD's development set found 105 of its 1,534 rule "
            "sentences wrong and 148 missing; correcting those 105 raised a fine-tuned model from "
            "44.76 to 54.29 percent on them, Source 21. So treat rules the way you treat code. "
            "Each one has an owner who can say it is still true. Each one is versioned, so you "
            "can roll it back. And each one is tested against questions whose answers a person "
            "checked by hand.",
            "The point to land: Business rules decide the number; write them down, give each an "
            "owner and a version, and test them against hand-checked answers.",
            "Example: A support agent's refund policy is the same kind of rule (illustrative): if "
            "the 30-day window lives only in a team lead's head, the agent answers confidently and "
            "wrongly. In our warehouse, a rule written as the word harborpine anywhere in the "
            "email, not the domain, comes out 28,474.44 dollars low: written, and still wrong.",
            'Ask the room: "Who owns your definition of net revenue?" Expect: finance, an '
            "analyst, or nobody in particular.",
            "Misconceptions: That writing the rules down solves it. Written rules have defects "
            "too; only a test against checked answers tells you which.",
            "Transition: So why are questions over a real warehouse hard? Four reasons.",
        ],
    ),
    # 2 insight: why real warehouses are hard ----------------------------------------------------------
    dict(
        kind="insight",
        title="Why real warehouses are hard",
        minutes=2.5,
        says="Definitions that differ by team, large cryptic schemas, informal values, and wrong "
        "numbers that look right: each is about meaning, not syntax",
        src="deck-evidence E5, E6, E10; deck-sources part 2: [17] abstract and Table 5, [18] "
        "Appendix B, [37], [49], [12] Table 2; audit 9 (T-improve: the sample line to the notes)",
        on_slide=[
            "Insight: Every hard part is about meaning: valid SQL can still answer the wrong "
            "question.",
            "Evidence: On enterprise schemas, the paper's best agent solved 21.3 percent[^17]",
            "- Teams differ: one revenue, several formulas",
            "- Schemas are large[^17] and cryptically named[^37]",
            "- Informal values: filter on an unstored word, get nothing[^49]",
            "- Wrong numbers look right: one database wrongly passed 6.5 percent of queries[^12]",
        ],
        notes=[
            "Purpose: Name the four reasons questions over a real warehouse go wrong, so every "
            "later design decision answers one of them.",
            "What to say: Four reasons, one per line. First, definitions differ by team. You heard "
            "it in the problem statement: finance, sales, and marketing each have a formula for "
            "revenue, and the agent has to pick one. Second, schemas are large "
            "and cryptically named. Spider 2.0 built 632 tasks on enterprise databases often over "
            "1,000 columns, and the paper's best agent solved 21.3 percent, Source 17. Snowflake's "
            "documentation gives the example of gross revenue in a column named amt ttl pre dsc, "
            "Source 37. Third, values are informal. A user asks about the blue hiking jacket; the "
            "warehouse stores a name nobody says aloud. Uber's tool filtered on status Finished "
            "when the stored value was Completed: the query ran and returned nothing, Source 49. "
            "Fourth, a wrong number looks exactly like a right one. Checking results on the one "
            "database a benchmark ships wrongly passed 6.5 percent of all predicted queries, on "
            "average over 21 Spider submissions, Source 12. Those are the papers' own percentages. Notice "
            "what the four share: the model writes valid SQL in every case, and the answer is "
            "still wrong.",
            "The point to land: Each difficulty is about meaning, not syntax: the model can write "
            "valid SQL and still answer the wrong question.",
            "Example: A coding agent hits the same wall (illustrative): it can write code that "
            "compiles against a codebase whose conventions live only in reviewers' heads. Our run "
            "at the start used calendar dates, Coordinated Universal Time, and every account, and "
            "nothing failed.",
            'Ask the room: "Which of the four hurts your warehouse most?" Expect: the naming, '
            "then, after a pause, the definitions that differ by team.",
            "Misconceptions: That classic benchmark scores describe your warehouse. Classic "
            "benchmarks have small, clean schemas; Spider 2.0 was built because enterprise work "
            "looks different.",
            "Transition: Here is a reference architecture that answers all four, in nine stages.",
        ],
    ),
    # 3 concept diagram: the reference architecture ----------------------------------------------------
    dict(
        kind="concept",
        title="Nine stages from question to checked answer",
        minutes=3,
        says="Nine stages from question to evaluated answer; the model writes the query in only "
        "one of them",
        src="platform/tools/diagrams/definitions.py text_to_sql_architecture_generic; "
        "docs/text-to-sql-design.md, the reference architecture; deck-sources [18] Appendix B; "
        "audit 10 (T-improve: generic stage names first, DataPilot's choices second)",
        figure={
            "diagram": "text-to-sql-architecture-generic",
            "alt": "The text-to-SQL reference architecture in nine stages, each named by its job and its"
            " loop: question routing, where fixed code sends each question to its path; schema "
            "linking, which finds the tables and columns that matter; business knowledge as "
            "rules, versioned and tested; value lookup, which matches words to stored values; "
            "query generation, where a model writes the query; validation by syntax tree, cost, "
            "and personal-data checks; capped execution with a read-only role and a row cap; an "
            "answer that is reviewed, with its assumptions stated, or a question back; and "
            "evaluation, which compares results with gold answers on two databases and sends "
            "failures back to the business knowledge",
        },
        on_slide=[],
        notes=[
            "Purpose: Give learners one reference architecture for text-to-SQL that fits any "
            "warehouse, with DataPilot's choice at each stage as the worked example.",
            "What to say: Whether a product or your own code runs it, every text-to-SQL system has "
            "these nine stages. For each, the job first, then DataPilot's choice. One, routing: "
            "fixed code sends each question to its path; DataPilot uses a table, never a model. "
            "Two, schema linking: find the tables and columns that matter; DataPilot's schema "
            "helper may only list and describe tables, though our runs showed no gain from it, a "
            "gap Section 1 returns to. Three, business knowledge: rules, versioned and tested; "
            "DataPilot puts a versioned file in every prompt. Four, value lookup: match the user's "
            "words to stored values; Assignment 1 builds it. Five, generation: a model writes one "
            "read-only query; in DataPilot, the analyst agent. Six, validation before anything "
            "runs: parse the syntax tree, allow one schema and let the grants decide its tables, "
            "estimate the cost, and hold "
            "personal data. Seven, capped execution: a read-only role, a timeout, and a row cap "
            "with the total count. Eight, the answer: reviewed, with stated assumptions, or a "
            "question back. Nine, evaluation: compare results, not query text, with gold answers "
            "on two databases. The arrow back to three is how failures become new rules. Now the "
            "lesson: routing, validation, execution, and evaluation are code; models link the "
            "schema, write the query, review the answer, and propose rules. Put every guarantee "
            "in a code stage.",
            "The point to land: Text-to-SQL is a pipeline of nine decisions; the model writes the "
            "query in only one of them, and every guarantee lives in a code stage.",
            "Example: In the run you saw at the start, every check of stage six passed and the "
            "query ran cleanly in stage seven; only the gold check of stage nine proved the number "
            "wrong.",
            'Ask the room: "Which stages does your system have today?" Expect: generation and '
            "execution; rarely value lookup or evaluation.",
            "Misconceptions: That stage five is the system. When LinkAlign pooled every Spider "
            "database's schema, schema-linking errors caused 68.3 percent of a "
            "retrieval-plus-DIN-SQL baseline's failures, Source 18, "
            "and our traps all sit in stage three: most failures come from what the model was "
            "given, not from SQL syntax.",
            "Transition: Each stage hides a choice. Four of them decide most designs; here they "
            "are, with their trade-offs.",
        ],
    ),
    # 4 design callout: the four decisions -------------------------------------------------------------
    dict(
        kind="design_callout",
        title="Four decisions every text-to-SQL design makes",
        minutes=2.5,
        says="Where rules live, one shot or an agent, assume or ask, and how much schema, with "
        "what to lean toward and what DataPilot chose",
        src="deck-evidence E19, E20; deck-sources [3], [18], [30], [37], [44], [49]; "
        "docs/text-to-sql-design.md, steps 3, 5, and 8 and 'What the course did not measure'; "
        "audit 11 and 12 (the Measured column moved to Sections 1, 2 and 4)",
        on_slide=[
            "Decision: which way to lean, and why",
            "| Decision | Options | Lean toward |",
            "|---|---|---|",
            "| Where rules live | Prompt, file, semantic layer, view | Views for formulas[^44]; a "
            "file for learned rules |",
            "| One shot or agent | One call, or a loop | Simplest that passes tests[^3] |",
            "| Assume or ask | State it, or ask | Assume aloud; ask if undefined |",
            "| How much schema | All, scoped, retrieved | Five or fewer per agent[^44] |",
            "DataPilot: gated rules, an agent, stated assumptions, tables on demand.",
        ],
        notes=[
            "Purpose: Give four design decisions every text-to-SQL system faces, with their "
            "trade-offs, what to lean toward, and what DataPilot chose.",
            "What to say: Four decisions. Where rules live. The prompt is fastest and drifts. A "
            "view or a semantic layer computes a formula once, in the database, but enforces it "
            "only if the agent can read nothing else. A versioned file can be learned, tested, "
            "and rolled back. Databricks advises text instructions only as a last resort, Source "
            "44. We chose a file, because the hill-climbing loop must propose and gate rules. One "
            "shot or an agent. One call is cheaper and faster; an agent can inspect tables and "
            "repair a refused query. Anthropic advises the simplest solution that works, Source 3. "
            "We chose an agent and never measured it against one shot, so treat it as open. "
            "Assume or ask. A question back leaves nothing to check; an answer with stated "
            "assumptions lets a reviewer and a gold check judge it. So assume, say so, and ask "
            "when a business term has no rule. How much schema. More schema means more to "
            "confuse; Databricks advises five or fewer tables, Source 44, and at scale an agent "
            "proposes candidate tables and a person confirms them, as Uber's table agent does, "
            "Source 49.",
            "The point to land: Put rules where you can test and roll them back, start simple, "
            "state assumptions a checker can judge, and show the model only the tables it needs.",
            "Example: A support agent faces the same assume-or-ask choice (illustrative): for "
            '"refund my last order", it states which order it picked; for a premium plan nobody '
            "defined, it asks. Our analyst asked about VIP customers and about loyal customers, "
            "one run each.",
            'Ask the room: "Which of your rules could become a view today?" Expect: net revenue, '
            "active customer.",
            "Misconceptions: That a semantic layer guarantees the formula. Only if the agent "
            "cannot reach the base tables; it can still pick the wrong metric or grain.",
            "Transition: Now we build the first loop of that design: the agent loop.",
        ],
    ),
]
