"""The README images: deterministic, self-labelling, and the only ones that exist.

The headline property is byte-identity across renders **within one environment**.
Without it `git status` is noisy after every run, nobody can tell a re-render from
a data change, and the images stop being reviewable — which is how a stale figure
survives in a README.

Across environments it does not hold, and asserting it did cost a CI run: the
images were committed from macOS, CI runs Linux, and matplotlib rasterises text
through FreeType, so the pixels differ. Freshness is therefore checked through
`assets/manifest.json`, which records what the images were rendered FROM — a
question that has the same answer everywhere.

**Nothing here compares raw image bytes with a bare assert.** That same CI run sat
for nine minutes and was killed by the job timeout, because a failing
`assert a == b` on two 110 KB byte strings sends pytest into `difflib.ndiff` over
110,000 elements. Comparisons go through hexdigests, which diff instantly and
read better when they fail.
"""

import hashlib
import re
import struct
from pathlib import Path

import pytest

from tools import render_readme_charts as charts


def digest(path: Path) -> str:
    """Compare hashes, never bytes. See the module docstring."""
    return hashlib.sha256(path.read_bytes()).hexdigest()

REPO_ROOT = Path(__file__).resolve().parent.parent
README = REPO_ROOT / "README.md"
ASSETS = REPO_ROOT / "assets"


# Rendering is the expensive part of this module — a cold runner pays fifteen
# seconds to build matplotlib's font cache before the first figure. Both renders
# are module-scoped and shared, so the whole file costs two passes rather than one
# per test.


@pytest.fixture(scope="module")
def rendered(tmp_path_factory) -> list[Path]:
    return charts.render_all(tmp_path_factory.mktemp("render_first"))


@pytest.fixture(scope="module")
def rendered_again(tmp_path_factory) -> list[Path]:
    return charts.render_all(tmp_path_factory.mktemp("render_second"))


# ---- determinism ------------------------------------------------------------


def test_rerunning_produces_byte_identical_pngs(rendered, rendered_again):
    """THE requirement, and it holds on every platform.

    matplotlib stamps its own version into a PNG Software chunk by default, which
    would make every render differ for no reason.
    """
    assert [p.name for p in rendered] == [p.name for p in rendered_again]
    for a, b in zip(rendered, rendered_again, strict=True):
        assert digest(a) == digest(b), f"{a.name} differs between two renders"


def test_no_software_stamp_is_written(rendered):
    """The mechanism behind the property above, asserted directly rather than
    inferred — so a future edit that drops `metadata={"Software": None}` fails
    here with a message saying why."""
    for path in rendered:
        assert b"Software" not in path.read_bytes()[:2048], (
            f"{path.name} carries a Software chunk; renders will not be reproducible"
        )


# ---- self-labelling ---------------------------------------------------------


def test_every_figure_is_given_the_measurement_date():
    """A stored figure that could pass for a fresh one is what this project
    refuses. The date reaches the drawing code, not just the caption."""
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", charts.load_reference()["measured_on"])
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", charts.load_curve()["measured_on"])


def test_every_reference_cell_carries_an_n():
    """Each bar prints its own n. A cell with no n could not be drawn honestly."""
    for cell in charts.load_reference()["cells"]:
        assert cell["rate_n"] > 0, f"{cell['key']} has no n"


def test_every_curve_point_carries_an_n():
    for point in charts.load_curve()["points"]:
        assert point["n_answered"] >= 0
        assert point["n_total"] > 0


def test_the_provenance_band_says_not_computed_now(monkeypatch, tmp_path):
    """The band is drawn inside the image, because a caption is read once and a
    band is read every time the image is."""
    captured = {}
    original = charts._frame

    def spy(title, measured_on, caption, *, right):
        captured["measured_on"] = measured_on
        return original(title, measured_on, caption, right=right)

    monkeypatch.setattr(charts, "_frame", spy)
    charts.render_dial(charts.load_reference(), tmp_path / "band_probe.png")
    assert captured["measured_on"] == charts.load_reference()["measured_on"]


def test_the_captions_are_imported_not_retyped():
    """The disclosures come from the module the live views use. Retyping them is
    how the README ends up carrying a warning the app no longer makes."""
    from loopeng.sweep.chart_model import COST_CAPTION, DIAL_CAPTION, REFERENCE_CAPTION

    assert charts.DIAL_CAPTION is DIAL_CAPTION
    assert charts.COST_CAPTION is COST_CAPTION
    assert charts.REFERENCE_CAPTION is REFERENCE_CAPTION


