# Module: Loop Engineering - guide: the demo-guide PDF builder

A Markdown-to-PDF builder for a live demo guide: a cover, a contents page with page numbers,
then one part per file, printed on `A4` paper by Playwright Chromium. No model calls, no containers.

| File | What it is |
|---|---|
| `build_pdf.py` | The builder; reads a JavaScript Object Notation (JSON) file (`--config`). |
| `template.html` | The page skeleton (`{{title}}`, `{{css}}`, `{{cover}}`, `{{toc}}`, `{{body}}`). |
| `style.css` | Print styles. Every colour is a CSS variable with a neutral default. |
| `CONVENTIONS.md` | The Markdown the builder turns into steps, boxes, commands and figures. |
| `intro.md` | A stub for the guide's introduction. |
| `guide.example.json` | A configuration file to copy into your guide folder as `guide.json`. |

## Set up a guide

```bash
mkdir -p guide/source guide/chapters guide/images
cp tools/guide/guide.example.json guide/guide.json
cp tools/guide/intro.md guide/source/intro.md
# edit guide.json: titles, output name, palette, parts
uv run python tools/guide/build_pdf.py --config guide/guide.json --images
```

`--images` first copies the images the Markdown uses from the capture folder (the configuration file's
`images`, filled by `tools/capture/`) into `guide/images/`, scaled to 2000 px wide, and drops
the unused ones. Missing images print as orange placeholder boxes and are listed.

## Conventions kept from the course this was cut from

- **Step template:** `### Step N: short action`, then the field lines `**Where:**`, `**Type:**`,
  `**You should see:**`, `**Look at:**`, `**What it means:**`, in that order.
- **Boxes:** `> [!CHECKPOINT]`, `> [!IFDIFFERENT]`, `> [!INSTRUCTOR]`, `> [!WARNING]`,
  `> [!NOTE]`; a line with "→" starts on a new line ("cause → fix").
- **Commands and output:** a `bash` block is a dark command box with a copy label; a `text`
  block is an output box of at most 12 lines.
- **Figures:** an image line, a blank line, an italic caption, then an optional numbered list
  whose numbers match the callouts drawn on the image. Kept on one page.
- **Palette:** override any variable from the configuration file's `palette`, for example
  `{"accent": "<your app's accent>"}`, so the guide matches the app on screen.

Scan the finished PDF before you share it: `tools/scan/scan_pdf.py`.
