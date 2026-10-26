"""Section 1: Agent loop, 0:25 to 1:03, 38 minutes, 13 slides, under the design system.

The slide schema is in slides/design-system.md; slides/source/samples.py is its worked example.
Every course number comes from the deck evidence list (entries E1 and on, named in each slide's
src), every external figure from the verified source list, cited on a slide as [^n] with the
source's number there. The arc of the owner's specification, section 1: the opening insight, the
problem as a story, the concept, the mechanism, the live demo, the evidence, the text-to-SQL design
callout, applying it, the pitfalls, and a recap with one question.
"""

RULES = "design system"

DEMO_PAGE = "https://github.com/ANI-IN/loop-engineering/tree/main/section-1-agent-loop/demo"
EXPECTED = "section-1-agent-loop/demo/expected/"

SLIDES = [
    # 1 section opener --------------------------------------------------------------------------
    dict(
        kind="opener",
        title="Section 1: Agent loop",
        minutes=1,
        says="The agent loop fixes an agent that sees too little to be right, or too much to "
        "stay in budget",
        src="section-1-agent-loop/README.md",
        on_slide=[
            "Fixes: an agent that sees too little to be right, or receives too much to stay "
            "inside its budget",
            "Insight: What the tools show decides the answer: fuller tool output lifted easy runs "
            "from 12 to 17 of 21.",
        ],
        notes=[
            "Purpose: Open Section 1 and name the two failures the agent loop is designed against.",
            "What to say: Section 1 is the agent loop: one analyst agent, its tools, and the "
            "hard stops on every run. We skip the basics and spend the time on two design "
            "questions. What do the tools let the agent see? And how much do they hand back? "
            "Too little, and it guesses. Too much, and one result blows the budget.",
            "The point to land: The agent can only be as good as what its tools show and return.",
            "Example: The describe tool decides whether a status column looks like a number or "
            "like a handful of codes.",
            'Ask the room: "What does your agent see of your warehouse today: names, types, or '
            'sample rows?" Expect: names and types; sample rows are rare.',
            "Misconceptions: That the agent loop is the easy part. Its tools and its answer "
            "shape decide what the next three loops can check.",
            "Transition: First, the lesson this section proves, with its evidence.",
        ],
    ),
    # 2 insight: the opening insight ------------------------------------------------------------
    dict(
        kind="insight",
        title="What the tools show decides the answer",
        minutes=1.5,
        says="Fuller tool output lifted easy answers from 12 to 17 of 21; no tool shows a "
        "business rule",
        src="E15 (docs/benefits.md, Section 1: Agent loop); E7 (docs/calibration-report.md, "
        "Traps); deck sources [18] LinkAlign, Appendix B",
        on_slide=[
            "Insight: An agent is only as right as what its tools let it see; fix the view "
            "before the prompt.",
            "Evidence: Fuller tool output lifted easy runs from 12 to 17 of 21.",
            "- Spider, 500 questions, every schema pooled: 68.3 percent of failures were "
            "schema linking[^18]",
            "- No tool shows a business rule: 0 of 99 trap-question runs passed",
        ],
        notes=[
            "Purpose: Land the section's opening insight: what the tools show decides the "
            "answer, and no tool can show a rule that lives in people's heads.",
            "What to say: Here is the lesson of this section before we prove it. An agent "
            "answers from what its tools show it, nothing else. Our own measurement first. On 24 "
            "October, seven easy questions, three times each: with column names only, unbounded "
            "rows, and no scout, 12 of 21 runs were correct; with full descriptions, capped "
            "rows, and the scout, 17 of 21. Research points the same way: LinkAlign pooled the "
            "schemas of every Spider database on purpose, and 68.3 percent of the failures in "
            "its 500 questions were schema-linking errors, the step that maps a question's words "
            "onto tables and columns, Source 18. The last bullet is the limit. Under the "
            "starting knowledge, 33 trap questions ran three times each with every tool on, and "
            "0 of 99 runs passed. No column carries the fiscal year or the internal accounts. So "
            "this section fixes what the agent can see; Section 4 adds the rules it cannot.",
            "The point to land: Fix what the agent can see before you tune what it says.",
            "Example: With names only, the order status is just a small number; with its "
            "distinct values shown, the agent sees a short list of codes and can ask what they "
            "mean.",
            'Ask the room: "When your agent got a query wrong last, was it the reasoning or '
            'what it could see?" Expect: most say reasoning at first, then admit it picked the '
            "wrong column.",
            'Misconceptions: "A stronger model fixes linking." A stronger model reads the same '
            "tool output; if a code or a rule is not there, it guesses.",
            "Transition: Now the other side: what happens when a tool returns too much.",
        ],
    ),
    # 3 problem story ---------------------------------------------------------------------------
    dict(
        kind="story",
        title="One tool result used three run budgets",
        minutes=2,
        says="With the row cap removed, one 10,000-row result took a run to 184,983 tokens",
        src="E16, E17 (docs/evidence/section-1-agent-loop.md, Results; docs/costs.md, "
        "Commands); capture run 199d2188, 25 October 2026, "
        "section-1-agent-loop/demo/expected/agent-unbounded-rows-planted-tokens.png",
        image={
            "path": EXPECTED + "agent-unbounded-rows-planted-tokens.png",
            "alt": "The foot of the Agent page after the large query with the unbounded rows "
            "bug on: the live stamp, started 14:53:33, trace not received at the LangSmith "
            "monthly limit, run 199d2188; under it, 184,983 tokens, 0.0230 dollars, 7.5 seconds",
            "crop": (0.06, 0.81, 0.445, 0.08),
            "callouts": [(0.965, 0.23, 1), (0.46, 0.77, 2)],
        },
        on_slide=[
            '"List the ten most recent orders after a 10,000-row query"',
            "1. Run 199d2188: all 10,000 rows went back to the model",
            "2. 184,983 tokens, escalated: over three 60,000-token budgets",
            "Footer: Six runs with the row cap removed: 182,654 to 187,030 tokens each",
        ],
        notes=[
            "Purpose: Show, from a real run, that one oversized tool result breaks a run that a "
            "prompt and a budget were supposed to protect.",
            "What to say: This is a real run from 25 October, with one planted bug switched "
            "on: the row cap in the query tool removed. The request asked for ten thousand rows "
            "on purpose: select star from order items, limit ten thousand, then list the ten "
            "most recent orders. In your system the trigger is any query that is not "
            "aggregated on a big table. Marker one, beside the run id on its live stamp: the grey text there only says "
            "LangSmith refused the trace at its monthly limit; the run itself is complete. "
            "The query ran fine, and every row went back to the model as the tool's result. Marker two, the counter "
            "under it: the run ended escalated at 184,983 tokens, against a 60,000-token "
            "budget. How? The budget is checked before each model call. The call that carried "
            "the rows started under budget, and that single call overshot; the next check "
            "stopped the run. Six runs with the cap removed went the same way: 182,654 to "
            "187,030 tokens each, every one escalated. At two cents a run, the bill is not the "
            "danger. The context is: every later call carries those rows, and a bigger result "
            "was refused outright by the provider. A budget checked between calls cannot bound "
            "what one call carries. Only the tool can.",
            "The point to land: A run budget limits how many calls you make; only the tool "
            "limits how much one call carries.",
            "Example: Earlier, a query for every order item, 1,020,321 rows and about 32.6 "
            "million characters, was refused by the model provider outright: the request was "
            "longer than its limit of 10,485,760 characters.",
            'Ask the room: "Which of your tools could return ten thousand of anything?" Expect: '
            "search, logs, query tools, file listings.",
            'Misconceptions: "A larger context window solves this." It postpones it: every '
            "token is sent again and paid for on every later call in the run.",
            "Transition: To see where the cap belongs, here is the whole loop on one page.",
        ],
    ),
    # 4 concept diagram -------------------------------------------------------------------------
    dict(
        kind="concept",
        title="The agent loop: one analyst, four tools, hard stops",
        minutes=2,
        says="The analyst sees the warehouse only through its tools, inside stops on every run",
        src="section-1-agent-loop/diagrams/agent-loop.png; section-1-agent-loop/README.md; E18 "
        "(pack.yaml limits and budgets)",
        figure={
            "diagram": "agent-loop",
            "alt": "A question goes to the analyst agent. Its prompt on every model call holds "
            "the business date and the active knowledge version. Its tools are list_tables, "
            "describe_table, run_query, and scout_schema; run_query goes through the checker, "
            "graders then the read-only executor, and returns at most 50 rows and the total "
            "count. scout_schema starts the schema scout agent, whose tool boundary holds "
            "list_tables and describe_table and no run_query. The run ends in an answer "
            "envelope: status, query, rows, answer, assumptions. Stops every run: 12 model "
            "calls, 16 tool calls, 60,000 tokens.",
        },
        on_slide=[],
        notes=[
            "Purpose: Give the mental model of the agent loop in one picture before any code.",
            "What to say: The idea on this slide: The agent sees the warehouse only through its tools, inside stops it cannot talk past. "
            "Let me walk the diagram from left to right. A question arrives, in the "
            "dashed box on the left. It goes to the analyst agent, the large oval. Above it is "
            "the prompt, rewritten on every model call: the business date, 31 January 2026, and "
            "the active version of the business knowledge, which starts almost empty. To the right are the "
            "analyst's four tools. list_tables and describe_table show the schema. run_query "
            "never touches the database itself: it hands the query to the checker, the graders "
            "and then a read-only executor, and at most 50 rows come back with the total count. "
            "scout_schema starts a second agent, the schema scout, in the dashed boundary at the "
            "bottom right. The scout can read the catalog but has no run_query, and it keeps no "
            "memory between questions. Bottom left are the stops of every run: 12 model calls, "
            "16 tool calls, 60,000 tokens. They sit in middleware and settings, not in the "
            "prompt. Bottom centre is what comes back: an answer envelope with a status, the "
            "query, the rows, the answer, and the assumptions. Every later loop checks, routes, "
            "or learns from that envelope.",
            "The point to land: Design the tools, the stops, and the answer shape first; the "
            "prompt comes last.",
            "Example: In the confident wrong answer you will see live, the scout took 11.1 of "
            "the 20.3 seconds of tool time.",
            'Ask the room: "Which of these three stops does your agent have?" Expect: a '
            "timeout, sometimes a step limit, rarely a token budget.",
            "Misconceptions: That stops belong in the prompt. A prompt asks the model; "
            "middleware ends the run whatever the model wants.",
            "Transition: Start with the tool that decides what the agent sees: describe_table.",
        ],
    ),
    # 5 mechanism: schema exposure --------------------------------------------------------------
    dict(
        kind="mechanism",
        title="What describe_table shows the agent",
        minutes=2,
        says="Types, comments, three sample rows, and the distinct values of small columns",
        src="platform/src/datapilot/loop1_agent/tools.py lines 100-118; E15; LangChain's "
        "community SQLDatabase utility (langchain_community/utilities/sql_database.py, read on "
        "26 October 2026: sample_rows_in_table_info=3, max_string_length=300, and run fetches "
        "every row)",
        code={
            "language": "python",
            "origin": "platform/src/datapilot/loop1_agent/tools.py lines 100-118, inside the "
            "method Warehouse.describe_table, shown two indentation levels out (lines 102-115 "
            "left out, and the comment of line 101)",
            "lines": [
                'if planted("BUG_NAMES_ONLY_SCHEMA"):',
                "    return f\"{table.name}: {', '.join(table.column_names)}\"",
                "...",
                '    "columns": columns,',
                '    "sample_rows": sample_rows(self.url, table, schema),',
                '    "distinct_values": few_distinct_values(self.url, table, schema),',
            ],
            "marks": [
                (1, "table.column_names", 1),
                (3, '"columns": columns', 2),
                (4, "sample_rows(self.url, table, schema)", 3),
                (5, "few_distinct_values(self.url, table, schema)", 4),
            ],
        },
        on_slide=[
            "Idea: schema linking succeeds or fails in this tool",
            "1. Planted bug: names only",
            "2. Types, nullability, neutral comments",
            "3. Three sample rows, for formats",
            "4. Distinct values of small columns",
        ],
        notes=[
            "Purpose: Show the real tool that decides what the agent knows about a table, and "
            "the trade-off behind each field.",
            "What to say: This is the describe tool, the agent's only window onto a table. "
            "Marker one is a planted bug we use for measurement: with it on, the tool returns "
            "column names only, the setup that scored 12 of 21 in the paired measurement. Marker two is the "
            "normal path: each column with its type, whether it can be empty, and a neutral "
            "comment, one that describes storage and never a business rule. Marker three: three "
            "sample rows, which teach formats such as money in cents. They also carry risk: a "
            "few product names in our warehouse hold prompt-injection text, so the real "
            "boundary sits below the model, in the read-only role of Section 2. If you use "
            "LangChain's community SQL toolkit, its database utility already gives you the "
            "table definition and three sample rows by default, Source 54. What DataPilot adds is marker "
            "four: the distinct values of columns that have only a few. That turns a status "
            "column from a mystery number into a short list of codes the agent can reason "
            "about or ask about. Every field costs tokens on every describe call, so keep what "
            "helps linking and nothing else.",
            "The point to land: Tool output design is schema-linking design.",
            "Example: The agent's query in the confident wrong answer used status 4, so the "
            "cancelled orders, status 5, stayed out: the codes were visible even though their "
            "meaning was not.",
            'Ask the room: Only if ahead of the clock: "Would you drop sample rows to stop injection?" Expect: some say '
            "yes; the better answer is keep them small and block writes below the model.",
            "Misconceptions: That hiding data from the model makes it safe. Safety comes from "
            "what the model is allowed to do, not from what it may see.",
            "Transition: Showing enough is half the tool. The other half is returning no more "
            "than enough.",
        ],
    ),
    # 6 mechanism: the caps in the tool ---------------------------------------------------------
    dict(
        kind="mechanism",
        title="Cap rows and values in the tool, not the prompt",
        minutes=2,
        says="The query tool returns at most 50 rows, values cut at 2,000 characters, the total "
        "count, and a notice",
        src="platform/src/datapilot/loop1_agent/tools.py lines 39-48; E16, E18, E37; deck "
        "sources [4]; LangChain's community SQLDatabase utility (max_string_length=300; run "
        "fetches every row), read on 26 October 2026",
        code={
            "language": "python",
            "origin": "platform/src/datapilot/loop1_agent/tools.py lines 39-48 (lines 43-44 "
            "and 46-47 left out)",
            "lines": [
                "def format_result(result: QueryResult, row_cap: int) -> str:",
                "    rows, truncated = cap_rows(list(result.rows), row_cap)",
                "    rows, values_cut = cap_values(rows)",
                "    payload: dict[str, Any] = {",
                "    ...",
                '        "total_row_count": result.total_row_count,',
                "    ...",
                '    notices = [f"Showing {len(rows)} of {result.total_row_count} rows."] if '
                "truncated else []",
            ],
            "marks": [
                (1, "cap_rows(list(result.rows), row_cap)", 1),
                (2, "cap_values(rows)", 2),
                (5, '"total_row_count": result.total_row_count', 3),
                (7, "notices", 4),
            ],
        },
        on_slide=[
            "Idea: the tool decides how much reaches the model[^4]",
            "1. 50 rows: 30,216 tokens, not 182,654",
            "2. Each value cut at 2,000 characters",
            "3. The total count still goes back",
            "4. A notice says rows were cut",
        ],
        notes=[
            "Purpose: Show the real code that bounds every query result, and why each of its "
            "four parts is needed.",
            "What to say: Every query result passes through this function before the model "
            "sees it. Marker one: the rows are cut to the row cap, 50, set in the pack's "
            "settings. In the paired run of 24 October the large query used 30,216 tokens with "
            "the cap and 182,654 without it, the reviewer's round trip included. We did not "
            "test a limit written only in the prompt; LangChain's SQL agent tutorial limits "
            "results that way, Source 5. "
            "Marker two: each value is cut at 2,000 characters. LangChain's SQL database "
            "utility also cuts values, at 300 characters, but it returns every row a query "
            "fetches, Source 54. Marker three: the total row count still goes "
            "back, so the agent knows what it did not see. Without the count, 50 rows look like "
            "the whole answer. Marker four: when rows were cut, a notice says so and tells the "
            "agent not to combine rows into one value to see more; the count tells it to "
            "filter or aggregate instead. Anthropic's guidance on writing tools says the same: truncate responses "
            "that could use up the context, and steer the agent with the message, Source 4. The "
            "trade-off: a cap can hide rows a question needs, which is why the count and the "
            "notice travel with it.",
            "The point to land: A cap in the tool holds whatever the model asks for.",
            "Example: With the cap removed, the story's run used 184,983 tokens and ended "
            "escalated.",
            'Ask the room: Only if ahead of the clock: "What should the agent do when it sees '
            'the notice?" Expect: '
            "aggregate in the query, or narrow the question.",
            "Misconceptions: That a row cap bounds size. It bounds rows; one row can hold "
            "anything, such as the 5,261 email addresses of Section 3, so cap the values too.",
            "Transition: The tools are bounded. Now the agent around them: its stops and its "
            "answer.",
        ],
    ),
    # 7 mechanism: the analyst, the stops, the envelope -----------------------------------------
    dict(
        kind="mechanism",
        title="The analyst: knowledge, stops, and the answer envelope",
        minutes=2.5,
        says="One create_agent call: knowledge on every call, call limits as middleware, a typed "
        "envelope as the answer",
        src="platform/src/datapilot/loop1_agent/analyst.py lines 72-86; "
        "platform/src/datapilot/contracts/answer.py lines 11-28; E18, E19, E20",
        code={
            "language": "python",
            "origin": "platform/src/datapilot/loop1_agent/analyst.py lines 76-83, inside the "
            "create_agent call of lines 72-86, shown two indentation levels out; the envelope's "
            "fields are in platform/src/datapilot/contracts/answer.py lines 21-28",
            "lines": [
                "middleware=[",
                "    knowledge_prompt(prompts.ANALYST, knowledge),",
                "    *middleware,",
                "    ModelCallLimitMiddleware(run_limit=limits.model_call_limit, "
                'exit_behavior="end"),',
                '    # "end" works only for a single tool; "continue" answers extra calls with an '
                "error.",
                "    ToolCallLimitMiddleware(run_limit=limits.tool_call_limit, "
                'exit_behavior="continue"),',
                "],",
                "response_format=ToolStrategy(AnswerEnvelope),",
            ],
            "marks": [
                (1, "knowledge_prompt(prompts.ANALYST, knowledge)", 1),
                (3, "ModelCallLimitMiddleware", 2),
                (5, "ToolCallLimitMiddleware", 2),
                (7, "ToolStrategy", 3),
                (7, "AnswerEnvelope", 4),
            ],
        },
        on_slide=[
            "Idea: the stops and the answer shape live in code",
            "1. Knowledge on every call",
            "2. 12 model calls, 16 tool calls",
            "3. The answer must validate",
            "4. Status, query, assumptions",
        ],
        notes=[
            "Purpose: Show how the analyst is assembled: where knowledge enters, where the "
            "stops live, and the answer shape every later loop reads.",
            "What to say: The analyst is one create_agent call from LangChain; these are its "
            "middleware and its answer format. Marker one: a middleware rewrites the system "
            "prompt before every model call with the business date and the active knowledge "
            "version. A new version of the rules changes this block and nothing else, and every "
            "run records which version it used. The line under it, star middleware, is where "
            "the 60,000-token budget per run plugs in, and where later sections add the kill "
            "switch and approvals. Marker two: the call limits, read from the pack's settings. "
            "The model call limit ends the run at 12 calls. The tool call limit, as the comment "
            "says, answers extra calls with an error at 16, so the model can still answer. "
            "Marker three: the answer must validate as an envelope, or the validation error "
            "goes back to the model to fix, inside the same limits. Marker four: the envelope "
            "itself carries a status, the final query, the rows, and the assumptions. The "
            "status has four values: answered, needs clarification, refused, escalated, so not "
            "answering is a legal outcome code can route. The assumptions carry a rule from "
            "calibration: answer with stated assumptions, and ask when a term has no rule and "
            "nothing in the schema defines it. Early on, the fiscal year 2025 revenue question "
            "came back as a clarifying question, which left the reviewer and the gold check "
            "nothing to check.",
            "The point to land: Put the stops in middleware and the answer in a typed envelope; "
            "then every later loop has something to check.",
            'Example: Asked "How many VIP customers do we have?" and "What was revenue for our '
            'loyal customers last month?", the analyst ended with needs clarification on both '
            "questions, one run each: no column and no rule defines either term.",
            "Ask the room: Only if ahead of the clock: \"Where does your agent's step limit "
            'live?" Expect: in the framework '
            "default, or in the prompt.",
            "Misconceptions: That a valid envelope is a correct answer. It is a checkable one; "
            "Section 2 does the checking.",
            "Transition: Enough code. Let us run the loop live.",
        ],
    ),
    # 8 demo ------------------------------------------------------------------------------------
    dict(
        kind="demo",
        title="Live: the agent loop, right, wrong, and unbounded",
        minutes=16,
        says="The simple question, the confident wrong answer, and unbounded rows, live; then "
        "the code",
        src="platform/demos/registry.yaml (section agent-loop); "
        "section-1-agent-loop/demo/README.md; section-1-agent-loop/demo/walkthrough.md; E3, "
        "E13, E16, E22, E26",
        on_slide=[
            "Badge: DEMO - 1",
            "What to watch for:",
            "- Simple: each tool call, then an envelope",
            "- Wrong answer: fluent, then a gold mismatch",
            "- Unbounded rows: tokens, cap off then on",
            "Guaranteed moment: a confident, wrong fiscal year 2025 revenue answer, each trap "
            "named on its query.",
            "Link: Demo page on GitHub | " + DEMO_PAGE,
        ],
        notes=[
            "Purpose: Run the agent loop live: one correct answer, one confident wrong answer "
            "only the gold check exposes, and the row cap off and on.",
            "What to say: Let's watch the agent loop answer, get it wrong, and blow its budget, "
            "live. Nothing here is recorded and nothing is scripted: each run calls the class "
            "model, and the model chooses its own tools. First a simple question, so you see the "
            "loop work end to end. Then the fiscal year 2025 revenue question from the opening: "
            "this time you watch the agent loop produce that wrong number, tool by tool. Then "
            "the row cap, off and then on, so the story's token counter happens in front of you. "
            "Watch three things: the tool timeline, the gold check, and the token counter. When "
            "each result lands I will read its numbers aloud and show its live stamp, the start "
            "time and the trace link, so you know it ran just now. After the demos, three "
            "minutes in the editor on the same code you saw on the slides.",
            "Demo: The simple question.",
            "Command: 0:38 to 0:41. First check the status line: the report-only level, the "
            'kill switch released, and Planted None: the fixed system. Then type "How many '
            'orders have been placed in total?" in the console and press Agent > Ask; or, in '
            "the demo terminal, make demo NAME=agent-simple-question, which sends the same "
            "question.",
            "Point at: first the tool timeline as each call appears, list_tables, "
            "describe_table, run_query, with its duration; then the one-line count query and "
            "the envelope's status; then the tokens and cost; last the live stamp.",
            "Expected output: Posted, 405,738 orders, one count query, about 5,100 tokens and "
            "0.0005 dollars; 14 to 39 seconds in the recorded runs.",
            "While it runs: 14 to 39 seconds of the 3-minute slot. Say that nothing is "
            "scripted: the model chose these tools itself, and the path can differ run to run; "
            "the envelope and its query are what we check.",
            "If it fails: 1. Read the status aloud; a run that answers correctly with more tool "
            "calls is not a failure. 2. If it stays queued or stalls, run make reset "
            "NAME=agent-loop in the demo terminal (about 7 seconds). 3. Press Agent > Ask again "
            "with the same question. 4. A missing trace link is not a failure: say LangSmith "
            "may be refusing traces and point at the run id. Cutoff for every demo of this "
            "slide: a retry that would end after 0:53 takes the code walkthrough's time; after "
            "0:54, skip it and name it for the Thursday review.",
            "Backup screenshot: "
            + EXPECTED
            + "agent-simple-question-answer.png, the posted count with its three tool calls; "
            "show it only while the reset runs, never instead of the run.",
            "Demo: The confident wrong answer.",
            "Command: 0:41 to 0:46. Press Agent > Ask the spine question in the console, the "
            "button for the fiscal year 2025 revenue question; or make demo "
            "NAME=agent-confident-wrong-answer.",
            "Point at: first the answer text, which states its own assumption, calendar year "
            "2025 in Coordinated Universal Time; then the answer-versus-gold ledger with the "
            "mismatch on both databases; then the annotated query, each mark and its trap note; "
            "last the live stamp.",
            "Expected output: a mismatch against the gold answer, 64,015,091.21 dollars, with "
            "one or more trap notes; the recorded runs answered 72,394,572.08 with three trap "
            "notes, or 76,981,355.95; usually held for approval by a reviewer concern; 35 to 76 "
            "seconds.",
            "While it runs: 35 to 76 seconds of the 5-minute slot. Ask the room to predict "
            "which of the five traps the query will hit, and to write it in the chat. If the "
            "strip shows holding for approval, say that is the reviewer of Section 2 doubting "
            "the fiscal year; leave it held, the gold check still shows.",
            "If it fails: 1. If the answer is held, do nothing: the gold check still appears. "
            "2. If no number comes back, there is no gold check: run make reset NAME=agent-loop "
            "(about 7 seconds). 3. Press Agent > Ask the spine question (the console's button "
            "for the fiscal year 2025 revenue question) again. 4. If it comes back correct, say "
            "so: the gold check, not the wording, is the verdict, and one run is one run. The "
            "slide's cutoff applies: after 0:54, no retry.",
            "Backup screenshot: "
            + EXPECTED
            + "agent-confident-wrong-answer-sql.png, the query with its three trap marks and "
            "the mismatch; show it only while the reset runs, never instead of the run.",
            "Demo: Unbounded rows.",
            "Command: 0:46 to 0:50. First, in the demo terminal, make demo "
            "NAME=agent-unbounded-rows PLANTED=1, the bug on for that run only; then press "
            "Agent > Run large query in the console, or make demo NAME=agent-unbounded-rows, "
            "with it off.",
            "Point at: the token counter of the planted run and its escalated status; then the "
            "same counter on the fixed run; then the notice, Showing 50 of 10000 rows, and the "
            "total count under the rows; last the live stamp of each. Then, 0:50 to 0:53, in "
            "the editor, the code in the walkthrough page's order: "
            "platform/src/datapilot/loop1_agent/analyst.py lines 56-58, the knowledge "
            "injection; analyst.py lines 72-86, the stops and the envelope; "
            "platform/src/datapilot/loop1_agent/tools.py lines 33-54, the cap and its planted "
            "branch. Short of time, open tools.py only; never cut a core demo for the code.",
            "Expected output: with the bug on, 182,654 to 187,030 tokens, escalated at the run "
            "budget, in about 12 seconds; with it off, 17,298 to 30,216 tokens in 26 to 48 "
            "seconds, sometimes held by a reviewer concern.",
            "While it runs: two runs inside the 4-minute slot. During the planted run, say the "
            "budget is checked before each call, so one call can overshoot it; during the fixed "
            "run, point back at the cap on slide 19, Cap rows and values in the tool.",
            "If it fails: 1. If the counter does not jump, the run went without the flag: "
            "repeat make demo NAME=agent-unbounded-rows PLANTED=1. 2. If the fixed run holds "
            "for approval, leave it: the token counter is the moment. 3. Anything else: make "
            "reset NAME=agent-loop (about 7 seconds), then the same trigger. After 0:54, no "
            "retry.",
            "Backup screenshot: "
            + EXPECTED
            + "agent-unbounded-rows-planted-tokens.png and agent-unbounded-rows-fixed-tokens.png "
            "in the same folder, 184,983 against 28,468 tokens; show them only while the reset "
            "runs, never instead of the run.",
            "Demo: Texas last quarter.",
            "Command: optional, cut first, only inside the 1-minute buffer, 0:53 to 0:54, when "
            "the core demos finished early: press Agent > Ask with the Texas question, or make "
            "demo NAME=agent-texas-last-quarter.",
            "Point at: the join path in the query, four tables, and the date range: August to "
            "October 2025 is the last completed fiscal quarter against the business date of "
            "31 January 2026.",
            "Expected output: an answer whose query joins four tables; no benchmark question "
            "asks this question, so no gold check; the date range shows whether the "
            "fiscal-quarter trap was hit.",
            "While it runs: inside the 1-minute buffer. Say last completed fiscal quarter: on "
            "31 January the current fiscal quarter is still open.",
            "If it fails: drop it; it is optional, and no reset is spent on it.",
            "Backup screenshot: none is captured for this optional demo; cut it rather than "
            "describe it.",
            "The point to land: A clean run and a correct answer are different things; only the "
            "gold check told them apart.",
            "Example: Run 9182df01 answered 72,394,572.08 dollars for calendar year 2025 in "
            "Coordinated Universal Time, with the internal accounts kept.",
            'Ask the room: "What in the envelope would let a reviewer catch this?" Expect: the '
            "query and the stated assumption.",
            "Misconceptions: That the demo is rigged to fail. The model chose every query; the "
            "rules are simply not in the data.",
            "Transition: One run is a story. Here is the measurement.",
        ],
    ),
    # 9 evidence --------------------------------------------------------------------------------
    dict(
        kind="evidence",
        title="What better tools changed, and what they cost",
        minutes=2,
        says="Full descriptions, capped rows, and the scout: 17 of 21 correct against 12 of 21",
        src="E15 (docs/benefits.md, Section 1: Agent loop); E7",
        chart={
            "type": "column",
            "title": "Seven easy questions, asked 3 times on each side",
            "categories": ["Answered correctly", "Wrong answers that went out"],
            "series": [("Without the tools", [12, 9]), ("With the tools", [17, 4])],
            "x_label": "Outcome of each run",
            "y_label": "Runs, out of 21",
            "maximum": 21,
        },
        on_slide=[
            "Sample: 21 runs per side, gpt-6-luna, reviewer off, 24 October 2026",
            "- Without: column names, unbounded rows, no scout",
            "- Tokens per run: 3,738 without, 4,857 with",
            "Insight: Better tools lifted easy answers from 12 to 17 of 21; three changes "
            "mixed, so which one helped is unmeasured.",
        ],
        notes=[
            "Purpose: Show the measured effect of the agent loop's tool design, with its "
            "sample size and its cost.",
            "What to say: This is the paired measurement of 24 October. Seven questions without "
            "traps, each asked three times on each side, so 21 runs per side, with the reviewer "
            "off on both sides so it could not hide the difference. Without means the tools "
            "showed column names only, query results were not capped, and there was no schema "
            "scout. With means full column descriptions, capped rows, and the scout. Read the "
            "chart left to right: 12 of 21 correct without, 17 of 21 with. Wrong answers that "
            "went out fell from 9 to 4. The cost: more tokens per run, 4,857 against 3,738, yet "
            "the 21 runs cost slightly less in dollars with the tools, 0.0083 against 0.0097; "
            "the evidence does not explain why, and prompt caching is only a guess. Two "
            "cautions. This row mixes three changes, so it tells you what happened, not which "
            "change did it. And 21 runs per side is small: treat it as a direction, not a rate. "
            "The earlier, smaller measurement of 23 October agreed in direction, 6 of 7 against "
            "4 of 7. And the limit you saw on slide 15 still holds: better tools did nothing "
            "for the trap questions.",
            "The point to land: Better tools made more easy answers right, and did nothing for "
            "the business rules.",
            "Example: The fiscal year 2025 revenue question still failed with every tool on, as "
            "you just saw.",
            'Ask the room: "Which of the three changes would you test first, alone?" Expect: '
            "the column descriptions.",
            "Misconceptions: That 17 of 21 is an accuracy rate. It is one session's count on "
            "seven questions.",
            "Transition: So what does this mean when you design your own text-to-SQL system?",
        ],
    ),
    # 10 design callout -------------------------------------------------------------------------
    dict(
        kind="design_callout",
        title="Your design: schema exposure and value lookup",
        minutes=2.5,
        says="Show the schema on demand, look values up before filtering, and bound every result",
        src="section-1-agent-loop/assignment/README.md; tools.py; deck sources [16], [17], "
        "[44], [45], [49] (Part 4, lessons 4 and 11)",
        on_slide=[
            "Decision: how much schema to show, and how to find values?",
            "| Choice | Do | Because |",
            "|---|---|---|",
            "| Tables | Retrieve, then describe on demand | Schemas often pass 1,000 "
            "columns[^17] |",
            "| Columns | Types, comments, samples, few values | Codes become visible |",
            "| Values | Look up stored values before filtering | Real values are messy[^16] |",
            "DataPilot: describe on demand, capped results; value lookup is Assignment 1.",
        ],
        notes=[
            "Purpose: Turn the agent loop into two design decisions for the learner's own "
            "text-to-SQL system: schema exposure and value lookup.",
            "What to say: Two decisions sit in the agent loop of any text-to-SQL design. First, "
            "schema exposure: how much of the schema the agent sees. Do not paste the whole "
            "schema into the prompt. Spider 2.0 describes enterprise databases that often hold "
            "over 1,000 columns, Source 17, and Uber's QueryGPT team reported single tables over "
            "200 columns using 40,000 to 60,000 tokens of a request, Source 49. Our warehouse is "
            "small, so listing every table works. At scale even the table list is too long: "
            "retrieve candidate tables from their descriptions, scope each agent to one subject "
            "area of about five tables, as Databricks advises for its Genie Agents, Source 44, "
            "and let a person confirm the tables, as Uber's table agent does. Then describe the "
            "few it needs, with types, comments, samples, and the distinct values of small "
            "columns. Second, value lookup. Users never type the stored value: they say the blue "
            "hiking jacket, or misspell a product line, and BIRD names dirty database contents "
            "as a hard part of real text-to-SQL, Source 16. An agent that filters on the user's words finds no "
            "rows and answers with confidence that nothing exists. The fix is a tool that maps "
            "the wording to stored values first, and asks when two are equally close. That is "
            "Assignment 1: a value-lookup tool for DataPilot that records each match in the "
            "envelope's assumptions and asks on a tie.",
            "The point to land: Show the schema on demand, and never filter on the user's words "
            "until a tool has found the stored value.",
            "Example: The catalog holds Alpine Trek 45L Backpack and Alpine Trek 45 L Backpack; "
            "a lookup must ask which one, not pick.",
            "Ask the room: \"How does your system match a user's product name to the stored "
            'one?" Expect: an exact filter, or a pattern match.',
            "Misconceptions: That a pattern match is a lookup. It finds the wrong product as "
            "happily as the right one, and never asks.",
            "Transition: What do you change in your own agent next week?",
        ],
    ),
    # 11 apply-it checklist ---------------------------------------------------------------------
    dict(
        kind="checklist",
        title="Apply it: audit your agent's view next week",
        minutes=1.5,
        says="Five changes for your own agent next week",
        src="section-1-agent-loop/README.md, Apply it in a real system; "
        "section-1-agent-loop/demo/walkthrough.md",
        on_slide=[
            "- Print what each tool returns for one real table",
            "- Cap every list tool: rows, value length, total count, a notice",
            "- Return an envelope: status, query, rows, assumptions",
            "- Set stops in middleware: model calls, tool calls, tokens",
            "- Add a value lookup before any filter on a name",
        ],
        notes=[
            "Purpose: Give five concrete changes a learner can apply to their own agent next week.",
            "What to say: Five things for next week, each about an hour. One: pick one real "
            "table and print exactly what each of your tools returns for it. Is the field your "
            "agent needs visible, typed, and shown with examples? Are the codes visible? Two: "
            "give every tool that can return a list a row cap, a cap on each value's length, "
            "the total count, and a notice when anything was cut; test it with a query that "
            "returns more than the cap. Three: return a structured envelope, not prose: a "
            "status that allows not answering, the final query, the rows, and the assumptions. "
            "Four: put hard stops in middleware, read from one settings file: model calls, tool "
            "calls, and a token budget per run. Five: add a value lookup before any filter on a "
            "name, and ask when two stored values are equally close. Assignment 1 walks you "
            "through that last one, checked live.",
            "The point to land: Fix the view, the size, and the shape before you touch the prompt.",
            "Example: Our row cap and call limits sit in the pack's settings, so a change needs "
            "no code.",
            'Ask the room: "Which item would take you longest?" Expect: the envelope, because '
            "downstream code reads prose today.",
            "Misconceptions: That this needs a new framework. Each item changes tools and "
            "middleware you already have.",
            "Transition: Before the recap, the mistakes teams repeat here.",
        ],
    ),
    # 12 pitfalls -------------------------------------------------------------------------------
    dict(
        kind="pitfalls",
        title="Agent loop pitfalls that cost tokens or hide answers",
        minutes=1.5,
        says="Three agent-loop mistakes, what each did in our runs, and the fix",
        src="E14, E16, E20 (docs/calibration-report.md, Agents on and off, Changes recorded; "
        "docs/benefits.md)",
        on_slide=[
            "| Pitfall | What happened | Do instead |",
            "|---|---|---|",
            "| No cap in the tool | Up to 187,030 tokens a run | Cap rows and values in the tool |",
            "| Asking whenever unsure | A question back, nothing to check | Answer with stated "
            "assumptions |",
            "| Prose instead of an envelope | No query to re-run | Return status, query, rows, "
            "assumptions |",
            "Insight: Measure a helper agent on and off: on 4 questions, 1 run each, the scout "
            "added 1.7 to 2.2 times the tokens and changed no gold result.",
        ],
        notes=[
            "Purpose: Name the agent-loop mistakes that cost the most in our runs, with the "
            "fix for each and the measured cost of an unmeasured helper.",
            "What to say: Three pitfalls from this course's runs. First, no cap in the tool, as in the story. "
            "With ours removed, ten thousand rows reached the model and runs reached up to "
            "187,030 tokens. Second, asking whenever unsure. Early "
            "on, the analyst answered the fiscal year 2025 revenue question with a clarifying "
            "question, which left the reviewer and the gold check nothing to check. Answer with "
            "stated assumptions; ask when a term has no rule, such as VIP. Third, prose instead "
            "of an envelope: a sentence with no query cannot be re-run. Now the insight. On four "
            "questions, one run each, the scout added 1.7 to 2.2 times the tokens, with the "
            "reviewer off and on, and the gold results were identical. The scout stays because it "
            "was part of the setup that scored 17 of 21 and keeps table exploration out of the "
            "analyst's context; whether it pays alone is unmeasured.",
            "The point to land: Every pitfall here looks careful; measure it before you trust it.",
            'Example: "Employee headcount by department" names nothing in a sales warehouse, '
            "and it correctly ended needs clarification.",
            'Ask the room: "Which helper agent in your system was never measured off?" Expect: '
            "a router or a planner.",
            "Misconceptions: That more agents add reliability. They add calls, latency, and "
            "correlated errors when they share a model.",
            "Transition: Let me check what stuck.",
        ],
    ),
    # 13 recap and question ---------------------------------------------------------------------
    dict(
        kind="recap",
        title="Recap: what can your agent not see?",
        minutes=1.5,
        says="Three points to keep, and one question about the envelope",
        src="section-1-agent-loop/README.md; contracts/answer.py",
        on_slide=[
            "- The tools decide what the agent sees",
            "- Cap rows and values in the tool, with the count",
            "- Stops in middleware; the answer in an envelope",
            'Question: An agent answers "orders this quarter" with one confident number. Which '
            "two envelope fields show whether it used the fiscal quarter?",
        ],
        notes=[
            "Purpose: Consolidate the agent loop and check one idea with a question.",
            "What to say: Three points to keep. The tools decide what the agent sees, so design "
            "them before the prompt. Caps belong in the tool, on rows and on values, with the "
            "count. The stops live in middleware and the answer in a typed envelope. Now the "
            "question on the slide; give the room thirty seconds in the chat. The answer: the "
            "final query, whose date range shows calendar or fiscal months, and the "
            "assumptions, where a good agent states which quarter it used. Without those two "
            "fields, the number is all you have.",
            "The point to land: A number you cannot trace to a query and its assumptions "
            "cannot be checked.",
            "Example: The confident wrong answer wrote its own assumption, calendar year 2025 "
            "in Coordinated Universal Time, into the answer text.",
            "Ask the room: the question on the slide. Expect: the final query and the "
            "assumptions; some say the status, which only says it answered.",
            "Misconceptions: That a stated assumption makes the answer right. It makes the "
            "mistake visible; the verification loop has to catch it.",
            "Transition: So how do we catch a wrong answer that looks right? That is Section 2: "
            "Verification loop.",
        ],
    ),
]
