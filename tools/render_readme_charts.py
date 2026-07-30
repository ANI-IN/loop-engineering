"""The only way an image enters the README.

Nothing here is hand-placed, screenshotted, or cropped out of a browser. Every
file in `assets/` is written by this script, from `results/reference/`, and a
test asserts re-running it produces byte-identical output.

WHY THE IMAGES LABEL THEMSELVES
-------------------------------

A README image outlives every sentence next to it. It gets screenshotted, pasted
into a deck, and quoted back six months later with the caption long gone. So the
provenance is drawn **inside the image**, where it cannot be separated from the
number:

  - the measurement date, in the header band of every figure
  - the `n` behind every bar and every point, next to that bar or point
  - a REFERENCE band saying in words that this was not computed just now

A stored figure that could pass for a fresh one is exactly what this project
refuses, and a README is the easiest place in the world for one to survive.

WHY IT IS NOT THE APP'S CHART CODE
----------------------------------

`loopeng.sweep.charts` draws whatever is on disk now: it is redrawn as a sweep
lands, degrades to "in progress, n=NN so far", and is not required to be
byte-identical between runs. This renders a FROZEN measurement that ships in the
README, where byte-identity is the property the whole file rests on. Same
library, same model, different lifetime and different failure mode.

That used to read "builds SVG strings for the live Gradio views". Both halves
were wrong — it is matplotlib now, and no view ever consumed those figures.

What is NOT forked is `loopeng.sweep.chart_model`: the caption prose, the cell
ordering, the role colours, and the cell-to-row transform all come from there, so
both backends draw the same rows for the same payload and only the geometry differs.

That boundary used to be drawn in the wrong place. The captions were imported, but
cell ordering, worker/frontier colouring, the hatched-outline convention for stored
bars and the value-and-n gutter were each implemented twice — and the wrapping of
`DIAL_CAPTION` with `REFERENCE_CAPTION` was assembled differently in each. Two
implementations of a disclosure's layout is one that can be shortened in one place.

DETERMINISM, AND ITS LIMIT
--------------------------

**Within one environment, re-running this produces byte-identical PNGs.** That is
the property the README depends on: `git status` stays silent after a re-render,
so a change to an image is always a change to the data, and the images stay
reviewable.

matplotlib stamps its own version into a PNG `Software` chunk by default, which
would break that. It is suppressed below. Nothing else here reads a clock, a
random seed, or a dict whose order is not sorted first.

**Across environments it is NOT byte-identical, and claiming otherwise cost a CI
run.** matplotlib rasterises text through FreeType, and a different platform or
FreeType build produces different pixels for the same figure. A test asserting the
committed images matched a fresh render therefore passed on the machine that
generated them and failed everywhere else.

So freshness is tracked by a manifest instead. `assets/manifest.json` records the
hash of each image, the hash of every source file it was rendered from, and the
environment that rendered it. That makes the check that matters —
*"did the data change without the images being regenerated?"* — answerable
anywhere, while byte-identity is only asserted where it can honestly hold.
"""

import hashlib
import json
import platform
import sys
from pathlib import Path

import matplotlib

# Agg before pyplot: no display, no backend probing, no window manager.
matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from loopeng.sweep.chart_model import (  # noqa: E402
    ABSTENTION_CAPTION,
    COST_CAPTION,
    DIAL_CAPTION,
    FRONTIER_COLOUR,
    REFERENCE_CAPTION,
    WORKER_COLOUR,
    bar_rows,
    money,
    ordered_cells,
    role_colour,
)

REFERENCE_DIR = REPO_ROOT / "results" / "reference"
ASSETS_DIR = REPO_ROOT / "assets"

# One aspect ratio and one pixel width for every figure, so a reader scrolling the
# README sees a consistent column rather than a ransom note.
#
# Taller than a slide would be, because the disclosures are long and they are not
# optional. A caption clipped by the figure edge is a disclosure that silently did
# not ship, which is the failure this project is least entitled to.
#
# DPI is set by the weight cap rather than by taste: at 140 the three figures came
# to 403 KB against a 400 KB budget and the renderer refused. The right response
# was fewer pixels, not a shorter disclosure.
FIG_W_IN, FIG_H_IN = 10.0, 6.9     # 1200 x 828 px at the DPI below
DPI = 120

