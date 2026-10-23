# style: the prose and page checks

The style tools already live in the skeleton that `scripts/new_module.py` copies into a new
course, so they are not duplicated here:

- `platform/scripts/check_style.py`: the page checks (SC01 to SC30),
  configured per course in `platform/config/course.toml`. Run `--list-checks` for the full list.
- `platform/scripts/lint_prose.py`: banned words and phrases, and
  emoji, with the banned list in the same `course.toml`.

Run both on every page you write, the slide outline and the demo guide included:

```bash
uv run python platform/scripts/check_style.py --strict
uv run python platform/scripts/lint_prose.py
```

## Rules worth keeping in any course

1. **Banned words.** Filler and hype ("simply", "just", "seamless", "powerful", "robust") and
   internal phrases. Add **time words** that date a page: "tonight", "today's run", "this
   morning", "yesterday", "last week". A page is read for months; write the fact, not when it
   happened.
2. **Codes only in brackets.** An internal code (a section code such as S1, an assignment code
   such as A2) never stands bare in prose. Write the plain name, and add the code in brackets
   only where a reader needs it to find a file: "Section 2: State and sessions (S2)".
3. **Full name on first use.** The first mention of a named kind on a page uses its full
   "<Kind> N: <name>" form ("Assignment 1: Instructions"); later mentions may shorten it.
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

When you add a rule, add it to `course.toml` (words) or as a new SC check with a test, never
as a note in a page that a machine cannot check.
