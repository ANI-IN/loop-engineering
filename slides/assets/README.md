# Slide assets

Files the deck builder (`slides/source/build_deck.py`) places on slides.

## The DEMO slide laptop

`demo-laptop.png` (972 by 583 pixels) is the laptop picture of the DEMO slides in the Harness
Engineering deck, `slides/Harness Engineering for Coding Agents.pptx` in the reference repository
ANI-IN/harness-engineering-session (commit `562664c020c41f5013811a714f94ccbf236bc338`), where it is
`ppt/media/image53.png`. It is copied unchanged and placed at the same position as in that deck,
with the DEMO badge centred on its screen.

## Fonts

`fonts/` holds the two deck fonts, both under the SIL Open Font License 1.1, each with its
`OFL.txt`. They come from Google Fonts' repository, google/fonts:

| Folder | Files | Source in google/fonts |
|---|---|---|
| `fonts/fira-sans/` | Fira Sans regular, bold, italic, bold italic | `ofl/firasans`, commit `e345593da2a4d596212542edbd28f2ed08fe6cbe` |
| `fonts/lexend/` | `Lexend[wght].ttf`, the variable font | `ofl/lexend`, commit `e2332cf862ac3145c0ee5f24f04f4c1819b2410b` |

`fonts/lexend/Lexend-Medium.ttf` is made from the variable font by
`slides/scripts/make_lexend_medium.py` (weight 500, family name "Lexend Medium", the name the
template's DEMO badge uses). The license allows modified versions; its reserved font name is
"RevReading Lexend", which the static font does not use.

To embed the fonts in a built deck on Windows: install them for the current user with
`slides/scripts/install_fonts.py`, then run `slides/scripts/embed_fonts.py` on the deck.
