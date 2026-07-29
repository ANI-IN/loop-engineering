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

`loopeng.sweep.charts` builds SVG strings for the live Gradio views, where the
figure is redrawn every few seconds while a sweep lands and must degrade to "in
progress, n=NN so far". This renders static PNGs of a frozen measurement for
GitHub. Different medium, different lifetime, different failure mode.

What is NOT forked is the part that would actually drift: the data comes from the
same `results/reference/` files the app reads, and the captions are imported from
`loopeng.sweep.charts` rather than retyped. If the disclosure about temperature
asymmetry changes there, it changes here.

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

from loopeng.sweep.charts import (  # noqa: E402
    COST_CAPTION,
    DIAL_CAPTION,
    REFERENCE_CAPTION,
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

INK = "#0b1220"
BODY = "#1e293b"
MUTED = "#64748b"
HAIRLINE = "#cbd5e1"
WORKER = "#0ea5e9"
FRONTIER = "#f97316"
REF_BAND = "#fef3c7"
REF_INK = "#92400e"

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


def _ordered_cells(payload: dict) -> list[dict]:
    """Sorted explicitly. File order is not a contract and a reordered input must
    not silently produce a different image."""
    return sorted(
        payload["cells"],
        key=lambda c: (c["role"], c["level"], c["mode"], c["replicate"]),
    )


def render_dial(payload: dict, path: Path) -> Path:
    """Silent-error rate per cell, with the Wilson interval and the n on each bar."""
    cells = _ordered_cells(payload)
    fig, ax = _frame(
        "Silent-error rate by cell — over answers that ran and returned",
        payload["measured_on"],
        f"{DIAL_CAPTION} {REFERENCE_CAPTION}",
        right=BAR_PLOT_RIGHT,
    )

    labels = [c["label"] for c in cells]
    values = [c["rate_value"] * 100 for c in cells]
    lows = [(c["rate_value"] - c["rate_ci_low"]) * 100 for c in cells]
    highs = [(c["rate_ci_high"] - c["rate_value"]) * 100 for c in cells]
    positions = list(range(len(cells)))

    ax.barh(
        positions, values,
        color="none",
        edgecolor=[WORKER if c["role"] == "worker" else FRONTIER for c in cells],
        linewidth=1.8,
        # Hatched, never solid: a stored measurement must not look like one this
        # session produced. Same rule the live chart follows.
        hatch="///",
        height=0.62,
    )
    ax.errorbar(
        values, positions, xerr=[lows, highs],
        fmt="none", ecolor=INK, elinewidth=1.4, capsize=4,
    )

    _value_gutter(
        ax, positions,
        [f"{value:.1f}%" for value in values],
        [cell["rate_n"] for cell in cells],
    )

    ax.set_yticks(positions)
    ax.set_yticklabels(labels, fontsize=9.5, color=BODY)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("silent-error rate (%) — lower is better", fontsize=9, color=MUTED)
    ax.grid(axis="x", color=HAIRLINE, linewidth=0.6, alpha=0.7)
    ax.set_axisbelow(True)
    return _save(fig, path)


def render_cost(payload: dict, path: Path) -> Path:
    """Estimated spend per cell. Estimated, never measured — see loopeng.pricing."""
    cells = _ordered_cells(payload)
    fig, ax = _frame(
        "Estimated spend by cell — tokens measured, dollars estimated",
        payload["measured_on"],
        f"{COST_CAPTION} {REFERENCE_CAPTION}",
        right=BAR_PLOT_RIGHT,
    )

    labels = [c["label"] for c in cells]
    values = [c["cost_usd"]["value"] for c in cells]
    positions = list(range(len(cells)))
    ceiling = max(values)

    ax.barh(
        positions, values,
        color="none",
        edgecolor=[WORKER if c["role"] == "worker" else FRONTIER for c in cells],
        linewidth=1.8, hatch="///", height=0.62,
    )
    _value_gutter(
        ax, positions,
        [f"est. ${value:.4f}" for value in values],
        [cell["rate_n"] for cell in cells],
    )

    ax.set_yticks(positions)
    ax.set_yticklabels(labels, fontsize=9.5, color=BODY)
    ax.invert_yaxis()
    ax.set_xlim(0, ceiling * 1.06)
    ax.set_xlabel("estimated USD per cell — includes calls that failed", fontsize=9, color=MUTED)
    ax.grid(axis="x", color=HAIRLINE, linewidth=0.6, alpha=0.7)
    ax.set_axisbelow(True)
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
        "Each point is one abstention threshold. Moving right answers more questions; "
        "moving up gets more of the answered ones right. The trade is the point — a "
        "single accuracy number hides it completely. Error bars are Wilson 95% on "
        "precision. Items are clustered parameterisations rather than independent "
        "trials, so every interval is narrower than the evidence supports. "
        + REFERENCE_CAPTION,
        right=0.97,
    )

    xs = [p["coverage_value"] * 100 for p in points]
    ys = [p["precision_value"] * 100 for p in points]
    lows = [(p["precision_value"] - p["precision_ci_low"]) * 100 for p in points]
    highs = [(p["precision_ci_high"] - p["precision_value"]) * 100 for p in points]

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
        ) * 100
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
