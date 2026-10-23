# capture: screenshots, terminal renders, and callouts for a guide

Four scripts, no model calls. Run them with the course repo's environment (`uv run python ...`);
they need Pillow, and `capture.py` also needs Playwright Chromium
(`uv run playwright install chromium`).

| File | What it does |
|---|---|
| `capturelib.py` | Pure helpers: host-path and user-name redaction, key refusal, URL masking, line ranges, callout geometry, `images.json` entries. |
| `capture.py` | Screenshots of a web app from a JSON config (base URL, viewport, shots, callout targets). |
| `term_render.py` | A terminal capture (`terminal.txt`) as a clean dark PNG, with line ranges and highlights. |
| `callouts.py` | Numbered circles, arrows, and outlines on an image; colours from the app's CSS tokens. |

## Rules the tools enforce

- **Viewport:** 1024x900 CSS px at device pixel ratio 2 by default, so text prints at 8 pt or
  more at A4 text width. Change it in the config's `viewport`, not in the code.
- **Redaction:** `/home/<name>`, `/Users/<name>`, `/mnt/c/Users/<name>`, and `C:\Users\<name>`
  become `~`; each name in the config's `users` becomes `<user>` (terminal renders), or stops
  the capture (screenshots).
- **Keys:** `sk-...`, `lsv2_...`, `ghp_...`, `AKIA...`, bearer tokens and private key blocks
  are refused. Nothing is written, and the error never repeats the key.
- **Accounts:** links that match `mask_urls` are shortened to `host/…` before the page is
  measured; links that match `account_urls`, and UUID-like ids, stop the capture.
- **Callouts verified:** a callout is drawn only when the element found holds the text the
  callout is about (`must`, or the `text` match). Dropped callouts are listed at the end.
- **Placement:** at most 7 callouts per image, numbered in reading order; circles go next to
  their target, inside the image, off other targets and busy pixels, and no arrow crosses
  another arrow or circle.

## Use

```bash
uv run python tools/capture/capture.py --config capture.json --out ~/guide-work/images/s1
uv run python tools/capture/term_render.py terminal.txt out.png --command "make demo" \
    --lines -12 --highlight 3 --user <your-user-name>
```

The config format is in the docstring of `capture.py`. Each run merges entries into
`<out>/images.json` (`file, screen, moment, alt, callouts, source_run_id, recorded_or_live`),
which the guide's captions and numbered lists are checked against.

Its tests live with the course kit, outside this repository.
