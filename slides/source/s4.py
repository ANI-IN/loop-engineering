"""Section 4: Hill-climbing loop, 3:03-3:38, 35 minutes, under design system 3.

The third rebuild (27 October 2026), in the reference deck's rhythm: the agenda with the star on
the hill-climbing loop, the failure story (Friday's plausible rule that broke nine answers and fixed
none, blocked by the gate), the question slide ("Why not add a rule for each failure?"), the four
techniques (gold questions and the development and holdout split; agents propose, code decides; the
gate's four conditions, and overfitting; autonomy earned per metric family), the text-to-SQL design
callout, the cheat sheet, the DEMO slide, the Measured slide with the scoreboard, and Ask about
anything. Course numbers come from the deck evidence (.dev/deck3-evidence.md, parts 1 and 3;
docs/evidence/section-4-hill-climbing-loop.md); sources are cited by their stable numbers in
sources.py (113, 106, 110, 103, and 12 reused from the problem block). Review round 1's rulings
applied (1, 2, 3, 14, 15, 16, 20, 21, 23; the agenda's labels as the coordinator gave them).

The hill-climbing chain starts on the failure story (about 3:05; its Do lines hold the commands) and
runs while the question and technique slides are taught; the DEMO slide (about 3:21:30 to 3:33:30)
reads its results. Start no new chain after 3:17; the exit for a gate that has not landed is 3:33,
the end of the demo slot.
"""

RULES = "design system 3"

DEMO_PAGE = "https://github.com/ANI-IN/loop-engineering/tree/main/section-4-hill-climbing-loop/demo"
EXPECTED = "section-4-hill-climbing-loop/demo/expected/"

# Ending a running hill-climbing request: stop, reset, start, never restart. Written once per slide.
STOP_RESET_START = (
    "docker compose stop hill-climbing-runner (about 11 seconds), make reset "
    "NAME=hill-climbing-loop (about 7 seconds), docker compose start hill-climbing-runner (about 3 "
    "seconds), about 20 seconds in all; never restart the runner instead, since a restarted runner "
    "keeps serving and the reset refuses again"
)

# Who approved version 13 in the published run (round 3 ruling 6; round 1 ruling 3 of the third
# rebuild: recorded as "console", before the name rule; never "approved by a named person").
APPROVED_13 = (
    "approved at the gate's approval step in rehearsal on 24 October, by the build session "
    'standing in for the instructor, and recorded as "console", before the name rule'
)

