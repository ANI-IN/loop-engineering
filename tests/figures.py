"""Reading what a figure actually says.

The live charts used to be SVG strings, so a test asserted on the markup: `"REFERENCE"
in svg`. They are matplotlib figures now, and the equivalent assertion has to look at
the drawn text rather than at a serialisation — otherwise a test either checks nothing
or checks a PNG's bytes, and neither says whether the disclosure reached the image.

Lives in tests/ rather than in the chart module: production code should not carry an
accessor that exists for assertions.
"""

from matplotlib.text import Text


def texts(figure) -> str:
    """Every string drawn on a figure, joined, with whitespace collapsed.

    Joined rather than returned as a list because the assertions are all "does this
    figure say X", and a disclosure split across two Text objects is still on the
    image.

    **Collapsed because the caption wrapper inserts newlines at the column width.**
    A phrase can be split mid-assertion — `"share no\nanswered items"` is the same
    content as `"share no answered items"` and a different string — so an assertion
    written against the sentence fails on a caption that contains it and renders it
    correctly.

    That happened three times in this build before the helper was fixed rather than
    the assertions. A test coupled to where the wrap lands passes and fails for
    reasons unrelated to the property it protects, in both directions, which is the
    same defect as a checker that matches nothing.
    """
    joined = " ".join(
        artist.get_text() for artist in figure.findobj(Text) if artist.get_text()
    )
    return " ".join(joined.split())
