from __future__ import annotations

import streamlit as st

from app.config import get_config
from app.utils.session import current_user_email, logout


def render_sidebar(active_page: str = "Dashboard") -> None:
    config = get_config()

    with st.sidebar:
        st.title("LeadFlow AI")
        st.caption("Internal lead follow-up workspace")

        st.divider()
        st.markdown("**Signed in as**")
        st.write(current_user_email())

        st.divider()
        st.markdown("**Workspace**")
        st.write(active_page)
        st.caption(f"API: {config.api_base_url}")

        st.divider()
        if st.button("Log out", use_container_width=True):
            logout()
            st.switch_page("pages/login.py")
