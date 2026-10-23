# Slide review: a read-only change list for the deck

Use this after the repo changes (a renamed file, a new count, a changed command or result) to
tell the deck's owner exactly what to update. The review never edits the deck: the owner may be
editing it, and two writers on one .pptx lose work.

## Procedure

1. **Copy the deck.** Copy `slides/<COURSE>.pptx` to a scratch folder. Never open, save, or
   script against the original.
2. **Extract the text and notes** of the copy with python-pptx:

   ```bash
   uv run python slides/scripts/extract_deck.py /tmp/deck-copy.pptx \
       --out /tmp/deck.md
   ```

   The Markdown has one `## Slide N: <title>` block per slide, with its layout, its text (table
   cells as rows), and its notes as a quote.
3. **Compare with the repo,** slide by slide. For each slide, check:
   - file paths and commands: does the file exist, does the command still run as written?
   - numbers and results: does each match the evidence page it comes from?
   - names: section, assignment, and tool names as the repo spells them; codes only in brackets;
   - timings: do the `Time:` lines still add up to the class length?
   - "Re-check after live runs" lines: is each still true after the latest runs?
4. **Write the change list** as a table, one row per outdated item:

   | Slide | Outdated (quote it) | Suggested wording | Source in the repo |
   |---|---|---|---|
   | 12: <title> | "<text on the slide or in its notes>" | "<new text>" | `<file>` |

   Quote the old text exactly so the owner can search for it. Suggest wording that fits the
   space on the slide; say "notes" when the change is in the speaker notes.
5. **Optional note additions:** a second, shorter table of notes the owner may want to add (a
   likely question, a fallback, a missing "Re-check after live runs" line). Mark these as
   optional.
6. **Hand it over** in chat or in a review page, never as an edited deck. When the owner has
   applied it, run steps 1 to 3 again on a fresh copy to confirm.

## Rules

- Never edit the deck, never save the copy back over it, never commit a changed deck for
  someone else.
- The repo is the source of truth: when a slide and the repo disagree, the slide changes (or
  the owner decides the repo is wrong and fixes the repo first).
- Report only what is outdated or wrong, with its source. Style preferences go in the optional
  table.
- An empty change list is a valid result: say "no slide contradicts the repo" and list what was
  checked.