SLIDES = [
    # 66 agenda ---------------------------------------------------------------------------------
    dict(
        kind="agenda",
        title="Today's Agenda",
        minutes=0.5,
        says="The four loops, the star on the hill-climbing loop",
        src="the specification of 27 October 2026, the recurring agenda; the poll",
        on_slide=[
            "1. Agent loop: what it sees",
            "2. Verification loop: is it right?",
            "3. Event loop: runs unattended",
            "4. Hill-climbing loop: improves safely",
            "Now: 4",
        ],
        notes=[
            "Purpose: Show where the class is: the last of the four loops, the one that makes the "
            "answer right.",
            "What to say: The star is on the fourth loop: does the agent improve safely? The poll "
            "before the break: [number] of you have a hill-climbing loop, and [number] have none "
            "of the four. Section 3: Event loop ended with the question running safely "
            "unattended, and still wrong. This section makes it right without breaking anything "
            "else.",
            "The point to land: The last loop improves the agent, and it must prove each change "
            "before it ships.",
            "Example: The fiscal year 2025 question is still wrong; this section fixes it.",
            "Ask the room: none here; the question comes at the end of the section.",
            "Misconceptions: That improving means a better model. Here only the knowledge changes.",
            "Transition: Here is how a sensible fix goes wrong.",
        ],
    ),
    # 67 failure story --------------------------------------------------------------------------
    dict(
        kind="failure",
        title="Failure story: The rule that broke nine answers",
        minutes=2.5,
        says="Five steps from a quick fix that reads like policy to nine broken answers; the "
        "chain starts",
        src=".dev/deck3-evidence.md, Friday (experiment 84417bfe against 82ad72d5, 24 October "
        "2026); docs/calibration-report.md, The over-broad rule; knowledge/v2-overbroad.yaml; "
        "docs/instructor-guide.md, Section 4, steps 1 and 2; round 1 presenter findings 1 and 2",
        allow_commands=True,
        on_slide=[
            "Lead: An illustrative question: should discounted orders count toward revenue?",
            "1. Monday's revenue is too high; an analyst writes a fix.",
            "2. The new rule: exclude discounted orders from revenue.",
            "3. It reads like policy, so nobody tests it.",
            "4. Revenue now drops discounted orders: real sales.",
            "5. Nine right answers are now wrong; nothing errors.",
        ],
        notes=[
            "Purpose: Walk Friday's failure from a sensible fix to nine broken answers, then start "
            "the improvement loop that runs through the section.",
            "What to say: This story is illustrative: Friday's failure, told as an analyst's "
            "change. Monday's revenue answer is too high, and someone wants it fixed today. The "
            "rule sounds right, and reads like policy, so nobody runs every question. But "
            "discounted orders are real sales. Step five, in red: nine answers that were right "
            "are now wrong, and nothing errors. In our runs "
            "this was a planted change, and a gate blocked it: it fixed no question and broke "
            "nine. Two results from the poll and the break: the starting rules pass 2 of 15 holdout "
            "questions, and the naive analyzer's rules were blocked; why, you will see in "
            "technique 2. Now I start the improvement loop; it runs while we talk.",
            "Do: At 3:04, on the Improve page: read the baseline's holdout ledger (2 of 15), then "
            "the naive analyzer's blocked verdict. No verdict yet? Read the baseline and look "
            "again at 3:05. Baseline never started? At 3:05 reset, press Improve > Run experiment "
            "on the active version, then the two buttons below; the gate reads 4 to 6 minutes "
            "late.",
            "Do: About 3:05: make reset NAME=hill-climbing-loop (keeps the baseline); then "
            "Improve > Run analyzer, and at once Improve > Run experiment on the candidate.",
            "Do: If the reset prints not reset, wait for the naive request; still running at "
            "3:06: " + STOP_RESET_START + "; then the two buttons, and read the naive verdict at "
            "the Thursday review.",
            "The point to land: A fix judged only by the question that prompted it can break "
            "working answers without a single error.",
            "Example: Experiment 84417bfe of 24 October, the rule added to version 11 of the "
            "knowledge: holdout fell from 12 to 7 of 15, with 9 confirmed regressions, all "
            "revenue questions.",
            'Ask the room: "Who on your team can change a metric definition without a test?" '
            "Expect: almost anyone.",
            "Misconceptions: That a rule that reads well is safe. This one read like policy and "
            "passed review by eye; only measuring every question showed what it broke, and "
            "none of the nine broken answers raised an error.",
            "Transition: So why not simply add a rule for each failure?",
        ],
    ),
    # 68 question -------------------------------------------------------------------------------
    dict(
        kind="question",
        title="Hill-climbing loop: Why not add a rule for each failure?",
        minutes=2.5,
        says="The naive fix, a patch per failure, and why it fails",
        src="the specification of 27 October 2026, section 4, item 3; sources.py "
        "entries 113 and 110; .dev/deck3-evidence.md, Friday; docs/calibration-report.md, the "
        "naive analyzer of 23 October (version 7, 911423fb); round 1 rulings 1 and 21",
        on_slide=[
            "Lead: Each failed question shows what went wrong, and a rule for it takes a minute "
            "to write.",
            "Key idea: A patch fixes one question and breaks others; decide on unseen questions.",
            "1. A patch is judged by the question it was written for, so it always looks like "
            "progress",
            "2. A rule that reads like policy can quietly break answers that used to pass",
            "3. A score you aim at stops measuring: copied rules can pass even the holdout",
        ],
        notes=[
            "Purpose: Answer the naive fix, a rule for each failure, with the section's key idea "
            "and three reasons.",
            "What to say: Here is the obvious fix for Friday's kind of problem. Every failed "
            "question tells you what went wrong, so write a rule for each one and ship it. The "
            "key idea says no: a patch fixes one question and breaks others, so decide on "
            "questions the rule writer never saw. Three reasons. One: a patch is judged by the "
            "question it was written for. It was written to make that question pass, so of "
            "course it passes; the check measures your effort, not the system. Two: a rule that "
            "reads like policy can break answers that used to pass, quietly. The discount rule "
            "broke nine and fixed none, and only a run over every question showed it. Three: a "
            "score you aim at stops measuring. This is Goodhart's law, in Marilyn Strathern's "
            "phrasing: when a measure becomes a target, it ceases to be a good measure. We cite "
            "it through Mattson and others, Source [^113]. Google's machine learning course warns "
            "that many rounds of tuning against one test set fit its peculiarities, Source "
            "[^110]. Copied rules can even pass held-back questions when those questions share "
            "the same business rules, so a score alone cannot tell copying from learning. So the "
            "questions you learn from cannot decide, and how each rule was written is checked "
            "too.",
            "The point to land: A fix must be judged on questions nobody tuned it on, and on "
            "every question, not just the one it fixed.",
            "Example: On 23 October an early analyzer pasted each failed development question and "
            "its gold query into a rule. Its version passed 15 of 15 holdout questions, because "
            "both splits share the same five business rules. The holdout could not tell copying "
            "from learning, so the gate now refuses copied wording outright.",
            'Ask the room: "When did a fix of yours break something else?" Expect: a prompt '
            "change, a dashboard filter, a dbt model.",
            "Misconceptions: That a careful person writing rules avoids this. The discount rule "
            "was careful; it was wrong for nine questions nobody looked at.",
            "Transition: So the first technique: gold questions, and a split that keeps the "
            "deciding questions unseen.",
        ],
    ),
    # 69 technique 1 ----------------------------------------------------------------------------
    dict(
        kind="technique",
        title="1) Gold questions and the development and holdout split",
        minutes=2.5,
        says="Checked gold questions, split before reading any failure; count passes over runs",
        src="sources.py entries 106 and 110; docs/evidence/section-4-hill-climbing-loop.md; "
        "pack benchmark (25 development, 15 holdout)",
        figure={
            "diagram": "pattern-dev-holdout",
            "alt": "Development and holdout splits: gold questions split into development, where "
            "you read the failures and change things, and holdout, never read, which decides "
            "what ships; beside it, one question run three times passes, fails, and passes, so "
            "count passes over repeated runs: 2 of 3, since one run is only a sample",
        },
        on_slide=[
            "- **What:** questions with answers a person checked; judge every change by all of "
            "them, never by one.",
            "- **How:** split before you read any failure: learn on development, decide on a "
            "holdout nobody studies.",
            "- **Example:** run each question 3 times and count a pass at 2 of 3; one run is only "
            "a sample.",
            "- **Elsewhere:** a model's test set, a coding agent's hidden tests; a test set read "
            "too often wears out.[^110]",
            "Key idea: Learn on the development questions; let questions nobody studied decide "
            "what ships.",
        ],
        notes=[
            "Purpose: Teach the first technique: checked gold questions, split into development "
            "and holdout before anyone reads a failure, with passes counted over repeated runs.",
            "What to say: Start with the instrument. A gold question is a question with an "
            "answer a person has checked, and every change is judged by all of them, never by the "
            "one that prompted it. Walk the diagram from the left. The gold questions split in "
            "two. Development questions: you read their failures and change things. Holdout "
            "questions: nobody who writes rules ever reads them, and they decide what ships. "
            "Split before you read a single failure, or the split means nothing. On the right, "
            "one question run three times: pass, fail, pass. A model can answer the same "
            "question differently from run to run, so count passes over repeated runs, 2 of 3, "
            "and treat one failure as a reason to re-run, not as proof. How many to start? "
            "Anthropic's guide to agent evaluations says 20 to 50 tasks drawn from real failures "
            "is a great start, Source [^106]. And a holdout wears out: Google warns that test "
            "sets read too often stop being unseen, Source [^110]; refresh yours. DataPilot keeps "
            "40 gold questions, 25 development and 15 holdout, each with a hand-written gold "
            "query, checked by its result on two databases.",
            "The point to land: The questions you learn from never decide, the questions that "
            "decide are never studied, and one run is only a sample.",
            "Example: Version 1, the starting knowledge, passed 2 of 15 holdout questions in "
            "every baseline from 22 to 25 October; that run is the line every candidate must "
            "beat.",
            'Ask the room: "Who on your team can read your test set today?" Expect: everyone, '
            "which is the problem.",
            "Misconceptions: That temperature zero makes runs repeatable. It does not, and we "
            "never set a temperature today; repeat the runs instead.",
            "Transition: With the split in place, who writes the rules? Agents, but they only "
            "propose.",
        ],
    ),
    # 70 technique 2 ----------------------------------------------------------------------------
    dict(
        kind="technique",
        title="2) Agents propose, code decides",
        minutes=2.5,
        says="Agents propose rules; a schema check, the overfit guard and the gate decide",
        src="section-4-hill-climbing-loop/README.md; platform/demos/registry.yaml "
        "(improve-analyzer-team-approve); .dev/deck-evidence.md E45; round 1: upskilling 10, "
        "engineer 12, instructional 6, presenter 15",
        figure={
            "diagram": "pattern-agents-propose",
            "alt": "Agents propose, code decides: from the failed development questions, agents read the"
            " failures and propose rules, and a critic agent keeps, narrows, or drops them; then "
            "code decides: the rules are checked against the schema, so each rule's query runs, "
            "an overfit guard refuses copied test wording, and the gold questions are scored for "
            "the gate; a rule that fails a check is blocked and dropped",
        },
        on_slide=[
            "- **What:** agents read failures and write rules; deterministic code decides which "
            "rules survive.",
            "- **How:** an analyzer team: one agent diagnoses, one proposes, a critic keeps, narrows "
            "or drops each rule.",
            "- **Code:** each rule's query must run on the real schema; a guard refuses rules "
            "copying test wording.",
            "- **Example:** write two candidates, keep the better one on development questions, "
            "gate only that one.",
            "- **Elsewhere:** a coding agent's patch merges only when the build and the tests "
            "pass.",
            "Key idea: Agents write proposals; deterministic checks decide which ones reach the "
            "gate.",
        ],
        notes=[
            "Purpose: Teach the second technique: agents propose rules, and deterministic code "
            "decides which ones reach the gate.",
            "What to say: Agents are good at reading failures and writing a plausible rule. They "
            "are not trustworthy judges of their own rules. So split the work. Walk the diagram. "
            "Top row: the failed development questions go to agents. In DataPilot this is the "
            "analyzer team: a failure analyst diagnoses, a rule writer proposes, and a critic "
            "keeps, narrows or drops each rule. Bottom row: code decides. First, rules checked "
            "against the schema: each rule carries query guidance, and that query must run on the real "
            "schema, or the rule is dropped. Then the overfit guard: code that refuses a rule "
            "sharing 6 consecutive words with a benchmark question, or 20 consecutive query "
            "tokens with a gold query. That is why the naive analyzer's rules were blocked at "
            "the start: each quoted a failed question word for word. The guard catches only "
            "verbatim copying; a paraphrase passes it, so the holdout, which no agent sees, is "
            "the defence that matters. One more lesson: one analyzer run is a sample. Write two "
            "candidates, keep one on development questions alone, and gate only that one.",
            "Do: At 3:11, on your own screen, not the shared one: glance at the Improve page; the "
            "analyzer team should be finishing. Still writing? Say: two analyzer runs and 50 "
            "development runs are in flight.",
            "The point to land: Let agents write; let deterministic checks, which cannot be "
            "persuaded, decide what reaches the gate.",
            "Example: A rule once named a placeholder instead of a filter, and the revenue answer "
            "came out wrong while labelled verified; now every rule's query must run first.",
            'Ask the room: "Where does an agent grade its own work in your system?" Expect: a '
            "self-review step, or none.",
            "Misconceptions: That the critic makes the code checks unnecessary. It shares the "
            "writer's knowledge, and with it the writer's blind spots.",
            "Transition: The checks feed one decision: the gate.",
        ],
    ),
    # 71 technique 3 ----------------------------------------------------------------------------
    dict(
        kind="technique",
        title="3) The gate's four conditions, and overfitting",
        minutes=2.5,
        says="A holdout gain above noise, zero confirmed regressions, rules that pass a guard, a "
        "named approver; any failure blocks",
        src="platform/src/datapilot/loop4_hill_climbing/gate.py (decide); contracts api.py "
        "approver_name; DECISIONS.md, 27 October 2026, decision 2; sources.py entry 113; "
        "docs/calibration-report.md (911423fb); round 1 rulings 1, 2 and 3",
        figure={
            "diagram": "pattern-promotion-gate",
            "alt": "A promotion gate of four conditions: a candidate version must have 1, a "
            "holdout gain above noise, 2, zero confirmed regressions, 3, new rules that pass the "
            "guard, and 4, a named approver; any one that fails blocks it with its reason; "
            "copied rules can lift even the holdout, so the guard checks how rules are written",
        },
        on_slide=[
            "- **What:** the promotion gate decides if a new version goes live, writing a reason "
            "per condition.",
            "- **How:** a holdout gain above noise, zero confirmed regressions, rules passing a "
            "guard, a named approver.",
            "- **Overfitting:** a chased score misleads[^113]; a holdout sharing every rule cannot "
            "tell copying from learning.",
            "- **Elsewhere:** a canary release's promotion check: error rates within bounds, then "
            "a person signs off.",
            "Key idea: Any failed condition blocks the candidate; a person approves last, never "
            "alone.",
        ],
        notes=[
            "Purpose: Teach the third technique: the promotion gate's four conditions, and why a "
            "score alone cannot show overfitting.",
            "What to say: Walk the diagram from the left. A candidate version meets four "
            "conditions. One: a holdout gain above your run-to-run noise. Two: zero confirmed "
            "regressions; a question that passed before and fails now is re-run, and counts only "
            "if it fails again. Only apparent regressions are re-run, never the new passes, so "
            "confirmation leans toward the candidate; in yours, re-run both. Three: every new "
            "rule passes a guard against copied test wording. Four: a named approver; record the "
            "signed-in approver and exactly what they approved. Any one failing blocks the "
            "candidate, with its reason, and both experiments come from one session, or the gate "
            "measures drift. DataPilot is the worked example, with a known gap: its gate asks "
            "only for more holdout passes, so one question in 15 is enough, and that is within "
            "noise. Its approver types a name, and the gate refuses an empty name or the word "
            "console. Now overfitting, Goodhart's law at work, Source [^113]. Copied rules can "
            "raise the score, even on the holdout, and a holdout that shares every rule with "
            "development cannot tell copying from learning. So the guard is a policy against "
            "copied wording, not a detector of overfitting.",
            "The point to land: Every condition is code that writes a reason; the person is the "
            "last condition, never the only one.",
            "Example: On 23 October an early analyzer quoted each failed question with its gold "
            "query; its version passed 15 of 15 holdout questions and a gate of three conditions "
            "said ready. Nobody approved it, and the guard became the fourth condition.",
            'Ask the room: "Which condition would your release process skip?" Expect: the '
            "margin, or the regressions.",
            "Misconceptions: That a typed name proves who approved. It records a claim; "
            "production systems take a signed-in identity.",
            "Transition: A version that passes the gate is trusted, but for which questions?",
        ],
    ),
    # 72 technique 4 ----------------------------------------------------------------------------
    dict(
        kind="technique",
        title="4) Autonomy earned per metric family",
        minutes=2.5,
        says="A family clears for the unattended level on its own holdout questions; drift lowers "
        "it",
        src="platform/src/datapilot/loop4_hill_climbing/eligibility.py (confirmed_clearance); "
        "section-4-hill-climbing-loop/README.md; section-4-hill-climbing-loop/assignment; "
        "sources.py entry 103; docs/evidence/section-4-hill-climbing-loop.md; round 1 ruling "
        "15, upskilling 11, presenter 15",
        allow_commands=True,
        figure={
            "diagram": "pattern-autonomy-per-family",
            "alt": "Autonomy earned per metric family: a family clears when it has at least 3 "
            "holdout questions and each passes 2 of 3 runs; for example, sales totals clear and "
            "run unattended, order counts have one shortfall and stay assisted, and basket size "
            "has 1 question, which is not evidence, so it stays assisted; scheduled re-runs "
            "where a drop comes with no change of yours lower that family only; the failure of "
            "one level for the whole agent: it lets one weak family post unchecked",
        },
        on_slide=[
            "- **What:** grant the unattended level per group of questions about one measure, not "
            "to the whole agent.",
            "- **How:** a family clears with 3 or more holdout questions, each passing 2 of 3 runs; "
            "others stay assisted.",
            "- **Example:** sales totals post unattended; order counts post assisted; risky actions "
            "wait.",
            "- **Drift:** a scheduled re-run that falls with no change of yours lowers that family "
            "only.",
            "- **Elsewhere:** a feature flag turned on per segment; published levels of autonomy "
            "for agents.[^103]",
            "Key idea: Autonomy follows each family's evidence, and the same measurement takes it "
            "back.",
        ],
        notes=[
            "Purpose: Teach the fourth technique: autonomy earned per metric family, and what so "
            "small a sample can and cannot support.",
            "What to say: Passing the gate says the rules are better, not that every answer may "
            "post unwatched. A metric family is a group of questions about one measure: revenue, "
            "orders, average order value. Walk the diagram; its names are generic, and sales "
            "totals plays the part of DataPilot's revenue family. On the left, the rule: a family "
            "clears for the unattended level when it has at least three holdout questions and "
            "each passes 2 of 3 runs. In the middle, three families. Sales totals clear and post "
            "unattended. Order counts have one shortfall and stay assisted: their answers still "
            "post, labelled verified, and anything risky waits for a person. In DataPilot, for an "
            "answer with no personal data, the two levels differ only in the label the post "
            "carries; in yours, decide what the unattended level may skip. Basket size has a "
            "single question, which is not evidence. DataPilot today does clear its one-question "
            "family, average order value; that is the gap Assignment 4: Hill-climbing loop "
            "closes. On the right, drift: scheduled re-runs catch a drop you did not cause and "
            "lower that family only. Three questions at 2 of 3 runs is a floor, not proof: a "
            "decision with a review date. And DataPilot re-runs only the questions that fall "
            "short, so a second chance leans toward clearing; in yours, add the two rounds "
            "together, 4 of 6, or re-run every question. A level is earned twice: the event "
            "loop's forced failures prove the safeguards once; this rule proves the answers, "
            "family by family. Our reading of Feng and others' levels: assisted is their "
            "approver role, unattended their observer role, Source [^103].",
            "Do: At 3:16, on your own screen. Stalled: no candidate yet (after a baseline started "
            "at 3:05, one by about 3:17:30 is normal: judge by the strip), or N of 70 runs done "
            "unchanged for 2 minutes. Only then: stop, reset, start, as in slide 67's third Do "
            "line, then the two buttons; read its gate at the Thursday review. After 3:17 start "
            "none.",
            "The point to land: Grant autonomy where the evidence earned it, one family at a "
            "time, review it on a date, and let the same measurement take it back.",
            "Example: Revenue cleared in 7 of 11 live promotions: none of 3 under the earlier "
            "one-experiment rule, 7 of 8 under today's. The clearance itself varies.",
            'Ask the room: "Which family would you let post unattended first?" Expect: read-only '
            "totals.",
            "Misconceptions: That clearing a family means nobody checks risky answers. Personal "
            "data and exports wait for a person at every level.",
            "Transition: So where should the learned rules live in your own text-to-SQL design?",
        ],
    ),
    # 73 design callout -------------------------------------------------------------------------
    dict(
        kind="design_callout",
        title="Text-to-SQL design: Where learned rules live",
        minutes=1.5,
        says="Where learned rules live, and an execution-match benchmark that decides each change",
        src="section-4-hill-climbing-loop/README.md; platform/src/datapilot/loop4_hill_climbing/"
        "evaluator.py (compare); .dev/deck-evidence.md E11, E12; sources.py entry 12; round 1: "
        "upskilling 16, engineer 17, presenter 4",
        on_slide=[
            "Lead: Put rules where you can diff, test and roll them back.",
            "Decision: where do learned rules live, and what decides?",
            "| Option | Decided by | Watch for |",
            "|---|---|---|",
            "| Prompt patch per failure | The questions just fixed | Rises by construction |",
            "| Versioned knowledge file | Execution match on gold[^12] | Rules copying the test |",
            "| Semantic layer or views | A reviewed change, all gold re-run | Slow; promote proven "
            "rules here |",
            "DataPilot: a knowledge file learned from failures, promoted on the holdout.",
        ],
        notes=[
            "Purpose: Turn the hill-climbing loop into two design decisions for the learner's own "
            "text-to-SQL system.",
            "What to say: Two decisions. First, where learned rules live. A prompt patch is "
            "judged by the questions it was written for, so it rises by construction. A "
            "versioned knowledge file, like ours, holds each rule with its query guidance and can "
            "be diffed, approved and rolled back. A semantic layer or views put rules where every "
            "tool reads them; a change there is reviewed and every gold question re-run, which is "
            "slow, so promote a rule there once the file has proven it. Second, what decides: "
            "execution match. Run the agent's query and the gold query and compare the results, "
            "never the query text, on more than one database, because one database lets some "
            "wrong queries pass, Source [^12]; two is our minimum, not the paper's. DataPilot "
            "ignores column names, requires the same column count, compares rows as a multiset "
            "unless the question asks for an order, and allows numbers a small tolerance.",
            "The point to land: Keep rules where you can diff and roll them back, and let results "
            "on held-out gold queries decide.",
            "Example: The gold answer to the fiscal year 2025 question, 64,015,091.21 dollars, is "
            "checked on the warehouse and on a second database seeded differently.",
            'Ask the room: "Where do your metric definitions live today?" Expect: dbt, a wiki, or '
            "old dashboards.",
            "Misconceptions: That comparing query text is stricter. It rejects correct queries "
            "written another way.",
            "Transition: The four techniques on one page.",
        ],
    ),
    # 74 cheat sheet ----------------------------------------------------------------------------
    dict(
        kind="table",
        title="Cheat Sheet: The hill-climbing loop",
        minutes=1.5,
        says="The four techniques: what each does and how to apply it in your system",
        src="the four technique slides; section-4-hill-climbing-loop/demo/walkthrough.md, If you "
        "copy this into your repository; sources.py entry 106; round 1 ruling 2, engineer 13",
        on_slide=[
            "Lead: Four techniques, what each does, and how to apply it in your system.",
            "| Technique | What it does | How to apply it in your system |",
            "|---|---|---|",
            "| Gold questions, the split | Judges each change on unseen questions | Write 20 to "
            "50 from real failures[^106]; split first |",
            "| Agents propose, code decides | Agents write rules; checks drop bad ones | Run each "
            "rule's query on the schema; write two |",
            "| The gate | Blocks a version unless all conditions pass | Gain above noise, zero "
            "regressions, a guard, a named approver |",
            "| Autonomy per family | Grants unattended runs the evidence earned | Clear a family "
            "on 3 holdout questions; re-run on a schedule |",
        ],
        notes=[
            "Purpose: Give the four techniques on one page, each with what it does and how to "
            "apply it in the learner's own system.",
            "What to say: One row per technique; the last column is what to do next week. Gold "
            "questions: write 20 to 50 from real failures, each answer checked by a person, as "
            "Anthropic suggests, Source [^106], and split them before you read a failure. Agents "
            "propose, code decides: run each proposed rule's query against your schema, refuse a "
            "rule that copies test wording, and write two candidates, keeping one on development "
            "questions. The gate: a holdout gain larger than your noise, zero confirmed "
            "regressions, rules that pass the guard, and a signed-in approver. Measure your "
            "noise: run the active version twice in one session and count the questions that flip. "
            "Autonomy per "
            "family: clear a family only on three or more holdout questions, and re-run the gold "
            "set on a schedule and whenever the model or the data changes. Assignment 4 builds "
            "parts of this; the full list is in the section's README.",
            "The point to land: Split first, measure second, learn third; never in another order.",
            "Example: The discount rule from the failure story is the test for the gate's row: it "
            "must be blocked.",
            'Ask the room: "Which row is missing in your team today?" Expect: the split, most '
            "often, then the scheduled re-run.",
            "Misconceptions: That rules written by people can skip the gate. The discount rule was "
            "written for the course by a person.",
            "Transition: Now let us see what the improvement loop did while we talked.",
        ],
    ),
    # 75 demo -----------------------------------------------------------------------------------
    dict(
        kind="demo",
        title="Section 4: Hill-climbing loop - Implementation Notes: The gate decides",
        minutes=12,
        says="The analyzer team's diff, the candidate experiment and the gate, approval by name, "
        "then the revenue question at its earned level, live",
        src="platform/demos/registry.yaml (section hill-climbing-loop); docs/instructor-guide.md, "
        "Section 4 and the class-day safeguard; docs/evidence/section-4-hill-climbing-loop.md; "
        "DECISIONS.md, 27 October 2026, decision 2; round 1 rulings 3 and 23, presenter 3 and 19",
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
            "Purpose: Read what the chain started on the failure story produced, approve it by "
            "name, and send the fiscal year 2025 revenue question at the level its family earned.",
            "What to say: Let's see what the loop learned while we talked. This is the analyzer "
            "team's diff: two candidates, one kept on the development questions alone; the "
            "holdout never took part. Every rule here survived the critic, the check against the "
            "schema, and the overfit guard. Now the candidate's ledger, against this session's baseline. "
            "Look for two things: flips, questions that failed under the baseline and pass now, "
            "and the regression count. If the count is zero and the holdout passes are higher, "
            "the gate waits for one thing: a person. I read the diff, type my name as the "
            "approver, and approve. The console refuses an empty name or the word console; in "
            "your system, record the signed-in person and exactly what they approved. Now the "
            "runner makes it the active version and re-runs any holdout question that fell "
            "short, to decide which families cleared the unattended level. Then the revenue "
            "question arrives as a webhook and posts at that level. Nothing here is scripted: "
            "every count on screen comes from this run.",
            "Do: Run sheet. 3:21:30: the analyzer team's diff (two candidates, one kept), then "
            "the candidate's ledger: flips, 0 regressions.",
            "Do: Gate ready: read the diff aloud, type your name in Your name, recorded as the "
            "approver, above the knowledge diff, and click Approve.",
            'Do: "Active version" shows: Improve > Set the unattended level, or make autonomy '
            'LEVEL=unattended BY="your name".',
            "Do: The note above the Events buttons goes away: Events > Send webhook question. The "
            "machine time is about 9 to 17 minutes; approval waits for this slot, so the last run "
            "lands about 3:24 to 3:28.",
            "Do: It lands early: use the time left on the candidate's ledger and the LangSmith "
            "trace list, then go to the evidence slide early.",
            "Do: Stall (the test is on slide 72): stop, reset, start, as in slide 72's notes; "
            "after 3:17 start none: say so, go to the evidence slide, and read the class chain at "
            "the Thursday review.",
            "Do: Fallback, not landed by 3:33: go to the evidence slide, return when it lands, and "
            "pay for it by skipping the evidence slide's room question and shortening Ask about "
            "anything.",
            "Do: Fallback, Gold check failed: the class-day safeguard, in the last demo below.",
            "Demo: The baseline experiment.",
            "Command: done on the failure story at 3:04, from its Do lines; it started at the "
            "poll with Improve > Run experiment on the active version, or make demo "
            "NAME=improve-baseline-experiment.",
            "Point at: only if asked again: the holdout ledger, the failed trap questions, one "
            "row's start time and its trace link or Not traced.",
            "Expected output: version 1 at 2 of 15 holdout questions, as in every baseline from 22 "
            "to 25 October, and 4 or 5 of 25 development questions.",
            "While it runs: it finished before the section, 236 to 386 seconds after the trigger.",
            "If it fails: handled on the failure story (its first Do line).",
            "Backup screenshot: " + EXPECTED + "improve-baseline-experiment-ledger.png.",
            "Demo: The naive analyzer, blocked.",
            "Command: read on the failure story at 3:04; queued at the break with make demo "
            "NAME=improve-naive-analyzer-blocked PLANTED=1, or Improve > Run the naive analyzer "
            "(planted).",
            "Point at: only if asked again: one rule quoting a benchmark question word for word, "
            "and the gate's verdict, blocked, naming the rules the overfit guard rejects.",
            "Expected output: about 21 rules, every one flagged, and the verdict blocked; in 6 "
            "measured runs, holdout 2 of 15 five times and 0 of 15 once.",
            "While it runs: it finished in the break, 211 to 580 seconds from the trigger to the "
            "verdict.",
            "If it fails: handled on the failure story (its third Do line).",
            "Backup screenshot: " + EXPECTED + "improve-naive-analyzer-blocked-gate.png.",
            "Demo: The analyzer team and approval.",
            "Command: started on the failure story at about 3:05: make reset "
            "NAME=hill-climbing-loop, then Improve > Run analyzer (or make demo "
            "NAME=improve-analyzer-team-approve), and at once Improve > Run experiment on the "
            "candidate.",
            "Point at: one diagnosis with no rule in it; one proposed rule with its query "
            "guidance; the critic's decision and reason; the guard's result; the line naming "
            "candidates A and B and the one kept; the knowledge diff waiting for approval.",
            "Expected output: a candidate version with general rules in the diff, not yet "
            "approved. In the main chain of 24 October, candidate A passed 13 of 25 development "
            "questions with 8 rules and B 14 of 25 with 6, so B was kept as version 11; in the "
            "capture chain, A passed 22 of 25 and was kept as version 13.",
            "While it runs: during the question and technique slides, 326 to 377 seconds in five "
            "measured runs, ending by about 3:11; the candidate experiment follows, and the gate "
            "reads about 3:13 to 3:19. Slow but moving is not stalled: if the gate has not read at "
            "3:17, say: 70 benchmark runs are still in flight, and a confirming re-run lengthens "
            "them.",
            "If it fails: a stall: the run sheet's stall fallback.",
            "Backup screenshot: " + EXPECTED + "improve-analyzer-team-diff.png, the knowledge "
            "diff under the line naming both candidates.",
            "Demo: The candidate experiment.",
            "Command: nothing to press: it was queued with the analyzer. Only if it never started, "
            "Improve > Run experiment on the candidate, or make demo "
            "NAME=improve-candidate-experiment; a second press queues a second experiment. "
            "Approve as the run sheet says; the button stays off until a name is typed.",
            "Point at: the flips against this session's baseline; regressions at zero on both "
            "splits; the gate's reason lines, one per condition; after approval, the line saying "
            "the version is the active version.",
            "Expected output: holdout flips, no regressions, the gate ready for human approval. "
            "In the registry's measured runs, 0 to 12 of 13 holdout trap questions flipped, a "
            "majority in 6 of 10, in 171.3 to 459 seconds; kept candidates of two passed 12 to 14 "
            "of 15. The gate may block, which is a correct outcome.",
            'While it runs: if the ledger reads "Apparent regression: confirming", say: the gate '
            "is re-running before it believes a failure.",
            "If it fails: blocked: say the gate refused a version that did not earn it, which is "
            "the point; leave the verdict on screen and go to the evidence slide. A stall: the run "
            "sheet's stall fallback.",
            "Backup screenshot: " + EXPECTED + "improve-candidate-experiment-ledger.png, 14 of 15 "
            "against 2 with 12 fixed and 0 regressions.",
            "Demo: Cleared for the unattended level.",
            "Command: Events > Send webhook question, or make demo "
            "NAME=improve-cleared-unattended, once the status line shows the kill switch released "
            "and the unattended level.",
            "Point at: the run's strip with Gold check passed and the value; the level it posted "
            "at; the status line naming the families cleared.",
            "Expected output: 64,015,091.21 dollars, posted at the unattended level when revenue "
            "cleared, at the assisted level when not; correct at the unattended level in 8 "
            "recorded runs, 50 to 162 seconds after the first send when held for the clearance "
            "re-runs.",
            "While it runs: say how a family clears: every holdout question passes 2 of 3 runs, "
            "and one that falls short must pass 2 of 3 more. The assisted level is a correct "
            "outcome: the answer still posts, labelled verified instead of unattended.",
            'If it fails: if the strip reads "Gold check failed", use the class-day safeguard, '
            "live. One: say the class version misses a trap, and its record stays as it is. Two: "
            'make safeguard-activate BY="your name". Three: show the status line naming the '
            "version verified in rehearsal. Four: Events > Send webhook question again. Five: if "
            "it stalls, send again; do not reset, since a reset sets the report-only level. If "
            "make safeguard-status named no version before class, leave the wrong answer on "
            "screen as the gate's evidence. Rehearsed live twice; correct both times, in 19 and "
            "21 seconds.",
            "Backup screenshot: " + EXPECTED + "improve-cleared-unattended-board.png, the posted "
            "answer with Gold check passed.",
            "The point to land: Rules were learned from failures, measured on questions no one "
            "tuned on, and trusted only as far as the evidence went.",
            "Example: In the capture chain of 24 October, run 59174f10 posted 64,015,091.21 dollars at the unattended "
            "level under version 13, which passed 14 of 15 holdout questions against 2 with 0 "
            "regressions and was " + APPROVED_13 + ". In class you approve today's candidate "
            "under your own name.",
            'Ask the room: "Would you have approved this diff without the ledger?" Expect: no; '
            "the rules read well either way.",
            "Misconceptions: That the demo is scripted. Every rule, flip, and level comes from "
            "this run; the counts differ from rehearsal.",
            "Transition: One chain is a story; next, the measurement with and without the loop.",
        ],
    ),
    # 76 evidence -------------------------------------------------------------------------------
    dict(
        kind="evidence",
        title="Measured: With and without the hill-climbing loop",
        scoreboard=4,
        minutes=2,
        says="Starting rules against learned rules: 2 against 13 of 15 holdout questions, 0 "
        "regressions; single candidates 2 to 11 of 15",
        src="docs/benefits.md, Section 4: Hill-climbing loop; .dev/deck3-evidence.md, part 3; "
        "docs/evidence/section-4-hill-climbing-loop.md (74ff242b, b50131b4, the two-candidate "
        "rows, revenue cleared 7 of 11); .dev/deck-evidence.md E45; .dev/deck2-reconcile.md items "
        "4 and 5; round 1 rulings 1, 14, 15, 16, 26",
        chart={
            "type": "column",
            "title": "Questions passed, one session",
            "categories": ["Holdout (15)", "Development (25)"],
            "series": [
                ("Starting rules (version 1)", [2, 5]),
                ("Learned rules (version 11)", [13, 16]),
            ],
            "x_label": "Benchmark split",
            "y_label": "Passed",
            "maximum": 25,
        },
        on_slide=[
            "Lead: The analyzer team varies from run to run, so gate every candidate on unseen "
            "questions.",
            "Sample: one session; 15 holdout questions run 3 times, a pass at 2 of 3; 25 "
            "development run once",
            "- **Regressions:** 0",
            "- **One candidate:** 2 to 11 of 15",
            "- **Better of two:** 12 to 14 of 15",
            "- **Revenue cleared:** 7 of 11 promotions",
        ],
        notes=[
            "Purpose: Show the measured effect of the hill-climbing loop, with its sample size, "
            "the analyzer team's own variation, and where the fiscal year question stands.",
            "What to say: One rehearsal session of 24 October 2026. The starting rules, version "
            "1, pass 2 of 15 holdout and 5 of 25 development questions. The learned rules, "
            "version 11, which the analyzer team wrote and the gate promoted, pass 13 of 15 and "
            "16 of 25, with 0 regressions. Both splits share the five business rules, so this "
            "measures learning those rules, not rules nobody wrote down. And every candidate was "
            "gated on the same 15 questions, so a version kept for passing them scores a little "
            "high on them; refresh the holdout, Source [^110]. The lines on the right measure "
            "the analyzer team itself. A run that wrote one candidate scored 2 to 11 of 15, "
            "and one of those, version 4, read 12 on a re-measurement; a run that wrote two and "
            "kept the better on development questions scored 12 to 14, in 7 promotions. Those "
            "runs are not paired, and an analyzer fix landed in the same sessions. Revenue "
            "cleared the unattended level in 7 of 11 live promotions: none of 3 under the "
            "earlier one-experiment rule, 7 of 8 under today's. Read that as a gate that usually "
            "opens on a small sample, a decision with a review date, not a measured error rate. "
            "The scoreboard is complete: the published run is version 13, a later promotion of "
            "the same loop.",
            "The point to land: The loop took the holdout from 2 to 13 of 15 with no regression; "
            "the analyzer team varies, so gate every candidate.",
            "Example: Experiments 74ff242b and b50131b4; the published answer is run 59174f10, "
            "version 13, 14 of 15 holdout questions.",
            'Ask the room: "Why choose between two candidates on development questions, not the '
            'holdout?" Expect: choosing on the holdout would make it a development set.',
            "Misconceptions: That 13 of 15 is an accuracy rate. It is one count on 15 questions; "
            "version 11 measured 13 and, later that day, 12.",
            "Transition: Questions before the closing.",
        ],
    ),
    # 77 Ask about anything (copied) ------------------------------------------------------------
    dict(
        kind="qa",
        title="Ask about anything",
        minutes=2.5,
        says="Questions about the hill-climbing loop, and one question that applies the gate",
        src="the reference deck, slide 31; the second rebuild's recap question (slide 71); round 1 "
        "upskilling 15",
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
            "Purpose: Take questions on the hill-climbing loop before the closing.",
            "What to say: Before the chat's questions, ask, for 30 seconds: a new support prompt "
            "beats last month's run of the old one by 3 of 30 on its tuning tickets; why is that "
            "not proof, and what would you run? Expect two reasons: the tuning tickets are the "
            "development set, and last month's run is another session. Then take the chat's "
            "questions.",
            "Do: The answer to give: run both prompts now, in one session, on held-out tickets, "
            "three runs each; require a gain above noise and zero confirmed regressions; then a "
            "signed-in reviewer approves.",
            "Transition: Next, the question, answered.",
        ],
    ),
]
