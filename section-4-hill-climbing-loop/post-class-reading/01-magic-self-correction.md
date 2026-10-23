# [MAGIC: Generating Self-Correction Guideline for In-Context Text-to-SQL](https://arxiv.org/abs/2406.12692) <!-- check-style: allow SC33 the source title is quoted as published -->

Reading time: about 40 minutes.
Source: Arian Askari, Christian Poelitz, and Xinye Tang (Leiden University, Microsoft), [MAGIC: Generating Self-Correction Guideline for In-Context Text-to-SQL](https://arxiv.org/abs/2406.12692), 2024-06-18.

> **Terms on this page**
>
> - **Analyzer team**: The failure analyst, the rule writer, and the critic, which turn failed dev items into a candidate knowledge version.
> - **Dev split**: The benchmark questions the analyzer team may learn from.
> - **Holdout split**: The benchmark questions the analyzer team never sees; the gate decides on them.

## Why it matters

DataPilot's analyzer team does what this paper does: it reads the failures of a large language
model (LLM) on training questions and writes guidance that prevents them. MAGIC is the clearest
published version of that idea, with three cooperating agents. Reading it shows both why the
pattern works and why Section 4: Hill-climbing loop puts a holdout gate after it.

## Three key ideas

1. **Hand-written correction rules do not scale.** Self-correction "commonly relies on manually
   crafted self-correction guidelines by human experts that are not only labor-intensive to
   produce but also limited by the human ability in identifying all potential error patterns".
   The rules behind a wrong number are exactly what experts forget to write down.

2. **Split the work across agents.** "MAGIC uses three specialized agents: a manager, a
   correction, and a feedback agent." They "collaborate on the failures of an LLM-based method on
   the training set to iteratively generate and refine a self-correction guideline". DataPilot's
   split is diagnosis, proposal, and criticism: the failure analyst, the rule writer, and the
   critic, which may keep, narrow, or drop a rule but never add one.

3. **Guidance is tailored to its training failures.** The method "automatically generates the
   self-correction guideline that is tailored to the mistakes of the initial system". Tailored is
   the strength and the risk: a rule that fits the training failures can fail elsewhere. That is
   why DataPilot's overfit guard rejects rules that copy a question, and why the gate decides on
   holdout questions the team never saw.

## Apply it to your repository

1. Collect ten failed answers of your agent, with the right answer for each.
2. Write a diagnosis for each one without proposing a fix. Notice how often two failures share a
   cause.
3. Write one general rule per shared cause, and test it on questions that were not in the ten.
4. Run `make demo NAME=improve-naive-analyzer-blocked` to see what happens when the critic and the
   guard are skipped.

## Sources

- Source 1: MAGIC: Generating Self-Correction Guideline for In-Context Text-to-SQL, <https://arxiv.org/abs/2406.12692>, Arian Askari et al., 2024-06-18
