# The template domain pack

A complete, small domain pack to copy for your own warehouse. Its worked example is Lantern Coffee
Club, a coffee subscription business with three traps. The step-by-step guide is
[use-in-your-repo/apply-to-your-repo.md](../../../use-in-your-repo/apply-to-your-repo.md); check a
pack with `make check-pack PACK=<pack>`, and select it with `DATAPILOT_PACK=<pack>` in `.env`.

| File | What it holds | What you change |
|---|---|---|
| `pack.yaml` | Every setting the platform reads: databases, models, limits, caps, evaluation, autonomy, preflight checks | The lines marked `YOURS` |
| `data/club.sql` | The example schema `club` and its rows, loaded with `psql -v variant=1` or `2` | Replace with your own data, or drop it when you use your own Postgres |
| `benchmark/business_rules.md` | The ground truth: four rules, three of them traps | Your rules, with an id for each trap |
| `benchmark/dev.yaml` | 6 questions the analyzer team may learn from, with gold and naive queries | Your dev questions |
| `benchmark/holdout.yaml` | 4 questions the analyzer team never sees; the gate decides on them | Your holdout questions, worded away from dev |
| `knowledge/v1.yaml` | The near-empty starting knowledge: the money rule only | Keep it as it is |

The three traps of the example:

- `refunds`: `payments.kind = 2` is a refund stored as a positive amount; net revenue subtracts it.
- `test_payments`: `payments.kind = 3` rows are test payments and never count.
- `pacific_time`: days and months are read in Pacific time; `paid_ts` is stored in UTC.

The data is computed from `generate_series`, so every load gives the same rows. The two variants
differ in the number of members, refunds, and test payments, so a naive query that matches gold on
one database by chance still fails on the other.
