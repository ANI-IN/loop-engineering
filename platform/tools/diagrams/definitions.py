"""The course diagrams, written as code so every label can be traced to the file it comes from.

Each function builds one scene. A slide diagram is a 1920 by 791 panel with labels of 40 pixels or
more (18 points on the deck's diagram panel); the three dense reference diagrams (the system, the
run lifecycle, the warehouse data model) are page-only 1920 by 1080 panels with labels of 20
pixels or more. `export_diagrams.py --build` measures the labels in the browser, writes the
.excalidraw sources (with the step frames when `steps` is set and one variant per loop in
`highlights`), and renders them. After that the .excalidraw file is the source: open it at
excalidraw.com to edit it, or change the function here and build again (a build overwrites hand
edits).

Each shape is filled with the colour of the loop it belongs to (`Scene.loop`, scene.LOOPS) and
every loop is named in words on the diagram, so colour never carries meaning alone. The facts on
each diagram come from the files named in its docstring (paths from the repository root); each
diagrams/README.md lists them again beside the embed snippet.
"""

from __future__ import annotations

import importlib.util
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from scene import MUTED, PAGE_HEIGHT, WHITE, Scene

REPO = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class Spec:
    name: str
    folder: str
    build: Callable[[], Scene]
    steps: bool = False
    highlights: tuple[str, ...] = ()  # one variant per loop named here: <name>-<loop>-loop


LEGEND = [
    ("agent", "An agent: a model decides"),
    ("code", "Code: same input, same result"),
    ("store", "Stored state"),
    ("human", "A person decides"),
    ("outside", "Outside DataPilot"),
]


