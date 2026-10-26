"""The course diagrams, written as code so every label can be traced to the file it comes from.

Each function builds one scene on the 1920 by 1080 panel. `export_diagrams.py --build` measures the
labels in the browser, writes the .excalidraw sources (and the step frames when `steps` is set),
and renders them. After that the .excalidraw file is the source: open it at excalidraw.com to
edit it, or change the function here and build again (a build overwrites hand edits).

The facts on each diagram come from the files named in its docstring (paths from the repository
root); each diagrams/README.md lists them again beside the embed snippet.
"""

from __future__ import annotations

import importlib.util
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from scene import Scene

REPO = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class Spec:
    name: str
    folder: str
    build: Callable[[], Scene]
    steps: bool = False


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


# --- 1. System architecture ----------------------------------------------------------------------
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
    s = Scene("system-architecture")
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
    s.shape("outside", 50, 60, 340, 90, "Webhook sender")
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
    s.legend(40, 820, LEGEND)

    # Row 2: the worker and the hill-climbing loop runner.
    s.shape("boundary", 920, 60, 480, 380)
    s.text(944, 72, "Worker: one job at a time", size=26)
    s.shape("agent", 950, 116, 420, 86, "Analyst agent", size=26)
    s.shape("agent", 950, 214, 205, 100, "Schema\nscout agent", size=22)
    s.shape("agent", 1165, 214, 205, 100, "Reviewer\nagent", size=22)
    s.shape("code", 950, 330, 420, 92, "Seven graders and the\nread-only executor", size=24)

    s.shape("boundary", 1440, 60, 460, 380)
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
        "Two candidates, one kept on dev\nPromotion, then clearance re-runs\n"
        "Gold checks of live runs\nOne runner per database",
        size=20,
    )

    # Row 3: the services outside, and the data the agents read.
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
    s.arrow([(392, 410), (465, 410), (465, 880), (478, 880)], dashed=True)
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
    s.arrow([(1300, 782), (1300, 818)], dashed=True)
    return s