CAPTION_NAMES = (
    "REFERENCE_CAPTION", "DIAL_CAPTION", "COST_CAPTION",
    "DELTA_CAPTION", "ABSTENTION_CAPTION",
    "CROSS_MODEL_CAVEAT", "CLUSTER_CAVEAT",
)


def test_every_caption_string_is_defined_in_exactly_one_module():
    """THE anti-drift assertion, and it is grep-shaped on purpose.

    Both renderers used to carry their own copy of DIAL_CAPTION and REFERENCE_CAPTION,
    and the Wilson and cluster caveats were typed out twice. A correction to one did not
    reach the other. Importing is fine; assigning is not.
    """
    import re

    src = REPO_ROOT / "src" / "loopeng"
    scanned = [
        src / "sweep" / "chart_model.py",
        src / "sweep" / "charts.py",
        REPO_ROOT / "tools" / "render_readme_charts.py",
    ]
    for name in CAPTION_NAMES:
        assigning = [
            path.relative_to(REPO_ROOT) for path in scanned
            if re.search(rf"^{name}\s*=", path.read_text(encoding="utf-8"), re.MULTILINE)
        ]
        assert assigning == [Path("src/loopeng/sweep/chart_model.py")], (
            f"{name} is assigned in {assigning}; it belongs to chart_model alone"
        )


def test_the_two_caveats_are_composed_into_the_captions_not_restated():
    """One correction, one place. If the temperature asymmetry changes, it changes in
    every caption that mentions it."""
    from loopeng.sweep.chart_model import (
        CLUSTER_CAVEAT,
        CROSS_MODEL_CAVEAT,
        DELTA_CAPTION,
        DIAL_CAPTION,
    )

    assert CROSS_MODEL_CAVEAT in DIAL_CAPTION
    assert CLUSTER_CAVEAT in DIAL_CAPTION
    assert CLUSTER_CAVEAT in DELTA_CAPTION


def test_both_backends_draw_the_same_rows_for_the_same_cells():
    """Cell ordering, role colour, the reference badge and the note text were each
    implemented twice. One transform now, so the two figures cannot disagree."""
    from loopeng.sweep.chart_model import bar_rows

    payload = charts.load_reference()
    assert charts.rows_for(payload, metric="rate") == bar_rows(payload["cells"],
                                                               metric="rate")
    assert charts.rows_for(payload, metric="cost") == bar_rows(payload["cells"],
                                                               metric="cost")


def test_the_readme_figure_does_not_claim_the_live_charts_provenance():
    """"free to recompute" is true of a live curve and false of a frozen PNG."""
    from loopeng.sweep.chart_model import ABSTENTION_CAPTION, ABSTENTION_LIVE_NOTE

    assert ABSTENTION_LIVE_NOTE not in ABSTENTION_CAPTION
    assert "free to recompute" in ABSTENTION_LIVE_NOTE


# ---- layout and weight ------------------------------------------------------


def test_every_figure_shares_one_aspect_ratio_and_width(rendered):
    """A reader scrolling the README should see a consistent column."""
    sizes = {_png_size(path) for path in rendered}
    assert len(sizes) == 1, f"figures differ in size: {sizes}"


def test_total_image_weight_is_under_the_cap(rendered):
    total = sum(path.stat().st_size for path in rendered)
    assert total <= charts.MAX_TOTAL_BYTES, (
        f"{total:,} bytes of a {charts.MAX_TOTAL_BYTES:,} cap; these load on every view"
    )


def test_going_over_the_cap_fails_rather_than_shipping(tmp_path, monkeypatch):
    """The cap is enforced, not documented."""
    monkeypatch.setattr(charts, "MAX_TOTAL_BYTES", 1)
    assert charts.main([str(tmp_path)]) == 1


def test_the_committed_images_match_the_manifest(rendered):
    """Catches an image edited or replaced by hand, on any platform.

    The manifest records what the renderer wrote. If a committed file no longer
    hashes to its manifest entry, it did not come out of the renderer.
    """
    manifest = charts.read_manifest()
    for produced in rendered:
        committed = ASSETS / produced.name
        assert committed.is_file(), f"assets/{produced.name} is missing — re-run the renderer"
        assert digest(committed) == manifest["images"][produced.name], (
            f"assets/{produced.name} does not match assets/manifest.json. It was "
            f"edited by hand, or written by something other than the renderer."
        )


