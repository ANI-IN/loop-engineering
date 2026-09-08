# What one full run produced

**Measured 2026-09-08** · models agent=gpt-5.6-luna, judge=claude-haiku-4-5, reference=gpt-6-astra · n=60 held out · account tier: OpenAI paid tier, single account, concurrency 6-8

Dress rehearsal: all six arms plus the session sweep, run end to end on the presenting machine. Nothing here was hand-edited.

| arm | model | level | loops | n | correct | silent | visible | abstained | unearned | est. cost |
|---|---|---|---|---|---|---|---|---|---|---|
| `trap-agent-L0` | gpt-5.6-luna | L0 | none — single shot | 60 | 8 | 42 | 6 | 0 | 4 | est. $0.0134 |
| `A-baseline` | gpt-5.6-luna | L3 | none — single shot | 60 | 48 | 6 | 6 | 0 | 0 | est. $0.0174 |
| `B-retry` | gpt-5.6-luna | L3 | L1 only | 60 | 47 | 7 | 6 | 0 | 0 | est. $0.0174 |
| `C-verified` | gpt-5.6-luna | L3 | L1 + L2 | 60 | 53 | 1 | 6 | 0 | 0 | est. $0.0186 |
| `D-reference` | gpt-6-astra | L3 | none — single shot | 60 | 60 | 0 | 0 | 0 | 0 | est. $0.7887 |
| `trap-reference-L0` | gpt-6-astra | L0 | none — single shot | 60 | 8 | 28 | 6 | 18 | 0 | est. $0.9965 |

## The named secondary

```
APPROACHED BUT SHORT. The frontier model bare was ahead of the budget model bare (6 items to 0), and with the loops the budget model did not catch it.
BY ACCURACY, over all 60 items: 53 correct against 60 — a gap of 7.
DECOMPOSED, over the 54 items BOTH arms answered: the deficit is 1 discordant (0 to 1). The other 6 are items the looped arm did not answer at all — it declined, or failed visibly. That is a different failure from being wrong: an arm wrong on 1 and visibly failing on 6 is not an arm quietly wrong on 7, and only one of those categories is what this session is about.
No p-value: this compares two models, and that refusal is in code.
```
