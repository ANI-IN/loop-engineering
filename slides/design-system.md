# Loop Engineering deck: design system and slide schema

This page is the design system of the class deck and the schema every block module in
`slides/source/` follows when it sets `RULES = "design system"` or, for the second rebuild,
`RULES = "design system 2"` (the same design system under its own block plan and the added checks
of the section "The second rebuild" below). The outline builder
(`slides/source/build.py`) checks every rule a script can; the deck builder draws one fixed layout
per slide type from the same data. The sample block module, `slides/source/samples.py`, holds one
slide of every type with full speaker notes: copy from it.

## Colour and wayfinding

One colour per loop, from the course template's palette. Each loop colour is a fill with dark text
(`212121`) on it, and every use of a colour also carries the loop's name, so colour never carries
meaning alone. A loop colour is never text on the navy background.

| Loop | Fill | Dark text on it |
|---|---|---|
| Agent loop | blue `3896D2` | 4.95 to 1 |
| Verification loop | teal `0097A7` | 4.59 to 1 |
| Event loop | orange `FFAB40` | 8.55 to 1 |
| Hill-climbing loop | lime `EEFF41` | 14.58 to 1 |

The template's neutrals stay: the navy background `324158` (white text on it, 10.33 to 1), the card
`F0F3F6` (navy text on it, 9.28 to 1), white (navy text, 10.33 to 1), and the blue-grey `78909C`
(dark text on it, 4.81 to 1; the "Without" side of a comparison and its chart series, and the
code highlight outside a loop). Two tints
of those neutrals serve as backgrounds and quiet text, not as accents: `D9E0E6` for a neutral
table header (dark text, 12.08 to 1) and `C5CFD8` for a tracker name that is not current (on navy,
6.54 to 1).

The one added accent is violet `B39DDB`, for the Insight callout only (dark text on it, 6.72 to
1). Link text is navy on a light panel: the template's teal link colour reads at 3.15 to 1 there,
so the deck builder sets the theme's link colour to navy.

The colour of a slide comes from its block: a section's slides use their loop's colour; the
opening, the design segment, the breaks, the poll, and the closing use the neutrals.

## Typography

- Fira Sans for every word on a slide, Fira Mono for code, and Lexend Medium for the DEMO badge
  only. All three are embedded in the built deck.
- Titles: 36 points, bold, white, at most two lines (the section opener and the title slide: 40).
- Body text: at least 20 points. The subtitle line under a title, a quote, and the Insight
  callout of a compact slide: 24. The Insight callout's lesson on an insight slide: 28. A measured
  value on a value card: 32.
- Code: Fira Mono at 18, 16, or 14 points, the largest at which the longest line fits.
- Nothing on a slide is under 14 points. Only these may go under 20, down to 14: the progress
  tracker, code lines and their markers, the sources list, a chart's text and its sample line
  (and the payoff's sample line), the scoreboard (16, the current section's state 18), the DEMO badge (18), and a source marker.
  Their shapes are named with "(small)", which the fit check reads.

## Grid and margins

The slide is 13.333 by 7.5 inches. Content sits on 12 columns between 0.6-inch margins, with
0.25-inch gutters (a column is 0.78 inches; 8 columns are 8.01 inches, 4 columns 3.88). The title
box runs from 0.18 to 1.4 inches, bottom-anchored, so the first content line sits the same
distance under every title. The content area runs from 1.6 to 6.6 inches. The progress tracker
sits under it, from 6.86 inches, and ends left of 10.9 inches, clear of the template's logo in the
bottom right corner. Stacked blocks keep a 0.2-inch gap (0.1 to 0.16 inside lists).

One idea per slide. A concept-type slide has at most 4 bullets and about 60 visible words; the
depth goes into the speaker notes. Prefer a diagram, a comparison, a table, or annotated code to
bullets.

## The progress tracker

