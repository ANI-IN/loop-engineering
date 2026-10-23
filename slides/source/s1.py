"""Section 1: Agent loop. Slide data for the rewritten outline (rules and checks in build.py)."""

FAILURE = (
    "An agent that cannot see the business rules behind a schema answers confidently and wrong, "
    "and nothing in its output shows where the number came from."
)
DEMOS = ["agent-simple-question", "agent-confident-wrong-answer", "agent-unbounded-rows"]
R = "<!-- refresh after the session: {} -->"
MEASURED = (
    "the simple question shown in 37 and 39 seconds; the confident wrong answer shown in 76 "
    "seconds, 76,981,355.95 dollars against gold 64,015,091.21 with 4 trap labels, while the second "
    "attempt got no gold check within 90 seconds (hardened the same night); retaken twice on 23 "
    "October, both shown, 72,394,572.08 dollars against gold with 3 trap labels each; unbounded "
    "rows, fixed half 19,661 and 17,298 tokens per run, planted half 183,639 and 185,727 tokens."
)
NUMBERS = [
    "Schema linking errors account for 68.3 percent of failures (500 sampled Spider examples, schema retrieved across all databases, DIN-SQL): Source 4, version 3, Appendix B.",
    "GPT-4 from 34.88 to 54.89 percent execution accuracy on the BIRD test set with knowledge evidence: Source 2, Table 2.",
    "BIRD size, 12,751 question-SQL pairs over 95 databases; on the test set with evidence, ChatGPT with chain-of-thought prompting 40.08 percent and GPT-4 54.89 percent, against humans 92.96 percent: Source 2, abstract and Table 2.",
    "Spider 2.0, 632 tasks: the best agent, built on o1-preview, solves 21.3 percent, while earlier GPT-4-based methods reach 91.2 percent on Spider 1.0 and 73.0 percent on BIRD: Source 3, abstract, introduction, and Table 5.",
    "LinkAlign, 33.09 percent on Spider 2.0-Lite with open-source models: Source 4.",
    "Row cap of 50 rows: `limits.row_cap` in pack.yaml.",
    "Token budget of 60,000 tokens per run: `budgets.tokens_per_run` in pack.yaml.",
    "12 model calls and 16 tool calls per run: `limits.model_call_limit` and `limits.tool_call_limit` in pack.yaml.",
    "Class model prices, gpt-6-luna at 0.10 dollars input, 0.01 cached input, and 0.50 dollars output per 1M tokens: `prices` in pack.yaml.",
    "Cost of one analyst run, about 0.001 dollars; between 5 and 8 of every 10 input tokens served from the prompt cache: docs/calibration-report.md, Spend.",
    "Output cap per model call, reasoning included: 16,000 tokens for the analyst, 8,000 for the schema scout: `models` in pack.yaml.",
    "The 10,000-row result in the unbounded rows demo: the demo registry; the fixed half used 17,298 and 19,661 tokens per run, the planted half 183,639 and 185,727 tokens per run: docs/calibration-report.md, Demos and Resumed after the ledger correction.",
    "Mean tokens and seconds per question over four questions: scout and reviewer on 8,648 and 24.2, scout off 3,853 and 12.8, reviewer off 5,786 and 12.8, both off 3,337 and 10.1; gold results identical in every configuration: docs/calibration-report.md, Agents on and off.",
    "Traps under the starting knowledge: 0 of 99 trap runs passed, every trap item 3 times: docs/calibration-report.md, Traps.",
    "The confident wrong answer, 76,981,355.95 dollars against gold 64,015,091.21 with 4 trap labels, in 76 seconds: docs/calibration-report.md, Demos; retaken twice, 72,394,572.08 dollars with 3 trap labels each: docs/calibration-report.md, Resumed without traces.",
]

