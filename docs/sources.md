# Sources

Every verified outside source behind the course, with the course's own evidence pages at the end:
118 sources. The class slides and their speaker notes cite 82 of them, numbered as here, and the
rest support the course's pages. A slide marks a sourced claim with a small number, such as [16];
that number is the entry here. Many titles name Structured Query Language (SQL), a large language model
(LLM), artificial intelligence (AI), or an application programming interface (API).

Each entry gives the title, the authors or the organisation, the year (or "undated" when the page
carries no date), the full address, and what the course uses it for. Sources [1] to [54] were
opened and read on 26 October 2026, and [55] to [118], the named patterns and their equivalents in
other stacks, on 27 October 2026. The pages of the OWASP Gen AI Security Project, [66] to [69],
answered 200 on 27 October 2026, with every quote the course uses, but they may answer a script
with a browser check (403), which a link checker reports as refused. A benchmark figure keeps
the form its source publishes, with its condition; course numbers are counts and come from the
evidence pages in the last group.

## Agent design

- <a id="source-1"></a>**[1]** The Art of Loop Engineering. Sydney Runkle, LangChain, 2026.
  <https://www.langchain.com/blog/the-art-of-loop-engineering>
  Used for the four loops, the grader that sends failures back, and its cost in latency.
- <a id="source-2"></a>**[2]** Loop Engineering: Design systems that prompt your agents. Cobus
  Greyling, undated. <https://cobusgreyling.github.io/loop-engineering/>
  Used for the three autonomy levels and their drops: an incident to the assisted level, the kill
  switch to the report-only level.
- <a id="source-3"></a>**[3]** Building effective agents. Erik Schluntz and Barry Zhang,
  Anthropic, 2024. <https://www.anthropic.com/research/building-effective-agents>
  Used for starting simple and for tools designed so mistakes are hard to make.
- <a id="source-4"></a>**[4]** Writing effective tools for AI agents. Ken Aizawa, Anthropic, 2025.
  <https://www.anthropic.com/research/writing-tools-for-agents>
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
  <https://docs.cube.dev/docs/introduction>
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
  undated. <https://docs.databricks.com/aws/en/genie-agents/best-practices>
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
- <a id="source-49"></a>**[49]** QueryGPT: Natural Language to SQL Using Generative AI. Jeffrey
  Johnson, Callie Busch, Abhi Khune, Pradeep Chakka, Uber Engineering, 2024.
  <https://www.uber.com/blog/query-gpt/>
  Used for large schemas, intent routing, column pruning, a wrong filter that runs cleanly, and noise.

## Section 1: Agent loop, patterns and other stacks

- <a id="source-55"></a>**[55]** Function calling. OpenAI documentation, undated.
  <https://developers.openai.com/api/docs/guides/function-calling>
  Used for the agent loop as a conversation your code drives, tool definitions billed as input
  tokens, and keeping the tool set small.
- <a id="source-56"></a>**[56]** How tool use works. Anthropic documentation, undated.
  <https://platform.claude.com/docs/en/agents-and-tools/tool-use/how-tool-use-works>
  Used for each tool call as a round trip, and stop reasons the application must handle.
- <a id="source-57"></a>**[57]** Handle tool calls. Anthropic documentation, undated.
  <https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls>
  Used for instructive tool errors the model can recover from.
- <a id="source-58"></a>**[58]** Running agents (OpenAI Agents SDK documentation). OpenAI,
  undated. <https://openai.github.io/openai-agents-python/running_agents/>
  Used for the loop ending in code, a turn cap that raises an error, and a run stopped after a turn.
- <a id="source-59"></a>**[59]** Graph API overview. LangChain documentation, undated.
  <https://docs.langchain.com/oss/python/langgraph/graph-api>
  Used for the recursion limit as a stop condition, and checkpoints between steps.
- <a id="source-60"></a>**[60]** GRAPH_RECURSION_LIMIT. LangChain documentation, undated.
  <https://docs.langchain.com/oss/python/langgraph/errors/GRAPH_RECURSION_LIMIT>
  Used for the error a graph raises when it reaches its step limit before a stop condition.
