# DataPilot console design

The console is a Streamlit app shared over Zoom at 1280x720 to engineers who already know
LangChain, LangGraph, and LangSmith. It has one job in class: make each loop's state change visible
within 2 seconds, and make the reason for every block or failure readable from the back of a Zoom
gallery. It is not a product dashboard. Every element must earn its place in a demo.

The direction is the flight deck (approved at the design review, Direction A, with the
amber correction). The metaphor sets the layout and a few words ("Holding for approval",
"cleared"); it never adds pictures, gauges, or decoration. Plain verbs win wherever the metaphor
would hide the meaning.

Status: approved by the owner, with the changes of the approval round applied (browser-formatted
times, the fit at 1280x720, the business date, the grouped benchmark strip, configurable limits,
sentence-case chips, and samples that use only real columns). The style tile is
`design/style_tile.py`, run with `make style-tile`.

## 1. Tokens

Light theme on purpose: a light ground keeps its contrast through Zoom's compression of large dark
areas, and it avoids the banned "near-black with neon". There is no dark variant.

| Token | Hex | Role | Streamlit theme key |
|---|---|---|---|
| chart-paper | `#EDF1F3` | App background | `backgroundColor`, dataframe header |
| strip-white | `#FBFCFC` | Strips, panels, inputs, code | `secondaryBackgroundColor`, `codeBackgroundColor` |
| ink | `#17283A` | Text, 2 px rules, strip borders | `textColor` |
| graphite | `#5B6B79` | Secondary text, idle and "not run" states | `grayColor`, `grayTextColor` |
| rule | `#7D8B97` | Native widget borders (3:1 minimum for controls) | `borderColor` |
| hairline | `#C9D1D7` | Table grid lines only; never the only separator | `dataframeBorderColor` |
| airspace-magenta | `#9E2F6E` | The only accent: focus ring, selection, primary action, links | `primaryColor`, `linkColor`, `violetColor` |
| cleared-green | `#2E7A57` | Passed, cleared, posted | `greenColor`, `greenTextColor` |
| holding-amber | `#B7791F` | Holding: fills and edges only, never text | `yellowColor`, `orangeColor` |
| holding-amber-text | `#8A5A12` | Amber words | `yellowTextColor`, `orangeTextColor` |
| fault-red | `#B13A30` | Failed, blocked, regression, the kill switch | `redColor`, `redTextColor` |
| info-slate | `#3D5A73` | Neutral notices (`st.info`) | `blueColor`, `blueTextColor` |
| cleared-tint | `#E9F3EE` | Background behind green words | `greenBackgroundColor` |
| holding-tint | `#F7EFE1` | Background behind amber words | `yellowBackgroundColor`, `orangeBackgroundColor` |
| fault-tint | `#F9EAE8` | Error notices, trap marks in SQL | `redBackgroundColor` |
| magenta-tint | `#F7EAF1` | Selected segment, change highlight | `violetBackgroundColor` |
| info-tint | `#EAF0F5` | Behind `st.info` | `blueBackgroundColor` |
| gray-tint | `#E8ECEF` | Behind gray badges | `grayBackgroundColor` |
| chart-teal | `#2D6E7E` | Third chart series only | `chartCategoricalColors[2]` |

Chart series, in order: ink, airspace-magenta, chart-teal, graphite. Charts never use green, amber,
or red for a category, because those three mean a status.

### Contrast

