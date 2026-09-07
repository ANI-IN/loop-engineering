# Five guards on one capability is a tell

**Written:** 2026-09-07, on removing the stored-measurement render path.

## The situation

The session's central claim is that every figure on screen was computed during the
session. The build defended that claim with five separate mechanisms, all guarding the
same thing — the ability to draw a cell that had been measured earlier:

1. a hatched fill, so a stored bar looked different
2. a `REFERENCE` badge in the row label
3. the measurement date printed beside every stored value
4. a four-way `--reference` mode flag (`auto` / `hide` / `fill` / `compare`) with a
   carefully reasoned default
5. a test running the chart entry point against an empty directory, asserting the
   output carried no `REFERENCE` row and no p-value

Each was well-argued. The mode flag's default had been changed once already, after a
fresh clone was found rendering twelve finished bars and a pre-registered p-value on a
machine that had never made an API call. The comment explaining that fix is three
paragraphs long and entirely correct.

## The tell

**If a property needs five mechanisms to hold, the property is not held by the
mechanisms. It is absent from the design.**

Every one of those five existed to make a capability safe. None of them removed the
capability. So the honest reading of the file is not "this is well defended" but "this
can still happen, and here are five reasons it probably will not this time".

The defended failure had already occurred once, which is what produced guard 4. That is
the shape of a system where the guards are load-bearing: they get added after the thing
they prevent has happened, and the next one gets added after the next time.

## What was done

The capability was removed. There is no stored-cell format, no loader, no flag, and no
hatching. These are all deleted and no longer in the repository:
`src/loopeng/sweep/reference.py`, `src/loopeng/views/exhibit.py`,
`tools/render_readme_charts.py`, `results/reference/`, `results/prefix_v1/` and
`assets/*.png`.

**A render path that cannot express "stored" cannot show one.** No test is needed for a
thing that has no code, so four of the five mechanisms deleted themselves and the fifth
became unnecessary.

The change was forced by something else — the model policy replaced both scoring models,
so every committed measurement described a system that no longer existed — but the
argument stands on its own and would have applied without it.

## The cost, stated

Removing the capability removed something real. A cloner could previously run their own
cells and see them beside the author's, with the difference computed by exact McNemar.
That was genuinely useful and it is gone.

It comes back as `reference/`: one full session run, committed, holding the JSONL, the
rendered PNGs and a summary table. The difference is structural rather than cosmetic —
**`reference/` is importable by nothing under `src/loopeng/`**, and a test asserts it.
It is documentation. It cannot reach a chart, because there is no longer a chart path
that could accept it.

## The generalisation

When counting the mechanisms that keep a property true, the count is the finding. One
mechanism is a design. Two is a design plus a check. Five is a capability nobody was
willing to delete.

The question to ask is not "are these guards sufficient" but "what would have to be
untrue for none of them to be needed".
