"""Section 1: Agent loop, 0:47 to 1:22, 35 minutes, 12 slides, under design system 3.

The schema is in slides/design-system.md, section "The third rebuild (design system 3)";
slides/source/samples3.py holds one slide of every type. The order is the reference deck's
rhythm: the agenda with the star on the agent loop, the failure story, the question slide, the
four techniques 1) to 4) with their pattern diagrams, the text-to-SQL design callout, the cheat
sheet, the DEMO slide, the Measured slide with the scoreboard, and Ask about anything. The second
rebuild's generic loop and DataPilot's query tool cap are told in the techniques' notes (design
system 3 has no code slide). Every course number comes from the deck evidence (.dev/deck-evidence.md
entries E1 and on, .dev/deck3-evidence.md, docs/benefits.md, docs/calibration-report.md, named in
each slide's src); every external claim from a shortlisted source, cited as [^n] on a slide and
"Source [^n]" in the notes: 4, 61, 62 and 65.
"""

RULES = "design system 3"

DEMO_PAGE = "https://github.com/ANI-IN/loop-engineering/tree/main/section-1-agent-loop/demo"
EXPECTED = "section-1-agent-loop/demo/expected/"

SLIDES = [
    # 27 agenda ---------------------------------------------------------------------------------
    dict(
        kind="agenda",
        title="Today's Agenda",
        minutes=0.5,
        says="The four loops, the star on the agent loop",
        src="the owner's specification of 27 October 2026, section 4, item 1",
        on_slide=[
            "1. Agent loop: what it sees",
            "2. Verification loop: is it right?",
            "3. Event loop: runs unattended",
            "4. Hill-climbing loop: improves safely",
            "Now: 1",
        ],
        notes=[
            "Purpose: Show where the class is: the first of the four loops.",
            "What to say: Four loops, one per section. The star is on the first: the agent loop, "
            "and what the agent can see. We start here because every later loop checks, runs or "
            "improves what this one produces. By the end of this section the agent will see "
            "enough, and you will see that seeing enough is not the same as being right.",
            "The point to land: The agent loop comes first: the other three work on its output.",
            "Example: The fiscal year 2025 revenue question runs through all four sections.",
            "Ask the room: none here; the question comes at the end of the section.",
            "Misconceptions: That the loops are layers of one prompt. Each loop is code around "
            "the same model.",
            "Transition: Here is the failure this section fixes.",
        ],
    ),
    # 28 failure story ----------------------------------------------------------------------------
    dict(
        kind="failure",
        title="Failure story: 10,000 rows, three run budgets, no answer",
        minutes=2.5,
        says="Five steps from a request to a run that spends three run budgets and answers nothing",
        src=".dev/deck3-evidence.md, part 1, Tuesday, part 2 (the demo question, 182,654 to "
        "187,030 tokens in 6 runs, the run budget checked before each call, the run "
        "escalated); E16, E17; platform/src/datapilot/loop1_agent/guard.py line 59 (spent "
        "tokens only); docs/evidence/section-1-agent-loop.md, Results; docs/benefits.md, "
        "Section 1; lead rulings 6, 14 and 20 of review round 1",
        on_slide=[
            "Lead: An illustrative question: run a query of 10,000 rows, then list the ten "
            "latest orders.",
            "1. A request asks the agent to query 10,000 rows first.",
            "2. Nothing cuts the result: every row goes to the model.",
            "3. The next model call carries every row as input.",
            "4. Code counts spent tokens only; that call overshoots.",
            "5. Escalated, no answer, and three run budgets gone.",
        ],
        notes=[
            "Purpose: Walk the illustrative path from a reasonable request to a run that spends "
            "three run budgets and answers nothing, each step causing the next.",
            "What to say: This story is illustrative, built from Tuesday in the week of "
            "failures, and its numbers come from the course's runs. Step one: an analyst wants "
            "the ten latest orders, and the request also tells the agent to run a query that "
            "returns 10,000 rows first. Real requests do this by accident: select everything, "
            "then summarise. Step two: the query tool hands every row back to the model. Nothing "
            "in the tool cuts the result, so the whole result becomes the tool's answer. Step "
            "three: those rows now sit in the context, and the next model call carries all of "
            "them as input tokens. Step four: the run budget is 60,000 tokens, and before each "
            "call DataPilot's code compares the tokens already spent with it. Spent was still "
            "under, so that one call goes out and overshoots the budget on its own. Step five, in "
            "red, is the costly end: the run is escalated, which means stopped and handed to a "
            "person with its reasons, at about 185,000 tokens, three run budgets, and the "
            "analyst gets no list. Nothing here was malicious, and the model did what it was "
            "told. The tool decided how much one call could carry, and it decided nothing. The "
            "general fix is to cap what the tool returns; where the platform allows, also count "
            "the next call's input before you send it.",
            "The point to land: Cap what a tool returns; a run budget that counts only spent "
            "tokens cannot stop one oversized call.",
            "Example: With the row cap switched off, six runs reached 182,654 to 187,030 tokens "
            "against the 60,000-token run budget and were escalated; capture run 199d2188 reached "
            "184,983. The request named the query, and the rows were order items.",
            'Ask the room: "Which of your tools could return ten thousand of anything?" Expect: '
            "search, logs, query tools, file listings.",
            "Misconceptions: That a larger context window solves this. It postpones it: every "
            "token is sent again, and paid for, on every later call in the run.",
            "Transition: So why not give the agent everything, the whole schema and all the "
            "rows, and let it sort them out?",
        ],
    ),
    # 29 question ---------------------------------------------------------------------------------
    dict(
        kind="question",
        title="Agent loop: Why not give it the whole schema and all rows?",
        minutes=2.5,
        says="The naive fix, give the agent everything, and three reasons it fails",
        src="the owner's specification of 27 October 2026, section 4, item 3; sources.py entry "
        "61; E16 (docs/benefits.md, Section 1: 182,654 against 30,216 tokens)",
        on_slide=[
            "Lead: The warehouse has five tables, and the model's context window holds far more "
            "than that.",
            "Key idea: Context is a budget: show what is needed, on demand, capped.",
            "1. A whole schema crowds out the question, and every call pays for it again",
            "2. One unbounded result can spend the whole run budget in a single call",
            "3. More context is not more knowledge: neither the schema nor the rows state the "
            "business rules",
        ],
        notes=[
            "Purpose: Answer the naive fix, give the agent everything, with the section's key "
            "idea and three reasons.",
            "What to say: Here is the obvious fix, and you may have heard it at work. Our "
            "warehouse is small, five tables. Why not paste the whole schema into the prompt and "
            "let every query return all its rows? The key idea says no: context is a budget. "
            "Show what is needed, on demand, and capped. Anthropic's guide to context "
            "engineering calls context a finite resource with diminishing returns, Source "
            "[^61]. Three reasons. One: a whole schema crowds out the question. A real warehouse "
            "has hundreds of tables; the right column is lost among the wrong ones, and every "
            "model call pays for all of them again. Providers cache a repeated prefix at a "
            "fraction of the price, so put the stable schema and rules first; caching lowers the "
            "bill, not the crowding. Two: one unbounded result can spend the whole run budget in "
            "a single call, which is the failure story you just saw. "
            "Three, and this one matters most: more context is not more knowledge. The schema "
            "shows every column named amount and still says nothing about the fiscal year, "
            "cancelled orders or internal accounts, and the rows do not say it either. Monday's "
            "wrong revenue answer would come back exactly as wrong, only slower and more "
            "expensive. So this section's job is not to show more. It is to design what the "
            "agent sees, when it sees it, and how much of it arrives.",
            "The point to land: Giving the agent everything costs more and fixes nothing that "
            "matters; design what it sees instead.",
            "Example: The same 10,000-row request took 182,654 tokens with no row cap and 30,216 "
            "with it, the reviewer's round trip included, one run a side (be82d6f6 and "
            "e1f21cf2).",
            'Ask the room: "How many tables does your warehouse have?" Expect: hundreds, which '
            "settles reason one.",
            "Misconceptions: That a long context window removes the budget. A long window still "
            "costs tokens on every call and still buries the column that matters.",
            "Transition: So what should the agent see? The first technique: the tools decide.",
        ],
    ),
    # 30 technique 1 ------------------------------------------------------------------------------
    dict(
        kind="technique",
        title="1) Tools decide what the agent sees",
        minutes=2.5,
        says="Schema linking by progressive disclosure: names first, details on demand",
        src="the owner's specification of 27 October 2026, section 4, item 4; "
        ".dev/review/deck3-diagrams-technique.md (pattern-progressive-disclosure); sources.py "
        "entries 4 and 62; E15 (docs/benefits.md, Section 1); section-1-agent-loop/README.md",
        figure={
            "diagram": "pattern-progressive-disclosure",
            "alt": "Progressive disclosure: list_tables for a small schema, every name and "
            "nothing more, or search_schema for a large one, retrieving the closest tables only; "
            "then describe_table on demand, the columns of the tables picked and nothing else; "
            "then the model writes the query with real table and column names; beside it, the "
            "failure this prevents: the whole schema up front fills the context, and the model "
            "guesses names",
        },
        on_slide=[
            "- **What:** the agent sees a warehouse only through its tools; their outputs are its "
            "whole view.",
            "- **How:** list names first, search them in a large schema, and describe only the "
            "tables picked.",
            "- **Example:** a column named amount says nothing; net of discount, in cents, says "
            "how to sum it.",
            "- **Elsewhere:** Agent Skills load each skill's name and description first, the rest "
            "on demand.[^62]",
            "Key idea: What a tool returns is all the agent knows; design that view before the "
            "prompt.",
        ],
        notes=[
            "Purpose: Teach the first technique: tools decide what the agent sees, through "
            "schema linking and progressive disclosure.",
            "What to say: The first technique is a change of mind. The agent never sees your "
            "warehouse. It sees what its tools return and nothing else, so designing the tools "
            "is designing what it can know. Schema linking maps the words of a question onto "
            "tables, columns and values; progressive disclosure is how the tools support it. "
            "Walk the diagram from left to right. First the names: for a small schema, a list of "
            "every table with one line each; for a large one, a search that returns only the "
            "closest tables. Then describe on demand: the columns of the tables the model picked, "
            "their types and what each one means. Only then does the model write the query, "
            "with real table and column names. On the right, the failure this prevents: the "
            "whole schema up front fills the context, and the model guesses names. The example "
            "on the slide matters for Monday: a column named amount says nothing, while net of "
            "discount, in cents, tells the agent how to add it up. The same design appears "
            "outside data agents. Anthropic's Agent Skills load each skill's name and "
            "description first and its body only when needed, Source [^62], and its guide to "
            "writing tools says to return what the task needs, Source [^4].",
            "The point to land: Design what the tools return before you touch the prompt; it is "
            "everything the agent knows.",
            "Example: DataPilot's describe tool returns each column's type and comment from the "
            "warehouse, three sample rows, and the values of columns that have only a few. Better "
            "descriptions, capped rows and the schema helper together took seven easy "
            "questions from 12 of 21 correct runs to 17 of 21.",
            'Ask the room: "What does your agent see when it lists your tables?" Expect: names '
            "only, or everything at once.",
            "Misconceptions: That descriptions fix the business rules. They help easy questions; "
            "the fiscal year rule still needs the hill-climbing loop.",
            "Transition: Next: what happens when a tool returns too much.",
        ],
    ),
    # 31 technique 2 ------------------------------------------------------------------------------
    dict(
        kind="technique",
        title="2) Cap rows and values in the tool, with a notice",
        minutes=2.5,
        says="The tool returns at most a set number of rows, cuts long values, and says what it "
        "cut",
        src=".dev/review/deck3-diagrams-technique.md (pattern-row-cap); sources.py entry 4; "
        "platform/src/datapilot/loop1_agent/tools.py lines 39-60 (format_result); E16, E18",
        figure={
            "diagram": "pattern-row-cap",
            "alt": "Cap rows and values in the tool: a result of 12,000 rows goes to the tool, "
            "which caps it at 50 rows and cuts long values short; it returns the 50 rows and a "
            'notice, "50 of 12,000; add a filter"; the model narrows its query and asks again, '
            "with a filter; the failure without a cap: 12,000 rows fill the context and the run "
            "budget",
        },
        on_slide=[
            "- **What:** the tool, not the prompt, bounds what one call can put into the context.",
            "- **How:** return a set number of rows, cut long values, and add the total count and "
            "a notice.",
            "- **Example:** 50 of 12,000 rows; add a filter. The model sees what it missed, and "
            "what next.",
            "- **Limit:** fetch the cap plus one row and count separately; a cap after fetching "
            "guards only the context.",
            "- **Elsewhere:** Claude Code caps a tool response at 25,000 tokens by default.[^4]",
            "Key idea: Cap in the tool; a budget that counts only spent tokens cannot stop one "
            "oversized call.",
        ],
        notes=[
            "Purpose: Teach the second technique: cap rows and values inside the tool, and say "
            "what was cut.",
            "What to say: Everything a tool returns stays in the conversation and is sent again "
            "on every later model call, so one large result is paid for many times; caching a "
            "repeated prefix lowers that price, not the crowding. Walk the diagram. A result of "
            "12,000 rows reaches the tool. The tool keeps 50 rows and cuts each long value "
            "short, because one row can hold a whole list of email addresses. It returns the "
            "rows, the total count and a notice: 50 of 12,000, add a filter. The count tells the "
            "model what it did not see; the notice tells it what to do next. On the right, the "
            "failure without a cap: Tuesday's story. Anthropic's guide to writing tools "
            "recommends truncation with instructions that steer the agent, Source [^4]. A second "
            "guard: count the input tokens of the next request before you send it, and stop if "
            "it would cross the run budget. DataPilot checks only the tokens already spent, which "
            "is why one call overshot. In DataPilot, one function formats every query result: it "
            "cuts the rows to the pack's row cap of 50, cuts each value at 2,000 characters, "
            "keeps the total row count, and adds a notice when rows were cut. Its executor still "
            "fetches every row to count them: that is the Limit line.",
            "The point to land: A cap in the tool holds whatever the model asks for; a cap in the "
            "prompt holds only if the model obeys.",
            "Example: A coding agent's file search returns the first 50 of 3,000 matches with a "
            "notice to narrow the pattern. DataPilot's notice reads: Showing 50 of 10000 rows.",
            'Ask the room: "What should the agent do when it sees the notice?" Expect: aggregate '
            "in the query, or narrow the question.",
            "Misconceptions: That a cap hides answers. It can, which is why the count and the "
            "notice travel with it.",
            "Transition: A cap bounds one call. Next: what bounds the whole run, and what shape "
            "its answer takes.",
        ],
    ),
    # 32 technique 3 ------------------------------------------------------------------------------
    dict(
        kind="technique",
        title="3) Stops in code, and the answer envelope",
        minutes=2.5,
        says="Code checks the limits every turn and validates a typed answer before it posts",
        src=".dev/review/deck3-diagrams-technique.md (pattern-stops-envelope); the second "
        "rebuild's generic loop (slides of 27 October 2026, the pattern in code); "
        "platform/src/datapilot/loop1_agent/analyst.py lines 72-86; "
        "platform/src/datapilot/contracts/answer.py lines 11-28; E18 (pack.yaml limits)",
        figure={
            "diagram": "pattern-stops-envelope",
            "alt": "Stops in code, and the answer envelope: the model calls a tool or answers, and "
            "each turn passes stop rules in code, on model calls, tool calls, tokens, and time, "
            "before it goes on; a limit hit ends the run escalated, with the reason; every run ends in an answer envelope with a status, the answer, the "
            "evidence, and the assumptions, which code validates before it posts; the failure "
            "without them: endless turns, or free text nobody can check",
        },
        on_slide=[
            "- **What:** code, not the model, decides whether there is a next turn, and checks "
            "the answer's shape.",
            "- **How:** check calls, tokens and time every turn; return status, answer, evidence "
            "and assumptions.",
            "- **In code:** a counter around each model call; at the limit, return the envelope "
            "as escalated.",
            "- **Elsewhere:** a support agent at its limit hands the ticket to a person, with what "
            "it found.",
            "Key idea: The model chooses the next step; code decides whether there is one.",
        ],
        notes=[
            "Purpose: Teach the third technique: stop conditions in code, and an answer envelope "
            "code can check.",
            "What to say: A stuck model does not know it is stuck, so a prompt that says stop "
            "after five tries is a hope. Walk the diagram. The model calls a tool or answers, "
            "and every turn passes stop rules in code, on model calls, tool calls, tokens and "
            "time. A limit ends the run escalated, with its reason, not with an exception that "
            "loses what the agent found. Escalated means handed to a person with its reasons; "
            "held, which you meet in Section 2, means waiting for a person's approval. Every run "
            "ends in an answer envelope: a status, the answer, the evidence such as the query "
            "and its rows, and the assumptions it made. Code validates it before anything posts, "
            "and a validation error goes back to the model as feedback inside the same limits. "
            "The In code line is the whole loop: a counter around one call. DataPilot sets these when the analyst is built: 12 model calls, 16 "
            "tool calls, a response format that must validate as the envelope, and a run "
            "budget of 60,000 tokens. It sets no deadline per run and no request timeout of its "
            "own; add both in yours, because a check between turns cannot interrupt a call in "
            "flight.",
            "The point to land: The model chooses the next step; your code decides whether there "
            "is one, and what shape the answer takes.",
            "Example: A support agent, illustrative: after eight tool calls without an answer it "
            "stops and hands the ticket to a person, status escalated, with what it found.",
            'Ask the room: "Where does your agent\'s step limit live today?" Expect: in the '
            "framework default, or in the prompt.",
            "Misconceptions: That a valid envelope is a correct answer. It is a checkable one; "
            "Section 2: Verification loop does the checking.",
            "Transition: The last technique adds help: looking values up, and helper agents, at "
            "a price.",
        ],
    ),
    # 33 technique 4 ------------------------------------------------------------------------------
    dict(
        kind="technique",
        title="4) Value lookup and helper agents, and their cost",
        minutes=2.5,
        says="Look values up before filtering; a helper agent costs calls, tokens and time, so "
        "measure it before you keep it",
        src=".dev/review/deck3-diagrams-technique.md (pattern-value-lookup); sources.py entry "
        "65; E14 (docs/calibration-report.md, Agents on and off); DECISIONS.md, 27 October 2026, "
        "item 3; section-1-agent-loop/assignment/README.md",
        figure={
            "diagram": "pattern-value-lookup",
            "alt": 'Value lookup and helper agents: a question says "California", and a value '
            'lookup finds the stored value, "CA", so the filter matches real rows; without it, '
            'state = "California" matches 0 rows; beside it, a helper agent reads the large '
            "schema in its own context and passes a brief to the main agent, which keeps a clean "
            "context; the cost: more model calls, tokens, and time, and what its brief leaves "
            "out never arrives, so measure a helper before you keep it",
        },
        on_slide=[
            "- **What:** a lookup finds the stored value; a helper reads in its own context and "
            "returns a brief.",
            "- **How:** match the user's word to the column's stored values; on a tie, ask; record "
            "the match as an assumption. Helpers get read-only tools.",
            "- **Elsewhere:** a coding agent's helper reads a long build log and returns the "
            "failing test.",
            "- **Open question:** our schema helper used 1.7 to 2.2 times the tokens, no gold "
            "change. Keep it?",
            "Key idea: Measure a helper before you keep it: it costs calls, tokens and time on "
            "every run.",
        ],
        notes=[
            "Purpose: Teach the fourth technique, value lookup and helper agents with their cost, "
            "and pose the open question: measure a helper before you keep it.",
            "What to say: Two ways to give the agent what its tools do not show. The left of the "
            "diagram: the question says California, but the warehouse stores CA. A filter on the "
            "user's word matches zero rows, and the agent reports zero sales, fluently. A value "
            "lookup finds the stored value first, and asks when two stored values are equally "
            "close. The right: a helper agent reads the large schema in its own context and "
            "passes a short brief to the main agent, which keeps a clean context. The cost is "
            "real: more model calls, tokens and time on every run, and what the brief leaves out "
            "never arrives. Anthropic reports that its multi-agent research runs used about 15 "
            "times the tokens of a chat, Source [^65]. Now the open question, and it is "
            "DataPilot's own. Its schema helper suggests tables and joins. In our runs it used "
            "1.7 to 2.2 times the tokens and changed no gold result. It stays on: measuring it "
            "on the holdout questions, on and off, is owed to the rehearsal. What would you do "
            "with it? Whatever you decide, decide it from a measurement: a helper on questions it "
            "has not seen, on and off, before you keep it.",
            "The point to land: Look values up before filtering on them; keep a helper only "
            "after measuring it on and off.",
            "Example: On four questions, one run each, reviewer off, the helper took 5,786 tokens "
            "and 12.8 seconds a question against 3,337 and 10.1 without; with the reviewer on, "
            "8,648 against 3,853. Value lookup is Assignment 1: Agent loop.",
            'Ask the room: "Which helper agent in your system was never measured off?" Expect: a '
            "router or a planner.",
            "Misconceptions: That more agents add reliability. They add calls, latency and "
            "correlated errors when they share a model.",
            "Transition: Now the decision this loop makes in your own text-to-SQL design.",
        ],
    ),
    # 34 design callout ---------------------------------------------------------------------------
    dict(
        kind="design_callout",
        title="Text-to-SQL design: Schema exposure and value lookup",
        minutes=1.5,
        says="How much schema the agent sees, and how it finds values, by warehouse size",
        src="section-1-agent-loop/assignment/README.md; the second rebuild's design callout "
        "(slide 26); E10",
        on_slide=[
            "Lead: Size decides how much schema to show; values are always looked up.",
            "Decision: how much schema to show, how to find values",
            "| Choice | Small warehouse | Large warehouse |",
            "|---|---|---|",
            "| Tables | List every name | Retrieve candidates; a person confirms |",
            "| Columns | Describe on demand | Prune to the columns in play |",
            "| Values | Look up before filtering | Match stored values, fix spelling |",
            "DataPilot: lists every table, describes on demand; value lookup is Assignment 1.",
        ],
        notes=[
            "Purpose: Turn the agent loop into the schema and value decisions of the learner's "
            "own text-to-SQL design, by warehouse size.",
            "What to say: The agent loop holds two text-to-SQL decisions, and the answer depends "
            "on the size of your warehouse. Read the table by row. Tables: in a small warehouse, "
            "list every name; in a large one, a retrieval step proposes candidate tables and a "
            "person, or a check, confirms them, because retrieval can miss a table. Columns: "
            "describe on demand in a small one; in a large one, prune to the columns in play, "
            "since every column shown is paid for on every call. Values: in both, look a value "
            "up before filtering on it. DataPilot's warehouse is small, so it lists every table and "
            "describes on demand. Value lookup is Assignment 1: a tool that finds the closest "
            "stored value, records the match in the envelope's assumptions, and asks on a tie. "
            "Decide which column you are in before you write a prompt: a large warehouse needs "
            "retrieval and its review.",
            "The point to land: Size decides how much schema to show; values are always looked "
            "up, never typed in from the question.",
            "Example: The catalogue holds Alpine Trek 45L Backpack and Alpine Trek 45 L "
            "Backpack; a lookup must ask which one, not pick.",
            'Ask the room: "Which column of this table is your warehouse?" Expect: most say large.',
            "Misconceptions: That retrieval removes the need for review. Retrieval can miss the "
            "table that matters, which is why a person or a check confirms it.",
            "Transition: The four techniques on one page, with what to do in your own system.",
        ],
    ),
    # 35 cheat sheet ------------------------------------------------------------------------------
    dict(
        kind="table",
        title="Cheat Sheet: The agent loop in four techniques",
        minutes=1.5,
        says="Each technique, what it does, and how to apply it in your own system",
        src="section-1-agent-loop/README.md, Apply it in a real system; the second rebuild's "
        "apply-it checklist and pitfalls (slides 27 and 28)",
        on_slide=[
            "Lead: What the agent sees, how much, and when it stops.",
            "| Technique | What it does | How to apply it in your system |",
            "|---|---|---|",
            "| Tools decide what it sees | Names first, then details | Print what each tool "
            "returns for one real table |",
            "| Cap in the tool | Bounds rows and values; says what it cut | Cap every list tool; "
            "test with a huge result |",
            "| Stops and the envelope | Code ends the run; answers are typed | Put the limits in "
            "settings; return status, answer, evidence, assumptions |",
            "| Value lookup and helpers | Finds stored values; isolates side reading | Look up "
            "before filtering; measure each helper on and off |",
        ],
        notes=[
            "Purpose: Give the four techniques as one table, each with a concrete change a "
            "learner can make in their own system next week.",
            "What to say: One row per technique, and the third column is the work for next "
            "week. First row: pick one real table and print exactly what each tool returns for "
            "it. Second row: give every list tool a row cap, a cap on each value's length, the total "
            "count and a notice, then test it with a query that returns more than the cap; rewrite "
            "tool errors as one sentence each, what failed and what to try next. Third "
            "row: put hard stops in code, read from one settings file, and return an answer "
            "envelope, status, answer, evidence and assumptions, with a status that allows not "
            "answering. Fourth row: add a value lookup before any filter on a name. Then switch "
            "each helper agent off for a day of questions and compare; keep it only if it earns "
            "its tokens. The full list is in Section 1's README, Apply it in a real system.",
            "The point to land: Fix the view, the size and the stops before you touch the prompt.",
            "Example: DataPilot's row cap and call limits sit in its pack's settings, so changing "
            "them needs no code.",
            'Ask the room: "Which row would take you longest?" Expect: the envelope, because '
            "downstream code reads prose today.",
            "Misconceptions: That this needs a new framework. Each row changes tools and code "
            "you already have.",
            "Transition: Enough tables. Let us run the loop live.",
        ],
    ),
    # 36 demo -------------------------------------------------------------------------------------
    dict(
        kind="demo",
        title="Section 1: Agent loop - Implementation Notes: The confident wrong answer",
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
            "What to say: Let's watch the agent loop answer, get it wrong, and blow its run "
            "budget, live. Nothing here is recorded and nothing is scripted: each run calls the "
            "class model, and the model chooses its own tools. First a simple question, so you see the "
            "loop work end to end. Then the fiscal year 2025 revenue question from Monday of the "
            "week: this time you watch the agent loop produce that wrong number, tool by tool. "
            "Then the row cap, off and then on, so the failure story's token counter happens in "
            "front of you. Watch three things: the tool timeline, the gold check, and the token "
            "counter. When each result lands I will read its numbers aloud and show its live "
            "stamp, the start time and the trace link, so you know it ran just now.",
            "Do: Run sheet 1: at 1:05:30, check the status line: report-only level, kill switch "
            "released, Planted None.",
            'Do: Run sheet 2: Agent: type "How many orders have been placed in total?", then '
            "press Ask: a posted count, three tool calls.",
            "Do: Run sheet 3: at 1:08:30, Agent > Ask the spine question: a mismatch against "
            "gold, trap notes on the query; held is fine.",
            "Do: Run sheet 4: at 1:13:30, make demo NAME=agent-unbounded-rows PLANTED=1: the "
            "token counter jumps, escalated.",
            "Do: Run sheet 5: Agent > Run large query: the counter stays low, the notice shows.",
            "Do: Run sheet 6, the one fallback for every demo: make reset NAME=agent-loop (about "
            "7 seconds), then the same trigger; show the backup screenshot only while the reset "
            "runs.",
            "Do: Run sheet 7: cutoff 1:16:30, no retry after it; name a missed demo for the "
            "Thursday review.",
            "Do: Run sheet 8: Texas last quarter only if ahead of the clock.",
            "Demo: The simple question.",
            "Command: 1:05:30 to 1:08:30. First check the status line: the report-only level, the "
            'kill switch released, and Planted None: the fixed system. Then type "How many orders '
            'have been placed in total?" in the console and press Agent > Ask; or, in the demo '
            "terminal, make demo NAME=agent-simple-question, which sends the same question.",
            "Point at: first the tool timeline as each call appears, list_tables, describe_table, "
            "run_query, with its duration; then the one-line count query and the envelope's "
            "status; then the tokens and cost; last the live stamp.",
            "Expected output: Posted, 405,738 orders, one count query, about 5,100 tokens and "
            "0.0005 dollars; 14 to 39 seconds in the recorded runs.",
            "While it runs: 14 to 39 seconds of the 3-minute slot. Say that nothing is scripted: "
            "the model chose these tools itself, and the path can differ run to run; the envelope "
            "and its query are what we check.",
            "If it fails: a run that answers correctly with more tool calls is not a failure, "
            "and a missing trace link is not one either: LangSmith may be refusing traces, so "
            "point at the run id. Queued or stalled: the run sheet's reset (line 6).",
            "Backup screenshot: "
            + EXPECTED
            + "agent-simple-question-answer.png, the posted count with its three tool calls.",
            "Demo: The confident wrong answer.",
            "Command: 1:08:30 to 1:13:30. Press Agent > Ask the spine question in the console, "
            "the button for the fiscal year 2025 revenue question; or make demo "
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
            "If it fails: held is not a failure: the gold check still appears. No number back "
            "means no gold check: the run sheet's reset. If it comes back correct, say so: the "
            "gold check, not the wording, is the verdict, and one run is one run.",
            "Backup screenshot: "
            + EXPECTED
            + "agent-confident-wrong-answer-sql.png, the query with its three trap marks and the "
            "mismatch.",
            "Demo: Unbounded rows.",
            "Command: 1:13:30 to 1:17:30. First, in the demo terminal, make demo "
            "NAME=agent-unbounded-rows PLANTED=1, the bug on for that run only; then press Agent > "
            "Run large query in the console, or make demo NAME=agent-unbounded-rows, with it off.",
            "Point at: the token counter of the planted run and its escalated status; then the "
            "same counter on the fixed run; then the notice, Showing 50 of 10000 rows, and the "
            "total count under the rows; last the live stamp of each. If a minute is left, open "
            "platform/src/datapilot/loop1_agent/tools.py lines 33-54 in the editor: the cap from "
            "technique 2 and its planted branch.",
            "Expected output: with the bug on, 182,654 to 187,030 tokens, escalated at the run "
            "budget, in about 12 seconds; with it off, 17,298 to 30,216 tokens in 26 to 48 "
            "seconds, sometimes held by a reviewer concern.",
            "While it runs: two runs inside the 4-minute slot. During the planted run, say that "
            "DataPilot compares only the tokens already spent with the run budget before each "
            "call, so one call can overshoot it: step four of the failure story. During the fixed "
            "run, point back at the cap of technique 2.",
            "If it fails: a counter that does not jump means the run went without the flag: "
            "repeat the planted command. A fixed run held for approval is fine: the token "
            "counter is the moment. Anything else: the run sheet's reset.",
            "Backup screenshot: "
            + EXPECTED
            + "agent-unbounded-rows-planted-tokens.png and agent-unbounded-rows-fixed-tokens.png "
            "in the same folder, 184,983 against 28,468 tokens.",
            "Demo: Texas last quarter.",
            "Command: optional, cut first, only when the three core demos end before 1:16:30: "
            "press Agent > Ask with the Texas question, or make demo "
            "NAME=agent-texas-last-quarter.",
            "Point at: the join path in the query, four or five tables (orders, order items, "
            "products, categories, and customers or the ship state), and the date range: August "
            "to October 2025 is the last completed fiscal quarter against the business date of "
            "31 January 2026.",
            "Expected output: an answer whose query joins four or five tables (the recorded run "
            "had 4 joins); no benchmark question asks "
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
            "Coordinated Universal Time, with the internal accounts kept; the reviewer held it, "
            "so it never posted.",
            'Ask the room: "What in the envelope would let a reviewer catch this?" Expect: the '
            "query and the stated assumption.",
            "Misconceptions: That the demo is rigged to fail. The model chose every query; the "
            "rules are simply not in the data.",
            "Transition: One run is a story. Next, the measurement: what better tools changed, and "
            "what they cost.",
        ],
    ),
    # 37 evidence ---------------------------------------------------------------------------------
    dict(
        kind="evidence",
        title="Measured: With and without the agent loop's tools",
        scoreboard=1,
        minutes=2,
        says="Full descriptions, capped rows, the schema helper: 17 of 21 correct against 12",
        src="E15 (docs/benefits.md, Section 1: Agent loop; docs/calibration-report.md, The "
        "benefits measurement); .dev/deck3-evidence.md, part 3, Section 1; E7",
        chart={
            "type": "column",
            "title": "Seven easy questions, 3 runs a side",
            "categories": ["Correct", "Sent out wrong"],
            "series": [("Without the tools", [12, 9]), ("With the tools", [17, 4])],
            "x_label": "Outcome of each run",
            "y_label": "Runs, out of 21",
            "maximum": 21,
        },
        on_slide=[
            "Lead: Better tools fixed more easy answers; three changes at once cannot say which "
            "one helped.",
            "Sample: 21 runs per side, seven questions asked 3 times each, reviewer off",
            "- **Without:** column names only, unbounded rows, no schema helper",
            "- **With:** full descriptions, capped rows, the schema helper",
            "- **Cost:** about 1,100 more tokens a run",
        ],
        notes=[
            "Purpose: Show the measured effect of the agent loop's tool design, with its sample "
            "size and its cost, and where the fiscal year question stands.",
            "What to say: This is the paired measurement of 24 October 2026, rehearsal session "
            "56894641, on the class model. Seven questions without traps, each asked three times "
            "on each side, so 21 runs per side, with the reviewer off on both sides so it could "
            "not hide the difference. Without means column names only, unbounded rows and no "
            "schema helper; with means full descriptions, capped rows and the schema helper. "
            "Read the chart: 12 of 21 correct without, 17 of 21 with; wrong answers sent out fell "
            "from 9 to 4. The cost: about 1,100 more tokens a run, 4,857 against 3,738. That is "
            "less than the schema helper cost on its own in technique 4, 1.7 to 2.2 times: those "
            "were four other questions, one run each, so the two costs are not comparable, and "
            "this row cannot split its cost among the three changes. Two cautions. This row "
            "mixes three changes, so it says what happened, not which change did it. And 21 "
            "runs per side is a direction, not a rate; the smaller run of 23 October agreed in "
            "direction, 6 of 7 against 4 of 7. Now the scoreboard at the top: the agent sees "
            "enough, but the fiscal year 2025 answer is still wrong. Enough means easy questions "
            "got better, not all of them: 4 of 21 still went out wrong. Better tools did nothing for "
            "the traps: under the starting knowledge, 0 of 99 trap-question runs passed. Whether "
            "the schema helper earns its place is still the open question from technique 4.",
            "The point to land: Better tools made more easy answers right, and did nothing for "
            "the business rules.",
            "Example: The dollar figures of the two sides come from different runs and are not "
            "comparable, so claim no saving; the cost to state is the tokens.",
            'Ask the room: "Which of the three changes would you test first, alone?" Expect: the '
            "column descriptions.",
            "Misconceptions: That 17 of 21 is an accuracy rate. It is one session's count on "
            "seven questions.",
            "Transition: Questions before we move on.",
        ],
    ),
    # 38 Ask about anything (copied) --------------------------------------------------------------
    dict(
        kind="qa",
        title="Ask about anything",
        minutes=2.5,
        says="Questions about the agent loop, and one question to apply it",
        src="the reference deck, slide 31; the second rebuild's Section 1 recap question",
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
        notes=[
            "Purpose: Take questions on the agent loop before the next section.",
            "What to say: Before the chat's questions, ask this (30 seconds): a support agent's "
            "ticket search can match 40,000 tickets. What should the tool return, and what stops "
            "the run? Answer in the chat. Then take questions from the chat; the teaching "
            "assistants pick the top ones.",
            "Do: The answer to draw out: the 20 most relevant tickets with only the fields the "
            "next step needs, the total count, and a notice such as showing 20 of 40,000, filter "
            "by customer or date; errors as one sentence on what to try; limits in code on model "
            "calls, tool calls and tokens; an envelope whose status can be needs clarification.",
            "Transition: Next, the verification loop: how to catch a wrong answer that looks "
            "right.",
        ],
    ),
]