SLIDES = [
    # 1 -----------------------------------------------------------------------------------------
    dict(
        kind="agenda",
        title="Agenda (Section 1 highlighted)",
        layout="concept",
        minutes=0.5,
        says="Section 1: Agent loop, then verification, event, and hill-climbing loops",
        src="section-1-agent-loop/README.md",
        container="step cards: four sections, the first highlighted",
        on_slide=[
            "1. Agent loop (now): what the agent can see, and what it returns",
            "2. Verification loop",
            "3. Event loop",
            "4. Hill-climbing loop",
        ],
        notes=[
            "Say: We start with the agent on its own, before anything checks it. You all know how to "
            "build a tool-calling agent, so we will not spend a minute on that. We spend the time on "
            "four design decisions that decide whether its answers can be trusted later: what the "
            "tools show, how much the tools return, what shape the answer takes, and when a second "
            "agent is worth its cost. Every later loop depends on these four. The verification loop "
            "can only check an answer that has a shape. The event loop can only route an answer whose "
            "status it can read. The hill-climbing loop can only improve rules the agent can actually "
            "use. So this section is the foundation, and its demo ends on a failure the next three "
            "sections exist to fix.",
            "Point at: the highlighted first row, then the three rows still to come.",
            'Likely question: "Is there a live demo in every section?" Answer: Yes, several per '
            "section, all on one demo slide near the end of the section, all live against the class "
            "model, with the code opened in the editor right after.",
            "Transition: Let me start with a story you have probably lived through in some form.",
        ],
    ),
    # 2 -----------------------------------------------------------------------------------------
    dict(
        kind="story",
        title="Failure story: the board-deck number",
        layout="diagram",
        minutes=2,
        says="Illustrative: asked for net revenue, the agent sums the wrong column over the wrong year",
        src="section-1-agent-loop/concepts.md",
        container="step cards: four numbered beats, then a lesson bar",
        on_slide=[
            "Illustrative",
            "1. **The ask**: Finance asks for net revenue in fiscal year 2025, for the board deck "
            "due that afternoon.",
            "2. **The tempting column**: the agent finds a total column on orders and sums it, tax "
            "and shipping included.",
            "3. **The wrong year**: it sums January to December; the fiscal year runs February to "
            "January, cancelled and internal orders left in.",
            "4. **The confident sentence**: one fluent line goes into the deck; a month later nobody "
            "can say where it came from.",
            "Lesson: the query ran without error; the meaning was wrong, and nothing showed it.",
        ],
        notes=[
            "Say: This story is illustrative, and the people are fictional. Priya, a finance manager at "
            "Harbor & Pine Outfitters, asks the analytics agent: what was our net revenue in fiscal "
            "year 2025? Beat one. The agent lists the tables, which is exactly what a good agent does. "
            "Beat two. It finds a column called `total_cents` on the orders table. The name fits the "
            "question perfectly. Beat three. It sums that column from January to December. But "
            "Harbor & Pine's fiscal year runs February to January, and `total_cents` includes tax and "
            "shipping. Cancelled orders, which carry an undocumented status code, are still in. So are "
            "the warehouse team's test orders, placed from internal accounts. Beat four. The answer "
            "comes back as one fluent, confident sentence. It goes into a board deck. A month later "
            "someone asks where the number came from, and nobody can say, because the agent returned "
            "prose, not a query anyone could inspect.",
            "Point at: the four beats, top to bottom; pause on beat four, then read the lesson bar.",
            'Likely question: "Would an experienced analyst have caught it?" Answer: Only one who '
            "already knew every rule. The sentence reads well, and the query ran without error. "
            "Nothing failed; the meaning was wrong.",
            "Transition: So the tempting fix is obvious: use a bigger model.",
        ],
    ),
    # 3 -----------------------------------------------------------------------------------------
    dict(
        kind="question",
        title="Agent loop: will a stronger model fix the revenue number?",
        layout="concept",
        minutes=2.5,
        says="KEY IDEA: No. The rules are not in the schema; tools expose the error, gated knowledge fixes it",
        src="section-1-agent-loop/README.md",
        container="key-idea box, then three reason cards",
        on_slide=[
            "KEY IDEA: No. The rules are not in the schema. Better tools expose the error; gated "
            "knowledge fixes it.",
            "- Knowledge, not the model: GPT-4 rises from 34.88 to 54.89 percent on the BIRD test "
            "set once it gets domain evidence.",
            "- Real schemas are harder: GPT-4 methods reach 91.2 percent on Spider 1.0; the best agent "
            "solves 21.3 percent of Spider 2.0.",
            "- No temperature dial: reasoning models reject a custom temperature, so consistency "
            "comes from knowledge and measurement.",
        ],
        notes=[
            "Say: No. A stronger model reads the same schema, and the rules that define net revenue "
            "and fiscal year are not in it. The research is blunt about this. Source 2: BIRD "
            "(https://arxiv.org/abs/2305.03111), in summary: its 12,751 question-SQL pairs ship with "
            "external-knowledge evidence, and with that evidence GPT-4 rises from 34.88 to 54.89 "
            "percent on the BIRD test set. The model did not change; the knowledge did. Source 3: "
            "Spider 2.0 (https://arxiv.org/abs/2411.07763), in summary: on enterprise workflows the best "
            "agent, built on o1-preview, solves 21.3 percent of tasks, while earlier GPT-4-based "
            "methods reach 91.2 percent on Spider 1.0. Real "
            "schemas are bigger and messier than benchmarks. And there is one more reason a bigger "
            "model is no shortcut to consistency: reasoning models reject a custom temperature, so you "
            "cannot turn randomness down. Consistency has to come from knowledge you control and from "
            "measurement. So this section improves the tools first, and makes every answer "
            "inspectable. The rules arrive in Section 4: Hill-climbing loop, behind a gate.",
            "Point at: the KEY IDEA box, then the three reasons in order.",
            'Likely question: "Why not write the rules into the prompt now?" Answer: Rules written '
            "without measurement fit the cases you tried. We will earn them, and measure them on "
            "questions the rule writer never saw.",
            "Transition: Concept one: how the agent sees the schema at all.",
        ],
    ),
    # 4 -----------------------------------------------------------------------------------------
    dict(
        kind="concept",
        title="1) Schema linking: tools are how the agent sees",
        layout="table",
        minutes=4.5,
        says="Principle: the agent can only link words to columns its tools let it see",
        src="section-1-agent-loop/concepts.md",
        table=True,
        container="two-column cards: how it works | worked example; trade-off and at-work lines; key-idea bar",
        on_slide=[
            "Principle: the agent links words to columns only through what its tools show.",
            "Think of it as onboarding: a data dictionary and a few rows beat a list of table names.",
            "| How it works | Worked example |",
            "|---|---|",
            "| Linking maps question words to tables, columns, values | Names only: status is just a number |",
            "| It happens before SQL, and SQL inherits its errors | Distinct values: status has few codes |",
            "| Linking errors: 68.3 percent of failures (LinkAlign, Spider sample) | Still hidden: February fiscal year |",
            "Trade-offs: every field shown costs tokens; samples also carry text the model may follow.",
            "At work: audit what each tool returns before tuning the prompt.",
            "Key idea: the agent cannot use what its tools do not show.",
        ],
        notes=[
            "Plain explanation: Schema linking is the step where the agent maps the words in a "
            "question, like revenue or cancelled, onto tables, columns, and values. It happens "
            "before any SQL is written, and every later step inherits its mistakes. The agent links "
            "only through what its tools return, so tool output design is schema-linking design.",
            "Concrete example from DataPilot: Our describe tool returns column types, nullability, "
            "neutral comments, three sample rows, and the distinct values of low-cardinality columns. "
            "With the planted names-only schema bug (`BUG_NAMES_ONLY_SCHEMA`) it returns names only. "
            "Then a smallint status column looks like any number. With distinct values shown, the "
            "agent sees a handful of codes and can at least ask what they mean.",
            "Analogy: A new hire given only a list of table names writes worse queries than one given "
            "a data dictionary and a few example rows. Same person, different onboarding.",
            "Under the hood: Showing more costs tokens, so the design is selective. Types and comments "
            "are cheap and always useful. Samples are capped at three rows. Distinct values appear "
            "only for low-cardinality columns, where they reveal a coding. Notice what stays "
            "invisible: no tool can show that the fiscal year starts in February, because that rule "
            "lives in people's heads. That is why the confident wrong answer survives good tools. "
            "Enterprise benchmarks show the cost of weak linking: GPT-4-based methods reach 91.2 "
            "percent on Spider 1.0, while the best agent, built on o1-preview, solves 21.3 percent "
            "of Spider 2.0 (Source 3). LinkAlign measured the "
            "share directly: on 500 randomly sampled Spider examples, with the schema retrieved "
            "across all databases and fed to DIN-SQL, schema linking errors were the main cause of "
            "failures.",
            "Source 4: LinkAlign, version 3 (https://arxiv.org/html/2503.18596v3), Section 2 error "
            'analysis: "schema linking errors are the main cause of Text-to-SQL failures", with an '
            'error rate greater than 60 percent; Appendix B: "schema linking errors account for '
            '68.3% of Text-to-SQL failures".',
            "Transfer: Any agent over an API, a codebase, or a document store has the same step. "
            "Before tuning prompts, audit what each tool returns: is the field the agent needs "
            "visible, typed, and exemplified? Fix the view before the reasoning.",
            "Point at: the left column, then the worked example column top to bottom: names only, "
            "distinct values, and the rule that stays hidden; then the key-idea bar.",
            'Ask: "Which worked-example line would have saved the cancelled-orders trap?" Expected: '
            "distinct values; they show the status column is a code, though not what each code "
            "means.",
            'Likely question: "Do sample rows leak data to the model?" Answer: They send a few '
            "warehouse rows into the context. Personal-data columns are tagged, and queries that "
            "touch them route to human approval in the verification loop.",
            'Likely question: "Why not send the whole schema up front?" Answer: On a large schema it '
            "floods the context with irrelevant tables. Describing on demand keeps the context about "
            "the question.",
            'Misconception: "A better model links better, so the tool output matters less." '
            "Correction: A better model reasons better about what it sees. It still cannot see what "
            "the tool withholds.",
            "Transition: Showing more is good. Receiving too much is the next problem.",
        ],
    ),
    # 5 -----------------------------------------------------------------------------------------
    dict(
        kind="concept",
        title="2) Context is a budget: cap at the tool",
        layout="diagram",
        minutes=4,
        says="Principle: the tool, not the prompt, bounds what reaches the model",
        src="platform/packs/datapilot_us/pack.yaml",
        table=True,
        container="two-column cards: how it works | worked example; trade-off and at-work lines; key-idea bar",
        on_slide=[
            "Principle: the tool, not the prompt, decides how much reaches the model.",
            "Think of it as handing a colleague a summary and a row count, not a printout of every "
            "order.",
            "| How it works | Worked example |",
            "|---|---|",
            "| Tool results are re-sent on every later model call | Uncapped: 10,000 rows, 183,639 to 185,727 tokens |",
            "| A cap returns 50 rows, the total count, a truncation notice | Re-sent on up to 12 model calls in one run |",
            "| The agent then aggregates in SQL or narrows the question | Capped: 17,298 to 19,661 tokens per run |",
            "Trade-offs: a cap can hide needed rows, so count and notice expose the truncation; "
            "too small a cap forces extra queries.",
            "At work: cap, count, and notice on every list-returning tool.",
            "Key idea: budgets in a prompt are hopes; budgets in a tool are facts.",
        ],
        notes=[
            "Plain explanation: Every token a tool returns stays in the conversation and is sent "
            "again on every later model call in the loop. So a large tool result is not a one-off "
            "cost; it is a tax on every remaining step. The place to bound it is the tool itself.",
            "Concrete example from DataPilot: The query tool returns at most 50 rows, the row cap in "
            "our pack settings, plus the total row count and a notice that the result was truncated. "
            "With the planted unbounded rows bug (`BUG_UNBOUNDED_ROWS`) a 10,000-row result goes "
            "straight to the model, and you will watch the token counter jump in the demo.",
            "Analogy: You do not hand a colleague a printout of every order to ask about one trend. "
            "You hand them a summary and say how many rows there were.",
            "Under the hood: Measured with the planted bug on, the 10,000-row result took one run to "
            "183,639 tokens and a second run to 185,727, about ten times the capped run and three "
            "times our 60,000-token budget per run. The budget is checked before each model call, "
            "so the call that carried the rows crossed it and the next was stopped. At the class model's "
            "input price of 0.10 dollars per million tokens that is cheap per call, but the result "
            "is re-sent on each of up to 12 model calls in the run, and it pushes out the schema and "
            "the question. Measured with the cap on, the large query and its list question used "
            "17,298 and 19,661 tokens per run, well inside the budget. The cap keeps the cost small "
            "and, more important, keeps the reasoning about the question. The total count and the "
            "truncation notice matter as much as the cap: without them the agent may mistake 50 rows "
            "for the whole answer. The same idea bounds the output side: each model call has its "
            "own output cap, 16,000 tokens for the analyst, reasoning included, and a response cut "
            "off at it ends the run escalated with the reason.",
            "Source 7: LangChain SQL agent (https://docs.langchain.com/oss/python/langchain/sql-agent), "
            "in summary: the official tutorial bounds results with a prompt instruction to limit "
            "queries, which is a request to the model rather than a property of the tool.",
            "Transfer: Put a cap, a count, and a truncation notice on every tool that can return a "
            "list: search results, log lines, files, API pages. Let the agent ask for the next page "
            "if it needs it. Budgets in the prompt are hopes; budgets in the tool are facts.",
            "Point at: the how-it-works column first, then the worked example: uncapped, re-sent "
            "on every call, capped and measured; both figures are measured; end on the "
            "key-idea bar.",
            'Ask: "What should the agent do when it sees the truncation notice?" Expected: '
            "aggregate in SQL instead of reading rows, or ask a narrower question.",
            'Likely question: "Why 50 rows?" Answer: It is a setting, chosen so a list question '
            "fits comfortably. Change the setting, not the code; the principle is that a cap exists.",
            'Likely question: "Does the cap ever give a wrong answer?" Answer: Only if the agent '
            "ignores the notice. That is why the count and the notice travel with the rows.",
            'Misconception: "Large context windows remove the need for caps." Correction: A large '
            "window raises the ceiling, not the quality. Irrelevant rows still dilute attention and "
            "still cost money on every call.",
            "Re-check after live runs: the capped figures, 17,298 and 19,661 tokens per run, and the "
            "uncapped figures, 183,639 and 185,727 tokens per run, against the evidence page.",
            "Transition: Now the other side of the loop: what the agent hands back.",
        ],
    ),
    # 6 -----------------------------------------------------------------------------------------
    dict(
        kind="concept",
        title="3) Structured output is a contract",
        layout="diagram",
        minutes=4,
        says="Principle: a structured answer can be checked; a sentence cannot",
        src="platform/src/datapilot/contracts/answer.py",
        table=True,
        container="two-column cards: how it works | worked example; trade-off and at-work lines; key-idea bar",
        on_slide=[
            "Principle: a structured answer can be checked; a sentence cannot.",
            "Think of it as a pull request with a diff, not a chat message saying it is fixed.",
            "| How it works | Worked example |",
            "|---|---|",
            "| Provider-native: the provider returns the schema | Envelope: status, final SQL, rows, assumptions |",
            "| Tool-based: a required tool call carries the schema | Status: answered, needs clarification, refused, escalated |",
            "| An invalid answer goes back to the model as an error | Board-deck story: the SQL field shows the calendar year |",
            "Trade-offs: retries spend model calls; a valid shape can still hold a wrong meaning.",
            "At work: give every agent that feeds software a schema with statuses for not answering.",
            "Key idea: output other code reads needs a contract, not prose.",
        ],
        notes=[
            "Plain explanation: The agent's final output is an interface. Other code reads it: "
            "graders, routers, evaluators, a channel post. An interface needs a schema, and a schema "
            "needs enforcement. Free text is an interface only a human can read.",
            "Concrete example from DataPilot: Every run returns an answer envelope: a status, the "
            "final SQL, columns, a rows preview, the row count, the answer text, the assumptions the "
            "agent made, and a clarifying question when one is needed. The status has four values: "
            "answered, needs clarification, refused, escalated. Every later loop reads these fields. "
            "In the board-deck story, the SQL field alone would have let someone see the calendar "
            "year in the WHERE clause. One rule came from calibration: the analyst answers with its "
            "assumptions stated and recorded, and asks for clarification only when a question names "
            "nothing in the schema. Early on, the spine question came back as a clarifying question, "
            "which left the reviewer and the gold check nothing to check.",
            "Analogy: A pull request with a diff against a message in chat saying it is fixed. Both "
            "may be true; only one can be reviewed.",
            "Under the hood: There are two enforcement strategies. Provider-native structured output "
            "asks the model provider to return the schema directly, where the model supports it. The "
            "tool-based strategy presents the schema as a tool the model must call; with error "
            "handling on, a validation failure goes back to the model as an error message and it "
            "tries again. A bare schema lets the framework pick by model profile. Either way the "
            "contract also helps consistency. Reasoning models reject a custom temperature, so you "
            "cannot buy determinism with a sampling setting. A fixed output shape, explicit "
            "assumptions, and repeated measurement are what you control.",
            "Source 6: Temperature in GPT-5 models "
            "(https://community.openai.com/t/temperature-in-gpt-5-models/1337133), in summary: "
            "developers report that GPT-5 reasoning models reject a custom temperature value.",
            "Source 5: LangChain structured output "
            "(https://docs.langchain.com/oss/python/langchain/structured-output), in summary: the "
            "response format takes a tool strategy, with optional error handling, or a provider "
            "strategy, and the result arrives as the structured response.",
            "Transfer: Give every agent that feeds other software an output schema with a status "
            "field, including statuses for not answering. Record assumptions as a list, not prose. "
            "Return validation errors to the model instead of crashing.",
            "Point at: the two strategies on the left, then the status values on the right: two of "
            "the four are ways of not answering; end on the key-idea bar.",
            'Ask: "Why does the envelope include needs clarification and refused?" Expected: so '
            "not answering is a legal, checkable outcome instead of a guess.",
            'Likely question: "Which strategy should I choose?" Answer: Provider-native where your '
            "model supports it; the tool strategy for portability across models. Measure the retry "
            "rate either way.",
            'Likely question: "Does a schema guarantee a correct answer?" Answer: No. It makes it '
            "checkable. Section 2: Verification loop does the checking.",
            'Misconception: "Structured output is just JSON formatting." Correction: It is a '
            "contract with enforcement and a retry path, and it decides what downstream code can "
            "verify.",
            "Transition: One more design decision: whether a second agent belongs here at all.",
        ],
    ),
    # 7 -----------------------------------------------------------------------------------------
    dict(
        kind="concept",
        title="4) A subagent must earn its place",
        layout="diagram",
        minutes=4.5,
        says="Principle: add an agent only where judgement is needed, keep it stateless, and measure it",
        src="platform/src/datapilot/contracts/agents.py",
        table=True,
        container="labelled diagram: analyst, tool boundary, scout, brief; worked-example card; key-idea bar",
        on_slide=[
            "Principle: add an agent only where judgement is needed; keep it stateless; measure it.",
            "Think of it as a specialist who answers a written question with a one-page memo.",
            "How it works:",
            "- The analyst calls one tool, scout schema, with the question only",
            "- The scout explores tables in its own context, then forgets",
            "- It returns a short brief: candidate tables, joins, caveats",
            "- The brief is advice; the analyst still describes tables itself",
            "Worked example: mean of four questions, scout and reviewer on, 8,648 tokens and 24 "
            "seconds; scout off, 3,853 and 13; same gold results.",
            "Trade-offs: one more model call and more latency per question.",
            "At work: name the judgement, the stateless input, and the short output before adding "
            "an agent.",
            "Key idea: a subagent pays off only as a context boundary you have measured.",
        ],
        notes=[
            "Plain explanation: Multi-agent designs are easy to draw and expensive to run. Each agent "
            "adds model calls, latency, and a new place for errors. A subagent earns its place when "
            "it does a judgement task the main agent does badly, inside a clean context boundary, at "
            "a cost you have measured.",
            "Concrete example from DataPilot: The analyst is one agent with three tools: list tables, "
            "describe a table, run a query. Its knowledge is injected by a dynamic prompt. The schema "
            "scout sits behind a fourth tool: the analyst calls it with the question, and the scout "
            "returns a schema brief of candidate tables, joins, and caveats. The scout is stateless. "
            "It sees only the question and the schema, never the conversation, and it can be switched "
            "off in the pack settings.",
            "Analogy: A specialist you consult with a written question and who sends back a one-page "
            "memo, rather than a colleague who joins every meeting.",
            "Under the hood: The stateless boundary is the point. The scout's exploration, every "
            "table it described and rejected, stays in its own context. The analyst receives only "
            "the brief, so its context stays about the question. That is the same budget argument as "
            "concept two, applied to reasoning instead of rows. The cost is real: an extra model "
            "call per question and more latency. Whether it pays off is an empirical question, so "
            "calibration measured it on four questions, once per configuration. With the scout and "
            "the reviewer on, a question averaged 8,648 tokens and 24.2 seconds; with the scout off, "
            "3,853 tokens and 12.8 seconds; with both off, 3,337 and 10.1. The gold results were "
            "identical in every configuration. On the two easy questions the scout was rarely "
            "called; the gap came from the two trap questions, where the reviewer's concerns sent "
            "the analyst back. Four questions are a small sample, so read it as a direction, not a "
            "verdict: on these four questions the scout changed no gold result. Notice what we did "
            "not do: no supervisor, no agent per table, no debate.",
            "Source 1: The art of loop engineering "
            "(https://www.langchain.com/blog/the-art-of-loop-engineering), in summary: the agent loop "
            "is the base of the four loops, and the others wrap it rather than replace it.",
            "Transfer: Before adding an agent, write down the judgement it makes, the context it "
            "needs, and what it returns. If you cannot name a stateless input and a short output, it "
            "is probably a tool or a step, not an agent. Then measure with it on and off.",
            "Point at: the four how-it-works points in order: the question going in, the private "
            "exploration, the short brief coming back, the brief as advice; then the worked "
            "example and the key-idea bar.",
            'Ask: "What would break if the scout kept memory across questions?" Expected: its '
            "answers would depend on earlier questions, which makes them harder to test and to "
            "trust.",
            'Likely question: "Why not a team of agents here?" Answer: Only table selection needs '
            "judgement. Everything else is deterministic and belongs in tools.",
            'Likely question: "What if the scout is wrong?" Answer: Its brief is advisory. The '
            "analyst still describes tables itself, and the verification loop checks the result.",
            'Misconception: "More agents give more reliability." Correction: More agents give more '
            "places to fail and correlated errors when they share a model. Reliability comes from "
            "checks, which is Section 2.",
            "Re-check after live runs: the scout's token and latency figures, 8,648 and 3,853 tokens, "
            "24.2 and 12.8 seconds, against the calibration report.",
            "Transition: The four moves on one slide.",
        ],
    ),
    # 8 -----------------------------------------------------------------------------------------
    dict(
        kind="cheat",
        title="Cheat sheet: the agent loop in four moves",
        layout="table",
        minutes=1,
        says="Show the schema well, cap results, return a contract, add agents only for judgement",
        src="section-1-agent-loop/README.md",
        table=True,
        container="table: move, principle, anti-pattern it prevents, check question",
        on_slide=[
            "| Move | Principle | Anti-pattern it prevents | Check question |",
            "|---|---|---|---|",
            "| Show the schema well | The agent links only what tools show | Names-only schema tools | Can the agent see types, samples, and codes? |",
            "| Cap at the tool | The tool bounds the context | Every row sent to the model | Does every list tool return a cap, count, and notice? |",
            "| Return a contract | Structured answers can be checked | A fluent sentence as output | Can code read the status and the SQL? |",
            "| Earn each subagent | Agents only for judgement, stateless | A crowd of agents by default | Have you measured it on and off? |",
        ],
        notes=[
            "Say: Four moves. Show the schema well, because linking is the bottleneck. Cap at the "
            "tool, because context is a budget paid on every call. Return a contract, because only "
            "a structured answer can be checked. Earn each subagent, by keeping it stateless and "
            "measuring it on and off.",
            "Point at: the check question column; these four questions are what to ask of your "
            "own agents.",
            'Likely question: "Which move matters most?" Answer: Showing the schema well; every '
            "later step depends on what the agent could see.",
            'Likely question: "Which one would you add first to an existing agent?" Answer: The '
            "output contract. It makes every other improvement measurable.",
            "Transition: Now watch all four live, and watch the spine question still come out wrong.",
        ],
    ),
    # 9 -----------------------------------------------------------------------------------------
    dict(
        kind="demo",
        title="Section 1: Agent loop - Implementation Notes: The confident wrong answer",
        layout="demo",
        minutes=17,
        says="Badge DEMO - 1 and title only; the demos are in the notes",
        src="section-1-agent-loop/demo/walkthrough.md",
        container="demo layout: badge and title only",
        on_slide=["Badge: DEMO - 1", "Title only; no screenshot"],
        notes=[
            "Run sheet: about 12 minutes for three core demos on the console Agent page, then about 5 "
            "minutes of code walkthrough in the editor. Share the console full screen; keep the "
            "editor and a terminal in separate windows. Calibration ran each core demo twice with a "
            "reset between; the measured times are under each demo.",
            "Demo: the simple question.",
            "Starting state: the Agent page, knowledge version v1 active, no planted item on, the "
            "status line at the report-only level. Reset first: `make reset NAME=agent-loop`.",
            "Do: Agent > Ask, type a plain count question such as how many orders shipped to Texas "
            "in fiscal year 2025, then Run; or `make demo NAME=agent-simple-question`.",
            "Narrate: this is the loop working as designed. Tie it to concept 1, Schema linking: "
            "watch the analyst list tables, describe one, and see types, samples, and distinct "
            "values before it writes SQL. Tie it to concept 3, Structured output is a contract: the "
            "answer comes back as an envelope with its SQL.",
            "Point at, in order: the tool timeline (list tables, describe table, run query, each "
            "with its duration); the envelope's status and final SQL; the tokens and cost; and last "
            "the live stamp: the run's start time in your local time and its trace link.",
            "Expected live result: a correct count with its SQL, tokens, cost, and a LangSmith trace "
            "link. Measured: 37 and 39 seconds from trigger to result; one analyst run costs about "
            "0.001 dollars.",
            "May vary: the analyst's wording, the number of tool calls, latency, tokens. If it does, "
            "say: the path varies run to run because the model reasons freshly each time; the "
            "contract and the SQL are what we check.",
            "If it stalls: reset and run it again, `make reset NAME=agent-loop`, then the same "
            "trigger.",
            "Demo: the confident wrong answer.",
            "Starting state: the same page after the first demo; knowledge version v1 still active. "
            "Reset first if anything else ran: `make reset NAME=agent-loop`.",
            "Do: Agent > Ask the spine question, or `make demo NAME=agent-confident-wrong-answer`.",
            "Narrate: the spine question, what was our net revenue in fiscal year 2025. Tie it to "
            "the question slide: a stronger model would not help, because the rules are not in the "
            "schema. Tie it to concept 1: the tools showed everything they could, and the fiscal "
            "year rule is still invisible.",
            "Point at, in order: the confident answer text; the answer-versus-gold ledger showing "
            "the mismatch; the annotated SQL, where each note names a trap behind a fragment (the "
            "calendar year, `total_cents`, cancelled orders left in, internal accounts left in); and "
            "last the live stamp: the run's start time in your local time and its trace link.",
            "Expected live result: a mismatch against gold with at least one trap note on the SQL. "
            "Measured: in 76 seconds, 76,981,355.95 dollars against gold 64,015,091.21, with 4 trap "
            "labels; retaken twice, both shown, 72,394,572.08 dollars with 3 trap labels each, then "
            "held by two reviewer concerns; under the starting knowledge 0 of 99 trap runs passed in "
            "calibration.",
            "May vary: which traps the SQL hits, the wrong value, the wording, and whether the run "
            "posts or holds. If it does, say: the exact mistake varies, the fact of a mistake does "
            "not, because the knowledge it needs is absent. If the strip shows held for approval, "
            "say: that is the reviewer from Section 2: Verification loop raising a concern, which it "
            "did on this answer in calibration; the gold check still shows the mismatch.",
            "If it stalls: reset and run it again, `make reset NAME=agent-loop`, then the same "
            "trigger. In calibration the second attempt got no gold check within 90 seconds; the gold "
            "checks were hardened the same night so one run can never block another, and both "
            "retakes got their gold check.",
            "Demo: unbounded rows.",
            "Starting state: the Agent page; the unbounded rows bug (`BUG_UNBOUNDED_ROWS`) switched "
            "on, its chip visible on the status line. Reset first: `make reset NAME=agent-loop`.",
            "Do: Agent > Run large query, or `make demo NAME=agent-unbounded-rows`. Then set "
            "`BUG_UNBOUNDED_ROWS=0` in `.env`, run `make up` so the services read it, and run it "
            "again. Before class the flag was set to 1 the same way.",
            "Narrate: tie it to concept 2, Context is a budget. With the bug on, a 10,000-row result "
            "goes to the model and every later call carries it. With it off, the tool returns the "
            "row cap, the total count, and the truncation notice.",
            "Point at, in order: the token counter with the bug on; the same counter with it off; "
            "the truncation notice and the total count under the rows; and last the live stamp: the "
            "run's start time in your local time and its trace link.",
            "Expected live result: tokens per run jump with the bug on and drop back with it off. "
            "Measured with the bug on: 183,639 and 185,727 tokens per run, stopped by the run budget "
            "after 18 or 19 seconds. With the bug off: 19,661 and 17,298 tokens per run; one of the "
            "two runs was held by a reviewer concern, which does not change the token story.",
            "May vary: exact token counts, the list question's wording. If it does, say: the size of "
            "the jump depends on the rows, but the direction never changes.",
            "If it stalls: reset and run it again, `make reset NAME=agent-loop`, then the same "
            "trigger.",
            "Optional, cut first: Texas last quarter (`make demo NAME=agent-texas-last-quarter`), a "
            "four-table join for Texas customers over the last completed fiscal quarter, August to "
            "October 2025 against the business date of 31 January 2026, with the join path "
            'visible in the SQL. Say "last completed fiscal quarter": on 31 January the current '
            "fiscal quarter is still open.",
            "Code walkthrough: about 5 minutes, in the order of the section's demo walkthrough page.",
            "Open `platform/src/datapilot/loop1_agent/analyst.py`, lines 56-58: the knowledge "
            "injection, the base of concept 1, Schema linking, and of the confident wrong answer. "
            "Say: the dynamic prompt writes the base prompt, the business date, and the active "
            "knowledge version before every model call; under v1 that block holds only the money "
            "rule, so the traps decide the answer. A new version changes this block and nothing "
            "else.",
            "Open `platform/src/datapilot/loop1_agent/analyst.py`, lines 72-86: implements concept "
            "3, Structured output is a contract, and the stops of concept 2. Say: one "
            "`create_agent` call; `ToolStrategy(AnswerEnvelope)` makes the answer a typed object the "
            "graders read; the model call limit ends the run at 12 calls and the tool call limit "
            "answers extra calls with an error at 16; `*middleware` is where later loops add the run "
            "guard, the kill switch, and approvals.",
            "Open `platform/src/datapilot/loop1_agent/tools.py`, lines 33-54: implements concept 2, "
            "Context is a budget, and is the unbounded rows demo. Say: the cap lives in the tool, "
            "so no prompt wording can lift it; the result carries the total row count and a notice "
            "that tells the model what to do next; `cap_values` cuts any value longer than 2,000 "
            "characters, because one row can hold an array of every address; the planted branch for `BUG_UNBOUNDED_ROWS` is one "
            "guarded line, never a fake model output.",
            "If time allows, the same file's describe tool shows concept 1: types, three sample "
            "rows, and distinct values; and concept 4's scout sits behind one more tool. Neither has "
            "a line range on the walkthrough page, so open them by name only if asked.",
            "Transition: Questions before we add the verification loop.",
        ],
    ),
    # 10 ----------------------------------------------------------------------------------------
    dict(
        kind="questions",
        title="Questions",
        layout="concept",
        minutes=3,
        says="No Question Is Too Small Every Question Deserves an Answer!! Two likely questions",
        src="-",
        container="fixed question layout",
        on_slide=[
            "No Question Is Too Small Every Question Deserves an Answer!!",
            "Why not put the rules in the prompt? Does the scout pay for itself?",
        ],
        notes=[
            "Say: Take questions. Two likely ones are on the slide; send anything long to the "
            "Thursday parking lot.",
            "Point at: the two questions on the slide.",
            'Likely question: "Why not put the business rules in the prompt now?" Answer: Because '
            "we want to show what earning them looks like. The starting knowledge version is almost "
            "empty on purpose, so every trap fails in class and the hill-climbing loop has "
            "something to improve and measure.",
            'Likely question: "Does the scout cost more than it saves?" Answer: On four questions '
            "it changed no gold result, and the runs with it on cost more tokens and seconds. "
            "On a schema with hundreds of tables the answer can flip, which is the point of measuring "
            "with it on and off.",
            'Likely question: "Why not ask the model to double-check its own SQL?" Answer: That is '
            "the same model grading itself. Section 2 puts deterministic checks first.",
            "Transition: If time is short, skip the reference slides and go to Section 2: "
            "Verification loop.",
        ],
    ),
    # 11 ----------------------------------------------------------------------------------------
    dict(
        kind="reference",
        title="Reference: skip if short on time - tool output design",
        layout="table",
        minutes=1,
        says="What a schema tool should show and withhold, and why sample rows cut both ways",
        src="section-1-agent-loop/concepts.md",
        table=True,
        container="table with a how-to-read line",
        on_slide=[
            "How to read this: each row is one choice; the last column says what it buys or risks.",
            "| Show | Withhold | Why |",
            "|---|---|---|",
            "| Types, comments | Internal notes | Cheap, always useful |",
            "| Three sample rows | Bulk rows | Formats help; text can inject |",
            "| Distinct values, small columns | Distinct values, large columns | Reveals codes cheaply |",
            "| Total count, truncation notice | Rows past the cap | Honest about size |",
        ],
        notes=[
            "Plain explanation: Every tool result is a design choice between helping the agent link "
            "words to data and spending its context. This table is the checklist we used.",
            "Concrete example from DataPilot: A few product names in the warehouse carry "
            "prompt-injection text, such as a request to delete data. Sample rows show them to the "
            "model. That is the double edge: the same rows that teach formats also carry text the "
            "model may follow.",
            "Analogy: Showing a contractor the building plans helps them work; it also shows them "
            "where the safe is. You give the plans and still lock the safe.",
            "Under the hood: Withholding is not the defence against injection; the defence is that "
            "nothing the model writes can modify data. The read-only role and the syntax-tree guard "
            "in Section 2: Verification loop render an injected instruction harmless, and a security "
            "suite proves no write happens. So we keep samples small and keep the hard boundary "
            "below the model.",
            "Source 4: LinkAlign, version 3 (https://arxiv.org/html/2503.18596v3), Appendix B: "
            '"schema linking errors account for 68.3% of Text-to-SQL failures".',
            "Transfer: For any tool that returns external content, such as web pages, tickets, or "
            "emails, assume the content can carry instructions. Show what helps, and put the "
            "boundary in permissions, not in the prompt.",
            "Point at: the sample rows row and its last cell.",
            'Ask: "Would you remove sample rows to stop injection?" Expected: no; keep them small and '
            "block writes below the model.",
            'Likely question: "How many samples are enough?" Answer: Three shows formats without '
            "spending much context; more rarely adds information.",
            'Likely question: "Should comments explain business rules?" Answer: Neutral comments '
            "only. Business rules belong in versioned knowledge you can gate and roll back.",
            'Misconception: "Hiding data from the model makes it safe." Correction: Safety comes '
            "from what the model is allowed to do, not from what it is allowed to see.",
            "Transition: Next reference: strategies for structured output.",
        ],
    ),
    # 12 ----------------------------------------------------------------------------------------
    dict(
        kind="reference",
        title="Reference: skip if short on time - structured output strategies",
        layout="table",
        minutes=0.5,
        says="Provider-native, tool-based, and prompt-only output: how each enforces and fails",
        src="section-1-agent-loop/concepts.md",
        table=True,
        container="table with a how-to-read line",
        on_slide=[
            "How to read this: rows run from strongest to weakest enforcement; read the failure "
            "mode before you choose.",
            "| Strategy | Enforced by | Failure mode |",
            "|---|---|---|",
            "| Provider-native | The model provider | Not every model supports it |",
            "| Tool-based | A required tool call | Validation error, model retries |",
            "| Prompt-only JSON | Nothing | Parse errors, silent drift |",
        ],
        notes=[
            "Plain explanation: There are three ways to get a structured answer from a model, and "
            "they differ in who enforces the shape and what happens when it breaks.",
            "Concrete example from DataPilot: The answer envelope is requested through the "
            "framework's response format. The analyst's output either validates as an envelope or "
            "the validation error goes back to the model for another attempt, inside the run's call "
            "limits.",
            "Analogy: A typed function signature, a runtime validator, and a comment saying please "
            "return a dictionary.",
            "Under the hood: Provider-native output asks the provider to return the schema directly "
            "where the model supports it. The tool strategy turns the schema into a tool the model "
            "must call; with error handling on, a validation failure becomes a message the model can "
            "fix. A bare schema lets the framework choose by model profile. Prompt-only JSON has no "
            "enforcement and no retry path, so failures surface downstream. Every retry counts "
            "against the run's 12 model calls.",
            "Source 5: LangChain structured output "
            "(https://docs.langchain.com/oss/python/langchain/structured-output), in summary: tool "
            "strategy with optional error handling, provider strategy, or a bare schema chosen by "
            "model profile.",
            "Transfer: Choose provider-native when your model supports it, the tool strategy when "
            "you need portability, and never prompt-only for output other code reads. Log the retry "
            "rate.",
            "Point at: the failure mode column.",
            'Ask: "Which strategy hides failures longest?" Expected: prompt-only JSON.',
            'Likely question: "Do retries hide a bad prompt?" Answer: They can; a rising retry rate '
            "is a signal to fix the schema or the instructions.",
            'Likely question: "Can a valid envelope still be wrong?" Answer: Yes. Valid shape, wrong '
            "meaning is exactly the next section's problem.",
            'Misconception: "Schema validation proves correctness." Correction: It proves shape only.',
            "Re-check after live runs: the 12-call limit against the pack settings, and the "
            "analyst's output cap of 16,000 tokens per call.",
            "Transition: Last reference: the five traps.",
        ],
    ),
    # 13 ----------------------------------------------------------------------------------------
    dict(
        kind="reference",
        title="Reference: skip if short on time - five traps",
        layout="table",
        minutes=0.5,
        says="The five traps as categories of business knowledge a schema does not carry",
        src="platform/planted/registry.yaml",
        table=True,
        container="table with a how-to-read line",
        on_slide=[
            "How to read this: the category column names the kind of knowledge to look for in "
            "your own data.",
            "| Trap | Missing knowledge | Category |",
            "|---|---|---|",
            "| Fiscal year | February to January | Calendar convention |",
            "| Net revenue | Not the total column | Metric definition |",
            "| Cancelled orders | Status 5 excluded | Undocumented code |",
            "| Eastern time | Business day boundary | Time zone |",
            "| Internal accounts | Company email domain | Hidden population |",
        ],
        notes=[
            "Plain explanation: Each trap is a kind of business knowledge that real schemas rarely "
            "carry. Naming the category helps you find the same gaps in your own data.",
            "Concrete example from DataPilot: The fiscal year runs February to January and is named "
            "for its end year. Net revenue is subtotal minus discount, never `total_cents`, which "
            "includes tax and shipping. Cancelled orders carry an opaque status code 5. Business "
            "days are in Eastern time, so evening orders cross the UTC date. Internal accounts are "
            "known only by the company email domain; there is no flag column.",
            "Analogy: The unwritten rules a new analyst learns in their first month, usually by "
            "getting a number wrong in a meeting.",
            "Under the hood: Each trap was chosen so the schema gives no hint. The internal accounts "
            "trap uses an email domain because a visible flag column is solved unaided; internal "
            "accounts hold exactly 3 of the top 10 revenue spots in each fiscal year, about 2.49 "
            "percent of revenue on the main warehouse. Calibration "
            "ran every trap item three times under the starting knowledge, 99 runs, and none passed, "
            "so no trap needed strengthening. The labels most often attached to the wrong SQL were "
            "the missing internal-account filter, the missing status filter, the calendar-year range, "
            "and UTC truncation. This is the same gap BIRD's evidence fills: with it, GPT-4 "
            "rises from 34.88 to 54.89 percent on the BIRD test set.",
            "Source 2: BIRD (https://arxiv.org/abs/2305.03111), in summary: questions come with "
            "external-knowledge evidence, and all models improve when given it.",
            "Transfer: List the categories for your own domain: calendars, metric definitions, "
            "codes, time zones, hidden populations such as test accounts. Each is a candidate rule "
            "for a knowledge version.",
            "Point at: the category column.",
            'Ask: "Which category exists in your data?" Expected: usually test accounts and metric '
            "definitions.",
            'Likely question: "Why five traps?" Answer: Each changes a naive answer on its own, and '
            "together they cover the common categories.",
            'Likely question: "Is money in cents a trap?" Answer: No; the column suffix makes it '
            "visible, so it stays a rule, not a trap.",
            'Misconception: "Good naming would remove these." Correction: Names help with codes; '
            "they cannot carry a calendar or a metric definition.",
            "Transition: Section 2: Verification loop checks what the agent returns.",
        ],
    ),
]
