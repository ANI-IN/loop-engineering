"""Export every Excalidraw diagram to SVG (font embedded) and PNG (scale 2), at authoring time only.

Every slide diagram (a 1920 by 791 panel) and every pattern diagram (a 1920 by 540 panel) is also
exported for the deck: a PNG at scale 3 with a transparent background (the panel's fill left
out, so the slide's own light panel shows through) into the deck's own diagrams folder (DECK
below), which is private and never ships. Its renders.json records, for each PNG, the source it
came from and the SHA-256 of both.

Learners never run this: the renders are committed beside their sources. It drives headless
Chromium through Playwright for Python (the dev dependency group) on export_page.html, a local page
that loads one pinned Excalidraw build from jsDelivr and calls its exportToSvg and exportToBlob.
No Node, no npm, no build step.

Each diagrams/ folder keeps a renders.json: for every source, the SHA-256 of the .excalidraw it was
rendered from and of the .svg and .png it produced. A test (platform/tests/unit/test_diagrams.py)
fails when a source changed without a new render, or a render changed by hand; it needs no browser.

Usage (from the repository root), with no option it renders what is stale, pages and deck:
    uv run python platform/tools/diagrams/export_diagrams.py
    --all      render every source, pages and deck
    --build    write the sources from definitions.py first (a build overwrites hand edits)
    --check    report stale renders only, with no browser
Once per machine: uv run playwright install chromium
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import struct
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PAGE = HERE / "export_page.html"
MANIFEST = "renders.json"
EXCALIDRAW_VERSION = "0.18.1"  # @excalidraw/excalidraw on npm, released 2026-04-20
SCALE = 2
DECK = REPO / "slides" / "assets" / "diagrams"
DECK_SCALE = 3
SLIDE_PANEL = (1920, 791)  # scene.WIDTH by scene.SLIDE_HEIGHT: a slide's diagram panel
PATTERN_PANEL = (1920, 540)  # scene.WIDTH by scene.PATTERN_HEIGHT: a pattern slide's panel
DECK_PANELS = (SLIDE_PANEL, PATTERN_PANEL)  # the diagrams the deck shows


def diagram_folders(root: Path = REPO) -> list[Path]:
    folders = [
        root / "docs" / "diagrams",
        root / "docs" / "diagrams" / "patterns",
        *sorted(root.glob("section-*/diagrams")),
    ]
    return [f for f in folders if f.is_dir()]


def sources(root: Path = REPO) -> list[Path]:
    return [s for folder in diagram_folders(root) for s in sorted(folder.glob("*.excalidraw"))]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_manifest(folder: Path) -> dict[str, Any]:
    path = folder / MANIFEST
    if not path.exists():
        return {"excalidraw": EXCALIDRAW_VERSION, "renders": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def write_manifest(folder: Path, manifest: dict[str, Any]) -> None:
    manifest["about"] = (
        "SHA-256 of each diagram source and of the renders made from it, written by "
        "platform/tools/diagrams/export_diagrams.py; do not edit by hand."
    )
    manifest["renders"] = dict(sorted(manifest["renders"].items()))
    ordered = {k: manifest[k] for k in ("about", "excalidraw", "renders")}
    text = json.dumps(ordered, indent=2) + "\n"
    (folder / MANIFEST).write_text(text, encoding="utf-8", newline="\n")


def problems(root: Path = REPO) -> list[str]:
    """Every source without a current SVG and PNG, and every render without its source."""
    out: list[str] = []
    for folder in diagram_folders(root):
        manifest = read_manifest(folder)
        renders = manifest.get("renders", {})
        names = {s.stem for s in folder.glob("*.excalidraw")}
        for name in sorted(names):
            source = folder / f"{name}.excalidraw"
            rel = source.relative_to(root).as_posix()
            entry = renders.get(name)
            if entry is None:
                out.append(f"{rel}: never rendered")
                continue
            if entry["source"] != sha256(source):
                out.append(f"{rel}: changed since its last render")
            for suffix in ("svg", "png"):
                render = source.with_suffix(f".{suffix}")
                if not render.exists():
                    out.append(f"{rel}: no .{suffix}")
                elif entry[suffix] != sha256(render):
                    out.append(f"{render.relative_to(root).as_posix()}: not the recorded render")
        for name in sorted(set(renders) - names):
            out.append(f"{folder.relative_to(root).as_posix()}/{MANIFEST}: {name} has no source")
    return out


def panel_size(source: Path) -> tuple[float, float]:
    panel = json.loads(source.read_text(encoding="utf-8"))["elements"][0]
    return panel["width"], panel["height"]


def deck_sources(root: Path = REPO) -> list[Path]:
    """The deck's diagrams: every source on a slide panel (1920 by 791) or a pattern panel (1920
    by 540), without the step frames (no slide builds a diagram up today, and each export is about
    a megabyte)."""
    return [
        s
        for s in sources(root)
        if panel_size(s) in DECK_PANELS and not re.search(r"-step-\d+$", s.stem)
    ]


def deck_scene(scene: dict[str, Any]) -> dict[str, Any]:
    """The scene for the deck: the same elements with the panel's fill and outline left out, so
    the export has a transparent background and keeps the panel's size."""
    elements = [dict(e) for e in scene["elements"]]
    elements[0]["backgroundColor"] = "transparent"
    elements[0]["strokeColor"] = "transparent"
    return {**scene, "elements": elements}


