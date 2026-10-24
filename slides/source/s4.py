"""Section 4: Hill-climbing loop. Slides and speaker notes for the rewritten outline (rules and checks in build.py)."""

FAILURE = (
    "Rules learned from the questions they were written for raise that score, break other answers, "
    "and then get trusted to run unattended on too little evidence."
)

DEMOS = [
    "improve-baseline-experiment",
    "improve-naive-analyzer-blocked",
    "improve-analyzer-team-approve",
    "improve-candidate-experiment",
    "improve-cleared-unattended",
]

R = "<!-- refresh after the session: {} -->"
MEASURED = (
    "the baseline experiment shown in 285 and 266 seconds, the starting version at 2 of 15 holdout "
    "passes; the analyzer team shown in 62 and 98 seconds, 7 and 8 rules through the overfit guard; "
    "the candidate experiment not shown, 3 and 6 of 15 against 2 with 0 regressions (the version "
    "promoted on 22 October scored 11 and 12 of 15); cleared for the unattended level not shown, both "
    "attempts posted at the assisted level with a wrong answer after those weak candidates, while on "
    "22 October the spine question by webhook was right at the assisted level. On 23 October the "
    "analyzer team at reasoning effort high gave candidates of 2, 9, and 5 of 15 from the same failed "
    "dev items, so the spread stays; the finale chain on the confirmed standard promoted the best, 10 "
    "of 15 against 2 with 0 regressions, cleared average order value and products but not revenue "
    "(one revenue item fell short twice), and posted the spine question at the assisted level with a "
    "wrong answer, 63,986,616.77 dollars against gold 64,015,091.21, from an internal-account filter "
    "that was too broad; the naive analyzer's first live attempt, before it was made deterministic, "
    "passed 15 of 15 holdout items and the gate did not block it. In the live session of 23 October, "
    "afternoon, with the SQL guidance check and two candidates chosen on the dev split: candidate A "
    "18 of 25 dev with 11 rules, candidate B 19 of 25 with 8 rules, B kept as v8, the guidance check "
    "rejecting none of its rules, in 326 seconds; v8 passed 14 of 15 holdout items against 2, 12 of 13 "
    "trap items fixed, 0 regressions; revenue, average order value, customers, and products cleared, "
    "orders not; the spine question correct, 64,015,091.21 dollars, posted at the unattended level; "
    "and the deterministic naive analyzer blocked twice, 21 rules all flagged, holdout 2 of 15. In "
    "the capture session of 23 October, evening: candidate A 21 of 25 dev with 8 rules, candidate B "
    "10 of 25 with 5 rules, A kept as v9, in 377 seconds; v9 passed 14 of 15 holdout items against 2, "
    "0 regressions, in 186 seconds; the finale held 5 times over 50 seconds while the promotion and "
    "its clearance re-runs finished, then the spine question correct, 64,015,091.21 dollars, posted "
    "at the unattended level with the same four families cleared; and the naive analyzer blocked a "
    "third time, 20 rules all flagged, holdout 2 of 15."
)

NUMBERS = [
    "40 benchmark items, 25 dev and 15 holdout, so 70 runs per experiment: from "
    "`platform/packs/datapilot_us/benchmark/dev.yaml` and `holdout.yaml` with `evaluation.holdout_repeats`.",
    "Holdout questions per metric family (revenue 4, orders 4, customers 3, products 3, average order "
    "value 1): from `platform/packs/datapilot_us/benchmark/holdout.yaml`; calibration replaced 3 "
    "unstable items, then restored the reviewed holdout, so 0 were replaced in the end: "
    "docs/calibration-report.md, Stability and the holdout.",
    "Holdout passes 2 of 15 under the starting version and 12 of 15 under the promoted one; 10 of 13 "
    "holdout trap items flipped; 0 regressions on either split: docs/calibration-report.md, Model "
    "bake-off. On 23 October v5 passed 10 of 15 against 2, 8 fixed, 0 regressions on either split, "
    "dev 15 of 25, in 257.6 seconds: docs/calibration-report.md, Resumed after the ledger correction.",
    "Wall time of one 70-run experiment at concurrency 8: 182 to 459 seconds over every 70-run "
    "experiment, two candidates at reasoning effort high taking 458.9 and 403.8; cost 0.0594 to "
    "0.0914 dollars: docs/calibration-report.md, Wall time.",
    "Analyzer team candidates from the same kind of input: four runs at reasoning effort medium gave "
    "11, 3, and 6 of 15 holdout passes against 2, and 2 for v3 in an earlier session, with the first "
    "candidate re-measured at 12: docs/calibration-report.md, Analyzer comparison; 2, 9, and 5 of 15 "
    "at reasoning effort high from the same failed dev items: docs/calibration-report.md, Resumed "
    "without traces. The response is two candidates chosen on the dev split only, "
    "`analyzer.candidates` 2 in pack.yaml; measured twice, the kept candidate passed 14 of 15 both "
    "times and the step took 326 and 377 seconds: docs/calibration-report.md, Live sessions of 23 "
    "October, afternoon and evening.",
    "A family clears for the unattended level on the gate's confirmed standard: every holdout item "
    "passes 2 of 3 runs, an item that falls short passes 2 of 3 more: `evaluation` in pack.yaml and "
    "docs/calibration-report.md, Stability and the holdout. On 23 October average order value and "
    "products cleared; revenue did not: net-revenue-cyber-monday-2025 failed 3 of 3, then passed 2 "
    "of 3 more, and app-share-net-revenue-fiscal-2026 passed 1 of 3, then 1 of 3 more: "
    "docs/calibration-report.md, Resumed after the ledger correction. In session 4 revenue, average "
    "order value, customers, and products cleared, revenue with no re-run; orders did not: "
    "business-day-orders-november-2025 failed 3 of 3, then 0 of 3 more: docs/calibration-report.md, "
    "Live session of 23 October, afternoon. In the evening the same four families cleared under v9: "
    "docs/calibration-report.md, Live session of 23 October, evening.",
    "The finale of 23 October, morning, posted at the assisted level, labelled verified, "
    "63,986,616.77 dollars against gold 64,015,091.21, 16,291 tokens; that total is exactly the one an "
    "internal-account filter that is too broad gives, `NOT ILIKE '%harborpine%'`, which also removes "
    "the look-alike addresses. The finale of session 4, and again the finale under v9 that evening: "
    "64,015,091.21 dollars, gold passed, posted at the unattended level: docs/calibration-report.md.",
    "The naive analyzer's first live attempt, before it was made deterministic: 21 rules, 15 of 15 "
    "holdout and 25 of 25 dev, the gate ready for human approval; the deterministic naive analyzer, "
    "three times since: 21, 21, and 20 rules, all flagged, holdout 2 of 15, blocked: "
    "docs/calibration-report.md. The gate's four conditions: "
    "`platform/src/datapilot/loop4_hill_climbing/gate.py`.",
    "Experiment runs traced as a sample of about 1 run in 5, demo and check runs in full: "
    "`tracing.experiment_sample_rate` 0.2 in pack.yaml. "
    + R.format("trace sampling seen live after the LangSmith limit resets on 1 November"),
    "Holdout 3 runs and pass on 2; an apparent dev regression re-run 2 more times under each version, "
    "counted when the candidate fails 2 of 2 and the active version passes 2 of 2; concurrency 8; "
    "overfit guard 6 words and 20 SQL tokens: from `evaluation` in "
    "`platform/packs/datapilot_us/pack.yaml`.",
    "Confirming re-run of an apparent holdout regression (3 more runs, 2 of 3 must fail again) and the "
    "calibration stability filter (5 runs per item under each version, kept at 4 or 5 of 5 or 0 or 1 of "
    "5): `evaluation` in pack.yaml.",
    "MAGIC 56.52, 57.76, 59.13 on BIRD dev and 78.62 to 85.66 on Spider dev, when correcting only "
    "queries already known to be wrong; 56.52 to 58.55 on BIRD dev when applied to every query: "
    "Source 18, Tables 1 and 2.",
    "SEED 148 pairs (9.65 percent) without evidence, 105 (6.84 percent) with wrong evidence, CodeS-15B "
    "44.76 to 54.29: Source 20.",
    "6.5 percent mean false positives on one database, 11.0 percent on extra-hard queries, across 21 "
    "systems: Source 8.",
    "10 of 15 gives a 95 percent interval of 0.42 to 0.85; 12 of 15 gives 0.55 to 0.93; 14 of 15 "
    "gives 0.70 to 0.99: Wilson intervals, computed for the course.",
    "Three holdout items flaky at 0.7 per run: about 51 percent chance of a false regression on single "
    "runs, about 43 percent with pass on 2 of 3, about 11 percent with 2 of 3 "
    "plus a confirming 3-run re-run (computed for the course).",
    "Cortex Analyst suggests up to 10 verified queries at a time; Genie's chat-mode benchmarks "
    "compare numbers to 4 significant digits: Sources 22 and 21.",
    "N, the minimum holdout questions per family before the unattended level: 3, the calibration "
    "report's recommendation, built by Assignment 4: Hill-climbing loop, not in class code.",
]

