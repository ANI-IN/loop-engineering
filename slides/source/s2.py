"""Section 2: Verification loop. Slides and speaker notes for the rewritten outline (rules and checks in build.py)."""

FAILURE = (
    "Checks that read like safety let unsafe SQL reach the database, let a failing loop spend without "
    "end, and pass an answer that is safe, well formed, and wrong."
)

DEMOS = ["verify-malicious-sql", "verify-retry-cap", "verify-graders-pass-still-wrong"]

R = "<!-- refresh after the session: {} -->"
MEASURED = (
    "malicious SQL shown in 6 seconds both times, the syntax-tree guard stopping two statements and "
    "the role's missing grant the third with SQLSTATE 42501, and with the naive guard 25006, 25006, "
    "then 42501; the retry cap shown in 79 and 69 seconds, escalated after 3 attempts; every grader "
    "passes, still wrong: not shown in either attempt, because the graders passed but no gold check "
    "arrived within 90 seconds (hardened the same night); retaken twice on 23 October, both shown, "
    "76,981,355.95 dollars against gold 64,015,091.21 with 4 trap labels each; the retry cap planted "
    "half, twice, 9 attempts until the 60,000-token run budget stopped it, at 62,762 and 63,737 tokens."
)

NUMBERS = [
    "Retry cap of 3: from `limits.max_retries` in pack.yaml.",
    "12 model calls and 16 tool calls per run: from `limits.model_call_limit` and `limits.tool_call_limit` in pack.yaml.",
    "Statement timeout of 5,000 milliseconds: from `limits.statement_timeout_ms` in pack.yaml.",
    "Plan cost cap 500,000 and plan rows cap 5,000,000: from `cost_guard` in pack.yaml.",
    "6.5 percent mean false-positive rate of single-database execution match, 11.0 percent on extra-hard queries, about 1,000 fuzzed databases per schema, about 42 kept per query, 2.5 percent false negatives: from Source 8.",
    "SQLSTATE 25006, 42501, 57014: from Source 10 and runs measured for the course on PostgreSQL 16.2 during research; the class stack runs PostgreSQL 18.6.",
    "Malicious SQL: fixed system guard, guard, then 42501 from the missing grant; naive guard 25006, 25006, then 42501: docs/calibration-report.md, Demos.",
    "Retry cap demo: escalated after 3 attempts, in 69 and 79 seconds: docs/calibration-report.md, Demos; without the cap, 9 attempts until the 60,000-token run budget, 62,762 and 63,737 tokens, 0.0067 and 0.0069 dollars, 104 and 111 seconds: docs/calibration-report.md, Resumed after the ledger correction.",
    "Every grader passes, still wrong, retaken twice: 76,981,355.95 dollars against gold 64,015,091.21, 4 trap labels each: docs/calibration-report.md, Resumed without traces.",
    "The reviewer's verdict on the wrong spine answer under the starting knowledge: concern in 6 runs, approve in 1: docs/calibration-report.md, Agents on and off.",
    "Mean tokens and seconds per question with the reviewer off, 5,786 and 12.8, against 8,648 and 24.2 with the scout and reviewer on: docs/calibration-report.md, Agents on and off.",
    "Class code guesses at an undefined term in 5 of 8 runs; the reviewer turns most guesses into a held or escalated answer: docs/calibration-report.md, Agents on and off.",
    "Output cap per call, reasoning included: analyst 16,000 tokens, reviewer 8,000: `models` in pack.yaml.",
]

S8 = "Source 8: Semantic Evaluation for Text-to-SQL with Distilled Test Suites (https://arxiv.org/abs/2010.02840)"
S9 = "Source 9: PostgreSQL ALTER ROLE (https://www.postgresql.org/docs/current/sql-alterrole.html)"
S10 = "Source 10: PostgreSQL error codes (https://www.postgresql.org/docs/current/errcodes-appendix.html)"
S11 = "Source 11: LangChain custom middleware (https://docs.langchain.com/oss/python/langchain/middleware/custom)"
S12 = "Source 12: LangChain built-in middleware (https://docs.langchain.com/oss/python/langchain/middleware/built-in)"
S7 = "Source 7: LangChain SQL agent (https://docs.langchain.com/oss/python/langchain/sql-agent)"