Every slide carries the tracker at its foot: first the block's state ("Opening", "Design" for
the design segment, "Section 1" to "Section 4", "Break", "Poll", "Closing") in a white outlined
pill, then the four loops by name. Every pill keeps its place on every slide: the state pill has
one width, its longest label ("Foundations") in bold with the same side room as every loop pill
(0.34 inches in all), and each loop pill is as wide as its name in bold with that room. The
current loop's pill is filled in its colour with dark bold text; the others are outlined, their
names in quiet grey. The opening, the design segment, the breaks, and the poll fill no loop; the
closing fills all four, the four loops together.

## Cards

The left-bar card form belongs to the Insight callout alone. A card with a label, the DEMO
slide's guaranteed moment and the design callout's DataPilot choice, is a white card with a full
outline in the loop's colour (a neutral grey outside a loop) and its label in bold at the start of
its text. Every other card is the card colour with navy text.

A bold lead-in, a short "Label:" at the start of a line set in bold, belongs only to the types
written as "Label: text": a problem statement item, an evidence slide's measure card, a DEMO
slide's watch card, the pattern slide's lines, the payoff's cards and checks, and the insight
slide's "Evidence:" line. A numbered callout, a checklist item, a recap card, and an option card
keep their text as written, colon or not: a colon alone never makes a label.

One exception to the loop's colour: the hill-climbing loop's lime reads at about 1.1 to 1 on
white or the card colour, so wherever it would be an outline on a light fill (the labelled card,
the demo page link pill, a done pill of the scoreboard) the outline is the dark text colour
`212121` at the same weight. Lime stays wherever it is a fill.

## The Insight callout

One look everywhere: a white card with a violet bar on its left edge, a violet "Insight" label
with dark text, and the lesson under it in bold navy. An `Insight:` line is drawn this way on five
types, and the outline builder refuses it on any other:

- an insight slide: the slide's lead, at 28 points, or compact (24) beside a screenshot or chart;
- a section opener: compact, inside the band under the failure it fixes, the band growing to
  hold it; every section opens with one;
- an evidence slide: compact, under the measure cards beside the chart;
- a comparison or a pitfalls slide: compact, under the table.

An insight is a lesson that changes how an engineer designs or runs agents, and it is backed
by evidence on the same slide: a measured count with its sample size, or a source marker.

## Source markers

A sourced claim on a slide ends with a source marker written `[^3]` in the slide data. The deck
shows it as `[3]` at 14 points on the text's baseline, in the colour of the text around it (a
raised run would render at about 9 points, under the floor, and the fit check counts a raised run at
the two thirds of its size it renders at), and the
outline prints it as `[3]`. The number is the source's number in the sources list
(`slides/source/sources.py`), the same number the sources slide shows; the outline builder
refuses a marker that names no source. Course evidence (the calibration report, the paired
measurements page) is cited in the speaker notes and listed in its own group on the sources slide.

## Numbered callouts

A number in a white disc with a navy ring marks a place on annotated code or on a screenshot, and
the same number heads its callout card. On code the marker sits in the left gutter of the first
line it marks, and the marked fragments are highlighted in the loop's colour with dark bold text;
outside a loop (the opening's code) the highlight is the blue-grey `78909C`, since the neutral
header tint reads at about 1.15 to 1 on the code panel. The callout cards in a row under code keep
0.12 inches of side padding, so a short callout stays on one line.
On a screenshot the marker sits over the picture at the position the slide data gives. The
numbered lines of the slide must match the markers exactly.

## Diagrams

Every concept and architecture diagram is an Excalidraw drawing, generated from the diagrams'
definitions, in one style: the architect setting (roughness 0), Nunito for labels, the code font
for code, fixed stroke widths and one arrow style, the four loop colours as fills with dark text.
The deck places the diagram's PNG export (3 times scale, transparent background) on a light card
panel with its alternative text. A slide names its diagram, never a path:
`figure={"diagram": "agent-loop", "alt": "..."}`. A name with no deck export fails the build.

A slide that shows a full diagram has a title of one line and nothing else: no idea line, no
points. The idea and the diagram's points go into the speaker notes, walked step by step. The
diagram gets the whole content area, 12.13 by 5.0 inches, with no inner margin. Each diagram is
drawn on a canvas of that shape, 1920 by 791 pixels (5760 by 2373 in the scale-3 export), so its
smallest label, 40 pixels on the canvas, renders at about 18.2 points. The deck builder computes
that size for every diagram it places, from the shown width and the export's width over its
scale in the render records, and reports it; a diagram under 18 points is a build failure once
the redrawn exports are in.

## Screenshots

A screenshot is cropped to the region that matters, never a full console, with numbered markers
that match the slide's numbered lines. It sits on the navy background with a thin blue-grey edge.
The slide data names the picture's repository path, its alternative text, the crop (left, top,
right, bottom fractions), and each marker's position (fractions of the cropped picture).