def lifecycle_transitions() -> dict[tuple[str, str], str]:
    """(from, to) -> writer, read from the contract itself (it imports nothing but enum)."""
    path = REPO / "platform/src/datapilot/contracts/lifecycle.py"
    spec = importlib.util.spec_from_file_location("lifecycle_contract", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return {(a.value, b.value): by for (a, b), by in module.TRANSITIONS.items()}


# --- 0. The diagram style ------------------------------------------------------------------------
def diagram_style() -> Scene:
    """The style sample (docs/diagrams/README.md, "Diagram style"): the four loop colours, each
    kind of shape, an arrow with its label, a free label, a code label, and a muted shape."""
    s = Scene("diagram-style")
    for x, loop in zip((40, 505, 970, 1435), LOOPS, strict=True):
        s.chip(x, 30, 445, 80, loop)
    s.loop = "agent"
    s.shape("agent", 40, 160, 400, 200, "An agent:\na model decides")
    s.arrow([(442, 260), (538, 260)])
    s.loop = "verification"
    s.shape("code", 540, 160, 380, 200, "Code: same\ninput, same\nresult")
    s.arrow([(922, 260), (998, 260)])
    s.loop = None
    s.shape("human", 1000, 150, 400, 220, "A person\ndecides")
    s.arrow([(1402, 260), (1488, 260)])
    s.loop = "event"
    s.shape("store", 1490, 160, 390, 200, "Stored state:\nthe jobs table")
    s.loop = None
    s.shape("stop", 40, 410, 500, 140, "Stop: the kill\nswitch is engaged")
    s.shape("outside", 580, 410, 420, 140, "Outside DataPilot:\na webhook sender")
    s.arrow([(1002, 505), (1478, 505)])
    s.text(1240, 470, "an arrow label", align="center")
    s.loop = "agent"
    s.shape("code", 1480, 410, 400, 140, "run_query", code=True)
    s.loop = None
    s.text(40, 600, "A free label: Nunito, 40 pixels, 18 points on a slide")
    s.text(40, 680, "describe_table: the code font", code=True)
    # A muted shape, the way the per-section variants of the four-loop map show the other loops.
    s.loop = "hill-climbing"
    muted = s.shape("code", 1240, 610, 640, 130, "Muted: another loop")
    muted.update(backgroundColor=WHITE, strokeColor=MUTED)
    return s


# --- 1. System architecture (page only) ----------------------------------------------------------
def system_architecture() -> Scene:
    """compose.yaml (services, the one-shot migrate, ports); platform/src/datapilot/db.py (database
    roles, ops.schema_migrations); platform/src/datapilot/loop3_events/api/*.py (19 routes,
    listed in contracts/api.py ENDPOINTS); loop3_events/scheduler.py; loop3_events/worker.py;
    loop3_events/trace_refusals.py (ops.runs.trace_refused_at); loop3_events/improvement.py (the
    runner's advisory lock); loop4_hill_climbing/runner.py (requests, two candidates through
    candidates.py, promotions with clearance re-runs, gold checks of live runs);
    platform/ops/sql/ops/*.sql (tables, 018 schema_migrations owner only, 020 trace_refused_at,
    021 gate_baseline_id); platform/ops/sql/roles.sql; platform/packs/datapilot_us/pack.yaml
    (models)."""
    s = Scene("system-architecture", height=PAGE_HEIGHT)
    s.loop = "event"
    # Row 2 first, so the page spells out "application programming interface" before any
    # other label says API.
    s.shape(
        "code",
        480,
        60,
        360,
        380,
        "Application\nprogramming interface\n(API), FastAPI\n\n19 routes, among them:\n"
        "POST /events\nPOST /approvals/{run_id}\nPOST /control/kill-switch\n"
        "POST /control/autonomy\nPOST /experiments/run\nPOST /analyzer/run\n"
        "POST /knowledge/\n{version}/approve",
        size=22,
    )
    # Column A: who sends work in.
    s.shape("outside", 50, 60, 340, 90, "Webhook sender", size=24)
    s.shape("human", 90, 180, 260, 116, "A person", size=26)
    s.shape("code", 50, 330, 340, 100, "Console\nStreamlit, port 8501", size=26)
    s.text(
        60,
        440,
        "approves, stops, and runs\nexperiments through the API;\nreads runs directly",
        size=20,
    )
    s.shape("code", 50, 560, 340, 110, "Scheduler\n8 a.m. Eastern time digest", size=24)
    s.text(60, 678, "writes the digest event\nthe way POST /events does", size=20)
    s.loop = None
    s.legend(40, 820, LEGEND)

    # Row 2: the worker and the hill-climbing loop runner.
    s.loop = "agent"
    s.shape("boundary", 920, 60, 480, 380, loop=None)
    s.text(944, 72, "Worker: one job at a time", size=26)
    s.shape("agent", 950, 116, 420, 86, "Analyst agent", size=26)
    s.shape("agent", 950, 214, 205, 100, "Schema\nscout agent", size=22)
    s.loop = "verification"
    s.shape("agent", 1165, 214, 205, 100, "Reviewer\nagent", size=22)
    s.shape("code", 950, 330, 420, 92, "Seven graders and the\nread-only executor", size=24)

    s.loop = "hill-climbing"
    s.shape("boundary", 1440, 60, 460, 380, loop=None)
    s.text(1462, 72, "Hill-climbing loop runner", size=26)
    s.shape(
        "agent",
        1460,
        110,
        420,
        112,
        "Analyzer team agents:\nfailure analyst, rule\nwriter, critic",
        size=20,
    )
    s.shape(
        "code",
        1460,
        232,
        420,
        196,
        "Experiment runner, evaluator,\noverfit guard, promotion gate\n"
        "Two candidates, the better kept\nPromotion, then clearance re-runs\n"
        "Gold checks of live runs\nOne runner per database",
        size=20,
    )

    # Row 3: the services outside, and the data the agents read.
    s.loop = None
    s.shape("outside", 480, 520, 250, 100, "OpenAI API\nevery agent:\ngpt-6-luna", size=22)
    # Traces: every demo and check run in full, experiment runs as a sample
    # (`tracing.experiment_sample_rate` 0.2 in pack.yaml).
    s.shape(
        "outside",
        480,
        640,
        270,
        162,
        "LangSmith\ndemo and check runs\nin full; about 1\nexperiment run in 5;\n"
        "a refused trace is\nrecorded on its run",
        size=20,
    )
    s.shape("store", 950, 520, 180, 120, "Schema lg\ncheckpoints", size=24)
    s.shape("store", 1170, 520, 250, 120, "Schema warehouse\nread-only role", size=22)
    s.shape("store", 1610, 520, 260, 120, "Database\nwarehouse_alt\nread-only role", size=22)

    # Row 4: the state every process shares.
    s.shape(
        "store",
        480,
        820,
        1390,
        210,
        "PostgreSQL 18.6, database datapilot, schema ops: the shared state\n"
        "events, event duplicates, jobs, runs (with any trace refusal), run events, approvals,\n"
        "posts, control, budgets, autonomy policy, knowledge versions, experiments (with the\n"
        "gate's recorded baseline), promotion decisions, improvement requests, live sessions,\n"
        "analyzer candidates, rehearsal verifications, reset archives and their rows,\n"
        "schema migrations (written by the owner role only)",
        size=22,
    )

    # Arrows.
    s.arrow([(392, 105), (478, 105)])
    s.arrow([(220, 298), (220, 328)])
    s.arrow([(392, 380), (478, 380)])
    s.arrow([(392, 615), (445, 615), (445, 960), (478, 960)])
    s.arrow([(392, 410), (465, 410), (465, 880), (478, 880)])
    s.arrow([(760, 442), (760, 818)])
    s.text(772, 655, "event, job,\nand run in one\ntransaction", size=20)
    s.arrow([(935, 442), (935, 818)], both=True)
    s.text(947, 655, "claim, lease,\nheartbeat", size=20)
    s.arrow([(1040, 442), (1040, 518)], both=True)
    s.arrow([(1295, 442), (1295, 518)])
    s.arrow([(1490, 442), (1400, 518)])
    s.arrow([(1740, 442), (1740, 518)])
    s.arrow([(1520, 442), (1520, 818)], both=True)
    s.text(1532, 740, "requests,\nexperiments", size=20)
    s.text(1612, 655, "execution match\non both databases", size=20)
    # The one-shot service every other one waits on (compose.yaml, depends_on).
    s.shape(
        "code", 1110, 680, 380, 100, "migrate: applies the ops\nmigrations, then exits", size=22
    )
    s.arrow([(1300, 782), (1300, 818)])
    return s


# --- 2. The four loops as one system -------------------------------------------------------------
def four_loops() -> Scene:
    """platform/src/datapilot/loop1_agent/{analyst,scout}.py; loop2_verification/{checker,loop,
    reviewer}.py and graders/ (seven graders); loop3_events/{router,api/events,worker,autonomy,
    killswitch,approvals}.py; loop4_hill_climbing/{analyzer,gate,runner}.py (three analyzer agents,
    the gate's four conditions); platform/packs/datapilot_us/benchmark/{dev,holdout}.yaml (25 and
    15 items). One variant per section highlights its loop (Spec.highlights)."""
    s = Scene("four-loops")
    # Step 1: the agent loop, inside the verification loop, inside the event loop.
    s.step, s.loop = 1, "agent"
    s.shape("boundary", 350, 330, 550, 385)
    s.chip(370, 346, 250, 70, "agent")
    s.shape("agent", 370, 440, 230, 170, "Schema\nscout")
    s.shape("agent", 650, 440, 230, 170, "Analyst\nagent")
    s.arrow([(648, 525), (602, 525)], both=True)

    # Step 2: the verification loop around it.
    s.step, s.loop = 2, "verification"
    s.shape("boundary", 60, 230, 860, 515)
    s.chip(80, 246, 380, 70, "verification")
    s.shape("code", 80, 340, 230, 120, "Seven\ngraders")
    s.shape("agent", 75, 500, 250, 170, "Reviewer\nagent")
    s.arrow([(348, 400), (312, 400)])
    s.arrow([(195, 462), (195, 498)])

    # Step 3: the event loop around both.
    s.step, s.loop = 3, "event"
    s.shape("boundary", 30, 20, 1300, 755)
    s.chip(50, 36, 260, 70, "event")
    s.shape("outside", 340, 36, 240, 120, "An event\narrives")
    s.arrow([(582, 96), (618, 96)])
    s.shape("code", 620, 36, 270, 120, "Router: a\nfixed table")
    s.arrow([(892, 96), (928, 96)])
    s.shape("store", 930, 36, 370, 120, "Jobs table:\nclaim and lease")
    s.arrow([(1040, 158), (1040, 200), (765, 200), (765, 438)])
    s.shape("stop", 960, 220, 340, 110, "Kill switch:\nstops every run")
    s.shape("human", 960, 345, 340, 190, "Human\napproval")
    s.arrow([(922, 440), (958, 440)])
    s.shape("code", 960, 560, 340, 110, "Post, or hold\nfor a person")
    s.arrow([(1130, 537), (1130, 558)])

    # Step 4: the hill-climbing loop beside them, feeding a new knowledge version back.
    s.step, s.loop = 4, "hill-climbing"
    s.shape("boundary", 1360, 20, 530, 755)
    s.chip(1380, 36, 400, 70, "hill-climbing")
    s.shape("store", 1390, 122, 470, 160, "Benchmark:\n25 development,\n15 holdout")
    s.arrow([(1625, 284), (1625, 313)])
    s.shape("agent", 1390, 315, 470, 140, "Analyzer team:\nthree agents")
    s.arrow([(1625, 457), (1625, 483)])
    s.shape("code", 1390, 485, 470, 110, "Promotion gate:\nfour conditions")
    s.arrow([(1625, 597), (1625, 623)])
    s.shape("store", 1390, 625, 470, 130, "Active knowledge\nversion")
    # The label sits on the arrow's last leg, where it rises into the analyst, clear of every box.
    s.arrow([(1388, 735), (765, 735), (765, 612)])
    s.text(672, 668, "promoted", align="center")
    return s


# --- 3. The text-to-SQL reference architecture -------------------------------------------------
def text_to_sql_architecture() -> Scene:
    """The stages of a text-to-SQL system (docs/text-to-sql-design.md) and DataPilot's own:
    loop3_events/router.py (a fixed table, never a model); loop1_agent/scout.py (SchemaBrief:
    tables, joins, caveats); loop1_agent/knowledge.py (the active knowledge version, in every
    prompt through analyst.py); loop1_agent/extension.py (Assignment 1, the value lookup tool
    find_exact_values); loop1_agent/analyst.py and tools.py (run_query); loop2_verification/graders/
    parse.py, statement_policy.py (the syntax tree), cost.py (EXPLAIN), personal_data.py;
    executor.py (the read-only role) and tools.py (row_cap 50); loop2_verification/reviewer.py
    (the reviewer agent reads the answer); contracts/answer.py (assumptions,
    clarifying_question) and section-2-verification-loop/assignment/ (Assignment 2, the
    clarify-or-abstain grader); loop4_hill_climbing/evaluator.py (execution match on warehouse and
    warehouse_alt against the gold queries). No title on the 791-pixel canvas: stage 5 spells out
    Structured Query Language on its first use."""
    s = Scene("text-to-sql-architecture")
    stages = [
        # (loop, column, row, text)
        ("event", 0, 0, "1 Question routing: the\nrouter, a fixed table,\nnever a model"),
        ("agent", 1, 0, "2 Schema retrieval and\nlinking: the schema\nscout agent"),
        (
            "hill-climbing",
            2,
            0,
            "3 Business knowledge:\nthe knowledge version,\na light semantic layer",
        ),
        ("agent", 2, 1, "4 Value lookup: a tool\nfinds the stored value\n(Assignment 1)"),
        ("agent", 1, 1, "5 Structured Query\nLanguage (SQL): the\nanalyst agent writes it"),
        (
            "verification",
            0,
            1,
            "6 Validation: the\nsyntax-tree guard, cost\nestimate, personal data",
        ),
        (
            "verification",
            0,
            2,
            "7 Capped execution: the\nread-only executor,\nat most 50 rows back",
        ),
        (
            "verification",
            1,
            2,
            "8 Answer: reviewed,\nassumptions stated, or a\nclarifying question",
        ),
        (
            "hill-climbing",
            2,
            2,
            "9 Evaluation: execution\nmatch with gold queries\non two databases",
        ),
    ]
    xs, ys, w, h = (40, 680, 1320), (24, 290, 556), 560, 216
    for loop, col, row, text in stages:
        s.loop = loop
        name = {
            "agent": "Agent loop",
            "verification": "Verification loop",
            "event": "Event loop",
            "hill-climbing": "Hill-climbing loop",
        }[loop]
        s.shape("code", xs[col], ys[row], w, h, f"{text}\n{name}", align="left", valign="top")
    s.loop = None
    mid = [y + h / 2 for y in ys]
    # Row 1 left to right, row 2 right to left, row 3 left to right.
    s.arrow([(602, mid[0]), (678, mid[0])])
    s.arrow([(1242, mid[0]), (1318, mid[0])])
    s.arrow([(1600, ys[0] + h + 2), (1600, ys[1] - 2)])
    s.arrow([(1318, mid[1]), (1242, mid[1])])
    s.arrow([(678, mid[1]), (602, mid[1])])
    s.arrow([(320, ys[1] + h + 2), (320, ys[2] - 2)])
    s.arrow([(602, mid[2]), (678, mid[2])])
    s.arrow([(1242, mid[2]), (1318, mid[2])])
    # Evaluation feeds business knowledge: failures become new rules (the hill-climbing loop).
    s.arrow([(1882, mid[2]), (1906, mid[2]), (1906, mid[0]), (1882, mid[0])])
    return s


# --- 4. The agent loop ---------------------------------------------------------------------------
def agent_loop() -> Scene:
    """platform/src/datapilot/loop1_agent/analyst.py (create_agent, dynamic_prompt, limits,
    ToolStrategy(AnswerEnvelope)); loop1_agent/tools.py (the three tools, the row cap);
    loop1_agent/scout.py (scout_schema, catalog tools only, SchemaBrief);
    platform/src/datapilot/contracts/answer.py; platform/packs/datapilot_us/pack.yaml (limits:
    row_cap 50, model_call_limit 12, tool_call_limit 16; budgets: tokens_per_run 60000)."""
    s = Scene("agent-loop")
    s.step, s.loop = 1, "agent"
    s.shape("outside", 40, 310, 260, 120, "A question", loop=None)
    s.shape(
        "code",
        360,
        25,
        600,
        170,
        "Prompt on every model call:\nthe business date and the\nactive knowledge version",
    )
    s.shape("agent", 380, 270, 560, 200, "Analyst agent")
    s.arrow([(302, 370), (378, 370)])
    s.arrow([(660, 197), (660, 268)])
    s.chip(40, 30, 280, 70, "agent")

    s.step = 2
    s.text(1030, 22, "Tools of the analyst")
    s.shape("boundary", 1015, 82, 410, 333)
    s.shape("code", 1030, 92, 380, 70, "list_tables", code=True)
    s.shape("code", 1030, 172, 380, 70, "describe_table", code=True)
    s.shape("code", 1030, 252, 380, 70, "run_query", code=True)
    s.arrow([(928, 340), (1013, 340)], both=True)
    s.shape(
        "code",
        1490,
        18,
        390,
        222,
        "Checker: graders,\nthen the read-only\nexecutor\nVerification loop",
        loop="verification",
    )
    # What comes back travels on this arrow, so its label sits under the arrow's line.
    s.arrow([(1427, 287), (1685, 287), (1685, 242)], both=True)
    s.text(1450, 294, "at most 50 rows back,\nand the total count")

    s.step = 3
    s.shape("code", 1030, 332, 380, 70, "scout_schema", code=True)
    s.shape("fence", 1010, 440, 870, 335)
    s.text(1170, 450, "Tool boundary of the schema scout")
    s.shape("agent", 1030, 515, 400, 200, "Schema scout\nagent")
    s.shape("code", 1470, 510, 390, 70, "list_tables", code=True)
    s.shape("code", 1470, 590, 390, 70, "describe_table", code=True)
    # "No" in Nunito and run_query in the code font, on one stop box.
    s.shape("stop", 1470, 670, 390, 70, loop=None)
    s.text(1530, 680, "No")
    s.text(1594, 680, "run_query", code=True)
    s.arrow([(1130, 404), (1130, 525)], both=True)

    s.step = 4
    s.shape(
        "store", 460, 510, 480, 230, "Answer envelope:\nstatus, query, rows,\nanswer, assumptions"
    )
    s.arrow([(660, 472), (660, 508)])

    s.step = 5
    s.shape(
        "stop",
        40,
        510,
        380,
        230,
        "Stops every run:\n12 model calls,\n16 tool calls,\n60,000 tokens",
        loop=None,
    )
    return s


# --- 5. The verification layers ------------------------------------------------------------------
def verification_layers() -> Scene:
    """platform/src/datapilot/loop2_verification/checker.py (grader order); graders/*.py (the seven
    graders and their numbers); executor.py (read-only, rolled back); loop.py (the answer stage, the
    reviewer after the graders, the retry cap, held answers); reviewer.py;
    platform/src/datapilot/loop1_agent/guard.py (the stop before every model and tool call);
    loop3_events/killswitch.py; loop3_events/budget.py; pack.yaml (max_retries 3)."""
    s = Scene("verification-layers")
    s.loop = "verification"
    s.step = 1
    s.text(40, 18, "Every query, before it runs and after")
    s.chip(1480, 14, 400, 60, "verification")
    xs = [40 + i * 268 for i in range(7)]
    first = [
        "1 Parse",
        "2 SELECT\nonly",
        "3 Schema\nexists",
        "4 Cost\nestimate",
        "5 Personal\ndata",
    ]
    for x, label in zip(xs, first, strict=False):
        s.shape("code", x, 85, 234, 120, label)
    for x in xs[:4]:
        s.arrow([(x + 236, 145), (x + 266, 145)])
    for x in xs[:4]:
        s.arrow([(x + 114, 207), (x + 114, 243)])
    s.shape(
        "stop",
        40,
        245,
        990,
        110,
        "Blocked: the query does not run;\nthe reason goes back to the analyst",
        loop=None,
    )
    # The diamond sits below the arrow's head, so the head stays visible on its top point.
    s.shape("human", 1060, 255, 330, 186, "Human\napproval", loop=None)
    s.arrow([(1226, 207), (1226, 251)])

    s.step = 2
    # Not a grader, so no number: the query runs here, between grader 5 and grader 6.
    s.shape("code", xs[5], 85, 234, 120, "It runs:\nread-only")
    s.shape("code", xs[6], 85, 234, 120, "6 Execution")
    s.arrow([(xs[4] + 236, 145), (xs[5] - 2, 145)])
    s.arrow([(xs[5] + 236, 145), (xs[6] - 2, 145)])
    s.shape("stop", 1420, 245, 460, 110, "A refused write\nends the run", loop=None)
    s.arrow([(xs[5] + 114, 207), (xs[5] + 114, 243)])

    s.step = 3
    s.text(40, 395, "The answer, once the analyst answers")
    s.shape("store", 40, 465, 260, 130, "Answer\nenvelope")
    s.shape("code", 350, 465, 330, 130, "Graders 1 to 6\nagain")
    s.shape("code", 730, 465, 380, 130, "7 Final answer:\ntext matches rows")
    s.arrow([(302, 530), (348, 530)])
    s.arrow([(682, 530), (728, 530)])
    s.shape(
        "stop",
        350,
        635,
        760,
        110,
        "Failed: feedback and a retry;\nescalated after 3 attempts",
        loop=None,
    )
    s.arrow([(515, 597), (515, 633)])
    s.arrow([(920, 597), (920, 633)])

    s.step = 4
    s.shape("agent", 1160, 455, 330, 150, "Reviewer\nagent")
    s.shape("store", 1540, 465, 340, 130, "Answered:\nready to post")
    s.arrow([(1112, 530), (1158, 530)])
    s.arrow([(1492, 530), (1538, 530)])
    s.shape("human", 1160, 640, 330, 130, "A person", loop=None)
    s.arrow([(1325, 607), (1325, 636)])

    s.step = 5
    s.shape(
        "stop", 1530, 615, 350, 160, "Stop before\nevery call: kill\nswitch, budgets", loop=None
    )
    return s


# --- 6. The event loop ---------------------------------------------------------------------------
def event_loop() -> Scene:
    """platform/src/datapilot/loop3_events/api/events.py (ON CONFLICT on event_id, one
    transaction); scheduler.py; router.py (ROUTES, a lookup, never a model); worker.py (claim,
    lease, heartbeat, the checks at claim); reaper.py; budget.py; autonomy.py (post or hold);
    approvals.py (AsyncPostgresSaver in schema lg, thread_id = run_id; the parked job);
    api/control.py (POST /approvals/{run_id}); killswitch.py (checked at claim, before every model
    call, before every tool call)."""
    s = Scene("event-loop")
    s.loop = "event"
    s.step = 1
    s.shape("outside", 40, 40, 250, 160, "Webhook,\nscheduler,\nor console", loop=None)
    # The endpoint is the arrow the event travels on: its label sits on the arrow's line.
    s.arrow([(292, 150), (498, 150)])
    s.text(395, 95, "POST\n/events", align="center", code=True)
    s.shape("code", 500, 40, 300, 160, "Insert once\nper event_id")
    s.chip(780, 360, 300, 70, "event")

    s.step = 2
    s.arrow([(802, 120), (838, 120)])
    s.shape("code", 840, 40, 260, 160, "Router: a\nfixed table")
    s.arrow([(1102, 120), (1138, 120)])
    s.shape("store", 1140, 40, 270, 160, "Jobs table:\nthe queue")
    s.arrow([(1412, 120), (1448, 120)])
    s.shape("code", 1450, 40, 430, 160, "Worker: claim,\nlease, heartbeat")
    # Insert, router, and queue: code and a table, deliberately no agent.
    s.shape("fence", 480, 24, 950, 244, loop=None)
    s.text(955, 232, "No agent here: code and a table", align="center")

    s.step = 3
    s.shape("code", 1140, 290, 280, 160, "Reaper:\nrequeues an\nexpired lease")
    s.arrow([(1275, 288), (1275, 202)])
    s.shape("stop", 1450, 290, 330, 110, "Daily budget:\nchecked at claim", loop=None)
    s.arrow([(1615, 288), (1615, 202)])

    s.step = 4
    s.arrow([(1830, 202), (1830, 508)])
    s.shape("code", 1560, 510, 320, 160, "Autonomy:\npost at once,\nor hold")
    s.arrow([(1558, 590), (1462, 590)])
    s.shape("store", 1020, 510, 440, 160, "Parked job and a\ncheckpoint: survives\na restart")
    s.arrow([(1018, 590), (962, 590)])
    s.shape("human", 580, 495, 380, 190, "Human\napproval", loop=None)
    s.arrow([(578, 590), (502, 590)])
    s.shape("outside", 40, 525, 460, 130, "Channel post", loop=None)
    # The bypass leaves the autonomy box downwards; its label sits in the arrow's corner.
    s.arrow([(1720, 672), (1720, 740), (270, 740), (270, 657)])
    s.text(1475, 687, "post at once")

    s.step = 5
    s.shape(
        "stop",
        40,
        290,
        680,
        170,
        "Kill switch: checked at claim,\nbefore every model call,\nand before every tool call",
        loop=None,
    )
    return s


# --- 7. The hill-climbing loop -------------------------------------------------------------------
def hill_climbing_loop() -> Scene:
    """platform/packs/datapilot_us/benchmark/{dev,holdout}.yaml (25 and 15 items);
    platform/src/datapilot/loop4_hill_climbing/{evaluator,experiment,analyzer,overfit_guard,
    candidates}.py; loop4_hill_climbing/gate.py (decide, in its order: more holdout passes than the
    active version, zero confirmed regressions on the development and holdout splits, human
    approval, every new rule passes the overfit guard); runner.py (the promoted version becomes
    active); pack.yaml (analyzer.candidates 2; evaluation: overfit_question_words 6,
    overfit_sql_tokens 20)."""
    s = Scene("hill-climbing-loop")
    s.loop = "hill-climbing"
    s.step = 1
    s.shape("store", 40, 30, 420, 170, "Benchmark:\n25 development,\n15 holdout")
    s.arrow([(462, 115), (518, 115)])
    s.shape("code", 520, 30, 480, 170, "Experiment:\nexecution match\non two databases")
    s.chip(1500, 392, 380, 58, "hill-climbing")

    s.step = 2
    s.arrow([(1002, 115), (1058, 115)])
    s.shape(
        "agent", 1060, 18, 820, 197, "Analyzer team, three agents:\nfailed development questions"
    )

    s.step = 3
    s.arrow([(1470, 217), (1470, 258)])
    s.shape(
        "code", 1060, 260, 820, 120, "Overfit guard: no rule may copy\na question or a gold query"
    )
    s.arrow([(1058, 320), (1002, 320)])
    s.shape("store", 520, 260, 480, 120, "Two candidates;\nthe better one is kept")

    s.step = 4
    s.arrow([(760, 382), (760, 418)])
    s.shape(
        "code",
        520,
        420,
        940,
        280,
        "Promotion gate: all four, or blocked\n1  More holdout passes than the active version\n"
        "2  Zero confirmed regressions on both splits\n"
        "3  Human approval\n"
        "4  Every new rule passes the overfit guard",
        align="left",
        valign="top",
    )
    s.shape("human", 1510, 460, 370, 230, "Human\napproval", loop=None)
    s.arrow([(1508, 575), (1462, 575)])
    s.arrow([(518, 560), (462, 560)])
    s.shape("store", 40, 460, 420, 200, "Promoted: the\nnew active\nknowledge version")
    s.arrow([(250, 458), (250, 235), (600, 235), (600, 202)])
    # The label touches the return line it names.
    s.text(262, 280, "the next\nbaseline")
    return s


# --- 8. The run lifecycle (page only) ----------------------------------------------------------
STATES = {
    # state -> (kind, x, y, width, height)
    "received": ("state", 20, 400, 220, 70),
    "queued": ("state", 300, 400, 220, 70),
    "running": ("state", 580, 400, 220, 70),
    "verifying": ("state", 860, 400, 220, 70),
    "blocked_budget": ("stop", 300, 130, 220, 70),
    "escalated": ("stop", 580, 130, 220, 70),
    "failed": ("stop", 860, 130, 220, 70),
    "blocked_killswitch": ("stop", 20, 720, 220, 70),
    "awaiting_approval": ("human", 480, 680, 360, 150),
    "answered": ("state", 910, 720, 190, 70),
    "rejected": ("stop", 545, 930, 230, 70),
    "posted": ("terminal", 910, 930, 190, 70),
}

# (from, to) -> the points of its arrow, and where its number sits along it
ROUTES: dict[tuple[str, str], tuple[list[tuple[float, float]], float]] = {
    ("received", "queued"): ([(242, 435), (298, 435)], 0.5),
    ("queued", "running"): ([(522, 420), (578, 420)], 0.5),
    ("queued", "blocked_budget"): ([(410, 398), (410, 202)], 0.5),
    ("queued", "blocked_killswitch"): ([(330, 472), (160, 718)], 0.5),
    ("running", "queued"): ([(578, 455), (522, 455)], 0.5),
    ("running", "verifying"): ([(802, 420), (858, 420)], 0.5),
    ("running", "awaiting_approval"): ([(630, 472), (630, 686)], 0.45),
    ("running", "escalated"): ([(690, 398), (690, 202)], 0.5),
    ("running", "failed"): ([(770, 398), (880, 202)], 0.3),
    ("running", "blocked_budget"): ([(600, 398), (500, 202)], 0.5),
    ("running", "blocked_killswitch"): ([(600, 472), (230, 718)], 0.6),
    ("verifying", "running"): ([(858, 455), (802, 455)], 0.5),
    ("verifying", "answered"): ([(1000, 472), (1000, 718)], 0.5),
    ("verifying", "awaiting_approval"): ([(900, 472), (790, 732)], 0.5),
    ("verifying", "escalated"): ([(880, 398), (780, 202)], 0.3),
    ("verifying", "blocked_killswitch"): ([(870, 472), (840, 560), (250, 742)], 0.0),
    ("verifying", "failed"): ([(970, 398), (970, 202)], 0.5),
    ("awaiting_approval", "running"): ([(700, 696), (700, 472)], 0.45),
    ("awaiting_approval", "answered"): ([(812, 742), (908, 742)], 0.5),
    ("awaiting_approval", "rejected"): ([(660, 832), (660, 928)], 0.5),
    ("awaiting_approval", "blocked_killswitch"): ([(478, 755), (242, 755)], 0.5),
    ("answered", "posted"): ([(1005, 792), (1005, 928)], 0.5),
    ("answered", "awaiting_approval"): ([(908, 772), (802, 772)], 0.5),
}


def run_lifecycle() -> Scene:
    """platform/src/datapilot/contracts/lifecycle.py (RunStatus, TERMINAL, TRANSITIONS with the
    writer of each); loop3_events/lifecycle.py; loop3_events/api/events.py (the received row)."""
    s = Scene("run-lifecycle", height=PAGE_HEIGHT)
    transitions = lifecycle_transitions()
    if set(transitions) != set(ROUTES):
        raise SystemExit("run-lifecycle: ROUTES no longer match the TRANSITIONS of the contract")
    for state, (kind, x, y, w, h) in STATES.items():
        s.shape(kind, x, y, w, h, state, size=22)
    s.text(20, 300, "A run starts here,\nwritten by the api", size=20)
    s.arrow([(130, 352), (130, 398)])
    key = []
    for number, ((frm, to), by) in enumerate(transitions.items(), start=1):
        points, at = ROUTES[(frm, to)]
        if len(points) == 2:
            s.arrow(points, str(number), size=22, label_at=at)
        else:
            s.arrow(points, str(number), size=22)
        key.append(f"{number:>2}  {frm} to {to}, {by}")
    s.text(1135, 40, "Who writes each transition", size=26)
    s.text(1135, 88, "\n".join(key), size=20)
    s.legend(
        1135,
        720,
        [
            ("state", "The run goes on"),
            ("human", "A person decides"),
            ("terminal", "The run ends: posted"),
            ("stop", "The run ends without a post"),
        ],
    )
    s.text(
        1135,
        920,
        "Every change is checked against the contract\nand recorded as a run event"
        " in the same\ntransaction.",
        size=20,
    )
    return s


# --- 9. The warehouse data model (page only) ---------------------------------------------------
LINE = 22 * 1.25  # one table row at 22 pixels


def _row(table_y: float, index: int) -> float:
    """The middle of row `index` of a table drawn at `table_y` (row 0 is the table name)."""
    return table_y + 12 + LINE * (index + 0.5)


def _table(s: Scene, x: float, y: float, w: float, name: str, columns: list[str]) -> None:
    height = 24 + LINE * (len(columns) + 1)
    text = "\n".join([name, *columns])
    s.shape("store", x, y, w, height, text, size=22, align="left", valign="top", code=True)
    s.line([(x + 10, y + 12 + LINE + 2), (x + w - 10, y + 12 + LINE + 2)])


CUSTOMERS = [
    "customer_id",
    "first_name",
    "last_name",
    "email",
    "phone",
    "city",
    "state",
    "zip",
    "created_at",
    "ccpa_opt_out",
]
ORDERS = [
    "order_id",
    "customer_id",
    "order_ts",
    "status",
    "channel",
    "ship_state",
    "subtotal_cents",
    "discount_cents",
    "tax_amount",
    "shipping_cents",
    "total_cents",
]
ORDER_ITEMS = ["order_item_id", "order_id", "product_id", "quantity", "unit_price_cents"]
PRODUCTS = [
    "product_id",
    "sku",
    "name",
    "category_id",
    "list_price_cents",
    "cost_cents",
    "is_active",
]
CATEGORIES = ["category_id", "name", "parent_id"]


def warehouse_data_model() -> Scene:
    """platform/ops/sql/warehouse_schema.sql (tables and columns); warehouse_indexes.sql (keys and
    the customers_marketable view); platform/planted/registry.yaml (data-traps,
    total-cents-column, undocumented-status, utc-boundary-orders, internal-accounts-top-spenders,
    prompt-injection-product-names, near-duplicate-product-names);
    platform/packs/datapilot_us/benchmark/business_rules.md (business rules 1 to 6);
    pack.yaml (personal_data columns)."""
    s = Scene("warehouse-data-model", height=PAGE_HEIGHT)
    cx, cy, ox, oy, rx = 60, 80, 690, 80, 1200
    _table(s, cx, cy, 330, "customers", CUSTOMERS)
    _table(s, ox, oy, 340, "orders", ORDERS)
    _table(s, rx, 80, 330, "order_items", ORDER_ITEMS)
    _table(s, rx, 330, 330, "products", PRODUCTS)
    _table(s, rx, 640, 330, "categories", CATEGORIES)

    # Keys: each arrow runs from a column to the column it joins.
    s.arrow([(ox - 2, _row(oy, 2)), (cx + 332, _row(cy, 1))])
    s.arrow([(rx - 2, _row(80, 2)), (ox + 342, _row(oy, 1))])
    s.arrow(
        [
            (rx + 332, _row(80, 3)),
            (rx + 360, _row(80, 3)),
            (rx + 360, _row(330, 1)),
            (rx + 334, _row(330, 1)),
        ]
    )
    s.arrow(
        [
            (rx + 332, _row(330, 4)),
            (rx + 375, _row(330, 4)),
            (rx + 375, _row(640, 1) - 4),
            (rx + 334, _row(640, 1) - 4),
        ]
    )
    s.arrow(
        [
            (rx + 332, _row(640, 3)),
            (rx + 348, _row(640, 3)),
            (rx + 348, _row(640, 1) + 6),
            (rx + 334, _row(640, 1) + 6),
        ]
    )

    # Personal data: a small diamond on each column a query must not read without approval.
    for index in (2, 3, 4, 5):
        s.shape("human", cx + 290, _row(cy, index) - 12, 28, 24)

    s.shape(
        "store",
        cx,
        560,
        330,
        150,
        "customers_marketable, a view:\ncustomers who may receive\nmarketing, without opt-outs\n"
        "and internal accounts",
        size=20,
    )
    s.arrow([(225, cy + 24 + LINE * 11 + 2), (225, 558)])

    # The traps, each pointing at the column where it hides.
    s.shape(
        "stop",
        410,
        250,
        260,
        200,
        "Trap: internal\naccounts. Email at\nharborpine.com, in\nmixed case; three\n"
        "are among the top\n"
        "10 spenders",
        size=20,
    )
    s.arrow([(408, 300), (cx + 332, _row(cy, 4))])
    traps = [
        # (top, height, text, target row in orders, lane x)
        (
            470,
            120,
            "Trap: net revenue. Revenue is\nsubtotal_cents minus discount_cents;\n"
            "total_cents adds tax and shipping",
            _row(oy, 11),
            1050,
        ),
        (
            610,
            100,
            "Trap: cancelled orders. Status 5\nmeans cancelled; no table or\ncomment says so",
            _row(oy, 4),
            1080,
        ),
        (
            730,
            130,
            "Trap: Eastern time. order_ts is stored\nin Coordinated Universal Time (UTC);"
            " an\nevening order falls on the next UTC date",
            _row(oy, 3) + 4,
            1110,
        ),
        (
            880,
            120,
            "Trap: fiscal year. It runs February 1\nto January 31 and is named by the\n"
            "year it ends in",
            _row(oy, 3) - 4,
            1140,
        ),
    ]
    for top, height, text, target, lane in traps:
        s.shape("stop", 560, top, 470, height, text, size=20)
        mid = top + height / 2
        s.arrow([(1032, mid), (lane, mid), (lane, target), (ox + 342, target)])
    s.shape(
        "stop",
        1600,
        370,
        280,
        150,
        "Trap: product names.\nThree carry prompt-\ninjection text; two\ndiffer by one space",
        size=20,
    )
    s.arrow([(1598, _row(330, 3)), (rx + 334, _row(330, 3))])

    s.legend(
        60,
        790,
        [
            ("store", "A table or a view"),
            ("stop", "A trap: a naive answer goes wrong"),
            ("human", "Personal data: a person approves"),
        ],
    )
    s.text(
        60,
        940,
        "Arrows join a column to the key\nit names. Money columns hold\nwhole cents,"
        " tax_amount too.",
        size=20,
    )
    return s


LOOPS = ("agent", "verification", "event", "hill-climbing")

DIAGRAMS: list[Spec] = [
    Spec("diagram-style", "docs/diagrams", diagram_style),
    Spec("system-architecture", "docs/diagrams", system_architecture),
    Spec("four-loops", "docs/diagrams", four_loops, steps=True, highlights=LOOPS),
    Spec("text-to-sql-architecture", "docs/diagrams", text_to_sql_architecture),
    Spec("run-lifecycle", "docs/diagrams", run_lifecycle),
    Spec("warehouse-data-model", "docs/diagrams", warehouse_data_model),
    Spec("agent-loop", "section-1-agent-loop/diagrams", agent_loop, steps=True),
    Spec(
        "verification-layers",
        "section-2-verification-loop/diagrams",
        verification_layers,
        steps=True,
    ),
    Spec("event-loop", "section-3-event-loop/diagrams", event_loop, steps=True),
    Spec(
        "hill-climbing-loop",
        "section-4-hill-climbing-loop/diagrams",
        hill_climbing_loop,
        steps=True,
    ),
]
