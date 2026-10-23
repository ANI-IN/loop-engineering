# scan: keys, host paths, and account links before anything goes public

Two scripts, read-only, no network.

| File | What it scans |
|---|---|
| `scan_secrets.py` | A git repository: every tracked file, and the full history (`git log --all -p`, added lines and commit messages). |
| `scan_pdf.py` | The text of a PDF (the demo guide, a handout), page by page, with pypdf. |

## What counts

- **Keys:** `sk-...`, `lsv2_...`, `ghp_...` (and the other GitHub token prefixes), `AKIA...`,
  `xox?-...`, bearer tokens, and private key blocks. Patterns use word boundaries, so `sk-`
  inside `task-abc...` is not a key.
- **Host paths:** `/home/<name>/`, `/Users/<name>/`, `/mnt/c/Users/<name>`, `C:\Users\<name>`.
- **Account links (PDF):** UUID-like ids and any link matching `--account` regexes.
- **Placeholders (PDF):** TODO, TBD, FIXME, XXX, lorem ipsum, and `<ANGLE PLACEHOLDERS>` left in
  the text.

## Output

Only booleans per check, file names or page numbers, and masked prefixes (the first 4
characters and the length). A key is never printed, so the output can go in a report or a
chat. Both scripts exit 1 on a hit.

```bash
uv run python tools/scan/scan_secrets.py --repo . --paths
uv run --with pypdf python tools/scan/scan_pdf.py "guide/Demo Guide.pdf"
```

A key found in the history is still a leak after it is deleted from the tree: revoke it first,
then rewrite the history or build the public repository fresh (see `tools/release/`).