## Charts

Charts are native PowerPoint charts, drawn from the numbers in the slide data: clustered columns
or bars on a light panel, data labels on every bar, both axes titled, the legend below. Colours:
one series is the block's loop colour (blue-grey outside a loop); without and with are blue-grey,
then the loop colour (navy outside a loop); a dark outline on every bar. The Insight violet is
never a series colour. The value axis ends above the tallest bar (at least 12 percent above it,
otherwise a round number 15 percent up), so a data label never meets the chart title. Axis titles
are bold italic, so they never read as one more category label; write an axis title that names
the axis, such as "Trap in the question", not one more category. Every chart states its sample
size on the slide's "Sample:" line, printed under the chart.

## Tables

Tables carry their own fills: a header row (neutral, the loop's colour for a pitfalls table, or
per column in a comparison: blue-grey for "Without", the loop colour for "With"), and body rows
alternating white and the card colour, navy text at 20 points. At most 4 body rows. Each column
is as wide as its longest cell on one line when the columns fit the panel; when they do not, a
column whose longest cell fits an even share keeps its width, and the others share the rest by
their longest cells, each at least its longest word and 1.3 inches wide. A comparison's "Without"
and "With" columns stay equal.

## Slide types and their layouts

Each type has one fixed layout. The key is the slide's `kind`.

| Key | Type | Layout |
|---|---|---|
| `title` | Title | The template's title layout: the title (40 points), then one subtitle paragraph per line; slide 2 names the instructor as `[INSTRUCTOR NAME]` |
| `agenda` | Agenda | Numbered rows; the row marked "(now)" is filled in its loop's colour with a "Now" label |
| `opener` | Section opener | A full-width band in the loop's colour: the section's name at 40 points, then "The failure it fixes", then the opening insight as the compact Insight callout |
| `insight` | Insight | The Insight callout at the top of the content area on every insight slide. With a screenshot or chart: the visual on 7 columns down the full content height, the compact callout and the evidence on 5, numbered callouts only for the screenshot's markers. Without one: the callout across the slide, then the evidence line and bulleted lines |
| `story` | Problem story | The question across the top; the annotated code (or screenshot) on 8 columns with the value cards on 4; the numbered callouts in a row; the footer at the bottom. Code too wide for 8 columns takes the full width, and the values join the question's row |
| `concept` | Concept diagram | A one-line title, then the diagram on the whole content area, 12.13 by 5.0 inches; no idea line and no points (both in the notes) |
| `mechanism` | Mechanism | The idea line, opened by the code panel's label chip ("Pattern" on the neutral tint, "DataPilot" in the loop's colour) when the code names its panel; the annotated code across the slide; the numbered callouts in a row, or four of them in two rows when that is lower |
| `demo` | Demo | The laptop, its screen navy, with the white DEMO badge as a shape on it and the labelled demo page link under it; what to watch for and the guaranteed moment card on the right |
| `evidence` | Evidence | The native chart on 7 columns with its sample line; the measure cards and a compact Insight callout on 5 (or a table across the slide) |
| `comparison` | Without and with | The comparison table across the slide; a compact Insight callout or a footer under it |
| `design_callout` | Design callout | The "Text-to-SQL design" label in the loop's colour at the start of the decision line's row, the options table or cards, and the DataPilot card |
| `checklist` | Apply it | Up to 6 items, each an empty check box and its card |
| `pitfalls` | Pitfalls | A table: pitfall, what happens, what to do instead |
| `recap` | Recap and question | With a `scoreboard` field, the scoreboard across the top; then up to 3 recap cards on 7 columns and the "Check your understanding" card on 5 (its question at 20 points under the scoreboard, 24 without) |
| `poll` | Poll | The fixed poll wording, centred |
| `break` | Break | The fixed break wording, centred |
| `closing` | Closing | Up to 10 numbered items, in two columns past 5, every card as tall as the tallest so the columns end level; an item's disc takes the colour of the section named at its end |
| `sources` | Sources | Two light panels: group headings and numbered entries with their full addresses; an address never breaks at its hyphens. Each entry hangs from its number (its wrapped lines and its address lines start under its title) with 3 points between entries, and the fit estimate measures both |
| `pattern` | Pattern | The one-line "Definition:"; the pattern diagram on the compact panel, 12.13 by 3.41 inches across the slide; "Use when:" and "Avoid when:" side by side, one line each; an optional "Elsewhere:" line with its source markers. No other line |
| `problem` | Problem statement | The lead line at 24 points; up to 3 items as cards down the slide, or 4 to 6 in a grid of two columns (2 by 3 at most), every card as tall as the tallest and growing to fill the slide (1.2 inches at most); an item tagged with a loop is filled in its colour with the loop's name on its first line |
| `payoff` | Payoff | "Before" and "After" cards side by side with the level it posted at, each a label over a value at 32 points, the three values starting at one height; Before and After as wide as their values need (3 to 4 columns), the level the rest; the scoreboard complete, each loop with what it contributed; the requirement groups checked off in two columns read down, each column as wide as its longest check needs on one line (three columns of two when the slide has no room for a third row); the sample line at the foot |

