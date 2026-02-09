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

    # Load medieval theme CSS and sound system
    from src.ui.themes import (
        load_css,
        render_background_music,
        render_pending_sfx,
        render_sound_controls,
    )
    load_css()

    # Session state defaults
    if "page" not in st.session_state:
        st.session_state["page"] = "home"
    if "_prior_roll_score" not in st.session_state:
        st.session_state["_prior_roll_score"] = 0

    # Page routing (lazy imports to avoid circular deps)
    page = st.session_state["page"]

    if page == "home" or page == "lobby_waiting":
        from src.ui.views.home import render_home_page
        render_home_page()
    elif page == "game":
        from src.ui.views.game import render_game_page
        render_game_page()
    elif page == "results":
        from src.ui.views.results import render_results_page
        render_results_page()
    else:
        st.session_state["page"] = "home"
        st.rerun()

    # Sound system (sidebar controls + pending SFX + background music)
    render_sound_controls()
    render_pending_sfx()
    game_mode = st.session_state.get("game_mode")
    render_background_music(page, game_mode)


if __name__ == "__main__":
    main()
