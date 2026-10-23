# [Spider 2.0: Evaluating Language Models on Real-World Enterprise Text-to-SQL Workflows](https://arxiv.org/abs/2411.07763) <!-- check-style: allow SC33 the source title is quoted as published -->

Reading time: about 75 minutes.
Source: Fangyu Lei et al., [Spider 2.0: Evaluating Language Models on Real-World Enterprise Text-to-SQL Workflows](https://arxiv.org/abs/2411.07763), 2024-11-12.

> **Terms on this page**
>
> - **Agent loop**: The model calls tools, reads the results, and repeats until it answers.
> - **Schema scout**: A stateless helper agent that suggests tables and joins for a question.

## Why it matters

Harbor & Pine's warehouse is small on purpose, so every trap is visible in class. Yours is not.
Spider 2.0 measures agents on real enterprise databases and shows how much harder the agent loop
gets when the schema is large, spread across systems, and documented somewhere else. It is the
argument for spending effort on what the schema tools return, before adding rules or agents.

## Three key ideas

1. **Real schemas are huge.** The databases "are sourced from real data applications, often
   containing over 1,000 columns and stored in local or cloud database systems such as BigQuery
   and Snowflake". A tool that dumps every column into the context does not scale to that; a tool
   that lists tables, then describes one, does.

2. **The answer needs more than the schema.** Solving the tasks "frequently requires understanding
   and searching through database metadata, dialect documentation, and even project-level
   codebases". The knowledge an agent needs lives outside the tables, which is the same lesson as
   BIRD's external knowledge, at enterprise scale.

3. **Strong models still struggle.** The authors conclude that language models "require
   significant improvement in order to achieve adequate performance for real-world enterprise
   usage", even after strong results on earlier text-to-SQL benchmarks. A better model alone is not
   the fix; the loop around it is.

## Apply it to your repository

1. Count the tables and columns your agent's database role can see. If the answer is in the
   thousands, a describe-everything tool will not fit in the context.
2. List where your business definitions actually live: a wiki, a dbt project, a semantic layer.
   Each one is a candidate for a tool or for a knowledge version.
3. Decide whether a stateless helper, such as DataPilot's schema scout, earns its place: measure
   tokens and accuracy with it switched on and off (`agents.schema_scout.enabled` in `pack.yaml`).

## Sources

- Source 1: Spider 2.0: Evaluating Language Models on Real-World Enterprise Text-to-SQL Workflows, <https://arxiv.org/abs/2411.07763>, Fangyu Lei et al., 2024-11-12