## The slide schema

A block module sets `RULES = "design system"` and defines `SLIDES`, a list of dictionaries (the
breaks and the poll: `BLOCKS`, keyed by block). Every slide holds:

- `kind`: a key of the table above.
- `title`: at most 10 words; it is the slide's title placeholder.
- `minutes`: the slide's minutes; a block's slides add up to its minutes exactly.
- `says`: the one-line summary for the outline's table.
- `src`: reviewer metadata, where the content is grounded (repository paths allowed here only).
- `on_slide`: the lines the slide shows, in the line grammar below.
- `notes`: the speaker notes, one list item per label, in the standard's order.

Optional fields:

- `code`: annotated code: `language`, `origin` (the file and lines it comes from, printed in the
  outline), `lines` (the code lines as shown, an elided part as `...`), and `marks`, each
  `(line index, fragment, number)`; a fourth element `True` puts the number's disc on that mark's
  line instead of its first mark's. Required on `mechanism`; a `story` needs `code` or `image`.
  Under design system 2 a mechanism's code also names its `panel`: `"Pattern"` for short generic
  code or pseudocode (no DataPilot name in its lines or origin), `"DataPilot"` for its real code.
- `figure`: a diagram: `diagram` (the name of its deck export) and `alt`. Required
  on `concept` and on `pattern`, whose diagram is a pattern diagram, named `pattern-<name>`; a
  pattern diagram is shown only on a pattern slide.
- `scoreboard`: on a `recap` slide, the section number (1 to 4) whose state the scoreboard shows.
- `image`: a screenshot: `path`, `alt`, `crop`, and `callouts`, each `(x, y, number)`.
- `chart`: `type` (`column` or `bar`), `title`, `categories`, `series` (each `(name, values)`),
  `x_label`, `y_label`, and an optional `maximum` for the value axis. An `evidence` slide needs a
  chart or a table.
- `block`: in the sample module only, the block the slide would belong to.
- `allow_commands`: true on a break or poll slide whose notes name a command.

### The line grammar

