# Module: Loop Engineering - guide: the demo-guide PDF builder

A Markdown-to-PDF builder for a live demo guide: a cover, a contents page with page numbers,
then one part per file, printed on `A4` paper by Playwright Chromium. No model calls, no containers.

| File | What it is |
|---|---|
| `build_pdf.py` | The builder; reads a JavaScript Object Notation (JSON) file (`--config`). |
| `template.html` | The page skeleton (`{{title}}`, `{{css}}`, `{{cover}}`, `{{toc}}`, `{{body}}`). |
| `style.css` | Print styles. Every colour is a CSS variable with a neutral default. |
| `CONVENTIONS.md` | The Markdown the builder turns into steps, boxes, commands and figures. |
| `intro.md` | The guide's introduction. |

## Build this guide

This guide's configuration file is `guide/guide.json`: its titles, output name, and parts.

```bash
uv run python guide/source/build_pdf.py --config guide/guide.json
```

The images stay where they live, in each section's `demo/expected/` folder, and nothing is copied;
a missing image prints as an orange placeholder box and is listed. The `--images` option is for a
guide whose Markdown points at an `images/` folder beside it: it copies those images from a
capture folder (the configuration file's `images`) into that folder, scaled to 2000 px wide. This
guide does not use it.

## Conventions

The Markdown the builder turns into steps, boxes, commands and figures is described in
[CONVENTIONS.md](CONVENTIONS.md). Any colour of `style.css` can be overridden from the
configuration file's `palette`, for example `{"accent": "<your app's accent>"}`.

Scan the finished PDF before you share it: `platform/scripts/kit/scan/scan_pdf.py`.
