# [Can LLM Already Serve as A Database Interface? A BIg Bench for Large-Scale Database Grounded Text-to-SQLs](https://arxiv.org/abs/2305.03111) <!-- check-style: allow SC33 the source title is quoted as published -->

Reading time: about 65 minutes.
Source: Jinyang Li et al., [Can LLM Already Serve as A Database Interface? A BIg Bench for Large-Scale Database Grounded Text-to-SQLs](https://arxiv.org/abs/2305.03111), 2023-05-04.

> **Terms on this page**
>
> - **Trap**: A business rule the schema does not reveal, so a plausible query gets it wrong.
> - **Knowledge version**: A numbered set of business rules given to the agent in its prompt.
> - **Gold SQL**: The query an analyst wrote by hand that gives the right answer.

## Why it matters

BIRD is the benchmark that named the problem behind the spine question of this course. A large
language model (LLM) can write fluent Structured Query Language (SQL) and still get a business
number wrong, because the rule that defines the number is not in the schema. The paper calls that
missing rule external knowledge, and it hands the rule to the model as an "evidence" sentence.
DataPilot's knowledge versions are the same idea, learned and gated instead of hand-written.

## Three key ideas

1. **Values, not only schemas.** The authors build BIRD because earlier benchmarks "focus on
   database schema with few rows of database values". Real databases hold "dirty and noisy
   database values", and a model "must feature database value comprehension in addition to
   semantic parsing". This is why DataPilot's `describe_table` returns sample rows and distinct
   values, not only column names.

2. **External knowledge comes in kinds.** BIRD sorts the evidence it needs into four categories:
   numeric reasoning, domain knowledge, synonyms, and value illustration. Its domain example is a
   business analyst who "requires knowledge of financial indicators such as return on investment
   and net income". The Harbor & Pine traps map onto these kinds: net revenue is domain knowledge,
   and `status = 5` meaning cancelled is a value illustration.

3. **Evidence helps, but someone must write it.** "After being easily fed with the external
   knowledge evidence about the database values, all models have a clear improvement". In BIRD,
   experts annotated that evidence for each question. In your warehouse nobody has, which is the
   gap the hill-climbing loop fills, with holdout questions to check the rules generalize.

## Apply it to your repository

1. Pick one number your team reports every week. Write down every rule behind it that a new analyst
   could not read from the schema.
2. Sort those rules into BIRD's four kinds. The domain rules are the ones an agent will guess.
3. For each rule, write one question whose naive query gives a different answer than the gold SQL.
   Those questions are your first traps.
4. Compare with `platform/packs/datapilot_us/benchmark/business_rules.md`, where the six Harbor &
   Pine rules are written the same way.

## Sources

- Source 1: Can LLM Already Serve as A Database Interface? A BIg Bench for Large-Scale Database Grounded Text-to-SQLs, <https://arxiv.org/abs/2305.03111>, Jinyang Li et al., 2023-05-04
