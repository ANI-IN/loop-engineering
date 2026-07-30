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
    """Every string drawn on a figure, newline-joined. Tick labels included.

    Joined rather than returned as a list because the assertions are all "does this
    figure say X", and a disclosure split across two Text objects is still on the image.
    """
    return "\n".join(
        artist.get_text() for artist in figure.findobj(Text) if artist.get_text()
    )
