# Pre-delivery checklist

Run this **on the venue machine, at the venue, on the morning of**, in the order given.
Each step says what to do, what PASS looks like, and what to do when it fails.

Nothing here can be done from a development machine. That is why it is a checklist and
not a test.

Budget about **forty minutes** for a–e, plus the length of one dry run for f.

---

## 0) FIRST ACTION OF THE DAY, BEFORE THE LIVE SESSION

**Clear the sweep cells.**

```bash
rm -rf results/sweep results/ablation
```

**This is the single most damaging mistake available on the day.** The dry run leaves
completed cells on disk deliberately (see step g) — they are the outage insurance. But
the *live* sweep resumes from exactly those files. Leave them there and the DIAL chart
finishes instantly, rendering complete numbers to a room you have just told that nothing
is precomputed. It looks like a lie because it is indistinguishable from one.

**There is a guard, and the live command uses it.** Stage 3's command carries `--fresh`,
which refuses to start when completed cells exist rather than deleting them — the files
might still be your outage insurance, and only you know whether you still need them.

```bash
# THE LIVE COMMAND for stage 3
uv run python demos/04_hill_climbing_loop/sweep.py --profile delivery --fresh
```

**PASS** — the sweep starts from nothing and the DIAL chart fills while you talk.

**IF IT REFUSES** — it is telling you the cells are still there. Decide whether you still
want them for outage cover; if not, `rm -rf results/sweep` and re-run. Do not remove
`--fresh` to get past it.

---

## a) Cold start on the venue machine

**Do**

```bash
git clone https://github.com/ANI-IN/loop-engineering-workshop.git && cd loop-engineering-workshop
uv sync
uv run pytest -q          # offline suite: no network, no keys, no cost
uv run ruff check .
uv run python tools/lint_no_numbers.py
```

**PASS** — full suite green, lint clean, in about half a minute. The live tests report
as *deselected*, not as failures.

**IF IT FAILS**

- **`EnvironmentUnsafe` from `env_guard`** — this is a **path problem, not a code
  problem**. The guard exists because iCloud Drive silently evicts files and breaks
  imports. Move the checkout somewhere iCloud does not sync (`~/dev/`, not
  `~/Documents/` or `~/Desktop/`) and re-run. **Do not disable the guard.**
- **Import errors after `uv sync`** — confirm Python 3.12 with `uv run python -V`. The
  lock file pins everything else.
- **Anything else red** — stop and read it. A red suite on the venue machine before the
  session is the cheapest failure available today. Do not proceed to (b) hoping it is
  unrelated.

---

## b) Re-run the rate-limit probe

Phase 3 reads its per-model concurrency from `results/gate0.json`. **Those ceilings hold
for one account on one tier**, and neither is guaranteed to be what you are using here.

**Do**

```bash
uv run pytest tests/live/test_registry_live.py -m live -q
uv run python -c "
from loopeng.probes import probe_rate_limits
import json; print(json.dumps(probe_rate_limits(), indent=2))"
```

One call per model, headers only. **Never loop toward a 429** — provoking a rate limit
costs money, poisons the pool for the sweep, and tells you nothing the headers do not.

**PASS** — both models accept their request kwargs, and the `anthropic-ratelimit-*`
ceilings are at or above what `results/gate0.json` recorded.

**IF IT FAILS**

- **A 400 on either model** — the registry's `request_kwargs` are wrong for this
  account. Haiku is pinned to `temperature=0`; Sonnet must send no sampling parameters
  at all. Fix `registry.py`, not the test.
- **Ceiling lower than `gate0.json`** — lower `CONCURRENCY_PER_MODEL` in
  `src/loopeng/sweep/runner.py` **before** the sweep, not after it starts throwing 429s
  in front of people. The sweep will take longer. **Say so out loud when it does**,
  rather than letting a slow chart look broken.

---

## b2) Confirm the README images are current

Only needed if `results/reference/` changed since the last push. The images are generated
and a test asserts the committed ones match what the renderer produces.

```bash
uv run python tools/render_readme_charts.py
git status --short assets/          # must print nothing
```

**PASS** — the renderer runs and `git status` is silent, meaning the committed images are
byte-identical to a fresh render.

**IF IT SHOWS CHANGES** — the committed images are stale. Commit the regenerated ones.
Never hand-edit anything in `assets/`; it is the only directory in this repository whose
entire contents are written by a tool.

---

## c) Launch with a share link

**Do**

```bash
uv run python -u demos/views.py --view agent --share
```

**The `-u` is not optional if you redirect output.** Without it stdout is block-buffered
and the share URL never reaches the log — during the build that looked exactly like a
tunnel failure and was not one.

**PASS** — a `https://<...>.gradio.live` URL printed, plus the LAN URL, plus a QR
written to `results/share_qr.png`.

**Write the URL down here on the day. Never put it on a slide.** Gradio reports it as
*temporary, up to one week, best effort*: it is generated fresh at every delivery, and
a printed one will be dead.

**IF IT FAILS**

- **No URL after two minutes** — check `~/.cache/huggingface/gradio/frpc/` for the
  binary. Absent means the download was blocked. Present but not executable: `chmod +x`.
  Quarantined by macOS: `xattr -d com.apple.quarantine <path>`. Gatekeeper blocks fail
  silently rather than erroring, so check rather than assume.
- **Still nothing** — proceed. Step (d) decides whether the LAN path is enough.

