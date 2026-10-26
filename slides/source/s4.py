"""Section 4: Hill-climbing loop, 3:05-3:48, 43 minutes, under the design system.

Every slide follows the slide schema in slides/design-system.md. Course numbers come from the deck
evidence (entries E1 and on, named in each slide's src); external claims carry a source marker
numbered as the deck's verified source list (deck-sources, [1] to [53]). The hill-climbing chain
starts on the opener (about 3:07) and runs while slides 57 to 60 are taught, so the DEMO slide reads
its results (round 1, ruling 11).
"""

RULES = "design system"

DEMO_PAGE = "https://github.com/ANI-IN/loop-engineering/tree/main/section-4-hill-climbing-loop/demo"
EXPECTED = "section-4-hill-climbing-loop/demo/expected/"

SLIDES = [
    # 1 section opener: the chain starts here ----------------------------------------------------
    dict(
        kind="opener",
        title="Section 4: Hill-climbing loop",
        minutes=3,
        says="Read the two finished experiments, start the chain, and name the section's result",
        src="section-4-hill-climbing-loop/README.md; docs/instructor-guide.md, Section 4; evidence "
        "E42, E46, E54 (docs/benefits.md, Section 4)",
        on_slide=[
            "Fixes: learned rules that raise a score and quietly break other answers",
            "Insight: Same model, learned rules for the five traps: holdout passes rose from 2 to 13 "
            "of 15, 0\u00a0regressions.",
        ],
        notes=[
            "Purpose: Start the hill-climbing chain at once, reading the two experiments that "
            "finished in the break, and name the section's measured result.",
            "What to say: Welcome back. First let's put the machine to work, because this chain "
            "needs about 8 to 14 minutes before the gate reads. I'm on the Improve page. The baseline that started at the "
            "poll: the starting knowledge passes 2 of 15 holdout questions, and every trap "
            "question fails. The naive analyzer from the break: every rule it wrote is flagged, "
            "and the gate says blocked. Now I reset the section in the "
            "demo terminal, which keeps this baseline, then press Run analyzer and Run "
            "experiment on the candidate. If the reset answers not reset, the naive run is still "
            "finishing; we wait for it and reset then. While it works: the fiscal year 2025 revenue question "
            "is still wrong, because the rules are missing. This loop learns them. In one live "
            "session, same model, rules learned for the five traps lifted holdout passes from 2 "
            "to 13 of 15.",
            "The point to land: The model did not change; the knowledge did, and a gate decided "
            "whether to trust it.",
            "Example: Version 11 of the knowledge, promoted live on 24 October, passed 13 of 15 "
            "holdout questions against 2 for version 1.",
            'Ask the room: "How do you decide today that a prompt change is better?" Expect: a few '
            "manual checks, or the questions that just failed.",
            "Misconceptions: That improvement needs a bigger model. Here the same model went from 2 "
            "to 13 of 15 on rules alone.",
            "Transition: While the analyzer team works: how most teams improve an agent, and why "
            "it backfires.",
        ],
    ),
    # 2 problem story ---------------------------------------------------------------------------
    dict(
        kind="story",
        title="Patch each failure, and other answers break",
        minutes=2.5,
        says="A patch per failed question raises that score; one plausible rule broke nine answers",
        src="platform/packs/datapilot_us/knowledge/v2-overbroad.yaml lines 15-21; evidence E47 "
        "(docs/calibration-report.md, The over-broad rule)",
        code={
            "language": "yaml",
            "origin": "platform/packs/datapilot_us/knowledge/v2-overbroad.yaml lines 15-21, the "
            "over-broad rule, written by hand for the course; long lines wrapped",
            "lines": [
                "- id: exclude-discounted-orders",
                "  title: Exclude discounted orders from revenue",
                "  rule_text: >-",
                "    Orders with a discount are promotional and distort",
                "    revenue, so exclude discounted orders from revenue.",
                "  applies_when: a question asks for revenue, sales,",
                "    or average order value",
                "  sql_guidance: WHERE o.discount_cents = 0",
            ],
            "marks": [
                (3, "Orders with a discount are promotional", 1),
                (5, "revenue, sales,", 2),
                (7, "WHERE o.discount_cents = 0", 3),
            ],
        },
        on_slide=[
            '"Revenue came out wrong again. Add a rule and ship it."',
            "Value: Holdout questions passed | 12, then 7",
            "Value: Confirmed regressions | 9",
            "1. Sounds like a business rule",
            "2. Reaches every revenue question",
            "3. Removes real sales",
            "Footer: One added rule, measured live on 24 October 2026; the gate blocked it",
        ],
        notes=[
            "Purpose: Show, with a measured run, that a fix aimed at failed questions can raise "
            "their score and break answers that were right.",
            "What to say: The habit this section replaces is familiar. A check fails, someone adds "
            "a line to the prompt for each failed question, the same check passes the next day, "
            "and it ships. The score on those questions rises by construction, because the patch "
            "was written for exactly them. What nobody measures is everything else. Here is one "
            "patch, measured. We wrote this rule by hand to look like a sensible fix for a revenue "
            "answer. Marker one: it reads like a business rule, a reason and an instruction. "
            "Marker two: it applies to every question about revenue, sales, or average order "
            "value, not just the one that failed. Marker three: the Structured Query Language "
            "(SQL) guidance drops every order with a discount, and discounted orders are real "
            "sales. On 24 October we added it to the promoted version 11, which passed 12 of 15 "
            "holdout questions in that session; one question moves between sessions, as the "
            "evidence slide shows. With the rule, holdout passes fell to 7 of 15 and development "
            "questions from 15 to 11 of 25: 9 answers that passed before now failed, confirmed by "
            "re-runs, 4 development and 5 holdout. Nothing errored. The gate blocked it: holdout "
            "passes fell, and it named each broken answer.",
            "The point to land: A rule that sounds right is untested until every answer is "
            "re-measured.",
            "Example: The gate's verdict read: blocked, 9 regressions on questions that passed "
            "under version 11.",
            'Ask the room: "Who has shipped a prompt fix that broke something else?" Expect: most '
            "hands, found by a user weeks later.",
            "Misconceptions: That a rule that sounds right is right. This one sounds like policy "
            "and removes real revenue.",
            "Transition: So what would have caught it before it shipped? A loop with a gate.",
        ],
    ),
    # 3 concept diagram -------------------------------------------------------------------------
    dict(
        kind="concept",
        title="The hill-climbing loop: learn here, decide there",
        minutes=3,
        says="Experiment, analyzer team, overfit guard, two candidates, and a gate of four conditions",
        src="section-4-hill-climbing-loop/diagrams/hill-climbing-loop.excalidraw; "
        "platform/src/datapilot/loop4_hill_climbing/gate.py lines 1-25; evidence E11, E40, E45, "
        "E46, E50",
        figure={
            "diagram": "hill-climbing-loop",
            "alt": "The benchmark, 25 development and 15 holdout questions, feeds an experiment "
            "scored by execution match on two databases; the analyzer team of three agents reads "
            "only failed development questions; the overfit guard rejects a rule that copies a "
            "question or a gold query; of two candidates the better one is kept; the promotion "
            "gate needs all four conditions, in the order the gate writes its reasons: more holdout "
            "passes than the active version, zero confirmed regressions on both splits, human "
            "approval, and every new rule passing the overfit guard; the promoted version becomes "
            "the active knowledge version and the next baseline",
            "stand_in": "section-4-hill-climbing-loop/diagrams/hill-climbing-loop.svg",
        },
        on_slide=[],
        notes=[
            "Purpose: Give the whole loop in one picture, with the gate's four conditions in the "
            "order the gate's code checks them.",
            "What to say: The idea on this slide: Agents propose rules from development failures; code and a person decide on questions the agents never saw. "
            "Walk the diagram clockwise from the top left. The benchmark has 40 "
            "questions with hand-written gold queries: 25 development questions, 15 holdout "
            "questions. An experiment runs all of them under one knowledge version and scores "
            "each answer by its result, on two databases, not by its query text. Development "
            "questions run once, holdout questions three times. The analyzer team, three agents, "
            "reads only the failed development questions: a failure analyst diagnoses, a rule "
            "writer proposes rules, a critic keeps, narrows, or drops them. Then the overfit "
            "guard, which is code: no rule may copy a question or a gold query. The team writes "
            "two candidates; the better one on the development questions is kept. Now the gate, "
            "numbered in the order the gate writes its reasons: one, more holdout passes than the active version; "
            "two, zero confirmed regressions on both splits; three, human approval; four, every "
            "new rule passes the overfit guard. All four, or the candidate is blocked. A promoted "
            "version becomes the active knowledge and the next baseline. One honest caveat. The "
            "holdout is unseen by the agents, not by us: we changed the analyzer, the guard, and "
            "the gate after reading holdout results, and each change makes it a little less "
            "unseen. And our holdout tests the same five rules on new questions; it does not show "
            "the loop finding a rule it never failed on. Refresh yours, and keep a final set "
            "nobody reads.",
            "The point to land: The questions the agents learn from never decide; the questions "
            "that decide are never shown to them.",
            "Example: The fiscal year rule, February to January and named for its end year, is "
            "learned from failed development questions and proven on holdout questions the "
            "agents never read.",
            'Ask the room: "Which condition would you drop first to move faster?" Expect: human '
            "approval; then ask what else would catch a rule that copies the test.",
            "Misconceptions: That a holdout split is enough on its own. The next slides show the "
            "guard and the regression check each closing a hole the holdout leaves.",
            "Transition: Here is the code that keeps the agents to proposing.",
        ],
    ),
    # 4 mechanism: the analyzer team and the overfit guard ---------------------------------------
    dict(
        kind="mechanism",
        title="Agents propose rules; code decides which survive",
        minutes=3,
        says="The holdout refusal, the subtracting critic, the schema check, and the overfit guard",
        src="platform/src/datapilot/loop4_hill_climbing/analyzer.py lines 206-208, 241-242 and "
        "244; overfit_guard.py; pack.yaml evaluation; evidence E41, E48, E52",
        code={
            "language": "python",
            "origin": "platform/src/datapilot/loop4_hill_climbing/analyzer.py lines 206-208, 241-242 "
            "and 244 (lines 209-240 and 243 left out; the common indent removed)",
            "lines": [
                "holdout = [f.item.id for f in failed if f.item.split is not Split.DEV]",
                "if holdout:",
                '    raise ValueError(f"the analyzer team reads dev items only, got {holdout}")',
                "...",
                "kept, ignored = apply_reviews(proposed, reviews)",
                "guidance = [self.guidance.check(rule) for rule in kept] if self.guidance else []",
                "...",
                "guard = [self.guard.check(rule) for rule in runs]",
            ],
            "marks": [
                (2, "raise ValueError", 1),
                (4, "apply_reviews(proposed, reviews)", 2),
                (5, "self.guidance.check(rule)", 3),
                (7, "self.guard.check(rule)", 4),
            ],
        },
        on_slide=[
            "Idea: after the rule writer, every step only removes rules",
            "1. A holdout question stops it",
            "2. The critic only subtracts",
            "3. A rule's query must run on the schema",
            "4. The overfit guard runs last",
        ],
        notes=[
            "Purpose: Show the real code that keeps the holdout unseen and lets agents propose but "
            "never approve their own rules.",
            "What to say: This is the analyzer team's run. Marker one: before any model call, the "
            "code checks the failed questions it was handed, and a single holdout question raises "
            "an error. The holdout stays unseen in code, not by convention. Marker two: the "
            "critic's reviews are applied here. A review can keep, narrow, or drop a proposed "
            "rule; a review of a rule the writer never proposed is ignored, so the critic can "
            "never add one. Marker three: every rule carries SQL guidance that goes into the "
            "analyst's prompt word for word, so it is parsed against the real catalog. This check "
            "exists because of a measured failure: on 23 October a learned rule held a "
            "placeholder instead of a predicate, and the last run of that chain answered "
            "63,986,616.77 dollars against gold 64,015,091.21, labelled verified. Marker four: the "
            "overfit guard, deterministic and last. It rejects a rule that shares 6 consecutive "
            "words with any benchmark question or 20 consecutive SQL tokens with any gold query, "
            "thresholds from the pack. Live, it rejected a fiscal-quarter rule the critic had "
            "kept, in 4 chains, for copying 20 or more tokens of a gold query. Only rules that "
            "survive every check reach a candidate.",
            "The point to land: Let agents generate; let deterministic code subtract.",
            "Example: The critic dropped a business-day holiday rule in several runs; the guard "
            "caught the copied fiscal-quarter rule the critic missed.",
            'Ask the room: only if ahead of the clock: "Why may the critic not add rules?" Expect: then it would propose and '
            "judge its own work.",
            "Misconceptions: That the guard stops overfitting. It stops copying; a paraphrased rule "
            "can pass it, which is why the holdout gate decides.",
            "Transition: The surviving rules become a candidate. Now the gate that judges it.",
        ],
    ),
    # 5 mechanism: the gate's decide ------------------------------------------------------------
    dict(
        kind="mechanism",
        title="The gate's four conditions, in five lines",
        minutes=2.5,
        says="One live session, more holdout passes, zero regressions, approval, and a clean guard",
        src="platform/src/datapilot/loop4_hill_climbing/gate.py lines 117-135; pack.yaml "
        "evaluation; evidence E40, E41, E49",
        code={
            "language": "python",
            "origin": "platform/src/datapilot/loop4_hill_climbing/gate.py lines 117-135, the gate's "
            "decide (lines 118 and 121-133 left out; the common indent removed)",
            "lines": [
                "a, c = active.passes(Split.HOLDOUT), candidate.passes(Split.HOLDOUT)",
                "...",
                "better = c > a",
                "clean = regressions.total == 0",
                "...",
                "ready = better and clean and not overfit_flags",
                "promoted = ready and bool(approved_by)",
            ],
            "marks": [
                (2, "better = c > a", 1),
                (3, "clean = regressions.total == 0", 2),
                (6, "bool(approved_by)", 3),
                (5, "not overfit_flags", 4),
            ],
        },
        on_slide=[
            "Idea: the gate compares question by question, in one live session",
            "1. More holdout passes",
            "2. Zero confirmed regressions",
            "3. Human approval",
            "4. Overfit guard on the new rules",
        ],
        notes=[
            "Purpose: Show that promotion is a few deterministic lines, with every condition "
            "recorded, so learners can copy the shape.",
            "What to say: Just above these lines, the gate refuses to compare experiments "
            "from different live sessions: the model, the data, and the settings must match, or "
            "you measure drift instead of rules. That is why the baseline ran today, at the poll. "
            "Marker one: more holdout passes than the active version; each holdout question runs "
            "three times and passes on two. Marker two: zero regressions. A regression passed "
            "under the active version and fails under the candidate, and it counts only once "
            "confirmed: a holdout question gets 3 more runs and must fail 2; a development "
            "question is re-run twice under each version. One question once passed only 1 of 3, "
            "then passed 3 of 3 more: not a regression. In our runs no candidate gained on the "
            "holdout while it broke an answer, so this condition has not yet decided a verdict "
            "alone; it exists for that case. Marker three, on the last line: a person "
            "approves the knowledge diff, and only then is it promoted. Marker four: every new "
            "rule passes the overfit guard again, here at the gate; the code checks it on the "
            "line above approval, so one, two, and four make ready, and three makes promoted. The "
            "gate writes its reasons in this order: holdout passes, regressions, human approval, "
            "overfit guard.",
            "The point to land: An average can hide a broken answer; a paired check, question by "
            "question, names it.",
            "Example: The over-broad rule failed markers one and two: 7 against 12, and 9 confirmed "
            "regressions.",
            'Ask the room: only if ahead of the clock: "Why confirm a regression instead of trusting one failed run?" Expect: '
            "model answers vary run to run.",
            "Misconceptions: That a higher holdout score is enough to promote. It is one condition "
            "of four.",
            "Transition: The chain has been running since the opener. Let's see what it did.",
        ],
    ),
    # 6 demo ------------------------------------------------------------------------------------
    dict(
        kind="demo",
        title="Live: from the baseline to a right answer",
        minutes=15,
        says="The analyzer team's diff, the candidate experiment and the gate, approval, then the "
        "revenue question at its earned level, live",
        src="platform/demos/registry.yaml (section hill-climbing-loop); docs/instructor-guide.md, "
        "Section 4 and the class-day safeguard; evidence E42, E45, E46, E53, E55, E56",
        on_slide=[
            "Badge: DEMO - 4",
            "What to watch for:",
            "- Analyzer team: two candidates, one kept",
            "- Candidate: failed questions now pass",
            "- Revenue answer: right, earned level",
            "Guaranteed moment: the gate decides against this session's baseline: ready for a "
            "person, or blocked with reasons.",
            "Link: Demo page on GitHub | " + DEMO_PAGE + "#the-candidate-experiment",
        ],
        notes=[
            "Purpose: Read what the chain started on the opener produced, approve it, and send the "
            "fiscal year 2025 revenue question at the level its family earned.",
            "What to say: Let's see what the loop learned while we talked. This is the analyzer "
            "team's diff: two candidates, one kept on the development questions alone; the "
            "holdout never took part. Every rule here was proposed by a model and survived the "
            "critic, the schema check, and the overfit guard. Now the candidate's ledger, against "
            "this session's baseline. Look for two things: flips, questions that failed under the "
            "baseline and pass now, and the regression count. If the count is zero and the holdout passes are "
            "higher, the gate waits for one thing: a person. I read the diff, and I approve. Now "
            "the runner makes it the active version and re-runs any holdout question that fell "
            "short, to decide which metric families earned the unattended level. This is the "
            "part most teams skip: approval says the rules look right; the re-runs say whether "
            "the evidence earns autonomy. Then the revenue question arrives as a webhook and "
            "posts at the level its family earned. Nothing here is scripted: every count on "
            "screen comes from this run.",
            "Demo: The baseline experiment.",
            "Command: read on the opener, at 3:05; it started at the poll with Improve > Run "
            "experiment on the active version, or make demo NAME=improve-baseline-experiment. "
            "Press it only if it never started. No retry after 3:24.",
            "Point at: the benchmark progress strip on the run board, opened into the holdout "
            "ledger; the failed trap questions; one row's start time and its trace link or Not "
            "traced.",
            "Expected output: version 1 at 2 of 15 holdout questions, as in every baseline from 22 "
            "to 25 October, every holdout trap question failed, and 4 or 5 of 25 development "
            "questions.",
            "While it runs: it finished before the section, 236 to 386 seconds after the trigger. "
            "Say: this is the instrument; every later count is compared with this run.",
            "If it fails: if it never started, at 3:06 run make reset NAME=hill-climbing-loop "
            "(about 7 seconds), press the trigger, then at once Improve > Run analyzer and "
            "Improve > Run experiment on the candidate; the runner takes them in order, so the "
            "gate reads about 4 to 6 minutes later than planned, still inside this demo slide. If "
            "it has not read by 3:30, go on to the evidence slide and return to it. If the reset "
            "prints not reset, the naive request is still running: stop, reset, start, as in the "
            "naive analyzer's step.",
            "Backup screenshot: " + EXPECTED + "improve-baseline-experiment-ledger.png, what the "
            "finished ledger looks like, to point at while you reset and run again.",
            "Demo: The naive analyzer, blocked.",
            "Command: read on the opener; queued at the break with make demo "
            "NAME=improve-naive-analyzer-blocked PLANTED=1, or Improve > Run the naive analyzer "
            "(planted).",
            "Point at: one rule quoting a benchmark question word for word; the line saying the "
            "guard flags every rule, not applied; the gate's verdict, blocked, naming the rules "
            "the overfit guard rejects.",
            "Expected output: about 21 rules, every one flagged, and the verdict blocked; in 6 "
            "measured runs, holdout 2 of 15 five times and 0 of 15 once.",
            "While it runs: it finished in the break, 211 to 580 seconds from the trigger to the "
            "verdict. Say: these are patches, one per failed question; its history is the slide "
            "after the evidence.",
            "If it fails: if no verdict shows at 3:06, it may still be behind the baseline: read "
            "the baseline, keep talking, and look again at 3:07. If the reset prints not reset, "
            "the naive request is still running: never reset mid-request; wait until the "
            "Improve page shows it finished, then reset (about 7 seconds). If it has not "
            "finished by 3:08, stop, reset, start: docker compose "
            "stop hill-climbing-runner, then make reset NAME=hill-climbing-loop, then docker "
            "compose start hill-climbing-runner, about 20 seconds in all. Never restart the "
            "runner: a restarted runner keeps serving, so the reset refuses again. Then start the chain, and read the naive "
            "verdict at the Thursday review.",
            "Backup screenshot: " + EXPECTED + "improve-naive-analyzer-blocked-gate.png, the "
            "blocked verdict naming 21 rules, to point at while you reset and run again.",
            "Demo: The analyzer team and approval.",
            "Command: on the opener, about 3:07: make reset NAME=hill-climbing-loop, which keeps "
            "the baseline and clears the naive candidate; then Improve > Run analyzer, or make "
            "demo NAME=improve-analyzer-team-approve, and at once Improve > Run experiment on the "
            "candidate.",
            "Point at: one diagnosis with no rule in it; one proposed rule with its SQL guidance; "
            "the critic's decision and reason; the guard's result; the line naming candidates A "
            "and B and the one kept; the knowledge diff waiting for approval.",
            "Expected output: a candidate version with general rules in the diff, not yet "
            "approved. On 24 October: candidate A passed 13 of 25 development questions with 8 "
            "rules, B 14 of 25 with 6 rules.",
            "While it runs: it runs during slides 57 and 58, 326 to 377 seconds in five measured "
            "runs, ending by about 3:13; the candidate experiment follows during slides 58 to "
            "60, and the gate reads about 3:15 to 3:21. If the team is still writing at 3:13, "
            "say: two analyzer runs and 50 development runs are in flight. If the gate has not "
            "read at 3:19, say: 70 benchmark runs are still in flight, and a confirming re-run "
            "lengthens them.",
            "If it fails: a stalled request still reads as running, so a reset alone refuses: "
            "stop, reset, start: docker compose stop hill-climbing-runner, then make reset "
            "NAME=hill-climbing-loop, then docker compose start hill-climbing-runner, about 20 "
            "seconds in all. Never restart the runner: a restarted runner keeps serving, so the "
            "reset refuses again. The reset keeps the baseline and clears the candidate, so then "
            "press Improve > Run analyzer and Improve > Run experiment on the candidate. A fresh "
            "chain needs about 8 to 14 minutes to the gate: start none after 3:24. If the gate "
            "or the last run has not landed by 3:34, go on to slide 62, return here when the "
            "gate reads, and skip the room questions on slides 62 to 67.",
            "Backup screenshot: " + EXPECTED + "improve-analyzer-team-diff.png, the knowledge "
            "diff under the line naming both candidates, to point at while you reset and run "
            "again.",
            "Demo: The candidate experiment.",
            "Command: nothing to press: it was queued with the analyzer. Only if it never started, "
            "Improve > Run experiment on the candidate, or make demo "
            "NAME=improve-candidate-experiment; a second press queues a second experiment. When "
            "the gate reads ready for human approval, click Approve on the knowledge diff.",
            "Point at: the flips against this session's baseline; regressions at zero on both "
            "splits; the gate's five reason lines, in order: holdout passes, development "
            "regressions, holdout regressions, human approval, overfit guard; after approval, "
            "the line saying the version is the active version.",
            "Expected output: holdout flips, no regressions, the gate ready for human approval. "
            "In the registry's measured runs, 0 to 12 of 13 holdout trap questions flipped, a "
            "majority in 6 of 10, in 171.3 to 459 seconds; that range includes single-candidate "
            "runs, while kept candidates of two, with that session's analyzer fixes, passed 12 "
            "to 14 of 15. The gate may block, which "
            "is a correct outcome.",
            'While it runs: if the ledger reads "Apparent regression: confirming", say: the gate '
            "is re-running before it believes a failure. As soon as the version is active, set "
            "the unattended level: Improve > Set the unattended level, or make autonomy "
            'LEVEL=unattended BY="your name".',
            "If it fails: if the gate blocks the candidate, say: the gate refused a version that "
            "did not earn it, which is the point; leave the verdict on screen and go to the "
            "evidence slide. If it stalls, the request reads as running: stop, reset, start: docker compose "
            "stop hill-climbing-runner, then make reset NAME=hill-climbing-loop, then docker "
            "compose start hill-climbing-runner, about 20 seconds in all. Never restart the "
            "runner: a restarted runner keeps serving, so the reset refuses again. The "
            "reset clears the candidate, so the trigger after it is Improve > Run analyzer, then "
            "Run experiment on the candidate; start none after 3:24, and if nothing has landed "
            "by 3:34, go on to slide 62 and return when the gate reads.",
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
            "re-runs; it lands about 3:20 to 3:24. The whole chain from the opener is about 9 to "
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
            "21 seconds. If the last run has not posted by 3:34, go on to slide 62 and return "
            "when it posts.",
            "Backup screenshot: " + EXPECTED + "improve-cleared-unattended-board.png, the posted "
            "answer with Gold check passed, to point at while you reset and run again.",
            "The point to land: Rules were learned from failures, measured on questions no one "
            "tuned on, and trusted only as far as the evidence went.",
            "Example: On 24 October, version 11 passed 13 of 15 holdout questions against 2, and "
            "the revenue question posted 64,015,091.21 dollars at the unattended level.",
            'Ask the room: "Would you have approved this diff without the ledger?" Expect: no; '
            "the rules read well either way.",
            "Misconceptions: That the demo is scripted. Every rule, flip, and level comes from "
            "this run; the counts differ from rehearsal.",
            "Transition: One chain is a story; here is every promotion we measured.",
        ],
    ),
    # 7 evidence --------------------------------------------------------------------------------
    dict(
        kind="evidence",
        title="Nine promoted versions on the same 15 holdout questions",
        minutes=2.5,
        says="Version 1 passed 2 of 15; promoted versions 10 to 14, with 0 regressions",
        src="evidence E42, E43, E45 (docs/calibration-report.md, Model bake-off, Analyzer "
        "comparison, What this session supersedes; docs/evidence/section-4-hill-climbing-loop.md)",
        chart={
            "type": "column",
            "title": "Holdout questions passed by each knowledge version",
            "categories": ["1", "4", "5", "8", "9", "11", "13", "15", "17", "19"],
            "series": [("Holdout questions passed", [2, 12, 10, 14, 14, 13, 14, 13, 12, 13])],
            "x_label": "Knowledge version (1 is the starting version)",
            "y_label": "Passed, of 15",
            "maximum": 16,
        },
        on_slide=[
            "Sample: 15 holdout questions, 3 runs each, pass on 2 of 3; one experiment per bar, "
            "22 to 25 October 2026",
            "- Regressions: 0 for every promoted version",
            "- From 8 on: two candidates plus analyzer fixes",
            "Insight: Single candidates, mostly unpromoted, ranged 2 to 12 of 15; pairs, 12 to 14.",
        ],
        notes=[
            "Purpose: Show the promotions along the whole chain with their sample size, and the "
            "variance that made two candidates necessary.",
            "What to say: Each bar is one experiment on the same 15 holdout questions, each run "
            "three times and passed on two of three. Version 1, the starting knowledge, passed 2 "
            "of 15 in every baseline we measured, more than twenty of them. Every other bar is a "
            "promoted version, and every one had 0 confirmed regressions. The chart shows only "
            "promoted versions; candidates that were not promoted are not bars. Versions 4 and 5 "
            "came from one analyzer run each; version 4 measured 11 and then 12. Single runs were "
            "a lottery: from the same kind of input, one candidate passed 11, 3, or 6 of 15 at "
            "medium reasoning effort, and 2, 9, or 5 at high effort. From version 8 on, the team "
            "writes two candidates and keeps one on development questions alone, and the "
            "analyzer fixes of that session landed at the same time, so which change helped is "
            "unmeasured; the kept candidates passed 12 to 14 of 15. Single runs still vary: for "
            "version 15, candidate A passed 7 of 25 development questions and B 24. The evidence "
            "counts 11 live promotions; the chart draws the 9 versions whose experiments it "
            "lists. Of 15 candidate "
            "experiments recorded, 14 had 0 regressions; one had a regression on one development "
            "question. Fifteen questions is a small sample: version 11 measured 13 and, later "
            "that day, 12.",
            "The point to land: Measure the improver too: one run of it varied from 2 to 12 of 15.",
            "Example: Version 8 fixed 12 of the 13 holdout trap questions; the working-days order "
            "question still failed.",
            'Ask the room: "Why choose between the two candidates on development questions, not '
            'the holdout?" Expect: the holdout would stop measuring unseen questions.',
            "Misconceptions: That 14 of 15 is an accuracy rate. It is one count on 15 questions; "
            "a one-question difference is noise.",
            "Transition: Now the run that changed the gate itself.",
        ],
    ),
    # 8 insight: the naive analyzer story --------------------------------------------------------
    dict(
        kind="insight",
        title="A three-condition gate passed rules copied from the test",
        minutes=2.5,
        says="On 23 October naive rules passed 15 of 15; the gate gained the overfit guard; "
        "blocked 6 of 6 since",
        src="DECISIONS.md, 26 October 2026 item 6; evidence E40, E46 (docs/calibration-report.md, "
        "Resumed after the ledger correction, The naive analyzer)",
        on_slide=[
            "Insight: A holdout that shares its rules with development cannot tell learning from "
            "copying.",
            "Evidence: 23 October: copied rules passed 15 of 15 holdout questions.",
            "- The gate of three conditions said ready",
            "- Not approved; a fourth condition added",
            "- Since: 6 of 6 blocked, at 0 to 2 of 15",
        ],
        notes=[
            "Purpose: Tell the naive analyzer's history in order, and land why the gate checks how "
            "rules were written, not only how they score.",
            "What to say: This is the most surprising result of the course, and the order matters. "
            "On the morning of 23 October the gate had three conditions: more holdout passes, "
            "zero regressions, and human approval. We ran a naive analyzer that wrote one rule per "
            "failed development question, quoting the question with its gold query, with no "
            "critic and no guard. Its version passed 15 of 15 holdout questions and 25 of 25 "
            "development questions, and the gate read ready for human approval. No holdout "
            "question had reached it: the development questions' gold queries carried every "
            "convention the holdout needed, so copying the answer key generalized. It was not "
            "approved, and it was retired. Two changes followed. The naive analyzer now quotes "
            "only the question and the agent's failed query, never a gold query. And the "
            "gate gained a fourth condition, the overfit guard on the new rules, so a version "
            "written without the guard is blocked whatever its holdout count. Since then: blocked "
            "in 6 of 6 runs, but those runs scored 0 to 2 of 15, so the holdout condition alone "
            "would have blocked them: the guard has not yet met a high-scoring copied version "
            "live.",
            "The point to land: A holdout score can pass rules copied from the test; check how "
            "rules were written.",
            "Example: You saw the latest blocked verdict at the start of the section: every rule "
            "named.",
            'Ask the room: "What in your evaluation would notice rules copied from the answers?" '
            "Expect: nothing; scores look great.",
            "Misconceptions: That the holdout split protects you on its own. Leakage through the "
            "development answers passed it 15 of 15.",
            "Transition: A version that passes the gate earns more than a better prompt. It can "
            "earn autonomy.",
        ],
    ),
    # 9 insight: autonomy per metric family ------------------------------------------------------
    dict(
        kind="insight",
        title="Autonomy is earned one metric family at a time",
        minutes=2,
        says="Revenue cleared the unattended level in 7 of 11 promotions; orders never did",
        src="evidence E11, E51 (docs/calibration-report.md, Stability and the holdout, What this "
        "session supersedes); pack.yaml evaluation; the poll on slide 54",
        on_slide=[
            "Insight: Trust is earned per metric family, not per system.",
            "Evidence: Revenue cleared the unattended level in 7 of 11 live promotions; orders "
            "never did.",
            "- Clears: each holdout question passes 2 of 3",
            "- Orders: one question passed 0 of 3, then 0 of 3 more",
            "- Average order value: 1 holdout question, too few to clear",
        ],
        notes=[
            "Purpose: Answer the poll with evidence: autonomy is granted per metric family from "
            "holdout results, and some families never earn it.",
            "What to say: Before the break you voted on the autonomy level you would grant the "
            "revenue digest. Read the result back now. Here is what the evidence said. A "
            "promotion does not switch the whole system to unattended. Each metric family clears "
            "on its own holdout questions: every one passes 2 of 3 runs, and one that falls short "
            "must pass 2 of 3 more. Revenue cleared in 7 of 11 live promotions; under an earlier "
            "rule, all 4 revenue questions in one experiment, it cleared once in 4 measurements. "
            "Orders never cleared: its working-days question passed 0 of 3 runs, then 0 of 3 "
            "more. Now the third bullet. Average order value has 1 holdout question, and one question is "
            "not evidence of anything. The calibration report recommends at least 3 holdout "
            "questions per family; Assignment 4 builds that rule. So the honest answer to the poll is "
            "per family: unattended for revenue when it clears, assisted for orders.",
            "The point to land: Grant autonomy per capability, from that capability's own "
            "held-out evidence.",
            "Example: Holdout questions per family: revenue 4, orders 4, customers 3, products 3, "
            "average order value 1.",
            'Ask the room: "Did the poll\'s majority match what revenue earned?" Expect: most '
            "chose the assisted level, which matches orders, not revenue.",
            "Misconceptions: That one promotion makes the system trustworthy. It clears families, "
            "one at a time, and only on their own questions.",
            "Transition: So what does this mean for your own text-to-SQL design?",
        ],
    ),
    # 10 design callout -------------------------------------------------------------------------
    dict(
        kind="design_callout",
        title="Improve business knowledge from failures, measured by execution",
        minutes=2,
        says="Where learned rules live, and an execution-match benchmark that decides each change",
        src="section-4-hill-climbing-loop/README.md; evidence E11, E12; sources 12, 40, 43, 45",
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
            "every tool reads them; changes are slower, so re-run the benchmark on every change, "
            "as the Databricks build guide says, Source 45. Second, what decides: execution "
            "match. Run your query and the gold query and compare results, never query text, on "
            "two databases: one database passes wrong queries 6.5 percent of the time on "
            "average, Source 12. Products now do parts of this: Snowflake keeps evaluation "
            "queries out of the runtime context and counts regressions, Source 40. What we add "
            "is an improver that never reads the deciding questions, and a regression that "
            "blocks. Our benchmark has 40 questions, 33 with traps; the 15 holdout questions are "
            "never shown to the analyzer team.",
            "The point to land: Keep rules where you can diff and roll them back, and let results "
            "on held-out gold queries decide.",
            "Example: The gold answer to the fiscal year 2025 question, 64,015,091.21 dollars, is "
            "checked on both the warehouse and the second database, seeded differently.",
            'Ask the room: "Where do your metric definitions live today?" Expect: dbt, a wiki, or '
            "old dashboards.",
            "Misconceptions: That comparing SQL text is stricter. It rejects correct queries "
            "written another way.",
            "Transition: Here is what to do with this next week.",
        ],
    ),
    # 11 apply-it checklist ---------------------------------------------------------------------
    dict(
        kind="checklist",
        title="Apply it: a gated improvement loop for your agent",
        minutes=2,
        says="Six steps to build a hill-climbing loop on your own warehouse",
        src="section-4-hill-climbing-loop/demo/walkthrough.md, If you copy this into your "
        "repository; section-4-hill-climbing-loop/assignment/README.md; sources 21, 45",
        on_slide=[
            "- Write gold questions with hand-checked queries",
            "- Split them before you read any failure",
            "- Score by result on two databases",
            "- Set runs per question and re-runs before you compare",
            "- Reject rules that quote a question or gold query",
            "- Promote only on all four: holdout passes, zero regressions, approval, guard",
        ],
        notes=[
            "Purpose: Give six concrete steps a learner can take to build a gated improvement loop "
            "on their own system.",
            "What to say: Six steps, in order. One: write gold questions with hand-checked "
            "queries. Ours are 40; the Databricks build guide, Source 45, suggests starting with "
            "10 to 20, written before development. Two: split them before you read a single "
            "failure, and make the holdout unreadable, in code, to whatever writes rules. Three: "
            "score by result, on two databases, never by query text. Four: set the measurement "
            "before any comparison: runs per question, the pass threshold, and the re-runs that "
            "confirm a regression, the same for both versions, in one session. Five: put a "
            "deterministic guard after any rule writer, human or model. Six: promote only on all "
            "four conditions, more holdout passes, zero confirmed regressions, a person's "
            "approval, and the overfit guard, which runs again at the gate; record every reason. Then test the loop itself: a rule that quotes a question must be "
            "rejected, and a rule that breaks a passing question must be blocked. Assignment 4: "
            "Hill-climbing loop builds parts of this.",
            "The point to land: Split first, measure second, learn third; never in another order.",
            "Example: The over-broad rule from the problem story is the test for step six.",
            'Ask the room: "Which step is missing in your team today?" Expect: the split, most '
            "often.",
            "Misconceptions: That human-written rules can skip the gate. The SEED audit of the "
            "BIRD benchmark, Source 21, found wrong evidence in 105 of its 1,534 development pairs.",
            "Transition: Four ways this goes wrong, each from our runs.",
        ],
    ),
    # 12 pitfalls -------------------------------------------------------------------------------
    dict(
        kind="pitfalls",
        title="Pitfalls of learned knowledge, from our runs",
        minutes=2,
        says="One analyzer run, replaced test questions, a rule with a placeholder, and a holdout read "
        "too often",
        src="evidence E45, E46, E50, E52 (docs/calibration-report.md)",
        on_slide=[
            "| Pitfall | What happened | Do instead |",
            "|---|---|---|",
            "| Trusting one analyzer run | Candidates passed 2 to 12 of 15 | Write two; keep one on "
            "development questions |",
            "| Replacing flaky holdout questions | Instability moved to others | Confirm with "
            "re-runs |",
            "| A rule with a placeholder | Answer 28,474.44 dollars low, labelled verified | "
            "Parse each rule's query on the schema |",
            "| Tuning on holdout results | Analyzer and gate changed after reading them | Refresh "
            "it; keep a final set unread |",
        ],
        notes=[
            "Purpose: Name four mistakes in learned knowledge, each with what it did in this "
            "course's runs, and the fix.",
            "What to say: Four pitfalls, each one we hit. First, trusting one analyzer run: the "
            "same kind of input gave candidates from 2 to 12 of 15; two candidates, landing with "
            "that session's analyzer fixes, gave 12 to 14, and which change helped is unmeasured. Second, fixing noise by "
            "changing the test. Under a promoted version 3 of 15 holdout questions were "
            "unstable; we replaced them, and on the next pass others were unstable instead. The "
            "instability belonged to the version's answers, so we restored the reviewed holdout "
            "and confirm regressions with re-runs instead. Third, a rule with a placeholder: a learned rule "
            "named a placeholder instead of a predicate, and the fiscal year 2025 revenue answer "
            "came out 28,474.44 dollars low, labelled verified. Now every rule's SQL is parsed "
            "against the catalog. Fourth, reading the holdout too often: we changed the analyzer "
            "and the gate after reading its results, so it is less unseen than it was.",
            "The point to land: Noise, prose, and a tired holdout fool a loop as surely as copying "
            "does.",
            "Example: The wrong total, 63,986,616.77 dollars, is exactly what an internal-account "
            "filter that is too broad gives.",
            'Ask the room: "How often does your team read its test set?" Expect: after every '
            "change, which is the point.",
            "Misconceptions: That more repeats fix a small holdout. Repeats reduce noise per "
            "question; only more questions narrow the uncertainty.",
            "Transition: Let me check what stuck.",
        ],
    ),
    # 13 recap and question ---------------------------------------------------------------------
    dict(
        kind="recap",
        title="Recap: the hill-climbing loop",
        minutes=1,
        says="Three points to keep, and one question on the gate's conditions",
        src="section-4-hill-climbing-loop/README.md; evidence E40, E46, E54",
        on_slide=[
            "- Agents propose rules; code and a person decide",
            "- Learn on development questions; decide on the holdout",
            "- Promote only with zero confirmed regressions",
            "Question: A candidate passes 15 of 15 holdout questions with zero regressions, but "
            "its rules quote development questions. Is it promoted?",
        ],
        notes=[
            "Purpose: Consolidate the hill-climbing loop and check the gate's conditions with one "
            "question.",
            "What to say: Three points: agents propose, code and a person decide; learn on "
            "development questions, decide on the holdout; one confirmed regression blocks. Now "
            "the question; thirty seconds. The answer is no: the overfit guard on the new rules "
            "fails, so it is not even ready for approval. That exact case happened on 23 October, "
            "under three conditions, and it is why the fourth exists.",
            "The point to land: Promotion needs all four conditions; a perfect score and zero "
            "regressions satisfy only two.",
            "Example: Version 11 passed 13 of 15 holdout questions against 2, with 0 regressions "
            "and every rule through the guard, and was promoted.",
            "Ask the room: the question on the slide. Expect: no, the overfit guard; some say yes "
            "on the score, which is the trap.",
            "Misconceptions: That human approval would catch it. The rules read like sensible "
            "advice; the guard catches the copying in code.",
            "Transition: That completes the four loops. Next, all four together.",
        ],
    ),
]
