# Live Demo Guide: Markdown conventions

This page lists the Markdown the guide's PDF build turns into boxes and layout. Write plain
Markdown otherwise. `docs/STYLE.md` applies to every page here, and
`platform/scripts/check_style.py --strict` and `platform/scripts/lint_prose.py` check these files.

## Files and order

The PDF is, in order: the cover and the contents (built by the script), `part0.md`, the files in
`chapters/` in number order, and `appendix.md`. Each file has one H1. A chapter's H1 is
`# Chapter N: Section N: name`. The H1 and every H2 go into the contents; H3 headings do not.

## Steps

A step starts with `### Step N: short action`. Everything up to the next heading belongs to it.
The fields are paragraphs that start with a bold label, then three boxes, in this order (the
checker reports a missing or misplaced one as SC28):

| Field | What it holds |
|---|---|
| `**Where:**` | Which terminal or screen, and which folder |
| `**Type:**` | The copy-ready command, key, or click |
| `**You should see:**` | The real output or a screenshot from the recorded run |
| `**Look at:**` | The one line or element to read |
| `**What it means:**` | What it tells you, in plain words |
| `[!CHECKPOINT]` | One thing to confirm before going on |
| `[!IFDIFFERENT]` | One to three lines, each "what you see → the fix" |
| `[!INSTRUCTOR]` | What to point at and what to say in class |

A box is a blockquote whose first line is the marker, such as `> [!CHECKPOINT]`. `[!WARNING]` and
`[!NOTE]` boxes may also stand anywhere in a step. A line that holds "→" starts on a new line.

## Commands and output

- A fenced `bash` block is a command box: one command per line, no prompt sign, copied from a
  command that was really run. The only placeholder allowed is a value the reader supplies, such
  as the id of their own run.
- A fenced `text` block is an output box of at most 12 lines; use a terminal image for longer
  output.

## Screenshots and callouts

- An image on its own line, a blank line, an italic caption line, then an optional numbered list
  make one figure. The list numbers match the numbered circles on the image.
- Capture the console at a narrow viewport (about 1024 CSS pixels wide at 2x scale), so its text
  prints at 8 pt or more on the printed page. Prefer a focused crop that includes its heading over a full window.
- Place callouts in reading order, never crossing. Check in code that each one points at the
  element that holds its named text.
- Alt text and captions describe only what is visible in the frame. Check each one against the
  image; claims about a part that is cut off are the most common error.
- Mask host paths, user names, and account or workspace ids before capture, and scan the page
  text before saving.

## Dated words

Write "today", "in class", "this session", or "this run". The prose lint fails on words that only
make sense on the day they were written.
