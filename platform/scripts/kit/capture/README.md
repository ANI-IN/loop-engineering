# capture: screenshots, terminal renders, and callouts for a guide

The first four scripts make no model calls; `live_captures.py` drives live demos. Run them with the course repository's environment (`uv run python ...`);
they need Pillow, and `capture.py` also needs Playwright Chromium
(`uv run playwright install chromium`).

| File | What it does |
|---|---|
| `capturelib.py` | Pure helpers: host-path and user-name redaction, key refusal, URL masking, line ranges, callout geometry, `images.json` entries. |
| `capture.py` | Screenshots of a web app from a JSON configuration file (base URL, viewport, shots, callout targets). |
| `term_render.py` | A terminal capture (`terminal.txt`) as a clean dark PNG, with line ranges and highlights. |
| `callouts.py` | Numbered circles, arrows, and outlines on an image; colours from the app's CSS tokens. |
| `framing.py` | Whole-viewport frames of a Streamlit page (1280 by 720 at scale 2, Coordinated Universal Time): an element placed under the fixed header, then nudged until no edge, and nothing under the header, cuts a line. |
| `live_manifest.py` | DataPilot's live console captures: each image, the demo or chain step that produces it, its frame, its caption, and the state checks on the api's records. |
| `live_captures.py` | The runner the lead uses on the live stack: reset, trigger, wait for the state, capture, check, and log. Its usage is in its docstring. |

## Rules the tools enforce

- **Viewport:** 1024x900 CSS px at device pixel ratio 2 by default, so text prints at 8 pt or
  more at `A4` text width. Change it in the configuration's `viewport`, not in the code.
- **Redaction:** `/home/<name>`, `/Users/<name>`, `/mnt/c/Users/<name>`, and `C:\Users\<name>`
  become `~`; each name in the configuration's `users` becomes `<user>` (terminal renders), or stops
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
uv run python platform/scripts/kit/capture/capture.py --config capture.json --out ~/guide-work/images/s1
uv run python platform/scripts/kit/capture/term_render.py terminal.txt out.png --command "make demo" \
    --lines -12 --highlight 3 --user <your-user-name>
```

The configuration format is in the docstring of `capture.py`. Each run merges entries into
`<out>/images.json` (`file, screen, moment, alt, callouts, source_run_id, recorded_or_live`),
which the guide's captions and numbered lists are checked against.

The tests of `framing.py`, `live_captures.py`, `live_manifest.py`, and `term_render.py` are in
`platform/tests/unit/test_live_captures.py`.
