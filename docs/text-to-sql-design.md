# Designing text-to-SQL for your own warehouse <!-- check-style: allow SC33 the page title; the first sentence spells the term out -->

DataPilot is a text-to-Structured Query Language (SQL) system: a question in plain words goes in,
and a query and its answer come out. This page turns what the four sections built into ten
steps you can take on your own warehouse, plus an optional eleventh. Each step says what to do, the
decisions to make, the mistakes to avoid, and where the course teaches it.

> **Terms on this page**
>
> - **Text-to-SQL**: Turning a question in plain words into a SQL query that answers it.
> - **Trap**: A business rule the schema does not reveal, so a plausible query gets it wrong.
> - **Gold SQL**: The query an analyst wrote by hand that gives the right answer.
> - **Execution match**: Running an answer's query and the gold query and comparing their results, not their text.
> - **Development split**: The benchmark questions the analyzer team may learn from.
> - **Holdout split**: The benchmark questions the analyzer team never sees; the gate decides on them.
> - **Knowledge version**: A numbered set of business rules given to the agent in its prompt.
> - **Semantic layer**: A shared set of metric and dimension definitions that tools query instead of raw tables.
> - **Metric family**: A group of benchmark questions about one kind of measure, such as revenue.

A number from the course links to the evidence page that records it, with its sample size. A
number or claim from outside links to its entry on the [sources page](sources.md), shown as the
source number the slides use, such as [16]. "Designing text-to-SQL" below is the design segment of
the class, right after the four-loop map; this page holds what it teaches.

## Why your warehouse is harder than a benchmark

Four things make text-to-SQL hard inside a company, and none of them is fixed by a larger model.