OPEN_Q = (
    '"A family clears for the unattended level on its holdout questions: 4 for revenue, 1 for '
    'average order value. Is that enough evidence?"'
)

SLIDES = [
    # 1 -------------------------------------------------------------------------------------------
    dict(
        kind="agenda",
        title="Agenda (Section 4 highlighted)",
        layout="concept",
        container="numbered rows, fourth row highlighted",
        minutes=0.5,
        says="Section 4: Hill-climbing loop, the loop that improves the other three",
        src="section-4-hill-climbing-loop/README.md",
        on_slide=[
            "Today's agenda",
            "Section 1: Agent loop",
            "Section 2: Verification loop",
            "Section 3: Event loop",
            "Section 4: Hill-climbing loop (now)",
        ],
        notes=[
            "Say: Welcome back. Three loops are now in place. The agent loop answers with good tools and "
            "a checkable envelope. The verification loop stops unsafe and malformed work and hands the "
            "agent reasons it can act on. The event loop runs questions as jobs, holds personal data for "
            "human approval, and stops on the kill switch. What none of them does is get better. The "
            "spine question, net revenue in fiscal year 2025, is still wrong, because the business rules "
            "are still missing. This last section is the loop that learns those rules from failures, "
            "and the hard part is not learning. The hard part is knowing whether what was learned is "
            "true, and how much trust it earns. The baseline experiment you saw start at the poll has "
            "been running through the break; it is the class session's baseline, and we read it first "
            "in the demo.",
            "Point at: the highlighted fourth row, then back at the first three to recall what each loop "
            "already guarantees.",
            'Likely question: "Is the baseline experiment finished?" Answer: It should be; the run board '
            "shows its progress strip. If it is not, we read what is done and let it finish while the "
            "concepts run.",
            "Transition: First, the way most teams improve an agent today, and why it goes wrong.",
        ],
    ),
    # 2 -------------------------------------------------------------------------------------------
    dict(
        kind="story",
        title="Failure story: the prompt full of patches",
        layout="diagram",
        container="step cards: four numbered beats, then the lesson bar",
        minutes=1.5,
        says="Illustrative: a patch per failed question raises the score and breaks other answers",
        src="section-4-hill-climbing-loop/concepts.md",
        on_slide=[
            "Illustrative",
            "1. **Patches**: after the monthly check, one prompt line is pasted per failed question, "
            "including the fiscal year 2025 net revenue answer.",
            "2. **Score**: the same check rises the next day, because it asks the questions the patches "
            "were written for.",
            "3. **New wording**: next month's questions use other phrases, and the fiscal year answers "
            "are wrong again.",
            "4. **Regression**: a discounted-orders question that passed now fails, because one patch "
            "dropped discounts from revenue.",
            "Lesson: a score measured on the questions you tuned on rises by construction.",
        ],
        notes=[
            "Say: This story is illustrative and the person is fictional. Dana, an analytics engineer at "
            "Harbor & Pine, owns the analytics agent. The monthly check shows a set of failed questions, "
            "among them the net revenue for fiscal year 2025. Dana does what most of us have done: one "
            'patch per failure, pasted into the prompt. "Fiscal year 2025 runs February 2024 to January '
            '2025." "For the top customers question, leave out the account ending in harborpine." The '
            "score on the monthly check jumps the next day, because the check asks exactly the questions "
            "the patches name. Then the next month's questions arrive, phrased differently, and they are "
            "still wrong, because the patches named questions, not rules. Worse, a question about "
            "discounted orders that used to pass now fails, because one patch said to drop discounts "
            "from revenue. Nobody can say which patch broke it, because the prompt grew by twenty lines "
            "and was never measured on anything it had not seen.",
            "Point at: the four beats in order, and stop on beat four: a regression nobody saw. Then read "
            "the lesson bar.",
            'Likely question: "Is this not just normal prompt tuning?" Answer: It is, and that is the '
            "problem. It is measured on the same questions it was tuned on, so the score rises by "
            "construction.",
            "Transition: So the tempting rule is simple: if the score goes up, ship it.",
        ],
    ),
    # 3 -------------------------------------------------------------------------------------------
    dict(
        kind="question",
        title="Hill-climbing loop: promote rules when the dev score rises?",
        layout="concept",
        container="question line, key-idea box, three reason cards",
        minutes=2,
        says="KEY IDEA: No. Holdout questions never seen, zero regressions, and human approval decide",
        src="section-4-hill-climbing-loop/README.md",
        on_slide=[
            "If the dev score goes up, should we promote the new rules?",
            "KEY IDEA: No. Promote only on holdout questions the analyzer never saw, with zero "
            "regressions and human approval.",
            "- A dev score measures memory of the questions the rules came from",
            "- The same learned-guideline method gained on one model and dropped on another",
            "- An average can hide one broken answer behind six fixed ones",
        ],
        notes=[
            "Say: No. A score on the questions the rules were written from measures memory, not "
            "generalisation. MAGIC, Source 18: MAGIC: Generating Self-Correction Guideline for "
            "In-Context Text-to-SQL (https://arxiv.org/abs/2406.12692), learns a self-correction "
            "guideline from training failures; in their words, \"MAGIC's guideline outperforms expert "
            "human's created ones.\" Then a later survey re-ran it. Source 19: Toward Real-World Table Agents "
            "(https://arxiv.org/html/2507.10281) found small gains over the baseline, lower scores with "
            "Qwen2.5-Coder-32B on both Spider dev and BIRD dev; in summary, feedback refinement "
            "gained little for weaker models. Same method, different model, different verdict. That is the "
            "second reason on the slide, and the argument for a gate that decides on questions the "
            "learner never saw.",
            "Say: So the verdict has three parts. First, a holdout split the analyzer team never reads. "
            "Second, zero regressions, item by item, on both splits, which is the third reason on the "
            "slide. Third, a person approves the knowledge diff. Each part closes a different hole, and "
            "we take them in order.",
            "Point at: the KEY IDEA box, then the three reasons, top to bottom.",
            'Likely question: "Is a holdout split new?" Answer: No; every machine-learning engineer '
            "uses one. What we have not seen documented is the combination with zero regressions, human "
            "approval, an overfit guard, and autonomy granted per metric family.",
            "Transition: Before any of that, the instrument itself has to be right.",
        ],
    ),
    # 4 -------------------------------------------------------------------------------------------
    dict(
        kind="concept",
        title="1) A benchmark is a measuring instrument",
        layout="table",
        container="two-column cards: how it works | worked example, then the key-idea bar",
        minutes=4,
        says="Key idea: score results, not query text, on data built to expose each trap",
        src="platform/src/datapilot/loop4_hill_climbing/evaluator.py; Source 8",
        on_slide=[
            "Principle: score results, not query text, on data built to expose each trap.",
            "Think of it as checking a kitchen scale with known weights before trusting any recipe.",
            "| How it works | Worked example |",
            "|---|---|",
            "| Run gold and agent SQL live; compare normalized results | A correct query joined in "
            "another order passes; text comparison fails it |",
            "| Seed rows that trigger each trap | Cancelled orders and internal accounts change the "
            "naive net revenue |",
            "| Check a second database | One database alone: 6.5 percent false positives across 21 "
            "systems |",
            "| Split dev and holdout | 25 dev questions to learn from, 15 holdout to decide |",
            "Trade-offs: trap rows and a second database cost seeding work.",
            "At work: score outcomes; build fixtures that separate right from its nearest wrong "
            "neighbour; hold questions back.",
            "Key idea: an eval you cannot trust turns hill-climbing into noise.",
        ],
        notes=[
            "Plain explanation: Before you can improve anything, you need a measurement you trust. A "
            "benchmark is an instrument, and instruments have errors in both directions. It can call a "
            "right answer wrong, and it can call a wrong answer right. Each row on this slide removes one "
            "of those errors. The first two keep you from rejecting good answers and accepting bad ones. "
            "The last two keep the score honest as soon as something starts learning from it.",
            "Concrete example from DataPilot: The benchmark has 40 questions, 25 in the dev split and 15 "
            "in the holdout split, with no ambiguous category. Each has gold SQL written by hand. The "
            "evaluator runs the agent's SQL and the gold SQL live, on two databases, `warehouse` and "
            "`warehouse_alt`, and compares the normalized results with a numeric tolerance. The planted "
            "SQL text evaluator (`BUG_SQL_TEXT_EVAL`) compares query text instead, and marks a correct "
            "query wrong because it joins in a different order. That is the first row of the worked "
            "example. The seeded rows are chosen so every trap changes a naive answer: cancelled orders "
            "exist in the period, internal accounts sit among the top spenders, and evening orders cross "
            "the UTC date.",
            "Analogy: A kitchen scale is checked with known weights, more than one, before anyone trusts "
            "a recipe built on it.",
            "Under the hood: One database is not enough. Measured across 21 Spider submissions, checking "
            "results on the original database alone gave a 6.5 percent mean false-positive rate, and 11.0 "
            "percent on extra-hard queries. Their fix fuzzes about a thousand random databases per schema "
            "and keeps those that tell neighbour queries apart, about 42 per query. Two databases is the "
            "teaching-sized version of that idea. A trap-sensitivity test proves the data does its job: "
            "the naive SQL must give a different answer from the gold SQL, or the item tests nothing. One "
            "experiment is 25 dev runs plus 15 holdout items times 3 runs, so 70 runs.",
            "Source 8: Semantic Evaluation for Text-to-SQL with Distilled Test Suites "
            '(https://arxiv.org/abs/2010.02840): "Our method distills a small test suite of databases '
            'that achieves high code coverage for the gold query".',
            "Transfer: The same instrument applies to any LLM feature you evaluate. Score the outcome "
            "that matters, never the surface text. Build fixtures that separate the right behaviour from "
            "its nearest wrong neighbour. Keep a second fixture set. Hold questions back before anyone "
            "tunes on the rest.",
            "Point at: the how-it-works column top to bottom, then the second-database example, then the "
            "trade-offs line.",
            'Ask: "Why does comparing SQL text fail even when it looks stricter?" Expected: many correct '
            "queries exist for one question, so text match rejects right answers.",
            'Likely question: "Why not just ask a model to judge the answer?" Answer: A judge adds a '
            "second error source with the same blind spots. Execution match is deterministic and "
            "repeatable; keep model judges for text you cannot execute.",
            'Likely question: "Does order matter in the comparison?" Answer: Only when the question '
            "asks for an order; each item says so, and ties are broken deterministically in the gold SQL.",
            'Misconception: "A matching result means the query is right." Correction: It means it is '
            "right on this data. A second database, and rows built for each trap, shrink that gap.",
            "Re-check after live runs: the 25 dev and 15 holdout items and the 70 runs per experiment "
            "against the benchmark files and `evaluation.holdout_repeats`.",
            "Transition: Now something learns from this instrument, and that is where it gets dangerous.",
        ],
    ),
    # 5 -------------------------------------------------------------------------------------------
    dict(
        kind="concept",
        title="2) Rules learned from failures overfit",
        layout="diagram",
        container="step cards: four roles left to right, worked example card, key-idea bar",
        minutes=4,
        says="Key idea: split diagnosis, proposal, and criticism, then guard the rules in code",
        src="platform/src/datapilot/loop4_hill_climbing/analyzer.py; overfit_guard.py; Sources 18-20",
        on_slide=[
            "Principle: a rule written from a failure fits that failure; no agent grades its own rule.",
            "Think of it as code review where authors cannot approve their own change.",
            "How it works:",
            "- Failure analyst: diagnoses each failed dev item, writes no rules",
            "- Rule writer: turns diagnoses into general rules",
            "- Critic: keeps, narrows, or drops each rule; never adds",
            "- Overfit guard, in code: rejects 6 words of a question or 20 tokens of gold SQL",
            'Worked example: kept, "the fiscal year runs February to January, named for its end '
            'year"; rejected, a rule repeating a benchmark question word for word.',
            "Trade-offs: three model calls; a paraphrased rule can pass the guard, so the gate decides.",
            "At work: self-improving prompts and memory need a subtracting critic and a leak check.",
            "Key idea: learning is cheap; trusting what was learned is the work.",
        ],
        notes=[
            "Plain explanation: Learning rules from failures works, and it overfits by default. A model "
            "that sees a failed question and its gold SQL will happily write a rule that names the "
            "question. So the work is split. One agent diagnoses, one proposes, one criticises, and then "
            "deterministic code rejects anything that copied the benchmark. Each step can only narrow "
            "what the previous one produced.",
            "Concrete example from DataPilot: The failure analyst reads each failed dev item and returns "
            "a diagnosis: what went wrong and the likely cause, with no rules. The rule writer turns the "
            'diagnoses into general rules, such as the one on the slide, "the fiscal year runs February '
            'to January and is named for its end year". The critic keeps, narrows, or drops each rule. '
            "In code, a review of a rule the writer never proposed is ignored, so the critic cannot add "
            "one. Then the overfit guard rejects any rule that shares 6 consecutive words with a "
            "benchmark question or 20 consecutive SQL tokens with a gold query, from "
            "`evaluation.overfit_question_words` and `evaluation.overfit_sql_tokens`. The team reads dev "
            "items only; handing it a holdout item raises an error. A rule's SQL guidance must also "
            "run over the real schema: a check parses it against the catalog, and a placeholder or a "
            "column that does not exist goes back to the critic, then is dropped. The naive analyzer "
            "(`BUG_NAIVE_ANALYZER`) makes no model call: it writes one rule per failed dev question, "
            "quoting it word for word, and skips the critic; the guard flags every rule, unapplied.",
            "Analogy: A code review where the author cannot approve their own pull request, and the "
            "linter runs whatever the reviewers think.",
            "Under the hood: The research numbers show both sides. When correcting only the queries "
            "already known to be wrong, MAGIC lifted BIRD dev from 56.52 with no self-correction, to "
            "57.76 with DIN-SQL's human-written guideline, to 59.13 with its learned one, and Spider "
            "dev from 78.62 to 85.66. Applied to every query, with no one saying which are wrong, the "
            "human guideline fell to 55.80 and MAGIC's reached 58.55. The survey re-run found the gains small, and negative on "
            "one model. Knowledge itself is noisy too: SEED audited the human-written evidence in BIRD "
            "dev and found 105 pairs, 6.84 percent, with wrong evidence and 148 with none.",
            "Source 18: MAGIC: Generating Self-Correction Guideline for In-Context Text-to-SQL "
            '(https://arxiv.org/abs/2406.12692): "to iteratively generate and refine a self-correction '
            'guideline tailored to LLM mistakes".',
            "Transfer: Any loop that rewrites its own prompts, tools, or graders needs this shape: "
            "separate roles, a critic that can only subtract, and a deterministic leak check against "
            "your eval set. It applies to prompt optimisers and memory systems alike.",
            "Point at: the four role cards left to right, stop on the critic, then the guard, the only "
            "step that is code, then the worked example.",
            'Ask: "Why can the critic not add rules?" Expected: then it would be proposing and judging '
            "its own work.",
            'Likely question: "Would one stronger model do all three jobs better?" Answer: It might '
            "write better rules, but it would still grade itself. The split is about independence, not "
            "skill.",
            'Likely question: "Can a rule paraphrase a question and slip past the guard?" Answer: Yes, '
            "the trade-offs line says so. The guard catches copying; the holdout gate catches rules that "
            "do not generalise.",
            'Misconception: "Human-written rules are safe." Correction: SEED found wrong evidence in '
            "human-written BIRD rules too, which is why human rules pass the same gate.",
            "Re-check after live runs: the guard thresholds of 6 words and 20 SQL tokens against "
            "`evaluation` in the pack.",
            "Transition: The guard only removes obvious copying. The real decision is a measurement.",
        ],
    ),
    # 6 -------------------------------------------------------------------------------------------
    dict(
        kind="concept",
        title="3) The gate is a paired comparison",
        layout="table",
        container="two-column cards: how it works | worked example, then the key-idea bar",
        minutes=4,
        says="Key idea: compare item by item on the same holdout; a confirmed regression blocks",
        src="platform/src/datapilot/loop4_hill_climbing/gate.py; measurement.py; pack.yaml evaluation",
        on_slide=[
            "Principle: compare item by item, measured the same way in one session; a confirmed "
            "regression blocks.",
            "Think of it as a trial that measures each patient before and after, not two crowds.",
            "| How it works | Worked example |",
            "|---|---|",
            "| Holdout items: 3 runs per version, pass on 2 | 15 holdout items, 45 runs per version |",
            "| An apparent regression is re-run | Holdout: 3 more runs; dev: 2 per version |",
            "| Promote: more holdout passes, zero regressions, guarded rules, approval | The over-broad "
            "discount rule is blocked |",
            "| Both experiments in one live session | The baseline started at the poll |",
            "Trade-offs: three items flaky at 0.7 still give about an 11 percent false-regression "
            "chance; 15 items cannot detect small gains.",
            "At work: pre-register the measurement, run both arms together, block confirmed "
            "regressions.",
            "Key idea: an average can hide a broken answer; a paired check names it.",
        ],
        notes=[
            "Plain explanation: The gate does not ask whether the candidate's total is higher. It asks, "
            "item by item, whether anything that passed under the active version now fails. That is a "
            "paired comparison: the same questions, the same measurement, two versions. An aggregate can "
            "hide a trade, six items fixed and one broken. A paired check shows the broken one by name.",
            "Concrete example from DataPilot: The candidate passes the gate when its holdout passes exceed "
            "the active version's, regressions are zero on both splits, every rule it adds passes the "
            "overfit guard, and a person approves the knowledge diff. Each holdout item runs 3 times per "
            "version and passes on 2 of 3, from `evaluation.holdout_repeats` and "
            "`evaluation.holdout_pass_threshold`. An apparent holdout regression counts only if 2 of 3 "
            "more candidate runs fail. An apparent dev regression, from single runs, counts only if the "
            "candidate fails 2 more runs and the active version passes 2 more. The ledger shows the step "
            'as "Apparent regression: confirming". '
            "Runs go 8 at a time. The gate refuses to compare experiments from different live sessions, "
            'which is why the baseline is the one started at the poll. The over-broad version, "exclude '
            'discounted orders from revenue", fixes some items, breaks others, and is blocked.',
            "Analogy: A drug trial that measures each patient before and after, instead of comparing two "
            "crowds.",
            "Under the hood: Take three holdout items that are flaky, passing 7 runs in 10 under both "
            "versions. With single runs, at least one shows a false regression with about 51 percent "
            "chance. Passing on 2 of 3 lowers that only to about 43 percent. Adding the confirming 3-run "
            "re-run brings it to about 11 percent. Calibration ran each holdout item 5 times per "
            "version: all stable under the starting version, 3 unstable under the promoted one. Their "
            "replacements were unstable on the next pass too, so the instability belonged to the "
            "version's answers, and the reviewed holdout was restored. Measured: 2 of 15 holdout passes "
            "before, 14 of 15 after in the two latest runs, 0 regressions. A 70-run experiment took 182 to "
            "459 seconds. Fifteen items are still a small sample: 14 of 15 has a 95 percent interval "
            "of 0.70 to 0.99.",
            "Source 1: The art of loop engineering (https://www.langchain.com/blog/the-art-of-loop-"
            'engineering): "The fourth (and arguably most important) automates improvement!" Ours climbs on benchmark '
            "failures behind this gate rather than on production traces.",
            "Transfer: Use the same gate for any change to a model-backed system: a new prompt, a new "
            "model id, a new retriever. Pre-register how you measure, run both arms in one session, "
            "compare per item, confirm any regression before you believe it, and block on a confirmed one "
            "before you look at the average.",
            "Point at: the two-column card row by row, stop on the confirming-runs row, then the "
            "trade-offs line with its 11 percent.",
            'Ask: "Why must both experiments come from one session?" Expected: the model, data, and '
            "settings must match, or the comparison measures drift instead of the rules.",
            'Likely question: "Is zero regressions too strict?" Answer: On 40 items it can still block a '
            "good version, even with confirming runs; we accept that and say it. At scale you set a "
            "tolerance with a statistical test instead.",
            'Likely question: "Why not run every item ten times?" Answer: Cost and wall time. Each '
            "repeat multiplies the 70 runs; confirming only apparent regressions spends runs where they "
            "matter.",
            'Misconception: "Majority voting on three runs removes flakiness." Correction: It barely '
            "moves the false-regression chance; the confirming re-run and the calibration filter do the "
            "real work.",
            "Re-check after live runs: the settings against `evaluation` in the pack; 2 and 14 of 15, "
            "182 to 459 seconds, and 0 items replaced against the calibration report. The 51, 43, and "
            "11 percent figures assume three items flaky at 0.7.",
            "Transition: A promotion buys more than a better prompt. It buys autonomy.",
        ],
    ),
    # 7 -------------------------------------------------------------------------------------------
    dict(
        kind="concept",
        title="4) Autonomy is earned per metric family",
        layout="table",
        container="two columns: how it works points | holdout questions per family table, key-idea bar",
        minutes=3.5,
        says="Key idea: grant the unattended level per family, from that family's holdout evidence",
        src="platform/packs/datapilot_us/benchmark/holdout.yaml; pack.yaml autonomy; Source 17",
        on_slide=[
            "Principle: grant the unattended level per metric family, from that family's holdout "
            "evidence.",
            "Think of it as merge rights per service, earned with reviews on that service.",
            "How it works:",
            "- Every family starts at the report-only level",
            "- After promotion, a family clears when every holdout item passes 2 of 3 runs, "
            "confirmed by 3 more if short",
            "- Three consecutive escalations or the kill switch demote again",
            "| Family | Holdout questions |",
            "|---|---|",
            "| Revenue, orders | 4 each |",
            "| Customers, products | 3 each |",
            "| Average order value | 1 |",
            "Worked example: once revenue clears, fiscal year 2025 net revenue posts without approval; "
            "average order value, on 1 question, should not.",
            "Trade-offs: small families rest on few questions; the minimum of 3 is Assignment 4.",
            "At work: write the minimum evidence per capability before granting it.",
            "Key idea: autonomy follows evidence, one family at a time.",
        ],
        notes=[
            "Plain explanation: Autonomy is not one switch for the whole system. A version that answers "
            "revenue questions well tells you nothing about product questions. So the unattended level "
            "is granted per metric family, only after a gated promotion, and only from that family's "
            "holdout results. Everything else stays at the level the event loop set.",
            "Concrete example from DataPilot: The class starts at the report-only level. At each "
            "promotion a family clears on the gate's own confirmed standard: every holdout item of the "
            "family passes at least 2 of 3 runs, and an item that falls short gets 3 more runs and "
            "counts if it passes 2 of them. Then the spine question arrives as a webhook and posts at "
            "the level its family earned: without approval if revenue cleared, at the assisted level "
            "if not. Calibration is why: under the earlier rule, all 4 revenue items had to pass in one "
            "experiment, which happened in one measurement of four. Measured three times on the confirmed "
            "standard: under v5 revenue did not clear, one item passing 1 of 3, then 1 of 3 more; under "
            "v8 and v9 it did. The "
            "families come from `autonomy.metric_families` in the pack: revenue, orders, average order "
            "value, customers, and products. Revenue, where net revenue lives, has 4 holdout questions; "
            "average order value has 1. Three consecutive escalations demote a family again, from "
            "`autonomy.demote_after_consecutive_escalations`, and the kill switch drops everything to "
            "the report-only level.",
            "Analogy: A new engineer earns merge rights per service, after reviews on that service, not "
            "for the whole monorepo at once.",
            "Under the hood: The three levels and the kill switch that drops the system to the "
            "report-only level come from Cobus Greyling's loop engineering patterns. What is distinctive here is the coupling: the "
            "unattended level is tied to eval results per family. The small-sample caveat from the last "
            "slide applies with force here. One holdout question for average order value is not "
            "evidence of anything, and the class code would still let that family through if it were "
            "promoted. The calibration report recommends N = 3: a family needs at least three holdout "
            "questions before the unattended level, which keeps average order value at the assisted "
            "level. That rule is not in class code; Assignment 4: Hill-climbing loop builds it.",
            "Source 17: Loop engineering (https://cobusgreyling.github.io/loop-engineering/), in summary: "
            "three autonomy levels, report-only, assisted, and unattended, and a kill switch that drops "
            "the system to report-only.",
            "Transfer: Grant agent permissions per capability from per-capability evidence. A coding "
            "agent can merge documentation fixes unattended long before it may touch billing code. "
            "Write down the minimum evidence per capability before you need it.",
            "Point at: the three how-it-works points, then the revenue row, then the last row with its "
            "single question, then the worked example.",
            'Ask: "Would you clear average order value on one passing holdout question?" Expected: no; '
            "one item is a coin flip, not evidence.",
            'Likely question: "Who can raise the level?" Answer: Only a gated promotion with human '
            "approval; nothing raises it automatically.",
            'Likely question: "What lowers it again?" Answer: Three consecutive escalations in the '
            "family, a holdout regression, an exhausted budget, or the kill switch.",
            'Misconception: "A promoted version is trusted everywhere." Correction: It is trusted for '
            "the families its holdout evidence covers, and nowhere else.",
            "Re-check after live runs: the holdout counts per family, 4, 4, 3, 3, and 1, against the "
            "benchmark files, and N = 3 against the calibration report.",
            "Say: End the promotion discussion with the open question, and leave it open: "
            + OPEN_Q,
            "Measured: revenue cleared on the confirmed standard in 2 of 6 live promotions, the two "
            "latest, under v8 and v9.",
            "Transition: Assignment 4 turns one answer into a rule. First, the four moves together.",
        ],
    ),
    # 8 -------------------------------------------------------------------------------------------
    dict(
        kind="cheat",
        title="Cheat sheet: the hill-climbing loop in four moves",
        layout="table",
        container="table: move, principle, anti-pattern, check question",
        minutes=0.5,
        says="Score by execution, split the learning, gate per item, earn autonomy per family",
        src="section-4-hill-climbing-loop/README.md",
        on_slide=[
            "| Move | Principle | Anti-pattern it prevents | Check question |",
            "|---|---|---|---|",
            "| Measure | Results on two databases, not text | Text match, lucky passes | Would a correct "
            "query written differently pass? |",
            "| Learn | Diagnose, propose, criticise; guard in code | Rules that quote the test | Can "
            "whatever writes a rule also approve it? |",
            "| Gate | Paired, per item, one session | Shipping on a higher average | Which questions does "
            "your gate never learn from? |",
            "| Trust | Unattended per family, from holdout | One switch for everything | How many held-out "
            "questions back each permission? |",
        ],
        notes=[
            "Say: Four moves. Measure with an instrument you trust. Learn with roles that cannot grade "
            "themselves. Gate with a paired comparison on questions the learner never saw. Trust per "
            "family, from evidence. The last column is the question to ask of your own system on Monday. "
            "Each move has a planted failure you are about to see blocked live.",
            "Point at: the gate row, the one that decides, then its check question.",
            'Likely question: "Where does human approval sit?" Answer: At the gate, on the knowledge '
            "diff, after the measurement says the candidate is ready.",
            'Likely question: "Which move would you build first at work?" Answer: Measure. Without a '
            "trusted instrument the other three are guesses.",
            "Transition: Now live; the baseline is waiting.",
        ],
    ),
    # 9 -------------------------------------------------------------------------------------------
    dict(
        kind="demo",
        title="Section 4: Hill-climbing loop - Implementation Notes: The candidate experiment",
        layout="demo",
        container="demo badge and title only",
        minutes=20,
        says="Badge DEMO - 4 and title only; the demos and the code walkthrough are in the notes",
        src="section-4-hill-climbing-loop/demo/walkthrough.md; platform/demos/registry.yaml",
        on_slide=["Badge: DEMO - 4", "Title only; no screenshot"],
        notes=[
            "Run sheet: five core demos in about 15 minutes, then the code walkthrough in about 5. The "
            "baseline experiment was started at 2:50, during the poll, so it is read, not started. Keep "
            "the Improve page shared full screen. Optional, cut first: the over-broad rule, blocked. "
            "Calibration ran each core demo twice with a reset between; the measured results are under "
            "each demo. This chain is the one whose result varies most: say so before it starts. "
            "Experiment runs are traced as a sample, about 1 run in 5, so a ledger row without a "
            'traced run reads "Not traced" and is scored all the same; every demo run outside an '
            "experiment, the finale included, is traced in full.",
            "Demo: the baseline experiment.",
            "Starting state: the experiment started at the poll on the active knowledge version, in the "
            "class session. The baseline is safe across a reset: `make reset NAME=hill-climbing-loop` "
            "keeps the current session's baseline experiment and prints what it kept with its start "
            "time. Only the separate, clearly named full reset discards it, and that is never used in "
            "class. Reset first only if it never started: `make reset NAME=hill-climbing-loop`.",
            'Do: on the run board, open the grouped benchmark progress strip, for example "Baseline '
            'benchmark: 41 of 70 runs done", and expand it into the holdout ledger. If it never '
            "started: Improve > Run experiment on the active version, or "
            "`make demo NAME=improve-baseline-experiment`.",
            "Narrate: This is the instrument from concept 1, A benchmark is a measuring instrument. "
            "Results are scored locally, on two databases. The trap items fail because the starting "
            "knowledge version is nearly empty. This run is the class session's baseline; the console "
            "accepts no baseline from an earlier session.",
            "Point at, in order: the progress strip, the holdout ledger rows, the failed trap items with "
            "their trap labels, and last the live stamp: the run's start time in your local time and its "
            'trace link, or "Not traced" where the sample left the row out.',
            "Expected live result: a holdout pass count for the starting version with the trap items "
            "failed. Measured: 2 of 15 holdout passes, 0 of 13 holdout trap items, in 285 and 266 "
            "seconds for 70 runs; that is past the registry's 3-minute target, which is why it runs "
            "through the poll and the break. One experiment cost 0.0594 to 0.0914 dollars where recorded.",
            "May vary: which non-trap items pass, and the wall time. If it does, say: the trap items are "
            "the ones that must fail, and they are guaranteed by the planted traps; the others vary run "
            "to run, which is why holdout items run three times and calibration removes unstable ones.",
            "If it stalls: reset and run it again, `make reset NAME=hill-climbing-loop`, then the same "
            "trigger. Read the reset output aloud: it names the baseline it kept and its start time.",
            "Demo: the naive analyzer, blocked.",
            "Starting state: it ran at the break and its verdict is on the Improve page. During the "
            "Section 3 questions `BUG_NAIVE_ANALYZER=1` was set in `.env` with `make up`; at the start "
            "of the break it was queued behind the baseline; once its gate read blocked, the flag was "
            "set back to 0 with `make up`, with the runner idle.",
            "Do: at the break, `make demo NAME=improve-naive-analyzer-blocked`, which queues the "
            "analyzer and then its candidate experiment, or Improve > Run analyzer, then Improve > Run "
            "experiment on the candidate; the runner takes them in that order. Here, read the result. "
            "Each attempt is the analyzer and a 70-run candidate experiment, 211 to 285 seconds "
            "from the trigger to the verdict in three measured runs, which is why it runs at the break.",
            "Narrate: This is concept 2, Rules learned from failures overfit, without its defences. The "
            "naive analyzer makes no model call: it writes one rule per failed dev question, quoting the "
            "question word for word with the query that failed, and skips the critic. The overfit guard "
            "flags every rule, but its verdict is not applied, so the knowledge diff keeps them all.",
            "Point at, in order: a rule that quotes a benchmark question; the guard's flag on every rule; "
            "after the candidate experiment, the gate verdict blocked, naming the rules the overfit guard "
            "rejects; and last the live stamp.",
            "Expected live result: the overfit guard flags every rule, and the gate verdict reads "
            "blocked, naming those rules, whatever the holdout count.",
            "May vary: how many dev items failed, the dev count, and the holdout count. If the holdout "
            "count rises, say: a higher score does not license rules that copy the test, and the gate's "
            "fourth condition blocks them anyway. Measured three times as it is now: 21, 21, and 20 rules, "
            "all flagged by the guard, dev 5, 6, and 4 of 25, holdout 2 of 15, and the gate blocked on "
            "both counts, in 211 to 285 seconds. Once before it was made deterministic, it read the reference queries, its 21 "
            "rules passed 15 of 15 holdout items, and the gate of three conditions let it through. That "
            "run is why the fourth exists.",
            "If it stalls: reset and run it again, `make reset NAME=hill-climbing-loop`, then the same "
            "trigger.",
            "Demo: the analyzer team and approval.",
            "Starting state: the naive analyzer's candidate is discarded. Reset first: "
            "`make reset NAME=hill-climbing-loop`; the baseline stays.",
            "Do: Improve > Run analyzer, or `make demo NAME=improve-analyzer-team-approve`, then at once "
            "Improve > Run experiment on the candidate: the runner starts it as soon as the team's "
            "candidate is written. The team took 326 and 377 seconds measured with two candidates.",
            "Narrate: Concept 2 with its defences. The failure analyst diagnoses, the rule writer "
            "proposes, the critic keeps, narrows, or drops, a rule whose SQL guidance does not run over "
            "the schema is dropped, and the overfit guard rejects any rule that quotes a question or "
            "copies gold SQL and passes the rest; live, it once rejected a rule the critic kept for "
            "copying 20 or more tokens of a gold query. The team writes two "
            "candidates this way; each runs on the dev split only, and the one kept has fewer dev "
            "regressions, then more dev passes, then fewer rules. The holdout never takes part in the "
            "choice.",
            "Point at, in order: one diagnosis with no rule in it, one proposed rule, the critic's "
            "decision and reason, the guard result, the line naming both candidates and the one kept, "
            "the knowledge diff waiting for human approval, and last the live stamp.",
            "Expected live result: a candidate version with general rules in the diff viewer, not yet "
            "approved, and the line naming both candidates and the one kept. Measured with two "
            "candidates, twice: 326 seconds, candidate A 18 of 25 dev with 11 rules, candidate B 19 of 25 "
            "with 8 rules, B kept; then 377 seconds, A 21 of 25 with 8 rules, B 10 of 25 with 5, A kept; "
            "the SQL guidance check rejected none of the kept rules either time. With one "
            "candidate it took 62 and 98 seconds, and 7 and 8 rules passed the overfit guard.",
            "May vary: the rule wording, the number of rules, and which candidate is kept. If it does, "
            "say: a different wording is fine; what matters is that no rule names a benchmark question.",
            "If it stalls: reset and run it again, `make reset NAME=hill-climbing-loop`, then the same "
            "trigger.",
            "Demo: the candidate experiment.",
            "Starting state: the candidate version from the analyzer team, in the same session as the "
            "baseline. Reset first: `make reset NAME=hill-climbing-loop` only if the candidate is "
            "missing; the baseline stays.",
            "Do: nothing to start: it was queued at once after the analyzer. Only if it never started, "
            "Improve > Run experiment on the candidate, or `make demo NAME=improve-candidate-experiment`; "
            "a second press queues a second 70-run experiment. When the gate reads ready for human "
            "approval, click Approve on the knowledge diff.",
            "Narrate: Concept 3, The gate is a paired comparison. Same items, same measurement, same "
            "session. Holdout items run three times and pass on two; an apparent holdout regression is "
            "confirmed by three more runs, and an apparent dev regression by two more runs of each "
            "version, before it counts.",
            "Point at, in order: the live holdout ledger with the flips marked against this session's "
            "baseline, the regression column at zero on both splits, the gate reasons, the verdict after "
            "approval, then the LangSmith trace list of `datapilot-experiments` filtered by knowledge "
            "version to show the candidate's traced runs, a sample of about 1 run in 5, tagged by split, "
            "item, and repetition, and last the live stamp.",
            R.format(
                "the sampled trace list seen live after the LangSmith limit resets on 1 November"
            ),
            "Expected live result: holdout flips marked against this session's baseline, no regressions, "
            "and the gate verdict passed once approved. Measured: the two latest candidates, each kept "
            "from two, v8 and then v9, each scored 14 of 15 against 2, fixing 12 of 13 holdout trap items "
            "with 0 regressions, in 211 and 186 seconds from the trigger; the version promoted on 22 October scored 12 "
            "of 15. A 70-run experiment took 182 to 459 seconds; two, at reasoning effort high, ran past the 5-minute budget. The same input also gave candidates of 3, 6, and 11 of 15, and at "
            "reasoning effort high 2, 9, and 5 of 15, so higher effort did not narrow the spread; the "
            "best of those three passed 10 of 15 against 2 with 0 regressions when it was measured "
            "again for the finale. That spread is why the team writes two candidates and keeps the "
            "better on dev. A weak candidate is still possible. If the gate blocks it for too few "
            "holdout passes, say: the gate is refusing a version that did not earn it, which is the "
            "point.",
            'May vary: which items flip and the wall time. If the ledger shows "Apparent regression: '
            'confirming", say: this is concept 3 at work; wait for the re-runs. If the regression is '
            "confirmed, say: the gate is doing its job; read the item, and the version stays blocked.",
            "If it stalls: reset and run it again, `make reset NAME=hill-climbing-loop`, then the same "
            "trigger.",
            "Demo: cleared for the unattended level.",
            "Starting state: the candidate is promoted and active: after approval, as soon as the "
            "Improve page says the version is the active version, set the unattended level, Improve "
            '> Set the unattended level, or `make autonomy LEVEL=unattended BY="<your name>"` (every '
            "reset sets the report-only level). Then wait until the note above "
            "the Events buttons goes away, when the clearance re-runs finish (50 seconds, measured "
            "once). The status line then names the families cleared, or reads Not cleared for every "
            "family when none cleared, and the finale posts at the assisted level. Send webhook "
            "question sends the spine question from the promotion on. The kill switch is released. "
            "No reset.",
            "Do: Events > Send webhook question, or `make demo NAME=improve-cleared-unattended`. "
            "Both refuse, saying which step is missing, while the promotion is pending or its "
            "re-runs still run, the kill switch is engaged, or the level is lower.",
            "Narrate: Concept 4, Autonomy is earned per metric family. The spine question, net revenue in "
            "fiscal year 2025, arrives as a webhook under the promoted version. The moment is the "
            "correct answer, posted at the level its family has earned: without approval when revenue "
            "cleared on the gate's confirmed standard, every revenue holdout item at 2 of 3 runs or 2 "
            "of 3 more, and at the assisted level when it fell short.",
            "Point at, in order: the correct answer against gold, 64,015,091.21 dollars, on the "
            "finale's strip, which shows the gold check once the runner writes it; the post and "
            "its level; the status line naming the families cleared, with any clearance re-runs beside "
            "their items in the candidate experiment; and last the live stamp.",
            "Expected live result: a correct answer, posted at the unattended level if revenue cleared "
            "and at the assisted level if it did not.",
            "May vary: the wording, the latency, and the level; the answer is correct either way. If it "
            "posts at the assisted level, say: the gate held back autonomy the evidence did not earn. "
            "Measured three times on the confirmed standard. First, under v5, revenue did not clear, and "
            "the answer was "
            "wrong, 63,986,616.77 dollars against gold 64,015,091.21: its internal-account filter was too "
            "broad and also removed the look-alike addresses, because no rule stated the email-domain "
            "predicate. The analyzer now drops a rule whose SQL guidance does not run over the schema. "
            "Then, under v8 and again under v9, revenue cleared and the answer, 64,015,091.21 dollars, "
            "posted at the unattended level.",
            "If the answer is wrong in class: use the class-day safeguard, live, from the instructor "
            'guide: `make safeguard-activate BY="<your name>"`, which makes the version verified in '
            "rehearsal active and records it, then send the finale again. Say: the gate's record of the "
            "class candidate stays as it is, and nothing is hidden.",
            "If it stalls: reset and run it again, `make reset NAME=hill-climbing-loop`, then the same "
            "trigger.",
            "Say: Then ask the open question and leave it open: " + OPEN_Q,
            "Optional, cut first, and only after a candidate has been promoted: the over-broad rule, "
            "blocked: Improve > Add the over-broad rule to the active version, or "
            '`make demo NAME=improve-overbroad-rule-blocked`. The rule "exclude discounted orders from '
            'revenue" breaks revenue items that pass under the active version, and the gate blocks it '
            "for regressions.",
            "Code walkthrough: about 5 minutes, in the order of the section's demo walkthrough page.",
            "Open `platform/src/datapilot/loop4_hill_climbing/experiment.py`, lines 192-194: implements "
            "concept 1, A benchmark is a measuring instrument, behind both experiments. Say: each "
            "item's runs go one after another; `scheme.repeats` gives a holdout item 3 runs and a dev "
            "item one, from the pack; a holdout item passes on 2 of its 3, and the same scheme applies "
            "to both versions.",
            "Open `platform/src/datapilot/loop4_hill_climbing/analyzer.py`, lines 206-210: implements "
            "concept 2, Rules learned from failures overfit, the naive analyzer demo. Say: a holdout item "
            "in the input stops the analyzer team, so the holdout stays unseen in code, not by "
            "convention; with `BUG_NAIVE_ANALYZER` on, `naive_rules` makes no model call and writes one "
            "rule per failed dev question, and the guard's verdict is not applied.",
            "Open the same file, lines 242-245: the analyzer team demo. Say: the critic can only keep, "
            "narrow, or drop a proposed rule; a rule whose SQL guidance does not parse against the "
            "catalog is dropped, such as a placeholder or a column that does not exist; the overfit "
            "guard is deterministic and runs last, 6 question words or 20 SQL tokens. Two candidates "
            "are written this way, and `choose` in `candidates.py` keeps one on the dev split.",
            "Open `platform/src/datapilot/loop4_hill_climbing/gate.py`, lines 117-135: implements concept "
            "3, The gate is a paired comparison. Say: both experiments must come from the same live "
            "session; four conditions, all recorded: more holdout passes, zero confirmed regressions on "
            "either split, a person's approval, and every new rule passing the overfit guard; the "
            "over-broad rule fails `clean`, the naive analyzer's version fails `overfit_flags` whatever "
            "its holdout count.",
            "Open `platform/src/datapilot/loop4_hill_climbing/eligibility.py`, lines 72-80: the gate "
            "behind concept 4, the finale. Say: a family clears on the confirmed standard; an item that "
            "fell short is re-run 3 more times and must pass 2, and a family stops at its first item "
            "that falls short twice.",
            "Transition: Questions, starting from the open question.",
        ],
    ),
    # 10 ------------------------------------------------------------------------------------------
    dict(
        kind="questions",
        title="Questions",
        layout="concept",
        container="fixed question slide",
        minutes=3,
        says="Fixed question slide; open question: is N holdout questions enough evidence",
        src="-",
        on_slide=[
            "No Question Is Too Small Every Question Deserves an Answer!!",
            "Are four holdout questions enough? What would your gate require?",
        ],
        notes=[
            "Say: Start from the open question: "
            + OPEN_Q
            + " Take two or three answers. Then point to "
            "Assignment 4: Hill-climbing loop, which builds the rule that a metric family needs at least "
            "three holdout questions before the unattended level, and adds a repeat-customer family with "
            "its own questions. The calibration report recommends that minimum, N = 3.",
            "Point at: the fixed question slide.",
            'Likely question: "What if the gate blocks a good version by noise?" Answer: It can. Holdout '
            "items run three times and pass on two, every apparent regression is confirmed by more runs, "
            "three on the holdout and two of each version on dev, and calibration checks every item for "
            "stability; for three items flaky at 0.7 that leaves about "
            "an 11 percent false-regression chance. Beyond that, a larger holdout or a statistical test "
            "is the fix.",
            'Likely question: "Could the analyzer team learn from production traces instead?" Answer: '
            "Yes, that is LangChain's version of this loop. The gate stays the same: whatever it learns "
            "from, it is promoted only on questions it never saw.",
            'Likely question: "How often would you re-run the gate?" Answer: On every candidate, and '
            "again for the active version whenever the model or the data changes.",
            "Transition: If time is short, skip the reference slides and go to the wrap-up.",
        ],
    ),
    # 11 ------------------------------------------------------------------------------------------
    dict(
        kind="reference",
        title="Reference: skip if short on time - gate statistics",
        layout="table",
        container="two tables side by side: intervals | false-regression schemes, read-me line",
        minutes=1,
        says="How small holdouts behave: intervals, flaky items, three schemes, and the stability filter",
        src="computed for the course; pack.yaml evaluation",
        on_slide=[
            "| Holdout passes | 95 percent interval |",
            "|---|---|",
            "| 10 of 15 | 0.42 to 0.85 |",
            "| 12 of 15 | 0.55 to 0.93 |",
            "Three items flaky at 0.7 per run:",
            "| Scheme | False-regression chance |",
            "|---|---|",
            "| Single run | about 51 percent |",
            "| Pass on 2 of 3 | about 43 percent |",
            "| 2 of 3, then a confirming 3-run re-run | about 11 percent |",
            "| Plus the stability filter | run in calibration; 0 replaced in the end |",
            "Production gate: hundreds of items, or McNemar's paired test.",
            "How to read this: overlapping intervals mean 15 items cannot rank close versions; the "
            "second table shows why regressions are confirmed and unstable items removed.",
        ],
        notes=[
            "Plain explanation: This slide is the honest arithmetic behind the gate. A holdout of 15 "
            "items can tell a large improvement from none, but not a small one, and flaky items create "
            "false regressions far more often than intuition suggests. Three defences stack: majority "
            "voting, a confirming re-run, and removing unstable items before class.",
            "Concrete example from DataPilot: The holdout has 15 items. If the active version passes 10 "
            "and the candidate 12, the two intervals overlap almost entirely; the gate still promotes, "
            "because its rule is paired and per item, not a claim that the candidate is better in "
            'general. When an item that passed now fails, the ledger shows "Apparent regression: '
            'confirming" before it decides: 3 more runs on the holdout, 2 more of each version on dev.',
            "Analogy: Two coins that each landed heads 10 and 12 times out of 15 are not proven to be "
            "different coins.",
            "Under the hood: The intervals are 95 percent Wilson intervals: 0.42 to 0.85 for 10 of 15, and "
            "0.55 to 0.93 for 12 of 15. For flaky items, assume a 0.7 per-run pass rate under both "
            "versions. On single runs, at least one of three such items shows a false regression with "
            "about 51 percent chance. Pass on 2 of 3 barely helps, about 43 percent, because a flaky item "
            "still flips between versions. Requiring a confirming 3-run re-run, where 2 of 3 must fail "
            "again, brings it to about 11 percent. The stability filter attacks the cause: in calibration "
            "each holdout item runs 5 times under the starting and the promoted version and is kept only "
            "at 4 or 5 of 5, or 0 or 1 of 5, under each. In calibration every item was stable under the "
            "starting version and 3 were unstable under the promoted one; their same-family replacements "
            "were unstable on the next pass too, so the instability followed the version's answers, not "
            "the items, and the reviewed holdout of 15 was restored. A production gate uses "
            "hundreds of items or McNemar's paired test, which counts only the items that changed.",
            "Source 8: Semantic Evaluation for Text-to-SQL with Distilled Test Suites "
            '(https://arxiv.org/abs/2010.02840): "the current Spider metric leads to a 2.5% false '
            'negative rate on average"; measurement error exists before any model noise.',
            "Transfer: Before trusting any small eval, compute its interval and its false-alarm rate for "
            "your flake rate. Then confirm alarms before acting on them, and remove the flaky cases.",
            "Point at: the second table, row by row from 51 down to 11 percent, then the filter row.",
            'Ask: "What does McNemar\'s test look at?" Expected: only the discordant items, the ones that '
            "passed in one arm and failed in the other.",
            'Likely question: "Why not raise the threshold to 3 of 3?" Answer: Then a flaky item almost '
            "never passes under either version, and the holdout shrinks in effect.",
            'Likely question: "Where do the percentages come from?" Answer: all three are computed '
            "for the course, the same arithmetic for single runs and for the two stricter schemes.",
            'Misconception: "More repeats fix small samples." Correction: Repeats and confirming runs '
            "reduce per-item noise; only more items narrow the interval.",
            "Re-check after live runs: the holdout size and the repeat settings against the benchmark "
            "and the pack; 0 items replaced against the calibration report. The 43 and 11 percent "
            "figures are calculations on the stated assumptions.",
            "Transition: Next, what others have built.",
        ],
    ),
    # 12 ------------------------------------------------------------------------------------------
    dict(
        kind="reference",
        title="Reference: skip if short on time - prior art compared",
        layout="table",
        container="table: system, how it improves, gate and approval, read-me line",
        minutes=0.5,
        says="Genie, Cortex Analyst, Vanna, and LangChain's loop against this gate",
        src="Sources 1, 21-23",
        on_slide=[
            "| System | How it improves | Gate and approval |",
            "|---|---|---|",
            "| Databricks Genie | Benchmarks suggest instruction fixes | A person reviews; no gate described |",
            "| Snowflake Cortex Analyst | Up to 10 verified-query suggestions at a time | A person accepts each |",
            "| Vanna 2.0 | Saves successful interactions to memory | Automatic, no gate |",
            "| LangChain's loop | Analysis agent on production traces | Not described in the post |",
            "| DataPilot | Analyzer team on dev failures | Holdout, zero regressions, guarded rules, human approval |",
            "How to read this: the last column is what decides whether learned knowledge reaches "
            "production; each piece exists elsewhere, the combination is the difference.",
        ],
        notes=[
            "Plain explanation: Every piece of this loop exists somewhere. What we have not seen documented "
            "is the combination: a held-out split, zero per-item regressions, human approval of a "
            "versioned knowledge artefact, a deterministic overfit guard, and autonomy granted per metric "
            "family from holdout results. Say it as a combination we have not seen documented, never as an "
            "invention.",
            "Concrete example from DataPilot: The knowledge diff the gate shows is a versioned file of "
            "rules. Promotion changes which version is active, so rollback is choosing the previous one.",
            "Analogy: Feature flags plus a canary plus code review: each common, the combination is the "
            "discipline.",
            "Under the hood: Genie benchmarks in chat mode, the default, score answers against expected "
            "SQL results, comparing numbers to 4 significant digits; agent mode uses an LLM judge "
            "instead. Both suggest instruction fixes a human reviews. Cortex Analyst proposes up to "
            "10 verified-query candidates at a time for a person to accept. Vanna 2.0 saves "
            "successful interactions to tool memory automatically, which learns fastest and checks "
            "least. LangChain's post defines the same four loops; its hill-climbing loop reviews "
            "production traces and updates prompts, tools, or graders.",
            "Source 22: Suggestions for semantic models and views (https://docs.snowflake.com/en/"
            "user-guide/views-semantic/verified-query-suggestions), in summary: the "
            "system suggests verified queries and a person accepts them.",
            "Transfer: When you evaluate a vendor's self-improving feature, ask three questions: what does "
            "it learn from, what does it measure on that it did not learn from, and who approves.",
            "Point at: the gate column, top to bottom, then the read-me line.",
            'Ask: "Which row learns fastest, and what does that cost?" Expected: Vanna; it trusts every '
            "success, including lucky ones.",
            'Likely question: "Should production traces replace the benchmark?" Answer: They are a '
            "better source of failures; they are a worse referee, because no gold answer exists for most.",
            'Likely question: "Is human approval a bottleneck?" Answer: It is one review per version, '
            "not per answer.",
            'Misconception: "Human acceptance is the gate." Correction: A person can accept a rule that '
            "breaks other questions; measurement shows what a reviewer cannot see.",
            "Transition: Last, the ways learned knowledge goes wrong.",
        ],
    ),
    # 13 ------------------------------------------------------------------------------------------
    dict(
        kind="reference",
        title="Reference: skip if short on time - when learned knowledge fails",
        layout="table",
        container="table: failure mode, evidence, guard, read-me line",
        minutes=0.5,
        says="Failure modes of learned knowledge, their evidence, and the guard for each",
        src="Sources 18-20; pack.yaml evaluation; knowledge v2-overbroad",
        on_slide=[
            "| Failure mode | Evidence | Guard |",
            "|---|---|---|",
            "| Wrong human evidence | SEED: 105 BIRD dev pairs, 6.84 percent | Holdout gate |",
            "| Missing evidence | SEED: 148 pairs, 9.65 percent | Analyzer on failures |",
            "| Rules that do not transfer | MAGIC re-run: small gains, a drop | Holdout gate |",
            "| Rules quoting test questions | The naive analyzer | Overfit guard, a gate condition |",
            "| Over-broad rule | Exclude discounted orders | Zero regressions |",
            "How to read this: each row is one way knowledge goes wrong; the guard column names the "
            "step in this loop that catches it.",
        ],
        notes=[
            "Plain explanation: Knowledge fails in five recognisable ways, and each has a guard. Two are "
            "about the knowledge being wrong or absent, two about learning that does not generalise, and "
            "one about a rule that is right somewhere and wrong elsewhere.",
            'Concrete example from DataPilot: The pre-authored over-broad version adds "exclude '
            'discounted orders from revenue". It sounds like a fix for net revenue. It fixes some items '
            "and breaks others that passed before, and the zero-regression rule blocks it.",
            "Analogy: A style guide entry written after one bad review that then forbids a pattern the "
            "whole codebase uses correctly.",
            "Under the hood: SEED audited the human-written evidence in BIRD dev: 148 pairs, 9.65 percent, "
            "had none, and 105, 6.84 percent, had wrong evidence. Fixing the wrong evidence raised "
            "CodeS-15B from 44.76 to 54.29 on those pairs, so bad knowledge costs real accuracy. The "
            "MAGIC re-run showed small gains and a drop on one model, so learned rules need a holdout. "
            "The overfit guard rejects 6 consecutive question words or 20 consecutive gold SQL tokens.",
            'Source 20: SEED (https://arxiv.org/abs/2506.07423): "human-generated evidence in BIRD '
            "contains defects, including missing or erroneous evidence, which affects model "
            'performance."',
            "Transfer: Treat every knowledge source for an agent, wiki pages, memory, retrieved notes, as "
            "data that can be wrong. Version it, measure it, and gate changes to it like code.",
            "Point at: the over-broad row, the one the optional demo shows, then the guard column.",
            'Ask: "Which guard catches a rule that is right for revenue and wrong for orders?" Expected: '
            "zero regressions on both splits.",
            'Likely question: "Should human-written rules skip the gate?" Answer: No; SEED shows humans '
            "write wrong evidence too.",
            'Likely question: "Can the guard reject a good rule?" Answer: Rarely; a general rule seldom '
            "repeats six words of one question.",
            'Misconception: "More knowledge is always better." Correction: Wrong knowledge lowers '
            "accuracy; gated knowledge is better.",
            "Transition: That closes Section 4: Hill-climbing loop; on to the wrap-up.",
        ],
    ),
]