| A line that starts with | Becomes |
|---|---|
| `Idea:`, `Fixes:`, `Insight:`, `Evidence:`, `Sample:`, `Decision:`, `DataPilot:`, `Question:`, `Footer:`, `Value:`, `Badge:`, `Guaranteed moment:`, `Group:` | the element of that name in the type's layout |
| `Definition:`, `Use when:`, `Avoid when:`, `Elsewhere:` | a pattern slide's lines |
| `Lead:` | a problem statement's lead line; its items are bullets, each optionally ending `\| <loop>` (a loop's name, or "Section 2") |
| `Before: <label> \| <value>`, `After: <label> \| <value>`, `Level: <value>` (shown as "Posted at:" over the level at the value size; a few words, so it stays on one line), `Loop: Section N \| <what it contributed>` | the payoff's cards and its complete scoreboard; its requirement checks are bullets |
| `- ` | a bullet: a check box item, a recap card, a watch card, an option card, an evidence line under an Insight callout |
| `1. ` | a numbered line: a callout, an agenda row, a closing item |
| `\|` | a table row (the separator row is left out) |
| `"` | a quote card (the question of a problem story) |
| `Link: <label> \| <address>` | the DEMO slide's demo page link, the one link a slide may carry |
| `[n] <entry> <address>` | a source entry, on the sources slide only |

Inside a line, `**bold**` is bold and `[^3]` is a source marker. A count such as "6 of 6" is
joined by no-break spaces, so it never breaks across lines, and so are "Section" and
"Assignment" and their number wherever the deck builder draws text. A hyphenated word ("report-only") may
still break at its hyphen when a line is full: none of the deck fonts has a non-breaking hyphen. A value card is
`Value: <label> | <value>`; a closing item may end `| Section 2` to name the section that proves
it. No line on a slide holds a file name, a repository path, a make command, or a code span; the
code of a mechanism or a story lives in its `code` field.

### What each type must hold

| Type | Lines it must hold | Words on the slide | Bullets, at most |
|---|---|---|---|
| `title` | | 0 to 30 | 4 |
| `agenda` | 3 to 8 numbered rows | 3 to 45 | 0 |
| `opener` | `Fixes:`, `Insight:` | 3 to 45 | 0 |
| `insight` | `Insight:`, `Evidence:`; numbered lines only for a screenshot's markers | 15 to 60 | 4 |
| `story` | a quote, `Footer:` | 20 to 75 | 4 |
| `concept` | no line; a title of at most 52 characters (one line) | 0 | 0 |
| `mechanism` | `Idea:` | 15 to 75 | 4 |
| `demo` | `Badge:`, `What to watch for`, `Guaranteed moment:`, `Link:` | 20 to 80 | 3 |
| `evidence` | `Sample:` | 10 to 60 | 4 |
| `comparison` | a table with a "Without" and a "With" column | 15 to 80 | 4 |
| `design_callout` | `Decision:`, `DataPilot:` | 15 to 75 | 4 |
| `checklist` | 3 to 6 bullets | 20 to 90 | 6 |
| `pitfalls` | a table whose header starts "Pitfall" | 20 to 95 | 0 |
| `recap` | `Question:` | 10 to 60 | 3 |
| `poll`, `break` | the fixed wording | 0 to 30 | 0 |
| `closing` | 3 to 10 numbered items | 20 to 190 | 0 |
| `sources` | `Group:` headings and `[n]` entries | 20 to 260 | 0 |
| `pattern` | `Definition:`, `Use when:`, `Avoid when:`; `Elsewhere:` only with a source marker; each one line (at most 90, 44, 44 and 90 characters) | 12 to 60 | 0 |
| `problem` | `Lead:` and 3 to 6 items | 20 to 90 | 6 |
| `payoff` | `Before:`, `After:`, `Level:`, four `Loop:` lines in section order, 3 to 6 requirement checks, at most one `Sample:` | 40 to 130 | 6 |

Numbered lines are at most 4 on every other type. What fits, measured on the full deck: a
mechanism's code takes at most about 9 lines at 16 points with four short callouts (at most 93
characters a line at 14 points across the slide, about 58 on the 8 columns of a story beside its
values); a design callout's table at most 3 body rows of one or two lines; a closing list of 10
items at most about 8 words an item; a sources slide at most about 11 entries. Words on the slide leave out source markers, the
link line, and code. A table has at most 4 body rows. Every number on a slide or in the notes
comes from the course evidence (the calibration report, the paired measurements page, the evidence
pages) or a listed source.

## The speaker notes standard

Every slide's notes hold these labels, each line starting with its label, in this order:

