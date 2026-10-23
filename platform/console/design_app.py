"""The design style tile, served on its own so the demo console never reaches specimen data.

    make style-tile        (http://localhost:8531)

It sits next to static/ so the self-hosted fonts load, and next to .streamlit/ so the theme applies.
"""

from __future__ import annotations

import streamlit as st

st.navigation(
    [st.Page("design/style_tile.py", title="Style tile", url_path="style-tile", default=True)],
    position="hidden",
).run()
