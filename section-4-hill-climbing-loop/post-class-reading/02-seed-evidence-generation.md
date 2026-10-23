# [SEED: Enhancing Text-to-SQL Performance and Practical Usability Through Automatic Evidence Generation](https://arxiv.org/abs/2506.07423) <!-- check-style: allow SC33 the source title is quoted as published -->

Reading time: about 30 minutes.
Source: Janghyeon Yun et al., [SEED: Enhancing Text-to-SQL Performance and Practical Usability Through Automatic Evidence Generation](https://arxiv.org/abs/2506.07423), 2025-06-09.

> **Terms on this page**
>
> - **Knowledge version**: A numbered set of business rules given to the agent in its prompt.
> - **Promotion gate**: The check that a new knowledge version must pass before it becomes active.

## Why it matters

The BIRD benchmark hands the model an evidence sentence with every question. In a real warehouse
nobody writes those sentences, so someone or something must. SEED generates the evidence
automatically from the schema, descriptions, and values. It also shows that hand-written evidence
has defects, which is the case for treating every knowledge version as a candidate that must pass
a gate, whoever wrote it.

## Three key ideas

1. **Evidence assumes an expert.** BIRD "assumes that evidence is provided along with questions",
   which "assumes that users have expertise and domain knowledge, contradicting the fundamental
   goal of text-to-SQL". The person asking for net revenue does not know that status 5 means
   cancelled.

2. **Human evidence has defects.** "Human-generated evidence in BIRD contains defects, including
   missing or erroneous evidence, which affects model performance." The authors corrected a set
   of erroneous pairs by hand and conclude that "erroneous evidence can significantly degrade
   performance". A wrong rule is worse than no rule.

3. **Generate evidence from what the database already holds.** SEED "systematically analyzes
   database schema, description files, and values to extract relevant information". DataPilot's
   analyzer team learns from failed dev questions instead, but the lesson is shared: generated
   knowledge is a proposal, and it has to be measured before it is trusted.

## Apply it to your repository

1. Write down where your team's business definitions live today, and who keeps them up to date.
2. Pick three definitions and check each against the data with one query. Count how many are
   still true.
3. Treat any rule you add to an agent's prompt as a new version: run it on questions it was not
   written from, and compare with the version before.
4. Compare with the over-broad version, `platform/packs/datapilot_us/knowledge/v2-overbroad.yaml`:
   one plausible rule that the gate blocks.

## Sources

- Source 1: SEED: Enhancing Text-to-SQL Performance and Practical Usability Through Automatic Evidence Generation, <https://arxiv.org/abs/2506.07423>, Janghyeon Yun et al., 2025-06-09
