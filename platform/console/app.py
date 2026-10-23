"""DataPilot console. Run from platform/console so .streamlit/config.toml and static/ apply:
    cd platform/console && streamlit run app.py

Four pages, one per loop. Each page reads live state from the ops schema (the open live session
only) and acts through the api over HTTP; the console never imports a loop package and never
starts a session. Rules: platform/console/DESIGN.md.
"""

from __future__ import annotations

import streamlit as st

PAGES = [
    st.Page("screens/agent.py", title="Agent", url_path="agent", default=True),
    st.Page("screens/verify.py", title="Verify", url_path="verify"),
    st.Page("screens/events.py", title="Events", url_path="events"),
    st.Page("screens/improve.py", title="Improve", url_path="improve"),
]

st.set_page_config(page_title="DataPilot", layout="wide", initial_sidebar_state="collapsed")
st.navigation(PAGES, position="top").run()
