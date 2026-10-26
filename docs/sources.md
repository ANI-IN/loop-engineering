# Sources

Every verified outside source behind the course, with the course's own evidence pages at the end:
54 sources. The class slides and their speaker notes cite 30 of them, numbered as here, and the
rest support the course's pages. A slide marks a sourced claim with a small number, such as [16];
that number is the entry here. Many titles name Structured Query Language (SQL), a large language model
(LLM), artificial intelligence (AI), or an application programming interface (API).

Each entry gives the title, the authors or the organisation, the year (or "undated" when the page
carries no date), the full address, and what the course uses it for. Every address was opened and
read on 26 October 2026. A benchmark figure keeps the form its source publishes, with its
condition; course numbers are counts and come from the evidence pages in the last group.

## Agent design

- <a id="source-1"></a>**[1]** The Art of Loop Engineering. Sydney Runkle, LangChain, 2026.
  <https://www.langchain.com/blog/the-art-of-loop-engineering>
  Used for the four loops, the grader that sends failures back, and its cost in latency.
- <a id="source-2"></a>**[2]** Loop Engineering — Design systems that prompt your agents. Cobus
  Greyling, undated. <https://cobusgreyling.github.io/loop-engineering/>
  Used for the three autonomy levels and the kill switch that drops to the report-only level.
- <a id="source-3"></a>**[3]** Building effective agents. Erik Schluntz and Barry Zhang,
  Anthropic, 2024. <https://www.anthropic.com/engineering/building-effective-agents>
  Used for starting simple and for tools designed so mistakes are hard to make.
- <a id="source-4"></a>**[4]** Writing effective tools for AI agents. Ken Aizawa, Anthropic, 2025.
  <https://www.anthropic.com/engineering/writing-tools-for-agents>
  Used for capping what a tool returns, and for held-out test sets against overfitting.
- <a id="source-5"></a>**[5]** Build a SQL agent. LangChain documentation, undated.
  <https://docs.langchain.com/oss/python/langchain/sql-agent>
  Used for the tutorial's warning that its tools are not for production, and narrow permissions.
- <a id="source-6"></a>**[6]** Build a custom SQL agent (LangGraph). LangChain documentation,
  undated. <https://docs.langchain.com/oss/python/langgraph/sql-agent>
  Used for the same warning, and its query check as a model call rather than code.
- <a id="source-7"></a>**[7]** Structured output. LangChain documentation, undated.
  <https://docs.langchain.com/oss/python/langchain/structured-output>
  Used for the answer envelope as the agent's structured response.
- <a id="source-8"></a>**[8]** Custom middleware. LangChain documentation, undated.
  <https://docs.langchain.com/oss/python/langchain/middleware/custom>
  Used for the hooks before each model call and around each tool call that enforce the caps.
- <a id="source-9"></a>**[9]** Prebuilt middleware. LangChain documentation, undated.
  <https://docs.langchain.com/oss/python/langchain/middleware/built-in>
  Used for call limits that end a run, and the existing personal-data middleware.
- <a id="source-10"></a>**[10]** Human-in-the-loop. LangChain documentation, undated.
  <https://docs.langchain.com/oss/python/langchain/human-in-the-loop>
  Used for a paused approval as saved state, which needs a persistent checkpointer in production.
- <a id="source-11"></a>**[11]** Temperature in GPT-5 models. OpenAI Developer Community thread
  started by the user jim, 2025. <https://community.openai.com/t/temperature-in-gpt-5-models/1337133>
  Used only for developers' reports that GPT-5 reasoning models reject a custom temperature.
- <a id="source-54"></a>**[54]** SQLDatabase utility, source code. LangChain (langchain-community),
  2026.
  <https://github.com/langchain-ai/langchain-community/blob/main/libs/community/langchain_community/utilities/sql_database.py>
  Used for what LangChain's SQL toolkit already does: it describes a table with three sample rows
  and cuts values at 300 characters, but returns every row. DataPilot adds the distinct values of
  small columns and a row cap with the total count.

