"""Embeds the deck's fonts in a built deck with PowerPoint, and checks that no font falls back.

    uv run --no-project --python 3.12 --with comtypes python slides/scripts/embed_fonts.py \
        slides/build/sample.pptx

Windows only, PowerPoint installed, and the fonts installed for the user first
(slides/scripts/install_fonts.py). It opens the deck, saves it in place with TrueType fonts
embedded (the SaveAs EmbedTrueTypeFonts option, the same as File > Options > Save > Embed fonts
in the file), then reopens it and lists every font the deck uses (the Replace Fonts list) and
every font in the file's embedded font list. It exits 1 when a font other than Fira Sans and
Lexend Medium is used, or when a used font is not embedded. PowerPoint's own Font.Embedded flag
reads False while the font is installed, so the embedded list is read from the file itself.
"""

from __future__ import annotations

import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

import comtypes.client

ALLOWED = {"Fira Sans", "Lexend Medium"}
PPT_SAVE_AS_OPEN_XML = 24
MSO_TRUE = -1


EMBEDDED = re.compile(r'<p:embeddedFont><p:font typeface="([^"]+)"')


def fonts_of(presentation) -> list[str]:
    fonts = presentation.Fonts
    return [fonts.Item(i).Name for i in range(1, fonts.Count + 1)]


def embedded_in(deck: Path) -> set[str]:
    with zipfile.ZipFile(deck) as package:
        xml = package.read("ppt/presentation.xml").decode("utf-8")
    return set(EMBEDDED.findall(xml))


def main(argv: list[str]) -> int:
    deck = Path(argv[0]).resolve()
    app = comtypes.client.CreateObject("PowerPoint.Application")
    try:
        with tempfile.TemporaryDirectory() as scratch:
            saved = Path(scratch) / deck.name
            presentation = app.Presentations.Open(str(deck), 0, 0, 0)
            try:
                presentation.SaveAs(str(saved), PPT_SAVE_AS_OPEN_XML, MSO_TRUE)
            finally:
                presentation.Close()
            shutil.copyfile(saved, deck)
        presentation = app.Presentations.Open(str(deck), -1, 0, 0)
        try:
            fonts = fonts_of(presentation)
        finally:
            presentation.Close()
    finally:
        app.Quit()
    embedded_fonts = embedded_in(deck)
    problems = 0
    for name in fonts:
        embedded = name in embedded_fonts
        state = "embedded" if embedded else "not embedded"
        print(f"font {name}: {state}")
        if name not in ALLOWED:
            print(f"  x {name} is not a deck font; it falls back on a machine without it")
            problems += 1
        elif not embedded:
            print(f"  x {name} is not embedded")
            problems += 1
    print(f"font problems: {problems}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
