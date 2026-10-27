# Glossary

Every term and abbreviation Module: Loop Engineering uses, in plain words. Pages still spell out a
term the first time they use it, such as Structured Query Language (SQL); come here when a word
is new or you forgot it. The course names come first, then every other term from A to Z. Each definition has the same wording as the
glossary boxes on the pages.

## Course names

Pages write a name in full the first time, such as "Section 2: Verification loop", and then the
short form, "Section 2". The identifier in the right-hand column appears only in code: commands,
file names, logs, and captured output. The single source is `platform/src/datapilot/names.py`.

### Sections and assignments

| Name | What it covers | Identifier |
|---|---|---|
| Section 1: Agent loop | The analyst, its tools, the row cap, the answer envelope, the schema scout | `agent-loop` |
| Section 2: Verification loop | Seven graders, the read-only role, the retry cap, the reviewer | `verification-loop` |
| Section 3: Event loop | Events, the job queue, durable approval, autonomy levels, the kill switch | `event-loop` |
| Section 4: Hill-climbing loop | The benchmark, the analyzer team, the overfit guard, the promotion gate | `hill-climbing-loop` |
| Assignment 1: Agent loop | A value-lookup tool for informal or misspelled names | `make check-assignment NAME=agent-loop` |
| Assignment 2: Verification loop | A clarify-or-abstain grader and a personal-data leak grader | `make check-assignment NAME=verification-loop` |
| Assignment 3: Event loop | A nightly revenue anomaly alert, one per day, stopped by the kill switch | `make check-assignment NAME=event-loop` |
| Assignment 4: Hill-climbing loop | A repeat-customer metric family, a critic change, a holdout minimum per family | `make check-assignment NAME=hill-climbing-loop` |

### Business rules and traps

The business rules are the ground truth in
`platform/packs/datapilot_us/benchmark/business_rules.md`. Five of them are traps: the schema does
not reveal them.

| Business rule | What it says | Trap |
|---|---|---|
| Business rule 1: Fiscal year | The fiscal year runs February 1 to January 31 | Trap 1: Fiscal year |
| Business rule 2: Money in cents | Money columns hold whole cents | Not a trap |
| Business rule 3: Net revenue | Net revenue is subtotal minus discount, never `total_cents` | Trap 2: Net revenue |
| Business rule 4: Cancelled orders | Status 5 means cancelled; cancelled orders never count | Trap 3: Cancelled orders |
| Business rule 5: Eastern business days | Days and holidays are in Eastern time | Trap 4: Eastern time |
| Business rule 6: Internal accounts | Staff accounts on `@harborpine.com` are excluded | Trap 5: Internal accounts |

### Autonomy levels

| Level | What DataPilot may do | Identifier |
|---|---|---|
| report-only level | Answers are posted labelled unverified; no exports | `report_only` |
| assisted level | Answers are posted; personal data and exports need human approval | `assisted` |
| unattended level | Unattended posting, for eligible metric families only | `unattended` |

### Demos and planted bugs

Every demo has a readable slug, used in `make demo NAME=<slug>`, and a name in prose, such as "the
confident wrong answer" for `agent-confident-wrong-answer`. The full list is in each section's demo
page and in `platform/demos/registry.yaml`. Every planted bug is written by its name, then its flag
in a code span: the naive guard (`BUG_NAIVE_GUARD`). The list, with what each one does, is in
[planted items](planted-items.md).

## Terms A to Z

- **Agent loop**: The model calls tools, reads the results, and repeats until it answers.
- **Analyzer team**: The failure analyst, the rule writer, and the critic, which turn failed development
  questions into a candidate knowledge version.
- **Answer envelope**: The structured result of a run: status, SQL, rows, and answer text.
- **Application programming interface (API)**: The service DataPilot's console and commands call;
  in this course, the `api` container on port 8000.
- **Autonomy level**: How much DataPilot may do unattended: report-only, assisted, or unattended.
- **Baseline experiment**: The benchmark run under the active knowledge version, started in the open
  live session, that the candidate is compared against.
- **Business date**: The day DataPilot treats as today, 31 January 2026 (`DATAPILOT_BUSINESS_DATE`).
- **Candidate**: A knowledge version the analyzer team proposed, not yet promoted.
- **Candidates A and B**: The two rule sets the analyzer team writes from the same failed
  development questions; the development split alone picks the one that goes to the gate.
- **Class-day safeguard**: The live fallback for a wrong finale: the version verified in rehearsal
  becomes active, and the finale runs again.
- **Comma-separated values (CSV)**: A plain-text table format, one row per line.
- **Console**: The Streamlit app that shows every loop live, on four pages.
- **Coordinated Universal Time (UTC)**: The time zone the services run on; the console shows your
  local time.
