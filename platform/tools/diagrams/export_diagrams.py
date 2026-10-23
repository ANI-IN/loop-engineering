"""Export every Excalidraw diagram to SVG (font embedded) and PNG (scale 2), at authoring time only.

Learners never run this: the renders are committed beside their sources. It drives headless
Chromium through Playwright for Python (the dev dependency group) on export_page.html, a local page
that loads one pinned Excalidraw build from jsDelivr and calls its exportToSvg and exportToBlob.
No Node, no npm, no build step.

Each diagrams/ folder keeps a renders.json: for every source, the SHA-256 of the .excalidraw it was
rendered from and of the .svg and .png it produced. A test (platform/tests/unit/test_diagrams.py)
fails when a source changed without a new render, or a render changed by hand; it needs no browser.

Usage (from the repository root), with no option it renders what is stale:
    uv run python platform/tools/diagrams/export_diagrams.py
    --all      render every source
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


def diagram_folders(root: Path = REPO) -> list[Path]:
    folders = [root / "docs" / "diagrams", *sorted(root.glob("section-*/diagrams"))]
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
    result = page.evaluate("scene => window.diagrams.render(scene)", scene)
    if result["embeddedFonts"] < 1:
        raise SystemExit(f"{source.name}: the SVG has no embedded font")
    return result["svg"], base64.b64decode(result["png"])


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
        frames = [(spec.name, None)]
        if spec.steps:
            frames += [(f"{spec.name}-step-{n}", n) for n in range(1, scene.last_step + 1)]
        _remove_step_frames(folder, spec.name, {name for name, _ in frames})
        for name, upto in frames:
            path = folder / f"{name}.excalidraw"
            text = json.dumps(scene.frame(upto), indent=2, ensure_ascii=False) + "\n"
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
        found = problems()
        for line in found:
            print(line)
        print(f"diagrams: {len(sources())} sources, {len(found)} problems")
        return 1 if found else 0
    with browser_page() as page:
        if args.build:
            build(page, set(args.only) if args.only else None)
        todo = sources() if args.all else stale()
        export(todo, page)
    print(f"diagrams: {len(todo)} rendered, {len(sources())} sources")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