- <a id="source-61"></a>**[61]** Effective context engineering for AI agents. Prithvi
  Rajasekaran, Ethan Dixon, Carly Ryan, Jeremy Hadfield, Anthropic, 2025.
  <https://www.anthropic.com/research/effective-context-engineering-for-ai-agents>
  Used for context as a finite budget, loading data just in time, progressive disclosure, and
  helper agents that return short summaries.
- <a id="source-62"></a>**[62]** Equipping agents for the real world with Agent Skills. Barry
  Zhang, Keith Lazuka, Mahesh Murag, Anthropic, 2025.
  <https://www.anthropic.com/research/equipping-agents-for-the-real-world-with-agent-skills>
  Used for progressive disclosure: names and descriptions first, the rest on demand.
- <a id="source-63"></a>**[63]** Introducing advanced tool use on the Claude Developer Platform.
  Bin Wu and others, Anthropic, 2025. <https://www.anthropic.com/research/advanced-tool-use>
  Used for finding tools on demand in a large catalogue; its saving is Anthropic's own example.
- <a id="source-64"></a>**[64]** Structured model outputs. OpenAI documentation, undated.
  <https://developers.openai.com/api/docs/guides/structured-outputs>
  Used for the answer envelope enforced by a schema, and refusals as a separate field.
- <a id="source-65"></a>**[65]** How we built our multi-agent research system. Jeremy Hadfield,
  Barry Zhang, Kenneth Lien, Florian Scholz, Jeremy Fox, Daniel Ford, Anthropic, 2025.
  <https://www.anthropic.com/research/multi-agent-research-system>
  Used for helper agents with their own context, their token cost in Anthropic's own system, and
  when they do not fit.

## Section 2: Verification loop, patterns and other stacks

- <a id="source-66"></a>**[66]** OWASP Top 10 for LLM Applications 2025. OWASP Gen AI Security
  Project, 2025. <https://genai.owasp.org/llm-top-10/>
  Used for the risk list: prompt injection, sensitive information disclosure, excessive agency.
- <a id="source-67"></a>**[67]** LLM01:2025 Prompt Injection. OWASP Gen AI Security Project,
  2025. <https://genai.owasp.org/llmrisk/llm01-prompt-injection/>
  Used for injection through data, no known fool-proof prevention, and the layered mitigations.
- <a id="source-68"></a>**[68]** LLM06:2025 Excessive Agency. OWASP Gen AI Security Project,
  2025. <https://genai.owasp.org/llmrisk/llm062025-excessive-agency/>
  Used for its database example of excess permission, and authorisation outside the model.
- <a id="source-69"></a>**[69]** LLM02:2025 Sensitive Information Disclosure. OWASP Gen AI
  Security Project, 2025.
  <https://genai.owasp.org/llmrisk/llm022025-sensitive-information-disclosure/>
  Used for one user receiving another user's personal data, and redaction by pattern matching as
  one mitigation.
- <a id="source-70"></a>**[70]** LLM Prompt Injection Prevention Cheat Sheet. OWASP Cheat Sheet
  Series, undated.
  <https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html>
  Used for a guardrail model as one layer of defence in depth, and tool output as untrusted input.
- <a id="source-71"></a>**[71]** defense-in-depth (glossary). NIST (National Institute of
  Standards and Technology) Computer Security Resource Center, undated.
  <https://csrc.nist.gov/glossary/term/defense_in_depth>
  Used for the definition of defence in depth; ordering the layers cheap to strong is the
  course's own rule.
- <a id="source-72"></a>**[72]** SQLGlot API documentation. Toby Mao and contributors, undated.
  <https://sqlglot.com/sqlglot.html>
  Used for parsing a query and walking its tree, and its warning that it is not a validator.
- <a id="source-73"></a>**[73]** WITH Queries (Common Table Expressions). PostgreSQL Global
  Development Group, undated. <https://www.postgresql.org/docs/current/queries-with.html>
  Used for writes inside a `WITH` clause, which a starts-with check passes.
- <a id="source-74"></a>**[74]** SET TRANSACTION. PostgreSQL Global Development Group, undated.
  <https://www.postgresql.org/docs/current/sql-set-transaction.html>
  Used for a read-only default that one transaction can override, as the documentation words it.
