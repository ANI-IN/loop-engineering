"""Makes the static Lexend Medium font (weight 500) from the variable Lexend font.

    uv run --no-project --python 3.12 --with fonttools python slides/scripts/make_lexend_medium.py \
        "slides/assets/fonts/lexend/Lexend[wght].ttf" slides/assets/fonts/lexend/Lexend-Medium.ttf

Google Fonts ships Lexend only as a variable font, and PowerPoint embeds static TrueType fonts. The
template's DEMO badge uses the family "Lexend Medium", so this writes the weight-500 instance under
that family name. The SIL Open Font License allows modified versions; the reserved font name is
"RevReading Lexend", which this does not use.
"""

from __future__ import annotations

import sys

from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

WEIGHT = 500
WINDOWS = (3, 1, 0x409)  # platform, encoding, language of the name records Windows reads


def main(source: str, target: str) -> None:
    static = instancer.instantiateVariableFont(
        TTFont(source), {"wght": WEIGHT}, updateFontNames=True
    )
    names = static["name"]
    for name_id, value in (
        (1, "Lexend Medium"),
        (2, "Regular"),
        (4, "Lexend Medium"),
        (6, "Lexend-Medium"),
    ):
        names.setName(value, name_id, *WINDOWS)
    # No typographic family (name ids 16 and 17): a font PowerPoint loads from the deck is looked
    # up by that family when present ("Lexend", weight Medium) and the badge asks for
    # "Lexend Medium", so the static font is its own family.
    names.names = [r for r in names.names if r.platformID == 3 and r.nameID not in (16, 17)]
    static["OS/2"].usWeightClass = WEIGHT
    static.save(target)
    print(f"wrote {target}: Lexend Medium, weight {WEIGHT}, fsType {static['OS/2'].fsType}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