# --- 2. The four loops as one system -------------------------------------------------------------
def four_loops() -> Scene:
    """platform/src/datapilot/loop1_agent/{analyst,scout}.py; loop2_verification/{loop,
    reviewer}.py; loop3_events/{router,api/events,worker,autonomy,killswitch,reaper}.py;
    loop4_hill_climbing/{analyzer,candidates,overfit_guard,gate,runner}.py; pack.yaml
    (analyzer.candidates 2); platform/packs/datapilot_us/benchmark/{dev,holdout}.yaml (25 and 15
    items)."""
    s = Scene("four-loops")
    # Step 1: Section 1: Agent loop.
    s.step = 1
    s.shape("boundary", 90, 390, 560, 630)
    s.text(112, 402, "Section 1: Agent loop", size=26)
    s.shape("outside", 110, 460, 160, 70, "Question", size=24)
    s.shape("agent", 300, 445, 330, 100, "Analyst agent", size=26)
    s.shape("code", 110, 590, 250, 120, "Tools: list_tables,\ndescribe_table,\nrun_query", size=20)
    s.shape("agent", 390, 590, 240, 120, "Schema\nscout agent", size=22)
    s.shape("store", 110, 905, 510, 90, "Active knowledge version,\nadded to every prompt", size=22)
    s.arrow([(272, 495), (298, 495)])
    s.arrow([(330, 540), (280, 588)], both=True)
    s.arrow([(530, 546), (520, 588)], both=True)
    s.arrow([(375, 903), (375, 548)])

    # Step 2: Section 2: Verification loop.
    s.step = 2
    s.shape("boundary", 60, 330, 1030, 710)
    s.text(84, 342, "Section 2: Verification loop", size=26)
    s.shape("code", 670, 440, 180, 150, "Seven\ngraders:\nevery query,\nthen the\nanswer", size=20)
    s.shape("agent", 880, 440, 200, 150, "Reviewer\nagent: after\nthe graders", size=20)
    s.shape(
        "stop", 670, 640, 190, 150, "Failed: retry\nwith feedback,\nescalated at\nthe cap", size=20
    )
    s.shape("human", 870, 620, 210, 140, "Human\napproval", size=22)
    s.arrow([(632, 495), (668, 495)])
    s.arrow([(852, 515), (878, 515)])
    s.arrow([(760, 592), (760, 638)])
    s.arrow([(975, 592), (975, 620)])

    # Step 3: Section 3: Event loop.
    s.step = 3
    s.shape("boundary", 30, 30, 1290, 1020)
    s.text(54, 42, "Section 3: Event loop", size=26)
    s.shape("outside", 60, 100, 230, 110, "Event: webhook,\nschedule, or\nconsole", size=22)
    s.shape("code", 320, 100, 250, 110, "Idempotent\ninsert: one run\nper event", size=22)
    s.shape("code", 600, 100, 200, 110, "Router: a\nfixed table", size=24)
    s.shape("no-agent", 590, 222, 220, 96, "No agent\nhere", size=22)
    s.shape("store", 830, 100, 220, 110, "Jobs table:\nclaim, lease,\nheartbeat", size=22)
    s.shape("code", 1080, 100, 220, 110, "Reaper:\nrequeues an\nexpired lease", size=22)
    s.shape("code", 1110, 440, 190, 130, "Autonomy\npolicy: post\nor hold", size=22)
    s.shape("outside", 1110, 610, 190, 90, "Channel\npost", size=22)
    s.shape(
        "stop",
        1110,
        750,
        190,
        150,
        "Kill switch:\nchecked at\nclaim and\nbefore every\ncall",
        size=20,
    )
    s.arrow([(292, 155), (318, 155)])
    s.arrow([(572, 155), (598, 155)])
    s.arrow([(802, 155), (828, 155)])
    s.arrow([(1052, 155), (1078, 155)], both=True)
    s.arrow([(940, 212), (940, 380)])
    s.text(952, 250, "the worker\nclaims a job", size=20)
    s.arrow([(1082, 515), (1108, 515)])
    s.arrow([(1205, 572), (1205, 608)])

    # Step 4: Section 4: Hill-climbing loop.
    s.step = 4
    s.shape("boundary", 1350, 30, 540, 1020)
    s.text(1374, 42, "Section 4: Hill-climbing loop", size=26)
    s.shape("store", 1380, 96, 480, 84, "Benchmark: 25 dev items,\n15 holdout items", size=22)
    s.shape(
        "code",
        1380,
        208,
        480,
        90,
        "Experiment runner and evaluator:\nexecution match on two databases",
        size=20,
    )
    s.shape("agent", 1380, 326, 140, 104, "Failure\nanalyst", size=20)
    s.shape("agent", 1550, 326, 140, 104, "Rule\nwriter", size=20)
    s.shape("agent", 1720, 326, 140, 104, "Critic", size=20)
    s.text(1380, 438, "Analyzer team: failed dev items only", size=20)
    s.shape(
        "code",
        1380,
        476,
        480,
        80,
        "Overfit guard: no quoted question,\nno copied gold query",
        size=20,
    )
    s.shape(
        "code",
        1380,
        584,
        480,
        72,
        "Two candidates, each run on dev;\nthe better one becomes the draft",
        size=20,
    )
    s.shape(
        "code",
        1380,
        684,
        480,
        128,
        "Promotion gate: more holdout passes,\nzero confirmed regressions, every\n"
        "new rule passes the overfit guard,\nand human approval",
        size=20,
    )
    s.shape("human", 1490, 836, 260, 116, "Human\napproval", size=22)
    s.arrow([(1620, 182), (1620, 206)])
    s.arrow([(1450, 300), (1450, 324)])
    s.arrow([(1522, 378), (1548, 378)])
    s.arrow([(1692, 378), (1718, 378)])
    s.arrow([(1800, 432), (1800, 474)])
    s.arrow([(1620, 558), (1620, 582)])
    s.arrow([(1620, 658), (1620, 682)])
    s.arrow([(1620, 814), (1620, 834)])
    s.arrow([(1620, 954), (1620, 985), (622, 985)])
    s.text(700, 995, "promoted: the new active version", size=20)
    return s