- <a id="source-75"></a>**[75]** Privileges. PostgreSQL Global Development Group, undated.
  <https://www.postgresql.org/docs/current/ddl-priv.html>
  Used for starting from nothing: a role can use an object only once it is granted.
- <a id="source-76"></a>**[76]** GRANT. PostgreSQL Global Development Group, undated.
  <https://www.postgresql.org/docs/current/sql-grant.html>
  Used for granting safe columns rather than revoking a personal column from a table grant.
- <a id="source-77"></a>**[77]** Overview of Access Control. Snowflake documentation, undated.
  <https://docs.snowflake.com/en/user-guide/security-access-control-overview>
  Used for roles and deny by default: unless a grant allows it, access is denied.
- <a id="source-78"></a>**[78]** Access control privileges. Snowflake documentation, undated.
  <https://docs.snowflake.com/en/user-guide/security-access-control-privileges>
  Used for the read privilege on tables, and the grant a schema's database also needs.
- <a id="source-79"></a>**[79]** BigQuery IAM roles and permissions. Google Cloud documentation,
  2026. <https://docs.cloud.google.com/bigquery/docs/access-control>
  Used for read access per dataset and running queries as a separate role; identity and access
  management (IAM) is Google Cloud's permission system.
- <a id="source-80"></a>**[80]** Not what you've signed up for: Compromising Real-World
  LLM-Integrated Applications with Indirect Prompt Injection. Kai Greshake, Sahar Abdelnabi,
  Shailesh Mishra, Christoph Endres, Thorsten Holz, Mario Fritz, 2023.
  <https://arxiv.org/abs/2302.12173>
  Used for the origin of indirect prompt injection: instructions placed in data a model reads.
- <a id="source-81"></a>**[81]** Prompt Shields in Azure AI Content Safety. Microsoft
  documentation, undated.
  <https://learn.microsoft.com/en-us/azure/ai-services/content-safety/concepts/jailbreak-detection>
  Used for a vendor's name for injection through documents, off by default.
- <a id="source-82"></a>**[82]** Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena. Lianmin
  Zheng and others, 2023. <https://arxiv.org/abs/2306.05685>
  Used for a model judge's position, verbosity, and self-enhancement biases, and its agreement
  with people.
- <a id="source-83"></a>**[83]** LLM Evaluators Recognize and Favor Their Own Generations. Arjun
  Panickssery, Samuel R. Bowman, Shi Feng, 2024. <https://arxiv.org/abs/2404.13076>
  Used for self-preference: a model judge scores its own outputs higher.
- <a id="source-84"></a>**[84]** Great Models Think Alike and this Undermines AI Oversight.
  Shashwat Goel and others, 2025. <https://arxiv.org/abs/2502.04313>
  Used for judges favouring similar models, and correlated mistakes: a general risk, not a study
  of SQL judges.
- <a id="source-85"></a>**[85]** Timeouts, retries, and backoff with jitter. Amazon Builders'
  Library, Amazon Web Services, 2019.
  <https://builder.aws.com/content/3EumjoZascWd1oZiEgL8ORlv3qE/timeouts-retries-and-backoff-with-jitter>
  Used for capping retries, retrying at one layer, and not retrying errors that cannot succeed.

## Section 3: Event loop, patterns and other stacks

- <a id="source-86"></a>**[86]** Idempotent requests. Stripe documentation, undated.
  <https://docs.stripe.com/api/idempotent_requests>
  Used for idempotency keys, a saved first response, and no personal data in keys; Stripe's keys
  are random per request, and keying by meaning is the course's own rule.
- <a id="source-87"></a>**[87]** Receive Stripe events in your webhook endpoint. Stripe
  documentation, undated. <https://docs.stripe.com/webhooks>
  Used for webhooks that arrive more than once and out of order, deduplicated by event id.
- <a id="source-88"></a>**[88]** Amazon SQS at-least-once delivery. Amazon Simple Queue Service
  Developer Guide, Amazon Web Services, undated.
  <https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/standard-queues-at-least-once-delivery.html>
  Used for designing handlers to be idempotent under at-least-once delivery.
