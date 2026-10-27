# style: the prose and page checks

The style tools live in `platform/scripts/`, beside this kit, so they are not duplicated here:

- `platform/scripts/check_style.py`: the page checks (SC00 to SC33, with no SC29), configured
  per course in `platform/config/course.toml`, whose `banned_phrases` adds phrases to the
  checker's own list. Run `--list-checks` for the full list.
- `platform/scripts/lint_prose.py`: banned words, time words, filler phrases, and emoji. Its lists
  are in the script itself; `course.toml` holds only the source titles allowed to contain a banned
  word (`[prose] allowed_titles`).

Run both on every page you write, the slide outline and the demo guide included:

```bash
uv run python platform/scripts/check_style.py --strict
uv run python platform/scripts/lint_prose.py
```

## Rules worth keeping in any course

1. **Banned words.** Hype ("seamless", "powerful", "robust"), filler phrases, and internal
   phrases. Add **time words** that date a page: "tonight", "tomorrow", "this morning",
   "yesterday". A page is read for months; write the fact, not when it happened.
2. **No codes: write the full name.** A short code for a section, an assignment, or a level never
   appears in prose, code comments, commit messages, or labels, not even in brackets. Write the
   full name every time it stands alone: "Section 2: Verification loop", "the report-only level".
   File and folder names use readable slugs instead, such as `section-2-verification-loop/`.
3. **Full name on first use.** The first mention of a named kind on a page uses its full
   `<Kind> N: <name>` form ("Assignment 1: Instructions"); later mentions may shorten it.
4. **Quoted line numbers are checked.** When a page quotes a tool's output or a source file
   "at line N", a check reads the file and confirms the line still says it. A line number that
   is not checked goes stale with the next edit: remove it or check it.
5. **Ids stay in the evidence pages.** Run ids, finding ids, and commit hashes appear only in
   the evidence pages; other pages link there.
6. **No leftovers.** TODO, TBD, FIXME, XXX, empty placeholders, angle-bracket leftovers, and
   template guidance comments fail the strict run.
7. **Images carry captions and real alt text.** An image line, a blank line, then an italic
   caption; alt text is a concrete sentence, not a file name.
8. **One H1 per page, the module title first.**

When you add a rule, add it to a list in `lint_prose.py` or to `banned_phrases` in `course.toml`
(words), or as a new SC check with a test, never as a note in a page that a machine cannot check.
