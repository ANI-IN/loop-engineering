"""Section 1: Agent loop, 0:40 to 1:15, 35 minutes, 13 slides, under design system 2.

The slide schema is in slides/design-system.md; slides/source/samples.py is its worked example.
The order is the second rebuild's (the lead's brief, "Each section's 13 slides"): the opener, four
pattern slides with their pattern diagrams, the pattern in code, DataPilot's version, the demo, the
one evidence slide, the design callout, apply it, the pitfalls, and the recap with the scoreboard.
Every course number comes from the deck evidence list (entries E1 and on, named in each slide's
src); every external claim from the verified source lists (sources [1] to [54] as in
slides/source/sources.py, [55] to [65] from the second rebuild's source list), cited on a slide as
[^n] and in the notes as "Source n".
"""

RULES = "design system 2"

DEMO_PAGE = "https://github.com/ANI-IN/loop-engineering/tree/main/section-1-agent-loop/demo"
EXPECTED = "section-1-agent-loop/demo/expected/"

SLIDES = [
    # 1 section opener --------------------------------------------------------------------------
    dict(
        kind="opener",
        title="Section 1: Agent loop",
        minutes=1,
        says="The agent loop fixes an agent that sees too little to be right, or receives too "
        "much to stay in budget",
        src="section-1-agent-loop/README.md; E16, E17 (docs/evidence/section-1-agent-loop.md, "
        "Results; docs/costs.md, Commands; capture run 199d2188, 25 October 2026); E18 (pack.yaml "
        "budgets); deck source [4]",
        on_slide=[
            "Fixes: an agent that sees too little to be right, or receives too much to stay in "
            "budget",
            "Insight: Bound what a tool returns inside the tool[^4]; a budget checked between calls "
            "arrives too late.",
        ],
        notes=[
            "Purpose: Open Section 1 from the scoreboard: the question is still wrong, and the "
            "first loop decides what the agent can see and how much it receives.",
            "What to say: The fiscal year 2025 question is still wrong. Section 1 is the agent "
            "loop. Its failure is the runaway run from the four failures, back as promised: row "
            "cap off, ten thousand rows to the model, 184,983 tokens against a budget of 60,000. "
            "The budget is checked between calls; only the tool decides what one call carries. "
            "You will watch it live. By the end, the agent sees enough, and the answer is still "
            "wrong.",
            "The point to land: The agent can only be as good as what its tools show it and as "
            "safe as what its tools hand back.",
            "Example: Run 199d2188 on 25 October 2026, with the unbounded rows bug on: 184,983 "
            "tokens, escalated at the run budget; six such runs reached 182,654 to 187,030 tokens "
            "each.",
            'Ask the room: Only if ahead of the clock: "Which of your tools could return ten '
            'thousand of anything?" Expect: search, logs, query tools, file listings.',
            'Misconceptions: "A larger context window solves this." It postpones it: every token '
            "is sent again and paid for on every later call in the run.",
            "Transition: Start with the loop itself: a model, a tool, an observation, and the code "
            "that decides when it stops.",
        ],
    ),
    # 2 pattern: the agent loop and stop conditions in code -------------------------------------
    dict(
        kind="pattern",
        title="The agent loop, with stops in code",
        minutes=2.5,
        says="A model picks a tool, code runs it, the result comes back; code, not the model, "
        "ends the run",
        src="docs/diagrams/patterns/README.md (pattern-agent-loop); deck sources [1], [9], [55], "
        "[56], [58], [59], [60]; E18 (pack.yaml limits)",
        figure={
            "diagram": "pattern-agent-loop",
            "alt": "The agent loop: a task goes to the model, which either calls a tool or "
            "answers; the tool call goes to a tool that runs, and its observation comes back to "
            "the model, until the model answers; beside the loop, a grey box of stop conditions "
            "in code, model calls, tool calls, tokens, and time, checked every turn",
        },
        on_slide=[
            "Definition: A model calls a tool, reads the result, repeats; code decides when to "
            "stop.",
            "Use when: each step depends on the last",
            "Avoid when: one fixed query or call will do",
            "Elsewhere: OpenAI's Agents SDK caps turns; LangGraph caps steps at 1,000 by "
            "default[^58][^59]",
        ],
        notes=[
            "Purpose: Define the agent loop and stop conditions in code, as a pattern for any "
            "agent, before showing DataPilot's.",
            "What to say: The problem first. A task that needs several lookups, where each step "
            "depends on the last, cannot be written as one fixed call. The pattern is the agent "
            "loop, which LangChain sums up as a model calling tools in a loop until the task is "
            "complete, Source 1. Walk the diagram. A task goes to the model. The model either "
            "answers or asks for a tool. Your code runs the tool, because the model cannot run "
            "anything; Anthropic calls every tool call a round trip, Source 56. The result comes "
            "back as an observation, and the model goes again. Now the grey box: the stop "
            "conditions: model calls, tool calls, tokens, and time, checked by code on every turn. "
            "A stuck model does not know it is stuck, so a prompt that says stop after five tries "
            "is a hope. Code ends the run whatever the model wants, in a status you can route. A "
            "time limit needs a request timeout on every model and tool call too, because a check "
            "between turns cannot interrupt a call in flight. The alternative is a fixed chain: "
            "cheaper, predictable, and right when the steps are known in advance; the loop buys "
            "flexibility with calls, latency, and variation from run to run. Elsewhere, the OpenAI "
            "Agents SDK raises an error past its turn limit, Source 58, and LangGraph stops a "
            "graph at 1,000 steps by default, Source 59, a backstop against a cycle, Source 60, "
            "not a budget. DataPilot's limits are on its code slide; it bounds calls, tokens and "
            "query time, but sets no deadline per run and no request timeout of its own, so the "
            "client library's default applies. Add both in yours.",
            "The point to land: The model chooses the next step; your code decides whether there "
            "is one.",
            "Example: A support agent, illustrative: it looks up the order, reads the refund "
            "policy, drafts a reply, and after eight tool calls without an answer it stops and "
            "hands the ticket to a person, with what it found.",
            'Ask the room: "Where does your agent\'s step limit live today?" Expect: in the '
            "framework default, or in the prompt.",
            "Misconceptions: That the framework's default limit is your budget. A default of 1,000 "
            "steps stops an infinite loop, not an expensive one; set your own limits per run.",
            "Transition: The loop spends something on every turn: context. That is the next "
            "pattern.",
        ],
    ),
    # 3 pattern: context as a budget, and tool design -------------------------------------------
    dict(
        kind="pattern",
        title="Context is a budget; tools spend it",
        minutes=2.5,
        says="Return what the model needs, truncate with a notice, and return errors that say "
        "what to try",
        src="docs/diagrams/patterns/README.md (pattern-tool-design); deck sources [4], [55], "
        "[57], [61]; E16, E18; platform/src/datapilot/loop1_agent/tools.py lines 39-60",
        figure={
            "diagram": "pattern-tool-design",
            "alt": "Context as a budget: the context holds the instructions, the tool results, "
            "and the room left for the next steps; a tool returns only what the model needs into "
            "it; a long result is truncated with a notice, for example showing 50 of 12,000 rows, "
            "add a filter to see the rest; a failure comes back as a structured error saying what "
            "failed, why, and what to try next, never a stack trace",
        },
        on_slide=[
            "Definition: A tool returns only what the model needs, and says what it cut.",
            "Use when: a tool can return a lot, or fail",
            "Avoid when: the output is small and fixed",
            "Elsewhere: Claude Code caps a tool response at 25,000 tokens by default[^4]",
        ],
        notes=[
            "Purpose: Define context as a budget and the three rules of tool design that follow "
            "from it, for any agent.",
            "What to say: The problem in general terms. Everything a tool returns stays in the "
            "conversation and is sent again on every later model call, so one large result is "
            "paid for many times, and it crowds out the instructions. Anthropic calls it an "
            "attention budget: context is a finite resource with diminishing returns, Source 61. "
            "OpenAI bills even the tool definitions as input tokens, Source 55. Walk the diagram "
            "left to right. The context holds the instructions, the tool results, and the room "
            "left for the next steps. Rule one: a tool returns only what the model needs for its "
            "next step, high-signal fields, not the whole record, Source 4. Rule two: a long "
            "result is truncated with a notice, such as showing 50 of 12,000 rows, add a filter. "
            "The count tells the model what it did not see; the notice tells it what to do next, "
            "and Anthropic's tool guidance says the same, Source 4. Rule three: a failure comes "
            "back as a structured error: what failed, why, and what to try. Anthropic's tool "
            "documentation asks for instructive errors so the model can recover without "
            "guessing, Source 57; a stack trace spends the budget and teaches nothing. "
            "Alternatives: pagination and filter parameters on the tool, which pair well with a "
            "cap; a model that summarises the result, which costs a call and can drop the fact "
            "you needed; or a larger context window, which only postpones the bill.",
            "The point to land: Every token a tool returns is spent again on every later call; "
            "return less, say what you cut, and make errors steer.",
            "Example: A coding agent, illustrative: its file search returns the first 50 of 3,000 "
            "matches with a notice to narrow the pattern, and a failed build returns the failing "
            "test and line, not four hundred lines of log.",
            'Ask the room: "Which of your tools returns a stack trace to the model today?" '
            "Expect: most of them, by default.",
            "Misconceptions: That a row cap bounds size. It bounds rows; one row can hold an "
            "array of every email address, so cap each value's length too.",
            "Transition: Bounding what comes back is half of it. The other half is choosing what "
            "the agent asks to see: schema linking.",
        ],
    ),
    # 4 pattern: schema linking by progressive disclosure, and value grounding -----------------
    dict(
        kind="pattern",
        title="Schema linking by progressive disclosure",
        minutes=2.5,
        says="Names first, describe on demand, retrieve for large schemas, and look values up "
        "before filtering",
        src="docs/diagrams/patterns/README.md (pattern-progressive-disclosure); deck sources [18] "
        "(Appendix B), [44], [49], [55], [61], [62], [63]; E10; "
        "platform/src/datapilot/loop1_agent/tools.py lines 89-120",
        figure={
            "diagram": "pattern-progressive-disclosure",
            "alt": "Progressive disclosure: list_tables for a small schema, every name and nothing "
            "more, or search_schema for a large one, retrieving the closest tables only; then "
            "describe_table on demand for the tables picked; then find_values to check a stored "
            "value, for example CA or California; then the model writes the query with real "
            "names and real values",
        },
        on_slide=[
            "Definition: Names first, details on demand, stored values looked up before any "
            "filter.",
            "Use when: the schema will not fit the prompt",
            "Avoid when: a few small tables fit easily",
            "Elsewhere: Anthropic's Agent Skills load names and descriptions first, the rest on "
            "demand[^62]",
        ],
        notes=[
            "Purpose: Define schema linking by progressive disclosure and value grounding as one "
            "pattern any agent over a large catalogue can use.",
            "What to say: Schema linking is mapping the words of a question onto tables, columns, "
            "and values. It is where text-to-SQL fails most: LinkAlign pooled the schemas of every "
            "Spider database on purpose, and 68.3 percent of the failures in its 500 questions "
            "were schema-linking errors, Source 18. Pasting the whole schema into the prompt does "
            "not scale; Uber reported single tables of over 200 columns using 40,000 to 60,000 "
            "tokens of a request, Source 49. The pattern is progressive disclosure: the agent sees "
            "more only when it asks, Source 61. Walk the diagram. Step one, the names: for a small "
            "schema, list every table with a one-line description; for a large one, search the "
            "descriptions and return the closest few. Step two, describe on demand: types, "
            "comments, a few sample rows, and the distinct values of small columns, so a status "
            "column shows its codes. Step three, ground the values: a lookup turns California into "
            "the stored CA, and asks when two values are equally close. Only then does the model "
            "write the query. Trade-offs: each step is a call, and retrieval can miss; Uber found "
            "plain similarity search on schemas did not return relevant results, and added a step "
            "where a person confirms the tables, Source 49. Anthropic's Tool Search does the same "
            "for tools, Source 63; its savings are its own figures for a tool library, not for "
            "schemas.",
            "The point to land: Show names first, details on demand, and never filter on the "
            "user's words until a tool has found the stored value.",
            "Example: A support agent, illustrative: it lists the titles of two hundred help "
            "articles and opens the one it needs; a workflow agent with three hundred "
            "application programming interface endpoints searches them, as OpenAI's tool search "
            "defers large tool sets, Source 55.",
            'Ask the room: "How does your agent match a product name to the stored one?" Expect: '
            "an exact filter, or a pattern match.",
            "Misconceptions: That a pattern match is a lookup. It finds Alpine Trek 45L Backpack "
            "as happily as Alpine Trek 45 L Backpack, and never asks which one was meant.",
            "Transition: The agent now sees the right things. Last pattern: the answer envelope it "
            "hands back, and helper agents that look for it.",
        ],
    ),
    # 5 pattern: structured outputs, and helper agents for context isolation --------------------
    dict(
        kind="pattern",
        title="Answer envelopes and helper agents",
        minutes=2.5,
        says="A typed answer code can validate; helpers explore in their own context, at a cost",
        src="docs/diagrams/patterns/README.md (pattern-structured-output); deck sources [7], "
        "[61], [64], [65]; E14, E19, E20; platform/src/datapilot/contracts/answer.py lines 11-28",
        figure={
            "diagram": "pattern-structured-output",
            "alt": "A helper agent in its own context reads the large material and passes a short "
            "brief to the main agent, which keeps a clean context and returns an answer envelope "
            "in a fixed schema, with a status, the answer, the evidence, and the assumptions, "
            "validated by code before anyone reads it; the cost of a helper is more model calls "
            "and time, and any detail its brief leaves out never arrives",
        },
        on_slide=[
            "Definition: The answer is a typed envelope code checks; helpers read in their own "
            "context.",
            "Use when: code acts on it; side work is big",
            "Avoid when: a person reads; steps interlock",
            "Elsewhere: OpenAI's Structured Outputs: replies adhere to your supplied schema[^64]",
        ],
        notes=[
            "Purpose: Define structured outputs as an answer envelope, and helper agents for "
            "context isolation with their cost, as patterns for any agent.",
            "What to say: Two linked patterns. The problem: prose answers cannot be checked, "
            "routed, or re-run, and a main agent that explores everything itself fills its own "
            "context. Walk the diagram from the right. The main agent returns an answer envelope "
            "in a fixed schema: a status, the answer, the evidence, such as the query and its "
            "rows, and the assumptions it made. Code validates it before anyone reads it; a "
            "validation error goes back to the model inside the same limits, as LangChain's "
            "structured output retries, Source 7. Make the status allow not answering: answered, "
            "needs clarification, refused, escalated. A refusal is then an outcome code can route, "
            "not a sentence to parse; OpenAI's Structured Outputs keep every required field and "
            "make refusals detectable, Source 64. Now the left: a helper agent reads the large "
            "material in its own context and passes back a short brief. Anthropic's helpers often "
            "return 1,000 to 2,000 tokens, Source 61. The cost is real: more calls, more time, "
            "and any detail the brief drops never arrives. In Anthropic's own research system, "
            "multi-agent runs used about 15 times the tokens of a chat, Source 65. Use an envelope whenever code acts on the answer, and a "
            "helper when the side task is big; skip the envelope when a person only reads prose, "
            "and the helper when the steps interlock and need one shared context. Measure a helper "
            "on and off, and keep it only if it helps. DataPilot has not done that: the schema "
            "helper added 1.7 to 2.2 times the tokens on four questions, one run each, with no "
            "gold result changed, and it stays on. That is a known gap, not a recommendation.",
            "The point to land: Return a typed envelope every later step can check; add a helper "
            "only when its clean context is worth the calls it costs.",
            "Example: A coding agent, illustrative: a helper reads a 20,000-line build log and "
            "returns the failing test and its error; Anthropic notes that most coding tasks are "
            "less parallel than research, Source 65.",
            'Ask the room: "What does your agent return today: prose, or fields?" Expect: prose, '
            "parsed by a regular expression downstream.",
            "Misconceptions: That a valid envelope is a correct answer. It is a checkable one; "
            "Section 2 does the checking.",
            "Transition: Here are all four patterns as a few lines of code.",
        ],
    ),
    # 6 the pattern in code ---------------------------------------------------------------------
    dict(
        kind="mechanism",
        title="The pattern in code: a bounded agent loop",
        minutes=2,
        says="Code owns the loop, the stops, the cap on every result, and the shape of the answer",
        src="generic pseudocode written for the course",
        code={
            "language": "python",
            "panel": "Pattern",
            "origin": "generic pseudocode written for the course, in Python syntax",
            "lines": [
                "def run_agent(context, model, tools, limits):",
                "    for _ in range(limits.model_calls):",
                "        step = model.next(context, tools)",
                "        context.append(step)",
                "        if step.is_final and (answer := Envelope.check(step.output)).ok:",
                "            return answer.envelope",
                "        context.extend(observe(tools, step, limits))",
                '    return Envelope(status="escalated", reason="call limit", evidence=context)',
            ],
            "marks": [
                (1, "range(limits.model_calls)", 1),
                (4, "Envelope.check(step.output)", 2),
                (6, "observe(tools, step, limits)", 3),
                (7, 'status="escalated"', 4),
            ],
        },
        on_slide=[
            "Idea: code owns the stops, here or in an expense-report agent",
            "1. Code ends the loop, not the model",
            "2. A bad answer becomes feedback",
            "3. Each call, then its capped result",
            "4. A limit returns what was found",
        ],
        notes=[
            "Purpose: Show the four patterns as eight lines of generic code a learner can map onto "
            "any agent framework.",
            "What to say: Eight lines, no framework. Line one: the agent takes its context, which "
            "starts as the task, a model, its tools, and its limits. Marker one, line two: the "
            "loop counts model calls, a limit no answer from the model can extend; the tool-call "
            "count, tokens and time are the other stops from the agent loop slide, and observe "
            "can enforce the tool-call count. Line three: the model takes the next step. Line "
            "four: the model's own step goes into the context first, because "
            "tool-calling interfaces expect every result to follow its call. Marker two, lines "
            "five and six: a final step returns its envelope only if it passes the check. Marker "
            "three, line seven: observe returns one result per tool call in the step, each "
            "matched to its call id; it turns an exception into one sentence on what to try, and "
            "caps rows and each value, with the count and a notice. For a final step that failed "
            "the check, it returns the validation error as feedback. Marker four, line eight: at "
            "the limit the run still returns an envelope, status escalated, carrying what the "
            "agent found, so a person can pick it up.",
            "The point to land: Every guarantee in the loop is a line of code: the limit, the "
            "cap, and the shape of the answer.",
            "Example: A workflow agent that files expense reports, illustrative, uses the same "
            "eight lines: its limit stops a loop of failed uploads, and escalated sends the report "
            "to a person.",
            'Ask the room: "Which of these lines is missing from your agent?" Expect: the cap, '
            "the error sentence, and the escalated return.",
            "Misconceptions: That an exception is a fine way to end a run. An exception loses "
            "what the agent found; an envelope with a status keeps it and can be routed.",
            "Transition: Now the cap inside line seven, in DataPilot's real code.",
        ],
    ),
    # 7 DataPilot's version ---------------------------------------------------------------------
    dict(
        kind="mechanism",
        title="DataPilot's version: the query tool's cap",
        minutes=2,
        says="The query tool returns at most 50 rows, values cut at 2,000 characters, the total "
        "count, and a notice",
        src="platform/src/datapilot/loop1_agent/tools.py lines 39-60; "
        "platform/src/datapilot/loop1_agent/analyst.py lines 72-86; E16, E18",
        code={
            "language": "python",
            "panel": "DataPilot",
            "origin": "platform/src/datapilot/loop1_agent/tools.py lines 39-48 (the payload's "
            "other keys, lines 43-44 and 46, shown as one ...; the notice's text on line 48 "
            "shown as [...])",
            "lines": [
                "def format_result(result: QueryResult, row_cap: int) -> str:",
                "    rows, truncated = cap_rows(list(result.rows), row_cap)",
                "    rows, values_cut = cap_values(rows)",
                "    payload: dict[str, Any] = {",
                '        "total_row_count": result.total_row_count,',
                "        ...",
                "    }",
                "    notices = [...] if truncated else []",
            ],
            "marks": [
                (1, "cap_rows(list(result.rows), row_cap)", 1),
                (2, "cap_values(rows)", 2),
                (4, '"total_row_count": result.total_row_count', 3),
                (7, "notices", 4),
            ],
        },
        on_slide=[
            "Idea: the tool decides how much reaches the model",
            "1. At most 50 rows go back",
            "2. Each value cut at 2,000 characters",
            "3. The total count still goes back",
            "4. A notice says rows were cut",
        ],
        notes=[
            "Purpose: Show the cap of the generic loop in DataPilot's real code, line by line, and "
            "where its other stops live.",
            "What to say: Every query result passes through this function before the model sees "
            "it. Line one takes the result and the row cap. Marker one, line two: the rows are cut "
            "to the cap, 50, read from the pack's settings, not from the prompt. Marker two, line "
            "three: each value is cut at 2,000 characters, because a row cap counts rows, and one "
            "row can hold a whole list. Lines four to seven build the payload; the dots stand for "
            "the columns, the rows, and the truncated flag. Marker three, line five: the total row count still goes back, so 50 rows never look "
            "like the whole answer. Marker four, the last line: when rows were cut, a notice says "
            "Showing 50 of so many rows, and warns against combining rows. One limit: the cap protects the model's context, not the worker. The "
            "executor fetches every row to report the total count, bounded only by the statement "
            "timeout; on a large warehouse, fetch the cap plus one and count separately. The rest "
            "of the loop is set when the analyst is built: a model-call limit of 12, a tool-call "
            "limit of 16 that answers extra calls with an error, and a response format that must "
            "validate as the answer envelope; the token budget is a run guard passed in beside "
            "them.",
            "The point to land: A cap in the tool holds whatever the model asks for; a cap in the "
            "prompt holds only if the model obeys.",
            "Example: In the paired run of 24 October 2026, the capped large query used 30,216 "
            "tokens, the reviewer's round trip included, against the uncapped range you met in the "
            "opener.",
            'Ask the room: "What should the agent do when it sees the notice?" Expect: aggregate '
            "in the query, or narrow the question.",
            "Misconceptions: That a cap hides answers. It can, which is why the count and the "
            "notice travel with it: the agent knows to filter or aggregate instead.",
            "Transition: Enough code. Let us run the loop live.",
        ],
    ),
    # 8 demo ------------------------------------------------------------------------------------
    dict(
        kind="demo",
        title="Live: the agent loop, right, wrong, and unbounded",
        minutes=12,
        says="The simple question, the confident wrong answer, and unbounded rows, live",
        src="platform/demos/registry.yaml (section agent-loop); "
        "section-1-agent-loop/demo/README.md; section-1-agent-loop/demo/walkthrough.md; E3, "
        "E13, E16, E22",
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
            "Purpose: Run the agent loop live: one correct answer, one confident wrong answer only "
            "the gold check exposes, and the row cap off and on.",
            "What to say: Let's watch the agent loop answer, get it wrong, and blow its budget, "
            "live. Nothing here is recorded and nothing is scripted: each run calls the class "
            "model, and the model chooses its own tools. First a simple question, so you see the "
            "loop work end to end. Then the fiscal year 2025 revenue question from the opening: "
            "this time you watch the agent loop produce that wrong number, tool by tool. Then the "
            "row cap, off and then on, so the opener's token counter happens in front of you. "
            "Watch three things: the tool timeline, the gold check, and the token counter. When "
            "each result lands I will read its numbers aloud and show its live stamp, the start "
            "time and the trace link, so you know it ran just now.",
            "Demo: The simple question.",
            "Command: 0:55 to 0:58. First check the status line: the report-only level, the kill "
            'switch released, and Planted None: the fixed system. Then type "How many orders have '
            'been placed in total?" in the console and press Agent > Ask; or, in the demo '
            "terminal, make demo NAME=agent-simple-question, which sends the same question.",
            "Point at: first the tool timeline as each call appears, list_tables, describe_table, "
            "run_query, with its duration; then the one-line count query and the envelope's "
            "status; then the tokens and cost; last the live stamp.",
            "Expected output: Posted, 405,738 orders, one count query, about 5,100 tokens and "
            "0.0005 dollars; 14 to 39 seconds in the recorded runs.",
            "While it runs: 14 to 39 seconds of the 3-minute slot. Say that nothing is scripted: "
            "the model chose these tools itself, and the path can differ run to run; the envelope "
            "and its query are what we check.",
            "If it fails: 1. Read the status aloud; a run that answers correctly with more tool "
            "calls is not a failure. 2. If it stays queued or stalls, run make reset "
            "NAME=agent-loop in the demo terminal (about 7 seconds). 3. Press Agent > Ask again "
            "with the same question. 4. A missing trace link is not a failure: say LangSmith may "
            "be refusing traces and point at the run id. Cutoff for every demo of this slide: a "
            "retry that would end after 1:06 is skipped and named for the Thursday review.",
            "Backup screenshot: "
            + EXPECTED
            + "agent-simple-question-answer.png, the posted count with its three tool calls; show "
            "it only while the reset runs, never instead of the run.",
            "Demo: The confident wrong answer.",
            "Command: 0:58 to 1:03. Press Agent > Ask the spine question in the console, the "
            "button for the fiscal year 2025 revenue question; or make demo "
            "NAME=agent-confident-wrong-answer.",
            "Point at: first the answer text, which states its own assumption, calendar year 2025 "
            "in Coordinated Universal Time; then the answer-versus-gold ledger with the mismatch "
            "on both databases; then the annotated query, each mark and its trap note; last the "
            "live stamp.",
            "Expected output: a mismatch against the gold answer, 64,015,091.21 dollars, with one "
            "or more trap notes; the recorded runs answered 72,394,572.08 with three trap notes, "
            "or 76,981,355.95; usually held for approval by a reviewer concern; 35 to 76 seconds.",
            "While it runs: 35 to 76 seconds of the 5-minute slot. Ask the room to predict which "
            "of the five traps the query will hit, and to write it in the chat. If the strip shows "
            "holding for approval, say that is the reviewer of Section 2 doubting the fiscal year; "
            "leave it held, the gold check still shows.",
            "If it fails: 1. If the answer is held, do nothing: the gold check still appears. 2. "
            "If no number comes back, there is no gold check: run make reset NAME=agent-loop "
            "(about 7 seconds). 3. Press Agent > Ask the spine question (the console's button for "
            "the fiscal year 2025 revenue question) again. 4. If it comes back correct, say so: "
            "the gold check, not the wording, is the verdict, and one run is one run. The slide's "
            "cutoff applies: after 1:06, no retry.",
            "Backup screenshot: "
            + EXPECTED
            + "agent-confident-wrong-answer-sql.png, the query with its three trap marks and the "
            "mismatch; show it only while the reset runs, never instead of the run.",
            "Demo: Unbounded rows.",
            "Command: 1:03 to 1:07. First, in the demo terminal, make demo "
            "NAME=agent-unbounded-rows PLANTED=1, the bug on for that run only; then press Agent > "
            "Run large query in the console, or make demo NAME=agent-unbounded-rows, with it off.",
            "Point at: the token counter of the planted run and its escalated status; then the "
            "same counter on the fixed run; then the notice, Showing 50 of 10000 rows, and the "
            "total count under the rows; last the live stamp of each. If a minute is left, open "
            "platform/src/datapilot/loop1_agent/tools.py lines 33-54 in the editor: the cap from "
            "the code slide and its planted branch.",
            "Expected output: with the bug on, 182,654 to 187,030 tokens, escalated at the run "
            "budget, in about 12 seconds; with it off, 17,298 to 30,216 tokens in 26 to 48 "
            "seconds, sometimes held by a reviewer concern.",
            "While it runs: two runs inside the 4-minute slot. During the planted run, say the "
            "budget is checked before each call, so one call can overshoot it; during the fixed "
            "run, point back at the cap on the DataPilot code slide.",
            "If it fails: 1. If the counter does not jump, the run went without the flag: repeat "
            "make demo NAME=agent-unbounded-rows PLANTED=1. 2. If the fixed run holds for "
            "approval, leave it: the token counter is the moment. 3. Anything else: make reset "
            "NAME=agent-loop (about 7 seconds), then the same trigger. After 1:06, no retry.",
            "Backup screenshot: "
            + EXPECTED
            + "agent-unbounded-rows-planted-tokens.png and agent-unbounded-rows-fixed-tokens.png "
            "in the same folder, 184,983 against 28,468 tokens; show them only while the reset "
            "runs, never instead of the run.",
            "Demo: Texas last quarter.",
            "Command: optional, cut first, only when the three core demos end before 1:06: press "
            "Agent > Ask with the Texas question, or make demo NAME=agent-texas-last-quarter.",
            "Point at: the join path in the query, four tables, and the date range: August to "
            "October 2025 is the last completed fiscal quarter against the business date of 31 "
            "January 2026.",
            "Expected output: an answer whose query joins four tables; no benchmark question asks "
            "this question, so no gold check; the date range shows whether the fiscal-quarter "
            "trap was hit.",
            "While it runs: inside the slide's last minute. Say last completed fiscal quarter: on "
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
            "Transition: One run is a story. Next, the measurement: what better tools changed, and "
            "what they cost.",
        ],
    ),
    # 9 evidence --------------------------------------------------------------------------------
    dict(
        kind="evidence",
        title="What better tools changed, and what they cost",
        minutes=2,
        says="Full descriptions, capped rows, and the schema helper: 17 of 21 correct against 12 "
        "of 21",
        src="E15 (docs/benefits.md, Section 1: Agent loop; docs/calibration-report.md, The "
        "benefits measurement); E7",
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
            "Sample: 21 runs per side, seven questions asked 3 times each, reviewer off",
            "- **Lesson:** better tools fixed answers the schema can explain; three changes at "
            "once hide the cause",
            "- Without: column names only, unbounded rows, no schema helper",
            "- With: full descriptions, capped rows, the schema helper",
            "- Tokens a run: 3,738, then 4,857",
        ],
        notes=[
            "Purpose: Show the measured effect of the agent loop's tool design, with its sample "
            "size and its cost.",
            "What to say: This is the paired measurement of 24 October 2026, with gpt-6-luna. "
            "Seven questions without traps, each asked three times on each side, so 21 runs per "
            "side, with the reviewer off on both sides so it could not hide the difference. "
            "Without means the tools showed column names only, results were not capped, and there "
            "was no schema helper. With means full column descriptions, capped rows, and the "
            "schema helper. Read the chart left to right: 12 of 21 correct without, 17 of 21 with. Wrong "
            "answers that went out fell from 9 to 4. The cost: more tokens per run, 4,857 against "
            "3,738. Two cautions. This row mixes three changes, so "
            "it tells you what happened, not which change did it. And 21 runs per side is small: "
            "a direction, not a rate. The earlier, smaller run of 23 October agreed in direction, "
            "6 of 7 against 4 of 7. And better tools did nothing for the traps: under the "
            "starting knowledge, 0 of 99 trap-question runs passed.",
            "The point to land: Better tools made more easy answers right, and did nothing for "
            "the business rules.",
            "Example: The fiscal year 2025 revenue question still failed with every tool on, as "
            "you just saw. In dollars the 21 runs cost 0.0083 with the tools and 0.0097 without; "
            "the evidence does not record why, so do not read a saving into it.",
            'Ask the room: "Which of the three changes would you test first, alone?" Expect: the '
            "column descriptions.",
            "Misconceptions: That 17 of 21 is an accuracy rate. It is one session's count on seven "
            "questions.",
            "Transition: So what does this mean when you design your own text-to-SQL system?",
        ],
    ),
    # 10 design callout -------------------------------------------------------------------------
    dict(
        kind="design_callout",
        title="Your design: schema exposure and value lookup",
        minutes=1.5,
        says="How much schema the agent sees, and how it finds values, by the size of the "
        "warehouse",
        src="section-1-agent-loop/assignment/README.md; deck sources [44], [49]; E10",
        on_slide=[
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
            "confirms them, as Uber's table agent does, Source 49. Columns: describe on demand in a small one; in a large one, prune to the columns "
            "in play, as Uber's column prune agent does, Source 49. Values: always look a value up "
            "before filtering on it. Databricks advises five or fewer tables per Genie Agent, and "
            "its prompt matching maps the user's words to stored values, Source 44. DataPilot's "
            "warehouse is small, so it lists every table and describes on demand. Value lookup is "
            "Assignment 1: a tool that records each match in the envelope's assumptions and asks "
            "on a tie. Decide which column you are in before you write a prompt.",
            "The point to land: Size decides how much schema to show; values are always looked up, "
            "never typed in from the question.",
            "Example: The catalogue holds Alpine Trek 45L Backpack and Alpine Trek 45 L Backpack; "
            "a lookup must ask which one, not pick.",
            'Ask the room: Only if ahead of the clock: "Which column of this table is your '
            'warehouse?" Expect: most say large.',
            "Misconceptions: That retrieval removes the need for review. Retrieval can miss the "
            "table that matters, which is why a person or a check confirms it.",
            "Transition: What do you change in your own agent next week?",
        ],
    ),
    # 11 apply-it checklist ---------------------------------------------------------------------
    dict(
        kind="checklist",
        title="Apply it: audit your agent's view next week",
        minutes=1.5,
        says="Six changes for your own agent next week",
        src="section-1-agent-loop/README.md, Apply it in a real system; "
        "section-1-agent-loop/demo/walkthrough.md",
        on_slide=[
            "- Print what each tool returns for one real table",
            "- Cap rows, value length and total count in every list tool, with a notice",
            "- Rewrite errors as what failed and what to try next",
            "- Return an envelope with status, query, rows, assumptions",
            "- Set stops in code on model calls, tool calls, tokens",
            "- Add a value lookup before any filter on a name",
        ],
        notes=[
            "Purpose: Give six concrete changes a learner can apply to their own agent next week.",
            "What to say: Six things for next week, each about an hour. One: pick one real table "
            "and print exactly what each tool returns for it. Is the field your agent needs "
            "visible, typed, and shown with examples? Two: give every tool that can return a list "
            "a row cap, a cap on each value's length, the total count, and a notice; test it with "
            "a query that returns more than the cap. Three: rewrite your tool errors as one "
            "sentence each: what failed, and what to try next. Four: return a structured "
            "envelope, not prose, with a status that allows not answering. Five: put hard stops in "
            "code, read from one settings file: model calls, tool calls, and a token budget per "
            "run. Six: add a value lookup before any filter on a name, and ask when two stored "
            "values are equally close. Assignment 1 walks you through that last one, checked live.",
            "The point to land: Fix the view, the size, and the shape before you touch the prompt.",
            "Example: DataPilot's row cap and call limits sit in its pack's settings, so changing "
            "them needs no code.",
            'Ask the room: Only if ahead of the clock: "Which item would take you longest?" '
            "Expect: the envelope, because downstream code reads prose today.",
            "Misconceptions: That this needs a new framework. Each item changes tools and "
            "middleware you already have.",
            "Transition: Before the recap, the mistakes teams repeat here.",
        ],
    ),
    # 12 pitfalls -------------------------------------------------------------------------------
    dict(
        kind="pitfalls",
        title="Pitfalls that waste context or hide answers",
        minutes=1.5,
        says="Four agent-loop mistakes, what each causes, and what to do instead",
        src="E14, E16, E19, E20 (docs/calibration-report.md, Agents on and off, Changes recorded; "
        "docs/benefits.md); deck sources [4], [49], [57]",
        on_slide=[
            "| Pitfall | What happens | Do instead |",
            "|---|---|---|",
            "| A limit only in the prompt | One result floods later calls | Cap rows, values in "
            "the tool |",
            "| Stack traces as tool errors | It guesses, or retries blind | Say what failed, what "
            "to try |",
            "| The whole schema in the prompt | Wasted tokens, wrong columns | List, describe on "
            "demand |",
            "| Prose, not an envelope | Nothing to check or re-run | Return a typed envelope |",
        ],
        notes=[
            "Purpose: Name the four agent-loop mistakes that cost the most, each with what it "
            "causes and the fix.",
            "What to say: Four pitfalls. First, a limit written only in the prompt. The model may "
            "obey, but a prompt cannot bound one tool result, as the token counter showed in the "
            "demo. Second, stack traces as tool errors. The model reads two hundred "
            "lines of trace, guesses at the cause, or retries the same call; one sentence that "
            "says what failed and what to try next lets it recover, Source 57. Third, the whole "
            "schema in the prompt. It works on a small warehouse and fails on a large one: "
            "tokens spent on every call, and the right column lost among hundreds, Source 49. "
            "Fourth, prose instead of an envelope: a sentence with no query cannot be re-run or "
            "checked. One more, from the helper pattern: a helper agent that was never measured "
            "off, which is the gap the schema helper still has in DataPilot: it stays on with no "
            "measured gain yet, so measure yours.",
            "The point to land: Every pitfall here looks careful; measure it before you trust it.",
            "Example: Asking whenever unsure is a fifth pitfall: early on, the fiscal year 2025 "
            "question came back as a clarifying question, which left the reviewer and the gold "
            "check nothing to check; the analyst now answers with stated assumptions.",
            'Ask the room: Only if ahead of the clock: "Which helper agent in your system was '
            'never measured off?" Expect: a router or a planner.',
            "Misconceptions: That more agents add reliability. They add calls, latency, and "
            "correlated errors when they share a model.",
            "Transition: Let me check what stuck: the recap, the scoreboard, and one question "
            "about a new tool.",
        ],
    ),
    # 13 recap with the scoreboard --------------------------------------------------------------
    dict(
        kind="recap",
        title="Recap: what can your agent see?",
        scoreboard=1,
        minutes=1.5,
        says="Three points to keep, the scoreboard, and one question about a support agent's tool",
        src="section-1-agent-loop/README.md; slides/design-system.md, The scoreboard",
        on_slide=[
            "- The agent sees only what its tools return",
            "- Cap every result in the tool, with a notice",
            "- Stops in code; the answer in an envelope",
            "Question: A support agent's ticket search can match 40,000 tickets. What should the "
            "tool return, and what stops the run?",
        ],
        notes=[
            "Purpose: Consolidate the agent loop, show the scoreboard, and check the patterns on a "
            "new kind of agent.",
            "What to say: The scoreboard: the agent sees enough, but the answer is still wrong. "
            "Now the question; thirty seconds in the chat. The answer: the tool returns the 20 "
            "most relevant tickets with only the fields the next step needs, such as the ticket "
            "number, subject, status, and date; the total count; and a notice: showing 20 of "
            "40,000, "
            "filter by customer or date. A failure returns one sentence on what to try. The run "
            "stops on limits in code, model calls, tool calls, and tokens, and ends in an envelope "
            "whose status can be needs clarification, asking for the customer. The reasoning: "
            "context is a budget, the notice steers the next step, and only code bounds a result "
            "or a run.",
            "The point to land: The same four patterns bound any agent's tools: return less, say "
            "what was cut, stop in code, answer in an envelope.",
            "Example: The confident wrong answer wrote its own assumption, calendar year 2025 in "
            "Coordinated Universal Time, into its envelope.",
            "Ask the room: the question on the slide. Expect: a cap and a notice; fewer name the "
            "fields to drop or the status to end in.",
            "Misconceptions: That a stated assumption makes the answer right. It makes the "
            "mistake visible; the verification loop has to catch it.",
            "Transition: So how do we catch a wrong answer that looks right? That is Section 2: "
            "Verification loop.",
        ],
    ),
]