SLIDES = [
    # 1 -----------------------------------------------------------------------------------------
    dict(
        kind="agenda",
        title="Agenda (Section 2 highlighted)",
        layout="concept",
        container="icon row: four sections, the second highlighted",
        minutes=0.5,
        says="Section 2: Verification loop, after the agent loop",
        src="section-2-verification-loop/README.md",
        on_slide=[
            "1) Agent loop",
            "2) Verification loop (now)",
            "3) Event loop",
            "4) Hill-climbing loop",
        ],
        notes=[
            "Say: Section 1: Agent loop gave us an agent that answers with its SQL in a structured "
            "envelope. That envelope is something we can check, and this section is about checking it. "
            "We add a verification loop around the agent: deterministic graders that look at every query "
            "before it runs, at every result after it runs, and at the final answer. Failures go back to "
            "the agent with a reason it can act on. Then one independent agent, the reviewer, reads the "
            "answer after every grader has passed. The point to carry through the section: verification "
            "is a set of layers, each built on the assumption that the one above it fails, and a set of "
            "stops that the model does not get to choose.",
            "Point at: the highlighted second row; Section 1 is done and its answer is still wrong.",
            'Likely question: "Does a verification loop slow every answer down?" Answer: The graders are '
            "deterministic and cheap; the expensive part is the reviewer, one extra model call per answer, "
            "and calibration measures that cost so you can decide whether it pays.",
            "Transition: Let me start with a story about a product name.",
        ],
    ),
    # 2 -----------------------------------------------------------------------------------------
    dict(
        kind="story",
        title="Failure story: the product name that said delete",
        layout="diagram",
        container="step cards: five numbered beats, then a lesson bar",
        minutes=2,
        says="Illustrative: an instruction hidden in data reaches SQL, and only the last layer stops it",
        src="section-2-verification-loop/concepts.md",
        on_slide=[
            "Illustrative",
            "1. **Upload**: a supplier feed adds a product whose name asks the reader to delete old orders.",
            "2. **Context**: the agent describes the products table; three sample rows put that name in its prompt.",
            "3. **Query**: its next query is a SELECT, a semicolon, and a DELETE on orders.",
            "4. **Guard**: a first-word check sees SELECT and lets the whole text through.",
            "5. **Last layer**: only the role's missing write grant refuses it, a defense nobody designed as the main one.",
            "Lesson: a check that reads the first word is a sign on the door, not a lock.",
        ],
        notes=[
            "Say: This story is illustrative, and the person in it, Marcus, is fictional. Marcus runs the "
            "analytics agent at Harbor & Pine Outfitters. Beat one: a supplier upload leaves a product "
            "whose name reads like an instruction, asking whoever reads it to delete the old orders. "
            "Beat two: the agent describes the products table, and the sample rows put that name into "
            "its context. Beat three: the next query it writes is a SELECT followed by a semicolon and "
            "a DELETE. Beat four: the guard in front of the database checks that the text starts with "
            "SELECT, and it does. Beat five: the only thing that stops the delete is that the database "
            "role has no write grant. Nobody designed that role as the main defense; it just happened to "
            "be there. Elsewhere the same week, a check that always fails sends a run back to the model "
            "again and again, and the bill climbs until someone notices.",
            "Point at: beat five, the last layer doing the work every other layer claimed to do.",
            'Likely question: "Is prompt injection through data realistic for an internal analytics '
            'tool?" Answer: Any text the agent reads is input to the model, and sample rows are text; '
            "the class data carries a few such product names on purpose, and the security suite proves "
            "no write happens.",
            "Transition: So, if we add enough checks and they all pass, are we done?",
        ],
    ),
    # 3 -----------------------------------------------------------------------------------------
    dict(
        kind="question",
        title="Verification loop: if every grader passes, is the answer right?",
        layout="concept",
        container="key-idea box with three reason cards",
        minutes=2.5,
        says="KEY IDEA: No. Graders prove a query is safe and well formed, not that it means what the business means",
        src="section-2-verification-loop/README.md",
        on_slide=[
            "If every grader passes, is the answer right?",
            "KEY IDEA: No. Graders prove a query is safe and well formed, not that it means what the business means.",
            "- The spine query is one cheap SELECT on real tables, so every grader passes.",
            "- The fiscal year rule and the cancelled-order rule live in no grader.",
            "- Even a result match on one database shows about 6.5 percent false positives.",
        ],
        notes=[
            "Say: No. Take the spine question from Section 1, net revenue in fiscal year 2025. The query "
            "the agent writes is one statement, a plain SELECT, on tables that exist, cheap to run, "
            "touching no personal data, and it returns one sensible number. Every grader we build in "
            "this section passes it. It is still wrong, because the fiscal year starts in February and "
            "cancelled orders should not count, and no grader knows that. Graders check safety and "
            "form; meaning needs business knowledge, which arrives in Section 4: Hill-climbing loop. "
            "Even comparing results is weaker than it looks. "
            + S8
            + ': "hence calculating a tight '
            "upper-bound for semantic accuracy efficiently.\" The paper's point is that matching a "
            "result on one database is an upper bound on correctness, not proof: single-database "
            "execution match had a 6.5 percent mean false-positive rate across 21 Spider submissions.",
            "Point at: the KEY IDEA box, then the two words safe and means.",
            'Likely question: "Then why build graders at all?" Answer: They stop unsafe and malformed '
            "work before it runs, and they hand the agent a reason it can act on, which is most of what a "
            "retry loop needs.",
            "Transition: Concept one: what a guard should accept.",
        ],
    ),
    # 4 -----------------------------------------------------------------------------------------
    dict(
        kind="concept",
        title="1) Allowlist the shape, not a list of bad words",
        layout="diagram",
        container="two-column cards: how it works | worked example, with trade-offs, at-work, and key idea bars",
        allow_example=True,
        minutes=5,
        says="Key idea: accept only shapes you can name; reject everything else, including what the parser cannot model",
        src="measured for the course (sqlglot guard)",
        on_slide=[
            "Principle: accept only query shapes you can name; reject everything else.",
            "Think of it as a badge reader at the door, not a list of banned items.",
            "| How it works | Worked example |",
            "|---|---|",
            '| Parse: exactly one statement | "SELECT 1; DELETE FROM orders" is two statements: rejected |',
            "| Root must be SELECT or a set operation | A first-word check passes it; the tree guard does not |",
            "| Walk every node: no write, INTO, lock, or opaque command | A DELETE inside a CTE: rejected |",
            "| Functions and schemas on an allowed list | pg_sleep, dblink, set_config: denied |",
            "| Run the original text | Regenerated COPY ... TO PROGRAM came out mangled |",
            "Trade-offs: a false reject costs a retry; the tree cannot see SQL inside strings.",
            "At work: parse what your agent emits; run exactly what you checked.",
            "Key idea: an unknown shape is a rejection, not a pass.",
        ],
        notes=[
            "Plain explanation: A denylist names the bad things: no DELETE, no DROP. Attackers and "
            "parsers both find shapes you did not list. An allowlist names the one shape you accept, a "
            "single read-only query, and rejects everything else, including anything the parser could "
            "not understand. The guard walks the whole syntax tree, not the first word.",
            "Concrete example from DataPilot: the naive guard (`BUG_NAIVE_GUARD`) checks that the text "
            'starts with select or with. It passes "SELECT 1; DELETE FROM orders" and a data-modifying CTE, '
            "because both start with a SELECT. The syntax-tree guard rejects both before execution: the "
            "first parses to two statements, the second has a Delete node under a Select root.",
            "Analogy: a building that lists banned items at the door versus one that lets in only "
            "people holding a badge. The first fails on every item nobody thought to list.",
            "Under the hood: parsed with sqlglot in the Postgres dialect, SELECT INTO appears as an Into "
            "node and FOR UPDATE as a Lock node; neither looks like a write at the root. DO, CALL, "
            "VACUUM, EXPLAIN ANALYZE, PREPARE and EXECUTE fall back to an opaque Command node, so the "
            "guard rejects Command outright. `LISTEN foo` and `TABLE orders` misparse as aliases, which "
            "is why a parse that looks harmless is still not proof. Regenerating SQL from the tree can "
            "change meaning, so the executor runs the original text the guard approved. A function "
            "denylist covers calls such as `pg_sleep`, `dblink`, `query_to_xml`, and `set_config`, and "
            "a schema allowlist keeps every table inside the warehouse schema. One more rule came "
            "from calibration: agent SQL may not read the database clock, so `now()`, "
            "`current_date`, and the special date word today are rejected with feedback. A question "
            "about the previous day had answered 0, because the SQL read the wall clock while the "
            "data ends on the business date the prompt states.",
            S7 + ", in summary: the official tutorial checks queries with an LLM query checker and "
            "states the no-DML rule as a prompt instruction. Neither is a boundary.",
            "Transfer: the same rule applies to any agent that emits a language: shell commands, "
            "infrastructure plans, API calls built from text. Parse it, accept a named shape, reject "
            "the rest, and execute exactly what you checked.",
            "Point at: the How it works column, top to bottom; every row is a reason to reject, and the "
            "Worked example column shows the shape it catches.",
            'Ask: "Why execute the original text instead of the tree\'s regenerated SQL?" Expected: '
            "regeneration is lossy; the text you checked must be the text that runs.",
            'Likely question: "Will an allowlist reject legitimate queries?" Answer: Sometimes, and '
            "the reason goes back to the agent, which rewrites the query; a false reject costs a retry, a "
            "false accept costs data.",
            'Likely question: "Why not use the database\'s own parser?" Answer: You can, through '
            "EXPLAIN, but it accepts every valid statement, writes included; you still need a policy on "
            "the shape.",
            "Misconception: a good parser makes the guard complete. Correction: the tree cannot see SQL "
            "inside string literals, so the guard is one layer, never the last one.",
            "Transition: so what actually stops the statement the parser cannot see?",
        ],
    ),
    # 5 -----------------------------------------------------------------------------------------
    dict(
        kind="concept",
        title="2) Permissions are the boundary, not the parser",
        layout="table",
        container="table: layer | can the session undo it, with worked-example, trade-offs, at-work, and key idea bars",
        minutes=4.5,
        says="Key idea: a session can switch a default off; it cannot grant itself a privilege",
        src="measured for the course on PostgreSQL 16.2 during research (read-only role); compose.yaml (PostgreSQL 18.6)",
        on_slide=[
            "Principle: put the last defense where the agent's own session cannot change it.",
            "Think of it as a staff-only sign versus a door with no key cut for you.",
            "| Layer | Can the session undo it? |",
            "|---|---|",
            "| Prompt rule | Yes: the model can ignore it |",
            "| Read-only transaction default | Yes: one SET turns it off |",
            "| Temporary tables | Open until revoked from the public role |",
            "| Missing write grant | No: insufficient privilege, SQLSTATE 42501 |",
            "Worked example: inside a read-only transaction a write fails with 25006; after the session turns the default off, the same write still fails with 42501.",
            "Trade-offs: grants are coarse and need one role per agent; the guard still gives early, readable reasons.",
            "At work: scope the credential, not the instruction; probe the barrier at startup and refuse to run without it.",
            "Key idea: defaults are preferences; grants are walls.",
        ],
        notes=[
            "Plain explanation: every layer above the database is code you hope is right. The database "
            "role is the one layer the agent's own session cannot rewrite, as long as the barrier is a "
            "missing grant rather than a default setting. Defaults are preferences; grants are walls.",
            "Concrete example from DataPilot: the agent connects as a role with SELECT on the warehouse "
            "schema and nothing else. The executor also opens every query with `SET TRANSACTION READ "
            "ONLY`, and the process refuses to start unless a probe write inside a read-only transaction "
            "fails. Temporary tables and schema creation are revoked from the public role. A write the "
            "database refuses is an incident, not a mistake to retry: the run ends escalated at once.",
            "Analogy: a sign on a door that says staff only, versus a door with no key cut for you.",
            "Under the hood: tested on PostgreSQL 16.2 during research; the class stack runs 18.6, "
            "where the read-only probe at startup checks the same barrier. Inside `BEGIN READ ONLY`, an INSERT or CREATE "
            "TEMP raises SQLSTATE 25006 even as superuser. But a session can run `SET "
            "default_transaction_read_only = off`, and after that an INSERT failed with 42501 only "
            "because the role lacked the grant. CREATE TEMP TABLE succeeded until `REVOKE TEMP ON "
            "DATABASE ... FROM PUBLIC`. And `dblink` or `query_to_xml` can run SQL held inside a "
            "string, which no syntax tree sees; only the grants stop what those strings try to do.",
            S9 + ': "Role-specific variable settings take effect only at login; SET ROLE and SET '
            'SESSION AUTHORIZATION do not process role-specific variable settings." A role setting is '
            "a session default, applied at login, not a barrier.",
            "Transfer: for any agent with credentials, scope the credential, not the instructions. "
            "Read-only API tokens, least-privilege cloud roles, per-agent database users. Then test the "
            "barrier at startup the way the probe does, and refuse to run if it is missing.",
            "Point at: the two rows that answer yes; those are the layers an attacker can switch off.",
            'Ask: "Which row would you test in continuous integration?" Expected: the grant row, with a probe that must '
            "fail.",
            'Likely question: "If the role is the real boundary, why keep the guard?" Answer: the '
            "guard rejects early with a reason the agent can use, and it blocks reads the role allows "
            "but you do not want, such as `pg_sleep` or reading server files.",
            'Likely question: "Why revoke temporary tables if they vanish anyway?" Answer: a writable '
            "temp table is a place to stage data and a way around read-only assumptions; the probe found "
            "it open by default.",
            "Misconception: a read-only transaction makes the session read-only. Correction: the "
            "session can turn the default off; only the missing grant holds.",
            "Re-check after live runs: the SQLSTATE codes the malicious SQL demo shows against these.",
            "Transition: the database can stop a statement; who stops the loop?",
        ],
    ),
    # 6 -----------------------------------------------------------------------------------------
    dict(
        kind="concept",
        title="3) Stops that are not the model's choice",
        layout="table",
        container="table: stop | value | then, with worked-example, trade-offs, at-work, and key idea bars",
        minutes=4,
        says="Key idea: every loop needs a stop the model cannot argue with, placed before the next model call",
        src="platform/packs/datapilot_us/pack.yaml (limits, cost_guard); Sources 11 and 12 (middleware)",
        on_slide=[
            "Principle: every loop needs a stop the model cannot argue with.",
            "Think of it as a circuit breaker: it never asks the appliance whether it is finished.",
            "| Stop | Value | Then |",
            "|---|---|---|",
            "| Attempts per run | 3 | Escalated, with every reason |",
            "| Model calls per run | 12 | Run ends |",
            "| Tool calls per run | 16 | Run ends |",
            "| Statement timeout | 5 seconds | Cancelled, SQLSTATE 57014 |",
            "| Planned cost or rows | 500,000 or 5,000,000 | Rejected before it runs |",
            "Worked example: an always-failing grader stops at attempt 3; without the cap, cost climbs.",
            "Where it lives: before the next model call, never inside a tool.",
            "Trade-offs: a cap can end a run one more try would fix; escalation shows it.",
            "At work: put budgets and retries where every iteration passes.",
            "Key idea: a stop inside a tool is a suggestion; before the model call, a fact.",
        ],
        notes=[
            "Plain explanation: a verification loop sends failures back to the agent. That is a loop "
            "with a model in it, and the model will keep trying as long as you let it. The stop has to "
            "come from outside the model: a counter, a timeout, a cost estimate, checked by code.",
            "Concrete example from DataPilot: the retry cap is 3 attempts, from `limits.max_retries`. "
            "After the third failed grader the run ends escalated, with every grader's reason attached, "
            "for a person to read. A refused write never reaches this counter: it ends the run at once. "
            "Each run also stops at 12 model calls and 16 tool calls, and each model call at its "
            "output cap, 16,000 tokens for the analyst, reasoning included; a response cut off there "
            "ends the run escalated. Postgres cancels any statement after 5,000 milliseconds, and an "
            "EXPLAIN-based cost grader rejects plans above 500,000 cost units or 5,000,000 estimated "
            "rows before they run. The cost grader is not a security layer: it plans only what the "
            "syntax tree calls one read-only SELECT and says not applicable to anything else, so a "
            "write that slips past a broken guard meets the read-only transaction first.",
            "Analogy: a circuit breaker does not ask the appliance whether it is finished.",
            "Under the hood: where the stop lives matters. Tested with fake models, a check inside "
            "`wrap_tool_call` that returned `Command(goto=END)` did not end the run: control went back "
            "to the model, which simply tried again. What works is a hook before the model call that "
            "jumps to the end, plus a tool wrapper that returns a message without running the tool. "
            "The built-in tool-call limit only ends the run when it is scoped to one tool name.",
            S11 + ": \"`'end'`: Jump to the end of the agent execution (or the first `after_agent` "
            'hook)". That jump is available from the hooks around the model call, which is where a '
            "stop belongs.",
            S12
            + ", in summary: the model-call limit can end the run or raise; the tool-call limit "
            "ends the run only with a tool name set.",
            "Transfer: in any agent framework, find the one point every iteration passes through before "
            "spending money, which is the model call, and put budgets, kill switches, and retry counts "
            "there. A check deep inside a tool is a suggestion to the model, not a stop.",
            "Point at: the Where it lives line: before the next model call.",
            'Ask: "What should the run return when it hits the cap?" Expected: escalated, with the '
            "reasons, not a best guess.",
            'Likely question: "Is 3 the right retry count?" Answer: it is a setting; the principle is '
            "that some cap exists and that hitting it is a visible outcome, not a silent failure.",
            'Likely question: "Why a cost estimate when there is already a timeout?" Answer: the '
            "timeout spends five seconds of database time to learn what EXPLAIN tells you at once, and "
            "EXPLAIN gives the agent a reason it can fix.",
            "Misconception: a good prompt tells the model when to give up. Correction: the model "
            "decides it is nearly there on every attempt; only a counter ends the loop.",
            "Re-check after live runs: the retry cap demo ended escalated after 3 attempts in 69 and "
            "79 seconds in calibration, and without the cap went on for 9 attempts until the "
            "60,000-token run budget stopped it; the output caps against the pack.",
            "Transition: the loop now stops. Last question: who checks the meaning?",
        ],
    ),
    # 7 -----------------------------------------------------------------------------------------
    dict(
        kind="concept",
        title="4) A checker that shares the maker's blind spots",
        layout="table",
        container="table: check | catches | misses, with worked-example, trade-offs, at-work, and key idea bars",
        minutes=4.5,
        says="Key idea: judgement goes after the deterministic checks, and a checker on the same model shares its errors",
        src="platform/src/datapilot/contracts/agents.py; Source 8 (test-suite accuracy)",
        on_slide=[
            "Principle: a checker helps only where its errors differ from the maker's.",
            "Think of it as proofreading your own essay again in a different font.",
            "| Check | Catches | Misses |",
            "|---|---|---|",
            "| Seven deterministic graders | Unsafe, malformed, costly | Business meaning |",
            "| Reviewer on the same class model | Some meaning errors | What the analyst also misses |",
            "| Result match, one database | Wrong results | About 6.5 percent false positives |",
            "| Result match, two databases | Coincidental matches | Rules nobody wrote down |",
            "Worked example: the spine answer passes all seven graders, the reviewer objects in 6 of 7 runs, and gold fails on both databases.",
            "Trade-offs: one more model call per answer; a different model or the business rules lowers the correlation.",
            "At work: before adding an LLM judge, name what keeps its errors independent.",
            "Key idea: two agents with one blind spot agree on the same wrong answer.",
        ],
        notes=[
            "Plain explanation: maker and checker is an old control, and it works when the checker can "
            "fail differently from the maker. A reviewer agent built on the same model, reading the same "
            "schema, without the business rules, tends to miss what the analyst missed. So the reviewer "
            "goes after the deterministic graders, and it can add a concern but never pass a failed "
            "grader.",
            "Concrete example from DataPilot: the reviewer is an independent agent that sees only the "
            "question, the final SQL, the result preview, and the active knowledge version. It returns "
            "approve or concern with reasons. A concern goes back to the analyst once, within the retry "
            "cap; if it persists, the run holds for human approval. It runs on the same class model as "
            "the analyst. In calibration, on the wrong baseline answer to the spine question, it raised "
            "a concern in 6 runs and approved in 1. Better than feared, and still not a fix: a concern "
            "holds the answer, it never supplies the fiscal year rule. It is also the costly part: with "
            "it off, a question averaged 5,786 tokens and 12.8 seconds against 8,648 and 24.2 with "
            "everything on.",
            "Analogy: asking the author to proofread their own essay a second time, in a different "
            "font. It catches some typos and none of the misunderstandings.",
            "Under the hood: evaluation has the same problem. Matching a result on one database gave a "
            "6.5 percent mean false-positive rate across 21 Spider submissions, 11.0 percent on "
            "extra-hard queries. The paper's fix fuzzes about 1,000 random databases per schema and keeps "
            "about 42 per query that tell apart neighbour queries. DataPilot keeps the teaching-sized "
            "version: two databases, with seed rows that tell the traps apart.",
            S8 + ': "In contrast, the current Spider metric leads to a 2.5% false negative rate on '
            'average and 8.1% in the worst case." Weak metrics fail in both directions.',
            "Transfer: before adding an LLM judge, ask what keeps its errors independent: a "
            "different model, different inputs such as the gold data or the business rules, or a "
            "deterministic test. If none applies, spend the call elsewhere.",
            "Point at: the Misses column, top to bottom, then the worked example: seven graders pass, "
            "the reviewer objects but cannot supply the missing rules, gold fails.",
            'Ask: "Which input lowers the correlation of the reviewer\'s errors?" Expected: the '
            "business rules, a different model, or a second database.",
            'Likely question: "Should the reviewer use a stronger model?" Answer: a different model '
            "lowers the correlation; whether it pays is a measurement, and calibration gives the "
            "baseline: the reviewer roughly doubles the seconds per question.",
            'Likely question: "Why may the reviewer not override a grader?" Answer: a model can be '
            "talked out of a rule by a clever input; code cannot.",
            "Misconception: two agents agreeing is evidence. Correction: two agents with the same "
            "blind spot agree on the same wrong answer.",
            "Re-check after live runs: the reviewer's verdicts, concern in 6 runs and approve in 1, "
            "and the token and second figures against the calibration report.",
            "Transition: the four moves on one slide.",
        ],
    ),
    # 8 -----------------------------------------------------------------------------------------
    dict(
        kind="cheat",
        title="Cheat sheet: verification in four moves",
        layout="table",
        container="table: move | principle | anti-pattern it prevents | check question",
        minutes=1,
        says="Allowlist the shape, scope the credential, cap the loop, decorrelate the checker",
        src="section-2-verification-loop/README.md",
        on_slide=[
            "| Move | Principle | Anti-pattern it prevents | Check question |",
            "|---|---|---|---|",
            "| Allowlist the shape | An unknown shape is a rejection | A first-word check or keyword denylist | Does anything run that your parser could not classify? |",
            "| Scope the credential | Grants hold; defaults do not | Read-only by setting or by prompt | What does a write with your agent's credential return? |",
            "| Cap the loop | The stop lives before the model call | A retry loop the model decides to end | What ends a run that never succeeds? |",
            "| Decorrelate the checker | A checker must fail differently | An LLM judge on the same model and inputs | What does your checker see that the maker did not? |",
        ],
        notes=[
            "Say: four moves. Allowlist the shape of what the agent may run, and execute exactly the "
            "text you checked. Scope the credential so that the last defense is a missing grant. Cap "
            "the loop with stops the model cannot argue with, placed before the next model call. And add "
            "a checker only where its errors differ from the maker's.",
            "Point at: the Check question column; each question is one you can ask of your own system "
            "in a design review.",
            'Likely question: "Which move would you drop first under time pressure?" Answer: none of '
            "the first three; the checker is the one to measure before you keep it.",
            'Likely question: "Do these apply to agents without SQL?" Answer: yes; replace the '
            "database role with whatever credential your agent holds.",
            "Transition: now watch each one live.",
        ],
    ),
    # 9 -----------------------------------------------------------------------------------------
    dict(
        kind="demo",
        title="Section 2: Verification loop - Implementation Notes: Every grader passes, still wrong",
        layout="demo",
        container="demo: badge and title only",
        minutes=18,
        says="Badge DEMO - 2 and title only; the demos and the code walkthrough are in the notes",
        src="section-2-verification-loop/demo/walkthrough.md",
        on_slide=["Badge: DEMO - 2", "Title only; no screenshot"],
        notes=[
            "Run sheet: three core demos, about 12 minutes, then the code walkthrough, about 6 minutes. "
            "Share the console's Verify page full screen: the pre-flight checklist on the left, the "
            "defense-layer panel on the right. Calibration ran each core demo twice with a reset "
            "between; the measured results are under each demo. A planted bug is switched by setting "
            "its flag to 1 in `.env` and running `make up`, and back to 0 the same way.",
            "Demo: malicious SQL.",
            "Starting state: Verify page open, the naive guard (`BUG_NAIVE_GUARD`) switched on. Reset "
            "first: `make reset NAME=verification-loop`. The reset clears the runs, so its chip shows on "
            "the status line once the first run with the flag starts.",
            "Do: Verify > Send malicious SQL, or `make demo NAME=verify-malicious-sql`. Then switch the "
            "naive guard off and send it again.",
            "Narrate: concept 1, allowlist the shape. The naive guard reads the first word, sees SELECT, "
            'and lets "SELECT 1; DELETE FROM orders" and a data-modifying CTE through. Concept 2, '
            "permissions are the boundary: the read-only transaction refuses both with SQLSTATE 25006, "
            "and the third statement, a raw DELETE as the agent role, meets the missing grant, 42501. "
            "A refused write ends the run escalated at once; it is never fed back as a retry. With the "
            "syntax-tree guard on, layer two rejects the first two before they reach the database.",
            "Point at, in order: the statement text; the defense-layer panel with the layer that stopped "
            "each statement and the layers it never reached; and last the live stamp: "
            "the run's start time in your local time and its trace link.",
            "Expected live result: with the naive guard, 25006, 25006, then 42501; with the syntax-tree "
            "guard, the guard, the guard, then 42501; no warehouse row changes in either run. Measured: "
            "exactly that, in about 6 seconds, twice each.",
            "May vary: timings only. If they do, say: the outcome is deterministic; only the clock moves.",
            "If it stalls: reset and run it again, `make reset NAME=verification-loop`, then the same "
            "trigger.",
            "Demo: the retry cap.",
            "Starting state: the missing retry cap (`BUG_NO_RETRY_CAP`) switched on. Reset first: "
            "`make reset NAME=verification-loop`.",
            "Do: Verify > Inject failing grader, or `make demo NAME=verify-retry-cap`. Watch the cost "
            "counter for a few attempts, then switch the bug off and inject again.",
            "Narrate: concept 3, stops that are not the model's choice. The injected grader always "
            "fails, so the agent retries forever when nothing counts. With the cap, the run stops after "
            "3 attempts and ends escalated with every reason.",
            "Point at, in order: the attempt counter; the cost counter climbing with the bug on; the "
            "counter flat at 3 with the bug off; the escalated status with the reasons; and last the live "
            "stamp: the run's start time in your local time and its trace link.",
            "Expected live result: the cost counter stops at the cap and the run shows escalated. "
            "Measured with the cap: escalated after 3 attempts, in 79 and 69 seconds. Without the cap "
            "a run goes on until the run guard's 60,000-token budget stops it: measured twice, 9 "
            "attempts, 62,762 and 63,737 tokens, 0.0067 and 0.0069 dollars, in 104 and 111 seconds.",
            "May vary: the cost per attempt and the SQL of each retry. If they do, say: the model writes "
            "a different query each time; the counter does not care.",
            "If it stalls: reset and run it again, `make reset NAME=verification-loop`, then the same "
            "trigger.",
            "Demo: every grader passes, still wrong.",
            "Starting state: knowledge version v1 active, no planted bug on. Reset first: `make reset "
            "NAME=verification-loop`.",
            "Do: Verify > Ask the spine question, or `make demo NAME=verify-graders-pass-still-wrong`.",
            "Narrate: the tempting question from the start of the section. Every deterministic grader "
            "passes. Concept 4, a checker that shares the maker's blind spots: the reviewer reads the "
            "answer and gives its verdict, and the gold check on both databases fails anyway.",
            "Point at, in order: the checklist turning green line by line; the reviewer's verdict "
            "beside it; the failed gold check on both databases; and last the live stamp: the run's start "
            "time in your local time and its trace link.",
            "Expected live result: an all-green checklist beside a failed gold check.",
            "May vary: the reviewer's verdict and the wrong value. In calibration the reviewer raised "
            "a concern on this answer in 6 runs and approved in 1, so expect a concern and a hold for "
            "approval. If the reviewer raises a concern, say: good, and notice it still cannot supply "
            "the fiscal year rule; if it approves, say: same model, same blind spot.",
            "If it stalls: reset and run it again, `make reset NAME=verification-loop`, then the same "
            "trigger. In calibration both attempts passed every grader but got no gold check within 90 "
            "seconds; the gold checks were hardened the same night, and a failing promotion step no "
            "longer stops them. Both retakes were shown: 76,981,355.95 dollars against gold "
            "64,015,091.21, with 4 trap labels each, then held by two reviewer concerns.",
            "Optional, cut first: the cost guard, `make demo NAME=verify-cost-guard` (Verify > Send "
            "cartesian query): with the missing cost guard a cartesian join runs to the statement "
            "timeout; with the cost grader, EXPLAIN rejects it at once with a reason.",
            "Code walkthrough: about 6 minutes, in the editor, in the order of the section's demo "
            "walkthrough page.",
            "Open `platform/src/datapilot/loop2_verification/checker.py`, lines 85-101: the order of the "
            "layers, behind concepts 1, 2, and 3. Say: cheap text checks first, then the cost grader and "
            "the personal data grader, execution last, then the execution grader; the first blocking "
            "grader returns one clear reason; the executor runs the text as written; the cost grader "
            "plans only one read-only SELECT and says not applicable to anything else; and when the "
            "database refuses a write, 25006 or 42501, `checked.refused` marks it so the loop ends the "
            "run escalated with no retry.",
            "Open `platform/src/datapilot/loop2_verification/graders/statement_policy.py`, lines 84-95: "
            "implements concept 1, allowlist the shape, layer two of the malicious SQL demo. Say: the "
            "root check stops anything that is not a read; the walk over every node stops a DELETE "
            "hidden in a common table expression under a SELECT root, which a prefix check passes; with "
            "`BUG_NAIVE_GUARD` on, a `startswith` check replaces this grader. The clock rule sits just "
            "below these lines: agent SQL may not read the database clock.",
            "Open `platform/src/datapilot/loop2_verification/loop.py`, lines 364-369: implements concept "
            "3, stops that are not the model's choice, the retry cap demo. Say: before another attempt, "
            "`attempt_allowed` compares it with the cap of 3; at the cap the run ends escalated with every "
            "reason; just below, the run guard is checked before the feedback goes back, so a kill switch "
            "or a spent budget wins over a retry; with `BUG_NO_RETRY_CAP` on, `attempt_allowed` always "
            "says yes.",
            "Concept 4, the reviewer, has no line range on the walkthrough page. If asked, say: it runs "
            "only after every grader passes, sees only the question, the final SQL, a result preview, "
            "and the knowledge, and can add a concern but never pass a failed grader.",
            "Transition: questions before the break.",
        ],
    ),
    # 10 ----------------------------------------------------------------------------------------
    dict(
        kind="questions",
        title="Questions",
        layout="concept",
        container="key-idea box: fixed question wording, two likely questions",
        minutes=5,
        says="No Question Is Too Small Every Question Deserves an Answer!! Likely: why two databases; can the reviewer be fooled",
        src="-",
        on_slide=[
            "No Question Is Too Small Every Question Deserves an Answer!!",
            "Why two databases? Can the reviewer be fooled?",
        ],
        notes=[
            "Say: take questions; this slot also holds the section's discussion time. Send anything "
            "that needs more than two minutes to the Thursday parking lot.",
            "Point at: the two likely questions on the slide.",
            'Likely question: "Why compare on two databases?" Answer: a wrong query can return the '
            "right number on one database by coincidence; a second database with different rows "
            "exposes it, which is the teaching-sized version of the distilled test suites.",
            'Likely question: "Can a prompt injection fool the reviewer?" Answer: it might, which is '
            "why the reviewer can only add a concern and never pass a failed grader.",
            'Likely question: "Where would you put a personal-data check?" Answer: as a grader that '
            "routes the run to human approval instead of blocking it; Section 3: Event loop makes that "
            "approval survive a restart.",
            'Likely question: "What does the agent do with a term no rule defines, such as loyal '
            'customers?" Answer: in calibration it guessed with a stated reading in 5 of 8 runs, and '
            "the reviewer turned most guesses into a held or escalated answer. With the reviewer off "
            "the guess posts unflagged, which is why Assignment 2: Verification loop adds a "
            "clarify-or-abstain grader.",
            "Transition: if time is short, skip the reference slides and go to the break.",
        ],
    ),
    # 11 ----------------------------------------------------------------------------------------
    dict(
        kind="reference",
        title="Reference: skip if short on time - attack patterns",
        layout="table",
        container="two tables: pattern | example | defense, with a how-to-read bar",
        minutes=1,
        allow_example=True,
        says="Seven attack patterns a syntax-tree guard must handle, and the defense for each",
        src="measured for the course (sqlglot guard)",
        on_slide=[
            "How to read this: each row is a shape that passes a first-word or root-only check; the last column is the defense that stops it.",
            "Shapes that hide a write:",
            "| Pattern | Example | Defense |",
            "|---|---|---|",
            "| Stacked statements | SELECT 1; DELETE FROM orders | Exactly one statement |",
            "| Write inside a CTE | WITH d AS (DELETE ...) SELECT ... | Walk every node |",
            "| Hidden write or lock | SELECT ... INTO, FOR UPDATE | Reject INTO and lock nodes |",
            "| Unparsed statement | DO, CALL, VACUUM | Reject opaque commands |",
            "Shapes the parser misreads or cannot see:",
            "| Pattern | Example | Defense |",
            "|---|---|---|",
            "| Misparse | TABLE orders | Root allowlist |",
            "| SQL in a string | dblink, query_to_xml | Function denylist, then grants |",
            "| Lossy regeneration | COPY ... TO PROGRAM | Run the original text |",
        ],
        notes=[
            "Plain explanation: these are the shapes that get past a guard that only looks at the "
            "first word or the root node. Each row pairs a pattern with the specific defense that "
            "stops it.",
            "Concrete example from DataPilot: the malicious SQL demo sends the first two rows; the "
            "guard's tests cover every row, and the security suite asserts that no warehouse row "
            "changes.",
            "Analogy: a customs officer who checks the label on a box and never opens it.",
            "Under the hood: parsed in the Postgres dialect, the stacked string is two statements; the "
            "CTE has a Select root with a Delete inside; SELECT INTO is an Into node and FOR UPDATE a "
            "Lock node; DO, CALL, VACUUM, EXPLAIN ANALYZE, PREPARE and EXECUTE become an opaque Command; "
            "`LISTEN foo` and `TABLE orders` misparse as aliases; `dblink` and `query_to_xml` carry SQL in "
            "string literals; and `COPY ... TO PROGRAM` came out mangled when regenerated from the tree.",
            S7
            + ", in summary: the tutorial's checker is an LLM, which reads these patterns as text "
            "and can be persuaded.",
            "Transfer: keep a table like this for any language your agent emits, with one test per "
            "row, and add a row each time a parser surprises you.",
            "Point at: the Defense column; no row relies on the prompt.",
            "Ask: \"Which row is the grant's job, not the guard's?\" Expected: SQL in a string.",
            'Likely question: "Is a new parser version a risk?" Answer: yes; pin it, and keep these '
            "tests so an upgrade that changes a node type fails continuous integration.",
            'Likely question: "Why reject FOR UPDATE in a read-only tool?" Answer: it takes row locks '
            "that can block writers elsewhere, a side effect without a write.",
            "Misconception: if it parses, it is safe. Correction: three rows here parse without error.",
            "Transition: next reference slide.",
        ],
    ),
    # 12 ----------------------------------------------------------------------------------------
    dict(
        kind="reference",
        title="Reference: skip if short on time - database errors as feedback",
        layout="table",
        container="table: SQLSTATE | meaning | feedback to the agent | then, with a how-to-read bar",
        minutes=1,
        says="Map each database error to feedback the agent can act on, and to retry or stop",
        src="Source 10 (PostgreSQL error codes)",
        on_slide=[
            "How to read this: a fixable error becomes a reason the agent can act on, counted against the cap of 3; a refused write ends the run.",
            "| SQLSTATE | Meaning | Feedback to the agent | Then |",
            "|---|---|---|---|",
            "| 42601 | Syntax error | Send one valid SELECT statement | Retry, counted |",
            "| 42P01, 42703 | Unknown table or column | Look up the real names with the schema tools | Retry, counted |",
            "| 57014 | Statement timeout | Add filters or aggregate before returning | Retry, counted |",
            "| 25006 | Write in a read-only transaction | Write blocked: only SELECT queries can run | Run ends, escalated |",
            "| 42501 | Privilege refused | The role can only read the allowed schema | Run ends, escalated |",
        ],
        notes=[
            "Plain explanation: a raw database error is feedback written for a person at a terminal. "
            "Translate each fixable class of error into a short reason the agent can act on, and "
            "count every retry against the cap, so a run that keeps failing ends escalated for a "
            "person to read. A refused write is different: it is an incident, so the run stops at once.",
            "Concrete example from DataPilot: the executor maps each SQLSTATE to one sentence of "
            "feedback. A misspelled column comes back as a pointer to the schema tools, and the next "
            "attempt usually fixes it. A refused write, SQLSTATE 25006 or 42501, is never fed back as a "
            "retry: the run ends escalated at once, with the reason write blocked, only SELECT "
            "queries can run, for a person to read.",
            "Analogy: a compiler error message that points at the line, versus one that says failure.",
            "Under the hood: the condition names in the PostgreSQL appendix are `syntax_error` for "
            "42601, `undefined_table` for 42P01, `undefined_column` for 42703, `query_canceled` for "
            "57014, `read_only_sql_transaction` for 25006, and `insufficient_privilege` for 42501. The "
            "feedback strings are short and carry no data from the error text.",
            S10 + ': "read_only_sql_transaction" is the listed condition name for 25006, and '
            '"insufficient_privilege" for 42501.',
            "Transfer: for any tool an agent calls, classify its errors before launch, write the "
            "feedback text for each class, and decide which ones the agent may retry. Anything that "
            "signals an attempt to cross a boundary, such as a refused write, is an incident: stop "
            "the run at once instead of handing it back to the model.",
            "Point at: the Then column: the top three rows retry against the cap; the last two end the run.",
            'Ask: "Why does a refused write not get a retry?" Expected: it is an incident, not a '
            "mistake to fix; a retry would invite the model to try another way across the boundary.",
            'Likely question: "Should the agent see the full error text?" Answer: a trimmed message '
            "is better; full text can carry data back into the context.",
            'Likely question: "What about connection errors?" Answer: those are infrastructure, so '
            "retry with backoff outside the agent loop, not as agent attempts.",
            "Misconception: more error detail always helps the agent. Correction: one actionable "
            "sentence per error class beats a stack trace.",
            "Transition: last reference slide.",
        ],
    ),
    # 13 ----------------------------------------------------------------------------------------
    dict(
        kind="reference",
        title="Reference: skip if short on time - why one database lies",
        layout="diagram",
        container="two-column cards: the two-database example | the false-positive table, with a how-to-read bar",
        minutes=1,
        says="A wrong query can match on one database by coincidence; distinguishing rows expose it",
        src="Source 8 (test-suite accuracy)",
        on_slide=[
            "How to read this: a result match is only as strong as the rows it runs on; the table gives the measured size of the gap.",
            "Gold: net revenue without cancelled orders. Wrong: net revenue with them.",
            "Database A has no cancelled orders: both queries match.",
            "Database B has some: only gold matches.",
            "| Measure | Value |",
            "|---|---|",
            "| False positives, one database | 6.5 percent mean |",
            "| On extra-hard queries | 11.0 percent |",
            "| Fuzzed databases kept per query | About 42 |",
        ],
        notes=[
            "Plain explanation: a result match is only as strong as the data it runs on. If the rows "
            "that would separate the right query from the wrong one are absent, both return the same "
            "answer and the wrong one passes.",
            "Concrete example from DataPilot: the seed data carries the rows each trap needs: cancelled "
            "orders, internal accounts among the top spenders, and orders placed in the evening Eastern "
            "time that cross the UTC date. Gold answers are checked on two databases, the warehouse and "
            "an alternate copy.",
            "Analogy: a test suite whose inputs never hit the branch you changed.",
            "Under the hood: across 21 Spider submissions, matching on the original database gave a 6.5 "
            "percent mean false-positive rate and 11.0 percent on extra-hard queries. The fix fuzzes "
            "about 1,000 random databases per schema and keeps those that separate neighbour queries, "
            "where one constant, operator, or clause differs: about 42 per query.",
            S8 + ': "In contrast, the current Spider metric leads to a 2.5% false negative rate on '
            'average and 8.1% in the worst case."',
            "Transfer: when you evaluate any agent by its outputs, seed the inputs that separate right "
            "from plausible: the edge rows, the boundary dates, the excluded categories.",
            "Point at: database A, where the wrong query passes.",
            'Ask: "What row would you add to database A?" Expected: one cancelled order.',
            'Likely question: "Why only two databases?" Answer: it is the teaching-sized version; two '
            "with designed rows catch the traps we planted, and the paper shows what scale buys.",
            'Likely question: "Does a second database slow evaluation?" Answer: every item runs its '
            "SQL twice, which is database time, not model tokens.",
            "Misconception: execution match is the ground truth. Correction: it is an upper bound unless "
            "the data distinguishes the queries.",
            "Transition: time for a break.",
        ],
    ),
]
