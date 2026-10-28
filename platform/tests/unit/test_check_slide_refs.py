"""The slide-reference check: a published page names only slides the final class deck has."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_slide_refs.py"


def _load():
    spec = importlib.util.spec_from_file_location("check_slide_refs", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["check_slide_refs"] = module
    spec.loader.exec_module(module)
    return module


check = _load()

# A deck of three slides in the outline's own form: a titled slide, an untitled one, and one with
# no text and no time in its notes.
OUTLINE = """# Outline

Deck: 3 slides, SHA-256 0000.

## Slide 1: `Which loop when: Match the loop to the failure`

On the slide:

```text
Which loop when: Match the loop to the failure
```

Speaker notes:

```text
Timing: 2 minutes (0:00-0:02)
```

## Slide 2

On the slide:

```text
Today’s Agenda
```

Speaker notes:

```text
Timing: 0 minutes (0:02-0:02)
```

## Slide 3

On the slide:

```text
(no text)
```

Speaker notes:

```text
(no notes)
```
"""
SLIDES = check.deck(OUTLINE)
RUN_OF_SHOW = """| Time | Slide | What you do |
|---|---|---|
| 0:00-0:02 | 1. Which loop when: Match the loop to the failure | Read it |
| 0:02-0:03 | No slide | The notes give this minute to no slide |
| 0:02 | 2. Today's Agenda | The star |
| None in the notes | 3. No text | Close |
"""


def test_the_deck_is_read_from_the_outline() -> None:
    assert SLIDES[1]["title"].startswith("Which loop when")
    assert SLIDES[2]["lines"] == ["Today’s Agenda"] and SLIDES[2]["time"] == "0:02"
    assert SLIDES[3] == {"title": "", "lines": [], "time": None}


def test_a_page_naming_only_the_decks_slides_passes() -> None:
    page = 'See slide 1, "Which loop when: Match the loop\nto the failure", and slides 2 to 3.\n'
    assert check.page_problems("page.md", page + "\n" + RUN_OF_SHOW, SLIDES) == []


def test_a_slide_number_past_the_deck_fails() -> None:
    assert check.page_problems("page.md", "Teach slides 2 to 4.\n", SLIDES) == [
        "page.md:1: slide 4: the deck has 3"
    ]


def test_a_wrong_title_after_a_number_fails() -> None:
    found = check.page_problems("page.md", 'On slide 2, "Which loop when: X".\n', SLIDES)
    assert found == ["page.md:1: slide 2 is 'untitled', not 'Which loop when: X'"]


def test_a_quoted_title_the_deck_lacks_fails() -> None:
    found = check.page_problems("page.md", 'The "Measured: With and without" slide.\n', SLIDES)
    assert found == ["page.md:1: no slide of the deck is titled 'Measured: With and without'"]


def test_a_run_of_show_row_must_match_its_slide() -> None:
    page = RUN_OF_SHOW.replace("0:00-0:02", "0:00-0:03").replace("2. Today's Agenda", "2. Recap")
    found = check.page_problems("guide.md", page, SLIDES)
    assert found == [
        "guide.md:3: slide 1 runs 0:00-0:02 in its notes, not 0:00-0:03",
        "guide.md:5: 'Recap' is not on slide 2",
    ]


def test_a_run_of_show_names_every_slide_once_in_order() -> None:
    page = "\n".join(line for line in RUN_OF_SHOW.splitlines() if "| 2. " not in line)
    assert check.page_problems("guide.md", page, SLIDES) == [
        "guide.md: its run of show does not name slides 1 to 3 once each, in order"
    ]


def test_code_blocks_are_not_read_and_line_numbers_hold() -> None:
    page = "```text\nslide 9\n```\n\nslide 9\n"
    assert check.page_problems("page.md", page, SLIDES) == ["page.md:5: slide 9: the deck has 3"]


def test_the_trees_pages_pass() -> None:
    assert check.main([]) == 0
