"""Section 4: Hill-climbing loop, 3:03-3:45, 42 minutes, under design system 2.

The second rebuild (27 October 2026): the opener, four pattern slides (evaluation-driven development
and gold datasets; development and holdout splits with repeated runs; regressions, overfitting and
Goodhart's law; promotion gates, autonomy per capability and model drift), the pattern in code,
DataPilot's gate, the DEMO slide, the one evidence slide, the design callout, apply it, pitfalls,
and the recap with the complete scoreboard. Course numbers come from the deck evidence (entries E40
to E56, named in each slide's src) and the number reconciliation of the second rebuild; external
claims carry a source marker numbered as the deck's source list ([1] to [54], and [55] to [118]
from the second rebuild's verified sources). The opener reads the baseline and the naive
analyzer's verdict, then starts the hill-climbing chain (about 3:05); it runs while the pattern and
code slides are taught, so the DEMO slide reads its results. Review round 1 rulings applied (2, 3,
4, 10, 12, 13, 14, 17, 18).
"""

RULES = "design system 2"

DEMO_PAGE = "https://github.com/ANI-IN/loop-engineering/tree/main/section-4-hill-climbing-loop/demo"
EXPECTED = "section-4-hill-climbing-loop/demo/expected/"

# Ending a running hill-climbing request (round 3 ruling 1): stop, reset, start, never restart.
STOP_RESET_START = (
    "stop, reset, start: docker compose stop hill-climbing-runner (about 11 seconds), then make "
    "reset NAME=hill-climbing-loop (about 7 seconds), then docker compose start "
    "hill-climbing-runner (about 3 seconds), about 20 seconds in all. Never restart the runner: a "
    "restarted runner keeps serving, so the reset refuses again."
)

# Review round 1, ruling 17: no new chain after 3:17 (8 to 14 minutes to the gate, plus up to 3 for
# approval and the last run), and every 3:34 exit says which minutes pay for the return.
LAST_CHAIN = (
    "A fresh chain needs about 8 to 14 minutes to the gate, plus up to 3 minutes for approval and "
    "the last run: start no new chain after 3:17; when the demo slot starts, say so, go on to "
    "the evidence slide, and read the class chain at the Thursday review."
)
EXIT_3_34 = (
    "If it has not landed by 3:34, go on to the evidence slide, return when it lands, and pay for "
    "it by skipping the room questions on the evidence, design, apply-it, pitfalls and recap "
    "slides."
)

# Round 3 ruling 6: who approved version 13 in the published run.
APPROVED_13 = (
    "approved at the gate's approval step in rehearsal on 24 October, by the build session "
    "standing in for the instructor"
)