---

## d) Reach it from a phone — both paths

**Do**

1. Share URL from a phone **on cellular data**, wifi off.
2. LAN URL from a phone **on the venue wifi**.

Same-network success proves nothing about what the room will experience, which is why
the first test is on cellular.

**PASS** — at least one path loads the AGENT view and can submit a question to the queue.

**IF IT FAILS**

- **LAN fails, share works** — normal. **Many conference APs enable client isolation**,
  which blocks phone-to-laptop traffic. Use the share QR.
- **Both fail** — stage 3 is narrated the third way, written down in
  `demos/03_event_driven_loop/README.md`, and **it is not an apology**: questions are
  shouted from the room and typed by **someone who is not you**. The teaching point is
  that nobody is watching the *worker* — how a row reached the queue is irrelevant to
  that. Say what happened plainly. **Do not type it yourself and narrate it as though
  the room submitted it.**

**Record which paths survived.** That decides how stage 3 is narrated, and it is the one
thing here you cannot decide later.

---

## e) Projector legibility, from the back of the room

**Treat this as a real test.** It is the check that would have caught the projector CSS
being defined and never applied — a defect that passed every code review and every unit
test, and would have been obvious to anyone standing at the back.

**Do** — put each on the projector and **walk to the back row**:

- [ ] AGENT · TRAP · VERIFY · DIAL · OVERSIGHT
- [ ] the **event-driven terminal**, both windows. It is not a "view" so it gets missed;
      set the font large **before** the session, not during it.

**PASS** — from the back row you can read:

- the `computed HH:MM today · n=NN` stamp
- the interval inside `±`
- the **LIVE** and **REFERENCE** badges on DIAL, **as text** — colour alone must not be
  load-bearing, for the projector's sake as much as for anyone's eyes

**IF IT FAILS** — raise the sizes in `PROJECTOR_CSS` in `src/loopeng/views/chrome.py`
and relaunch. If a number is unreadable from the back it is decoration: either make it
legible or stop pointing at it.

---

## f) Full timed dry run

**Do**

```bash
uv run python demos/04_hill_climbing_loop/sweep.py --profile delivery
uv run python demos/views.py --view dial
```

Then run the whole session end to end, timed, on the venue network.

**PASS**

- the projected cost prints before the first cell and sits under the cap
- the sweep completes in roughly the time it took on development
- the whole session fits the slot with room to spare
- actual spend lands under the delivery cap

**IF IT FAILS**

- **Sweep aborts on projected spend** — the cap did its job **before** spending. Report
  the last completed cell and **stop. Do not retry into the cap.** Charts render what
  completed; missing cells show *not yet measured*, which is honest.
- **Sweep much slower than development** — almost always the venue network. Say so. The
  pre-registration is what the wait is for, so read it while the cells land. If you run
  out of pre-registration, talk about the cost cap and the fact that it aborts on
  *projected* rather than actual spend.
- **Model API unreachable** — know this before minute forty, not during it:

  | stage | survives an API outage? |
  |---|---|
  | 0 · warehouse, gold set, schema | **yes** — entirely local |
  | 1 · AGENT, live question | no |
  | 1 · TRAP, fresh run | no — but a trap run **earlier today** can be re-shown from `results/` |
  | 2 · VERIFY, rule-surface probes | **yes** — offline and free |
  | 2 · VERIFY, live loop | no |
  | 3 · event-driven worker | no |
  | 4 · DIAL, OVERSIGHT | **yes, if the sweep ran earlier** — both read `results/` |

  So: **run the delivery sweep during (f) and leave `results/` in place.** That single
  act turns a total API outage from "the session is over" into "stages 0, the Phase 2
  probes, and stage 4 still run". Decide it now, not then.

- **Anything makes you fill silence** — note it. Start it earlier next time, or cut it.

**Record final spend after the dry run.** It comes out of *your* budget, not the
session's: the grid budget is paid fresh per delivery.

---

## g) After the dry run: leave the cells, confirm they are untracked

The dry run's sweep cells are the outage insurance. **Do not delete them now** — step 0
of the live session is when they go.

**Do**

```bash
ls results/sweep/*.json | wc -l     # cells present on disk
git status --short                  # must print nothing
```

**PASS** — cell files exist on disk **and** `git status` is silent.

**Why both.** The files must be present, because they are what keeps stages 0, the
Phase 2 probes and stage 4 alive through an API outage. They must be untracked, because
a committed cell would arrive on every future clone and make the *first* live sweep on a
fresh machine resume-and-complete instantly — the same failure as step 0, but shipped
rather than left behind.

**IF `git status` SHOWS THEM** — `.gitignore` is wrong. Fix it before pushing anything.
The DIAL-renders-nothing test in the release checklist exists to catch exactly this.

---

## Already verified — do not redo

Kept short so the list above stays usable under time pressure.

- two simultaneous browser sessions, no state leakage (tested interleaved)
- no module-level mutable state in any view; every view uses `gr.State`
- `default_concurrency_limit` explicit, queue bounded
- Gradio analytics disabled — launch makes no outbound telemetry call
- sweep detaches and returns the terminal
- sweep resumes from `results/` after a mid-cell kill, with no duplicates
- sweep self-aborts on projected spend before spending anything
- progressive rendering mid-sweep, interval narrowing as items land
- all ten demo entry points cold-start from an empty working directory