## Verification and evaluation

- <a id="source-12"></a>**[12]** Semantic Evaluation for Text-to-SQL with Distilled Test Suites.
  Ruiqi Zhong, Tao Yu, Dan Klein, 2020. <https://arxiv.org/abs/2010.02840>
  Used for checking results on more than one database: one database passes some wrong queries.
- <a id="source-13"></a>**[13]** SQL Injection Prevention Cheat Sheet. OWASP (the Open Worldwide
  Application Security Project) Cheat Sheet Series,
  undated.
  <https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html>
  Used for least privilege: it limits the damage, and it does not prevent the attack.
- <a id="source-14"></a>**[14]** Appendix A. PostgreSQL Error Codes. PostgreSQL Global
  Development Group, undated. <https://www.postgresql.org/docs/current/errcodes-appendix.html>
  Used for the codes the course tests on: 25006, 42501, and 57014.
- <a id="source-15"></a>**[15]** ALTER ROLE. PostgreSQL Global Development Group, undated.
  <https://www.postgresql.org/docs/current/sql-alterrole.html>
  Used for per-role session settings, such as the agent role's statement timeout.

## Text-to-SQL research and benchmarks

- <a id="source-16"></a>**[16]** Can LLM Already Serve as A Database Interface? A BIg Bench for
  Large-Scale Database Grounded Text-to-SQLs (BIRD). Jinyang Li and others, 2023.
  <https://arxiv.org/abs/2305.03111>
  Used for business knowledge outside the schema, with and without its evidence sentences.
- <a id="source-17"></a>**[17]** Spider 2.0: Evaluating Language Models on Real-World Enterprise
  Text-to-SQL Workflows. Fangyu Lei and others, 2024. <https://arxiv.org/abs/2411.07763>
  Used for large enterprise schemas and how far agents fall on them.
- <a id="source-18"></a>**[18]** LinkAlign: Scalable Schema Linking for Real-World Large-Scale
  Multi-Database Text-to-SQL (version 3). Yihan Wang, Peiyu Liu, 2025.
  <https://arxiv.org/html/2503.18596v3>
  Used for schema linking as the main cause of failures, in a sample with every database's
  schema pooled.
- <a id="source-19"></a>**[19]** MAGIC: Generating Self-Correction Guideline for In-Context
  Text-to-SQL. Arian Askari, Christian Poelitz, Xinye Tang, 2024.
  <https://arxiv.org/abs/2406.12692>
  Used for guidelines written by agents from failures, the idea behind the analyzer team.
- <a id="source-20"></a>**[20]** Toward Real-World Table Agents: Capabilities, Workflows, and
  Design Principles for LLM-based Table Intelligence. Jiaming Tian and others, 2025.
  <https://arxiv.org/html/2507.10281>
  Used for a re-run in which failure-derived guidelines scored below the baseline.
- <a id="source-21"></a>**[21]** SEED: Enhancing Text-to-SQL Performance and Practical Usability
  Through Automatic Evidence Generation. Janghyeon Yun, Sang-goo Lee, 2025.
  <https://arxiv.org/abs/2506.07423>
  Used for business knowledge written by people that is itself missing or wrong.
- <a id="source-22"></a>**[22]** AMBROSIA: A Benchmark for Parsing Ambiguous Questions into
  Database Queries. Irina Saparina, Mirella Lapata, 2024. <https://arxiv.org/abs/2406.19073>
  Used for the kinds of ambiguity in real questions.
- <a id="source-23"></a>**[23]** PRACTIQ: A Practical Conversational Text-to-SQL dataset with
  Ambiguous and Unanswerable Queries. Mingwen Dong and others, 2024.
  <https://arxiv.org/abs/2410.11076v1>
  Used for classifying a question first, then clarifying only when it needs it.
- <a id="source-24"></a>**[24]** DIN-SQL: Decomposed In-Context Learning of Text-to-SQL with
  Self-Correction. Mohammadreza Pourreza, Davood Rafiei, 2023. <https://arxiv.org/abs/2304.11015>
  Used as the human-written self-correction baseline that MAGIC compares against.