Computed with the WCAG 2.x relative-luminance formula (4.5:1 for text, 3:1 for large text and for
control borders). The "measured" column comes from the style tile in Chromium: a script walked every
visible text element (including the components' shadow roots), read the computed text colour and
the first opaque background behind it, and computed the ratio. "Not rendered" means the pair is
allowed by the rules but does not appear in the style tile.

| Text | Background | Computed | Measured in the style tile | Use |
|---|---|---|---|---|
| ink | chart-paper | 13.19 | 13.19 | Body text |
| ink | strip-white | 14.58 | 14.58 | Strip and panel text, live stamps (14 px) |
| graphite | chart-paper | 4.83 | 4.83 (16 px and up) | Secondary text, "No runs" |
| graphite | strip-white | 5.34 | 5.34 (16 px and up) | Field names on strips |
| airspace-magenta | chart-paper | 5.99 | 5.99 | Links, selected segment |
| airspace-magenta | strip-white | 6.62 | 6.62 | Trace links on strips (14 px bold) |
| cleared-green | chart-paper | 4.58 | 4.58 | Checklist "Passed" |
| cleared-green | strip-white | 5.06 | 5.06 | "Posted", "revenue" cleared |
| holding-amber-text | strip-white | 5.75 | 5.75 | "Holding for approval" |
| holding-amber-text | chart-paper | 5.20 | not rendered | Amber words on the page |
| fault-red | chart-paper | 5.25 | 5.25 | "Failed", "Mismatch" |
| fault-red | strip-white | 5.81 | 5.81 | "Kill switch", "Regression" |
| fault-red | fault-tint | 5.11 | 5.11 | `st.error` text |
| white | fault-red | 5.97 | 5.97 (14 px tags) | Armed kill switch, trap numbers |
| white | airspace-magenta | 6.81 | 6.81 | Primary buttons, "Review" |
| white | cleared-green | 5.20 | not rendered | Reserved |
| cleared-green | cleared-tint | 4.59 | not rendered | `st.success` |
| holding-amber-text | holding-tint | 5.18 | not rendered | `st.warning` |
| info-slate | info-tint | 6.29 | not rendered | `st.info` |
| graphite | gray-tint | 4.62 | not rendered | Gray badges |
| graphite | magenta-tint | 4.71 | not rendered | Text in a selected segment |
| ink | holding-amber | 4.12 | none (rule: no text on amber) | Forbidden as text |
| holding-amber | chart-paper | 3.20 | none (fill only) | Edges and gauge fill, 3:1 as an interface part |
| rule | chart-paper | 3.07 | not text | Control borders, 3:1 minimum |
| hairline | chart-paper | 1.36 | not text | Table grid lines; decoration only |

The lowest measured text pair in the whole style tile is 4.58:1 (cleared-green on chart-paper, at
18 px). Every measured text pair passes 4.5:1.

### Status is a word and a shape, never colour alone

| Status | Word | Shape |
|---|---|---|
| Queued, received | "Queued", "Received" | Dashed ink edge |
| Running | "Running" | Solid ink edge |
| Verifying | "Verifying" | Double edge (two ink bars) |
| Holding for approval | "Holding for approval" | Amber filled edge |
| Answered, posted | "Answered", "Posted" | Green filled edge |
| Rejected, failed, escalated, blocked by budget, blocked by kill switch | The status in words (the bay title off the board) | Red edge struck through with a diagonal |
| Passed / failed (checklist, ledger cell) | "Passed" / "Failed" | Filled square / struck square |
| Not run | "Not run", "Not run yet" | Hollow square |
| Cleared / not cleared / suspended | the family name / "Not cleared: ..." / "revenue: suspended" | Filled / hollow / hollow square |
| Regression | "Regression" | Red struck edge and a red border on the row |
| Fixed | "Fixed: now passes" | Green edge |

Magenta is never a status. It marks focus, selection, the primary action, and links.

## 2. Type

All fonts are self-hosted under `static/fonts/` (SIL Open Font License; license texts beside the
files) and wired through `[[theme.fontFaces]]`, so the console works offline.

- **Atkinson Hyperlegible Next** 400 and 700 for every label, heading, number, and sentence.
- **Atkinson Hyperlegible Mono** 400 only for SQL, tool names, item ids, and the token counter.
  Never for ordinary labels.
- Tabular figures for every number (`font-variant-numeric: tabular-nums` in the components).

| Role | Size | Weight | Where |
|---|---|---|---|
| Page title | 26 px | 700 | `st.title` (`headingFontSizes[0]`) |
| Section label | 20 px | 700 | `st.header` |
| Sub-label | 18 px | 700 | `st.subheader` |
| Body | 18 px | 400 | `baseFontSize = 18` |
| Status line, lane titles, strip text | 16 px | 400 and 700 | the status line, run board, ledger runs |
| Code and SQL | 16 px | 400 | `codeFontSize`, annotated SQL |
| Live stamp on strips and bays | 14 px | 400, link 700 | "Started 11:59:09. Open trace" on one line |
| Trap number tags | 14 px | 700 | annotated SQL |

Nothing under 14 px. Sentence case everywhere. Why 14 px for the strip stamp: the line must fit on
one line in a lane. At 16 px "Started 11:59:09. Open trace" measures 211 px, at 14 px 188 px, and a
lane at 1280x720 is 220 px wide including its own borders and padding (26 px), so only 14 px fits.

## 3. Space, radius, borders, elevation

- Spacing steps: 2, 4, 8, 12, 16, 24 px. Strips stack with 4 px gaps; sections use Streamlit's own
  block spacing.
- Radius: **square** strips, rows, lanes, notes, and panels (0). **2 px** on controls (buttons,
  inputs, segmented controls), set by `baseRadius` and `buttonRadius`. Streamlit applies the same
  2 px to its own containers (alerts, code blocks, the dialog); that is the nearest it allows.
- Borders: 2 px ink on strips, lanes, and panels, because 1 px lines vanish in Zoom's compression.
  The state edge is the strip's 6 px left border; the status line and notes also use 6 px.
- **No shadows and no gradients.** Separation comes from rules and edges, not from fill
  differences (chart-paper and strip-white are only 1.1:1 apart).

## 4. The signature element: the flight strip

One low, square strip per run: a state edge on the left, the status word in bold, the question
(two lines at most), the current step or reason (one line), and the live stamp with its trace link
on one line. The same object appears on the run board, as the rows of the holdout ledger, and as
the frame of the status line, so learners track one shape across all four loops.

```text
+-+--------------------------------+
|#| Holding for approval           |   word: 16 px bold, in the state's text colour
|#| Export the California          |   question: 16 px, 2 lines, then an ellipsis
|#| customers who may receive...   |
|#| 412 rows of personal data      |   step or reason: 16 px graphite, 1 line
|#| Started 11:59:09. Open trace   |   live stamp: 14 px ink, link 14 px magenta bold, 1 line
|#| [ Review ]                     |   only when holding for approval
+-+--------------------------------+
 edge: 6 px amber (holding)
```

**The grouped benchmark strip.** Benchmark runs never appear as individual strips. Each running
benchmark is one strip in the Running lane: "Running", "Baseline benchmark: 41 of 70 runs done", a
thin ink progress bar, the stamp, and one button, "Show holdout ledger". The button expands the
live holdout ledger right under the board, where items fill in as their runs finish ("Not run
yet" until then); "Hide holdout ledger" closes it. When every run is done the strip moves to Done.

## 5. Live-only rules (owner decisions)

These follow `datapilot.contracts.live` and apply to every page.

1. **Times are formatted in the browser.** Services run in Docker on universal time, so the server
   never formats a time and never writes "local time" into a label. Components receive UTC ISO
   strings (`LiveStamp.to_browser()`, `LiveSession.to_browser()`: `started_at_utc`) and format them
   with `Intl.DateTimeFormat` in the viewer's time zone, 24-hour clock. When
   `DATAPILOT_DISPLAY_TIMEZONE` is set, the page passes it in the data as `display_tz` and the
   components format in that zone instead.
2. **Say it once.** The status line says "Times are in your local time" (or "Times are in
   America/New_York" when the display zone is set). No other label repeats it.
3. **Live stamp on every demo result**, on one line: "Started 11:59:09. Open trace". It is a field
   inside the flight strip, the ledger, and the annotated SQL header ("Open trace in LangSmith"),
   never a badge.
4. **Session indicator.** The status line shows "Session started 13:58" from the open session's
   `started_at_utc`. With no open session it says, in fault-red bold, "No live session. Run make
   preflight to start one." Sessions start only through `make preflight`; the console never starts
   one.
5. **Business date.** The status line shows "Business date: 31 January 2026"
   (`datapilot.business_date.status_label()`), so nobody reads the previous day against the wall clock.
6. **Only this session's runs.** The run board, the Agent and Verify results, and the ledger show
   only runs whose `session_id` is the open live session. With no session, the board shows the same
   sentence as the status line above empty lanes.
7. **Same-session baseline.** The Improve page accepts only a baseline experiment started in the
   open session. With none (`NoLiveBaseline`) it says "No baseline run in this session yet." and
   offers one action, "Run the baseline experiment". It never shows an older run.
8. **No comparison view.** The candidate experiment shows the live holdout ledger, then one link to
   the LangSmith trace list filtered by knowledge version ("Open every v2 trace in LangSmith,
   filtered by knowledge version. Experiment runs are traced as a sample: about 1 run in 5."). There
   is no LangSmith experiment-comparison view anywhere. Benchmark runs are traced as a sample
   (`tracing.experiment_sample_rate`), so a row none of whose runs was traced shows "Not traced" in
   the trace column (its tooltip: "Not traced: experiment runs are traced as a sample"), never a
   broken link; a row still running keeps the blank "Trace pending".
9. **Caching.** Console code may use `st.cache_resource` for connections and pools, and
   `st.cache_data` for small reads that are not model or evaluation results. It never caches an
   answer, a verdict, a proposal, or an experiment result.

**Rehearsal check: the console's clock.** At each rehearsal, before the first demo, compare the
session start time in the status line, and the stamp on the first strip, with the instructor's
own clock. They must match to the minute. If they are off by whole hours, the browser's time zone
is wrong: set `DATAPILOT_DISPLAY_TIMEZONE` to the instructor's zone (for example
`America/New_York`), restart the console, and check again.

## 6. Configurable limits

Read from `platform/packs/datapilot_us/pack.yaml`, `console:`; never hard-coded in a page or a
component.

| Key | Value | Used for |
|---|---|---|
| `kill_switch_disarm_seconds` | 5 | An armed kill switch disarms after this many seconds |
| `strips_per_lane` | 2 | Visible strips per lane, newest first; then "N more" |
| `poll_seconds` | 1 | The live fragment's `run_every`; never faster |

Off the board, each bay shows only its newest strip, then "N more".

## 7. Fit at 1280x720

Without scrolling, the Events page shows the status line, all five lanes, and the off-the-board
row, at 1280x720 and at 67 percent browser zoom, with Streamlit 1.65.0's header space (the status
line starts 108 px down) still present.

Rules that make it fit:

- Lanes size to their content, not to a fixed height. An empty lane collapses to its title and one
  line, "No runs".
- At most `strips_per_lane` strips per lane, then "N more"; one strip per bay off the board.
- The strip text is 16 px, the stamp 14 px on one line, the step one line, the question two lines.
- The status line is three rows at 16 px: identity, autonomy, and clearance; session, business
  date, token budget, and the kill switch; planted chips and the time-zone note. The kill switch
  message adds a fourth row only while armed or engaged. A notice row, the api notice or the
  class-day safeguard notice, is added only while it applies.
- No heading between the status line and the board; the navigation names the page.
- The grouped benchmark strip expands its ledger below the board only when asked.

Measured in the style tile (its first screen is the Events view), Chromium, Streamlit 1.65.0:

| Size and state | Status line (top to bottom) | Lanes end | Off-the-board row ends | Viewport height | Fits | Visible strips per lane | Stamps overflowing their strip |
|---|---|---|---|---|---|---|---|
| 1280x720, live | 108 to 218 | 528 | 635 | 720 | yes | 0, 2, 0, 1, 1 | 0 |
| 1280x720, after 15 s | 108 to 218 | 486 | 594 | 720 | yes | 1, 1, 0, 1, 2 (Done: "1 more") | 0 |
| 1280x720, kill switch armed | 108 to 269 | 558 | 665 | 720 | yes | 0, 2, 0, 1, 2 | 0 |
| 1280x720, kill switch engaged | 108 to 263 | 531 | 664 | 720 | yes | 0, 1, 0, 1, 2 | 0 |
| 1280x720, no live session | 108 to 244 | 355 | 436 | 720 | yes | all "No runs" | none shown |
| 67 percent zoom (1910x1075 CSS pixels) | 108 to 218 | 421 | 528 | 1075 | yes | 0, 1, 1, 1, 1 | 0 |

Every stamp line measured 18 px high: one line. The page's scroll position stayed 0 in every case.
Screenshots: `design/screenshots/01-events-1280x720.png` and
`design/screenshots/14-events-67-percent.png`.

## 8. Native widgets and the four custom components

Everything is a native, themed Streamlit element except four custom components. Those four use
components v2 with inline HTML, CSS, and JS (sources in `design/components/`, read and passed
inline; no bundler). They read Streamlit's theme CSS variables (`--st-text-color`,
`--st-secondary-background-color`, `--st-border-color`, `--st-primary-color`,
`--st-{green,yellow,red,gray,violet}-*`, `--st-font`, `--st-code-font`,
`--st-base-font-size`, `--st-button-radius`, `--st-link-color`), so `config.toml` drives both.

| Element | How |
|---|---|
| Status line with the guarded kill switch | **Custom component 1** (two-click state, events to Python) |
| Run board, including the grouped benchmark strip | **Custom component 2** (lanes, strips that move without remounting) |
| Annotated SQL | **Custom component 3** (numbered trap marks and notes) |
| Holdout ledger | **Custom component 4** (flips, regressions, stamps, pending cells, no-baseline and collapsed states) |
| Navigation | `st.navigation(position="top")` |
| Question input, Ask and Run buttons, demo controls | `st.text_input`, `st.button` |
| Tool-call timeline | Altair horizontal bars, width proportional to duration, chart tokens |
| Checklist, defense layers, reviewer verdict, answer against gold | `st.markdown` with Material icons for shape and a bold word |
| Cost counter for the failing grader | One sentence plus `st.progress` against the cap |
| Approval dialog | `st.dialog(width="large")` |
| Knowledge diff viewer | `st.code(language="diff")` |
| In-app channel | `st.container(border=True)` per post, newest first |
| Gate verdict | One `st.markdown` sentence with a shape and a word |
| Errors, notices | `st.error`, `st.info` |
| Specimen-state switches (style tile only) | `st.segmented_control` |

Component rules:

- Build the DOM once per mount; later calls update it in place. Every call is idempotent.
- Write user text with `textContent`, never `innerHTML` (questions arrive from webhooks).
- Format every time in the browser from a UTC ISO string.
- Give every component a stable `key`. Keep the timed fragment's element sequence identical on
  every run (the benchmark ledger is always emitted; closed, it is `collapsed` and takes no space).
- Events to Python use `setTriggerValue` (kill switch, review, show the holdout ledger, start the
  baseline experiment) and run in the `on_<name>_change` callback.
- Limits come from the data the page passes (section 6), never from constants in the JS.

## 9. Wireframes (1280x720)

### Status line (custom component 1, top of every page)

```text
+-----------------------------------------------------------------------------------------------+
|| DataPilot  Autonomy assisted level  Unattended clearance [#] revenue [ ] Not cleared: orders,  |
||   average order value, customers, products                                                    |
|| Session started 13:58  Business date: 31 January 2026  Tokens today [####--] 61,200 of 100,000|
||                                                                              ( Kill switch )  |
|| Planted [Naive guard] [Kill switch checked at claim only] [Demo pacing on: 2 s between stages]|
||                                                                  Times are in your local time |
+-----------------------------------------------------------------------------------------------+
```

- Autonomy in words: "report-only level", "assisted level", "unattended level".
- Unattended clearance per metric family: each cleared family by name with a filled green square;
  the rest grouped as "Not cleared: ..." with a hollow square. Family slugs show as words
  (`aov` is "average order value"). When the Improve page's gate clears a family, it moves into
  the cleared group here; that is where eligibility for the unattended level shows.
- Daily token budget: a thin bar, ink fill, and the numbers. At 80 percent the fill turns amber and
  the words "Near the daily cap" appear; at 100 percent red and "Cap reached: new runs blocked".
- Planted chips: dashed ink border, one per active planted item, a short sentence-case name ("Naive
  guard", "Kill switch checked at claim only"). With none: "None: the fixed system". The demo
  pacing chip has a solid graphite border and says what it does.
- Guarded kill switch: outlined in fault-red, "Kill switch".
  - First click arms it: red fill, white text "Click again to stop all workers", and a line below
    says "Armed. A second click stops every worker and forces the report-only level. Disarms in 5 s,
    or press Escape." The seconds come from `console.kill_switch_disarm_seconds`.
  - Second click stops all workers: the left edge turns red, autonomy reads "report-only level,
    forced by the kill switch", each cleared family reads "revenue: suspended" with a hollow
    square, and the line says "Kill switch engaged. All workers stopped; autonomy forced to the
    report-only level." The button becomes "Release kill switch".

### Agent page (Section 1: Agent loop)

```text
| Question [What was our net revenue in fiscal year 2025?        ] (Ask) (Run large query)       |
| Tool calls  list_tables [#] describe_table orders [###] run_query [##########]   total 6.2 s  |
|             0.4 s            1.1 s                   3.8 s     (bar width = duration)          |
| Started 11:59:09. Open trace in LangSmith                                                      |
| SQL                                                 | Trap notes                               |
|  1 SELECT SUM(o.total_cents[1]) / 100.0 ...         | [1] Trap: Net revenue                    |
|  4 WHERE[3] o.order_ts[4] >= '2025-01-01'[5]        |     total_cents includes tax and ...    |
|  5   AND o.order_ts[4] < '2026-01-01'[5]            | [5] Trap: Fiscal year ...                |
| Answer against gold                                                                             |
|   Agent answer  $41,230,118.07     Gold answer  $36,904,551.20     [x] Mismatch by $4,325,566.87|
| 7,912 tokens, $0.004, 6.2 s                                                                     |
```

- The timeline is an Altair bar per tool call; the label carries the tool name and seconds.
- The annotated SQL names the trap behind each wrong fragment; a correct query says "No trap found
  in this query." in green. The fiscal-year mark covers a calendar-year bound however the analyst
  writes it: a bare date, a `DATE`, `TIMESTAMP`, or `TIMESTAMPTZ` literal with a time and an
  offset, or a cast. A numbered note never points at nothing: when its fragment is not in the text,
  the note says that no line of the query is marked for it. Samples use only columns of `platform/ops/sql/warehouse_schema.sql`.
- Tokens, cost, and latency are one line of text, not tiles. The trace link is in the stamp line.

### Verify page (Section 2: Verification loop)

```text
| Checklist, attempt 2 of 3                  | Defense layers                                    |
|  [#] Passed  Parse: one statement           |  [#] Passed through  1 Prompt                     |
|  [#] Passed  Statement policy               |  [x] Stopped it      2 Syntax-tree guard          |
|  [x] Failed  Cost under the threshold:      |  [ ] Not reached     3 Schema allowlist           |
|              estimated 1.2 million rows     |  [ ] Not reached     4 Read-only role             |
|  [ ] Not run Personal data routing          |                                                   |
| Failing grader cost: $0.011 of the $0.020 cap  [#######---]  Stopped at the cap: escalated    |
| Every grader passed. Gold check on both databases: [x] Failed.  Reviewer: approved it.        |
| Started 12:04:51. Open trace                                                                   |
```

- Retries tick down the same checklist; the header says the attempt ("attempt 2 of 3").
- The layer that stopped malicious SQL says "Stopped it"; layers after it say "Not reached".
- Each statement wraps inside its column, so the data-modifying CTE shows whole, never cut at the
  right edge.
- "Every grader passes, still wrong": the all-passed checklist sits beside the failed gold check
  and the reviewer's verdict, whichever way it went.
- The cost counter stops at the cap and says so in words.

### Events page (Section 3: Event loop)

```text
| [status line]                                                                                   |
| Queued         | Running 2         | Verifying      | Holding for approval 1 | Done 4          |
| No runs        | [strip]           | No runs        | [strip] (Review)        | [strip]         |
|                | [Baseline         |                |                         | [strip]         |
|                |  benchmark: 41 of |                |                         | 2 more          |
|                |  70 runs done]    |                |                         |                 |
|                | (Show holdout ledger)                                                        |
| Off the board                                                                                   |
| Rejected 1      | Failed 1         | Escalated 1    | Blocked by budget 1    | Blocked by kill switch 2 |
| [reason, stamp] | [reason, stamp]  | [reason, stamp]| [reason, stamp]        | [reason, stamp] 1 more |
| ---- below the first screen ----                                                               |
| (Send webhook question) (Send the same event three times) (Request California export)          |
| (Restart worker)                                                                               |
| Worker restarted at 12:20:11. The pending approval survived: run 3f2a91c0 still holding.      |
| Channel                                                                                        |
|  12:21 Posted at the assisted level, verified: Net revenue in fiscal year 2025 ...             |
```

- Lanes: Queued, Running, Verifying, Holding for approval, Done; newest first.
- Absorbed duplicates show on the surviving strip: "2 duplicates absorbed".
- Approval dialog (native): title "Approve this export?", then one sentence that says exactly what
  will run and how many rows ("Approving runs the SQL below once and exports 412 rows to the
  marketing list. The rows include personal data: email and first name."), the SQL, the run, and
  two buttons, "Approve and run" and "Reject".
- Restart-worker outcome: one sentence with the time and what survived or was lost.
- The in-app channel lists posts newest first; each states its level and whether it was verified.

### Improve page (Section 4: Hill-climbing loop)

```text
| Baseline, v1, active   Started 12:31:02. Open trace                                            |
| Candidate, v2          Started 12:38:40. Open trace                                            |
| Each item runs 3 times and passes on 2 of 3. v1 passes 3 of 7; v2 passes 6 of 7: 4 fixed,     |
| 1 regression.                                                                                  |
| Question                                            v1, active        v2, candidate     Change  Trace|
|#Report the total net revenue for fiscal year 2026  [x] Failed 0 of 3 [#] Passed 3 of 3 Fixed: now passes Trace|
|/What number of orders arrived on Black Friday 2025 [#] Passed 3 of 3 [x] Failed 1 of 3 Regression Trace|
| Open every v2 trace in LangSmith, filtered by knowledge version.                               |
| Candidate A: 14 of 25 dev, 0 regressions, 7 rules; Candidate B: 12 of 25 dev, 1 regression,   |
| 8 rules; chosen: A                                                                             |
| [x] Gate: blocked. v2 fixes 4 holdout items but breaks 1 that v1 passed (orders on Black      |
| Friday 2025), so it is not promoted.                                                           |
| Knowledge diff (v1 to v2)                                                                      |
|  + fiscal_year: The fiscal year runs from February 1 to January 31 ...                          |
```

- Rows are real holdout items, by question (the id is the row's accessible name and tooltip).
- Flips are marked "Fixed: now passes" with a green edge; regressions are red, with the word
  "Regression" and a struck edge.
- The gate verdict is one plain sentence.
- Above the knowledge diff, one line names both candidates of the analyzer request, their dev
  results and rules, and the one kept (`ops.analyzer_candidates`); it is absent for a version
  that no analyzer request chose.
- No baseline in this session: "No baseline run in this session yet." and one button, "Run the
  baseline experiment".
- When the gate passes and a family qualifies, the status line moves that family to cleared.

## 10. States

| State | Status line | Run board | Agent and Verify | Ledger |
|---|---|---|---|---|
| Empty | "No live session. Run make preflight to start one." | Same sentence above empty lanes; with a session, "No runs in this session yet. Send a webhook question to start one." Each empty lane: "No runs" | "Ask a question to see the tool calls, the SQL, and the answer." | "No baseline run in this session yet." with "Run the baseline experiment" |
| Loading | Unchanged; values update in place | A queued strip appears at once; a benchmark is one grouped strip with its count | `st.spinner` with what is running: "Running the agent. In calibration a run took 14 to 76 seconds." | Cells read "Not run yet" until their runs finish |
| Live | One fragment every `poll_seconds`; changed fields get a 900 ms magenta-tint highlight | Strips move lanes; the moved strip gets a 900 ms magenta outline | Results appear with their stamp | Rows fill; summary sentence updates |
| Error | "Api not reachable. Start it with make up." in fault-red | Last known board stays; one `st.error` line above it says what failed and what to do | `st.error`: what happened, then what to do | `st.error` with the failed item and the retry action |
| Blocked | Kill switch engaged or budget cap reached, in words | Strips in "Blocked by budget" or "Blocked by kill switch" with the reason | The block reason as a sentence | Gate: blocked, with the reason |

## 11. Motion

Motion only on a state change, never as decoration, and none under `prefers-reduced-motion`.

- A strip that changes lane gets a 3 px magenta outline that fades over 900 ms.
- A status-line field that changes (autonomy, clearance, kill switch) gets a magenta-tint
  background that fades over 900 ms.
- Nothing pulses, spins, or slides. Streamlit's own spinner is the only looping motion, and only
  while something runs.

## 12. Copy

- Sentence case, including planted chips ("Naive guard", "Kill switch checked at claim only") and
  empty lanes ("No runs"). Plain verbs on buttons: "Ask", "Run", "Approve and run", "Reject",
  "Review", "Show holdout ledger", "Release kill switch", "Run the baseline experiment".
- Errors say what happened, then what to do: "The api did not answer within 2 seconds. Start it
  with make up, then reload this page."
- Never "successfully", never exclamation marks, never filler.
- Full names, never short forms: "report-only level", "assisted level", "unattended level",
  "fiscal year 2025", "Eastern time", "personal data", "human approval", "average order value".
  Planted items by their plain names, never by flag.
- Numbers with units and thousands separators: "61,200 of 100,000", "$0.011", "6.2 s". Times on a
  24-hour clock: "Started 11:59:09".
- Samples, specimens, and screenshots use only columns in `platform/ops/sql/warehouse_schema.sql`
  (for example `order_ts`, `subtotal_cents`, `discount_cents`, `total_cents`).

## 13. Banned

Each is checked on every page before it is called done (results for the style tile in section 15).

1. Identical rounded cards everywhere.
2. One radius and soft shadow on everything.
3. Gradients.
4. Cream with terracotta.
5. Near-black with neon.
6. ALL-CAPS eyebrow labels.
7. "A · B · C" meta strings.
8. Arrows appended to buttons.
9. Emoji.
10. Monospace for ordinary labels.
11. Decorative big-number tiles (including `st.metric` rows used as decoration).
12. Filler copy.

## 14. Style tile

`design/style_tile.py` is a small Streamlit page with the real theme and working prototypes of the
four components, fed by specimen data shaped like `ops.runs` and `ops.run_events`
(`design/specimen.py`; holdout rows are the real items of `holdout.yaml`). Its first screen is the
Events view: the status line and the run board, with a grouped benchmark strip. A fragment that
reruns every `poll_seconds` appends one stub run event and moves a strip across the board.
Specimen switches show the no-session and no-baseline states. No console page imports
`design/specimen.py`.

Run it with `make style-tile` (http://localhost:8531). The entry is `platform/console/design_app.py`,
which sits next to `static/` (the fonts) and `.streamlit/` (the theme), so the demo console never
reaches specimen data.

Screenshots (Streamlit 1.65.0, Chromium headless), in `design/screenshots/`:

| File | Shows |
|---|---|
| `01-events-1280x720.png` | The Events view at 1280x720, live |
| `02-events-1280x720-t15.png` | The same after 15 s; Done lane at its cap with "1 more" |
| `03-kill-armed.png` | Kill switch armed |
| `04-kill-engaged.png` | Kill switch engaged; clearance suspended |
| `05-approval-dialog.png` | The approval dialog opened from a strip |
| `06-benchmark-expanded.png` | The grouped benchmark strip, ledger opened |
| `07-benchmark-ledger.png` | The live benchmark ledger filling in |
| `08-tokens.png`, `09-type.png` | Tokens; type and native widgets |
| `10-annotated.png` | Annotated SQL with `order_ts` |
| `11-holdout.png`, `12-no-baseline.png` | The ledger; the no-baseline state |
| `13-no-session.png` | No live session |
| `14-events-67-percent.png` | The Events view at 67 percent browser zoom |

## 15. Self-review

### Streamlit pin re-check on 1.65.0

Method: the style tile ran headless on port 8531 under the pinned `streamlit==1.65.0`. Playwright
(Chromium headless shell, 1280x720) loaded it and watched for 15 seconds.

- Script executions came from counters in session state, written to a file each run.
- Remounts: each component's JS counts its calls, its mounts (a new root element), and its cleanups.
  The probe also kept references to both components' root elements and to one moving strip, and
  checked that they were the same connected nodes at the end.
- Greying: every 50 ms the probe sampled the effective opacity (the product up the tree, through
  the shadow host) of both components, the minimum opacity of every `[data-stale]` element, and
  whether any element was marked stale.

Results (final run, after the approval-round changes):

| Measure | Result |
|---|---|
| Full script runs / fragment runs during the 15 s window | 0 / 15 (counters 1 / 2 at the start, 1 / 17 at the end) |
| Status line: JS calls / mounts / cleanups | 3 / 1 / 0 (called only when its data changed) |
| Run board: JS calls / mounts / cleanups | 16 / 1 / 0 |
| Holdout ledgers: mounts | 2, one for each of the two ledger instances, none remounted |
| Same root nodes at 15 s | Yes, for both; the tracked strip stayed the same node through running, verifying, and done |
| Opacity samples below 1 (status line, board, any stale element) | 0, 0, 0 of 300 |
| Minimum opacity | 1.0 everywhere |
| `data-stale` toggles / samples with a stale element | 84 / 17 of 300 (cleared before the 0.5 s fade starts) |
| After arming and engaging the kill switch | Still 1 mount each; the engaged message showed |
| Approval dialog opened from a strip in the timed fragment | Opened, and still open after 3 fragment ticks |
| Browser console errors | None |

Neither component remounts or greys out on 1.65.0, so the pin stays at 1.65.0.

### Fit

Section 7: the Events view fits without scrolling at 1280x720 in every state measured and at 67
percent zoom.

### Contrast

Every text pair in the style tile measured 4.58:1 or higher (table in section 1). Earlier fixes:
the swatch labels no longer sit on the amber and rule colours (4.12 and 4.29); the trap number tags
went from 12.4 px to 14 px.

### "Remove one accessory" pass

- Removed: the "latest run event" caption under the board, and the "Run board" heading above it.
- Removed: hex labels printed on the swatches (they failed contrast on amber and rule).
- Removed: the run id line on strips; the id is in the strip's accessible name and in the dialog,
  and the live stamp took its place.
- Removed: the separate edge element on strips; the 6 px left border is the edge.
- Off-board bays show the reason instead of repeating the bay's own title as the strip word.

### Banned-list check (style tile)

| Banned | Result |
|---|---|
| Identical rounded cards | Pass: square strips with state edges; lanes, notes, and rows differ in structure |
| One radius and soft shadow | Pass: 0 radius on strips, 2 px on controls only, no `box-shadow` anywhere |
| Gradients | Pass: no gradient in any CSS |
| Cream with terracotta | Pass: cool grey ground, magenta accent |
| Near-black with neon | Pass: light theme |
| ALL-CAPS eyebrow labels | Pass: no `text-transform`, sentence case labels and chips |
| "A · B · C" meta strings | Pass: fields are labelled; no middle-dot separators |
| Arrows appended to buttons | Pass: verbs only |
| Emoji | Pass: shapes are CSS or Material icon glyphs |
| Monospace for ordinary labels | Pass: mono only for SQL and the token counter |
| Decorative big-number tiles | Pass: no `st.metric`; numbers sit in sentences and the gauge |
| Filler copy | Pass: every sentence states a fact or an action |

### Known limits of the style tile

- Specimen links point to a placeholder LangSmith path, not real traces.
- Streamlit 1.65.0 leaves about 100 px of empty header space above the page; `theme.paddingTop`
  exists only from 1.66.0. The Events view fits with it (section 7), so this does not justify
  moving the pin.
- The armed kill switch's longer label moves the button to its own row for up to 5 seconds; the
  view still fits (665 of 720 px).
- A step that names a tool ("run_query") shows in the strip's sans text; the console should set
  tool names in mono inside the step line.

## 16. Console build notes

Recorded by the console build. The console's component copies live in
`datapilot_console/components/`; they start from `design/components/` and add only these:

- **No-baseline label.** The ledger's one button reads "Run experiment on the active version", the
  label the demo registry gives the baseline experiment, instead of "Run the baseline experiment".
  With a baseline in the session, the same label is a native button on the Improve page.
- **Tool names in mono.** A strip's step sets a tool name ("run_query") in mono inside the line.
- **Annotated SQL, waiting.** Before a run has SQL, the component shows only its live stamp.
- **Api notice.** The status line has one more row, in fault-red bold, only while the api does not
  answer: "The api did not answer. Start it with make up."
- **Class-day safeguard notice.** While the version activated by the class-day safeguard is still
  the active one, the same notice row reads "Class-day safeguard: v5 is active, the version
  verified in rehearsal; its families keep the level they earned there. It replaced v6, which the
  gate promoted in class." (`views.safeguard_notice`).
- **Candidate line.** The Improve page shows the analyzer request's choice among its candidates
  above the knowledge diff, the sentence saved in `ops.analyzer_candidates`.
- **Lanes scroll inside themselves.** When the visible page area is short (a 1280x600 share), each
  lane's list scrolls inside the lane so the status line and the off-the-board row stay on the
  first screen; the page itself does not scroll. A scrolling lane ends below the last strip that
  fits whole, so the lane's edge never cuts through a strip or its button. Streamlit 1.65.0 with top navigation starts the
  status line at 144 px, not 108 px. Measured on seeded rows: the off-the-board row ends at 715
  of 720 px and 595 of 600 px, with the kill switch armed and disarmed
  (`screenshots/measurements.json`).
- **Regression confirmation.** A ledger row whose candidate looks like a regression shows
  "Apparent regression: confirming with 3 more runs" (amber edge and amber words), then the
  outcome: "Regression: confirmed, ..." or "Not a regression: ...".
- **Reads.** Duplicate counts on strips come from `ops.event_duplicates`, so `make demo` runs show
  them too; the gate's sentence comes from `ops.promotion_decisions`.