# Layout, in figure fractions. The plot is squeezed from below rather than the
# caption being shortened.
PLOT_TOP, PLOT_BOTTOM = 0.845, 0.315
CAPTION_TOP = 0.235
CAPTION_COLUMNS = 150

# The bar charts reserve a right-hand gutter and print the value and its n there,
# in axes coordinates, as two aligned columns. Drawing them just past the end of
# each bar looks fine until one bar is long, and then the label leaves the figure.
BAR_PLOT_RIGHT = 0.76
VALUE_COLUMN = 1.03
N_COLUMN = 1.26

# Total weight across every asset. These load on every page view, and a README
# that costs a megabyte to open is a README people stop opening.
MAX_TOTAL_BYTES = 400_000

# A proportion becomes an axis percentage. Named because it appears in three figures.
PERCENT = 100

# Room past the longest cost bar so its printed value is not flush against the frame.
COST_HEADROOM = 1.06

INK = "#0b1220"
BODY = "#1e293b"
MUTED = "#64748b"
HAIRLINE = "#cbd5e1"
REF_BAND = "#fef3c7"
REF_INK = "#92400e"

# The role palette comes from the shared model, so a role is the same colour on the
# projector and in the README. Aliased rather than re-declared.
WORKER = WORKER_COLOUR
FRONTIER = FRONTIER_COLOUR

# matplotlib's bundled font. Named explicitly so a font installed on one machine
# and not another cannot change the rendering.
plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["savefig.facecolor"] = "white"


def _wrap(text: str, width: int) -> str:
    words, line, lines = text.split(), "", []
    for word in words:
        if len(line) + len(word) + 1 > width:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    lines.append(line)
    return "\n".join(lines)


def _frame(title: str, measured_on: str, caption: str, *, right: float):
    """A figure with the provenance band every image in this project carries.

    `right` leaves a gutter for the value column on the bar charts, so a label
    never runs off the edge — a clipped number is worse than no number.
    """
    fig, ax = plt.subplots(figsize=(FIG_W_IN, FIG_H_IN), dpi=DPI)
    fig.subplots_adjust(left=0.30, right=right, top=PLOT_TOP, bottom=PLOT_BOTTOM)

    fig.text(0.026, 0.962, title, fontsize=15, fontweight="bold", color=INK, va="top")

    # The band is drawn, not written in a caption, because a caption is read once
    # and a band is read every time the image is.
    fig.text(
        0.026, 0.905,
        f"  REFERENCE · measured {measured_on} · not computed in this session  ",
        fontsize=10, fontweight="bold", color=REF_INK, va="top",
        bbox={"facecolor": REF_BAND, "edgecolor": "none", "pad": 4.0},
    )

    fig.text(
        0.026, CAPTION_TOP, _wrap(caption, CAPTION_COLUMNS),
        fontsize=7.2, color=MUTED, va="top", linespacing=1.5,
    )
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color(HAIRLINE)
    ax.tick_params(colors=MUTED, labelsize=9)
    return fig, ax


def _value_gutter(ax, positions, values: list[str], counts: list[int]) -> None:
    """Two aligned columns outside the axes: the value, and the n behind it."""
    for position, value, count in zip(positions, values, counts, strict=True):
        ax.text(
            VALUE_COLUMN, position, value,
            transform=ax.get_yaxis_transform(),
            va="center", ha="left", fontsize=9.5, color=INK, fontweight="bold",
        )
        ax.text(
            N_COLUMN, position, f"n={count}",
            transform=ax.get_yaxis_transform(),
            va="center", ha="left", fontsize=9, color=MUTED,
        )