# --- 3. The agent loop ---------------------------------------------------------------------------
def agent_loop() -> Scene:
    """platform/src/datapilot/loop1_agent/analyst.py (create_agent, dynamic_prompt, limits,
    ToolStrategy(AnswerEnvelope)); loop1_agent/tools.py (the three tools, the row cap);
    loop1_agent/scout.py (scout_schema, catalog tools only, SchemaBrief, six model calls);
    platform/src/datapilot/contracts/answer.py; platform/packs/datapilot_us/pack.yaml (limits:
    row_cap 50, model_call_limit 12, tool_call_limit 16; budgets: tokens_per_run 60000)."""
    s = Scene("agent-loop")
    s.step = 1
    s.shape("outside", 50, 440, 220, 100, "Question", size=28)
    s.shape(
        "code",
        380,
        70,
        520,
        130,
        "Prompt on every model call:\nbase prompt, business date,\nactive knowledge version",
        size=24,
    )
    s.shape("agent", 390, 400, 500, 180, "Analyst agent", size=30)
    s.arrow([(272, 490), (388, 490)])
    s.arrow([(640, 202), (640, 398)], "dynamic_prompt", size=20)

    s.step = 2
    s.shape("boundary", 1000, 130, 360, 420)
    s.text(1020, 140, "Tools of the analyst", size=22)
    s.shape("code", 1020, 180, 320, 70, "list_tables", size=24)
    s.shape("code", 1020, 265, 320, 70, "describe_table", size=24)
    s.shape("code", 1020, 350, 320, 70, "run_query", size=24)
    s.arrow([(892, 480), (998, 480)], both=True)
    s.text(898, 412, "tool call\nand result", size=20)
    s.shape("code", 1430, 330, 440, 110, "Checker: graders, then\nthe read-only executor", size=24)
    s.arrow([(1362, 385), (1428, 385)], both=True)
    s.text(1368, 300, "every\nquery", size=20)
    s.text(
        1430,
        452,
        "returns at most 50 rows, the\ntotal row count, and a notice\nwhen rows were cut",
        size=20,
    )

    s.step = 3
    s.shape("code", 1020, 455, 320, 70, "scout_schema", size=24)
    s.shape("fence", 1400, 560, 480, 330)
    s.text(1420, 572, "Tool boundary of the schema scout", size=22)
    s.shape(
        "agent",
        1430,
        610,
        420,
        110,
        "Schema scout agent:\nnew for each call, no memory",
        size=22,
    )
    s.shape("code", 1430, 740, 200, 60, "list_tables", size=22)
    s.shape("code", 1650, 740, 200, 60, "describe_table", size=22)
    s.shape("stop", 1430, 815, 420, 60, "No run_query: it cannot query", size=22)
    s.arrow([(1342, 505), (1428, 660)], both=True)
    s.text(1150, 590, "question in,\nSchemaBrief out:\ntables, joins,\ncaveats", size=20)

    s.step = 4
    s.shape(
        "store",
        50,
        700,
        900,
        230,
        "Answer envelope, the structured output\n\nstatus: answered, needs_clarification,"
        "\nrefused, or escalated\nfinal_sql, columns, rows_preview, row_count"
        "\nanswer_text, assumptions, clarifying_question",
        size=24,
        align="left",
        valign="top",
    )
    s.arrow([(640, 582), (640, 698)])
    s.text(50, 960, "Next, Section 2: Verification loop checks the envelope.", size=24)

    s.step = 5
    s.shape(
        "stop",
        50,
        70,
        290,
        170,
        "Stops for every run:\n12 model calls,\n16 tool calls,\n60,000 tokens",
        size=24,
    )
    return s