SLIDES = [
    # 1 section opener: the failure, felt; the chain starts here --------------------------------
    dict(
        kind="opener",
        title="Section 4: Hill-climbing loop",
        minutes=3,
        says="A fix that sounds right breaks working answers; read the break's results, start "
        "the chain",
        src="section-4-hill-climbing-loop/README.md; evidence E42, E46, E47 "
        "(docs/calibration-report.md, The over-broad rule); knowledge/v2-overbroad.yaml; the "
        "poll; Section 3's scoreboard; review round 1 rulings 12, 17, 18",
        on_slide=[
            "Fixes: one plausible new rule broke 9 of the 40 benchmark answers, with no error",
            "Insight: Judge a change by every question, not by the one it fixed.",
        ],
        notes=[
            "Purpose: Make the failure felt and start the chain. Cue, not to say: if the reset "
            "prints not reset, wait; by 3:06 stop, reset, start.",
            "What to say: Section 3 ended: it runs safely unattended, but it is still wrong. The "
            "poll: [number] of you have a hill-climbing loop, [number] none of the four. If most "
            "chose none, watch the gold set: a few checked questions are what you build first, "
            "and the gate is a few lines around them. The failure: revenue came out wrong, so "
            "someone adds a sensible rule, exclude discounted orders. Measured on every "
            "question, it broke 9 that used to pass, with no error. Two results from the break. "
            "The baseline: version 1, the starting knowledge, passes 2 of 15 holdout questions. "
            "The naive analyzer, a careless improver that quotes each failed question as a "
            "rule: blocked, because the overfit guard, code that rejects rules copying a test "
            "question, flags every rule; here is one. Now I reset, which keeps the baseline, and "
            "press Run analyzer, then Run experiment.",
            "The point to land: Patching what just failed breaks what was working; only judging "
            "every change by every question shows it.",
            "Example: The count on the slide is the over-broad rule's measured run of 24 October: "
            "added to version 11, it lowered holdout passes from 12 to 7 of 15 and left 9 "
            "confirmed regressions, 4 development and 5 holdout, among the 40 benchmark "
            "questions; its SQL guidance kept only orders with no discount, and discounted orders "
            "are real sales. The gate blocked it on both counts.",
            'Ask the room: "How does your team decide today that a prompt change is better?" '
            "Expect: a few manual checks, or the questions that just failed.",
            "Misconceptions: That a rule that reads well is safe to ship. The over-broad rule "
            "read like policy; only measuring every question showed what it broke.",
            "Transition: The first pattern: judge every change against a gold dataset.",
        ],
    ),
    # 2 pattern: evaluation-driven development; gold datasets ------------------------------------
    dict(
        kind="pattern",
        title="Evaluation-driven development on a gold dataset",
        minutes=3,
        says="Write checked gold questions first and judge every change by the whole set",
        src="docs/diagrams/patterns/README.md (pattern-eval-driven); sources 105, 106, 107, 45; "
        "evidence E42",
        figure={
            "diagram": "pattern-eval-driven",
            "alt": "Evaluation-driven development: a gold dataset of questions with checked "
            "answers; run the agent on every question; score each answer against its gold "
            "answer; read the failures; change one thing, a prompt, a tool, or a rule; run "
            "again; each new failure becomes a gold question",
        },
        on_slide=[
            "Definition: Write checked gold questions first; judge every change by the whole set.",
            "Use when: answers can be checked",
            "Avoid when: nobody can say what right means",
            "Elsewhere: OpenAI and Anthropic both recommend evaluation-driven "
            "development[^105][^106]",
        ],
        notes=[
            "Purpose: Define evaluation-driven development and the gold dataset, the instrument "
            "every later pattern in this section depends on.",
            "What to say: The problem in general terms: you change a prompt, a tool, or a rule, "
            "try three questions, and they look better. That is a feeling, not a measurement; "
            "OpenAI's guide calls it a vibe-based evaluation, Source 105. The pattern is "
            "evaluation-driven development. Walk the diagram from the left. A gold dataset: "
            "questions with answers a person has checked. Run the agent on every question. "
            "Score each answer against its gold answer, by the executed result, as Section 2 "
            "taught, not by the query text. Read the failures. Change one thing. Run the whole "
            "set again. Bottom left: each new failure from production becomes a gold question, "
            "so the set grows with what really goes wrong. How many questions? Anthropic says 20 "
            "to 50 tasks drawn from real failures is a great start, Source 106; Databricks "
            "suggests 10 to 20 for a Genie Agent, Source 45. Alternatives: judging by a model, "
            "which suits open text but shares the agent's blind spots; and monitoring "
            "production, which finds failures only after users meet them. Use both alongside "
            "the gold set, not instead of it. DataPilot's gold set has 40 questions, each with "
            "a hand-written gold query.",
            "The point to land: Write the gold questions before the change, and judge the change "
            "by all of them, never by the case that prompted it.",
            "Example: A coding agent works the same way: a suite of real bug reports, each with "
            "a test a person checked; a prompt change ships only when the whole suite is re-run. "
            "This example is illustrative. Anthropic's sourced case grades a booking agent by "
            "whether the reservation exists in the database, Source 106.",
            'Ask the room: "Where would your first 20 gold questions come from?" Expect: support '
            "tickets, analysts' saved queries, past incidents.",
            "Misconceptions: That the agent can write its own gold answers. Then the set measures "
            "agreement with itself; a person checks every gold answer, and the set should look "
            "like real traffic, which OpenAI warns about as biased design, Source 105.",
            "Transition: A gold set alone is not enough: which questions you learn from, and how "
            "often you run each one, decide what the score means.",
        ],
    ),
    # 3 pattern: development and holdout splits; run-to-run variation -----------------------------
    dict(
        kind="pattern",
        title="Development and holdout splits, and repeated runs",
        minutes=3,
        says="Learn on development questions, decide on unseen holdout ones, count passes over runs",
        src="docs/diagrams/patterns/README.md (pattern-dev-holdout); sources 108, 109, 110, 111, "
        "112; evidence E41, E45, E49; analyzer.py lines 206-208",
        figure={
            "diagram": "pattern-dev-holdout",
            "alt": "Development and holdout splits: gold questions split into development, where "
            "you read the failures and change things, and holdout, never read, which decides "
            "what ships; beside it, one question run three times passes, fails, and passes, so "
            "count passes over repeated runs: 2 of 3, since one run is only a sample",
        },
        on_slide=[
            "Definition: Learn on development questions; let unseen holdout ones decide, over "
            "runs.",
            "Use when: anything learns from your failures",
            "Avoid when: repeats, if outputs never vary",
            "Elsewhere: LangSmith evaluates on dataset splits, with repetitions for "
            "noise[^108][^109]",
        ],
        notes=[
            "Purpose: Define development and holdout splits and run-to-run variation. Cue, not "
            "to say: at 3:11, glance at the Improve page; the analyzer team should be finishing.",
            "What to say: Two problems in general terms. First, if the questions you study are "
            "the questions that decide, the score measures your memory of them. Second, a model "
            "can answer the same question differently from run to run, so one run is a sample, "
            "not a verdict. Walk the diagram. On the left, the gold questions split in two. "
            "Development questions: you read their failures and change things. Holdout "
            "questions: nobody who writes rules ever reads them, and they decide what ships. On "
            "the right, one question run three times: pass, fail, pass. Count passes over "
            "repeated runs, 2 of 3, and treat one failure as a reason to re-run, not as proof. "
            "How large is the noise? Thinking Machines got 80 different completions from 1,000 "
            "runs of one prompt at temperature zero, Source 111, and Atil and others saw "
            "accuracy vary by up to 15 percent across runs, Source 112. Never skip the split; "
            "skip the repeats only when the output never varies. Alternatives and "
            "trade-offs: rotating the split suits a small set but leaks over time; repeats cost "
            "tokens and reduce noise per question, while only more questions narrow the "
            "uncertainty of the total. Google warns that test sets wear out with repeated use, "
            "Source 110: refresh yours. DataPilot keeps 25 development and 15 holdout questions; "
            "its analyzer team, three agents, a failure analyst that diagnoses, a rule writer "
            "that proposes, and a critic that keeps, narrows or drops each rule, refuses a "
            "holdout question in code.",
            "The point to land: The questions you learn from never decide; the questions that "
            "decide are never studied; and one run is only a sample.",
            "Example: A support agent's prompt team reads only last quarter's development "
            "tickets; a held-out set of tickets, run three times each, decides whether a new "
            "prompt ships. This example is illustrative.",
            'Ask the room: "Who on your team can read your test set today?" Expect: everyone, '
            "which is the problem.",
            "Misconceptions: That temperature zero makes runs repeatable. It does not, as Source "
            "111 measured; and splitting after you have read the failures is no split at all.",
            "Transition: Even with a clean split, a better total can hide two failures: a "
            "regression, and rules that learned the test.",
        ],
    ),
    # 4 pattern: regressions; overfitting and Goodhart's law --------------------------------------
    dict(
        kind="pattern",
        title="Regressions, overfitting and Goodhart's law",
        minutes=3,
        says="Count broken answers on their own, and distrust a score you optimise against",
        src="docs/diagrams/patterns/README.md (pattern-goodhart); sources 113, 114, 115, 106, 40; "
        "evidence E46, E48",
        figure={
            "diagram": "pattern-goodhart",
            "alt": "Regressions: a change to the agent fixes three questions and fails one that "
            "used to pass; count a regression on its own, since a net gain can hide it; "
            "Goodhart's law, when a measure becomes a target, it stops being a good measure: a "
            "rule that copies a gold question's wording sends the development score up while "
            "the holdout score stays flat; overfit, it learned the test, not the task",
        },
        on_slide=[
            "Definition: Count each pass that now fails on its own; a score you aim at stops "
            "measuring[^113].",
            "Use when: working answers can break",
            "Avoid when: nothing passes yet to regress",
            "Elsewhere: Snowflake's Cortex Analyst counts verified queries now failing[^40]",
        ],
        notes=[
            "Purpose: Define regressions, overfitting and Goodhart's law, and show how both hide "
            "inside a better total.",
            "What to say: The problem: a total can rise while the system gets worse. Walk the "
            "left half. A change fixes three questions and breaks one that used to pass. The "
            "total goes up by two, and the broken answer is invisible unless you count it on its "
            "own. That is a regression: a question that passed under the active version and "
            "fails under the candidate, confirmed by re-runs so noise is not mistaken for it. "
            "One honest cost: if only apparent regressions are re-run and new passes are not, "
            "confirmation leans toward the candidate; re-run both. "
            "Anthropic says a regression suite should pass at nearly 100 percent, Source 106. "
            "Now the right half: Goodhart's law. In Marilyn Strathern's phrasing, when a measure "
            "becomes a target, it ceases to be a good measure; we cite it through Mattson and "
            "others, 2021, Source 113, with Strathern's 1997 paper, Source 114. A rule that "
            "copies a gold question's wording lifts the development score; the holdout stays "
            "flat, or rises if it shares the rules. It learned the test, not the task: "
            "overfitting, so check how each rule was written. Alternatives: refresh the "
            "holdout, keep a final set nobody reads, or check how rules were written. The "
            "worked case is the naive analyzer you saw blocked at the start: it once wrote rules "
            "that quoted failed development questions with their gold queries, and its version "
            "passed every holdout question, because our holdout shares its five business rules "
            "with development. A holdout score can pass rules copied from the test. So DataPilot "
            "added an overfit guard, code that rejects a rule sharing 6 consecutive words with a "
            "question or 20 consecutive SQL tokens with a gold query.",
            "The point to land: Count regressions separately, and when a score is the target, "
            "check how it was reached, not only what it reads.",
            "Example: A coding agent asked to make failing tests pass can special-case the test "
            "inputs: every test goes green and the bug stays. This example is illustrative.",
            'Ask the room: "Would your dashboard show one broken answer inside a net gain of '
            'two?" Expect: no, only the total.',
            "Misconceptions: That a perfect holdout score proves learning. On 23 October copied "
            "rules passed 15 of 15 and the gate of three conditions said ready; it was not "
            "approved, and the guard became a fourth condition. Since then the naive analyzer "
            "was blocked in 6 of 6 runs, but those scored 0 to 2 of 15, so the guard has not yet "
            "met a high-scoring copied version live.",
            "Transition: Now the gate that turns these checks into a decision, with a person, "
            "per capability, and watched for drift.",
        ],
    ),
    # 5 pattern: promotion gates, autonomy per capability, model drift ---------------------------
    dict(
        kind="pattern",
        title="Promotion gates, earned autonomy and drift checks",
        minutes=3,
        says="Promote on recorded checks and a person; grant autonomy per capability; watch drift",
        src="docs/diagrams/patterns/README.md (pattern-promotion-gate); sources 116, 117, 118; "
        "evidence E40, E51; eligibility.py confirmed_clearance; benchmark holdout.yaml",
        figure={
            "diagram": "pattern-promotion-gate",
            "alt": "A promotion gate: a candidate version passes a promotion gate, better on "
            "holdout with no regressions, then a person approves, and it is promoted with its "
            "autonomy earned; autonomy is set per capability, for example sales totals "
            "unattended and customer lists report-only; scheduled gold re-runs catch model "
            "drift, a drop with no change of yours, and lower the autonomy",
        },
        on_slide=[
            "Definition: Promote only on recorded checks and a person; grant autonomy per "
            "capability.",
            "Use when: changes reach users unreviewed",
            "Avoid when: a person checks every output",
            "Elsewhere: GitHub environments hold a deployment for a required reviewer[^117]",
        ],
        notes=[
            "Purpose: Define the promotion gate and drift. Cue, not to say: stalled at 3:17? "
            "Stop, reset, start. After 3:17 start none; at the demo, say so; go to evidence.",
            "What to say: The problem: a better candidate still has to be trusted, and trust is "
            "not one switch. Walk the top row. A candidate version reaches the promotion gate: "
            "better on the holdout, no regressions. Then a named person approves the diff, and "
            "only then is it promoted. Google's MLOps guide says the same for models: make sure "
            "the new model performs better than the current one before promoting it, Source "
            "116. The bottom left: autonomy is earned per capability, not per system. Sales "
            "totals can run unattended while customer lists stay report-only. The bottom right: "
            "model drift. A model's behaviour can change behind the same name: Chen, Zaharia and "
            "Zou saw one model's answers on the same prime-number task change sharply between "
            "March and June 2023, Source 118. A drop with no change of yours is drift; scheduled "
            "gold re-runs catch it, and the same measurement that granted autonomy lowers it. "
            "The course's advice, not a vendor's: record the exact model version you run, and "
            "compare only runs from the same session. Alternatives: a person reviewing every "
            "output, safe but slow; or automatic promotion, fast and unaccountable. In "
            "DataPilot, autonomy is granted per metric family, a group of questions about one "
            "measure, such as revenue or orders. A family clears when every one of its holdout "
            "questions passes 2 of 3 runs, one that falls short passing 2 of 3 more. Revenue "
            "cleared on its 4 holdout questions; orders never did.",
            "The point to land: A gate decides on evidence, a named person approves, and autonomy "
            "is granted per capability and taken back by the same measurement.",
            "Example: A workflow agent that handles invoices could send payment reminders "
            "unattended while refunds stay at the assisted level until refunds earn more. This "
            "example is illustrative.",
            'Ask the room: "Which capability of your agent would you grant the unattended level '
            'first?" Expect: read-only summaries; never money or personal data.',
            "Misconceptions: That a cleared family is proven. Average order value has a single "
            "holdout question, and class code would clear it on that alone, which is why "
            "Assignment 4 requires at least three; and the family comes from a keyword table, "
            "so a misrouted question takes its family's level.",
            "Transition: Here is the whole gate as eight lines of generic code.",
        ],
    ),
    # 6 the pattern in code: a generic promotion gate (ruling 4) ---------------------------------
    dict(
        kind="mechanism",
        title="The pattern in code: a promotion gate",
        minutes=2,
        says="One session, a margin above noise, zero regressions, and a named person signing last",
        src="generic pseudocode written for the course, after the gate's decide; review round 1 "
        "ruling 4",
        code={
            "language": "python",
            "panel": "Pattern",
            "origin": "generic pseudocode written for the course, in Python syntax",
            "lines": [
                "def gate(active, candidate, regressions, approvals, min_gain=2):",
                '    if active.session != candidate.session: raise ValueError("one session")',
                "    gain = candidate.holdout_passes - active.holdout_passes",
                "    flags = overfit_flags(candidate.rules)",
                "    ready = gain >= min_gain and not regressions and not flags",
                "    if not ready: return blocked(gain, regressions, flags)",
                "    approvals.request(candidate.diff_hash)",
                '    return "ready"',
            ],
            "marks": [
                (1, "active.session != candidate.session", 1),
                (4, "gain >= min_gain", 2),
                (4, "not regressions", 3),
                (6, "approvals.request(candidate.diff_hash)", 4),
            ],
        },
        on_slide=[
            "Idea: same gate for a support agent's prompt: checks mark it ready; a person promotes it",
            "1. One session, or you measure drift",
            "2. A margin above run-to-run noise",
            "3. Zero confirmed regressions",
            "4. A signed-in person approves that diff",
        ],
        notes=[
            "Purpose: Show the promotion gate as short generic code a learner can copy, explained "
            "line by line.",
            "What to say: Eight lines, no framework. Line one: the gate takes two recorded "
            "experiments, the confirmed regressions between them, an approval queue, and a "
            "minimum gain. Marker one: both experiments must come from one session, the same "
            "model, data and settings; otherwise you measure drift, so the code refuses. Line "
            "three: the gain in holdout passes, each question passing 2 of its 3 runs. Line "
            "four: the guard returns every new rule that copies the test. Markers two and three, "
            "line five. Marker two: "
            "the gain must beat your run-to-run noise; one question in 15 is within noise. Near "
            "the ceiling a fixed margin blocks everything: at 14 of 15 a gain of 2 is "
            "impossible, so gate on zero regressions plus a re-measured gain, or grow the "
            "holdout. Marker three: zero confirmed regressions and no flagged rule. "
            "Line six: anything less is blocked, with the gain, the regressions and the "
            "flagged rules. Marker four: the gate does not wait for a person; it writes ready "
            "and requests approval of the exact diff's hash, and a signed-in person's approval "
            "arrives later as its own recorded event.",
            "The point to land: Every condition is code that writes a reason; the person is the "
            "last condition, never the only one.",
            "Example: The same eight lines can gate a prompt change for a support agent, with "
            "tickets as the gold set and a team lead as the approver. This example is "
            "illustrative.",
            'Ask the room: "Which line would your release process skip?" Expect: line two; '
            "most compare against last week's numbers.",
            "Misconceptions: That an average over all questions can replace marker three. A net "
            "gain can hide a broken answer; only a question-by-question comparison names it.",
            "Transition: Now DataPilot's gate, the real code behind the demo, and where it falls "
            "short of this.",
        ],
    ),
    # 7 DataPilot's version: the gate's decide ----------------------------------------------------
    dict(
        kind="mechanism",
        title="DataPilot's gate: a precondition and four conditions",
        minutes=2.5,
        says="The same-session precondition, then holdout passes, zero regressions, the guard, "
        "and approval",
        src="platform/src/datapilot/loop4_hill_climbing/gate.py lines 115-135; analyzer.py lines "
        "206-208; eligibility.py confirmed_clearance; contracts api.py KnowledgeApprovalIn; "
        "pack.yaml evaluation; evidence E40, E41, E49; review round 1 ruling 3",
        code={
            "language": "python",
            "panel": "DataPilot",
            "origin": "platform/src/datapilot/loop4_hill_climbing/gate.py lines 115-135, the "
            "gate's decide (lines 117-118 and 121-133 left out; the common indent removed)",
            "lines": [
                "if active.session_id != candidate.session_id:",
                '    raise ValueError("both experiments must come from the same live session")',
                "...",
                "better = c > a",
                "clean = regressions.total == 0",
                "...",
                "ready = better and clean and not overfit_flags",
                "promoted = ready and bool(approved_by)",
            ],
            "marks": [
                (0, "active.session_id != candidate.session_id", 1),
                (3, "better = c > a", 2),
                (4, "clean = regressions.total == 0", 3),
                (6, "not overfit_flags", 4),
                (7, "bool(approved_by)", 4),
            ],
        },
        on_slide=[
            "Idea: plain code; every condition writes its reason",
            "1. One live session, a precondition",
            "2. More holdout passes",
            "3. Zero confirmed regressions",
            "4. No overfit flags; an approver's name",
        ],
        notes=[
            "Purpose: Show DataPilot's real gate as the worked example of the pattern, explained "
            "line by line, with its known gaps.",
            "What to say: This is the gate's decide function, the code the demo runs. Marker "
            "one, the first two lines: experiments from different live sessions raise an error; "
            "that is why the baseline ran today, at the poll. That check is a precondition, not "
            "a condition. Next, the gate counts holdout passes; a question passes on 2 of its 3 "
            "runs. Marker two: better means strictly more holdout passes, so one question is "
            "enough here, which is within noise; your gate should require a margin. Marker "
            "three: zero confirmed regressions on both splits. An apparent holdout regression "
            "gets 3 more runs and must fail 2; an apparent development regression is re-run "
            "twice under each version. One honest cost: only apparent regressions are re-run, "
            "never the new passes, so confirmation leans toward the candidate; in yours, re-run "
            "both. Marker four: ready needs no rule flagged by the overfit "
            "guard, which runs again here; promoted needs ready plus an approver's name. So four "
            "conditions decide: holdout passes, zero regressions, the guard, and approval. A "
            "known gap: the approver is whatever name the caller sends, the console sends "
            "console, and the gate checks only that it is not empty. In production, bind "
            "approval to a signed-in person and the hash of the diff they read. After approval, "
            "a separate step clears metric families.",
            "The point to land: The gate is a few lines of deterministic code; it is only as "
            "trustworthy as its margin and the identity behind its approval.",
            "Example: One revenue question once passed only 1 of 3 runs under version 4, then "
            "passed 3 of 3 more: the gate recorded it as not a regression.",
            'Ask the room: "Why confirm a regression instead of trusting one failed run?" '
            "Expect: answers vary from run to run.",
            "Misconceptions: That a higher holdout score is enough. It is one condition of four, "
            "and in our runs no candidate yet gained on the holdout while breaking an answer, so "
            "the regression condition exists for that case.",
            "Transition: The chain has been running since the opener. Let's see what it did.",
        ],
    ),
    # 8 demo --------------------------------------------------------------------------------------
    dict(
        kind="demo",
        title="Live: from the baseline to a right answer",
        minutes=12,
        says="The analyzer team's diff, the candidate experiment and the gate, approval, then the "
        "revenue question at its earned level, live",
        src="platform/demos/registry.yaml (section hill-climbing-loop); docs/instructor-guide.md, "
        "Section 4 and the class-day safeguard; evidence E42, E45, E46, E53, E55, E56; round 3 "
        "ruling 1; review round 1 rulings 2, 17",
        on_slide=[
            "Badge: DEMO - 4",
            "What to watch for:",
            "- Analyzer team: two candidates, one kept",
            "- Candidate: failed questions now pass",
            "- Revenue answer: right, at its earned level",
            "Guaranteed moment: the gate decides against this session's baseline: ready for a "
            "person, or blocked with reasons.",
            "Link: Demo page on GitHub | " + DEMO_PAGE + "#the-candidate-experiment",
        ],
        notes=[
            "Purpose: Read what the chain started on the opener produced, approve it, and send the "
            "fiscal year 2025 revenue question at the level its family earned.",
            "What to say: Let's see what the loop learned while we talked. This is the analyzer "
            "team's diff: two candidates, one kept on the development questions alone; the "
            "holdout never took part. Every rule here was proposed by the rule writer and "
            "survived the critic, the schema check, and the overfit guard. Now the candidate's "
            "ledger, against this session's baseline. Look for two things: flips, questions that "
            "failed under the baseline and pass now, and the regression count. If the count is "
            "zero and the holdout passes are higher, the gate waits for one thing: a person. I "
            "read the diff, and I approve. Notice what the record says: console, not my name. "
            "That is the gap from the code slide; in your system, bind approval to a signed-in "
            "person. Now the runner makes it the active "
            "version and re-runs any holdout question that fell short, to decide which metric "
            "families earned the unattended level. Approval says the rules look right; the "
            "re-runs say whether the evidence earns autonomy. Then the revenue question arrives "
            "as a webhook and posts at the level its family earned. Nothing here is scripted: "
            "every count on screen comes from this run.",
            "Demo: The baseline experiment.",
            "Command: read on the opener, at 3:04, before any reset; it started at the poll with "
            "Improve > Run experiment on the active version, or make demo "
            "NAME=improve-baseline-experiment. Press it only if it never started.",
            "Point at: the benchmark progress strip on the run board, opened into the holdout "
            "ledger; the failed trap questions; one row's start time and its trace link or Not "
            "traced.",
            "Expected output: version 1 at 2 of 15 holdout questions, as in every baseline from 22 "
            "to 25 October, every holdout trap question failed, and 4 or 5 of 25 development "
            "questions.",
            "While it runs: it finished before the section, 236 to 386 seconds after the trigger. "
            "Say: this is the instrument; every later count is compared with this run.",
            "If it fails: if it never started, at 3:05 run make reset NAME=hill-climbing-loop "
            "(about 7 seconds), press the trigger, then at once Improve > Run analyzer and "
            "Improve > Run experiment on the candidate; the runner takes them in order, so the "
            "gate reads about 4 to 6 minutes later than planned, still inside this demo slide. "
            + EXIT_3_34
            + " If the reset prints not reset, the naive request is still running: "
            + STOP_RESET_START,
            "Backup screenshot: " + EXPECTED + "improve-baseline-experiment-ledger.png, what the "
            "finished ledger looks like, to point at while you reset and run again.",
            "Demo: The naive analyzer, blocked.",
            "Command: read on the opener, at 3:04, before the reset clears it; queued at the "
            "break with make demo NAME=improve-naive-analyzer-blocked PLANTED=1, or Improve > Run "
            "the naive analyzer (planted).",
            "Point at: one rule quoting a benchmark question word for word; the line saying the "
            "guard flags every rule, not applied; the gate's verdict, blocked, naming the rules "
            "the overfit guard rejects.",
            "Expected output: about 21 rules, every one flagged, and the verdict blocked; in 6 "
            "measured runs, holdout 2 of 15 five times and 0 of 15 once.",
            "While it runs: it finished in the break, 211 to 580 seconds from the trigger to the "
            "verdict. Say: these are patches, one per failed question, the Goodhart case the "
            "pattern slides return to.",
            "If it fails: if no verdict shows at 3:04, it may still be behind the baseline: read "
            "the baseline, keep talking, and look again at 3:05. If the reset prints not reset, "
            "the naive request is still running: never reset mid-request; wait until the Improve "
            "page shows it finished, then reset. If it has not finished by 3:06, "
            + STOP_RESET_START
            + " Then start the chain, and read the naive verdict at the Thursday review.",
            "Backup screenshot: " + EXPECTED + "improve-naive-analyzer-blocked-gate.png, the "
            "blocked verdict naming 21 rules, to point at while you reset and run again.",
            "Demo: The analyzer team and approval.",
            "Command: on the opener, about 3:05, after both results are read: make reset "
            "NAME=hill-climbing-loop, which keeps the baseline and clears the naive candidate; "
            "then Improve > Run analyzer, or make demo NAME=improve-analyzer-team-approve, and "
            "at once Improve > Run experiment on the candidate.",
            "Point at: one diagnosis with no rule in it; one proposed rule with its SQL guidance; "
            "the critic's decision and reason; the guard's result; the line naming candidates A "
            "and B and the one kept; the knowledge diff waiting for approval.",
            "Expected output: a candidate version with general rules in the diff, not yet "
            "approved. On 24 October: candidate A passed 13 of 25 development questions with 8 "
            "rules, B 14 of 25 with 6 rules.",
            "While it runs: it runs during the pattern slides, 326 to 377 seconds in five "
            "measured runs, ending by about 3:11; the candidate experiment follows, and the gate "
            "reads about 3:13 to 3:19. If the team is still writing at 3:11, say: two analyzer "
            "runs and 50 development runs are in flight. If the gate has not read at 3:17, say: "
            "70 benchmark runs are still in flight, and a confirming re-run lengthens them.",
            "If it fails: a stalled request still reads as running, so a reset alone refuses: "
            + STOP_RESET_START
            + " The reset keeps the baseline and clears the candidate, so then press Improve > "
            "Run analyzer and Improve > Run experiment on the candidate. "
            + LAST_CHAIN
            + " "
            + EXIT_3_34,
            "Backup screenshot: " + EXPECTED + "improve-analyzer-team-diff.png, the knowledge "
            "diff under the line naming both candidates, to point at while you reset and run "
            "again.",
            "Demo: The candidate experiment.",
            "Command: nothing to press: it was queued with the analyzer. Only if it never started, "
            "Improve > Run experiment on the candidate, or make demo "
            "NAME=improve-candidate-experiment; a second press queues a second experiment. When "
            "the gate reads ready for human approval, read the diff aloud and click Approve on "
            "the knowledge diff, then say what the record shows, as in What to say.",
            "Point at: the flips against this session's baseline; regressions at zero on both "
            "splits; the gate's reason lines, one per condition, with regressions written once "
            "per split: holdout passes, development regressions, holdout regressions, human "
            "approval, overfit guard; after approval, the line saying the version is the active "
            "version.",
            "Expected output: holdout flips, no regressions, the gate ready for human approval. "
            "In the registry's measured runs, 0 to 12 of 13 holdout trap questions flipped, a "
            "majority in 6 of 10, in 171.3 to 459 seconds; that range includes single-candidate "
            "runs, while kept candidates of two, with that session's analyzer fixes, passed 12 "
            "to 14 of 15. The gate may block, which is a correct outcome.",
            'While it runs: if the ledger reads "Apparent regression: confirming", say: the gate '
            "is re-running before it believes a failure. As soon as the version is active, set "
            "the unattended level: Improve > Set the unattended level, or make autonomy "
            'LEVEL=unattended BY="your name".',
            "If it fails: if the gate blocks the candidate, say: the gate refused a version that "
            "did not earn it, which is the point; leave the verdict on screen and go to the "
            "evidence slide. If it stalls, the request reads as running: "
            + STOP_RESET_START
            + " The reset clears the candidate, so the trigger after it is Improve > Run "
            "analyzer, then Run experiment on the candidate. " + LAST_CHAIN + " " + EXIT_3_34,
            "Backup screenshot: " + EXPECTED + "improve-candidate-experiment-ledger.png, 14 of 15 "
            "against 2 with 12 fixed and 0 regressions, to point at while you reset and run again.",
            "Demo: Cleared for the unattended level.",
            "Command: when the note above the Events buttons goes away, Events > Send webhook "
            "question, or make demo NAME=improve-cleared-unattended. Check first that the status "
            "line shows the kill switch released and the unattended level.",
            "Point at: the run's strip with Gold check passed and the value; the level it posted "
            "at; the status line naming the families cleared.",
            "Expected output: 64,015,091.21 dollars, posted at the unattended level when revenue "
            "cleared, at the assisted level when not; correct at the unattended level in 8 "
            "recorded runs, 50 to 162 seconds after the first send when held for the clearance "
            "re-runs; it lands about 3:25 to 3:29. The whole chain from the opener is about 9 to "
            "17 minutes, added up from the measured steps.",
            "While it runs: say how a family clears: every holdout question passes 2 of 3 runs, "
            "and one that falls short must pass 2 of 3 more. The assisted level is a correct "
            "outcome: the gate held back autonomy the evidence did not earn.",
            'If it fails: if the strip reads "Gold check failed", use the class-day safeguard, '
            "live. One: say the class version misses a trap, and its record stays as it is. Two: "
            'make safeguard-activate BY="your name". Three: show the status line naming the '
            "version verified in rehearsal. Four: Events > Send webhook question again. Five: if "
            "it stalls, send again; do not reset, since a reset sets the report-only level. If "
            "make safeguard-status named no version before class, leave the wrong answer on "
            "screen as the gate's evidence. Rehearsed live twice; correct both times, in 19 and "
            "21 seconds. " + EXIT_3_34,
            "Backup screenshot: " + EXPECTED + "improve-cleared-unattended-board.png, the posted "
            "answer with Gold check passed, to point at while you reset and run again.",
            "The point to land: Rules were learned from failures, measured on questions no one "
            "tuned on, and trusted only as far as the evidence went.",
            "Example: On 24 October, run 59174f10 posted 64,015,091.21 dollars at the unattended "
            "level under version 13, which passed 14 of 15 holdout questions against 2 with 0 "
            "regressions and was " + APPROVED_13 + ". In class you approve today's candidate.",
            'Ask the room: "Would you have approved this diff without the ledger?" Expect: no; '
            "the rules read well either way.",
            "Misconceptions: That the demo is scripted. Every rule, flip, and level comes from "
            "this run; the counts differ from rehearsal.",
            "Transition: One chain is a story; next, how much the improver itself varies from "
            "run to run.",
        ],
    ),
    # 9 evidence (round 1 ruling 10, round 2 ruling 2): the improver's runs, from E45 ----------
    dict(
        kind="evidence",
        title="Measure the improver, not only the agent",
        minutes=2.5,
        says="One candidate per improver run scored 2 to 11 of 15; the better of two, 12 to 14",
        src="evidence E45 (docs/calibration-report.md, Analyzer comparison, What this session "
        "supersedes), checked value by value; E42, E43, E51; .dev/deck2-reconcile.md items 4 and "
        "5; review round 2 ruling 2",
        chart={
            "type": "column",
            "title": "Holdout passes per improver run",
            "categories": ["1", "2", "3", "4", "5", "6", "7"],
            "series": [
                ("One candidate", [11, 3, 6, 2, 2, 9, 5]),
                ("Better of two, chosen on development", [14, 14, 13, 14, 13, 12, 13]),
            ],
            "x_label": "Improver run (not paired)",
            "y_label": "Passed, of 15",
            "maximum": 16,
        },
        on_slide=[
            "Sample: 7 improver runs a side; 15 holdout questions, 3 runs each, pass on 2 of 3",
            "- Lesson: one improver run is a sample; write two, keep one on development "
            "questions, gate only that one",
            "- Caution: an analyzer fix landed with the pairs, so not all the gain is the "
            "second candidate",
            "- Regressions: 0 at every promotion",
        ],
        notes=[
            "Purpose: Show that the improver varies from run to run, with its sample size, and "
            "why DataPilot writes two candidates and gates only the one it keeps.",
            "What to say: Each bar is one run of the improver, scored on the same 15 holdout "
            "questions, each run three times and passed on two of three. The grey bars are runs "
            "that wrote one candidate, from the same kind of input: 11, 3 and 6 of 15 at medium "
            "reasoning effort, 2 for an early version before a personal-data fix, and 2, 9 and "
            "5 at high effort; version 4's 11 read 12 on a re-measurement. One more single "
            "candidate, version 5 at 10 of 15, is not drawn; it does not change the range. The "
            "lime bars are runs that wrote two candidates and kept the "
            "better one on development questions alone; only that one went to the gate, and "
            "each was promoted: 14, 14, 13, 14, 13, 12 and 13, versions 8 to 19. The runs are "
            "not paired: they come from several sessions, and the three high-effort runs, 2, 9 "
            "and 5, shared one session and one version 1 baseline. Every run was scored against "
            "a version 1 baseline that read 2 of 15, so compare each bar with 2, not with its "
            "neighbours. The "
            "caution on the slide matters: an analyzer fix landed in the same sessions as the "
            "pairs, so which change helped is unmeasured, and writing two is judgement as much "
            "as measurement. Every promoted candidate had 0 confirmed regressions; of 15 "
            "candidate experiments, 14 had none.",
            "The point to land: One improver run is a sample: write two, keep one on development "
            "questions, and gate only that one.",
            "Example: For version 15, candidate A passed 7 of 25 development questions and "
            "candidate B 24, from the same input. The record counts 11 promotions: the 7 pairs, "
            "version 4 at 11 and version 5 at 10 from single candidates, and two demo "
            "run-throughs at 3 and 6 that the gate of the time promoted because they beat 2. "
            "Revenue cleared the unattended level in 7 of those 11, never under the earlier "
            "one-experiment rule and in 7 of 8 under today's; orders in none.",
            'Ask the room: "Why choose between the two candidates on development questions, not '
            'the holdout?" Expect: choosing on the holdout would make it a development set.',
            "Misconceptions: That 14 of 15 is an accuracy rate. It is one count on 15 questions; "
            "a one-question difference is noise, and version 11 measured 13 and, later that day, "
            "12.",
            "Transition: So what does this loop change in your own text-to-SQL design?",
        ],
    ),
    # 10 design callout ---------------------------------------------------------------------------
    dict(
        kind="design_callout",
        title="Your design: where learned rules live",
        minutes=2,
        says="Where learned rules live, and an execution-match benchmark that decides each change",
        src="section-4-hill-climbing-loop/README.md; evidence E11, E12; sources 12, 40, 45",
        on_slide=[
            "Decision: where do learned rules live, and what decides?",
            "| Option | Decided by | Watch for |",
            "|---|---|---|",
            "| Prompt patch per failure | The questions just fixed | Rises by construction |",
            "| Versioned knowledge file | Execution match on gold[^12] | Rules copying the test |",
            "| Semantic layer or views | Every question, re-run[^45] | Slow manual changes |",
            "DataPilot: a knowledge file learned from failures, promoted on the holdout.",
        ],
        notes=[
            "Purpose: Turn the hill-climbing loop into design decisions for the learner's own "
            "text-to-SQL system.",
            "What to say: Two decisions. First, where learned rules live. A prompt patch is "
            "judged by the questions it was written for, so it always looks like progress. A "
            "versioned knowledge file, like ours, holds each rule with its SQL guidance and can "
            "be diffed, approved, and rolled back. A semantic layer or views put rules where "
            "every tool reads them; changes are slower, so re-test every benchmark after each "
            "change, as the Databricks guide says, Source 45. Second, what decides: execution "
            "match. Run the agent's query and the gold query and compare results, never query "
            "text, on more than one database, because one database lets some wrong queries "
            "pass, Source 12; the paper's suites hold about 42 databases per query, and two is "
            "our minimum, not theirs. Products now count regressions too: Snowflake's Cortex Analyst reports verified "
            "queries that were correct and now fail, Source 40. What we add is an improver that "
            "never reads the deciding questions, and a regression that blocks. Our benchmark has "
            "40 questions, 33 with traps; the 15 holdout questions are never shown to the "
            "analyzer team.",
            "The point to land: Keep rules where you can diff and roll them back, and let results "
            "on held-out gold queries decide.",
            "Example: The gold answer to the fiscal year 2025 question, 64,015,091.21 dollars, is "
            "checked on both the warehouse and a second database seeded differently.",
            'Ask the room: "Where do your metric definitions live today?" Expect: dbt, a wiki, or '
            "old dashboards.",
            "Misconceptions: That comparing SQL text is stricter. It rejects correct queries "
            "written another way.",
            "Transition: Here is what to do with this next week.",
        ],
    ),
    # 11 apply it ---------------------------------------------------------------------------------
    dict(
        kind="checklist",
        title="Apply it: a gated improvement loop for your agent",
        minutes=2,
        says="Six steps to build a hill-climbing loop on your own agent",
        src="section-4-hill-climbing-loop/demo/walkthrough.md, If you copy this into your "
        "repository; section-4-hill-climbing-loop/assignment/README.md; round 3 ruling 5; "
        "sources 106, 116, 118; review round 1 rulings 3, 4",
        on_slide=[
            "- Write gold questions from real failures, answers checked by hand",
            "- Split them before you read any failure",
            "- Score by result, with repeated runs per question",
            "- Count regressions on their own; re-run every flip, both ways",
            "- Promote on holdout passes, zero regressions, approval and the guard",
            "- Re-run the gold set on a schedule and on every model change",
        ],
        notes=[
            "Purpose: Give six concrete steps a learner can take to build a gated improvement loop "
            "on their own system.",
            "What to say: Six steps, in order. One: write gold questions from real failures, "
            "each answer checked by a person; Anthropic suggests 20 to 50 to start, Source 106. "
            "Two: split them before you read a single failure, and make the holdout unreadable, "
            "in code, to whatever writes rules. Three: score by result, never by query text, and "
            "fix the measurement before any comparison: runs per question and the pass "
            "threshold, the same for both versions, in one session. Four: count regressions on "
            "their own, and re-run every flip both ways: re-running only the failures leans "
            "toward the candidate, because a new pass counts at once. Five: promote only on all "
            "four: holdout "
            "passes by a margin above your noise, zero regressions, a named person's approval, "
            "and the overfit guard, which runs again at the gate; record every reason. Six: "
            "re-run the gold set on a schedule and whenever the model or the data changes, so "
            "drift shows up as a drop you did not cause, and lower autonomy when it does. Then "
            "test the loop itself: a rule that quotes a question must be rejected, and a rule "
            "that breaks a passing question must be blocked. Assignment 4: Hill-climbing loop "
            "builds parts of this.",
            "The point to land: Split first, measure second, learn third; never in another order.",
            "Example: The over-broad rule from the opener is the test for step five: it must be "
            "blocked.",
            'Ask the room: "Which step is missing in your team today?" Expect: the split, most '
            "often, then the scheduled re-run.",
            "Misconceptions: That human-written rules can skip the gate. The SEED audit of BIRD's "
            "evidence found wrong evidence in 105 of 1,534 development pairs, Source 21.",
            "Transition: Four ways this goes wrong, each one we hit or guard against.",
        ],
    ),
    # 12 pitfalls ---------------------------------------------------------------------------------
    dict(
        kind="pitfalls",
        title="Pitfalls that fool an improvement loop",
        minutes=2,
        says="One improver run, replaced test questions, comparing across sessions, and no drift "
        "check",
        src="evidence E45, E50, E40; sources 110, 116, 118",
        on_slide=[
            "| Pitfall | What happens | Do instead |",
            "|---|---|---|",
            "| Trusting one candidate | Candidates swing widely on the same input | Write "
            "two; keep one on development questions |",
            "| Replacing flaky holdout questions | The noise moves to other questions | Re-run "
            "to confirm; keep the set |",
            "| Comparing across sessions | A model or data change reads as progress | Measure "
            "both in one session |",
            "| No check after the model changes | Untouched answers get worse | Gold re-runs; "
            "lower autonomy |",
        ],
        notes=[
            "Purpose: Name four mistakes that fool an improvement loop, each with what it does and "
            "the fix.",
            "What to say: Four pitfalls. First, trusting one run of the improver: across the "
            "range you just saw, one candidate is a sample; write two and keep one on "
            "development questions alone. Second, fixing noise by changing the test. Under a "
            "promoted version, 3 of 15 holdout questions were unstable; we replaced them, and on "
            "the next pass others were unstable instead. The instability belonged to the "
            "version's answers, so we restored the reviewed holdout and confirm regressions "
            "with re-runs. Third, comparing across sessions: if the model, the data or the "
            "settings changed between baseline and candidate, the difference is not your "
            "change; DataPilot's gate refuses such a comparison, and the evidence chart you just "
            "saw is a trend for exactly this reason. Fourth, no check after the model changes: "
            "a model can drift behind the same name, Source 118, so re-run the gold set on a "
            "schedule and lower autonomy on a drop, as Google's guide advises monitoring and "
            "rolling back, Source 116. And one more to watch: reading the holdout too often "
            "wears it out, Source 110; we changed the analyzer and the gate after reading its "
            "results, so it is less unseen than it was.",
            "The point to land: Noise, a moved baseline and a tired holdout fool a loop as surely "
            "as copying does.",
            "Example: A rule once named a placeholder instead of a filter, and the revenue answer "
            "came out wrong while labelled verified; now every rule's SQL is parsed against the "
            "catalog before it can join a candidate.",
            'Ask the room: "When your model provider updates a model, what tells you?" Expect: '
            "an email, or a user.",
            "Misconceptions: That more repeats fix a small holdout. Repeats reduce noise per "
            "question; only more questions narrow the uncertainty.",
            "Transition: Let me check what stuck, with the scoreboard.",
        ],
    ),
    # 13 recap with the scoreboard ----------------------------------------------------------------
    dict(
        kind="recap",
        title="Recap: the hill-climbing loop",
        scoreboard=4,
        minutes=2,
        says="Three points to keep, the complete scoreboard, and one question applying the gate",
        src="section-4-hill-climbing-loop/README.md; evidence E40, E46, E53; review round 1 "
        "ruling 2",
        on_slide=[
            "- Judge every change by the whole gold set",
            "- Unseen holdout decides; zero regressions",
            "- A person promotes; autonomy per capability",
            "Question: A new support prompt beats last month's run of the old one by 3 of 30 "
            "on its tuning tickets. Why is that not proof, and what would you run?",
        ],
        notes=[
            "Purpose: Consolidate the hill-climbing loop, complete the scoreboard, and apply the "
            "gate to a new kind of agent.",
            "What to say: The scoreboard is complete: correct, 64,015,091.21 dollars, posted at "
            "the level its family has earned. If today's chain was blocked or is still running, "
            "the scoreboard shows the published run; the gate's verdict you saw is today's "
            "evidence. Three points to keep: judge every change by a gold set; decide on "
            "questions nobody studied, with zero regressions; a person promotes, and autonomy is "
            "earned per capability. Now the question; thirty seconds. Two reasons it proves "
            "nothing. First, the tuning tickets are the development set: the measure turned into "
            "a target. Second, last month's run is another session, so drift and noise are mixed "
            "into the 3, and 3 of 30 may be noise anyway. Instead, run both prompts now, in one "
            "session, on held-out tickets nobody tuned on, three runs each; require a gain "
            "larger than your run-to-run noise and zero confirmed regressions, re-running flips "
            "both ways; then a signed-in team lead approves the exact diff.",
            "The point to land: Promotion needs all four conditions, measured in one session; a "
            "higher score on the questions you tuned on satisfies none of them.",
            "Example: Version 13 passed 14 of 15 holdout questions against 2, with 0 "
            "regressions and every rule through the guard, and was " + APPROVED_13 + ". In "
            "class you approve today's candidate, and the console records the approver as "
            "console.",
            "Ask the room: the question on the slide. Expect: the tuning tickets; push for the "
            "second reason, last month's session, and for a margin over noise.",
            "Misconceptions: That human approval alone would catch it. The prompt reads well; "
            "the regression count and the held-out score catch it in code.",
            "Transition: That completes the four loops. Next, the question, answered.",
        ],
    ),
]