- **Critic**: The agent of the analyzer team that keeps, narrows, or drops each proposed rule, and
  never adds one.
- **Development split**: The benchmark questions the analyzer team may learn from.
- **Domain pack**: The folder that holds one warehouse's settings, rules, benchmark, and knowledge.
- **Drift canary**: Three easy questions that must pass and two trap questions that must still fail.
- **Escalated**: A run that ended without an answer because it hit a cap or a refused write.
- **Evaluator**: The code that runs a benchmark answer's query and the gold query on both
  warehouses and compares their results.
- **Event loop**: Events become jobs that workers run, with approvals, budgets, and a kill switch.
- **Execution match**: Running an answer's query and the gold query and comparing their results, not their text.
- **Failure analyst**: The agent of the analyzer team that diagnoses why each failed development question
  failed.
- **Fiscal year 2025 revenue question**: "What was our net revenue in fiscal year 2025?", the
  question every section asks.
- **Gold SQL**: The query an analyst wrote by hand that gives the right answer.
- **Grader**: A check that passes or fails one stage of a run and says why.
- **Hill-climbing loop**: Experiments find failures, an analyzer team proposes rules, and a gate
  decides.
- **Holdout split**: The benchmark questions the analyzer team never sees; the gate decides on them.
- **Human approval**: A person approves or rejects a held action before it runs.
- **Hypertext Transfer Protocol (HTTP)**: The protocol the api speaks; a webhook is one HTTP
  request.
- **Idempotency**: Running the same event twice has the effect of running it once.
- **JavaScript Object Notation (JSON)**: The text format of every api request and response.
- **Kill switch**: The guarded control that stops every worker and forces the report-only level.
- **Knowledge version**: A numbered set of business rules given to the agent in its prompt.
- **Large language model (LLM)**: A model such as gpt-6-luna that reads and writes text and calls
  tools.
- **Lease**: The time a worker owns a claimed job; a job whose lease expires goes back to the
  queue.
- **Live session**: Everything that runs between one `make preflight` and the next.
- **Live stamp**: A result's run start time and its LangSmith trace: a check prints the time in Coordinated Universal Time (UTC), the console in your local time.
- **Metric family**: A group of benchmark questions about one kind of measure, such as revenue.
- **Naive SQL**: The plausible query a model without the business rules writes; a trap makes it
  wrong.
- **Ops schema**: The `ops` tables in Postgres that hold runs, events, approvals, experiments, and
  budgets; `make up` applies its migrations.
- **Overfit guard**: The code check that rejects a rule copying a benchmark question or a gold
  query.
- **Personal data**: Customer emails, phone numbers, and names; a query that reads them waits for
  human approval.
- **Planted bug**: A defect switched on by a flag so a demo shows its failure every time.
- **Promotion gate**: The check that a new knowledge version must pass before it becomes active.
- **Regression**: An item that passed under the active version and fails under the candidate, confirmed by re-runs.
- **Reviewer**: An independent agent that reads the question, SQL, and result after the graders
  pass.
- **Router**: The fixed table from event type to handler and queue; deliberately not an agent.
- **Row cap**: The most rows a query returns to the model (`limits.row_cap`).
- **Reset archive**: The copy of every row a hill-climbing reset deletes or retires, kept in
  `ops.reset_archive_rows`.
- **Rule writer**: The agent of the analyzer team that proposes rules from the failure analyst's
  diagnoses.
- **Schema scout**: A stateless helper agent that suggests tables and joins for a question.
- **Semantic layer**: A shared set of metric and dimension definitions that tools query instead of raw tables.
- **Stability filter**: The calibration check that keeps only holdout items that pass or fail
  consistently.
- **Starting knowledge**: Version 1 of the knowledge (the starting version), the rules DataPilot
  starts with: only the money rule.
- **Structured Query Language (SQL)**: The language of every query the analyst writes.
- **Text-to-SQL**: Turning a question in plain words into a SQL query that answers it.
- **Trace**: The record of one run's steps, each model call and tool call, stored in LangSmith.
- **Trace sample**: The share of experiment runs that send a trace, about 1 in 5
  (`tracing.experiment_sample_rate`); a row with none reads "Not traced".
- **Trap**: A business rule the schema does not reveal, so a plausible query gets it wrong.
- **Uniform Resource Locator (URL)**: A web address, such as the console's <http://localhost:8501>.
- **Verification loop**: Graders check each query and answer, and send failures back to the agent.
- **WSL2**: Windows Subsystem for Linux, which runs a real Ubuntu next to Windows.