- <a id="source-89"></a>**[89]** Amazon SQS visibility timeout. Amazon Simple Queue Service
  Developer Guide, Amazon Web Services, undated.
  <https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-visibility-timeout.html>
  Used for the lease in a managed queue, a heartbeat that extends it, and no exactly-once
  guarantee.
- <a id="source-90"></a>**[90]** Using dead-letter queues in Amazon SQS. Amazon Simple Queue
  Service Developer Guide, Amazon Web Services, undated.
  <https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html>
  Used for bounded redelivery before a message moves aside.
- <a id="source-91"></a>**[91]** Extend ack time with lease management. Google Cloud Pub/Sub
  documentation, 2026. <https://docs.cloud.google.com/pubsub/docs/lease-management>
  Used for the lease-length trade-off: duplicates against slow redelivery.
- <a id="source-92"></a>**[92]** Design (Message Delivery Semantics), Apache Kafka documentation,
  version 4.4. Apache Kafka, undated. <https://kafka.apache.org/44/design/design/>
  Used for at-least-once by default, idempotent updates by primary key, and exactly-once that
  needs the destination's cooperation.
- <a id="source-93"></a>**[93]** What is Temporal? Temporal Technologies, undated.
  <https://docs.temporal.io/temporal>
  Used for durable execution: a workflow keeps its state through crashes.
- <a id="source-94"></a>**[94]** Temporal Workflow Execution overview. Temporal Technologies,
  undated. <https://docs.temporal.io/workflow-execution>
  Used for resuming from the event history.
- <a id="source-95"></a>**[95]** Activity Definition. Temporal Technologies, undated.
  <https://docs.temporal.io/activity-definition>
  Used for activities that may run more than once, so they must be idempotent.
- <a id="source-96"></a>**[96]** Approval Pattern. Temporal Technologies, undated.
  <https://docs.temporal.io/design-patterns/approval>
  Used for a workflow that waits for a decision, with a timeout path.
- <a id="source-97"></a>**[97]** Temporal Workflow message passing (Signals, Queries and
  Updates). Temporal Technologies, undated.
  <https://docs.temporal.io/encyclopedia/workflow-message-passing>
  Used for signals as asynchronous writes, the way an approval reaches a waiting workflow.
- <a id="source-98"></a>**[98]** Interrupts. LangChain documentation, undated.
  <https://docs.langchain.com/oss/python/langgraph/interrupts>
  Used for a paused graph saved by its persistence layer, and a resumed node that runs again.
- <a id="source-99"></a>**[99]** Persistence. LangChain documentation, undated.
  <https://docs.langchain.com/oss/python/langgraph/persistence>
  Used for checkpointers that keep a thread's state for human approval and recovery.
- <a id="source-100"></a>**[100]** Practices for Governing Agentic AI Systems. Yonadav Shavit,
  Sandhini Agarwal, Miles Brundage and others, OpenAI, 2023.
  <https://cdn.openai.com/papers/practices-for-governing-agentic-ai-systems.pdf>
  Used for interruptibility as a critical backstop, human approval of important actions, and
  approval earned by reliability as an open question.
- <a id="source-101"></a>**[101]** Feature Toggles (aka Feature Flags). Pete Hodgson,
  martinfowler.com, 2017. <https://martinfowler.com/articles/feature-toggles.html>
  Used for operator switches that disable a feature in production; they shed load, they do not
  stop an agent.
- <a id="source-102"></a>**[102]** CircuitBreaker. Martin Fowler, 2014.
  <https://martinfowler.com/bliki/CircuitBreaker.html>
  Used for a switch that trips on repeated failures, the automatic cousin of a kill switch.
- <a id="source-103"></a>**[103]** Levels of Autonomy for AI Agents. K. J. Kevin Feng, David W.
  McDonald, Amy X. Zhang, 2025. <https://arxiv.org/abs/2506.12469>
  Used for five levels defined by the user's role, and autonomy as a design choice; placing the
  course's three levels on those roles is the course's reading, not the paper's: assisted maps to
  their approver role, unattended to their observer role.
- <a id="source-104"></a>**[104]** Principles of Chaos Engineering. The Chaos Community,
  principlesofchaos.org, 2019. <https://principlesofchaos.org/>
  Used for proving a system by injecting real faults against a steady state, contained.