# --- 4. The verification layers ------------------------------------------------------------------
def verification_layers() -> Scene:
    """platform/src/datapilot/loop2_verification/checker.py (grader order); graders/*.py (the seven
    graders and their numbers); executor.py (read-only, rolled back); loop.py (the answer stage, the
    reviewer after the graders, the retry cap, held answers); limits.py; reviewer.py;
    platform/src/datapilot/loop1_agent/guard.py (the stop before the model call);
    loop3_events/killswitch.py; platform/ops/sql/roles.sql; pack.yaml (max_retries 3,
    statement_timeout_ms 5000, tokens_per_run 60000)."""
    s = Scene("verification-layers")
    s.step = 1
    s.text(
        40,
        175,
        "Stage 1: every Structured Query Language (SQL) query the analyst sends to run_query",
        size=26,
    )
    xs = [40, 302, 564, 826, 1088, 1350, 1612]
    first = [
        "1 Parse:\none statement",
        "2 Statement\npolicy: SELECT\nonly",
        "3 Schema:\ntables and\ncolumns exist",
        "4 Cost: plan\nunder the\nlimits",
        "5 Personal\ndata: route\nto a person",
    ]
    for x, label in zip(xs, first, strict=False):
        s.shape("code", x, 230, 230, 120, label, size=22)
    for x in xs[:4]:
        s.arrow([(x + 232, 290), (x + 260, 290)])
        s.arrow([(x + 115, 352), (x + 115, 398)])
    s.shape(
        "stop",
        40,
        400,
        1022,
        100,
        "Blocked: the query does not run; the reason goes\nback to the analyst as feedback",
        size=22,
    )
    s.shape("human", 1100, 380, 210, 140, "Human\napproval", size=22)
    s.arrow([(1203, 352), (1203, 380)])

    s.step = 2
    s.shape("code", 1350, 230, 230, 120, "Read-only\nexecutor:\nrolled back", size=22)
    s.shape("code", 1612, 230, 230, 120, "6 Execution:\nerrors become\nfeedback", size=22)
    s.arrow([(1320, 290), (1348, 290)])
    s.arrow([(1582, 290), (1610, 290)])
    s.shape(
        "store",
        1350,
        385,
        492,
        95,
        "Agent database role: SELECT only,\nread-only transaction, 5,000\n"
        "millisecond statement timeout",
        size=20,
    )
    s.arrow([(1465, 352), (1465, 383)])
    s.shape("stop", 1350, 492, 492, 64, "Refused write: escalated at once, no retry", size=20)

    s.step = 3
    s.text(40, 570, "Stage 2: the answer envelope, once the analyst answers", size=26)
    s.shape("store", 40, 620, 300, 140, "Answer\nenvelope", size=26)
    s.shape("code", 400, 620, 340, 140, "Final query again\nthrough graders 1 to 6", size=22)
    s.shape("code", 800, 620, 300, 140, "7 Final answer:\nthe text matches\nthe rows", size=22)
    s.arrow([(342, 690), (398, 690)])
    s.arrow([(742, 690), (798, 690)])
    s.shape(
        "stop",
        400,
        830,
        700,
        130,
        "Failed: feedback to the analyst and a retry;\nafter 3 attempts the run ends escalated",
        size=22,
    )
    s.arrow([(570, 762), (570, 828)])
    s.arrow([(950, 762), (950, 828)])

    s.step = 4
    s.shape(
        "agent", 1160, 610, 360, 160, "Reviewer agent:\nonly after every\ngrader passed", size=22
    )
    s.shape("store", 1580, 630, 280, 120, "Answered:\nready to post", size=24)
    s.arrow([(1102, 690), (1158, 690)])
    s.arrow([(1522, 690), (1578, 690)])
    s.shape("human", 1250, 830, 260, 150, "Human\napproval", size=22)
    s.arrow([(1340, 772), (1380, 832)])
    s.text(
        1540,
        820,
        "It sees the question, the\nquery, a preview of the rows,\nand the knowledge, nothing"
        "\nelse. A concern goes back\nonce; if it persists, a\nperson decides.",
        size=20,
    )

    s.step = 5
    s.shape(
        "stop",
        40,
        40,
        1840,
        100,
        "Stop before every model call and every tool call, and end the run: the kill switch is"
        " engaged, the daily\ntoken budget is spent, the run has used its 60,000 tokens, or the"
        " database refused a write",
        size=24,
    )
    return s