- <a id="source-25"></a>**[25]** ReFoRCE: A Text-to-SQL Agent with Self-Refinement, Consensus
  Enforcement, and Column Exploration. Minghang Deng and others, 2025.
  <https://arxiv.org/abs/2502.00675>
  Used for enterprise schema size, and for deferring cases the agent is not confident about.

## Event-driven systems

- <a id="source-26"></a>**[26]** Postgres Job Queues & Failure By MVCC. Brandur Leach, 2015.
  <https://brandur.org/postgres-queues>
  Multiversion concurrency control (MVCC) is how Postgres keeps old row
  versions. Used for why the job queue lives in the database, and what long transactions cost it.
- <a id="source-27"></a>**[27]** You Don't Need a Job Queue, Postgres Already Has SKIP LOCKED.
  Nurul Sundarani, Prisma, 2026.
  <https://www.prisma.io/blog/you-dont-need-a-job-queue-postgres-already-has-skip-locked>
  Used for leases, and its statement that its queue delivers at least once, so handlers must
  be safe to run twice.
- <a id="source-28"></a>**[28]** SELECT. PostgreSQL Global Development Group, undated.
  <https://www.postgresql.org/docs/current/sql-select.html>
  Used for `SKIP LOCKED`, how several workers claim jobs without waiting on each other.
- <a id="source-29"></a>**[29]** Making retries safe with idempotent APIs. Malcolm Featonby,
  Amazon Builders' Library, Amazon Web Services, undated.
  <https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/>
  Used for the caller-provided request identifier behind the idempotency key.

## Products and documentation

- <a id="source-30"></a>**[30]** dbt Semantic Layer. dbt Labs, undated.
  <https://docs.getdbt.com/docs/use-dbt-semantic-layer/dbt-sl>
  Used for metrics defined once and shared by every tool, an alternative home for business rules.
- <a id="source-31"></a>**[31]** About MetricFlow. dbt Labs, undated.
  <https://docs.getdbt.com/docs/build/about-metricflow>
  Used for a semantic layer that writes the SQL itself from metric definitions.
- <a id="source-32"></a>**[32]** dbt Semantic Layer FAQs. dbt Labs, undated.
  <https://docs.getdbt.com/docs/use-dbt-semantic-layer/sl-faqs>
  Used for the layer, not the model, generating the SQL for a metric request.
- <a id="source-33"></a>**[33]** Introduction (Cube documentation). Cube Dev, undated.
  <https://cube.dev/docs/product/introduction>
  Used for agents that query a semantic layer, which validates each query and applies access rules.
- <a id="source-34"></a>**[34]** AI context (Cube documentation). Cube Dev, undated.
  <https://docs.cube.dev/docs/data-modeling/ai-context>
  Used for descriptions written for agents inside a semantic layer.
- <a id="source-35"></a>**[35]** Analytics Chat (Cube documentation). Cube Dev, undated.
  <https://docs.cube.dev/docs/explore-analyze/analytics-chat>
  Used for a chat product whose queries all run against the semantic model.
- <a id="source-36"></a>**[36]** Cortex Analyst. Snowflake documentation, undated.
  <https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst>
  Used for why a schema alone is not enough, and for what a managed service does and does not offer.
- <a id="source-37"></a>**[37]** Overview of semantic views. Snowflake documentation, undated.
  <https://docs.snowflake.com/en/user-guide/views-semantic/overview>
  Used for poorly named columns, and a business rule written once as a metric.
- <a id="source-38"></a>**[38]** Cortex Analyst Verified Query Repository. Snowflake
  documentation, undated.
  <https://docs.snowflake.com/user-guide/snowflake-cortex/cortex-analyst/verified-query-repository>
  Used for checked example queries, and the harm a wrong one does.
