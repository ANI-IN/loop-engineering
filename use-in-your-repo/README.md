# Module: Loop Engineering - Use it in your repository

How to take the four loops off Harbor & Pine's warehouse and onto your own data: point DataPilot at
your own Postgres, or build a new domain pack from the template.

## The problem

**Illustrative scenario.** A data platform team watches the class demos and wants the same loops
around its own analytics agent. On Monday someone opens the repository and finds Harbor & Pine
everywhere: the schema, the benchmark, the traps, the canary questions. Nobody can tell which
parts are the platform and which parts are the example. The work stalls before the first query.

> **Terms on this page**
>
> - **Domain pack**: The folder that holds one warehouse's settings, rules, benchmark, and knowledge.
> - **Trap**: A business rule the schema does not reveal, so a plausible query gets it wrong.
> - **Knowledge version**: A numbered set of business rules given to the agent in its prompt.
> - **Drift canary**: Three easy questions that must pass and two trap questions that must still fail.

## Why it happens

- A course project bundles the platform with one worked example, so the example looks like part
  of the platform.
- The hard part of a new domain is not code. It is writing down the business rules, the gold
  Structured Query Language (SQL) for each question, and the traps that make a naive query wrong:
  the knowledge a large language model (LLM) cannot read from the schema, which BIRD calls
  external knowledge ([BIRD](https://arxiv.org/abs/2305.03111)).
- The safety of the loops rests on settings that are easy to get wrong on a new database: a
  read-only role, one allowed schema, and the personal data columns.

## How this section fixes it

DataPilot keeps everything specific to one warehouse in a domain pack under `platform/packs/`. The
code reads the pack's `pack.yaml`, its benchmark, its knowledge versions, and its preflight checks.
One line in `.env`, `DATAPILOT_PACK`, selects the pack every process reads, and each pack keeps its
own knowledge versions. The template pack, `platform/packs/_template/`, is a complete small pack
with a worked example, Lantern Coffee Club: a schema and data file, four business rules, three
traps, a benchmark with both splits, the starting knowledge, a data check, and a canary.

A checker, `use-in-your-repo/check_pack.py`, reads a pack through the platform's own loaders and
contracts; `make check-pack PACK=<name>` runs it with the database. It runs every gold query on
both databases and proves each naive query gives a different answer. The guide uses the template
as the example for every step.

## How to work through this section

| Part | What it gives you | Time |
|---|---|---|
| [apply-to-your-repo.md](apply-to-your-repo.md), part 1 | The template running on the Compose Postgres, checked end to end | One sitting |
| [apply-to-your-repo.md](apply-to-your-repo.md), part 2 | Your own domain pack: rules, traps, benchmark, knowledge, canary | Depends on your domain |
| [apply-to-your-repo.md](apply-to-your-repo.md), part 3 | DataPilot pointed at your own Postgres, with a read-only role | One sitting |
| [`platform/packs/_template/`](../platform/packs/_template/README.md) | The template pack, with every file explained | Reference |
| [`check_pack.py`](check_pack.py) | The pack check, before any model call | Reference |

## Where next

- Start with part 1 of the [guide](apply-to-your-repo.md).
- Then the [final project](../final-project/README.md), which asks for your own pack, traps, and
  benchmark, and a before-and-after report.

## Sources

- Source 1: Can LLM Already Serve as A Database Interface? A BIg Bench for Large-Scale Database Grounded Text-to-SQLs, <https://arxiv.org/abs/2305.03111>, Jinyang Li et al., 2023-05-04