# --- 5. The event loop ---------------------------------------------------------------------------
def event_loop() -> Scene:
    """platform/src/datapilot/loop3_events/api/events.py (ON CONFLICT, duplicates, one
    transaction); scheduler.py (digest:YYYY-MM-DD at 8 a.m. Eastern time); router.py; worker.py
    (claim, lease 30 seconds, heartbeat at a third of it, fenced finish, parked jobs, the checks at
    claim); router.py (ROUTES, DEFENSE_CHECK, job_route over extension.JOB_QUEUES); reaper.py;
    killswitch.py; approvals.py (AsyncPostgresSaver in schema lg, thread_id = run_id);
    api/control.py (POST /approvals/{run_id}); budget.py; platform/ops/sql/ops/001 and 002 (jobs
    columns, max_attempts 3); pack.yaml (tokens_per_day 2000000)."""
    s = Scene("event-loop")
    s.step = 1
    s.text(400, 30, "Idempotency key: event_id", size=26)
    s.shape("outside", 40, 80, 290, 100, "Webhook: event_id\nfrom the sender", size=22)
    s.shape(
        "code", 40, 210, 290, 110, "Scheduler: 8 a.m.\nEastern time,\ndigest:YYYY-MM-DD", size=22
    )
    s.shape("code", 40, 350, 290, 90, "Console", size=26)
    s.shape(
        "code",
        400,
        80,
        460,
        360,
        "POST /events\n\nINSERT ... ON CONFLICT\n(event_id) DO NOTHING\n\nA repeat: recorded in"
        "\nevent_duplicates, returns\nthe first run\n\nNew: event, job, and run\n"
        "in one transaction",
        size=22,
    )
    s.arrow([(332, 130), (398, 130)])
    s.arrow([(332, 265), (398, 265)])
    s.arrow([(332, 395), (398, 395)])

    s.step = 2
    s.shape(
        "code",
        400,
        480,
        460,
        182,
        "Router: a fixed table\nquestion.asked: default queue\nexport.requested: default queue"
        "\ndigest.requested: scheduled queue\na defense check: default queue\n"
        "a scheduled job: its listed queue",
        size=22,
    )
    s.shape("no-agent", 390, 672, 480, 90, "No agent: the route is a lookup", size=22)
    s.arrow([(630, 442), (630, 478)])
    s.shape(
        "store",
        940,
        80,
        420,
        330,
        "Jobs table\n\nstatus: queued, running,\nparked, done, dead\nattempts, max_attempts 3"
        "\nlease_owner, lease_until\nrun_after, queue",
        size=22,
    )
    s.arrow([(862, 200), (938, 200)])
    s.arrow([(862, 560), (950, 412)])
    s.shape(
        "code",
        1440,
        80,
        440,
        330,
        "Worker\n\n1. Claim: one short transaction,\nFOR UPDATE SKIP LOCKED,\na 30-second lease"
        "\n2. Heartbeat every 10 seconds\nwhile the run works\n3. Finish only while it still"
        "\nholds that lease",
        size=22,
    )
    s.arrow([(1362, 245), (1438, 245)], both=True)

    s.step = 3
    s.shape(
        "code",
        940,
        470,
        420,
        140,
        "Reaper: a lease that expired\ngoes back to the queue; after\n3 attempts the job is dead",
        size=22,
    )
    s.arrow([(1150, 468), (1150, 412)])
    s.shape(
        "stop",
        940,
        640,
        420,
        100,
        "Daily budget: checked before\neach claim, 2,000,000 tokens",
        size=22,
    )

    s.step = 4
    s.shape("human", 40, 800, 260, 160, "A person", size=24)
    s.shape(
        "code",
        360,
        800,
        400,
        160,
        "POST /approvals/{run_id}\napprove: the job goes\nback to the queue\nreject: the run ends",
        size=22,
    )
    s.shape("store", 820, 790, 330, 110, "Approvals table:\none open per run", size=22)
    s.shape("store", 820, 920, 330, 110, "Checkpoint in schema lg\nthread_id = run_id", size=22)
    s.shape(
        "code",
        1220,
        800,
        660,
        220,
        "Durable approval: the paused run lives in\nits checkpoint, not in the worker, so it"
        "\nsurvives a restart. The job waits as parked;\nafter approval the worker resumes the run"
        "\nfrom the checkpoint.",
        size=22,
    )
    s.arrow([(302, 880), (358, 880)])
    s.arrow([(762, 845), (818, 845)])
    s.arrow([(1152, 845), (1218, 845)])
    s.arrow([(1152, 975), (1218, 975)], both=True)

    s.step = 5
    s.shape(
        "stop",
        1440,
        470,
        440,
        220,
        "Kill switch: arm, then engage\nChecked at claim, before every\n"
        "model call, and before every"
        "\ntool call. Engaging it blocks\nruns waiting for approval and\n"
        "drops to the report-only level",
        size=20,
    )
    s.arrow([(1660, 468), (1660, 412)])
    return s