1. `Purpose:` one sentence on what the slide must achieve (at most 30 words).
2. `Timing:` generated by the outline builder from the minutes, such as
   "Timing: 3 minutes (0:12-0:15)"; never written in the data.
3. `What to say:` the talk track, in spoken language; a diagram is walked step by step.
4. `The point to land:` the one sentence learners must remember (at most 30 words).
5. `Example:` a concrete example or analogy, preferably from this course's runs.
6. `Ask the room:` a question and the answers to expect.
7. `Misconceptions:` what learners get wrong here, and the correction.
8. `Transition:` the sentence into the next slide (at most 40 words).

"What to say" has 150 to 300 words on an insight, problem story, concept, mechanism, evidence,
comparison, design callout, checklist, pitfalls, pattern, or payoff slide; 300 to 400 on a
problem statement slide (the owner's specification: a full talk track, examples learners
recognise, a question for the room); 80 to 300 on a DEMO slide; 60 to 200 on a recap or closing
slide; 30 to 150 on a title, agenda, section opener, or sources slide.

A DEMO slide gives each of its demos, after "What to say", as a group: `Demo: <title>.` (the demo's
title in the demo registry), `Command:` (the make command or the console control), `Point at:`,
`Expected output:`, `While it runs:` (how long it takes and what to say meanwhile), `If it fails:`
(the reset and the run again, step by step), and `Backup screenshot:`. The builder inserts each
demo's `Guaranteed moment:` from the registry after its expected output, word for word.

A break or the poll keeps the short form: `Purpose:`, `Timing:`, `What to say:` (15 to 90 words),
any number of `Do:` lines for the instructor, and `Transition:`.

A make command is "make" and a target the Makefile defines ("make demo", "make reset"); prose such
as "make the" is not one. Paths and commands appear only in a DEMO slide's notes (and a break's or the poll's, with
`allow_commands`). The word "replay" never appears, and no provisional marker is left.

## The block plan of the first rebuild (superseded)

This is the clock of the first rebuild, for modules that set `RULES = "design system"`
(`BLOCK_PLAN` in `slides/source/build.py`). The class now runs on the second rebuild's plan below
(`BLOCK_PLAN_2`); check timings against that table, not this one.

| Block | Key | Clock | Minutes | Slides at most |
|---|---|---|---|---|
| Opening | `opening` | 0:00-0:10 | 10 | 10 |
| Designing text-to-SQL | `design` | 0:10-0:25 | 15 | 6 |
| Section 1: Agent loop | `s1` | 0:25-1:03 | 38 | 13 |
| Section 2: Verification loop | `s2` | 1:03-1:45 | 42 | 13 |
| Break | `break1` | 1:45-1:55 | 10 | 1 |
| Section 3: Event loop | `s3` | 1:55-2:50 | 55 | 13 |
| Poll | `poll` | 2:50-2:55 | 5 | 1 |
| Break | `break2` | 2:55-3:05 | 10 | 1 |
| Section 4: Hill-climbing loop | `s4` | 3:05-3:48 | 43 | 13 |
| Closing | `closing` | 3:48-4:00 | 12 | 10 |

At most 85 slides in all. Each section has exactly one DEMO slide, with its demos in its notes.

## The second rebuild (design system 2)

A module that sets `RULES = "design system 2"` follows everything above, under this block plan
(27 October 2026) and the checks after it.

| Block | Key | Clock | Minutes | Slides at most |
|---|---|---|---|---|
| Opening | `opening` | 0:00-0:05 | 5 | 3 |
| The problem | `problem` | 0:05-0:17 | 12 | 4 |
| Foundations | `foundations` | 0:17-0:30 | 13 | 5 |
| Designing text-to-SQL | `design` | 0:30-0:40 | 10 | 4 |
| Section 1: Agent loop | `s1` | 0:40-1:15 | 35 | 13 |
| Section 2: Verification loop | `s2` | 1:15-1:50 | 35 | 13 |
| Break | `break1` | 1:50-2:00 | 10 | 1 |
| Section 3: Event loop | `s3` | 2:00-2:48 | 48 | 13 |
| Poll | `poll` | 2:48-2:53 | 5 | 1 |
| Break | `break2` | 2:53-3:03 | 10 | 1 |
| Section 4: Hill-climbing loop | `s4` | 3:03-3:45 | 42 | 13 |
| Closing | `closing` | 3:45-4:00 | 15 | 14 (7 slides and at most 7 sources slides) |