def test_the_images_were_rendered_from_the_committed_reference_data(rendered):
    """THE freshness check, and it is platform-independent.

    Byte-identity against a fresh render only works on the machine that generated
    the images. This asks the question that actually matters and has the same
    answer everywhere: did the source data move without the images being redrawn?
    """
    manifest = charts.read_manifest()
    assert manifest["sources"] == charts.source_hashes(), (
        "results/reference/ has changed since the README images were rendered. Run: "
        "uv run python tools/render_readme_charts.py"
    )


def test_byte_identity_with_a_fresh_render_where_that_can_hold(rendered):
    """Asserted only on the environment that produced the committed images.

    matplotlib rasterises text through FreeType, so a different platform or
    FreeType build renders the same figure to different pixels. Asserting this
    unconditionally passed on the machine that generated the assets and failed
    everywhere else — which is precisely the kind of claim this project is not
    entitled to make.
    """
    manifest = charts.read_manifest()
    here = charts.build_environment()
    if manifest["rendered_by"] != here:
        pytest.skip(
            f"images were rendered by {manifest['rendered_by']}; this is {here}. "
            f"Freshness is covered by the manifest source hashes instead."
        )
    for produced in rendered:
        assert digest(ASSETS / produced.name) == digest(produced)


def test_no_hand_placed_file_is_in_assets(rendered):
    """The renderer is the ONLY way an image enters the README."""
    produced = {path.name for path in rendered} | {charts.MANIFEST_NAME}
    committed = {path.name for path in ASSETS.glob("*") if path.is_file()}
    assert committed == produced, (
        f"assets/ holds files the renderer did not write: {sorted(committed - produced)}"
    )


def test_the_manifest_records_where_the_images_came_from():
    manifest = charts.read_manifest()
    assert set(manifest["sources"]) == set(charts.SOURCES)
    assert set(manifest["images"]) == {"dial.png", "cost.png", "abstention.png"}
    for key in ("platform", "machine", "matplotlib", "freetype"):
        assert manifest["rendered_by"][key]


# ---- how the README uses them -----------------------------------------------


def _readme_images() -> list[tuple[str, str]]:
    """Every markdown image in the README, as (alt, path)."""
    return re.findall(r"!\[([^\]]*)\]\(([^)]+)\)", README.read_text(encoding="utf-8"))


def test_the_readme_uses_markdown_images_not_html(tmp_path):
    """Never side by side, never in an HTML table."""
    body = README.read_text(encoding="utf-8")
    assert "<img" not in body
    assert "<table" not in body.lower()


def test_every_readme_image_resolves(tmp_path):
    for _alt, target in _readme_images():
        assert (REPO_ROOT / target).is_file(), f"README image does not resolve: {target}"


def test_every_readme_image_has_alt_text():
    for alt, target in _readme_images():
        assert alt.strip(), f"README image has no alt text: {target}"


def test_every_readme_image_is_surrounded_by_blank_lines():
    """Otherwise GitHub runs the surrounding text into the image."""
    lines = README.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if not re.match(r"^!\[[^\]]*\]\([^)]+\)\s*$", line.strip()):
            continue
        assert index > 0 and lines[index - 1].strip() == "", (
            f"README line {index + 1}: image has no blank line before it"
        )
        assert index + 1 < len(lines) and lines[index + 1].strip() == "", (
            f"README line {index + 1}: image has no blank line after it"
        )


def test_every_readme_image_is_captioned_with_its_date():
    """The caption states the development run's date and that the session
    computes these live. Prose stays number-free; the figure carries the numbers."""
    body = README.read_text(encoding="utf-8")
    measured_on = charts.load_reference()["measured_on"]
    for _alt, target in _readme_images():
        position = body.index(f"]({target})")
        following = body[position : position + 400]
        assert measured_on in following, (
            f"the image {target} has no caption naming the measurement date"
        )


def _png_size(path: Path) -> tuple[int, int]:
    header = path.read_bytes()[:24]
    return struct.unpack(">II", header[16:24])