# --- 6. The hill-climbing loop -------------------------------------------------------------------
def hill_climbing_loop() -> Scene:
    """platform/packs/datapilot_us/benchmark/{dev,holdout}.yaml (25 and 15 items);
    platform/src/datapilot/loop4_hill_climbing/{evaluator,experiment,measurement,analyzer,
    overfit_guard,gate,candidates}.py; loop4_hill_climbing/runner.py (the gate records its baseline;
    a promotion after approval decides only against that baseline, while the active version is
    unchanged and the gate has finished); loop4_hill_climbing/store.py (record_gate_baseline,
    gate_baseline; migration 021); loop3_events/autonomy.py (eligibility and demotion);
    pack.yaml (evaluation: holdout_repeats 3, holdout_pass_threshold 2, dev_regression_reruns 2,
    dev_regression_threshold 2, holdout_regression_reruns 3, holdout_regression_fail_threshold 2,
    concurrency 8, overfit_question_words 6, overfit_sql_tokens 20; autonomy: metric_families,
    demote_after_consecutive_escalations 3).

    An apparent dev regression is re-run 2 more times under each version and counts only when the
    candidate fails 2 of 2 and the active version passes 2 of 2 (gate.find_regressions); an
    apparent holdout regression is re-run 3 more times under the candidate and counts when 2 of
    them fail."""
    s = Scene("hill-climbing-loop")
    s.step = 1
    s.shape("store", 40, 60, 400, 150, "Benchmark\ndev: 25 items\nholdout: 15 items", size=24)
    s.shape("store", 40, 250, 400, 110, "Two databases:\nwarehouse and warehouse_alt", size=22)
    s.shape(
        "code",
        520,
        60,
        520,
        300,
        "Experiment runner and evaluator\n\nholdout: 3 runs per version,\npasses on 2 of 3"
        "\ndev: 1 run\n8 runs at a time\nA pass: the answer's query returns\n"
        "the gold result on both"
        " databases",
        size=22,
    )
    s.arrow([(442, 135), (518, 135)])
    s.arrow([(442, 305), (518, 305)])

    s.step = 2
    s.shape("boundary", 1160, 40, 720, 470)
    s.text(1184, 52, "Analyzer team, run twice: failed dev items only", size=22)
    s.shape(
        "agent", 1190, 100, 320, 130, "Failure analyst:\ndiagnoses each\nfailed dev item", size=22
    )
    s.shape(
        "agent",
        1540,
        100,
        320,
        130,
        "Rule writer: sees the\ndiagnoses and the\nschema, proposes rules",
        size=22,
    )
    s.shape("agent", 1365, 300, 340, 150, "Critic: keeps,\nnarrows, or drops;\nnever adds", size=22)
    s.arrow([(1042, 135), (1188, 165)])
    s.text(1050, 72, "failed\ndev items", size=20)
    s.arrow([(1512, 165), (1538, 165)])
    s.arrow([(1700, 232), (1650, 302)])

    s.step = 3
    s.shape(
        "code",
        1160,
        550,
        720,
        120,
        "Overfit guard: rejects a rule that shares 6 words\nin a row with any benchmark question,"
        " or 20\nquery tokens in a row with any gold query",
        size=22,
    )
    s.arrow([(1535, 452), (1535, 548)])
    s.shape(
        "store",
        1160,
        710,
        720,
        140,
        "Two candidates, each measured on the dev split; the\ndraft is the one with fewer dev"
        " regressions, then\nmore dev passes, then fewer rules",
        size=22,
    )
    s.arrow([(1520, 672), (1520, 708)])

    s.step = 4
    s.shape(
        "code",
        520,
        420,
        560,
        260,
        "Promotion gate\n\n1. more holdout passes than the\nbaseline experiment of the active"
        "\nversion, recorded at the gate\n2. zero regressions on dev and\non holdout\n"
        "3. every new rule passes the\noverfit guard\n4. human approval",
        size=20,
    )
    s.arrow([(1158, 750), (1082, 600)])
    s.shape(
        "code",
        520,
        715,
        560,
        170,
        "Confirming runs, for an item that passed\nbefore and fails now\ndev: 2 more runs of each"
        " version; a\nregression if the candidate fails both\nand the active version passes both\n"
        "holdout: 3 more; a regression if 2 fail",
        size=20,
    )
    s.arrow([(800, 682), (800, 713)], both=True)
    s.text(40, 372, "An approval given before the\ngate finishes waits for it", size=20)
    s.shape("human", 40, 440, 400, 200, "Human\napproval", size=26)
    s.arrow([(518, 540), (442, 540)])
    s.shape("store", 40, 690, 400, 100, "Active knowledge version:\nthe next baseline", size=22)
    s.arrow([(240, 642), (240, 688)])

    s.step = 5
    s.shape(
        "code",
        40,
        900,
        1840,
        140,
        "Autonomy per metric family: revenue, orders, average order value, customers, products."
        " A family\nreaches the unattended level only when every holdout item of the family passes"
        " 2 of 3 runs\nunder the active version (an item that falls short, 2 of 3 more); other"
        " families get the assisted level.\nA spent daily budget, 3 escalations in a row, or the"
        " kill switch drops the system to the report-only level.",
        size=22,
    )
    s.arrow([(240, 792), (240, 898)])
    return s


# --- 7. The run lifecycle ------------------------------------------------------------------------
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
    s = Scene("run-lifecycle")
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


# --- 8. The warehouse data model -----------------------------------------------------------------
LINE = 22 * 1.25  # one table row at 22 pixels


def _row(table_y: float, index: int) -> float:
    """The middle of row `index` of a table drawn at `table_y` (row 0 is the table name)."""
    return table_y + 12 + LINE * (index + 0.5)


def _table(s: Scene, x: float, y: float, w: float, name: str, columns: list[str]) -> None:
    height = 24 + LINE * (len(columns) + 1)
    s.shape(
        "store", x, y, w, height, "\n".join([name, *columns]), size=22, align="left", valign="top"
    )
    s.line([(x + 10, y + 12 + LINE + 2), (x + w - 10, y + 12 + LINE + 2)], width=1)


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
    s = Scene("warehouse-data-model")
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
    s.arrow([(225, cy + 24 + LINE * 11 + 2), (225, 558)], dashed=True)

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


DIAGRAMS: list[Spec] = [
    Spec("system-architecture", "docs/diagrams", system_architecture),
    Spec("four-loops", "docs/diagrams", four_loops, steps=True),
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