def read_deck_manifest(deck: Path) -> dict[str, Any]:
    path = deck / MANIFEST
    if not path.exists():
        return {"excalidraw": EXCALIDRAW_VERSION, "scale": DECK_SCALE, "renders": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def write_deck_manifest(deck: Path, manifest: dict[str, Any]) -> None:
    manifest["about"] = (
        "The deck's diagram exports: PNG at scale 3, transparent background. For each, the source "
        "it came from and the SHA-256 of the source and of the PNG, written by "
        "platform/tools/diagrams/export_diagrams.py; do not edit by hand."
    )
    manifest["scale"] = DECK_SCALE
    manifest["renders"] = dict(sorted(manifest["renders"].items()))
    ordered = {k: manifest[k] for k in ("about", "excalidraw", "scale", "renders")}
    deck.mkdir(parents=True, exist_ok=True)
    text = json.dumps(ordered, indent=2) + "\n"
    (deck / MANIFEST).write_text(text, encoding="utf-8", newline="\n")


def deck_problems(root: Path = REPO) -> list[str]:
    """Every slide diagram without a current deck PNG, and every deck PNG without its source.
    Nothing to check where the deck's assets folder is absent: the public copy leaves it out, and
    the private test of the deck's exports requires it."""
    deck = root / DECK.relative_to(REPO)
    if not deck.parent.is_dir():
        return []
    rel_deck = DECK.relative_to(REPO).as_posix()
    renders = read_deck_manifest(deck).get("renders", {})
    out: list[str] = []
    wanted: dict[str, Path] = {}
    for source in deck_sources(root):
        if source.stem in wanted:
            rel = source.relative_to(root).as_posix()
            out.append(f"{rel}: a second slide diagram named {source.stem}")
        wanted[source.stem] = source
    for name, source in sorted(wanted.items()):
        entry = renders.get(name)
        png = deck / f"{name}.png"
        if entry is None:
            out.append(f"{rel_deck}/{name}.png: never exported for the deck")
            continue
        origin = source.relative_to(root).as_posix()
        if entry["from"] != origin or entry["source"] != sha256(source):
            out.append(f"{rel_deck}/{name}.png: its source changed since the export")
        if not png.exists():
            out.append(f"{rel_deck}/{name}.png: missing")
        elif entry["png"] != sha256(png):
            out.append(f"{rel_deck}/{name}.png: not the recorded export")
    for name in sorted(set(renders) - set(wanted)):
        out.append(f"{rel_deck}/{MANIFEST}: {name} has no slide diagram source")
    if deck.is_dir():
        for png in sorted(deck.glob("*.png")):
            if png.stem not in renders:
                out.append(f"{rel_deck}/{png.name}: not recorded in {MANIFEST}")
    return out


def deck_stale(root: Path = REPO) -> list[Path]:
    """The slide diagrams whose deck export is missing or out of date (none without the deck's
    assets folder, as in the public copy)."""
    deck = root / DECK.relative_to(REPO)
    if not deck.parent.is_dir():
        return []
    renders = read_deck_manifest(deck).get("renders", {})
    found = []
    for source in deck_sources(root):
        entry = renders.get(source.stem)
        png = deck / f"{source.stem}.png"
        current = entry is not None and entry["source"] == sha256(source) and png.exists()
        if not (current and entry["png"] == sha256(png)):
            found.append(source)
    return found


def export_deck(paths: list[Path], page: Any) -> None:
    """The deck's PNG at scale 3 with a transparent background, for each slide diagram."""
    manifest = read_deck_manifest(DECK)
    for source in paths:
        scene = deck_scene(json.loads(source.read_text(encoding="utf-8")))
        result = page.evaluate(
            "([scene, options]) => window.diagrams.render(scene, options)",
            [scene, {"scale": DECK_SCALE, "svg": False}],
        )
        data = base64.b64decode(result["png"])
        _require_scale(source, scene, data, DECK_SCALE)
        DECK.mkdir(parents=True, exist_ok=True)
        png = DECK / f"{source.stem}.png"
        png.write_bytes(data)
        manifest["excalidraw"] = EXCALIDRAW_VERSION
        manifest["renders"][source.stem] = {
            "from": source.relative_to(REPO).as_posix(),
            "source": sha256(source),
            "png": sha256(png),
        }
        write_deck_manifest(DECK, manifest)
        print(f"exported {png.relative_to(REPO).as_posix()}")


def prune_deck(root: Path = REPO) -> None:
    """Drop deck exports whose slide diagram is gone (a rebuild with fewer steps, a rename)."""
    deck = root / DECK.relative_to(REPO)
    if not deck.is_dir():
        return
    manifest = read_deck_manifest(deck)
    keep = {s.stem for s in deck_sources(root)}
    for name in sorted(set(manifest["renders"]) - keep):
        (deck / f"{name}.png").unlink(missing_ok=True)
        manifest["renders"].pop(name)
    write_deck_manifest(deck, manifest)


def page_version(page: Path = PAGE) -> str:
    found = re.search(r'EXCALIDRAW_VERSION = "([^"]+)"', page.read_text(encoding="utf-8"))
    return found.group(1) if found else ""


@contextmanager
def browser_page() -> Iterator[Any]:
    """The export page, loaded and ready, in headless Chromium."""
    from playwright.sync_api import sync_playwright  # authoring time only (dev group)

    if page_version() != EXCALIDRAW_VERSION:
        raise SystemExit(
            "export_page.html and export_diagrams.py name different Excalidraw versions"
        )
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(PAGE.as_uri())
        version = page.evaluate("window.diagrams.ready")
        if errors:
            raise SystemExit(f"the export page failed: {errors[0]}")
        print(f"Excalidraw {version} in Chromium {browser.version}")
        try:
            yield page
        finally:
            browser.close()


def render(page: Any, source: Path) -> tuple[str, bytes]:
    scene = json.loads(source.read_text(encoding="utf-8"))
    result = page.evaluate(
        "([scene, options]) => window.diagrams.render(scene, options)",
        [scene, {"scale": SCALE, "svg": True}],
    )
    if result["embeddedFonts"] < 1:
        raise SystemExit(f"{source.name}: the SVG has no embedded font")
    png = base64.b64decode(result["png"])
    _require_scale(source, scene, png, SCALE)
    return result["svg"], png


def png_size(png: bytes) -> tuple[int, int]:
    """Width and height from a PNG's header (its first chunk, IHDR)."""
    if png[:8] != b"\x89PNG\r\n\x1a\n" or png[12:16] != b"IHDR":
        raise ValueError("not a PNG")
    width, height = struct.unpack(">II", png[16:24])
    return width, height


def _require_scale(source: Path, scene: dict[str, Any], png: bytes, scale: int) -> None:
    panel = scene["elements"][0]
    wanted = (round(panel["width"] * scale), round(panel["height"] * scale))
    if png_size(png) != wanted:
        raise SystemExit(
            f"{source.name}: the PNG is {png_size(png)}, not {wanted} at scale {scale}"
        )


def export(paths: list[Path], page: Any) -> None:
    for source in paths:
        folder = source.parent
        svg, png = render(page, source)
        source.with_suffix(".svg").write_text(svg + "\n", encoding="utf-8", newline="\n")
        source.with_suffix(".png").write_bytes(png)
        manifest = read_manifest(folder)
        manifest["excalidraw"] = EXCALIDRAW_VERSION
        manifest["renders"][source.stem] = {
            "source": sha256(source),
            "svg": sha256(source.with_suffix(".svg")),
            "png": sha256(source.with_suffix(".png")),
        }
        write_manifest(folder, manifest)
        print(f"rendered {source.relative_to(REPO).as_posix()}")


def stale(root: Path = REPO) -> list[Path]:
    found = []
    for source in sources(root):
        entry = read_manifest(source.parent).get("renders", {}).get(source.stem)
        current = entry is not None and entry["source"] == sha256(source)
        current = current and all(
            source.with_suffix(f".{s}").exists() and entry[s] == sha256(source.with_suffix(f".{s}"))
            for s in ("svg", "png")
        )
        if not current:
            found.append(source)
    return found


def _remove_step_frames(folder: Path, name: str, keep: set[str]) -> None:
    """A rebuild may have fewer steps: drop the frames it no longer writes, with their renders
    and their records."""
    manifest = read_manifest(folder)
    for old in folder.glob(f"{name}-step-*.excalidraw"):
        if old.stem in keep:
            continue
        for suffix in (".excalidraw", ".svg", ".png"):
            old.with_suffix(suffix).unlink(missing_ok=True)
        manifest["renders"].pop(old.stem, None)
    write_manifest(folder, manifest)


def build(page: Any, only: set[str] | None = None) -> list[Path]:
    """Write the .excalidraw sources from definitions.py: the full diagram and its step frames."""
    sys.path.insert(0, str(HERE))
    import definitions  # noqa: PLC0415 (authoring time only)

    written: list[Path] = []
    failed: list[str] = []
    for spec in definitions.DIAGRAMS:
        if only and spec.name not in only:
            continue
        scene = spec.build()
        try:
            scene.place(
                page.evaluate("items => window.diagrams.measure(items)", scene.measure_requests())
            )
        except ValueError as error:
            print(error)
            failed.append(spec.name)
            continue
        folder = REPO / spec.folder
        frames: list[tuple[str, int | None, str | None]] = [(spec.name, None, None)]
        if spec.steps:
            frames += [(f"{spec.name}-step-{n}", n, None) for n in range(1, scene.last_step + 1)]
        frames += [(f"{spec.name}-{loop}-loop", None, loop) for loop in spec.highlights]
        _remove_step_frames(folder, spec.name, {name for name, _, _ in frames})
        for name, upto, highlight in frames:
            path = folder / f"{name}.excalidraw"
            text = json.dumps(scene.frame(upto, highlight=highlight), indent=2, ensure_ascii=False)
            text += "\n"
            path.write_text(text, encoding="utf-8", newline="\n")
            written.append(path)
        print(f"built {spec.folder}/{spec.name} ({len(frames)} files)")
    if failed:
        raise SystemExit(f"not built: {', '.join(failed)}")
    return written


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--all", action="store_true", help="render every source, not only stale")
    parser.add_argument("--build", action="store_true", help="write sources from definitions.py")
    parser.add_argument("--only", nargs="*", help="with --build: these diagram names only")
    parser.add_argument("--check", action="store_true", help="report stale renders; no browser")
    args = parser.parse_args(argv)
    if args.check:
        found = problems() + deck_problems()
        for line in found:
            print(line)
        print(
            f"diagrams: {len(sources())} sources, {len(deck_sources())} for the deck, "
            f"{len(found)} problems"
        )
        return 1 if found else 0
    with browser_page() as page:
        if args.build:
            build(page, set(args.only) if args.only else None)
        todo = sources() if args.all else stale()
        export(todo, page)
        prune_deck()
        everything = deck_sources() if DECK.parent.is_dir() else []
        deck = everything if args.all else deck_stale()
        export_deck(deck, page)
    print(
        f"diagrams: {len(todo)} rendered, {len(deck)} exported for the deck, "
        f"{len(sources())} sources"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