def _save(fig, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Software=None strips the matplotlib version stamp, which is the only piece
    # of nondeterminism matplotlib writes into a PNG by default.
    fig.savefig(path, format="png", metadata={"Software": None})
    plt.close(fig)
    return path


def load_reference() -> dict:
    return json.loads((REFERENCE_DIR / "measurements.json").read_text(encoding="utf-8"))


def load_curve() -> dict:
    return json.loads((REFERENCE_DIR / "abstention_curve.json").read_text(encoding="utf-8"))


def rows_for(payload: dict, *, metric: str) -> list[dict]:
    """The shared cell-to-row transform. Same rows the live backend draws.

    Ordering, role colour, the reference badge and the note text are all decided in
    `loopeng.sweep.chart_model`, so this file cannot disagree with the live chart about
    any of them.
    """
    return bar_rows(payload["cells"], metric=metric)


def _barh(ax, rows, values):
    """The bar call both figures make. Hatched, never solid: a stored measurement must
    not look like one this session produced. Same rule the live chart follows."""
    return ax.barh(
        list(range(len(rows))), values,
        color="none",
        edgecolor=[role_colour(row["role"]) for row in rows],
        linewidth=1.8, hatch="///", height=0.62,
    )


def _y_labels(ax, rows) -> list[int]:
    positions = list(range(len(rows)))
    ax.set_yticks(positions)
    # The bare cell label, not chart_model's `REFERENCE · ` prefix: every bar in this
    # figure is a reference bar and the band above already says so once, in words. The
    # live chart needs the per-row prefix because it mixes the two.
    ax.set_yticklabels([row["label"].removeprefix("REFERENCE · ") for row in rows],
                       fontsize=9.5, color=BODY)
    ax.invert_yaxis()
    ax.grid(axis="x", color=HAIRLINE, linewidth=0.6, alpha=0.7)
    ax.set_axisbelow(True)
    return positions


def render_dial(payload: dict, path: Path) -> Path:
    """Silent-error rate per cell, with the Wilson interval and the n on each bar."""
    rows = rows_for(payload, metric="rate")
    fig, ax = _frame(
        "Silent-error rate by cell — over answers that ran and returned",
        payload["measured_on"],
        f"{DIAL_CAPTION} {REFERENCE_CAPTION}",
        right=BAR_PLOT_RIGHT,
    )

    values = [row["value"] * PERCENT for row in rows]
    lows = [(row["value"] - row["lo"]) * PERCENT for row in rows]
    highs = [(row["hi"] - row["value"]) * PERCENT for row in rows]

    _barh(ax, rows, values)
    positions = _y_labels(ax, rows)
    ax.errorbar(
        values, positions, xerr=[lows, highs],
        fmt="none", ecolor=INK, elinewidth=1.4, capsize=4,
    )
    _value_gutter(ax, positions, [f"{value:.1f}%" for value in values],
                  [row["n"] for row in rows])

    ax.set_xlim(0, PERCENT)
    ax.set_xlabel("silent-error rate (%) — lower is better", fontsize=9, color=MUTED)
    return _save(fig, path)


def render_cost(payload: dict, path: Path) -> Path:
    """Estimated spend per cell. Estimated, never measured — see loopeng.pricing."""
    rows = rows_for(payload, metric="cost")
    fig, ax = _frame(
        "Estimated spend by cell — tokens measured, dollars estimated",
        payload["measured_on"],
        f"{COST_CAPTION} {REFERENCE_CAPTION}",
        right=BAR_PLOT_RIGHT,
    )

    values = [row["value"] for row in rows]
    _barh(ax, rows, values)
    positions = _y_labels(ax, rows)
    _value_gutter(ax, positions, [money(value) for value in values],
                  [row["n"] for row in rows])

    ax.set_xlim(0, max(values) * COST_HEADROOM)
    ax.set_xlabel("estimated USD per cell — includes calls that failed", fontsize=9, color=MUTED)
    return _save(fig, path)


def render_abstention(payload: dict, path: Path) -> Path:
    """Coverage against precision as the abstention threshold moves.

    The trade is the point. A single accuracy number hides it completely.
    """
    points = sorted(
        (p for p in payload["points"]
         if p["coverage_value"] is not None and p["precision_value"] is not None),
        key=lambda p: p["coverage_value"],
    )
    fig, ax = _frame(
        f"Coverage vs precision as the threshold moves — {payload['label']}",
        payload["measured_on"],
        # The same caption the live ABSTENTION chart carries. It used to be typed out
        # here, which meant the Wilson and cluster caveats existed in two places on this
        # figure alone — see the module docstring.
        f"{ABSTENTION_CAPTION} {REFERENCE_CAPTION}",
        right=0.97,
    )

    xs = [p["coverage_value"] * PERCENT for p in points]
    ys = [p["precision_value"] * PERCENT for p in points]
    lows = [(p["precision_value"] - p["precision_ci_low"]) * PERCENT for p in points]
    highs = [(p["precision_ci_high"] - p["precision_value"]) * PERCENT for p in points]

    ax.plot(xs, ys, color=WORKER, linewidth=1.8, zorder=2)
    ax.errorbar(xs, ys, yerr=[lows, highs], fmt="none",
                ecolor=INK, elinewidth=1.2, capsize=4, alpha=0.6, zorder=1)
    ax.scatter(xs, ys, s=46, color=WORKER, zorder=3)

    # Label every distinct operating point once. Several thresholds land on the
    # same point; labelling each would stack identical text on itself. Thresholds
    # that share a point are listed together rather than one being picked.
    grouped: dict[tuple[float, float], list[dict]] = {}
    for point, x, y in zip(points, xs, ys, strict=True):
        grouped.setdefault((round(x, 4), round(y, 4)), []).append(point)

    # Anchored beyond the interval cap rather than beside the marker, so a label
    # never sits on the error bar it belongs to, and alternated above/below so two
    # neighbouring points cannot stack their labels on the same row. Alignment
    # flips at the edges so nothing is pushed outside the figure.
    for index, ((x, _y), sharing) in enumerate(sorted(grouped.items())):
        thresholds = ", ".join(f"{p['threshold']:.2f}" for p in sharing)
        label = (
            f"threshold{'s' if len(sharing) > 1 else ''} {thresholds}\n"
            f"n={sharing[0]['n_answered']} answered"
        )
        above = index % 2 == 1
        anchor = (
            max(p["precision_ci_high"] for p in sharing) if above
            else min(p["precision_ci_low"] for p in sharing)
        ) * PERCENT
        align = "right" if x > 90 else ("left" if x < 10 else "center")
        ax.annotate(
            label, (x, anchor), textcoords="offset points",
            xytext=(0, 10 if above else -10),
            fontsize=8, color=BODY, ha=align, va="bottom" if above else "top",
        )

    ax.set_xlim(-6, 108)
    ax.set_ylim(-14, 100)
    ax.set_xlabel("coverage (%) — share of questions answered at all",
                  fontsize=9, color=MUTED)
    ax.set_ylabel("precision (%) — share of ANSWERED that are right",
                  fontsize=9, color=MUTED)
    ax.grid(color=HAIRLINE, linewidth=0.6, alpha=0.7)
    ax.set_axisbelow(True)
    return _save(fig, path)


SOURCES = ("measurements.json", "abstention_curve.json")
MANIFEST_NAME = "manifest.json"


# ---------------------------------------------------------------------------
# The README captions, generated from the same JSON the images are drawn from.
#
# §12 argues that a figure's `n` and its date belong INSIDE the image, because a README
# image outlives every sentence next to it. The same argument applies one level out: a
# vague caption lets the figure be quoted without its values, and typing the values into
# the README by hand would make the caption the next number that drifts.
#
# So the numeric caption is a generated markdown TABLE. A table rather than prose for a
# specific reason: `tests/test_docs.py::test_the_readme_prose_names_no_measurement` strips
# table rows before checking that the prose states no measurement, and that rule is right —
# prose is where a number gets separated from its provenance. A table row carries its cell
# label with it.
#
# `tests/test_readme_charts.py` asserts the README contains exactly what this produces.
# ---------------------------------------------------------------------------
CAPTION_MARKER = "<!-- generated: tools/render_readme_charts.py -->"

REPRODUCE_COMMANDS = {
    "dial.png": "uv run python demos/04_hill_climbing_loop/charts.py --reference=compare",
    "cost.png": "uv run python demos/04_hill_climbing_loop/charts.py --reference=compare",
    "abstention.png": "uv run python demos/04_hill_climbing_loop/charts.py --reference=compare",
}


def _provenance(measured_on: str, model_id: str, reproduce: str) -> list[str]:
    """The sentence every generated caption ends with. One wording, not three."""
    return [
        "",
        f"These are the author's development-run measurements from **{measured_on}** on "
        f"`{model_id}`. They are **REFERENCE — not computed on your machine.** To render "
        f"the equivalent chart from your own key:",
        "",
        "```bash",
        reproduce,
        "```",
    ]


def caption_for(name: str, measurements: dict, curve: dict) -> str:
    """The generated markdown block that sits under one image in README §12."""
    measured_on = measurements["measured_on"]
    lines = [CAPTION_MARKER, ""]

    if name == "dial.png":
        lines += ["| cell | silent-error rate | est. cost |", "|---|---|---|"]
        # The cell's OWN rendered string, not a recomputation. Wilson is asymmetric about
        # p, and `Metric.render` deliberately reports the WIDER arm because the mean of
        # the two understates the error — which is exactly what a second implementation
        # here computed on the first attempt. One definition of ±, and it lives in Metric.
        for cell in ordered_cells(measurements["cells"]):
            lines.append(
                f"| `{cell['key']}` | {cell['silent_error_rate']} "
                f"| {money(cell['cost_usd']['value'])} |"
            )
        lines += _provenance(measured_on, "claude-sonnet-5", REPRODUCE_COMMANDS[name])
    elif name == "cost.png":
        lines += ["| cell | est. cost | n |", "|---|---|---|"]
        for row in rows_for(measurements, metric="cost"):
            lines.append(f"| `{row['key']}` | {money(row['value'])} | {row['n']} |")
        lines += _provenance(measured_on, "claude-sonnet-5", REPRODUCE_COMMANDS[name])
    elif name == "abstention.png":
        lines += ["| threshold | answered | coverage | precision |", "|---|---|---|---|"]
        for point in curve["points"]:
            lines.append(
                f"| {point['threshold']:.2f} | {point['n_answered']} | "
                f"{point['coverage']} | {point['precision']} |"
            )
        lines += _provenance(curve["measured_on"], "claude-haiku-4-5",
                             REPRODUCE_COMMANDS[name])
    else:
        raise ValueError(f"no caption defined for {name!r}")
    return "\n".join(lines)


def captions() -> dict[str, str]:
    """Every generated caption, keyed by the image it belongs under."""
    measurements, curve = load_reference(), load_curve()
    return {name: caption_for(name, measurements, curve) for name in sorted(SOURCE_IMAGES)}


SOURCE_IMAGES = ("dial.png", "cost.png", "abstention.png")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes() -> dict[str, str]:
    """Hash of every file the images are rendered FROM.

    This is what makes staleness detectable on a machine that cannot reproduce
    the pixels: if these move and the images did not, the README is out of date
    regardless of what platform anyone is on.
    """
    return {name: _sha256(REFERENCE_DIR / name) for name in SOURCES}


def build_environment() -> dict[str, str]:
    """What rendered these. Byte-identity can only be asserted where this matches."""
    from matplotlib import ft2font

    return {
        "platform": platform.system(),
        "machine": platform.machine(),
        "matplotlib": matplotlib.__version__,
        "freetype": ft2font.__freetype_version__,
    }


def render_all(assets_dir: Path = ASSETS_DIR, *, manifest: bool = True) -> list[Path]:
    """Write every README image. The complete set, every time."""
    measurements = load_reference()
    curve = load_curve()
    written = [
        render_dial(measurements, assets_dir / "dial.png"),
        render_cost(measurements, assets_dir / "cost.png"),
        render_abstention(curve, assets_dir / "abstention.png"),
    ]
    if manifest:
        write_manifest(written, assets_dir)
    return written


def write_manifest(written: list[Path], assets_dir: Path) -> Path:
    path = assets_dir / MANIFEST_NAME
    path.write_text(
        json.dumps(
            {
                "note": (
                    "Generated by tools/render_readme_charts.py. Not hand-edited. "
                    "`sources` is what makes a stale image detectable on a machine "
                    "that cannot reproduce the pixels; matplotlib does not rasterise "
                    "identically across platforms."
                ),
                "measured_on": load_reference()["measured_on"],
                "sources": source_hashes(),
                "images": {p.name: _sha256(p) for p in sorted(written, key=lambda p: p.name)},
                "rendered_by": build_environment(),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def read_manifest(assets_dir: Path = ASSETS_DIR) -> dict:
    return json.loads((assets_dir / MANIFEST_NAME).read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    assets_dir = Path(argv[0]) if argv else ASSETS_DIR

    written = render_all(assets_dir)
    total = sum(path.stat().st_size for path in written)

    environment = build_environment()
    print(f"rendered by {environment['platform']}/{environment['machine']}, "
          f"matplotlib {environment['matplotlib']}, freetype {environment['freetype']}")
    for path in written:
        # Relative when it is inside the repo, absolute otherwise. `relative_to`
        # raises on a path outside the root, which made the tool unusable for a
        # dry run into a scratch directory.
        shown = path.relative_to(REPO_ROOT) if path.is_relative_to(REPO_ROOT) else path
        print(f"  wrote {shown}  {path.stat().st_size:,} bytes")
    print(f"total image weight: {total:,} bytes of a {MAX_TOTAL_BYTES:,} byte cap")

    if total > MAX_TOTAL_BYTES:
        print("OVER THE CAP — these load on every README view. Reduce DPI or drop a figure.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