- <a id="source-39"></a>**[39]** Suggestions for semantic models and views. Snowflake
  documentation, undated.
  <https://docs.snowflake.com/en/user-guide/views-semantic/verified-query-suggestions>
  Used for suggested improvements that a person accepts, edits, or dismisses.
- <a id="source-40"></a>**[40]** Cortex Analyst evaluations. Snowflake documentation, undated.
  <https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst-evaluations>
  Used for evaluation queries kept out of the context, regression counts, and run-to-run variation.
- <a id="source-41"></a>**[41]** Cortex Analyst administrator monitoring. Snowflake documentation,
  undated.
  <https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst/admin-observability>
  Used for logging every request so the semantic model can be refined.
- <a id="source-42"></a>**[42]** Genie. Databricks documentation, undated.
  <https://docs.databricks.com/aws/en/genie/>
  Used for the Genie product family and its Genie Agents.
- <a id="source-43"></a>**[43]** Test and monitor a Genie Agent. Databricks documentation, 2026.
  <https://docs.databricks.com/aws/en/genie-agents/monitor>
  Used for benchmarks that compare results, and its own fiscal-calendar example.
- <a id="source-44"></a>**[44]** Curate an effective Genie Agent. Databricks documentation,
  undated. <https://docs.databricks.com/aws/en/genie/best-practices>
  Used for where business rules should live, few tables, value matching, and clarification rules.
- <a id="source-45"></a>**[45]** How to Build Production-Ready Genie Spaces, and Build Trust Along
  the Way. Pulkit Pareek and Eric Lind, Databricks, 2026.
  <https://www.databricks.com/blog/how-build-production-ready-genie-spaces-and-build-trust-along-way>
  Used for a benchmark written before development, kept out of the context, re-run on every change.
- <a id="source-46"></a>**[46]** Question-SQL Pairs. Wren AI documentation (Canner), undated.
  <https://docs.getwren.ai/oss/guide/knowledge/question-sql-pairs>
  Used for saved question and query pairs that a person checks by reading the query.
- <a id="source-47"></a>**[47]** Documentation (What is Vanna 2.0?). Vanna AI, undated.
  <https://vanna.ai/docs/>
  Used for a design that saves every successful interaction automatically, with no gate described.
- <a id="source-48"></a>**[48]** Golden SQLs. Dataherald AI documentation, undated.
  <https://dataherald.readthedocs.io/en/latest/api.golden_sql.html>
  Used for checked question and query samples placed in the prompt.
- <a id="source-49"></a>**[49]** QueryGPT – Natural Language to SQL Using Generative AI. Jeffrey
  Johnson, Callie Busch, Abhi Khune, Pradeep Chakka, Uber Engineering, 2024.
  <https://www.uber.com/blog/query-gpt/>
  Used for large schemas, intent routing, column pruning, a wrong filter that runs cleanly, and noise.

## The course's own evidence

These pages hold every course number the slides use, with its sample size and the runs behind it.

- <a id="source-50"></a>**[50]** Calibration report. ANI-IN, Loop Engineering, 2026.
  <https://github.com/ANI-IN/loop-engineering/blob/main/docs/calibration-report.md>
  Used for every measured run, experiment, and live session; in this repository,
  [the calibration report](calibration-report.md).
- <a id="source-51"></a>**[51]** Benefits. ANI-IN, Loop Engineering, 2026.
  <https://github.com/ANI-IN/loop-engineering/blob/main/docs/benefits.md>
  Used for each loop measured without and with its fix; in this repository,
  [the benefits page](benefits.md).
- <a id="source-52"></a>**[52]** Evidence. ANI-IN, Loop Engineering, 2026.
  <https://github.com/ANI-IN/loop-engineering/blob/main/docs/evidence.md>
  Used for the results and captures of each section; in this repository,
  [the evidence index](evidence.md).
- <a id="source-53"></a>**[53]** Costs. ANI-IN, Loop Engineering, 2026.
  <https://github.com/ANI-IN/loop-engineering/blob/main/docs/costs.md>
  Used for what each run and experiment costs, and the caps; in this repository,
  [the costs page](costs.md).