- **The rules live in people's heads, not in the schema.** DataPilot's five traps (fiscal year,
  net revenue, cancelled orders, Eastern time, internal accounts) are written down in the
  [business rules](../platform/packs/datapilot_us/benchmark/business_rules.md), which the agent
  never sees. Under the starting knowledge, 0 of 99 trap-question runs passed (33 questions, 3 runs
  each; [traps](calibration-report.md#traps)). On the BIRD benchmark, GPT-4's execution accuracy on
  the test set rises from 34.88 to 54.89 percent when it is given the evidence sentence
  ([16](sources.md#source-16)).
- **Schemas are large and poorly named.** Spider 2.0's databases often hold over 1,000 columns
  ([17](sources.md#source-17)). Snowflake gives the example of gross revenue that might be stored
  in a column named `amt_ttl_pre_dsc` ([37](sources.md#source-37)).
- **Values are informal.** People ask for "the blue hiking jacket"; the table stores a product
  name. Databricks writes that the way users ask "doesn’t directly match to the values that
  appear in the dataset" ([45](sources.md#source-45)).
- **A wrong number looks exactly like a right one.** DataPilot answered the fiscal year 2025
  revenue question with 72,394,572.08 dollars against a gold answer of 64,015,091.21, in a clean
  sentence with no error ([evidence for Section 1: Agent loop](evidence/section-1-agent-loop.md#results)).
  Uber's QueryGPT wrote `status = "Finished"` where the data says "Completed", and the query ran
  with no output ([49](sources.md#source-49)).

## The reference architecture

Every text-to-SQL system needs the same nine stages, whether a product or your own code runs them.
The diagram shows each stage, how DataPilot does it, and the loop that teaches it.

![The text-to-SQL reference architecture in nine stages, each with DataPilot's implementation and its loop: question routing by a fixed router; schema retrieval and linking by the schema scout agent; business knowledge in the knowledge version, a light semantic layer; value lookup, Assignment 1: Agent loop; SQL generation by the analyst agent; validation by the syntax-tree guard, the cost estimate, and the personal-data rules; capped execution through the read-only executor; an answer read by the reviewer agent, with its assumptions stated, or a clarifying question, which Assignment 2: Verification loop extends to undefined terms; and evaluation by execution match against gold queries on two databases, whose failures go back to the business knowledge, where the analyzer team proposes rules](diagrams/text-to-sql-architecture.png)

*Notice that routing, validation, execution, and evaluation are code; models link the schema, write the SQL, write and review the answer, and propose rules from stage 9.*

The code behind each stage is listed under the diagram on the [diagrams page](diagrams/README.md#the-text-to-sql-reference-architecture).
Value lookup is Assignment 1: Agent loop. Assignment 2: Verification loop adds the grader that
asks when a business term has no rule; the class analyst asks only when nothing in the schema
maps. The reviewer agent of Section 2: Verification loop is not a
stage of its own on the diagram: it reads the question, the query, and the result after the
graders pass, before the answer goes out.

### What the course did not measure

DataPilot is an agent with tools: it lists tables, describes them, runs queries, and tries again.
The other common design is one-shot generation: one model call writes the query from a prompt
that holds the schema and the rules. The course never ran one-shot generation against the agent
with tools, so it has no evidence on which is more accurate or cheaper on this warehouse. It also
never compared models: every agent runs on gpt-6-luna. Treat that choice as open, and measure it
on your own benchmark (step 2) before you commit to either.

The warehouse is small, five tables and one view, so the course did not test schema retrieval
over thousands of tables, or permissions for each asker. Steps 4 and 5 say what the sources
advise for both.

## Build or buy

Semantic-layer products and warehouse assistants already run several of these stages. The table
compares what their pages describe with what DataPilot does.

| Question | Semantic layers | Warehouse assistants | DataPilot |
|---|---|---|---|
| Where rules live | Metric definitions ([30](sources.md#source-30)) | Semantic views, example SQL ([37](sources.md#source-37), [44](sources.md#source-44)) | A versioned knowledge file |
| Who writes the SQL | The layer, or an agent it checks ([32](sources.md#source-32), [33](sources.md#source-33)) | The product's model ([36](sources.md#source-36)) | The analyst agent |
| Access per asker | The layer's policies ([33](sources.md#source-33)) | Warehouse access control ([36](sources.md#source-36)) | One service role |
| How it is measured | Not described on their pages | Held-back queries ([40](sources.md#source-40), [45](sources.md#source-45)) | Execution match, two databases |
| How it improves | A person edits or reviews ([33](sources.md#source-33)) | Suggestions a person reviews ([39](sources.md#source-39), [43](sources.md#source-43)) | A gate and human approval |

With dbt, MetricFlow writes the SQL ([32](sources.md#source-32)); Cube's agents write Semantic SQL
that the layer validates against the data model and its access policies ([33](sources.md#source-33)).

**What buying gives you.** Access control for each asker, applied by the platform, and an
interface someone else maintains; without a product, you build both yourself. Snowflake now
recommends Cortex Agents in place of Cortex Analyst ([36](sources.md#source-36)), so check which
product is current before you commit. A product also fixes some choices: Cortex Analyst does not
let you choose the model ([36](sources.md#source-36)).

**What buying does not give you.** The rules. Snowflake says schemas lack "business process
definitions and metrics" ([36](sources.md#source-36)), and Databricks's own example is a Genie
Agent using calendar quarters instead of the fiscal calendar ([43](sources.md#source-43)). A
product is where the rules live, not where they come from: steps 1 and 2 stay yours.

**What this course adds.** A holdout split the improver never sees, a gate that blocks on any
confirmed regression, an overfit guard, execution match on two databases, and autonomy earned per
metric family. Each part exists somewhere: Snowflake keeps evaluation queries out of the runtime
context and counts regressions ([40](sources.md#source-40)). The combination is what the course
measures; it was not compared with any product.

## The checklist

1. [Inventory the business rules](#inventory-the-business-rules)
2. [Build a gold question set before the agent](#build-a-gold-question-set-before-the-agent)
3. [Choose where each rule lives](#choose-where-each-rule-lives)
4. [Run each query read-only, with the asker's own access](#run-each-query-read-only-with-the-askers-own-access)
5. [Scope and describe tables; cap rows and values](#scope-and-describe-tables-cap-rows-and-values)
6. [Add value lookup](#add-value-lookup)
7. [Validate every query before it runs](#validate-every-query-before-it-runs)
8. [State assumptions; ask when a term has no rule](#state-assumptions-ask-when-a-term-has-no-rule)
9. [Measure execution match on two databases; re-run on every change](#measure-execution-match-on-two-databases-re-run-on-every-change)
10. [Start at the report-only level; earn autonomy per family](#start-at-the-report-only-level-earn-autonomy-per-family)
11. Optional: [Improve the rules from failures, behind a gate](#improve-the-rules-from-failures-behind-a-gate)

### Inventory the business rules

**Do this.** Write down every rule a correct answer depends on: the fiscal calendar, each metric's
formula, the status codes, the time zone, and the accounts to exclude. Give each rule an owner who
can say whether it is still true.

**Decide.** Which rules are fixed formulas and which change with the business, and who settles a
disagreement between two teams.

**Avoid.** Assuming the schema or column comments carry the rules. DataPilot's
[business rules page](../platform/packs/datapilot_us/benchmark/business_rules.md) states that
nothing in the schema, its comments, or its sample data holds them. Snowflake says the same of
schemas in general ([36](sources.md#source-36)).

**Taught in.** Designing text-to-SQL, the design segment, and
[Section 1: Agent loop](../section-1-agent-loop/README.md), where the five traps fail 0 of 99 runs
under the starting knowledge.

### Build a gold question set before the agent

**Do this.** Write 10 to 20 representative questions to start, each with a gold query you checked
by hand, before you build anything ([45](sources.md#source-45)). Make sure each rule from step 1
is carried by some question. Split the set into development questions and holdout questions.

**Decide.** How many holdout questions each metric family needs before it can earn autonomy.
[Assignment 4: Hill-climbing loop](../section-4-hill-climbing-loop/assignment/README.md) requires
at least 3 per family before the unattended level. The class code does not, and its average order
value family has 1 holdout question (`autonomy` in [pack.yaml](../platform/packs/datapilot_us/pack.yaml)).

**Avoid.** Letting anything that writes rules see the holdout split. Snowflake uses a verified
query either at runtime or as evaluation ground truth, "but not both at the same time"
([40](sources.md#source-40)). Avoid gold answers relative to today as well (step 9).

**Taught in.** [Section 4: Hill-climbing loop](../section-4-hill-climbing-loop/README.md) and
[Assignment 4: Hill-climbing loop](../section-4-hill-climbing-loop/assignment/README.md). DataPilot's
benchmark has 40 questions: 25 development questions and 15 holdout questions
([model bake-off](calibration-report.md#model-bake-off)).

### Choose where each rule lives

**Do this.** Put a fixed formula in a semantic layer or a database view, so the database computes
it. Put a rule the system must learn and gate in a versioned knowledge file. Keep the prompt for
the working method only.

**Decide.** Prompt, knowledge file, semantic layer, or view, rule by rule. Databricks advises text
instructions "only as a last resort" ([44](sources.md#source-44)). Snowflake defines net revenue
once as a metric ([37](sources.md#source-37)), and dbt shares one definition with every tool
([30](sources.md#source-30)). For a fiscal calendar, a view-side fix is a calendar table with a
fiscal-year column that every query joins.

**Avoid.** Believing a layer or a view guarantees the formula. It enforces the formula only if the
agent's role can read nothing else; otherwise the model can skip it, or pick the wrong view,
filter, or grain. A metric layer also answers only the questions its metrics express, so keep a
path for the rest. Avoid rules written as prose the database cannot check too: one learned rule
held a placeholder instead of a real predicate, and DataPilot's answer to the fiscal year 2025
revenue question was 28,474.44 dollars low while
labelled verified ([after the ledger correction](calibration-report.md#resumed-after-the-ledger-correction)).
DataPilot now parses each rule's SQL against the catalog.

**Taught in.** Designing text-to-SQL, the design segment, and
[Section 4](../section-4-hill-climbing-loop/README.md): with the rules learned into a knowledge
version and no model change, promoted versions passed 10 to 14 of 15 holdout questions, against 2
of 15 at the start ([Section 4 evidence](evidence/section-4-hill-climbing-loop.md#results)). The
course measured a knowledge file only; it did not compare it with a semantic layer, a view, or
one-shot generation.

### Run each query read-only, with the asker's own access

**Do this.** Give the agent a read-only role granted only the tables it needs. Run every query in a
read-only transaction with a statement timeout; DataPilot's is 5,000 milliseconds
(`statement_timeout_ms` in [pack.yaml](../platform/packs/datapilot_us/pack.yaml)). Leave no write
privilege to fall back on. Then run each query with the asker's own permissions as well, through
row-level security, column masking, or the warehouse's access control.

**Decide.** Which tables and views the role may read, the timeout your warehouse can afford, and
how the asker's identity reaches the query. Per-role settings in PostgreSQL become each session's
default ([15](sources.md#source-15)). Cortex Analyst follows Snowflake's role-based access control
([36](sources.md#source-36)), and Cube applies access policies before a query reaches the
warehouse ([33](sources.md#source-33)).

**Avoid.** One service role for everyone in a real company: DataPilot runs as one role, so every
asker sees what that role sees. Avoid forgetting where approved rows go: they go to the model
provider. One approved export sent 5,261 email addresses through the model
([resumed without traces](calibration-report.md#resumed-without-traces-stopped-at-the-ledger)).
Avoid trusting a prompt line or a model check to stop writes: the LangChain tutorial's tools "are
not intended to be secure" ([5](sources.md#source-5)). And avoid trusting the role alone: OWASP
says least privilege "limits the damage" and "does not prevent SQL injection"
([13](sources.md#source-13)).

**Taught in.** [Section 2: Verification loop](../section-2-verification-loop/README.md). With the guard
weakened, every malicious write still met the read-only transaction (25006) or the grants (42501),
and the orders table was unchanged ([Section 2 evidence](evidence/section-2-verification-loop.md#results)).

### Scope and describe tables; cap rows and values

**Do this.** Describe every column the agent may use, show a few sample rows and distinct values,
keep the set of tables small, and cap what a query returns: rows, characters per value, and the
total count.

**Decide.** How many tables to expose, and the caps. Databricks advises "five or fewer tables"
([44](sources.md#source-44)). LangChain's SQL toolkit already describes a table with three sample
rows and cuts values at 300 characters, but returns every row ([54](sources.md#source-54)).
DataPilot adds the distinct values of small columns and a row cap with the total count, and returns at most 50 rows and 2,000 characters per value
([the caps](costs.md#the-caps)).

**At scale.** On a warehouse with thousands of tables, even the table list is too long for the
context. Retrieve candidate tables from their descriptions, scope each agent to one subject area
of about five tables ([44](sources.md#source-44)), and let a person confirm the tables, as Uber's Table
Agent does ([49](sources.md#source-49)). Uber found that plain similarity search over schemas did
not return relevant results, and added a step that prunes columns from tables of over 200 columns
([49](sources.md#source-49)). In 500 Spider questions with every database's schema pooled,
schema-linking errors were 68.3 percent of failures ([18](sources.md#source-18)).

**Avoid.** A row cap without a size cap. One approved export returned a single row holding 5,261
email addresses, and the run reached 109,380 tokens against a 60,000-token budget
([resumed without traces](calibration-report.md#resumed-without-traces-stopped-at-the-ledger)).
With the value cap, the same export used 7,670 tokens.

**Taught in.** [Section 1](../section-1-agent-loop/README.md). With full column descriptions,
capped rows, and the schema scout, 17 of 21 easy runs were correct, against 12 of 21 with column
names only. A 10,000-row result cost 182,654 tokens without the row cap and 30,216 with it
([benefits](benefits.md#section-1-agent-loop)).

### Add value lookup

**Do this.** Before filtering on a name a person typed, look the stored value up. Ask when two
stored values are equally close.

**Decide.** Which columns get lookup (products, categories, regions) and how close a match must be.
Never build a value index over personal-data columns: the index would hand customers' names and
emails to every asker and to the model.

**Avoid.** Filtering on the user's words. Uber's agent filtered on "Finished" where the data says
"Completed", and the query ran with no output ([49](sources.md#source-49)). Databricks matches
values to the question for the same reason ([44](sources.md#source-44)). DataPilot's warehouse
keeps two product names that differ by one space on purpose
([data conditions](../platform/packs/datapilot_us/benchmark/business_rules.md#data-conditions-kept-on-purpose)).

**Taught in.** [Assignment 1: Agent loop](../section-1-agent-loop/assignment/README.md), which adds a
value-lookup tool.

### Validate every query before it runs

**Do this.** Parse the query into a syntax tree. Allow one read-only statement over allowed tables.
Estimate its cost from the query plan and refuse an expensive one. Send a query that returns
personal data to human approval.

**Decide.** The cost thresholds (DataPilot's are in `cost_guard` in
[pack.yaml](../platform/packs/datapilot_us/pack.yaml)), and which columns are personal data.

**Avoid.** Holding a query only because it mentions a personal column. DataPilot once held every
query that filtered internal accounts by email, so no correct candidate could be scored
([analyzer comparison](calibration-report.md#analyzer-comparison)); it now holds only queries that
return one. Avoid reading a passing check as a right answer: every grader passed on the wrong
fiscal year 2025 answer in 4 of 4 runs ([Section 2 evidence](evidence/section-2-verification-loop.md#results)).

**Taught in.** [Section 2](../section-2-verification-loop/README.md) and
[Assignment 2: Verification loop](../section-2-verification-loop/assignment/README.md). A join with
no join condition was refused before it ran, and without the cost guard it ran until the statement
timeout ([benefits](benefits.md#section-2-verification-loop)).

### State assumptions; ask when a term has no rule

**Do this.** Answer with the assumptions stated, so a reviewer or a checker can judge them. Ask a
clarifying question when the question uses a business term no rule defines, such as "VIP
customers", or names nothing the schema holds.

**Decide.** The trigger for asking, written down. Databricks says to "be explicit about when to
ask for clarifications" ([44](sources.md#source-44)); PRACTIQ classifies a question before it
clarifies ([23](sources.md#source-23)). A question can map cleanly to the schema and still be
ambiguous ([22](sources.md#source-22)), so the trigger is a missing rule, not a missing table.

**Avoid.** Asking when a rule answers the question. When DataPilot answered the fiscal year 2025
question with a clarifying question, it left "nothing for the reviewer or the gold check"
([changes recorded](calibration-report.md#changes-recorded)). Avoid guessing at an undefined term
too: the answer looks complete and is built on a guess.

**Taught in.** [Assignment 2](../section-2-verification-loop/assignment/README.md), which adds a
grader that asks when a business term is not defined, and [Section 1](../section-1-agent-loop/README.md).
The class prompt tells the analyst to assume, and to ask only when the question names nothing in
the schema (`platform/src/datapilot/loop1_agent/prompts.py`). Even so, "How many VIP customers do
we have?" and a question about "loyal customers" each ended with a clarifying question, one run
each ([edge cases](calibration-report.md#edge-cases)). The grader makes the rule code, so it no
longer depends on the model.

### Measure execution match on two databases; re-run on every change

**Do this.** Run each answer's query and compare its result with the gold result, on more than one
database, with repeated runs. A second database means the same schema with different rows: a
reseeded synthetic copy, or a shuffled and masked sample of production. DataPilot's second
database is a reseeded copy
([data conditions](../platform/packs/datapilot_us/benchmark/business_rules.md#data-conditions-kept-on-purpose)).
The test-suite paper samples 1,000 random databases for each schema and distils about 42 per query
([12](sources.md#source-12)).

Re-run the whole benchmark on every change: the prompt or the knowledge, and also the schema, a
rule owner's definition, or the data. Write every gold query with literal dates, never relative to
today.

**Decide.** How many databases, how many runs per question, and when a single failure counts as a
regression. DataPilot runs holdout questions 3 times and passes one on 2, and re-runs an apparent
regression before it counts ([confirming re-run](calibration-report.md#confirming-re-run)).
Compare results ignoring row order unless the question asks for an order, with a numeric
tolerance, as DataPilot's [evaluator](../platform/src/datapilot/loop4_hill_climbing/evaluator.py)
does. Genie's chat mode compares numbers rounded to 4 significant digits ([43](sources.md#source-43)).
Decide too what triggers a re-run: a schema migration, a changed rule, a new data source, a new
model. Snowflake warns that evaluation results "may drift over time" when verified queries use
time-relative concepts ([40](sources.md#source-40)).

**Avoid.** Judging by query text, or by one database. Checking results on a single database passed
wrong queries 6.5 percent of the time on average across 21 Spider submissions
([12](sources.md#source-12)). DataPilot checks gold on two databases with different seeds, so a
match cannot be a remembered number ([setup](calibration-report.md#setup)).

Avoid a benchmark that drifts with the calendar: DataPilot pins a business date, 31 January 2026,
and its gold SQL uses literal dates
([business date](../platform/packs/datapilot_us/benchmark/business_rules.md#business-date)).
Avoid rules that name columns that no longer exist: DataPilot parses each learned rule's SQL
against the catalog, which catches a renamed column
([after the ledger correction](calibration-report.md#resumed-after-the-ledger-correction)).

**Taught in.** [Section 4](../section-4-hill-climbing-loop/README.md), and the gold check of
[Section 2](../section-2-verification-loop/README.md). One 70-run benchmark experiment cost 0.0594
to 0.0914 dollars where recorded ([wall time](calibration-report.md#wall-time)), so you can afford
to measure every change. At every preflight, DataPilot's drift canary checks that three easy
questions still pass and two trap questions still fail under the starting knowledge
([drift canary](calibration-report.md#drift-canary)).

### Start at the report-only level; earn autonomy per family

**Do this.** Start every answer at the report-only level. Let a metric family run unattended only
after its holdout questions pass. Add a kill switch that reaches work already running, and a daily
token budget.

**Decide.** The standard a family must meet, and who may engage the kill switch. The three levels
and the kill switch come from Cobus Greyling's loop engineering page ([2](sources.md#source-2)).

**Avoid.** Autonomy for the whole system at once. Revenue cleared in 7 of 11 live promotions, and
orders never did ([stability and the holdout](calibration-report.md#stability-and-the-holdout)).
Avoid a kill switch checked only when a job is claimed: the run already in flight posted anyway.

**Taught in.** [Section 3: Event loop](../section-3-event-loop/README.md) and
[Section 4](../section-4-hill-climbing-loop/README.md). Checked in flight, the kill switch stopped
the run in every recorded run ([Section 3 evidence](evidence/section-3-event-loop.md#results)). The
daily budget stopped a rehearsal run at 1,969,486 of 2,000,000 tokens
([the retake chains](calibration-report.md#the-retake-chains)). Families clear on holdout results in
Section 4.

### Improve the rules from failures, behind a gate

This step is optional; it is what Section 4 adds on top of the other ten.

**Do this.** Let a team of agents propose rules from failed development questions only. Promote a
candidate only when the holdout gains, nothing regresses, a person approves, and every new rule
passes an overfit guard ([the gate](../platform/src/datapilot/loop4_hill_climbing/gate.py)).

**Decide.** Who approves, and what the overfit guard rejects. DataPilot's rejects a rule that copies
6 consecutive words of a benchmark question or 20 consecutive tokens of a gold query (`evaluation`
in [pack.yaml](../platform/packs/datapilot_us/pack.yaml)).

**Avoid.** Trusting a holdout count alone. A naive analyzer once passed 15 of 15 holdout questions
and the gate said ready; the gate gained the overfit guard, and the naive analyzer has been blocked
in 6 of 6 runs since ([the naive analyzer](calibration-report.md#the-naive-analyzer-1)). A plausible
rule, "exclude discounted orders from revenue", cost 9 confirmed regressions and was blocked
([the over-broad rule](calibration-report.md#the-over-broad-rule)). Products keep a person in the
loop too: Snowflake's suggestions "are not automatically applied" ([39](sources.md#source-39)).

**Taught in.** [Section 4](../section-4-hill-climbing-loop/README.md) and
[Assignment 4](../section-4-hill-climbing-loop/assignment/README.md).

## Where next

Try the checklist on a domain no section used in the [final project](../final-project/README.md),
then point DataPilot at your own Postgres with [use it in your repository](../use-in-your-repo/README.md).
Every outside source on this page is on the [sources page](sources.md).