## Section 4: Hill-climbing loop, patterns and other stacks

- <a id="source-105"></a>**[105]** Evaluation best practices. OpenAI documentation, undated.
  <https://developers.openai.com/api/docs/guides/evaluation-best-practices>
  Used for evaluation-driven development, evaluating on every change, and judge biases.
- <a id="source-106"></a>**[106]** Demystifying evals for AI agents. Mikaela Grace, Jeremy
  Hadfield, Rodrigo Olivares, Jiri De Jonghe, Anthropic, 2026.
  <https://www.anthropic.com/research/demystifying-evals-for-ai-agents>
  Used for a gold set started from real failures, regression evaluations, repeated trials, and
  grading the result rather than the path.
- <a id="source-107"></a>**[107]** Evaluation concepts (LangSmith documentation). LangChain,
  undated. <https://docs.langchain.com/langsmith/evaluation-concepts>
  Used for regression testing, and datasets with reference outputs.
- <a id="source-108"></a>**[108]** Manage datasets (LangSmith documentation). LangChain, undated.
  <https://docs.langchain.com/langsmith/manage-datasets>
  Used for dataset splits as a product feature.
- <a id="source-109"></a>**[109]** How to evaluate with repetitions (LangSmith documentation).
  LangChain, undated. <https://docs.langchain.com/langsmith/repetition>
  Used for repeated runs that reduce noise in agents.
- <a id="source-110"></a>**[110]** Datasets: Dividing the original dataset (Machine Learning
  Crash Course). Google for Developers, 2025.
  <https://developers.google.com/machine-learning/crash-course/overfitting/dividing-datasets>
  Used for test sets that wear out and get fitted when they are reused.
- <a id="source-111"></a>**[111]** Defeating Nondeterminism in LLM Inference. Horace He and
  others, Thinking Machines Lab, 2025.
  <https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/>
  Used for answers that differ from run to run even at temperature zero.
- <a id="source-112"></a>**[112]** Non-Determinism of "Deterministic" LLM Settings. Berk Atil and
  others, 2024. <https://arxiv.org/abs/2408.04667>
  Used for accuracy that varies across runs with the same settings.
- <a id="source-113"></a>**[113]** "When a Measure Becomes a Target, It Ceases to be a Good
  Measure". Christopher Mattson, Reamer L. Bushardt, Anthony R. Artino Jr., Journal of Graduate
  Medical Education, 2021. <https://pmc.ncbi.nlm.nih.gov/articles/PMC7901608/>
  Used for Strathern's phrasing of Goodhart's law, as a peer-reviewed source gives it.
- <a id="source-114"></a>**[114]** 'Improving ratings': audit in the British University system.
  Marilyn Strathern, European Review 5(3), pages 305 to 321, 1997.
  <https://www.cambridge.org/core/journals/european-review/article/abs/improving-ratings-audit-in-the-british-university-system/FC2EE640C0C44E3DB87C29FB666E9AAB>
  Used as the original of that phrasing; only its abstract is open.
- <a id="source-115"></a>**[115]** Categorizing Variants of Goodhart's Law. David Manheim, Scott
  Garrabrant, 2018. <https://arxiv.org/abs/1803.04585>
  Used for Goodhart's original wording, and the ways optimising a metric fails.
- <a id="source-116"></a>**[116]** MLOps: Continuous delivery and automation pipelines in machine
  learning. Google Cloud Architecture Center, 2024.
  <https://docs.cloud.google.com/architecture/mlops-continuous-delivery-and-automation-pipelines-in-machine-learning>
  Used for promoting a model only when it beats the current one, and monitoring for decay.
- <a id="source-117"></a>**[117]** Managing environments for deployment. GitHub documentation,
  undated.
  <https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments>
  Used for a deployment gate with required reviewers, a promotion gate in a mainstream tool.
- <a id="source-118"></a>**[118]** How is ChatGPT's behavior changing over time? Lingjiao Chen,
  Matei Zaharia, James Zou, 2023. <https://arxiv.org/abs/2307.09009>
  Used for one model's behaviour changing behind the same name, and the need to monitor.

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