The progress tracker's state pill reads "Problem" and "Foundations" for the two new blocks, which
fill no loop.

### The pattern panel

A pattern slide shows its pattern diagram on a compact panel, 12.13 by 3.41 inches, the full
content width, with no inner margin. Pattern diagrams are drawn on a canvas of 1920 by 540 pixels,
the panel's shape, and exported at scale 3 (5760 by 1620, transparent) with the other deck
exports; a 40-pixel label renders at about 18.2 points there, and the build fails when a label
would render under 18 points, as for the full diagrams. Generic: no DataPilot names. The sample
module's pattern slide reads a stand-in drawing of the same size, kept with the deck's private
assets, until the real export exists; the deck's own slides name exports only.

### The scoreboard

One recurring element tracks the fiscal year 2025 revenue question. A recap slide with
`scoreboard: N` shows four pills across the top of the content area, Sections 1 to 4 in order,
each headed by its loop's name, at 16 points. The current section's pill is filled in its loop's
colour with dark text and "Now:" before its state, the state at 18 points, since it is the
sentence the recap is about; the earlier ones are done, on the card colour with an outline in
their loop's colour (dark for the lime, as under "Cards"), a check mark beside the name, and their state; the later
ones are muted (outlined in blue-grey, the quiet tracker grey for text) and read "To come". The
states are the owner's sentences, held once in the outline builder (`SCOREBOARD`):

| After | State |
|---|---|
| Section 1 | The agent sees enough, but the answer is still wrong. |
| Section 2 | The wrong answer is caught and flagged, but only while someone is watching. |
| Section 3 | It runs safely unattended, but it is still wrong. |
| Section 4 | Correct: $64,015,091.21, posted at the level its family has earned. |

The payoff slide shows the scoreboard complete: all four pills filled, each with a check mark and
what that loop contributed (its `Loop:` line). No deck font has a check mark glyph, so the mark is
drawn as a line.

### The checks of design system 2

The outline builder adds these to every rule above:

- **The evidence diet.** No run id (a word of 8 or more hexadecimal characters with a digit in
  it), no date (a day and a month, a month and a day or a year, or a numeric date), and no
  `Sample:` line on any slide except the evidence, demo and payoff slides (and the sources slides'
  entries). They go into the speaker notes.
- **One insight per section, on its opener.** Each section has one opener, which holds exactly one
  `Insight:` line, and no other slide of the section holds one.
- **At most two code slides per section**, the pattern in code and DataPilot's version, each
  mechanism slide naming its panel `Pattern` or `DataPilot`.
- **The scoreboard.** Each section's recap carries `scoreboard` set to its section's number.
- **Structured Query Language** is spelled out once in the deck, on the title slide (the
  opening's first slide), and on no other slide; SQL is written bare everywhere else in the deck.
  The owner's decision is about this term alone: every other term (application programming
  interface, JavaScript Object Notation, and the rest) is still spelled out on its first use on
  each slide. The speaker notes are read as one page of their own and spell out each term at its
  first use there, SQL included.

## Rule sets while the deck is rewritten

The outline is built under one rule set. A block module without `RULES` follows the first
outline's rules, the deck's rules before this design system. When every block module of a plan
sets that plan's rule set (`"design system"` for the first rebuild's plan; `"design system 2"` for
the second's, with the new `problem` and `foundations` modules), the outline is built under that
plan; a module of another plan's block on another rule set keeps it from building. While the
modules disagree, `make outline` names each block and its rule set and writes nothing, so the
gate's outline check fails until the rewrite is merged whole. Check one rewritten block at any
time:

```bash
uv run python slides/source/build.py --check s1
uv run python slides/source/build.py --samples /tmp/samples-outline.md
```

The deck builder's `--type-samples` flag builds the sample module into
`slides/build/samples.pptx`, the folder git ignores.
