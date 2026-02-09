"""Devil's Dozen — Streamlit Application Entrypoint."""

from __future__ import annotations

import streamlit as st


def main() -> None:
    """Application entrypoint. Must call ``st.set_page_config`` first."""
    st.set_page_config(
        page_title="Devil's Dozen",
        page_icon="🎲",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    # Load medieval theme CSS
    from src.ui.themes import load_css
    load_css()

    # Session state defaults
    if "page" not in st.session_state:
        st.session_state["page"] = "home"
    if "_prior_roll_score" not in st.session_state:
        st.session_state["_prior_roll_score"] = 0

    # Page routing (lazy imports to avoid circular deps)
    page = st.session_state["page"]

    if page == "home" or page == "lobby_waiting":
        from src.ui.pages.home import render_home_page
        render_home_page()
    elif page == "game":
        from src.ui.pages.game import render_game_page
        render_game_page()
    elif page == "results":
        from src.ui.pages.results import render_results_page
        render_results_page()
    else:
        st.session_state["page"] = "home"
        st.rerun()


if __name__ == "__main__":
    main()
