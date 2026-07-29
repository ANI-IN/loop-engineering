"""Fixture: geometry marked `# layout`, which must be exempt.

Every literal here is an SVG coordinate or a display truncation. None of them can
encode a finding, and banning them would make the rule irritating enough to be
switched off — which protects less than a narrow rule people keep.
"""

BAR_HEIGHT = 26  # layout: bar height
PAD_LEFT = 300  # layout: label gutter


def render(label: str) -> str:
    return f'<text x="{PAD_LEFT - 12}" y="{BAR_HEIGHT}">{label[:52]}</text>'  # layout
