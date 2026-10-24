# layout-check: does the app hold at every width, pixel ratio, and zoom?

`layout_check.py` opens each page of a JSON configuration file in Playwright Chromium at many viewports and
prints every layout problem. Exit 1 on any problem, so it can gate a release or a continuous integration job. No
model calls; the app must already be running (or serve recorded data).

## The sweep

- every `step` CSS pixels from `min_width` to `max_width` (default 320 to 2560, step 40), at each of
  `heights` (600 and 1000), pixel ratio 1;
- pixel ratios `dprs` (1.25, 1.5, 2) at the `dpr_widths`;
- the named `viewports`: a 1920 by 1080 laptop at 150% and 125% display scaling, a small laptop,
  class screen sizes, a phone, and a browser at 150% and 175% zoom.

## The rules

1. No horizontal overflow: the page never scrolls sideways.
2. Nothing reaches past the right edge of the window.
3. No element is wider than its own box, except inside lists built to scroll
   (`scroll_selector`, default `[data-scroll]`).
4. No text is cut by an ellipsis unless the element carries the full text as a `title`.
5. Nothing clips its content vertically.
6. Pills (`pill_selector`) stay on one line.
7. No word of 8 or more letters or digits breaks across lines.
8. The page scrolls to its last panel (`panel_selector`).

## Use

```bash
uv run python platform/scripts/kit/layout-check/layout_check.py --config layout.json --shots /tmp/layout
```

```json
{"pages": [{"name": "home", "url": "http://127.0.0.1:8000/"},
           {"name": "run-screen-1", "url": "http://127.0.0.1:8000/run/1", "press": ["1"]}],
 "step": 80}
```

`--shots DIR` saves one full-page screenshot per page and viewport, named
`<page>-<width>x<height>[@dpr].png`, to look at by eye. Run the full sweep before each release
and a coarse one (`"step": 160`) while you work. The pure rule function, `problems()`, is
tested with the course kit, outside this repository.
